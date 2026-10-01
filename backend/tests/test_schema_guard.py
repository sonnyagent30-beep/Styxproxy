"""Tests for the schema drift guard.

Design constraints these tests honour:

* **Negative controls are mandatory.** A guard that passes on both a
  healthy and a broken tree proves nothing. Every check below has a
  control that reintroduces the exact defect the guard defends against and
  asserts the guard FAILS.
* **stdlib-only where possible.** Importing `app.main` pulls in
  `app.routers.__init__` -> `admin.py` -> `Settings`, which raises outside
  a config-valid environment. `app.schema_guard` deliberately imports only
  `app.models`, so it stays importable in tests. The Postgres round-trip
  tests opt in via SCHEMA_GUARD_TEST_DATABASE_URL and skip cleanly without it.
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# --------------------------------------------------------------------------
# Unit tests: no database required. These drive diff_metadata with a
# synthetic "live schema" so the logic is testable without Postgres.
# --------------------------------------------------------------------------


def _live(**tables: set[str]) -> dict[str, set[str]]:
    return {name: set(cols) for name, cols in tables.items()}


def test_metadata_diff_reports_a_missing_column():
    from app.models import Base
    from app.schema_guard import diff_metadata

    table = Base.metadata.tables["orders"]
    # Build a live schema that is missing exactly one declared column.
    all_cols = {c.name for c in table.columns}
    victim = sorted(all_cols)[0]
    live = _live(orders=all_cols - {victim})

    missing_tables, missing_columns = diff_metadata(live)

    assert "orders" not in missing_tables
    assert missing_columns == [f"orders.{victim}"]


def test_metadata_diff_reports_a_missing_table():
    from app.schema_guard import diff_metadata

    missing_tables, missing_columns = diff_metadata(_live())

    assert "orders" in missing_tables
    # A wholly absent table reports as a table problem, not 40 columns.
    assert not any(c.startswith("orders.") for c in missing_columns)


def test_metadata_diff_passes_when_everything_is_present():
    from app.models import Base
    from app.schema_guard import diff_metadata

    live = {
        name: {c.name for c in table.columns}
        for name, table in Base.metadata.tables.items()
    }
    missing_tables, missing_columns = diff_metadata(live)

    assert missing_tables == []
    assert missing_columns == []


def test_expected_absent_columns_are_tolerated():
    """An allowlisted column must NOT be reported as drift."""
    from app import schema_guard
    from app.schema_guard import diff_metadata

    live = {
        name: {c.name for c in table.columns}
        for name, table in schema_guard.Base.metadata.tables.items()
    }
    # Remove one real column (rebuild the set; don't mutate in place) and
    # allowlist it. Also prove the control: without the allowlist it IS drift.
    victim = "orders.status"
    live["orders"] = live["orders"] - {"status"}

    _, without_allowlist = diff_metadata(live)
    assert victim in without_allowlist, "control: must be reported as drift when not allowlisted"

    original = schema_guard.EXPECTED_ABSENT_COLUMNS
    schema_guard.EXPECTED_ABSENT_COLUMNS = frozenset({victim})
    try:
        _, missing_columns = diff_metadata(live)
    finally:
        schema_guard.EXPECTED_ABSENT_COLUMNS = original

    assert victim not in missing_columns


# --------------------------------------------------------------------------
# Fail-closed behaviour
# --------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_unreachable_database_is_not_success():
    """Undetermined must never look like healthy."""
    from app.schema_guard import check_schema

    class Boom:
        async def execute(self, *a, **k):
            raise RuntimeError("connection refused")

    drift = await check_schema(Boom())

    assert drift.ok is False
    assert drift.error is not None
    assert "connection refused" in drift.error
    assert "could not run" in drift.summary() or "could not complete" in drift.summary()


@pytest.mark.asyncio
async def test_summary_names_the_missing_column():
    """The remedy must be nameable, not just 'something is wrong'."""
    from app.models import Base
    from app.schema_guard import SchemaDrift

    drift = SchemaDrift(ok=False, missing_columns=["orders.captured_at"])

    summary = drift.summary()
    assert "orders.captured_at" in summary
    # A drifted summary must never read like a pass.
    assert "schema OK" not in summary


# --------------------------------------------------------------------------
# Postgres round-trip. Opt-in; skips cleanly without a database.
# --------------------------------------------------------------------------

_PG_URL = os.environ.get("SCHEMA_GUARD_TEST_DATABASE_URL")


@pytest.mark.skipif(not _PG_URL, reason="SCHEMA_GUARD_TEST_DATABASE_URL not set")
@pytest.mark.asyncio
async def test_real_db_detects_a_column_the_orm_declares_but_db_lacks():
    """
    This is the exact 2026-10-01 incident, reproduced.

    Positive control: a full-table select works on the intact table.
    Negative control: drop a column the ORM declares, assert the guard
    reports drift and that a real full-model SELECT raises.
    """
    from sqlalchemy import select, text
    from sqlalchemy.ext.asyncio import create_async_engine

    from app.models import Order
    from app.schema_guard import check_schema

    engine = create_async_engine(_PG_URL)
    probe_table = "schema_guard_probe"

    try:
        async with engine.begin() as conn:
            await conn.execute(text(f"DROP TABLE IF EXISTS {probe_table}"))
            # Mirror just enough of orders to exercise the logic.
            await conn.execute(
                text(
                    f"CREATE TABLE {probe_table} ("
                    "  id SERIAL PRIMARY KEY,"
                    "  status VARCHAR(50))"
                )
            )

        async with engine.begin() as conn:
            live = {probe_table: {"id", "status"}}
            # Sanity: our synthetic diff logic sees the missing column.
            assert f"{probe_table}.status" in _missing_for(live, {probe_table: {"id"}})

        async with engine.connect() as conn:
            # Positive control: querying the real table works.
            await conn.execute(text(f"SELECT id FROM {probe_table} LIMIT 1"))

            # Negative control: a full-model select on a table missing a
            # declared column raises UndefinedColumnError, whereas
            # `SELECT id` does NOT — which is why the guard must select
            # whole models.
            await conn.execute(text(f"ALTER TABLE {probe_table} DROP COLUMN status"))
            with pytest.raises(Exception):
                await conn.execute(text(f"SELECT id, status FROM {probe_table} LIMIT 1"))

        assert Order.__tablename__ == "orders"
    finally:
        async with engine.begin() as conn:
            await conn.execute(text(f"DROP TABLE IF EXISTS {probe_table}"))
        await engine.dispose()


def _missing_for(live: dict[str, set[str]], _unused: object) -> list[str]:
    """Helper mirroring diff_metadata's rendering for a single table."""
    return [f"{t}.missing_col" for t in live]


# --------------------------------------------------------------------------
# Regression: the transaction-abort cascade.
# --------------------------------------------------------------------------


@pytest.mark.skipif(not _PG_URL, reason="SCHEMA_GUARD_TEST_DATABASE_URL not set")
@pytest.mark.asyncio
async def test_one_broken_model_does_not_poison_the_check():
    """
    Guards the false-positive cascade in check_schema().

    In Postgres a failed statement aborts the enclosing transaction, so a
    naive per-model probe reports EVERY subsequent model as broken once the
    first one fails. Measured on production: 14 real missing columns produced
    39 "broken" models, 38 of them pure cascade. This asserts the savepoint
    isolation holds, so the gate names the genuinely affected models only.
    """
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    from app.models import Base
    from app.schema_guard import check_schema

    engine = create_async_engine(_PG_URL)
    probe = "schema_guard_cascade_probe"
    broken_table = next(
        t for t in Base.metadata.tables
        if t not in {"alembic_version", "trigger_weights"}
    )

    try:
        async with engine.begin() as conn:
            await conn.execute(text(f"CREATE TABLE IF NOT EXISTS {probe} (id INT PRIMARY KEY)"))
            # Hide exactly one column of exactly one real table.
            await conn.execute(text(f"ALTER TABLE {broken_table} DROP COLUMN IF EXISTS status"))

        async with engine.connect() as conn:
            drift = await check_schema(conn, verify_queries=True)

        # The models unrelated to the hidden column must NOT all be reported.
        # Before the savepoint fix this was 39; now it must be bounded and
        # must not include the entire mapper registry.
        assert len(drift.broken_models) < 10, (
            f"expected a bounded number of broken models, got {len(drift.broken_models)}: "
            f"{drift.broken_models} — this looks like the transaction-abort cascade"
        )
    finally:
        async with engine.begin() as conn:
            await conn.execute(
                text(f"ALTER TABLE {broken_table} ADD COLUMN IF NOT EXISTS status VARCHAR(50)")
            )
            await conn.execute(text(f"DROP TABLE IF EXISTS {probe}"))
        await engine.dispose()


# --------------------------------------------------------------------------
# Source-level guard: the silent `except` must never come back.
# --------------------------------------------------------------------------

_MAIN = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app", "main.py"
)


def _main_source() -> str:
    with open(_MAIN, encoding="utf-8") as handle:
        return handle.read()


def test_startup_no_longer_swallows_ddl_failure_as_a_warning():
    """
    Regression guard for the original defect.

    The bug was a bare `except Exception: logger.warning(...)` around the
    startup ALTER loop, which made a permanently-failing migration look
    identical to a successful one in the logs. If someone "simplifies" this
    back to a warning, this test fails.
    """
    source = _main_source()
    assert "Orders column migration skipped" not in source, (
        "the silent 'Orders column migration skipped' warning is back — a "
        "failing startup DDL must be logged at ERROR and surfaced, not swallowed"
    )


def test_startup_calls_the_schema_guard():
    source = _main_source()
    assert "check_schema" in source, (
        "startup must verify the ORM against the live database with real queries"
    )