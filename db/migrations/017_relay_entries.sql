-- Migration 015: styxproxy_relay_entries
-- Sprint 10 (RAYOBYTE-FIX SPRINT B): Maps paid customers to upstream providers
-- This is the "Postgres is the source of truth" table for the gost relay.
-- The relay_sync.py daemon reads from this table and renders /etc/styxproxy/auth.json
-- for gost to consume.

CREATE TABLE IF NOT EXISTS styxproxy_relay_entries (
    id SERIAL PRIMARY KEY,
    customer_id UUID REFERENCES customers(id) ON DELETE CASCADE,
    credential_id INTEGER REFERENCES styxproxy_credentials(id) ON DELETE CASCADE,
    upstream_type VARCHAR(40) NOT NULL,  -- rayobyte_resi, rayobyte_mobile, rayobyte_isp, proxy_seller_isp, contabo_dc, interserver_dc
    upstream_host VARCHAR(255) NOT NULL,
    upstream_port INTEGER NOT NULL,
    upstream_user VARCHAR(255),
    upstream_pass VARCHAR(255),
    upstream_protocol VARCHAR(10) DEFAULT 'socks5',  -- socks5, http, https
    exit_ip_strategy VARCHAR(20) DEFAULT 'pool',  -- 'pool' (rotating pool) or 'fixed' (specific IP)
    exit_ip_pool_code VARCHAR(2),  -- ISO 3166-1 alpha-2 country code, e.g. 'US', 'GB', 'NG'
    region VARCHAR(20),  -- 'US', 'UK', 'DE', etc. - which relay region serves this customer
    -- Bandwidth tracking (for rotating pool types)
    monthly_bandwidth_gb NUMERIC(10, 2),
    monthly_bandwidth_used_bytes BIGINT NOT NULL DEFAULT 0,
    last_bandwidth_reset_at TIMESTAMP WITH TIME ZONE,
    -- Lifecycle
    status VARCHAR(20) NOT NULL DEFAULT 'active',  -- active, suspended, expired, revoked
    suspend_reason VARCHAR(100),
    expires_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    -- Audit
    rotation_count INTEGER NOT NULL DEFAULT 0,
    last_rotated_at TIMESTAMP WITH TIME ZONE,
    last_used_at TIMESTAMP WITH TIME ZONE,
    bytes_used BIGINT NOT NULL DEFAULT 0  -- total bytes (across all rotations)
);

CREATE INDEX idx_relay_entries_customer ON styxproxy_relay_entries(customer_id);
CREATE INDEX idx_relay_entries_credential ON styxproxy_relay_entries(credential_id);
CREATE INDEX idx_relay_entries_status ON styxproxy_relay_entries(status);
CREATE INDEX idx_relay_entries_expires ON styxproxy_relay_entries(expires_at);
CREATE INDEX idx_relay_entries_region ON styxproxy_relay_entries(region);

-- Mark the table as owned by styxproxy_migrate (matching the rest of the schema)
ALTER TABLE styxproxy_relay_entries OWNER TO styxproxy_migrate;

-- Trigger for updated_at
CREATE OR REPLACE FUNCTION update_relay_entries_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_relay_entries_updated_at ON styxproxy_relay_entries;
CREATE TRIGGER trg_relay_entries_updated_at
    BEFORE UPDATE ON styxproxy_relay_entries
    FOR EACH ROW
    EXECUTE FUNCTION update_relay_entries_updated_at();

-- Add a few helpful views

-- View: active entries with their customer info
CREATE OR REPLACE VIEW v_active_relay_entries AS
SELECT
    r.id,
    r.customer_id,
    c.telegram_id,
    c.phone,
    r.credential_id,
    r.upstream_type,
    r.upstream_host,
    r.upstream_port,
    r.upstream_protocol,
    r.exit_ip_strategy,
    r.exit_ip_pool_code,
    r.region,
    r.monthly_bandwidth_gb,
    r.monthly_bandwidth_used_bytes,
    r.status,
    r.expires_at,
    r.created_at,
    r.updated_at
FROM styxproxy_relay_entries r
LEFT JOIN customers c ON r.customer_id = c.id
WHERE r.status = 'active';

-- View: entries near bandwidth exhaustion (>80% used)
CREATE OR REPLACE VIEW v_relay_bandwidth_warning AS
SELECT
    r.id,
    r.customer_id,
    r.upstream_type,
    r.monthly_bandwidth_gb,
    r.monthly_bandwidth_used_bytes,
    (r.monthly_bandwidth_used_bytes::NUMERIC / (r.monthly_bandwidth_gb * 1024 * 1024 * 1024)) * 100 AS pct_used
FROM styxproxy_relay_entries r
WHERE r.monthly_bandwidth_gb IS NOT NULL
  AND r.monthly_bandwidth_gb > 0
  AND r.status = 'active'
  AND (r.monthly_bandwidth_used_bytes::NUMERIC / (r.monthly_bandwidth_gb * 1024 * 1024 * 1024)) > 0.8;
