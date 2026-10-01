"""Fail-closed ORM-vs-database schema drift detection.

Why this module exists
----------------------
On 2026-10-01 a deploy shipped `app/models.py` declaring six `orders`
columns (`captured_at`, `gateway_status`, ...) while production's
database did not have them. Every query touching `orders` then raised
`asyncpg.exceptions.UndefinedColumnError`, and `/api/v1/health` returned
**200 throughout**, because that endpoint only runs `SELECT 1`.

The startup `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` loop was supposed
to paper over exactly this. It never ran successfully once: the app
connects as `styxproxy_app`, which is not the owner of `orders` (that is
`styxproxy_migrate`), so Postgres rejected the first ALTER with
`InsufficientPrivilegeError: must be owner of table orders`. The
surrounding `except` only logged a *warning*, so a permanently failing
migration was indistinguishable in the logs from a successful one.

Three rules this module is built on, each learned the hard way:

1. **Verify with a REAL query, never a probe.** `SELECT 1` says the socket
   works. It says nothing about whether the ORM's columns exist. And a
   *narrow* select is not enough either: `select(TrialSession.id)` returned
   200-equivalent OK while `select(TrialSession)` raised, because only the
   full-model select projects every declared column. So we select whole
   models.

2. **Fail closed.** Undetermined counts as drift. A guard that reports
   "healthy" because it could not reach the database is worse than no
   guard at all — it manufactures confidence.

3. **Report what is missing, not just that something is.** "schema drift
   detected" sends the next person hunting. The remedy is either a
   migration or the startup DDL; naming the exact `table.column` turns a
   mystery into a one-line fix.

Note on privileges: this module READS only (information_schema + SELECT).
The app role cannot and should not be able to ALTER tables it does not
own. Applying schema is the migration path's job (see
`docs/PRODUCTION_MIGRATIONS.md`); this module's job is to make the
disagreement impossible to miss.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from app.models import Base

# Columns whose absence is expected on a healthy database.
# alembic_version is owned by styxproxy_app itself and is never declared
# in Base.metadata, so it needs no allowlisting -- this set exists for
# operational overrides where a column is deliberately not deployed.
EXPECTED_ABSENT_COLUMNS: frozenset[str] = frozenset()


@dataclass
class SchemaDrift:
    """The result of a schema check. `ok` is the only field callers should trust."""

    ok: bool
    missing_tables: list[str] = field(default_factory=list)
    missing_columns: list[str] = field(default_factory=list)
    broken_models: list[str] = field(default_factory=list)
    models_checked: int = 0
    error: Optional[str] = None

    def summary(self) -> str:
        if self.ok:
            return f"schema OK ({self.models_checked} models verified against live DB)"
        parts = []
        if self.missing_tables:
            parts.append(f"{len(self.missing_tables)} missing table(s): {', '.join(self.missing_tables)}")
        if self.missing_columns:
            parts.append(f"{len(self.missing_columns)} missing column(s): {', '.join(self.missing_columns)}")
        if self.broken_models:
            parts.append(f"{len(self.broken_models)} model(s) raise on a real SELECT: {', '.join(self.broken_models)}")
        if self.error:
            parts.append(f"check could not complete: {self.error}")
        return "SCHEMA DRIFT — " + "; ".join(parts)


async def _fetch_live_columns(conn: AsyncConnection) -> dict[str, set[str]]:
    rows = await conn.execute(
        text(
            "SELECT table_name, column_name "
            "FROM information_schema.columns WHERE table_schema = 'public'"
        )
    )
    live: dict[str, set[str]] = {}
    for table_name, column_name in rows:
        live.setdefault(table_name, set()).add(column_name)
    return live


def diff_metadata(live: dict[str, set[str]]) -> tuple[list[str], list[str]]:
    """Compare Base.metadata against the live schema.

    Returns (missing_tables, missing_columns) where a missing column is
    rendered "table.column" for direct use in an ALTER statement.
    """
    missing_tables: list[str] = []
    missing_columns: list[str] = []
    for table_name, table in sorted(Base.metadata.tables.items()):
        if table_name not in live:
            missing_tables.append(table_name)
            continue
        present = live[table_name]
        for column in table.columns:
            if column.name in present:
                continue
            if f"{table_name}.{column.name}" in EXPECTED_ABSENT_COLUMNS:
                continue
            missing_columns.append(f"{table_name}.{column.name}")
    return missing_tables, missing_columns


async def check_schema(conn: AsyncConnection, *, verify_queries: bool = True) -> SchemaDrift:
    """Check the live database against the ORM. Never raises; never guesses.

    Args:
        conn: an open AsyncConnection using the application's own role —
            the privileges of the serving process are what matter, so the
            check must run as that role and not as a superuser.
        verify_queries: when True, additionally issue a real full-model
            SELECT per mapped class. This is the check that would have
            caught the 2026-10-01 incident; the information_schema diff
            alone can miss column-level problems that only surface in a
            projection (and vice versa), so run both.
    """
    try:
        live = await _fetch_live_columns(conn)
    except Exception as exc:  # noqa: BLE001 - fail closed, report, never raise
        return SchemaDrift(ok=False, error=f"could not read schema: {type(exc).__name__}: {exc}")

    missing_tables, missing_columns = diff_metadata(live)

    broken_models: list[str] = []
    checked = 0
    if verify_queries:
        from sqlalchemy import select

        for mapper in sorted(Base.registry.mappers, key=lambda m: m.class_.__name__):
            model = mapper.class_
            if model.__tablename__ not in Base.metadata.tables:
                continue
            if model.__tablename__ in missing_tables:
                # Already reported; querying it would only duplicate noise.
                broken_models.append(model.__name__)
                continue
            checked += 1
            try:
                # Full-model select on purpose: it projects every declared
                # column, which a select(Model.id) would not.
                #
                # The SAVEPOINT is load-bearing. In Postgres a failed statement
                # poisons the enclosing transaction ("current transaction is
                # aborted"), so without one rollback-to per model, the FIRST
                # genuine drift would make every subsequent model report
                # InFailedSQLTransactionError. Measured on production
                # 2026-10-01: 14 real missing columns produced 39 "broken"
                # models, of which 38 were pure cascade. A gate that cries wolf
                # gets ignored, so each probe must be independently isolatable.
                async with conn.begin_nested():
                    await conn.execute(select(model).limit(1))
            except Exception as exc:  # noqa: BLE001 - record and keep going
                broken_models.append(f"{model.__name__} ({type(exc).__name__})")
                # The savepoint already rolled back; the outer transaction is
                # usable again, so the next model gets a clean slate.

    return SchemaDrift(
        ok=not (missing_tables or missing_columns or broken_models),
        missing_tables=missing_tables,
        missing_columns=missing_columns,
        broken_models=broken_models,
        models_checked=checked,
    )