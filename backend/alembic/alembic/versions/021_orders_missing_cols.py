"""Add missing columns to orders table.

Revision ID: 021_orders_missing_cols
Revises: 020_plan_settings
Create Date: 2026-08-28

"""
from alembic import op
import sqlalchemy as sa

revision = '021_orders_missing_cols'
down_revision = '020_plan_settings'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add all missing columns to orders table
    op.add_column('orders', sa.Column('platform_account_id', sa.UUID(), nullable=True))
    op.add_column('orders', sa.Column('customer_phone', sa.String(20), nullable=True))
    op.add_column('orders', sa.Column('plan_type', sa.String(20), nullable=True))
    op.add_column('orders', sa.Column('plan_code', sa.String(50), nullable=True))
    op.add_column('orders', sa.Column('country', sa.String(10), nullable=True))
    op.add_column('orders', sa.Column('quantity', sa.Integer(), nullable=True))
    op.add_column('orders', sa.Column('amount_paid_ngn', sa.Numeric(12, 2), nullable=True))
    op.add_column('orders', sa.Column('payment_reference', sa.String(100), nullable=True))
    op.add_column('orders', sa.Column('tx_ref', sa.String(100), nullable=True))
    op.add_column('orders', sa.Column('provider', sa.String(50), nullable=True))
    op.add_column('orders', sa.Column('provider_order_id', sa.String(100), nullable=True))
    op.add_column('orders', sa.Column('styxproxy_credential_id', sa.Integer(), nullable=True))
    op.add_column('orders', sa.Column('status', sa.String(50), server_default='pending', nullable=False))
    op.add_column('orders', sa.Column('ip_tested', sa.Boolean(), server_default='false', nullable=False))
    op.add_column('orders', sa.Column('ip_test_result', sa.String(10), nullable=True))
    op.add_column('orders', sa.Column('data_total_gb', sa.Numeric(10, 2), nullable=True))
    op.add_column('orders', sa.Column('data_remaining_gb', sa.Numeric(10, 2), nullable=True))
    op.add_column('orders', sa.Column('data_expires', sa.DateTime(timezone=True), nullable=True))
    op.add_column('orders', sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('orders', sa.Column('ban_reported', sa.Boolean(), server_default='false', nullable=False))
    op.add_column('orders', sa.Column('screenshot_url', sa.Text(), nullable=True))
    op.add_column('orders', sa.Column('ban_verified', sa.String(50), nullable=True))
    op.add_column('orders', sa.Column('replacement_count', sa.Integer(), server_default='0', nullable=False))
    op.add_column('orders', sa.Column('refund_requested', sa.Boolean(), server_default='false', nullable=False))
    op.add_column('orders', sa.Column('refund_reason', sa.Text(), nullable=True))
    op.add_column('orders', sa.Column('notes', sa.Text(), nullable=True))
    op.add_column('orders', sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False))
    op.add_column('orders', sa.Column('fulfilled_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('orders', sa.Column('cost_usd', sa.Numeric(10, 4), nullable=True))
    op.add_column('orders', sa.Column('rotation_mode', sa.String(20), nullable=True))
    op.add_column('orders', sa.Column('city_id', sa.Integer(), nullable=True))
    op.add_column('orders', sa.Column('city_name', sa.String(100), nullable=True))
    op.add_column('orders', sa.Column('referral_tx_ref', sa.String(100), nullable=True))
    op.add_column('orders', sa.Column('emails_sent', sa.Integer(), server_default='0', nullable=False))
    op.add_column('orders', sa.Column('reminder_sent_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    # Remove all added columns
    op.drop_column('orders', 'reminder_sent_at')
    op.drop_column('orders', 'emails_sent')
    op.drop_column('orders', 'referral_tx_ref')
    op.drop_column('orders', 'city_name')
    op.drop_column('orders', 'city_id')
    op.drop_column('orders', 'rotation_mode')
    op.drop_column('orders', 'cost_usd')
    op.drop_column('orders', 'fulfilled_at')
    op.drop_column('orders', 'created_at')
    op.drop_column('orders', 'notes')
    op.drop_column('orders', 'refund_reason')
    op.drop_column('orders', 'refund_requested')
    op.drop_column('orders', 'replacement_count')
    op.drop_column('orders', 'ban_verified')
    op.drop_column('orders', 'screenshot_url')
    op.drop_column('orders', 'ban_reported')
    op.drop_column('orders', 'expires_at')
    op.drop_column('orders', 'data_expires')
    op.drop_column('orders', 'data_remaining_gb')
    op.drop_column('orders', 'data_total_gb')
    op.drop_column('orders', 'ip_test_result')
    op.drop_column('orders', 'ip_tested')
    op.drop_column('orders', 'status')
    op.drop_column('orders', 'styxproxy_credential_id')
    op.drop_column('orders', 'provider_order_id')
    op.drop_column('orders', 'provider')
    op.drop_column('orders', 'tx_ref')
    op.drop_column('orders', 'payment_reference')
    op.drop_column('orders', 'amount_paid_ngn')
    op.drop_column('orders', 'quantity')
    op.drop_column('orders', 'country')
    op.drop_column('orders', 'plan_code')
    op.drop_column('orders', 'plan_type')
    op.drop_column('orders', 'customer_phone')
    op.drop_column('orders', 'platform_account_id')
