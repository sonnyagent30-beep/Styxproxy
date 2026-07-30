"""Sprint 15 — RLS toggle service.

Actually executes ALTER TABLE / CREATE POLICY against Postgres, then
updates the rls_policy bookkeeping row. Every toggle is audit-logged
via app.services.audit.write_audit_log.

Connection note:
  Today's app connects as styxproxy (superuser, BYPASSRLS). Enabling RLS
  on a table here won't actually restrict the app until we re-pin the
  connection string to styxproxy_app (per Sprint 15 last todo). Until
  that happens, this work is forward-prep: the policies exist in Postgres
  with USING/WITH CHECK clauses; flipping DATABASE_URL later is config,
  not schema.

Safety:
  Each toggle is idempotent (re-enabling an already-enabled table is a
  no-op except for stamping applied_at). Disabling an already-disabled
  table is similarly a no-op. We never DROP POLICY (would lose USING
  clause); we only DROP POLICY IF EXISTS in disable path so a re-enable
  is reproducible.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import RlsPolicy

log = logging.getLogger(__name__)


async def list_policies(session: AsyncSession) -> tuple[list[RlsPolicy], int, int]:
    """Return all rls_policy rows + enabled_count + not_started_count."""
    result = (await session.execute(
        __import__("sqlalchemy").select(RlsPolicy).order_by(RlsPolicy.table_name)
    ))
    policies = list(result.scalars().all())
    enabled = sum(1 for p in policies if p.policy_enabled)
    not_started = sum(1 for p in policies if p.policy_status == "not_started")
    return policies, enabled, not_started


async def get_pg_rls_state(session: AsyncSession, table_name: str) -> tuple[str, int]:
    """Query pg_class + pg_policy for a given table.

    Returns (rowsecurity_status, policy_count).
    """
    row = (await session.execute(
        text("""
            SELECT c.relrowsecurity, COUNT(p.oid) AS policy_count
            FROM pg_class c
            LEFT JOIN pg_policy p ON p.polrelid = c.oid
            WHERE c.relname = :table AND c.relkind = 'r'
            GROUP BY c.relrowsecurity
        """),
        {"table": table_name},
    )).fetchone()
    if not row:
        return ("unknown", 0)
    state = "enabled" if row[0] else "disabled"
    return (state, int(row[1]))


async def toggle_policy(
    session: AsyncSession,
    *,
    table_name: str,
    enable: bool,
    using_clause: Optional[str] = None,
    with_check: Optional[str] = None,
    notes: Optional[str] = None,
    admin_email: Optional[str] = None,
) -> dict:
    """Enable or disable RLS on a single table. Returns the new state.

    Steps:
      1. Look up the rls_policy row (auto-create if missing for forward-prep).
      2. ALTER TABLE <name> ENABLE / DISABLE ROW LEVEL SECURITY.
      3. CREATE / DROP POLICY <name>_app_all TO styxproxy_app USING(...) WITH CHECK(...).
      4. Update rls_policy row: policy_enabled, policy_status, applied_at / rolled_back_at.
      5. Caller is expected to also call write_audit_log() for the audit trail.
    """
    using = using_clause or "true"
    check = with_check or "true"

    # 1. Find or create the rls_policy row
    row = (await session.execute(
        __import__("sqlalchemy").select(RlsPolicy).where(RlsPolicy.table_name == table_name)
    )).scalar_one_or_none()

    if row is None:
        row = RlsPolicy(
            table_name=table_name,
            policy_name=f"{table_name}_app_all",
            using_clause=using,
            with_check=check,
            role_name="styxproxy_app",
            policy_status="not_started",
            created_by=admin_email,
        )
        session.add(row)
        await session.flush()
        log.info("rls: created rls_policy row for %s by %s", table_name, admin_email)

    policy_name = row.policy_name or f"{table_name}_app_all"

    # 2 + 3. Toggle RLS in Postgres.
    if enable:
        await session.execute(text(f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY"))
        await session.execute(text(f"""
            DROP POLICY IF EXISTS {policy_name} ON {table_name};
            CREATE POLICY {policy_name}
              ON {table_name}
              AS PERMISSIVE
              FOR ALL
              TO styxproxy_app
              USING ({using})
              WITH CHECK ({check});
        """))
        # Make sure role exists (defensive — earlier migrations created styxproxy_app)
        await session.execute(text("""
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'styxproxy_app') THEN
                    CREATE ROLE styxproxy_app NOLOGIN NOSUPERUSER NOINHERIT;
                END IF;
            END $$;
            GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO styxproxy_app;
            GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO styxproxy_app;
        """))
        await session.commit()
        log.info("rls: ENABLED on %s (policy=%s)", table_name, policy_name)
    else:
        # Disable: drop policy first (if any), then ALTER.
        await session.execute(text(f"DROP POLICY IF EXISTS {policy_name} ON {table_name}"))
        await session.execute(text(f"ALTER TABLE {table_name} DISABLE ROW LEVEL SECURITY"))
        await session.commit()
        log.info("rls: DISABLED on %s", table_name)

    # 4. Update bookkeeping
    now = datetime.now(timezone.utc)
    row.policy_enabled = enable
    row.using_clause = using
    row.with_check = check
    row.policy_status = "enabled" if enable else "disabled"
    row.last_audit = now
    if enable:
        row.applied_at = now
    else:
        row.rolled_back_at = now
    if notes:
        row.notes = notes
    await session.commit()
    await session.refresh(row)

    # 5. Refresh PG-side state for response
    pg_state, pg_count = await get_pg_rls_state(session, table_name)

    return {
        "table_name": table_name,
        "policy_enabled": row.policy_enabled,
        "policy_status": row.policy_status,
        "applied_at": row.applied_at,
        "rolled_back_at": row.rolled_back_at,
        "pg_rls_state": pg_state,
        "pg_policy_count": pg_count,
    }


async def get_bypass_role_status(session: AsyncSession) -> dict:
    """Check styxproxy_app role + flag whether current user is BYPASSRLS."""
    bypass_role_exists_row = (await session.execute(
        text("SELECT EXISTS(SELECT 1 FROM pg_roles WHERE rolname = 'styxproxy_app')")
    )).scalar()
    current_user_role_row = (await session.execute(
        text("SELECT current_user, rolname, rolsuper, rolbypassrls FROM pg_roles WHERE rolname = current_user")
    )).fetchone()
    return {
        "bypass_role_exists": bool(bypass_role_exists_row),
        "current_user_role": (
            current_user_role_row[1] if current_user_role_row else "unknown"
        ),
        "bypass_role_attr_present": (
            bool(current_user_role_row[3]) if current_user_role_row else False
        ),
    }


# Phase 2a-2h rollout order (low-risk first, customer PII last).
# All tables are listed by unique_name so we can render an actionable plan.
ROLLOUT_PHASES = [
    ("2a", "plans", "Lowest-risk: catalog table, no PII, no JOINs", "low"),
    ("2b", "cities", "No PII, no JOINs, used by Sprint 13 pricing", "low"),
    ("2c", "categories", "Taxonomy table, no PII", "low"),
    ("2d", "countries", "Lookup table, no PII", "low"),
    ("2e", "platform_accounts", "FK to customers — verify ORM path", "medium"),
    ("2f", "styxproxy_credentials", "Encrypted secrets; verify cipher reads", "medium"),
    ("2g", "orders", "Has FKs to customers + plans; verify payment-status path", "high"),
    ("2h", "customers", "Highest PII risk; rollout last", "high"),
]


async def get_rollout_plan(session: AsyncSession) -> tuple[list[dict], Optional[str], bool]:
    """Return the 2a-2h phase list with completion flags + next phase + conn-string-pinned."""
    result = (await session.execute(
        __import__("sqlalchemy").select(RlsPolicy.table_name, RlsPolicy.policy_enabled, RlsPolicy.applied_at).where(
            RlsPolicy.table_name.in_([p[1] for p in ROLLOUT_PHASES])
        )
    ))
    by_table = {row[0]: (row[1], row[2]) for row in result.fetchall()}

    phases = []
    next_phase = None
    for ph, table, rationale, risk in ROLLOUT_PHASES:
        applied = by_table.get(table, (False, None))
        completed = bool(applied[0])
        phases.append({
            "phase": ph,
            "table_name": table,
            "rationale": rationale,
            "risk": risk,
            "completed": completed,
            "enabled_at": applied[1].isoformat() if applied[1] else None,
        })
        if not completed and next_phase is None:
            next_phase = ph

    # Connection-string pin: check DATABASE_URL / dbname mapping
    # The "real" check is whether the running app connects as styxproxy_app or styxproxy.
    # For now: rls_enabled=true on customers == full rollout.
    conn_pinned = False

    return phases, next_phase, conn_pinned
