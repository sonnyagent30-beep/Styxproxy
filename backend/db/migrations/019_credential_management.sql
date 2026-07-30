-- 019_credential_management.sql
-- Customer proxy management features:
--   1. password rotation tracking (last_rotated_at, rotation_count)
--   2. daily password rotation counter for rate limiting
--   3. sticky session config (last sticky IP + TTL)
--   4. bandwidth alert thresholds
--   5. upstream gateway health cache (for failover decisions)

-- 1. Add password rotation tracking
ALTER TABLE styxproxy_credentials
  ADD COLUMN IF NOT EXISTS password_rotated_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS password_rotations_today INTEGER NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS password_rotations_reset_at DATE NOT NULL DEFAULT CURRENT_DATE,
  ADD COLUMN IF NOT EXISTS country_target VARCHAR(2),  -- ISO 3166-1 alpha-2, NULL = pool default
  ADD COLUMN IF NOT EXISTS sticky_session_minutes INTEGER NOT NULL DEFAULT 0,  -- 0 = rotate per request, max 60
  ADD COLUMN IF NOT EXISTS bandwidth_alert_pct INTEGER NOT NULL DEFAULT 80,  -- alert at 80% of plan
  ADD COLUMN IF NOT EXISTS last_ip_country VARCHAR(2),
  ADD COLUMN IF NOT EXISTS last_ip_address INET,
  ADD COLUMN IF NOT EXISTS last_used_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS session_id VARCHAR(50),  -- current sticky session id
  ADD COLUMN IF NOT EXISTS session_expires_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_credentials_customer_phone
  ON styxproxy_credentials(customer_phone);
CREATE INDEX IF NOT EXISTS idx_credentials_status
  ON styxproxy_credentials(status);
CREATE INDEX IF NOT EXISTS idx_credentials_expires
  ON styxproxy_credentials(expires_at);

-- 2. Add country_target to relay_entries
ALTER TABLE styxproxy_relay_entries
  ADD COLUMN IF NOT EXISTS country_target VARCHAR(2),
  ADD COLUMN IF NOT EXISTS sticky_session_minutes INTEGER NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS session_id VARCHAR(50);

-- 3. Upstream gateway health table (for failover + monitoring)
CREATE TABLE IF NOT EXISTS upstream_gateway_health (
  id SERIAL PRIMARY KEY,
  upstream_host VARCHAR(255) NOT NULL,
  upstream_port INTEGER NOT NULL,
  upstream_protocol VARCHAR(10) NOT NULL DEFAULT 'http',
  upstream_type VARCHAR(40) NOT NULL,  -- rayobyte_resi, rayobyte_mobile, proxy_seller_isp, etc.
  check_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  is_reachable BOOLEAN NOT NULL,
  latency_ms INTEGER,
  error TEXT,
  bytes_sent BIGINT NOT NULL DEFAULT 0,
  bytes_failed BIGINT NOT NULL DEFAULT 0,
  last_success_at TIMESTAMPTZ,
  consecutive_failures INTEGER NOT NULL DEFAULT 0,
  UNIQUE(upstream_host, upstream_port, upstream_type, check_at)
);
CREATE INDEX IF NOT EXISTS idx_gateway_health_lookup
  ON upstream_gateway_health(upstream_host, upstream_port, upstream_type, check_at DESC);
CREATE INDEX IF NOT EXISTS idx_gateway_health_failures
  ON upstream_gateway_health(upstream_host, consecutive_failures DESC)
  WHERE consecutive_failures > 0;

-- 4. Password rotation audit log
CREATE TABLE IF NOT EXISTS credential_password_rotations (
  id SERIAL PRIMARY KEY,
  credential_id INTEGER NOT NULL REFERENCES styxproxy_credentials(id) ON DELETE CASCADE,
  rotated_by VARCHAR(20) NOT NULL,  -- 'customer' or 'admin'
  rotated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  ip_address INET,
  user_agent TEXT
);
CREATE INDEX IF NOT EXISTS idx_password_rotations_credential
  ON credential_password_rotations(credential_id, rotated_at DESC);

-- 5. Customer notification preferences (for low-bandwidth alerts)
CREATE TABLE IF NOT EXISTS credential_notifications (
  id SERIAL PRIMARY KEY,
  credential_id INTEGER NOT NULL REFERENCES styxproxy_credentials(id) ON DELETE CASCADE,
  notification_type VARCHAR(50) NOT NULL,  -- bandwidth_low, password_rotated, suspended, expired
  channel VARCHAR(20) NOT NULL DEFAULT 'sms',  -- sms, telegram, email
  target VARCHAR(255) NOT NULL,  -- phone, telegram_chat_id, or email
  enabled BOOLEAN NOT NULL DEFAULT true,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_notifications_credential
  ON credential_notifications(credential_id, enabled) WHERE enabled;

-- 6. Add new upstream_type values to plan table if needed (already has plan_type column)
COMMENT ON COLUMN styxproxy_relay_entries.upstream_type IS
  'rayobyte_resi | rayobyte_mobile | proxy_seller_isp | contabo_dc | interserver_dc';
COMMENT ON COLUMN styxproxy_credentials.pool_type IS
  'residential | mobile | datacenter | isp | trial';