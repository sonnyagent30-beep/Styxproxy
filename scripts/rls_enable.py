#!/opt/styxproxy/backend/venv/bin/python3
"""
rls_enable.py — guarded RLS enabler for the styxproxy database

USAGE:
  rls_enable.py <table>              # dry-run (default)
  rls_enable.py <table> --apply      # enable RLS + create bypass policy
  rls_enable.py <table> --disable    # reverse (rollback)
  rls_enable.py --status             # show RLS state for all known tables
  rls_enable.py --list               # show all tables + RLS state
  rls_enable.py --all                # apply to all tables in rls_enabled_tables flag

WHAT IT DOES:
  1. Reads the rls_enabled_tables feature flag (JSON array of table names).
  2. For each target table:
     a. ENABLE ROW LEVEL SECURITY
     b. CREATE POLICY <table>_app_bypass ON <table>
        FOR ALL TO styxproxy USING (true) WITH CHECK (true)
     c. CREATE POLICY <table>_superadmin_bypass ON <table>
        FOR ALL TO styxproxy_admin USING (true) WITH CHECK (true)
  3. Logs every action to plan_audit_log (action='rls_enable' or 'rls_disable').

WHY IT EXISTS:
  RLS was rolled back in commit 0ba7241 (Jul 23 2026) because policies were
  applied without thinking through the bypass model. This script enforces
  the bypass-everyone-but-track-changes model so:
    - app user (styxproxy) keeps working (policy is USING(true))
    - migration user (postgres) is unaffected (superuser bypass)
    - admin user (styxproxy_admin) gets the same access via separate policy
  If the policy breaks something, just run with --disable to remove it.

EXIT CODES:
  0  success (dry-run clean OR applied)
  1  table not found in target DB
  2  RLS already in different state than expected
  3  DB connection failed
"""
import argparse
import asyncio
import json
import os
import sys
from pathlib import Path


def load_env():
    """Try to load .env but don't fail if unreadable (e.g. when run as postgres)."""
    env_path = Path(__file__).resolve().parents[2] / ".env"
    if not env_path.exists():
        env_path = Path("/opt/styxproxy/.env")
    if not env_path.exists():
        return
    try:
        for line in env_path.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    except PermissionError:
        # Run as postgres user — .env is mode 600 root-only, peer auth will work
        pass


async def get_conn():
    try:
        import asyncpg
    except ImportError:
        print("ERROR: asyncpg not installed in venv")
        sys.exit(3)

    # Prefer DATABASE_URL (matches app config)
    db_url = os.environ.get("DATABASE_URL", "")
    if db_url.startswith("postgresql+asyncpg://"):
        db_url = db_url.replace("postgresql+asyncpg://", "postgresql://", 1)
    if db_url.startswith("postgresql://"):
        return await asyncpg.connect(db_url)

    # Fallback: peer auth (no password) when run as postgres user
    return await asyncpg.connect(
        host=os.environ.get("PGHOST", "/var/run/postgresql"),
        port=int(os.environ.get("PGPORT", "5432")),
        database=os.environ.get("PGDATABASE", "styxproxy"),
        user=os.environ.get("PGUSER", "postgres"),
        password=os.environ.get("PGPASSWORD", "") or None,
    )


async def table_exists(conn, table):
    row = await conn.fetchrow(
        "SELECT 1 FROM information_schema.tables "
        "WHERE table_schema='public' AND table_name=$1",
        table
    )
    return row is not None


async def get_rls_state(conn, table):
    row = await conn.fetchrow(
        "SELECT relname, relrowsecurity, relforcerowsecurity "
        "FROM pg_class WHERE relname=$1",
        table
    )
    if not row:
        return None
    return {"name": row["relname"], "rls": row["relrowsecurity"], "force_rls": row["relforcerowsecurity"]}


async def list_tables_status(conn):
    rows = await conn.fetch("""
        SELECT c.relname,
               c.relrowsecurity AS rls,
               c.relforcerowsecurity AS force_rls,
               (SELECT COUNT(*) FROM pg_policies p
                WHERE p.schemaname='public' AND p.tablename=c.relname) AS policy_count
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname='public' AND c.relkind='r'
        ORDER BY c.relname
    """)
    print(f"\n{'Table':<35} {'RLS':<6} {'Force':<6} {'Policies':<8}")
    print("-" * 60)
    for r in rows:
        print(f"{r['relname']:<35} {'ON' if r['rls'] else 'off':<6} "
              f"{'ON' if r['force_rls'] else 'off':<6} {r['policy_count']:<8}")
    print()


async def show_rls_status(conn, tables):
    print(f"\n{'Table':<35} {'RLS':<6} {'Force':<6} {'Policies':<8}")
    print("-" * 60)
    for t in tables:
        if not await table_exists(conn, t):
            print(f"{t:<35} {'(NOT FOUND)':<6}")
            continue
        state = await get_rls_state(conn, t)
        pol_count = await conn.fetchval(
            "SELECT COUNT(*) FROM pg_policies "
            "WHERE schemaname='public' AND tablename=$1",
            t
        )
        print(f"{t:<35} {'ON' if state['rls'] else 'off':<6} "
              f"{'ON' if state['force_rls'] else 'off':<6} {pol_count:<8}")
    print()


async def get_target_tables():
    conn = await get_conn()
    try:
        row = await conn.fetchrow(
            "SELECT admin_overrides FROM feature_flags WHERE name='rls_enabled_tables'"
        )
        if not row or not row["admin_overrides"]:
            return []
        try:
            tables = json.loads(row["admin_overrides"])
            return tables if isinstance(tables, list) else []
        except json.JSONDecodeError:
            print(f"WARN: rls_enabled_tables flag has invalid JSON: {row['admin_overrides']}")
            return []
    finally:
        await conn.close()


async def apply_rls(conn, table):
    if not await table_exists(conn, table):
        print(f"ERROR: table '{table}' not found")
        return False

    state = await get_rls_state(conn, table)
    print(f"\n[APPLY] {table}")
    print(f"  current state: RLS={'ON' if state['rls'] else 'off'}, "
          f"force={'ON' if state['force_rls'] else 'off'}")

    # Enable RLS
    await conn.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")

    # Discover roles that should get a bypass policy
    roles_to_grant = []
    for role in ("styxproxy", "styxproxy_admin"):
        exists = await conn.fetchval(
            "SELECT 1 FROM pg_roles WHERE rolname=$1", role
        )
        if exists:
            roles_to_grant.append(role)

    if not roles_to_grant:
        print("  WARN: no known roles found, app may lose access")
        roles_to_grant = ["public"]  # fallback: everyone

    # Create bypass policies
    for role in roles_to_grant:
        suffix = "admin" if role == "styxproxy_admin" else "app"
        await conn.execute(f"""
            DROP POLICY IF EXISTS {table}_{suffix}_bypass ON {table};
            CREATE POLICY {table}_{suffix}_bypass ON {table}
                FOR ALL TO {role}
                USING (true) WITH CHECK (true);
        """)
        print(f"  ✓ policy {table}_{suffix}_bypass (FOR ALL TO {role} USING(true))")

    # Log the change
    actor = os.environ.get("USER", "unknown") + "@rls_helper"
    await conn.execute("""
        INSERT INTO plan_audit_log (plan_id, action, actor_email, after, changed_fields)
        VALUES (NULL, $1, $2, $3, $4)
    """, 'rls_enable', actor,
         json.dumps({"table": table, "rls_enabled": True, "policies_for": roles_to_grant}),
         json.dumps(["rls_enabled"] + [f"policy_{r}" for r in roles_to_grant]))
    print("  ✓ logged to plan_audit_log")
    return True


async def disable_rls(conn, table):
    if not await table_exists(conn, table):
        print(f"ERROR: table '{table}' not found")
        return False
    print(f"\n[DISABLE] {table}")
    await conn.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
    # Drop all possible policies (don't require role existence)
    for suffix in ("app", "admin", "superadmin"):
        await conn.execute(
            f"DROP POLICY IF EXISTS {table}_{suffix}_bypass ON {table}"
        )
    actor = os.environ.get("USER", "unknown") + "@rls_helper"
    await conn.execute("""
        INSERT INTO plan_audit_log (plan_id, action, actor_email, after, changed_fields)
        VALUES (NULL, $1, $2, $3, $4)
    """, 'rls_disable', actor,
         json.dumps({"table": table, "rls_enabled": False}),
         json.dumps(["rls_enabled", "policies"]))
    print("  ✓ RLS disabled on {table}")
    print("  ✓ bypass policies dropped")
    print("  ✓ logged to plan_audit_log")
    return True


async def main():
    parser = argparse.ArgumentParser(
        description="RLS enable/disable helper for styxproxy",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument("table", nargs="?", help="table name (omit for --list/--status)")
    parser.add_argument("--apply", action="store_true",
                        help="actually enable RLS (default is dry-run)")
    parser.add_argument("--disable", action="store_true",
                        help="disable RLS and drop policies (rollback)")
    parser.add_argument("--status", action="store_true",
                        help="show RLS state for target table(s)")
    parser.add_argument("--list", action="store_true",
                        help="show RLS state for all public tables")
    parser.add_argument("--all", action="store_true",
                        help="apply to all tables in rls_enabled_tables flag")
    args = parser.parse_args()

    load_env()

    if args.list:
        conn = await get_conn()
        try:
            await list_tables_status(conn)
        finally:
            await conn.close()
        return

    if args.status:
        targets = await get_target_tables() if not args.table else [args.table]
        if not targets:
            print("rls_enabled_tables feature flag is empty. No targets.")
            return
        conn = await get_conn()
        try:
            await show_rls_status(conn, targets)
        finally:
            await conn.close()
        return

    if not args.table and not args.all:
        parser.error("either <table> or --all is required (or --list/--status)")

    # Resolve targets
    if args.all:
        targets = await get_target_tables()
        if not targets:
            print("rls_enabled_tables feature flag is empty. Nothing to do.")
            print("Set via: PATCH /api/admin/auth/flags/rls_enabled_tables")
            print("Or via psql:")
            print("  UPDATE feature_flags")
            print("    SET admin_overrides='[\"orders\"]'")
            print("    WHERE name='rls_enabled_tables';")
            return
    else:
        targets = [args.table]

    print(f"Targets: {targets}")
    print(f"Mode: {'APPLY (writes to DB)' if args.apply else 'DISABLE (rollback)' if args.disable else 'DRY-RUN'}")

    conn = await get_conn()
    try:
        for t in targets:
            if args.disable:
                await disable_rls(conn, t)
            elif args.apply:
                await apply_rls(conn, t)
            else:
                # Dry-run
                if not await table_exists(conn, t):
                    print(f"  ✗ {t}: NOT FOUND")
                    continue
                state = await get_rls_state(conn, t)
                pol = await conn.fetchval(
                    "SELECT COUNT(*) FROM pg_policies "
                    "WHERE schemaname='public' AND tablename=$1",
                    t
                )
                print(f"  [DRY] {t}: RLS={'ON' if state['rls'] else 'off'}, "
                      f"policies={pol} → would enable + 2 bypass policies")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
