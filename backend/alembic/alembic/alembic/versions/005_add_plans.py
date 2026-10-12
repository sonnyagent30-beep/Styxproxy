"""Add plans table.

Revision ID: 005_add_plans
Revises: 004_add_posts
Create Date: 2026-07-15
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers
revision: str = '005_add_plans'
down_revision: Union[str, None] = '004_add_posts'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create plans table
    op.create_table(
        'plans',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('plan_code', sa.String(50), nullable=False),
        sa.Column('plan_type', sa.String(20), nullable=False),
        sa.Column('country', sa.String(10), nullable=False),
        sa.Column('price_ngn', sa.Numeric(12, 2), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False, default=1),
        sa.Column('duration_days', sa.Integer(), nullable=False, default=30),
        sa.Column('features', sa.JSON(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('sort_order', sa.Integer(), nullable=False, default=0),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('plan_code'),
    )
    op.create_index('idx_plans_code', 'plans', ['plan_code'], unique=True)
    op.create_index('idx_plans_type_country', 'plans', ['plan_type', 'country'])
    op.create_index('idx_plans_active', 'plans', ['is_active'])
    
    # Insert default plans (matching the old hardcoded products)
    op.execute("""
        INSERT INTO plans (plan_code, plan_type, country, price_ngn, quantity, duration_days, features, is_active, sort_order)
        VALUES 
            ('ISP-NG-1', 'ISP', 'NG', 5000, 1, 30, '{"features": ["High speed", "Nigeria IPs", "Unlimited bandwidth"]}', true, 1),
            ('ISP-NG-2', 'ISP', 'NG', 9500, 2, 30, '{"features": ["High speed", "Nigeria IPs", "Unlimited bandwidth"]}', true, 2),
            ('DC-NG-1', 'DC', 'NG', 8000, 1, 30, '{"features": ["Dedicated IP", "Nigeria IPs", "Static IP"]}', true, 3),
            ('RESIDENTIAL-UK-1', 'RESIDENTIAL', 'UK', 12000, 1, 30, '{"features": ["Residential IPs", "UK IPs", "High anonymity"]}', true, 4),
            ('RESIDENTIAL-US-1', 'RESIDENTIAL', 'US', 10000, 1, 30, '{"features": ["Residential IPs", "US IPs", "High anonymity"]}', true, 5),
            ('MOBILE-DE-1', 'MOBILE', 'DE', 15000, 1, 30, '{"features": ["Mobile IPs", "Germany IPs", "4G/5G"]}', true, 6),
            ('MOBILE-JP-1', 'MOBILE', 'JP', 18000, 1, 30, '{"features": ["Mobile IPs", "Japan IPs", "4G/5G"]}', true, 7)
    """)


def downgrade() -> None:
    op.drop_index('idx_plans_active', table_name='plans')
    op.drop_index('idx_plans_type_country', table_name='plans')
    op.drop_index('idx_plans_code', table_name='plans')
    op.drop_table('plans')
