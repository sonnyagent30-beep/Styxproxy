"""Add support_threads and support_messages tables.

Revision ID: 007_add_support_threads
Revises: 006_add_contact_escalations
Create Date: 2026-07-22
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = '007_add_support_threads'
down_revision: Union[str, None] = ('006_add_contact_escalations', '006_add_password_reset_tokens')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'support_threads',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('customer_email', sa.String(255), nullable=False),
        sa.Column('customer_name', sa.String(100), nullable=True),
        sa.Column('subject', sa.String(500), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='open'),
        sa.Column('order_id', sa.String(20), sa.ForeignKey('orders.order_id', ondelete='SET NULL'), nullable=True),
        sa.Column('resend_last_message_id', sa.String(100), nullable=True),
        sa.Column('last_message_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('idx_support_threads_customer_email', 'support_threads', ['customer_email'])
    op.create_index('idx_support_threads_status', 'support_threads', ['status'])
    op.create_index('idx_support_threads_last_message', 'support_threads', ['last_message_at'])

    op.create_table(
        'support_messages',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('thread_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('support_threads.id', ondelete='CASCADE'), nullable=False),
        sa.Column('direction', sa.String(20), nullable=False),
        sa.Column('from_email', sa.String(255), nullable=False),
        sa.Column('to_email', sa.String(255), nullable=False),
        sa.Column('subject', sa.String(500), nullable=False),
        sa.Column('body_text', sa.Text(), nullable=True),
        sa.Column('body_html', sa.Text(), nullable=True),
        sa.Column('resend_id', sa.String(100), nullable=True),
        sa.Column('in_reply_to', sa.String(255), nullable=True),
        sa.Column('references', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('idx_support_messages_thread', 'support_messages', ['thread_id'])
    op.create_index('idx_support_messages_created', 'support_messages', ['created_at'])


def downgrade() -> None:
    op.drop_index('idx_support_messages_created', table_name='support_messages')
    op.drop_index('idx_support_messages_thread', table_name='support_messages')
    op.drop_table('support_messages')
    op.drop_index('idx_support_threads_last_message', table_name='support_threads')
    op.drop_index('idx_support_threads_status', table_name='support_threads')
    op.drop_index('idx_support_threads_customer_email', table_name='support_threads')
    op.drop_table('support_threads')