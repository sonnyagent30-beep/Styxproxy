"""Create the 14 model tables no migration ever created (t_e7fbfe21).

## Why this exists

`alembic upgrade head` reached head on a clean Postgres 16 after t_2af95a6b
fixed nine defects in the chain — but reaching head was never the same as
producing the schema the application expects. `app/models.py` is the
authoritative schema (production was grown by hand and by
`Base.metadata.create_all` in app/main.py's lifespan); the chain under
`alembic/versions/` was written largely *after the fact* as a record of that
production, not as a recipe for building it. See backend/docs/SCHEMA_DRIFT.md.

So fourteen tables the ORM queries had never been created by any revision. On a
database built purely by migrations, every one of them raises
`UndefinedColumnError: relation "<name>" does not exist` on first touch:

    admin_webhooks        admin_webhook_logs     categories
    charon_ab_assignments charon_ab_outcomes     cities
    email_unsubscribes    idempotency_responses  plan_cities
    post_categories       referral_credits       refund_approvals
    trigger_events        trigger_weights

## Decision: bring the chain up to the model

The alternative was to declare the chain archival and build clean schemas some
other way. That was rejected: `Base.metadata.create_all` in main.py's lifespan
creates tables but seeds no rows, so it cannot express seed data (countries,
trigger weights, plans), and it cannot be relied on as a schema contract — it
is a side effect of booting the app, so nothing verifies it. `upgrade head` on
a clean database is the thing CI needs, and it should produce a working
schema.

This is Option 1 and it is the smaller surprise: additive DDL on top of a chain
nobody re-runs, touching no production. Production is frozen at
`merge_20260819_three_heads` and is out of scope for this card.

## Idempotency

`CREATE TABLE IF NOT EXISTS` throughout. app/main.py runs
`Base.metadata.create_all` on every boot, so on any deployment where this
migration has not yet run, the table may already exist with a slightly
different shape. Re-running must not explode — it must converge.

Revision ID: 20261001_model_tables_parity
Revises: 20261001_refund_gateway_evidence
Create Date: 2026-10-01 13:40:00.000000
"""

from alembic import op

# revision identifiers
revision = "20261001_model_tables_parity"
down_revision = "20261001_refund_gateway_evidence"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Charon A/B + trigger telemetry ─────────────────────────────────────
    # Keyed by the Charons session_id, so both are sized to match it.
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS charon_ab_assignments (
            id SERIAL PRIMARY KEY,
            session_id VARCHAR(64) NOT NULL UNIQUE,
            variant VARCHAR(1) NOT NULL,
            assigned_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS charon_ab_outcomes (
            id SERIAL PRIMARY KEY,
            session_id VARCHAR(64) NOT NULL,
            variant VARCHAR(1) NOT NULL,
            conversation_id VARCHAR(64),
            outcome VARCHAR(20) NOT NULL,
            concluded_at TIMESTAMP WITH TIME ZONE,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS trigger_events (
            id SERIAL PRIMARY KEY,
            session_id VARCHAR(64) NOT NULL,
            trigger_id VARCHAR(50) NOT NULL,
            fired_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
            outcome VARCHAR(20) NOT NULL,
            charon_msg TEXT,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_trigger_events_session "
        "ON trigger_events (session_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_trigger_events_trigger_fired "
        "ON trigger_events (trigger_id, fired_at)"
    )
    # Rolling per-trigger conversion stats. main.py seeds this table at boot,
    # so a clean database needs it before that code path runs.
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS trigger_weights (
            trigger_id VARCHAR(50) PRIMARY KEY,
            weight NUMERIC(5, 3) NOT NULL,
            total_fires INTEGER NOT NULL,
            total_opens INTEGER NOT NULL,
            total_dismissed INTEGER NOT NULL,
            total_converted INTEGER NOT NULL,
            positive_rate NUMERIC(5, 4) NOT NULL,
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
        )
        """
    )

    # ── Sprint 13 city picker ──────────────────────────────────────────────
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS cities (
            id SERIAL PRIMARY KEY,
            country_code VARCHAR(2) NOT NULL,
            city_name VARCHAR(100) NOT NULL,
            state_code VARCHAR(10),
            isp_name VARCHAR(100),
            latitude NUMERIC(9, 6),
            longitude NUMERIC(9, 6),
            is_active BOOLEAN NOT NULL,
            source VARCHAR(20),
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_cities_country ON cities (country_code)"
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_cities_active ON cities (is_active)")
    # Composite PK: a plan either offers a city or it does not.
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS plan_cities (
            plan_id INTEGER NOT NULL REFERENCES plans(id) ON DELETE CASCADE,
            city_id INTEGER NOT NULL REFERENCES cities(id) ON DELETE CASCADE,
            is_enabled BOOLEAN NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
            PRIMARY KEY (plan_id, city_id)
        )
        """
    )

    # ── Blog categories ────────────────────────────────────────────────────
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS categories (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name VARCHAR(100) NOT NULL,
            slug VARCHAR(100) NOT NULL UNIQUE,
            description TEXT,
            color VARCHAR(7),
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_categories_slug ON categories (slug)"
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS post_categories (
            post_id UUID NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
            category_id UUID NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
            PRIMARY KEY (post_id, category_id)
        )
        """
    )

    # ── Idempotency store for /api/payments/initiate ──────────────────────
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS idempotency_responses (
            key_hash VARCHAR(64) PRIMARY KEY,
            status_code INTEGER,
            response_body TEXT,
            response_headers TEXT,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
            expires_at TIMESTAMP WITH TIME ZONE NOT NULL
        )
        """
    )

    # ── Email suppression ──────────────────────────────────────────────────
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS email_unsubscribes (
            email VARCHAR(255) PRIMARY KEY,
            unsubscribed_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
            source VARCHAR(50) NOT NULL
        )
        """
    )

    # ── Admin webhooks ─────────────────────────────────────────────────────
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS admin_webhooks (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name VARCHAR(100) NOT NULL,
            url VARCHAR(500) NOT NULL,
            events VARCHAR(50)[] NOT NULL,
            secret_hash VARCHAR(255) NOT NULL,
            is_active BOOLEAN NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_admin_webhooks_active "
        "ON admin_webhooks (is_active)"
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS admin_webhook_logs (
            id SERIAL PRIMARY KEY,
            webhook_id UUID NOT NULL REFERENCES admin_webhooks(id),
            event_type VARCHAR(50) NOT NULL,
            payload JSON NOT NULL,
            response_status INTEGER,
            response_body TEXT,
            success BOOLEAN NOT NULL,
            attempts INTEGER NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_admin_webhook_logs_webhook "
        "ON admin_webhook_logs (webhook_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_admin_webhook_logs_created "
        "ON admin_webhook_logs (created_at)"
    )

    # ── Referral credits ───────────────────────────────────────────────────
    # One credit per referee, ever: enforced by the unique constraint below so
    # a replayed webhook cannot mint a second one.
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS referral_credits (
            id SERIAL PRIMARY KEY,
            referrer_customer_id UUID NOT NULL REFERENCES customers(id),
            referee_customer_id UUID NOT NULL REFERENCES customers(id),
            credit_amount_nGN BIGINT NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
            applied_at TIMESTAMP WITH TIME ZONE,
            referee_payment_tx_ref VARCHAR(100),
            CONSTRAINT uq_one_credit_per_referee UNIQUE (referee_customer_id)
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_referral_credits_referrer "
        "ON referral_credits (referrer_customer_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_referral_credits_referee "
        "ON referral_credits (referee_customer_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_referral_credits_applied "
        "ON referral_credits (applied_at)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_referral_credits_referee_payment_tx_ref "
        "ON referral_credits (referee_payment_tx_ref)"
    )

    # ── Refund approvals (human gate before Finance acts) ──────────────────
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS refund_approvals (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            order_id VARCHAR(20) NOT NULL REFERENCES orders(order_id),
            requested_by VARCHAR(255) NOT NULL,
            requested_amount NUMERIC(12, 2) NOT NULL,
            status VARCHAR(20) NOT NULL,
            reviewed_by VARCHAR(255),
            reviewed_at TIMESTAMP WITH TIME ZONE,
            reviewer_notes TEXT,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_refund_approvals_order "
        "ON refund_approvals (order_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_refund_approvals_status "
        "ON refund_approvals (status)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_refund_approvals_requested_by "
        "ON refund_approvals (requested_by)"
    )


def downgrade() -> None:
    """Drop the tables this revision created.

    Data-destroying, as downgrades always are — these are tables the previous
    revision did not have, so downgrading returns the schema to that state.
    """
    for table in (
        "refund_approvals",
        "referral_credits",
        "admin_webhook_logs",
        "admin_webhooks",
        "email_unsubscribes",
        "idempotency_responses",
        "post_categories",
        "categories",
        "plan_cities",
        "cities",
        "trigger_weights",
        "trigger_events",
        "charon_ab_outcomes",
        "charon_ab_assignments",
    ):
        op.execute(f"DROP TABLE IF EXISTS {table}")