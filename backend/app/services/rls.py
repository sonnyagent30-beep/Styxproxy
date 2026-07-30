"""Sprint 15 — RLS toggle service.

Executes ALTER TABLE / CREATE POLICY against Postgres via a separate
engine connected as styxproxy_migrate (the table owner). The app user
(styxproxy) is BYPASSRLS=false and NOT the table owner, so ALTER TABLE
fails in its session.

Bookkeeping (rls_policy row) stays on the app session. The router then
calls write_audit_log() for the audit trail.

Today the app connects as styxproxy, which BYPASSES RLS — so enabling
RLS here only takes effect once DATABASE_URL is re-pinned to
styxproxy_app (Sprint 15 final todo). Until then this forward-preps the
policies in Postgres.

Single-statement SQL only — asyncpg with prepared statements rejects
multi-statement strings.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.models import RlsPolicy

log = logging.getLogger(__name__)


def _read_migrate_password() -> str:
    """Read styxproxy_migrate password from /opt/styxproxy/.env."""
    env_path = Path("/opt/styxproxy/.env")
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if line.startswith("MIGRATE_PASSWORD="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return "styxproxy_migrate_2026"


def get_migrate_engine():
    """Separate engine connected as styxproxy_migrate (table owner)."""
    url = (
        f"postgresql+asyncpg://styxproxy_migrate:{_read_migrate_password()}"
        "@127.0.0.1:5432/styxproxy"
    )
    return create_async_engine(url, echo=False)


async def _ensure_styxproxy_app_role(eng) -> bool:
    """Create styxproxy_app role + grant schema-level read/write if missing.

    Returns True if role existed, False if newly created. Idempotent.
    """
    async with eng.begin() as mconn:
        existed = (await mconn.execute(
            text("SELECT EXISTS(SELECT 1 FROM pg_roles WHERE rolname = :r)"),
            {"r": "styxproxy_app"},
        )).scalar()
        if not existed:
            await mconn.execute(
                text(
                    "CREATE ROLE styxproxy_app NOLOGIN NOSUPERUSER NOINHERIT"
                )
            )
            log.info("rls: created role styxproxy_app")
        # Always re-grant (cheap, idempotent)
        await mconn.execute(
            text(
                "GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES "
                "IN SCHEMA public TO styxproxy_app"
            )
        )
        await mconn.execute(
            text(
                "GRANT USAGE, SELECT ON ALL SEQUENCES "
                "IN SCHEMA public TO styxproxy_app"
            )
        )
        # ALTER DEFAULT PRIVILEGES so future tables inherit
        await mconn.execute(
            text(
                "ALTER DEFAULT PRIVILEGES IN SCHEMA public "
                "GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO styxproxy_app"
            )
        )
        await mconn.execute(
            text(
                "ALTER DEFAULT PRIVILEGES IN SCHEMA public "
                "GRANT USAGE, SELECT ON SEQUENCES TO styxproxy_app"
            )
        )
    return bool(existed)


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
    """Query pg_class + pg_policy for a given table. Returns (state, policy_count)."""
    row = (await session.execute(
        text(
            "SELECT c.relrowsecurity, COUNT(p.oid) AS policy_count "
            "FROM pg_class c LEFT JOIN pg_policy p ON p.polrelid = c.oid "
            "WHERE c.relname = :table AND c.relkind = 'r' "
            "GROUP BY c.relrowsecurity"
        ),
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
    """Enable or disable RLS on a single table. Returns the new state."""
    using = using_clause or "true"
    check = with_check or "true"

    # 1. Find or create the rls_policy row in the app session
    row = (await session.execute(
        __import__("sqlalchemy").select(RlsPolicy).where(
            RlsPolicy.table_name == table_name
        )
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

    # 2 + 3. DDL through the migrate engine (table-owner role).
    # Single-statement per execute — asyncpg rejects multi-stmt prep statements.
    eng = get_migrate_engine()
    try:
        if enable:
            # Ensure styxproxy_app role + grants exist first
            await _ensure_styxproxy_app_role(eng)
            async with eng.begin() as mconn:
                await mconn.execute(
                    text(
                        "ALTER TABLE " + table_name + " ENABLE ROW LEVEL SECURITY"
                    )
                )
                await mconn.execute(
                    text("DROP POLICY IF EXISTS " + policy_name + " ON " + table_name)
                )
                await mconn.execute(
                    text(
                        "CREATE POLICY " + policy_name +
                        " ON " + table_name +
                        " AS PERMISSIVE FOR ALL TO styxproxy_app" +
                        " USING (" + using + ") WITH CHECK (" + check + ")"
                    )
                )
            log.info("rls: ENABLED on %s (policy=%s)", table_name, policy_name)
        else:
            async with eng.begin() as mconn:
                await mconn.execute(
                    text("DROP POLICY IF EXISTS " + policy_name + " ON " + table_name)
                )
                await mconn.execute(
                    text(
                        "ALTER TABLE " + table_name + " DISABLE ROW LEVEL SECURITY"
                    )
                )
            log.info("rls: DISABLED on %s", table_name)
    finally:
        await eng.dispose()

    # 4. Bookkeeping commit on app session
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
        text(
            "SELECT current_user, rolname, rolsuper, rolbypassrls "
            "FROM pg_roles WHERE rolname = current_user"
        )
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
    """Return 2a-2h phase list + next phase + conn-string-pinned."""
    result = (await session.execute(
        __import__("sqlalchemy").select(
            RlsPolicy.table_name, RlsPolicy.policy_enabled, RlsPolicy.applied_at
        ).where(
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

    conn_pinned = False
    return phases, next_phase, conn_pinned
