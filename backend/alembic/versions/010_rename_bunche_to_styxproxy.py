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

    # Rename columns inside the renamed table.
    #
    # 001_initial creates this table with `bun_username` and `password_hash`,
    # NOT `bun_password`. So on a database built purely from this chain the
    # source column is `password_hash`, and the original
    # `RENAME COLUMN bun_password ...` raised
    # UndefinedColumnError and killed `alembic upgrade head`. Production
    # happened to have a hand-applied `bun_password`, which is why it was never
    # seen.
    #
    # Handle both source names so this is correct whether the table came from
    # 001 or from production's out-of-band schema. IF EXISTS on the TABLE does
    # not guard a missing COLUMN, so each rename is gated on the column being
    # present.
    for old, new in (
        ("bun_username", "styxproxy_username"),
        ("bun_password", "styxproxy_password"),
        ("password_hash", "styxproxy_password"),
    ):
        op.execute(
            f"""
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name = 'styxproxy_credentials' AND column_name = '{old}'
                ) THEN
                    EXECUTE 'ALTER TABLE styxproxy_credentials RENAME COLUMN {old} TO {new}';
                END IF;
            END $$;
            """
        )


def downgrade() -> None:
    op.execute("ALTER TABLE IF EXISTS styxproxy_credentials RENAME COLUMN styxproxy_username TO bun_username")
    op.execute("ALTER TABLE IF EXISTS styxproxy_credentials RENAME COLUMN styxproxy_password TO password_hash")
    op.execute("ALTER TABLE IF EXISTS styxproxy_credentials RENAME TO bunche_credentials")
