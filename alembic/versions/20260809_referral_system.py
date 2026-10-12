"""Add referral system columns + abuse prevention.

Adds: customers.referral_credit_ngn, customers.referred_by, customers.name
Adds: orders.referred_by_phone, orders.referral_name_used,
      orders.referral_credit_earned_ngn, orders.referral_credit_used_ngn
Adds: referral_abuse_events table for tracking self-referrals, velocity breaches, clawbacks
"""

from alembic import op
import sqlalchemy as sa

revision = "referral_system_v1"
down_revision = "013_health_snapshots"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    # ── customers table ───────────────────────────────────────────────────────
    conn.execute(sa.text("""
        ALTER TABLE customers
        ADD COLUMN IF NOT EXISTS name VARCHAR(30) UNIQUE,
        ADD COLUMN IF NOT EXISTS referral_credit_ngn DECIMAL(12,2) NOT NULL DEFAULT 0,
        ADD COLUMN IF NOT EXISTS referred_by VARCHAR(20),
        ADD COLUMN IF NOT EXISTS referral_count_monthly INT NOT NULL DEFAULT 0,
        ADD COLUMN IF NOT EXISTS referral_count_total INT NOT NULL DEFAULT 0,
        ADD COLUMN IF NOT EXISTS referral_credit_revoked_ngn DECIMAL(12,2) NOT NULL DEFAULT 0;
    """))

    conn.execute(sa.text("""
        COMMENT ON COLUMN customers.name IS 'Referral code — customer chosen name';
        COMMENT ON COLUMN customers.referral_credit_ngn IS 'Earned referral credit (NGN)';
        COMMENT ON COLUMN customers.referred_by IS 'Phone of person who referred this customer';
        COMMENT ON COLUMN customers.referral_count_monthly IS 'Referrals credited this calendar month';
        COMMENT ON COLUMN customers.referral_count_total IS 'Total referrals credited ever';
        COMMENT ON COLUMN customers.referral_credit_revoked_ngn IS 'Credit revoked due to refund clawback';
    """))

    # ── orders table ────────────────────────────────────────────────────────────
    conn.execute(sa.text("""
        ALTER TABLE orders
        ADD COLUMN IF NOT EXISTS referred_by_phone VARCHAR(20),
        ADD COLUMN IF NOT EXISTS referral_name_used VARCHAR(30),
        ADD COLUMN IF NOT EXISTS referral_credit_earned_ngn DECIMAL(12,2) NOT NULL DEFAULT 0,
        ADD COLUMN IF NOT EXISTS referral_credit_used_ngn DECIMAL(12,2) NOT NULL DEFAULT 0,
        ADD COLUMN IF NOT EXISTS referral_abuse_flagged BOOLEAN NOT NULL DEFAULT FALSE,
        ADD COLUMN IF NOT EXISTS referral_abuse_reason VARCHAR(50);
    """))

    # ── referral_abuse_events table ─────────────────────────────────────────────
    conn.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS referral_abuse_events (
            id SERIAL PRIMARY KEY,
            referred_customer_phone VARCHAR(20) NOT NULL,
            referrer_phone VARCHAR(20),
            abuse_type VARCHAR(30) NOT NULL,
            -- abuse_type: self_referral | velocity_breach | refund_clawback | duplicate_referral
            order_id VARCHAR(50),
            credit_amount_ngn DECIMAL(12,2),
            revoked BOOLEAN NOT NULL DEFAULT FALSE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
    """))

    conn.execute(sa.text("""
        COMMENT ON TABLE referral_abuse_events IS
            'Audit log for referral abuse: self-referrals, velocity breaches, refund clawbacks';
        COMMENT ON COLUMN referral_abuse_events.abuse_type IS
            'self_referral | velocity_breach | refund_clawback | duplicate_referral';
    """))

    # ── Indexes ────────────────────────────────────────────────────────────────
    conn.execute(sa.text(
        "CREATE INDEX IF NOT EXISTS idx_customers_name ON customers (name)"
    ))
    conn.execute(sa.text(
        "CREATE INDEX IF NOT EXISTS idx_orders_referred_by_phone ON orders (referred_by_phone)"
    ))
    conn.execute(sa.text(
        "CREATE INDEX IF NOT EXISTS idx_abuse_events_phone ON referral_abuse_events (referred_customer_phone)"
    ))
    conn.execute(sa.text(
        "CREATE INDEX IF NOT EXISTS idx_abuse_events_type ON referral_abuse_events (abuse_type)"
    ))


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text(
        "DROP TABLE IF EXISTS referral_abuse_events"
    ))
    for col in [
        "referral_abuse_reason", "referral_abuse_flagged",
        "referral_credit_used_ngn", "referral_credit_earned_ngn",
        "referral_name_used", "referred_by_phone",
    ]:
        conn.execute(sa.text(f"ALTER TABLE orders DROP COLUMN IF EXISTS {col}"))
    for col in [
        "referral_credit_revoked_ngn", "referral_count_total",
        "referral_count_monthly", "referred_by",
        "referral_credit_ngn", "name",
    ]:
        conn.execute(sa.text(f"ALTER TABLE customers DROP COLUMN IF EXISTS {col}"))
