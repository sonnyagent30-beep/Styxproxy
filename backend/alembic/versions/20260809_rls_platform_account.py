"""Add real RLS policies for orders and styxproxy_credentials.

The existing policies have qual=true (everything passes) — this replaces them
with actual platform_account_id filtering.

Before: RLS was effectively a no-op.
After:  customers only see their own orders/credentials at the DB level.
"""

from alembic import op
import sqlalchemy as sa

revision = "rls_platform_account_v1"
down_revision = "013_health_snapshots"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    # ── 1. Ensure RLS is enforced for the app user ───────────────────────────
    # Without this, RLS is advisory-only for the owning role.
    conn.execute(sa.text("ALTER TABLE orders FORCE ROW LEVEL SECURITY"))
    conn.execute(sa.text("ALTER TABLE styxproxy_credentials FORCE ROW LEVEL SECURITY"))

    # ── 2. Drop permissive policies (qual=true lets everything through) ───────
    permissive_orders = [
        "orders_app_bypass",
        "orders_all",
        "orders_admin_all",
    ]
    permissive_creds = [
        "styxproxy_credentials_app_bypass",
        "styxproxy_credentials_all",
        "styxproxy_credentials_admin_all",
    ]

    for pol in permissive_orders:
        conn.execute(sa.text(f'DROP POLICY IF EXISTS "{pol}" ON orders'))

    for pol in permissive_creds:
        conn.execute(sa.text(f'DROP POLICY IF EXISTS "{pol}" ON styxproxy_credentials'))

    # ── 3. Create real per-account policies ───────────────────────────────────

    # orders — SELECT: only own orders
    conn.execute(sa.text("""
        CREATE POLICY orders_select_own
            ON orders FOR SELECT
            USING (platform_account_id::text = current_setting('app.current_platform_account_id', true))
    """))

    # orders — INSERT: must belong to own account
    conn.execute(sa.text("""
        CREATE POLICY orders_insert_own
            ON orders FOR INSERT
            WITH CHECK (platform_account_id::text = current_setting('app.current_platform_account_id', true))
    """))

    # orders — UPDATE: only own orders
    conn.execute(sa.text("""
        CREATE POLICY orders_update_own
            ON orders FOR UPDATE
            USING (platform_account_id::text = current_setting('app.current_platform_account_id', true))
            WITH CHECK (platform_account_id::text = current_setting('app.current_platform_account_id', true))
    """))

    # orders — DELETE: only own orders
    conn.execute(sa.text("""
        CREATE POLICY orders_delete_own
            ON orders FOR DELETE
            USING (platform_account_id::text = current_setting('app.current_platform_account_id', true))
    """))

    # styxproxy_credentials — SELECT: join through order
    conn.execute(sa.text("""
        CREATE POLICY creds_select_own
            ON styxproxy_credentials FOR SELECT
            USING (
                EXISTS (
                    SELECT 1 FROM orders
                    WHERE orders.id = styxproxy_credentials.order_id
                    AND orders.platform_account_id::text = current_setting('app.current_platform_account_id', true)
                )
            )
    """))

    # styxproxy_credentials — UPDATE/DELETE: via order join
    conn.execute(sa.text("""
        CREATE POLICY creds_update_own
            ON styxproxy_credentials FOR UPDATE
            USING (
                EXISTS (
                    SELECT 1 FROM orders
                    WHERE orders.id = styxproxy_credentials.order_id
                    AND orders.platform_account_id::text = current_setting('app.current_platform_account_id', true)
                )
            )
            WITH CHECK (
                EXISTS (
                    SELECT 1 FROM orders
                    WHERE orders.id = styxproxy_credentials.order_id
                    AND orders.platform_account_id::text = current_setting('app.current_platform_account_id', true)
                )
            )
    """))

    conn.execute(sa.text("""
        CREATE POLICY creds_delete_own
            ON styxproxy_credentials FOR DELETE
            USING (
                EXISTS (
                    SELECT 1 FROM orders
                    WHERE orders.id = styxproxy_credentials.order_id
                    AND orders.platform_account_id::text = current_setting('app.current_platform_account_id', true)
                )
            )
    """))

    # ── 4. Index for performance ─────────────────────────────────────────────
    # platform_account_id already indexed but ensure it
    conn.execute(sa.text("""
        CREATE INDEX IF NOT EXISTS orders_platform_account_id_idx
            ON orders (platform_account_id)
    """))


def downgrade() -> None:
    """Drop RLS policies and restore permissive ones (dangerous — do not use in prod)."""
    conn = op.get_bind()

    # Drop RLS policies
    for pol in ["orders_select_own", "orders_insert_own", "orders_update_own", "orders_delete_own"]:
        conn.execute(sa.text(f'DROP POLICY IF EXISTS "{pol}" ON orders'))
    for pol in ["creds_select_own", "creds_update_own", "creds_delete_own"]:
        conn.execute(sa.text(f'DROP POLICY IF EXISTS "{pol}" ON styxproxy_credentials'))

    # Restore permissive policies (use ONLY if you understand the security implication)
    conn.execute(sa.text('ALTER TABLE orders NO FORCE ROW LEVEL SECURITY'))
    conn.execute(sa.text('ALTER TABLE styxproxy_credentials NO FORCE ROW LEVEL SECURITY'))
