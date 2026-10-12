#!/usr/bin/env python3
"""Deploy gate: prove the ORM and the live database actually agree.

Run this AFTER restarting the service. An HTTP health probe is not
sufficient and never was: on 2026-10-01 a deploy shipped six `orders`
columns the database did not have, every orders query raised
UndefinedColumnError, and `/api/v1/health` returned 200 the entire time
because that endpoint only runs `SELECT 1`.

Exit codes (fail-closed — undetermined is NOT success):
    0  schema agrees; the deploy is sound
    1  drift detected, or the check could not run
    2  bad usage

Usage:
    python3 scripts/schema_gate.py
    python3 scripts/schema_gate.py --apply-ddl     # opt-in local repair

`--apply-ddl` emits and runs ADD COLUMN IF NOT EXISTS for the missing
columns using the app's own credentials. On production this will FAIL for
tables the app role does not own — that is correct and expected: schema
changes are a migration responsibility, not a serving process's. The
failure is the signal that the supported migration path is needed.
See docs/PRODUCTION_MIGRATIONS.md.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys

# Allow running as `python3 scripts/schema_gate.py` from backend/.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Postgres type names for the repair path. Only used when the app role
# genuinely owns the table (dev/CI); production uses migrations.
_PG_TYPES = {
    "VARCHAR": "VARCHAR",
    "TEXT": "TEXT",
    "INTEGER": "INTEGER",
    "BIGINT": "BIGINT",
    "BOOLEAN": "BOOLEAN",
    "NUMERIC": "NUMERIC",
    "DATETIME": "TIMESTAMP",
    "TIMESTAMP": "TIMESTAMP",
    "UUID": "UUID",
}


def _render_ddl(missing: list[str]) -> list[str]:
    """Render ALTER TABLE statements for missing "table.column" pairs."""
    statements = []
    for item in missing:
        table, _, column = item.partition(".")
        col = Base.metadata.tables[table].columns[column]
        type_name = str(col.type).upper().split("(")[0]
        pg_type = _PG_TYPES.get(type_name)
        if pg_type is None:
            # Safest general-purpose additive type when we cannot map it.
            pg_type = "TEXT"
        suffix = ""
        if getattr(col, "server_default", None) is not None:
            default = getattr(col.server_default, "arg", None)
            text_default = getattr(default, "text", None)
            if isinstance(text_default, str) and text_default and text_default.isidentifier() is False:
                suffix = f" DEFAULT {text_default}"
        statements.append(
            f'ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column} {pg_type}{suffix};'
        )
    return statements


async def _run(args: argparse.Namespace) -> int:
    from sqlalchemy import text

    from app.database import engine
    from app.models import Base
    from app.schema_guard import check_schema

    async with engine.connect() as conn:
        drift = await check_schema(conn, verify_queries=not args.skip_queries)

    if drift.ok:
        print(f"[PASS] {drift.summary()}")
        return 0

    print(f"[FAIL] {drift.summary()}", file=sys.stderr)
    if drift.missing_columns:
        print("\n  Missing columns:", file=sys.stderr)
        for item in drift.missing_columns:
            print(f"    {item}", file=sys.stderr)
    if drift.missing_tables:
        print("\n  Missing tables:", file=sys.stderr)
        for item in drift.missing_tables:
            print(f"    {item}", file=sys.stderr)

    if args.apply_ddl and drift.missing_columns:
        print("\nApplying ADD COLUMN IF NOT EXISTS as the app role...", file=sys.stderr)

        failures = 0
        async with engine.begin() as conn:
            for stmt in _render_ddl(drift.missing_columns):
                try:
                    await conn.execute(text(stmt))
                    print(f"  applied: {stmt}", file=sys.stderr)
                except Exception as exc:  # noqa: BLE001
                    failures += 1
                    print(f"  FAILED:  {stmt}\n           {exc}", file=sys.stderr)
        if failures:
            print(
                f"\n{failures} statement(s) failed. The app role does not own these\n"
                "tables — use the documented migration path (docs/PRODUCTION_MIGRATIONS.md).",
                file=sys.stderr,
            )
            return 1
        print("\nRe-checking after apply...", file=sys.stderr)
        async with engine.connect() as conn:
            drift = await check_schema(conn, verify_queries=not args.skip_queries)
        if drift.ok:
            print(f"[PASS] {drift.summary()}")
            return 0
        print(f"[FAIL] still drifting after apply: {drift.summary()}", file=sys.stderr)
        return 1

    return 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Fail-closed ORM/schema deploy gate")
    parser.add_argument(
        "--skip-queries",
        action="store_true",
        help="metadata diff only (faster, but misses projection-level breakage)",
    )
    parser.add_argument(
        "--apply-ddl",
        action="store_true",
        help="attempt ADD COLUMN IF NOT EXISTS as the app role (dev/CI only)",
    )
    args = parser.parse_args()
    try:
        return asyncio.run(_run(args))
    except Exception as exc:  # noqa: BLE001 - fail closed: could-not-run != pass
        print(f"[FAIL] gate could not run: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())