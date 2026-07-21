"""Add contact_submissions and charon_escalations tables.

Revision ID: 006_add_contact_escalations
Revises: 005_add_plans
Create Date: 2026-07-21
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '006_add_contact_escalations'
down_revision: Union[str, None] = '005_add_plans'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Contact submissions table
    op.create_table(
        'contact_submissions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('email', sa.String(255), nullable=False, index=True),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('phone', sa.String(20), nullable=True),
        sa.Column('tx_ref', sa.String(40), nullable=True, index=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('admin_notes', sa.Text(), nullable=True),
        sa.Column('admin_phone', sa.String(20), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )

    # Charon escalations table
    op.create_table(
        'charon_escalations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('conversation_id', sa.String(100), nullable=False, index=True),
        sa.Column('customer_email', sa.String(255), nullable=True, index=True),
        sa.Column('customer_phone', sa.String(20), nullable=True),
        sa.Column('initial_message', sa.Text(), nullable=False),
        sa.Column('history_summary', sa.Text(), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('admin_notes', sa.Text(), nullable=True),
        sa.Column('admin_phone', sa.String(20), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('charon_escalations')
    op.drop_table('contact_submissions')
