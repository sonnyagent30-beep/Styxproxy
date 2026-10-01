"""Report the gap between `alembic upgrade head` and `app/models.py`.

Prints every model table the migrated database does not have, and every column
the model declares that the database lacks. Used to size the schema drift
documented in backend/docs/SCHEMA_DRIFT.md (card t_2af95a6b).

Run this against a database built purely by `alembic upgrade head`:

    cd backend
    DATABASE_URL=postgresql+asyncpg://... python scripts/schema_drift_report.py

Read-only: it issues a single SELECT against information_schema.
"""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

os.environ.setdefault("TESTING", "1")
for _var in (
    "JWT_SECRET",
    "ADMIN_TOKEN",
    "FLUTTERWAVE_WEBHOOK_SECRET",
    "MINIMAX_API_KEY",
    "THEOREM_REACH_WEBHOOK_SECRET",
    "OPS_JWT_SECRET",
):
    os.environ.setdefault(_var, "x")

from sqlalchemy import text  # noqa: E402

from app.database import engine  # noqa: E402
from app.models import Base  # noqa: E402


async def report() -> int:
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

    db_tables: dict[str, set[str]] = {}
    for table, column in rows:
        db_tables.setdefault(table, set()).add(column)

    missing_tables: list[str] = []
    missing_columns: dict[str, list[str]] = {}

    # sorted_tables warns on the orders <-> styxproxy_credentials FK cycle; the
    # order does not matter for a set-difference report.
    for table in Base.metadata.tables.values():
        if table.name not in db_tables:
            missing_tables.append(table.name)
            continue
        gap = sorted({c.name for c in table.columns} - db_tables[table.name])
        if gap:
            missing_columns[table.name] = gap

    print(f"MISSING TABLES ({len(missing_tables)}):")
    for name in sorted(missing_tables):
        print(f"  - {name}")

    print(f"\nTABLES WITH MISSING COLUMNS ({len(missing_columns)}):")
    for name in sorted(missing_columns):
        print(f"  - {name}: {missing_columns[name]}")

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(report()))
