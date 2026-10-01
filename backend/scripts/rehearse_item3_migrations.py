"""Rehearse gate item 3's migration against a live PostgreSQL (QA's blocker scenario).

QA reproduced the blocker by applying item 2's ADD COLUMN IF NOT EXISTS and then
item 3's bare op.add_column for the same name, getting:

    ERROR: column "gateway_refund_id" of relation "..." already exists

This script proves the reworked migration does NOT do that: it applies item 2's
migration, then item 3's, then both again (idempotency), checks the column set,
downgrades both in order, and removes the scratch schema.

SAFETY: everything happens inside a dedicated schema (`item3_rehearsal`) that is
created and dropped by this script. It never touches a pre-existing `orders`
table, so it is safe to point at a database that has real data.

Run:  python3 scripts/rehearse_item3_migrations.py
Requires: ITEM3_REHEARSAL_URL — a PG URL with CREATE SCHEMA rights. The schema
name can be overridden with ITEM3_REHEARSAL_SCHEMA.
"""

from __future__ import annotations

import importlib.util
import os
import pathlib
import sys
import types

VERSIONS = pathlib.Path(__file__).resolve().parents[1] / "alembic" / "versions"

ITEM2 = "20261001_order_capture_columns"
ITEM3 = "20261001_refund_gateway_evidence"

SCHEMA = os.environ.get("ITEM3_REHEARSAL_SCHEMA", "item3_rehearsal")


def _load(revision: str):
    path = VERSIONS / f"{revision}.py"
    if not path.is_file():
        raise FileNotFoundError(f"migration file missing: {path}")
    spec = importlib.util.spec_from_file_location(revision, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    url = os.environ.get("ITEM3_REHEARSAL_URL")
    if not url:
        print("SKIP: ITEM3_REHEARSAL_URL not set")
        return 0

    import sqlalchemy as sa
    from alembic.migration import MigrationContext
    from alembic.operations import Operations

    engine = sa.create_engine(url)
    failures: list[str] = []

    with engine.begin() as conn:
        # Isolated schema. DROP SCHEMA ... CASCADE removes anything left over
        # from a previous aborted run; it can only ever touch our own schema.
        conn.execute(sa.text(f'DROP SCHEMA IF EXISTS "{SCHEMA}" CASCADE'))
        conn.execute(sa.text(f'CREATE SCHEMA "{SCHEMA}"'))
        conn.execute(sa.text(f'SET search_path TO "{SCHEMA}"'))
        conn.execute(sa.text("CREATE TABLE orders (id serial primary key)"))

        ops = Operations(MigrationContext.configure(conn))
        shim = types.SimpleNamespace(execute=lambda sql: ops.execute(sql))

        def columns() -> list[str]:
            return [
                r[0]
                for r in conn.execute(
                    sa.text(
                        "select column_name from information_schema.columns "
                        f"where table_schema='{SCHEMA}' and table_name='orders' order by 1"
                    )
                )
            ]

        item2 = _load(ITEM2)
        item2.__dict__["op"] = shim
        item2.upgrade()
        print(f"OK   {ITEM2} applied")

        item3 = _load(ITEM3)
        item3.__dict__["op"] = shim
        try:
            item3.upgrade()
            print(f"OK   {ITEM3} applied — no duplicate-column error")
        except Exception as e:  # the exact blocker QA hit
            failures.append(f"{ITEM3} upgrade failed: {e}")

        # Idempotency: app/main.py's lifespan re-runs these ALTERs on every boot.
        try:
            item2.upgrade()
            item3.upgrade()
            print("OK   both migrations re-ran cleanly (idempotent)")
        except Exception as e:
            failures.append(f"re-run failed: {e}")

        cols = columns()
        present = [c for c in cols if "refund" in c or c.startswith("gateway_") or c == "captured_at"]
        print(f"     columns after upgrade: {present}")

        for required in (
            "gateway_refund_id",
            "gateway_refund_status",
            "gateway_refund_amount",
            "gateway_refunded_at",
        ):
            if required not in cols:
                failures.append(f"missing column after upgrade: {required}")

        try:
            item3.downgrade()
            print(f"OK   {ITEM3} downgraded")
        except Exception as e:
            failures.append(f"{ITEM3} downgrade failed: {e}")

        after = columns()
        for dropped in ("gateway_refund_status", "gateway_refund_amount", "gateway_refunded_at"):
            if dropped in after:
                failures.append(f"item 3 downgrade left {dropped} behind")
        if "gateway_refund_id" not in after:
            failures.append("item 3 downgrade dropped gateway_refund_id, which item 2 owns")
        else:
            print("OK   item 3 downgrade left item 2's gateway_refund_id intact")

        try:
            item2.downgrade()
            print(f"OK   {ITEM2} downgraded")
        except Exception as e:
            failures.append(f"{ITEM2} downgrade failed: {e}")

        conn.execute(sa.text(f'DROP SCHEMA IF EXISTS "{SCHEMA}" CASCADE'))
        print(f"OK   scratch schema {SCHEMA} dropped")

    if failures:
        print("\nFAILED:")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("\nALL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
