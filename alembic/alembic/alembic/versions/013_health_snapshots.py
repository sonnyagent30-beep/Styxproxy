"""Alembic migration 013: add health_snapshots table for §14 M5.

Theme A: time-series of system health probes. Cron job polls every minute
and writes a row; GET /api/admin/health/history reads for admin dashboard.

Retention strategy: out of scope for this migration. Add a separate
cron (e.g. daily) to prune rows older than 7 days.
"""

from alembic import op

revision = "013_health_snapshots"
down_revision = "012_missing_indexes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS health_snapshots (
            id SERIAL PRIMARY KEY,
            db_connected BOOLEAN NOT NULL DEFAULT FALSE,
            redis_connected BOOLEAN NOT NULL DEFAULT FALSE,
            m2_connected BOOLEAN NOT NULL DEFAULT FALSE,
            litellm_connected BOOLEAN NOT NULL DEFAULT FALSE,
            ollama_connected BOOLEAN NOT NULL DEFAULT FALSE,
            overall_status VARCHAR(20) NOT NULL DEFAULT 'unknown',
            charon_available BOOLEAN NOT NULL DEFAULT FALSE,
            total_latency_ms NUMERIC(10, 2),
            error_summary TEXT,
            source VARCHAR(20) NOT NULL DEFAULT 'cron',
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_health_snapshots_created
        ON health_snapshots (created_at DESC)
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_health_snapshots_created")
    op.execute("DROP TABLE IF EXISTS health_snapshots")
