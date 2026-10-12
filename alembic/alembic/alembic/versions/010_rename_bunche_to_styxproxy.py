"""Rename BuncheCredential → StyxproxyCredential

Revision ID: 010_rename_bunche_to_styxproxy
Revises: 009_widen_admin_audit_admin_phone
Create Date: 2026-07-22

Renames the proxy credential storage to match the Styxproxy brand:
  - table:        bunche_credentials        → styxproxy_credentials
  - column:       bun_username              → styxproxy_username
  - column:       bun_password              → styxproxy_password

The literal proxy username prefix (formerly "bun_") is changed to "sty_"
in the Python helper at the same time. Existing rows are preserved with
their old prefix — those credentials are no longer in active rotation
because dev environment has no production traffic.

No-op-safe: uses IF EXISTS so re-running on an already-renamed DB is fine.
"""
from typing import Sequence, Union

from alembic import op


revision: str = "010_rename_bunche_to_styxproxy"
down_revision: Union[str, None] = "009_audit_phone_widen"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Rename table.
    op.execute("ALTER TABLE IF EXISTS bunche_credentials RENAME TO styxproxy_credentials")

    # Rename columns inside the renamed table. (Plain ALTER … RENAME COLUMN
    # works whether the source table already uses the new name or not, as
    # long as the old column is still present.)
    op.execute("ALTER TABLE IF EXISTS styxproxy_credentials RENAME COLUMN bun_username TO styxproxy_username")
    op.execute("ALTER TABLE IF EXISTS styxproxy_credentials RENAME COLUMN bun_password TO styxproxy_password")


def downgrade() -> None:
    op.execute("ALTER TABLE IF EXISTS styxproxy_credentials RENAME COLUMN styxproxy_username TO bun_username")
    op.execute("ALTER TABLE IF EXISTS styxproxy_credentials RENAME COLUMN styxproxy_password TO bun_password")
    op.execute("ALTER TABLE IF EXISTS styxproxy_credentials RENAME TO bunche_credentials")
