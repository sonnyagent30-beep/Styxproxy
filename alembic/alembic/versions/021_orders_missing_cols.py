"""Add missing columns to orders table (idempotent).

Revision ID: 021_orders_missing_cols
Revises: 020_plan_settings
Create Date: 2026-08-28

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

revision = '021_orders_missing_cols'
down_revision = '020_plan_settings'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Use raw SQL with IF NOT EXISTS for idempotency
    columns = [
        ('platform_account_id', 'UUID'),
        ('customer_phone', 'VARCHAR(20)'),
        ('plan_type', 'VARCHAR(20)'),
        ('plan_code', 'VARCHAR(50)'),
        ('country', 'VARCHAR(10)'),
        ('quantity', 'INTEGER'),
        ('amount_paid_ngn', 'NUMERIC(12, 2)'),
        ('payment_reference', 'VARCHAR(100)'),
        ('tx_ref', 'VARCHAR(100)'),
        ('provider', 'VARCHAR(50)'),
        ('provider_order_id', 'VARCHAR(100)'),
        ('styxproxy_credential_id', 'INTEGER'),
        ('status', 'VARCHAR(50) DEFAULT 'pending''),
        ('ip_tested', 'BOOLEAN DEFAULT false'),
        ('ip_test_result', 'VARCHAR(10)'),
        ('data_total_gb', 'NUMERIC(10, 2)'),
        ('data_remaining_gb', 'NUMERIC(10, 2)'),
        ('data_expires', 'TIMESTAMP WITH TIME ZONE'),
        ('expires_at', 'TIMESTAMP WITH TIME ZONE'),
        ('ban_reported', 'BOOLEAN DEFAULT false'),
        ('screenshot_url', 'TEXT'),
        ('ban_verified', 'VARCHAR(50)'),
        ('replacement_count', 'INTEGER DEFAULT 0'),
        ('refund_requested', 'BOOLEAN DEFAULT false'),
        ('refund_reason', 'TEXT'),
        ('notes', 'TEXT'),
        ('created_at', 'TIMESTAMP WITH TIME ZONE DEFAULT now()'),
        ('fulfilled_at', 'TIMESTAMP WITH TIME ZONE'),
        ('cost_usd', 'NUMERIC(10, 4)'),
        ('rotation_mode', 'VARCHAR(20)'),
        ('city_id', 'INTEGER'),
        ('city_name', 'VARCHAR(100)'),
        ('referral_tx_ref', 'VARCHAR(100)'),
        ('emails_sent', 'INTEGER DEFAULT 0'),
        ('reminder_sent_at', 'TIMESTAMP WITH TIME ZONE'),
    ]
    
    for col_name, col_type in columns:
        op.execute(f"ALTER TABLE orders ADD COLUMN IF NOT EXISTS {col_name} {col_type}")


def downgrade() -> None:
    # Remove all added columns
    columns = [
        'reminder_sent_at', 'emails_sent', 'referral_tx_ref', 'city_name', 'city_id',
        'rotation_mode', 'cost_usd', 'fulfilled_at', 'created_at', 'notes',
        'refund_reason', 'refund_requested', 'replacement_count', 'ban_verified',
        'screenshot_url', 'ban_reported', 'expires_at', 'data_expires',
        'data_remaining_gb', 'data_total_gb', 'ip_test_result', 'ip_tested',
        'status', 'styxproxy_credential_id', 'provider_order_id', 'provider',
        'tx_ref', 'payment_reference', 'amount_paid_ngn', 'quantity', 'country',
        'plan_code', 'plan_type', 'customer_phone', 'platform_account_id',
    ]
    for col_name in columns:
        op.execute(f"ALTER TABLE orders DROP COLUMN IF EXISTS {col_name}")
