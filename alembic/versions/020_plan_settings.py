"""Add plan_settings table.

Revision ID: 020_plan_settings
Revises: 019_trial_consent
Create Date: 2026-08-05

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '020_plan_settings'
down_revision = '019_trial_consent'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'plan_settings',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('plan_type', sa.String(20), nullable=True),
        sa.Column('country', sa.String(10), nullable=True),
        sa.Column('setting_key', sa.String(50), nullable=False),
        sa.Column('setting_value', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('priority', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('valid_from', sa.DateTime(timezone=True), nullable=True),
        sa.Column('valid_until', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_plan_settings_type_country', 'plan_settings', ['plan_type', 'country'])
    op.create_index('idx_plan_settings_active', 'plan_settings', ['is_active'])


def downgrade() -> None:
    op.drop_index('idx_plan_settings_active', table_name='plan_settings')
    op.drop_index('idx_plan_settings_type_country', table_name='plan_settings')
    op.drop_table('plan_settings')
