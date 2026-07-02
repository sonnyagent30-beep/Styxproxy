"""Initial migration — create all 10 tables.

Revision ID: 001_initial
Revises:
Create Date: 2026-07-02 00:00:00.000000
"""
from typing import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '001_initial'
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # customers
    op.create_table(
        'customers',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('phone', sa.String(20), unique=True, nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('recovery_method', sa.String(10), nullable=True),
        sa.Column('pin_hash', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('blocked', sa.Boolean, default=False, nullable=False),
        sa.Column('blocked_reason', sa.Text, nullable=True),
        sa.Column('free_trials_used_today', sa.Integer, default=0, nullable=False),
        sa.Column('free_trial_offer_sent_today', sa.Boolean, default=False, nullable=False),
        sa.Column('free_trial_offer_sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('free_trial_declined_today', sa.Boolean, default=False, nullable=False),
        sa.Column('total_orders', sa.Integer, default=0, nullable=False),
        sa.Column('lifetime_value_ngn', sa.Numeric(12, 2), default=0, nullable=False),
        sa.Column('last_active_subscription', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_message_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_order_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('replacement_count', sa.Integer, default=0, nullable=False),
        sa.Column('consent_given', sa.Boolean, default=False, nullable=False),
        sa.Column('consent_version', sa.String(20), nullable=True),
        sa.Column('consent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('support_notes', sa.Text, nullable=True),
    )

    # platform_accounts
    op.create_table(
        'platform_accounts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('customer_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('customers.id'), nullable=True),
        sa.Column('platform', sa.String(50), nullable=False),
        sa.Column('platform_user_id', sa.String(100), nullable=False),
        sa.Column('extra_data', postgresql.JSON, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column('is_primary', sa.Boolean, default=False, nullable=False),
        sa.UniqueConstraint('platform', 'platform_user_id', name='uq_platform_user'),
    )

    # merge_requests
    op.create_table(
        'merge_requests',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('source_account_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('platform_accounts.id'), nullable=False),
        sa.Column('target_account_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('platform_accounts.id'), nullable=False),
        sa.Column('status', sa.String(20), default='pending', nullable=False),
        sa.Column('requested_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('customers.id'), nullable=True),
        sa.Column('approved_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('customers.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    )

    # orders
    op.create_table(
        'orders',
        sa.Column('order_id', sa.String(20), primary_key=True),
        sa.Column('platform_account_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('platform_accounts.id'), nullable=True),
        sa.Column('customer_phone', sa.String(20), sa.ForeignKey('customers.phone'), nullable=True),
        sa.Column('plan_type', sa.String(20), nullable=True),
        sa.Column('plan_code', sa.String(50), nullable=True),
        sa.Column('country', sa.String(10), nullable=True),
        sa.Column('quantity', sa.Integer, nullable=True),
        sa.Column('amount_paid_ngn', sa.Numeric(12, 2), nullable=True),
        sa.Column('payment_reference', sa.String(100), nullable=True),
        sa.Column('provider', sa.String(50), nullable=True),
        sa.Column('provider_order_id', sa.String(100), nullable=True),
        sa.Column('bunche_credential_id', sa.Integer, sa.ForeignKey('bunche_credentials.id'), nullable=True),
        sa.Column('status', sa.String(50), default='pending', nullable=False),
        sa.Column('ip_tested', sa.Boolean, default=False, nullable=False),
        sa.Column('ip_test_result', sa.String(10), nullable=True),
        sa.Column('data_total_gb', sa.Numeric(10, 2), nullable=True),
        sa.Column('data_remaining_gb', sa.Numeric(10, 2), nullable=True),
        sa.Column('data_expires', sa.DateTime(timezone=True), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('ban_reported', sa.Boolean, default=False, nullable=False),
        sa.Column('screenshot_url', sa.Text, nullable=True),
        sa.Column('ban_verified', sa.String(50), nullable=True),
        sa.Column('replacement_count', sa.Integer, default=0, nullable=False),
        sa.Column('refund_requested', sa.Boolean, default=False, nullable=False),
        sa.Column('refund_reason', sa.Text, nullable=True),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('fulfilled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('cost_usd', sa.Numeric(10, 4), nullable=True),
    )
    op.create_index('idx_orders_customer', 'orders', ['customer_phone'])
    op.create_index('idx_orders_status', 'orders', ['status'])
    op.create_index('idx_orders_expires', 'orders', ['expires_at'])
    op.create_index('idx_orders_created', 'orders', ['created_at'])

    # bunche_credentials
    op.create_table(
        'bunche_credentials',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('bun_username', sa.String(50), unique=True, nullable=False),
        sa.Column('password_hash', sa.Text, nullable=False),
        sa.Column('customer_phone', sa.String(20), sa.ForeignKey('customers.phone'), nullable=True),
        sa.Column('order_id', sa.String(20), sa.ForeignKey('orders.order_id'), nullable=True),
        sa.Column('pool_type', sa.String(20), default='paid', nullable=False),
        sa.Column('provider_name', sa.String(50), nullable=True),
        sa.Column('provider_order_id', sa.String(100), nullable=True),
        sa.Column('provider_username', sa.String(100), nullable=True),
        sa.Column('provider_password', sa.String(100), nullable=True),
        sa.Column('upstream_proxy_ip', postgresql.INET, nullable=True),
        sa.Column('upstream_proxy_port', sa.Integer, default=1080, nullable=False),
        sa.Column('dante_port', sa.Integer, nullable=True),
        sa.Column('status', sa.String(20), default='active', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('revoke_reason', sa.String(50), nullable=True),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('gb_used', sa.Numeric(10, 2), default=0, nullable=False),
    )
    op.create_index('idx_bunche_cred_username', 'bunche_credentials', ['bun_username'])
    op.create_index('idx_bunche_cred_customer', 'bunche_credentials', ['customer_phone'])
    op.create_index('idx_bunche_cred_status', 'bunche_credentials', ['status'])
    op.create_index('idx_bunche_cred_pool', 'bunche_credentials', ['pool_type'])
    op.create_index('idx_bunche_cred_expires', 'bunche_credentials', ['expires_at'])

    # free_trials
    op.create_table(
        'free_trials',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('phone', sa.String(20), sa.ForeignKey('customers.phone'), nullable=True),
        sa.Column('trial_date', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('survey_id', sa.String(50), nullable=True),
        sa.Column('reward_usd', sa.Numeric(10, 4), nullable=True),
        sa.Column('bunche_credential_id', sa.Integer, sa.ForeignKey('bunche_credentials.id'), nullable=True),
        sa.Column('status', sa.String(20), nullable=True),
        sa.Column('disclaimer_accepted', sa.Boolean, default=False, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('idx_free_trials_phone_date', 'free_trials', ['phone', 'trial_date'])
    op.create_index('idx_free_trials_status', 'free_trials', ['status'])

    # pending_trial_surveys
    op.create_table(
        'pending_trial_surveys',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('free_trial_id', sa.Integer, sa.ForeignKey('free_trials.id'), nullable=True),
        sa.Column('customer_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('customers.id'), nullable=True),
        sa.Column('survey_token', sa.String(100), unique=True, nullable=False),
        sa.Column('questions', postgresql.JSON, nullable=True),
        sa.Column('responses', postgresql.JSON, nullable=True),
        sa.Column('status', sa.String(20), default='pending', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    )

    # customer_audit_log
    op.create_table(
        'customer_audit_log',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('request_id', sa.String(50), nullable=True),
        sa.Column('customer_hash', sa.String(20), nullable=True),
        sa.Column('event_type', sa.String(50), nullable=True),
        sa.Column('order_id', sa.String(20), nullable=True),
        sa.Column('workflow', sa.String(50), nullable=True),
        sa.Column('status', sa.String(20), nullable=True),
        sa.Column('details', postgresql.JSON, nullable=True),
    )
    op.create_index('idx_audit_timestamp', 'customer_audit_log', ['timestamp'])
    op.create_index('idx_audit_customer', 'customer_audit_log', ['customer_hash'])
    op.create_index('idx_audit_event', 'customer_audit_log', ['event_type'])

    # processed_webhooks
    op.create_table(
        'processed_webhooks',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('webhook_id', sa.String(100), unique=True, nullable=False),
        sa.Column('provider', sa.String(20), nullable=True),
        sa.Column('event_type', sa.String(50), nullable=True),
        sa.Column('processed_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('response_sent', sa.Boolean, default=False, nullable=False),
        sa.Column('extra_data', postgresql.JSON, nullable=True),
    )
    op.create_index('idx_processed_webhooks_id', 'processed_webhooks', ['webhook_id'])

    # admin_auth
    op.create_table(
        'admin_auth',
        sa.Column('admin_phone', sa.String(20), primary_key=True),
        sa.Column('pin_hash', sa.Text, nullable=True),
        sa.Column('pin_set_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('totp_secret', sa.Text, nullable=True),
        sa.Column('totp_enabled', sa.Boolean, default=False, nullable=False),
        sa.Column('totp_set_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('failed_attempts', sa.Integer, default=0, nullable=False),
        sa.Column('locked_until', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('last_used', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('idx_admin_auth_locked', 'admin_auth', ['locked_until'])


def downgrade() -> None:
    op.drop_table('admin_auth')
    op.drop_table('processed_webhooks')
    op.drop_table('customer_audit_log')
    op.drop_table('pending_trial_surveys')
    op.drop_table('free_trials')
    op.drop_index('idx_bunche_cred_expires', table_name='bunche_credentials')
    op.drop_index('idx_bunche_cred_pool', table_name='bunche_credentials')
    op.drop_index('idx_bunche_cred_status', table_name='bunche_credentials')
    op.drop_index('idx_bunche_cred_customer', table_name='bunche_credentials')
    op.drop_index('idx_bunche_cred_username', table_name='bunche_credentials')
    op.drop_table('bunche_credentials')
    op.drop_index('idx_orders_created', table_name='orders')
    op.drop_index('idx_orders_expires', table_name='orders')
    op.drop_index('idx_orders_status', table_name='orders')
    op.drop_index('idx_orders_customer', table_name='orders')
    op.drop_table('orders')
    op.drop_table('merge_requests')
    op.drop_table('platform_accounts')
    op.drop_table('customers')
