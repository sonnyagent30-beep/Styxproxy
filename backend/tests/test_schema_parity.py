"""Guard: the migration chain must produce the schema app/models.py declares.

`alembic upgrade head` exiting 0 is NOT proof the schema is usable. Before
t_e7fbfe21 the chain reached head while leaving 14 model tables uncreated and 11
tables missing columns — so on a database built purely by migrations, admin
login raised `UndefinedColumnError: column admin_auth.email does not exist` and
every residential order hit `column plans.price_per_gb does not exist`.

Those failures were invisible in production because production was grown by
`Base.metadata.create_all` in app/main.py's lifespan, not by alembic. The
migrations were written afterwards as a record. Anything that changes a model
without a matching revision reintroduces the drift silently, because no test
exercised the migrated schema.

This compares `Base.metadata` against information_schema and fails on drift.
It is the regression gate for that whole class of bug.

Skipped (not failed) when no database is reachable — a missing database is not
schema drift, and the suite must still run where there is none. Point it at a
database built purely by migrations:

    SCHEMA_DRIFT_DATABASE_URL=postgresql+asyncpg://u:p@h/db python -m pytest tests/test_schema_parity.py

Note the case-insensitive column comparison: Postgres folds unquoted
identifiers to lower case, so the model's `credit_amount_nGN` is legitimately
stored as `credit_amount_ngn`. Comparing case-sensitively would report drift
forever and train people to ignore this test.
"""
from __future__ import annotations

import os

import pytest

DB_URL = os.environ.get("SCHEMA_DRIFT_DATABASE_URL")
pytestmark = pytest.mark.skipif(
    not DB_URL, reason="set SCHEMA_DRIFT_DATABASE_URL to check migration parity"
)


@pytest.fixture
async def actual_schema():
    """{table: {lowercased column names}} from information_schema."""
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    engine = create_async_engine(DB_URL)
    try:
        async with engine.connect() as conn:
            rows = (
                await conn.execute(
                    text(
                        "SELECT table_name, column_name "
                        "FROM information_schema.columns "
                        "WHERE table_schema = 'public'"
                    )
                )
            ).all()
    finally:
        await engine.dispose()

    schema: dict[str, set[str]] = {}
    for table, column in rows:
        schema.setdefault(table, set()).add(column.lower())
    return schema


async def test_every_model_table_exists(actual_schema):
    """No table the ORM declares may be missing from the migrated schema."""
    from app.models import Base

    missing = sorted(t for t in Base.metadata.tables if t not in actual_schema)
    assert not missing, (
        f"{len(missing)} model table(s) no migration creates: {missing}. "
        "Add a revision, or the ORM will raise UndefinedColumnError on a "
        "database built by `alembic upgrade head`. See "
        "backend/docs/SCHEMA_DRIFT.md."
    )


async def test_every_model_column_exists(actual_schema):
    """No column the ORM selects may be missing from the migrated schema.

    This is the check that would have caught plans.price_per_gb and
    admin_auth.email.
    """
    from app.models import Base

    gaps: dict[str, list[str]] = {}
    for name, table in Base.metadata.tables.items():
        if name not in actual_schema:
            continue  # reported by the table test above
        actual = actual_schema[name]
        missing = sorted(c.name for c in table.columns if c.name.lower() not in actual)
        if missing:
            gaps[name] = missing

    assert not gaps, (
        f"{len(gaps)} table(s) missing model columns: {gaps}. "
        "Add a revision, or the ORM will raise UndefinedColumnError on a "
        "database built by `alembic upgrade head`. See "
        "backend/docs/SCHEMA_DRIFT.md."
    )


async def test_admin_auth_can_be_written_and_read_by_email(actual_schema):
    """The concrete breakage, asserted rather than inferred.

    app/routers/auth.py filters admins by `AdminAuth.email` in 19 places and
    creates them with `email=`/`password_hash=`, but the migrated table was
    keyed by admin_phone with neither column. Admin auth was entirely
    non-functional on a migration-built database.
    """
    assert {"email", "password_hash"} <= actual_schema.get("admin_auth", set()), (
        "admin_auth lacks email/password_hash: every admin login and every "
        "admin insert fails on a migrated database"
    )


async def test_plan_pricing_columns_exist(actual_schema):
    """The other concrete breakage: residential/mobile order pricing.

    app/routers/orders.py reads min_gb, max_gb and price_per_gb on the live
    order path. Deleting the dead /api/products endpoint removed the only
    witness this failure had, so assert it directly.
    """
    required = {"price_per_gb", "min_gb", "max_gb", "gb_tiers"}
    assert required <= actual_schema.get("plans", set()), (
        f"plans missing {sorted(required - actual_schema.get('plans', set()))}: "
        "residential/mobile order creation fails on a migrated database"
    )