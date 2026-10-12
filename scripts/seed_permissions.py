"""Seed the admin_permissions family (Theme C).

Populates:
  - admin_permissions: ~50 permission codes covering all admin capabilities
  - admin_role_permissions: defaults matching the existing 3-role system
      (superadmin = all, admin = most, viewer = read-only)

Idempotent: ON CONFLICT (code) / ON CONFLICT (role, permission_code) DO UPDATE.

Run once after migration 016:
  /opt/styxproxy/backend/venv/bin/python3 /opt/styxproxy/backend/scripts/seed_permissions.py

The seed list is the authoritative source of truth — update here, then
re-run the script to push to live.
"""

import asyncio
import os
import sys

sys.path.insert(0, "/opt/styxproxy/backend")

_env_path = "/opt/styxproxy/.env"
if os.path.exists(_env_path):
    with open(_env_path) as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _v = _line.split("=", 1)
                os.environ.setdefault(_k.strip(), _v.strip())

from sqlalchemy import select  # noqa: E402
from sqlalchemy.dialects.postgresql import insert as pg_insert  # noqa: E402

from app.database import async_session  # noqa: E402
from app.models import AdminPermission, AdminRolePermission  # noqa: E402

# (code, category, description, is_sensitive)
PERMISSIONS = [
    # AUTH
    ("admin.auth.invite.create", "auth", "Create new admin invite codes", True),
    ("admin.auth.invite.list", "auth", "List all admin invites", False),
    ("admin.auth.invite.delete", "auth", "Delete admin invite codes", True),
    ("admin.auth.password.change", "auth", "Change own admin password", False),
    ("admin.auth.password.reset_request", "auth", "Request password reset for any admin", True),
    ("admin.auth.totp.change", "auth", "Enable/disable own TOTP", False),
    ("admin.auth.lock_admin", "auth", "Lock or unlock other admin accounts", True),
    ("admin.auth.role.update", "auth", "Change another admin's role", True),
    ("admin.auth.team.list", "auth", "View admin team list", False),
    # FEATURE FLAGS
    ("admin.feature_flags.create", "feature_flags", "Create new feature flags", True),
    ("admin.feature_flags.list", "feature_flags", "List all feature flags", False),
    ("admin.feature_flags.read", "feature_flags", "Read feature flag by name", False),
    ("admin.feature_flags.update", "feature_flags", "Enable/disable/update feature flags", True),
    ("admin.feature_flags.delete", "feature_flags", "Delete feature flags", True),
    # CUSTOMER / SALES
    ("admin.customers.list", "customers", "View customer list and details", False),
    ("admin.customers.support.respond", "customers", "Respond to support threads", False),
    ("admin.customers.escalations.handle", "customers", "Resolve Charon escalations", False),
    ("admin.customers.trials.list", "customers", "View free trial history", False),
    # ORDERS
    ("admin.orders.list", "orders", "List all orders", False),
    ("admin.orders.refund", "orders", "Issue refunds for orders", True),
    ("admin.orders.re_fulfill", "orders", "Re-fulfill credentials for an order", True),
    # CONTENT
    ("admin.content.posts.create", "content", "Create blog posts", False),
    ("admin.content.posts.update", "content", "Update blog posts", False),
    ("admin.content.posts.delete", "content", "Delete blog posts", True),
    ("admin.content.posts.publish", "content", "Publish/unpublish blog posts", False),
    ("admin.content.chunks.backfill", "content", "Re-chunk blog posts for Charon KB", True),
    # MONITORING (§14)
    ("admin.monitor.health.read", "monitoring", "View system health dashboard", False),
    ("admin.monitor.metrics.read", "monitoring", "View business metrics", False),
    ("admin.monitor.logs.read", "monitoring", "View error and audit logs", False),
    ("admin.monitor.db.read", "monitoring", "View DB connection pool + slow queries", False),
    ("admin.monitor.cache.read", "monitoring", "View Redis cache stats", False),
    ("admin.monitor.webhooks.read", "monitoring", "View webhook delivery stats", False),
    ("admin.monitor.providers.read", "monitoring", "View provider availability", False),
    ("admin.monitor.self_test.run", "monitoring", "Run the pipeline self-test", True),
    # BILLING
    ("admin.billing.transactions.list", "billing", "View payment transactions", False),
    ("admin.billing.balance.adjust", "billing", "Adjust customer credit balances", True),
    ("admin.billing.webhooks.replay", "billing", "Replay a webhook delivery", True),
    # SAFETY / KILL SWITCH
    ("admin.safety.kill_switch.engage", "safety", "Disable checkout endpoint via kill switch", True),
    ("admin.safety.maintenance.toggle", "safety", "Toggle maintenance mode", True),
    ("admin.safety.feature_flag.create", "safety", "Create the checkout_disabled feature flag", True),
    # INTEGRATIONS
    ("admin.integrations.sentry.test", "integrations", "Send a Sentry test event", False),
    ("admin.integrations.twilio.test", "integrations", "Send a test WhatsApp/SMS message", True),
    ("admin.integrations.stripe.test", "integrations", "Verify Stripe credentials", True),
    ("admin.integrations.paypal.test", "integrations", "Verify PayPal credentials", True),
    # PERMISSIONS
    ("admin.permissions.list", "permissions", "View permission catalog", False),
    ("admin.permissions.grant", "permissions", "Grant or revoke permissions", True),
    ("admin.permissions.approve_request", "permissions", "Approve permission change requests", True),
    ("admin.permissions.create_request", "permissions", "File a permission change request", False),
    # SYSTEM
    ("admin.system.backup.read", "system", "View backup status", False),
    ("admin.system.backup.run", "system", "Trigger a backup run", True),
    ("admin.system.maintenance.read", "system", "View maintenance state", False),
    ("admin.system.audit_log.read", "system", "View admin audit log", False),
    ("admin.system.secrets.read", "system", "View secrets vault (masked values)", True),
    ("admin.system.secrets.write", "system", "Write or delete secrets in vault", True),
    ("admin.system.secrets.restart", "system", "Restart backend API from vault", True),
]


# Role defaults: superadmin gets ALL, admin gets most, viewer gets read-only
# Following the existing RoleChecker in app/routers/auth.py:
#   require_superadmin: only 'superadmin'
#   require_admin: 'admin', 'superadmin'
#   require_viewer: 'admin', 'superadmin', 'viewer'
SUPERADMIN_GRANTS = [(code, True) for (code, *_) in PERMISSIONS]
# admin = all except safety/admin operations
ADMIN_DENY = {
    "admin.auth.invite.create",  # superadmin only per current code
    "admin.auth.invite.delete",
    "admin.auth.password.reset_request",
    "admin.auth.lock_admin",
    "admin.auth.role.update",
    "admin.feature_flags.create",
    "admin.feature_flags.delete",
    "admin.orders.refund",
    "admin.orders.re_fulfill",
    "admin.content.posts.delete",
    "admin.content.chunks.backfill",
    "admin.monitor.self_test.run",
    "admin.billing.balance.adjust",
    "admin.billing.webhooks.replay",
    "admin.safety.kill_switch.engage",
    "admin.safety.maintenance.toggle",
    "admin.safety.feature_flag.create",
    "admin.integrations.twilio.test",
    "admin.integrations.stripe.test",
    "admin.integrations.paypal.test",
    "admin.permissions.grant",
    "admin.permissions.approve_request",
    "admin.system.backup.run",
}
ADMIN_GRANTS = [(code, code not in ADMIN_DENY) for (code, *_) in PERMISSIONS]
# viewer = read-only + audit
VIEWER_DENY = set(ADMIN_DENY) | {
    "admin.feature_flags.update",
    "admin.customers.support.respond",
    "admin.customers.escalations.handle",
    "admin.content.posts.create",
    "admin.content.posts.update",
    "admin.content.posts.publish",
    "admin.permissions.create_request",
    "admin.auth.password.change",
    "admin.auth.totp.change",
}
VIEWER_GRANTS = [(code, code not in VIEWER_DENY) for (code, *_) in PERMISSIONS]


async def main() -> int:
    async with async_session() as session:
        # 1. Seed permissions catalog
        for code, category, description, is_sensitive in PERMISSIONS:
            stmt = (
                pg_insert(AdminPermission)
                .values(
                    code=code,
                    category=category,
                    description=description,
                    is_sensitive=is_sensitive,
                )
                .on_conflict_do_update(
                    index_elements=["code"],
                    set_={
                        "category": category,
                        "description": description,
                        "is_sensitive": is_sensitive,
                    },
                )
            )
            await session.execute(stmt)

        # 2. Seed role defaults
        for role, grants in (
            ("superadmin", SUPERADMIN_GRANTS),
            ("admin", ADMIN_GRANTS),
            ("viewer", VIEWER_GRANTS),
        ):
            for code, granted in grants:
                stmt = (
                    pg_insert(AdminRolePermission)
                    .values(
                        role=role,
                        permission_code=code,
                        granted=granted,
                    )
                    .on_conflict_do_update(
                        index_elements=["role", "permission_code"],
                        set_={
                            "granted": granted,
                        },
                    )
                )
                await session.execute(stmt)

        await session.commit()

        # Verify
        catalog_count = (await session.execute(select(AdminPermission))).scalars().all()
        role_count = (await session.execute(select(AdminRolePermission))).scalars().all()
        print(f"Seeded {len(catalog_count)} permission codes")
        print(f"Seeded {len(role_count)} role-permission grants (3 roles x {len(catalog_count)} codes each)")
        print()
        for role in ("superadmin", "admin", "viewer"):
            role_codes = [r for r in role_count if r.role == role and r.granted]
            print(f"  {role}: {len(role_codes)}/{len(catalog_count)} permissions granted")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
