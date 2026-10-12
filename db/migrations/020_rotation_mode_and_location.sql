-- 020_rotation_mode_and_location.sql
-- Allow customers to:
--   1. Pick a rotation_mode (rotating pool vs static IP) at purchase
--   2. Pick a location (country) at purchase AND change it via /manage
--   3. Plans become "type + size" templates; country is a runtime choice

-- 1. Add rotation_mode to plans table
--    rotating = pool of IPs that rotate per request
--    static   = pin to single IP (sticky session, max 60 min)
--    both     = customer can pick either at purchase
ALTER TABLE plans
  ADD COLUMN IF NOT EXISTS rotation_mode VARCHAR(20) NOT NULL DEFAULT 'both',
  ADD COLUMN IF NOT EXISTS supports_country_change BOOLEAN NOT NULL DEFAULT true;

COMMENT ON COLUMN plans.rotation_mode IS 'rotating | static | both (customer choice)';
COMMENT ON COLUMN plans.supports_country_change IS 'false for ISP/Datacenter (fixed location)';

-- 2. Add rotation_mode to orders table
ALTER TABLE orders
  ADD COLUMN IF NOT EXISTS rotation_mode VARCHAR(20);

COMMENT ON COLUMN orders.rotation_mode IS 'rotating | static — what customer picked at purchase';

-- 3. Add rotation_mode + assigned_static_ip to styxproxy_credentials
ALTER TABLE styxproxy_credentials
  ADD COLUMN IF NOT EXISTS rotation_mode VARCHAR(20) NOT NULL DEFAULT 'rotating',
  ADD COLUMN IF NOT EXISTS assigned_static_ip INET,
  ADD COLUMN IF NOT EXISTS assigned_static_session_id VARCHAR(50),
  ADD COLUMN IF NOT EXISTS last_static_assigned_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS location_change_count INTEGER NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS rotation_mode_change_count INTEGER NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS location_changes_reset_at DATE NOT NULL DEFAULT CURRENT_DATE,
  ADD COLUMN IF NOT EXISTS rotation_mode_changes_reset_at DATE NOT NULL DEFAULT CURRENT_DATE;

COMMENT ON COLUMN styxproxy_credentials.rotation_mode IS 'rotating | static — current setting';
COMMENT ON COLUMN styxproxy_credentials.assigned_static_ip IS 'For static mode: the IP the relay pins to';
COMMENT ON COLUMN styxproxy_credentials.assigned_static_session_id IS 'For static mode: Rayobyte session-XXX used to pin';

-- 4. Index for fast lookup
CREATE INDEX IF NOT EXISTS idx_credentials_rotation_mode
  ON styxproxy_credentials(rotation_mode) WHERE status = 'active';

-- 5. Pricing hints for static (premium tier)
--    Static IPs are premium — they consume one slot from a finite pool per country
--    so we price them higher. Add a multiplier to plans.
ALTER TABLE plans
  ADD COLUMN IF NOT EXISTS static_price_multiplier NUMERIC(4,2) NOT NULL DEFAULT 2.50;

COMMENT ON COLUMN plans.static_price_multiplier IS 'static mode costs this × base price (e.g. 2.5x)';