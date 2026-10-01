"""Add protocol column to bunche_credentials.

Revision ID: 002_add_protocol
Revises: 001_initial
Create Date: 2026-07-02
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "002_add_protocol"
down_revision: Union[str, Sequence[str], None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add protocol column with default value 'socks5'
    op.add_column(
        "bunche_credentials",
        sa.Column("protocol", sa.String(10), nullable=False, server_default="socks5"),
    )
    
    # Add index for faster protocol queries
    op.create_index("idx_bunche_cred_protocol", "bunche_credentials", ["protocol"])


def downgrade() -> None:
    op.drop_index("idx_bunche_cred_protocol", table_name="bunche_credentials")
    op.drop_column("bunche_credentials", "protocol")
