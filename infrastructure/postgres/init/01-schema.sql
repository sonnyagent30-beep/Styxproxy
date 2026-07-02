-- Bunche — PostgreSQL Schema v2.0
-- Source: docs/DATABASE_SCHEMA.md (Option A — full multi-channel)
-- Version: 2.0
-- Date: 2026-07-01

BEGIN;

-- ── Extensions ──────────────────────────────────────────────
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ── ENUM Types ────────────────────────────────────────────
CREATE TYPE platform AS ENUM ('telegram', 'whatsapp');
CREATE TYPE account_status AS ENUM ('active', 'suspended', 'banned', 'pending_merge');
CREATE TYPE order_status AS ENUM (
    'pending_payment', 'paid', 'processing',
    'fulfilled', 'active', 'expired',
    'cancelled', 'refunded'
);
CREATE TYPE pool_type AS ENUM ('paid', 'free_trial', 'refunded_recycled');
CREATE TYPE credential_status AS ENUM ('active', 'expired', 'revoked', 'suspended');
CREATE TYPE trial_status AS ENUM ('pending', 'active', 'expired', 'dead');
CREATE TYPE merge_status AS ENUM (
    'pending', 'otp_sent', 'verified',
    'completed', 'expired', 'failed', 'cancelled'
);
CREATE TYPE error_severity AS ENUM ('low', 'medium', 'high', 'critical');
CREATE TYPE error_status AS ENUM ('open', 'in_progress', 'resolved');

-- ── customers ─────────────────────────────────────────────
-- Unified customer profile. Created when first platform account is
-- registered, or when two accounts are merged. A customer may have
-- 0, 1, or 2 platform accounts (Telegram + WhatsApp).
CREATE TABLE customers (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Set when two accounts are merged
    merged_at                   TIMESTAMPTZ,
    merged_from_telegram        BOOLEAN DEFAULT FALSE,
    merged_from_whatsapp        BOOLEAN DEFAULT FALSE,

    -- Preferences
    preferred_channel           VARCHAR(20) DEFAULT 'either',
    -- 'telegram', 'whatsapp', 'either'

    -- Referral
    referral_code               VARCHAR(20) UNIQUE NOT NULL,
    referred_by                 UUID REFERENCES customers(id),

    -- Metrics (aggregated across all platforms after merge)
    total_orders                INT DEFAULT 0,
    lifetime_value_ngn          DECIMAL(12,2) DEFAULT 0,
    last_active_at              TIMESTAMPTZ,

    created_at                  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_customers_referral      ON customers(referral_code);
CREATE INDEX idx_customers_referred_by   ON customers(referred_by);

-- ── platform_accounts ───────────────────────────────────────
-- One row per platform per customer.
-- customer_id is NULL until the two accounts are merged.
CREATE TABLE platform_accounts (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- NULL until accounts are merged
    customer_id                 UUID REFERENCES customers(id),

    platform                    platform NOT NULL,
    -- 'telegram' or 'whatsapp'

    -- For Telegram: chat_id (as string)
    -- For WhatsApp: phone number hash (sha256[:20])
    platform_user_id            VARCHAR(100) NOT NULL,

    display_name                VARCHAR(200),
    username                    VARCHAR(100),  -- Telegram username (without @)

    account_status              account_status DEFAULT 'active',
    -- 'active', 'suspended', 'banned', 'pending_merge'

    -- Flexible per-platform metadata
    -- Telegram: {language, is_bot_admin, telegram_user_id}
    -- WhatsApp: {wa_phone, wa_business_account_id}
    metadata                    JSONB DEFAULT '{}',

    first_seen_at               TIMESTAMPTZ DEFAULT NOW(),
    last_active_at              TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(platform, platform_user_id)
);

CREATE INDEX idx_platform_accounts_customer  ON platform_accounts(customer_id);
CREATE INDEX idx_platform_accounts_platform ON platform_accounts(platform);
CREATE INDEX idx_platform_accounts_status    ON platform_accounts(account_status);
CREATE INDEX idx_platform_accounts_lookup   ON platform_accounts(platform, platform_user_id);

-- ── merge_requests ──────────────────────────────────────────
-- OTP-based account linking. Customer initiates from one channel,
-- OTP is sent to the other channel.
CREATE TABLE merge_requests (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    requester_platform          platform NOT NULL,
    requester_platform_user_id  VARCHAR(100) NOT NULL,

    target_platform             platform NOT NULL,
    target_platform_user_id    VARCHAR(100) NOT NULL,

    otp_code                    VARCHAR(6) NOT NULL,
    otp_sent_at                 TIMESTAMPTZ DEFAULT NOW(),
    otp_expires_at              TIMESTAMPTZ NOT NULL,  -- valid for 10 minutes

    status                      merge_status DEFAULT 'pending',
    -- 'pending', 'otp_sent', 'verified', 'completed',
    -- 'expired', 'failed', 'cancelled'

    created_at                  TIMESTAMPTZ DEFAULT NOW(),
    completed_at                TIMESTAMPTZ
);

CREATE INDEX idx_merge_requests_requester ON merge_requests(requester_platform, requester_platform_user_id);
CREATE INDEX idx_merge_requests_target   ON merge_requests(target_platform, target_platform_user_id);
CREATE INDEX idx_merge_requests_status    ON merge_requests(status);

-- ── orders ─────────────────────────────────────────────────
-- Every proxy order. Linked to platform_account (not directly
-- to customers) to preserve per-channel context.
CREATE TABLE orders (
    order_id                    VARCHAR(20) PRIMARY KEY,

    -- Which platform account placed this order
    platform_account_id          UUID REFERENCES platform_accounts(id),

    -- Channel used to place the order
    channel_origin              platform NOT NULL,

    -- Product details
    plan_type                   VARCHAR(20),   -- 'ISP', 'DC', 'RESIDENTIAL', 'MOBILE'
    plan_code                   VARCHAR(50),
    country                      VARCHAR(10),
    quantity                    INT DEFAULT 1,
    amount_paid_ngn             DECIMAL(12,2),
    payment_reference           VARCHAR(100),

    -- Provider
    provider                     VARCHAR(50),  -- 'Proxy-Seller', 'DataImpulse', 'Rayobyte'
    provider_order_id            VARCHAR(100),

    -- Bunche credential issued for this order
    bunche_credential_id         INT REFERENCES bunche_credentials(id),

    status                      order_status DEFAULT 'pending_payment',
    -- 'pending_payment', 'paid', 'processing', 'fulfilled',
    -- 'active', 'expired', 'cancelled', 'refunded'

    ip_tested                   BOOLEAN DEFAULT FALSE,
    ip_test_result              VARCHAR(10),  -- 'PASS', 'FAIL', 'N/A'

    -- Data tracking (for GB-based plans)
    data_total_gb               DECIMAL(10,2),
    data_remaining_gb            DECIMAL(10,2),
    data_expires                TIMESTAMPTZ,

    expires_at                  TIMESTAMPTZ,

    -- Ban tracking
    ban_reported                BOOLEAN DEFAULT FALSE,
    screenshot_url              TEXT,
    ban_verified                VARCHAR(50),  -- 'verified', 'rejected', 'pending'
    replacement_count           INT DEFAULT 0,
    refund_requested            BOOLEAN DEFAULT FALSE,
    refund_reason               TEXT,
    notes                       TEXT,

    created_at                  TIMESTAMPTZ DEFAULT NOW(),
    fulfilled_at                TIMESTAMPTZ,
    cost_usd                    DECIMAL(10,4)
);

CREATE INDEX idx_orders_platform_account  ON orders(platform_account_id);
CREATE INDEX idx_orders_channel           ON orders(channel_origin);
CREATE INDEX idx_orders_status           ON orders(status);
CREATE INDEX idx_orders_expires          ON orders(expires_at)
    WHERE expires_at IS NOT NULL;
CREATE INDEX idx_orders_created          ON orders(created_at DESC);

-- ── bunche_credentials ─────────────────────────────────────
-- Maps Bunche-branded usernames to upstream provider proxy IPs.
-- This is the core Dante auth table. Dante uses bun_username to
-- route traffic to the correct upstream proxy.
CREATE TABLE bunche_credentials (
    id                          SERIAL PRIMARY KEY,

    -- Bunche username issued to customer (used to auth to Dante)
    bun_username                 VARCHAR(50) UNIQUE NOT NULL,
    -- Format: bun_<random> e.g. bun_ayomide7

    -- bcrypt hash of the Bunche password (NOT the provider password)
    password_hash               TEXT NOT NULL,

    -- Customer linkage (via platform_account, not directly to customer)
    platform_account_id          UUID REFERENCES platform_accounts(id),
    order_id                    VARCHAR(20) REFERENCES orders(order_id),

    pool_type                   pool_type DEFAULT 'paid',
    -- 'paid', 'free_trial', 'refunded_recycled'

    -- The actual upstream proxy from the provider
    provider_name               VARCHAR(50),  -- 'Proxy-Seller', 'DataImpulse'
    provider_order_id            VARCHAR(100),
    provider_username            VARCHAR(100),
    provider_password            VARCHAR(100),
    upstream_proxy_ip            INET,
    upstream_proxy_port          INT DEFAULT 1080,

    -- Dante config
    dante_port                  INT,

    status                      credential_status DEFAULT 'active',
    -- 'active', 'expired', 'revoked', 'suspended'

    created_at                  TIMESTAMPTZ DEFAULT NOW(),
    expires_at                  TIMESTAMPTZ,   -- NULL = never expires (paid)
    revoked_at                   TIMESTAMPTZ,
    revoke_reason                VARCHAR(50),  -- 'refund', 'expiry', 'abuse', 'manual'

    last_used_at                TIMESTAMPTZ,
    gb_used                     DECIMAL(10,2) DEFAULT 0
);

CREATE INDEX idx_bunche_cred_username         ON bunche_credentials(bun_username);
CREATE INDEX idx_bunche_cred_platform_account ON bunche_credentials(platform_account_id);
CREATE INDEX idx_bunche_cred_status          ON bunche_credentials(status);
CREATE INDEX idx_bunche_cred_pool            ON bunche_credentials(pool_type, status);
CREATE INDEX idx_bunche_cred_expires         ON bunche_credentials(expires_at)
    WHERE expires_at IS NOT NULL AND status = 'active';

-- ── free_trials ────────────────────────────────────────────
-- Tracks free trial sessions. One row per trial session.
-- Customer completes Theorem Reach surveys, then claims credentials.
CREATE TABLE free_trials (
    id                          SERIAL PRIMARY KEY,

    platform_account_id          UUID REFERENCES platform_accounts(id),
    channel_origin              platform NOT NULL,

    trial_date                  TIMESTAMPTZ DEFAULT NOW(),

    -- How many survey postbacks have been recorded for this session
    surveys_completed            INT DEFAULT 0,
    total_hours                 INT DEFAULT 0,  -- surveys_completed × 2hr

    -- Set when customer says "done" and credentials are sent
    bunche_credential_id         INT REFERENCES bunche_credentials(id),

    status                      trial_status DEFAULT 'pending',
    -- 'pending' (doing surveys), 'active' (creds sent), 'expired', 'dead'

    disclaimer_accepted         BOOLEAN DEFAULT FALSE,
    created_at                  TIMESTAMPTZ DEFAULT NOW(),
    fulfilled_at                TIMESTAMPTZ
);

CREATE INDEX idx_free_trials_platform_account ON free_trials(platform_account_id, trial_date);
CREATE INDEX idx_free_trials_status          ON free_trials(status);

-- ── pending_trial_surveys ──────────────────────────────────
-- Records each Theorem Reach postback individually.
-- Customer accumulates surveys until they say "done".
CREATE TABLE pending_trial_surveys (
    id                          SERIAL PRIMARY KEY,

    platform_account_id          UUID REFERENCES platform_accounts(id),
    channel_origin              platform NOT NULL,

    -- Theorem Reach postback data
    survey_transaction_id        VARCHAR(100) UNIQUE NOT NULL,
    survey_user_id               VARCHAR(50),
    survey_id                    VARCHAR(50),
    payout_usd                   DECIMAL(8,2),
    survey_completed_at          TIMESTAMPTZ DEFAULT NOW(),

    -- Session linkage
    free_trial_id                INT REFERENCES free_trials(id),

    -- Whether this survey has been credited toward a fulfilled trial
    credited                    BOOLEAN DEFAULT FALSE,

    created_at                  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_pending_surveys_platform ON pending_trial_surveys(platform_account_id);
CREATE INDEX idx_pending_surveys_session  ON pending_trial_surveys(free_trial_id);
CREATE INDEX idx_pending_surveys_uncredited ON pending_trial_surveys(credited)
    WHERE credited = FALSE;

-- ── customer_audit_log ─────────────────────────────────────
-- Immutable audit trail linked to platform_account_id.
-- No UPDATE or DELETE allowed on this table.
CREATE TABLE customer_audit_log (
    id                          BIGSERIAL PRIMARY KEY,
    timestamp                    TIMESTAMPTZ DEFAULT NOW(),
    request_id                   VARCHAR(50),

    -- Links to platform_account (preserves per-channel identity before merge)
    platform_account_id          UUID REFERENCES platform_accounts(id),

    event_type                   VARCHAR(50),
    order_id                    VARCHAR(20),
    workflow                     VARCHAR(50),
    status                       VARCHAR(20),
    details                      JSONB
);

CREATE INDEX idx_audit_timestamp       ON customer_audit_log(timestamp DESC);
CREATE INDEX idx_audit_platform_account ON customer_audit_log(platform_account_id);
CREATE INDEX idx_audit_event          ON customer_audit_log(event_type, timestamp);

-- Prevent updates/deletes on audit log (immutable)
CREATE OR REPLACE FUNCTION make_audit_log_immutable()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'INSERT ONLY — audit log records cannot be updated or deleted';
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_audit_immutable
    BEFORE UPDATE OR DELETE ON customer_audit_log
    FOR EACH ROW EXECUTE FUNCTION make_audit_log_immutable();

-- ── processed_webhooks ──────────────────────────────────────
-- Idempotency storage for webhook processing.
-- Records are kept for 90 days then cleaned up.
CREATE TABLE processed_webhooks (
    id                          BIGSERIAL PRIMARY KEY,
    webhook_id                  VARCHAR(100) UNIQUE NOT NULL,
    provider                    VARCHAR(20),
    event_type                   VARCHAR(50),
    processed_at                 TIMESTAMPTZ DEFAULT NOW(),
    response_sent               BOOLEAN DEFAULT FALSE,
    metadata                    JSONB
);

CREATE INDEX idx_processed_webhooks_id       ON processed_webhooks(webhook_id);
CREATE INDEX idx_processed_webhooks_cleanup   ON processed_webhooks(processed_at)
    WHERE processed_at < NOW() - INTERVAL '90 days';

-- ── admin_auth ──────────────────────────────────────────────
-- Admin authentication: PIN (bcrypt) + TOTP
CREATE TABLE admin_auth (
    admin_phone                 VARCHAR(20) PRIMARY KEY,
    pin_hash                    TEXT,          -- bcrypt hash of 4-6 digit PIN
    pin_set_at                  TIMESTAMPTZ,
    totp_secret                 TEXT,          -- encrypted TOTP secret
    totp_enabled               BOOLEAN DEFAULT FALSE,
    totp_set_at                 TIMESTAMPTZ,
    failed_attempts            INT DEFAULT 0,
    locked_until                TIMESTAMPTZ,
    created_at                  TIMESTAMPTZ DEFAULT NOW(),
    last_used                   TIMESTAMPTZ
);

CREATE INDEX idx_admin_auth_locked ON admin_auth(locked_until)
    WHERE locked_until IS NOT NULL;

-- ── admin_commands_log ─────────────────────────────────────
-- Every admin action logged for security auditing.
CREATE TABLE admin_commands_log (
    id                          BIGSERIAL PRIMARY KEY,
    timestamp                    TIMESTAMPTZ DEFAULT NOW(),
    admin_phone                 VARCHAR(20),
    command                      TEXT,
    risk_level                   VARCHAR(10),
    auth_method                  VARCHAR(20),
    auth_success                BOOLEAN,
    execution_success           BOOLEAN,
    error_message                TEXT,
    metadata                     JSONB,
    session_id                   UUID,
    ip_address                  VARCHAR(45)
);

CREATE INDEX idx_admin_commands_timestamp ON admin_commands_log(timestamp DESC);
CREATE INDEX idx_admin_commands_admin    ON admin_commands_log(admin_phone, timestamp);
CREATE INDEX idx_admin_commands_failures  ON admin_commands_log(auth_success, timestamp)
    WHERE auth_success = FALSE;

-- ── admin_sessions_log ─────────────────────────────────────
CREATE TABLE admin_sessions_log (
    id                          BIGSERIAL PRIMARY KEY,
    session_id                   UUID,
    admin_phone                 VARCHAR(20),
    started_at                   TIMESTAMPTZ,
    ended_at                     TIMESTAMPTZ,
    duration_minutes            INT,
    commands_used               INT,
    ended_reason                 VARCHAR(50),
    ip_address                  VARCHAR(45)
);

CREATE INDEX idx_sessions_admin ON admin_sessions_log(admin_phone, started_at);

-- ── error_log ───────────────────────────────────────────────
-- Workflow and system error tracking for n8n + FastAPI.
CREATE TABLE error_log (
    id                          BIGSERIAL PRIMARY KEY,
    timestamp                    TIMESTAMPTZ DEFAULT NOW(),
    workflow_name                VARCHAR(50),
    node_name                    VARCHAR(50),
    error_type                   VARCHAR(50),
    error_message                TEXT,
    error_stack                  TEXT,
    execution_id                 VARCHAR(50),
    platform_account_id          UUID REFERENCES platform_accounts(id),
    order_id                    VARCHAR(20),
    severity                    error_severity DEFAULT 'medium',
    status                      error_status DEFAULT 'open',
    resolved_by                  VARCHAR(50),
    resolved_at                  TIMESTAMPTZ,
    resolution_notes             TEXT
);

CREATE INDEX idx_error_severity  ON error_log(severity, status);
CREATE INDEX idx_error_timestamp ON error_log(timestamp DESC);
CREATE INDEX idx_error_open     ON error_log(status) WHERE status = 'open';

-- ── provider_log ────────────────────────────────────────────
-- Logs from Proxy-Seller / DataImpulse API calls.
CREATE TABLE provider_log (
    id                          BIGSERIAL PRIMARY KEY,
    timestamp                    TIMESTAMPTZ DEFAULT NOW(),
    provider                     VARCHAR(50),
    event_type                   VARCHAR(50),
    status                       VARCHAR(20),
    details                      TEXT,
    latency_ms                   INT,
    response_code                VARCHAR(20)
);

CREATE INDEX idx_provider_timestamp ON provider_log(timestamp DESC);
CREATE INDEX idx_provider_status    ON provider_log(provider, status);
CREATE INDEX idx_provider_health    ON provider_log(event_type, timestamp)
    WHERE event_type = 'health_check';

-- ── daily_summary ───────────────────────────────────────────
-- Aggregated daily stats for the admin dashboard.
CREATE TABLE daily_summary (
    date                        DATE PRIMARY KEY,
    total_orders                INT,
    total_revenue_ngn           DECIMAL(12,2),
    total_errors                INT,
    critical_errors            INT,
    total_refunds               INT,
    refund_amount_ngn           DECIMAL(12,2),
    new_customers               INT,
    free_trials_used            INT,
    provider_downtime_min        INT,
    credentials_active          INT,
    credentials_free_trial       INT
);

-- ── rate_limit_log ─────────────────────────────────────────
-- Per-IP and per-user rate limit tracking.
CREATE TABLE rate_limit_log (
    id                          BIGSERIAL PRIMARY KEY,
    timestamp                    TIMESTAMPTZ DEFAULT NOW(),
    layer                        VARCHAR(20),  -- 'nginx', 'api', 'n8n'
    endpoint                     VARCHAR(50),
    identifier                   VARCHAR(100),
    identifier_type              VARCHAR(10),  -- 'chat_id', 'phone_hash', 'ip'
    action                       VARCHAR(20),  -- 'allowed', 'blocked', 'throttled'
    user_agent                   TEXT,
    request_id                    VARCHAR(50)
);

CREATE INDEX idx_rate_limit_timestamp ON rate_limit_log(timestamp DESC);
CREATE INDEX idx_rate_limit_blocks   ON rate_limit_log(layer, action, timestamp)
    WHERE action != 'allowed';
CREATE INDEX idx_rate_limit_ip       ON rate_limit_log(identifier_type, identifier)
    WHERE identifier_type = 'ip';

-- ── webhook_security_log ───────────────────────────────────
-- Webhook signature verification failures.
CREATE TABLE webhook_security_log (
    id                          BIGSERIAL PRIMARY KEY,
    timestamp                    TIMESTAMPTZ DEFAULT NOW(),
    provider                     VARCHAR(20),
    verified                    BOOLEAN,
    failure_reason               TEXT,
    ip_address                  VARCHAR(45),
    user_agent                   TEXT,
    request_id                    VARCHAR(50)
);

CREATE INDEX idx_webhook_log_timestamp ON webhook_security_log(timestamp DESC);
CREATE INDEX idx_webhook_log_failures  ON webhook_security_log(verified, timestamp)
    WHERE verified = FALSE;

-- ── Seed data: products ────────────────────────────────────
INSERT INTO products (sku, name, category, description, buy_cost_usd, sell_price, stock_qty, is_active) VALUES
-- ISP Proxies
('ISP_UK_1M',  'ISP Proxy UK 1 Month',   'ISP',        'United Kingdom ISP proxy, 1 month',  8.00, 5500.00, 100, TRUE),
('ISP_US_1M',  'ISP Proxy US 1 Month',   'ISP',        'United States ISP proxy, 1 month',  8.00, 5500.00, 100, TRUE),
('ISP_DE_1M',  'ISP Proxy DE 1 Month',   'ISP',        'Germany ISP proxy, 1 month',        8.00, 5500.00, 100, TRUE),
('ISP_UK_3M',  'ISP Proxy UK 3 Months', 'ISP',        'United Kingdom ISP proxy, 3 months', 22.00, 15000.00, 50, TRUE),
('ISP_US_3M',  'ISP Proxy US 3 Months', 'ISP',        'United States ISP proxy, 3 months', 22.00, 15000.00, 50, TRUE),
-- Datacenter
('DC_IPv4_1M', 'DC IPv4 1 Month',       'DATACENTER', 'Datacenter IPv4 proxy, 1 month',   3.00, 2500.00, 500, TRUE),
('DC_IPv6_1M', 'DC IPv6 1 Month',       'DATACENTER', 'Datacenter IPv6 proxy, 1 month',   2.00, 2000.00, 500, TRUE),
-- Residential
('RES_5GB',    'Residential 5GB',        'RESIDENTIAL','Residential proxy, 5GB data',        5.00, 1500.00, 200, TRUE),
('RES_10GB',   'Residential 10GB',       'RESIDENTIAL','Residential proxy, 10GB data',       9.00, 2800.00, 200, TRUE),
-- Mobile 4G
('MOB_5GB',    'Mobile 4G 5GB',          'MOBILE',     'Mobile 4G proxy, 5GB data',         12.00, 6000.00, 50, TRUE),
('MOB_10GB',   'Mobile 4G 10GB',         'MOBILE',     'Mobile 4G proxy, 10GB data',        22.00, 11000.00, 50, TRUE);

COMMIT;
