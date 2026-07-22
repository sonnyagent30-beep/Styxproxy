# Styxproxy — Database Schema (PostgreSQL)

**Last Updated:** 2026-07-01
**Status:** Planning Complete — Ready for Implementation

---

## Overview

Replaces Google Sheets with self-hosted PostgreSQL for scalability and reliability. Includes the `styxproxy_credentials` table for mapping Styxproxy usernames to provider IPs via the Dante auth layer.

**Key design principle:** Not every Nigerian number has WhatsApp. Phone number cannot be the common identifier between channels. Instead, each platform (Telegram, WhatsApp) has its own account record. Customers can optionally merge them when they choose.

---

## Schema

### customers

Unified customer profile. Created when the first platform account is created, or when two platform accounts are merged. A customer may have 0, 1, or 2 platform accounts.

```sql
CREATE TABLE customers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Set when two accounts are merged
    merged_at TIMESTAMPTZ,
    merged_from_telegram BOOLEAN DEFAULT FALSE,  -- TRUE if Telegram account was involved in merge
    merged_from_whatsapp BOOLEAN DEFAULT FALSE,  -- TRUE if WhatsApp account was involved in merge

    -- Preferences
    preferred_channel VARCHAR(20) DEFAULT 'either',  -- 'telegram', 'whatsapp', 'either'

    -- Referral
    referral_code VARCHAR(20) UNIQUE NOT NULL,
    referred_by UUID REFERENCES customers(id),

    -- Metrics (aggregated across all platforms after merge)
    total_orders INT DEFAULT 0,
    lifetime_value_ngn DECIMAL(12,2) DEFAULT 0,
    last_active_at TIMESTAMPTZ,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_customers_referral ON customers(referral_code);
CREATE INDEX idx_customers_referred_by ON customers(referred_by);
```

---

### platform_accounts

One row per platform per customer. A customer starts with one platform_account. After a merge, they have two.

**Critical rule:** `customer_id` is NULL until the account is merged. Before merge, the account exists independently.

```sql
CREATE TABLE platform_accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- NULL until accounts are merged
    customer_id UUID REFERENCES customers(id),

    -- Which platform
    platform VARCHAR(20) NOT NULL,  -- 'telegram' or 'whatsapp'

    -- Platform identity
    -- For Telegram: this is the Telegram chat_id (as string)
    -- For WhatsApp: this is the WhatsApp phone number hash (sha256[:20])
    platform_user_id VARCHAR(100) NOT NULL,

    -- Display info
    display_name VARCHAR(200),
    username VARCHAR(100),  -- Telegram username (without @)

    -- Account status
    account_status VARCHAR(20) DEFAULT 'active',  -- 'active', 'suspended', 'banned', 'pending_merge'

    -- Platform metadata (JSONB — flexible per-platform data)
    -- Telegram: {language, is_bot_admin, telegram_user_id}
    -- WhatsApp: {wa_phone, wa_business_account_id}
    metadata JSONB DEFAULT '{}',

    -- Timestamps
    first_seen_at TIMESTAMPTZ DEFAULT NOW(),
    last_active_at TIMESTAMPTZ DEFAULT NOW(),

    -- Constraints
    UNIQUE(platform, platform_user_id)
);

CREATE INDEX idx_platform_accounts_customer ON platform_accounts(customer_id);
CREATE INDEX idx_platform_accounts_platform ON platform_accounts(platform);
CREATE INDEX idx_platform_accounts_status ON platform_accounts(account_status);
CREATE INDEX idx_platform_accounts_lookup ON platform_accounts(platform, platform_user_id);
```

---

### merge_requests

Tracks customer-initiated account linking. Customer asks to link Telegram ↔ WhatsApp. System sends OTP to the target platform. On verify, both platform_accounts get the same `customer_id`.

```sql
CREATE TABLE merge_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Who is requesting the link
    requester_platform VARCHAR(20) NOT NULL,  -- 'telegram' or 'whatsapp'
    requester_platform_user_id VARCHAR(100) NOT NULL,

    -- What they want to link to (phone hash for WhatsApp, chat_id for Telegram)
    target_platform VARCHAR(20) NOT NULL,
    target_platform_user_id VARCHAR(100) NOT NULL,

    -- OTP verification
    otp_code VARCHAR(6) NOT NULL,
    otp_sent_at TIMESTAMPTZ DEFAULT NOW(),
    otp_expires_at TIMESTAMPTZ NOT NULL,  -- otp_code valid for 10 minutes

    -- Status
    status VARCHAR(20) DEFAULT 'pending',  -- 'pending', 'otp_sent', 'verified', 'completed', 'expired', 'failed', 'cancelled'

    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

CREATE INDEX idx_merge_requests_requester ON merge_requests(requester_platform, requester_platform_user_id);
CREATE INDEX idx_merge_requests_target ON merge_requests(target_platform, target_platform_user_id);
CREATE INDEX idx_merge_requests_status ON merge_requests(status);
```

---

### customers (original — add this note)

> **Note:** The `customers` table above replaces the old design that used `phone VARCHAR(20) PRIMARY KEY`. Phone is no longer the primary key. All existing references to `customers.phone` must be updated to use `platform_accounts` lookups instead.

---

### orders

Every proxy order. Linked to `platform_accounts` (not directly to customers — preserves per-platform context).

```sql
CREATE TABLE orders (
    order_id VARCHAR(20) PRIMARY KEY,

    -- Which platform account placed this order
    platform_account_id UUID REFERENCES platform_accounts(id),

    -- Which channel they used to order (for routing follow-ups)
    channel_origin VARCHAR(20) NOT NULL,  -- 'telegram' or 'whatsapp'

    plan_type VARCHAR(20),  -- 'ISP', 'DC', 'RESIDENTIAL', 'MOBILE'
    plan_code VARCHAR(50),
    country VARCHAR(10),
    quantity INT,
    amount_paid_ngn DECIMAL(12,2),
    payment_reference VARCHAR(100),
    provider VARCHAR(50),  -- 'Proxy-Seller', 'DataImpulse', 'Rayobyte'
    provider_order_id VARCHAR(100),

    -- Styxproxy credential issued for this order
    styxproxy_credential_id INT REFERENCES styxproxy_credentials(id),

    status VARCHAR(50) DEFAULT 'pending',  -- 'pending_payment', 'paid', 'fulfilled', 'active', 'expired', 'cancelled', 'refunded'
    ip_tested BOOLEAN DEFAULT FALSE,
    ip_test_result VARCHAR(10),  -- 'PASS', 'FAIL', 'N/A'

    -- Data tracking
    data_total_gb DECIMAL(10,2),
    data_remaining_gb DECIMAL(10,2),
    data_expires TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,

    -- Ban tracking
    ban_reported BOOLEAN DEFAULT FALSE,
    screenshot_url TEXT,
    ban_verified VARCHAR(50),  -- 'verified', 'rejected', 'pending'
    replacement_count INT DEFAULT 0,
    refund_requested BOOLEAN DEFAULT FALSE,
    refund_reason TEXT,
    notes TEXT,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    fulfilled_at TIMESTAMPTZ,
    cost_usd DECIMAL(10,4)
);

CREATE INDEX idx_orders_platform_account ON orders(platform_account_id);
CREATE INDEX idx_orders_channel ON orders(channel_origin);
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_orders_expires ON orders(expires_at) WHERE expires_at IS NOT NULL;
CREATE INDEX idx_orders_created ON orders(created_at DESC);
```

---

### styxproxy_credentials

Maps Styxproxy-branded usernames to provider proxy IPs. This is the core of the auth layer.

```sql
CREATE TABLE styxproxy_credentials (
    id SERIAL PRIMARY KEY,

    -- Styxproxy username issued to customer
    bun_username VARCHAR(50) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,  -- bcrypt hash of the Styxproxy password

    -- Customer linkage (via platform_account, not directly to customer)
    platform_account_id UUID REFERENCES platform_accounts(id),
    order_id VARCHAR(20) REFERENCES orders(order_id),

    pool_type VARCHAR(20) DEFAULT 'paid',  -- 'paid', 'free_trial', 'refunded_recycled'

    -- The actual upstream proxy IP (from provider)
    provider_name VARCHAR(50),  -- 'Proxy-Seller', 'DataImpulse', 'Rayobyte'
    provider_order_id VARCHAR(100),
    provider_username VARCHAR(100),
    provider_password VARCHAR(100),
    upstream_proxy_ip INET,
    upstream_proxy_port INT DEFAULT 1080,

    -- Dante config
    dante_port INT,

    -- Status
    status VARCHAR(20) DEFAULT 'active',  -- 'active', 'expired', 'revoked', 'suspended'

    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ,  -- NULL = never expires (paid). Set for free trials.
    revoked_at TIMESTAMPTZ,
    revoke_reason VARCHAR(50),  -- 'refund', 'expiry', 'abuse', 'manual'

    last_used_at TIMESTAMPTZ,
    gb_used DECIMAL(10,2) DEFAULT 0
);

CREATE INDEX idx_styxproxy_cred_username ON styxproxy_credentials(bun_username);
CREATE INDEX idx_styxproxy_cred_platform_account ON styxproxy_credentials(platform_account_id);
CREATE INDEX idx_styxproxy_cred_status ON styxproxy_credentials(status);
CREATE INDEX idx_styxproxy_cred_pool ON styxproxy_credentials(pool_type, status);
CREATE INDEX idx_styxproxy_cred_expires ON styxproxy_credentials(expires_at)
    WHERE expires_at IS NOT NULL AND status = 'active';
```

---

### free_trials

Tracks free trial usage. One row per completed trial session (not per survey).

```sql
CREATE TABLE free_trials (
    id SERIAL PRIMARY KEY,

    platform_account_id UUID REFERENCES platform_accounts(id),
    channel_origin VARCHAR(20) NOT NULL,  -- 'telegram' or 'whatsapp'

    trial_date TIMESTAMPTZ DEFAULT NOW(),

    -- One row per session, not per survey
    -- surveys_completed is the count of survey postbacks recorded for this session
    surveys_completed INT DEFAULT 0,  -- how many surveys done (× 2hr each = total time)
    total_hours INT DEFAULT 0,  -- surveys_completed × 2

    -- Credential details (set once, when customer says "done")
    styxproxy_credential_id INT REFERENCES styxproxy_credentials(id),

    status VARCHAR(20) DEFAULT 'pending',  -- 'pending' (doing surveys), 'active' (creds sent), 'expired', 'dead'
    disclaimer_accepted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    fulfilled_at TIMESTAMPTZ  -- when credentials were sent
);

CREATE INDEX idx_free_trials_platform_account ON free_trials(platform_account_id, trial_date);
CREATE INDEX idx_free_trials_status ON free_trials(status);
```

### pending_trial_surveys

Records each Theorem Reach postback as it comes in. Customer accumulates surveys until they say "done."

```sql
CREATE TABLE pending_trial_surveys (
    id SERIAL PRIMARY KEY,

    platform_account_id UUID REFERENCES platform_accounts(id),
    channel_origin VARCHAR(20) NOT NULL,

    -- Theorem Reach postback data
    survey_transaction_id VARCHAR(100) UNIQUE NOT NULL,
    survey_user_id VARCHAR(50),
    survey_id VARCHAR(50),
    payout_usd DECIMAL(8,2),
    survey_completed_at TIMESTAMPTZ DEFAULT NOW(),

    -- Session linkage
    free_trial_id INT REFERENCES free_trials(id),

    -- Whether this survey has been counted toward a fulfilled trial
    credited BOOLEAN DEFAULT FALSE,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_pending_surveys_platform ON pending_trial_surveys(platform_account_id);
CREATE INDEX idx_pending_surveys_session ON pending_trial_surveys(free_trial_id);
CREATE INDEX idx_pending_surveys_uncredited ON pending_trial_surveys(credited) WHERE credited = FALSE;
```

---

### customer_audit_log

Immutable audit trail. Links to platform_account_id (not customer_id) so unmerged accounts have full history.

```sql
CREATE TABLE customer_audit_log (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    request_id VARCHAR(50),

    -- Link to platform account (preserves per-channel identity before merge)
    platform_account_id UUID REFERENCES platform_accounts(id),

    event_type VARCHAR(50),
    order_id VARCHAR(20),
    workflow VARCHAR(50),
    status VARCHAR(20),
    details JSONB
);

CREATE INDEX idx_audit_timestamp ON customer_audit_log(timestamp DESC);
CREATE INDEX idx_audit_platform_account ON customer_audit_log(platform_account_id);
CREATE INDEX idx_audit_event ON customer_audit_log(event_type, timestamp);
```

---

### error_log

```sql
CREATE TABLE error_log (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    workflow_name VARCHAR(50),
    node_name VARCHAR(50),
    error_type VARCHAR(50),
    error_message TEXT,
    error_stack TEXT,
    execution_id VARCHAR(50),
    platform_account_id UUID REFERENCES platform_accounts(id),
    order_id VARCHAR(20),
    severity VARCHAR(20),
    status VARCHAR(20) DEFAULT 'open',
    resolved_by VARCHAR(50),
    resolved_at TIMESTAMPTZ,
    resolution_notes TEXT
);

CREATE INDEX idx_error_severity ON error_log(severity, status);
CREATE INDEX idx_error_timestamp ON error_log(timestamp DESC);
CREATE INDEX idx_error_open ON error_log(status) WHERE status = 'open';
```

---

### provider_log

```sql
CREATE TABLE provider_log (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    provider VARCHAR(50),
    event_type VARCHAR(50),
    status VARCHAR(20),
    details TEXT,
    latency_ms INT,
    response_code VARCHAR(20)
);

CREATE INDEX idx_provider_timestamp ON provider_log(timestamp DESC);
CREATE INDEX idx_provider_status ON provider_log(provider, status);
CREATE INDEX idx_provider_health ON provider_log(event_type, timestamp) WHERE event_type = 'health_check';
```

---

### daily_summary

```sql
CREATE TABLE daily_summary (
    date DATE PRIMARY KEY,
    total_orders INT,
    total_revenue_ngn DECIMAL(12,2),
    total_errors INT,
    critical_errors INT,
    total_refunds INT,
    refund_amount_ngn DECIMAL(12,2),
    new_customers INT,
    free_trials_used INT,
    provider_downtime_min INT,
    credentials_active INT,
    credentials_free_trial INT
);
```

---

### processed_webhooks

Idempotency storage.

```sql
CREATE TABLE processed_webhooks (
    id BIGSERIAL PRIMARY KEY,
    webhook_id VARCHAR(100) UNIQUE NOT NULL,
    provider VARCHAR(20),
    event_type VARCHAR(50),
    processed_at TIMESTAMPTZ DEFAULT NOW(),
    response_sent BOOLEAN DEFAULT FALSE,
    metadata JSONB
);

CREATE INDEX idx_processed_webhooks_id ON processed_webhooks(webhook_id);
CREATE INDEX idx_processed_webhooks_cleanup ON processed_webhooks(processed_at)
    WHERE processed_at < NOW() - INTERVAL '90 days';
```

---

### admin_auth

```sql
CREATE TABLE admin_auth (
    admin_phone VARCHAR(20) PRIMARY KEY,
    pin_hash TEXT,
    pin_set_at TIMESTAMPTZ,
    totp_secret TEXT,
    totp_enabled BOOLEAN DEFAULT FALSE,
    totp_set_at TIMESTAMPTZ,
    failed_attempts INT DEFAULT 0,
    locked_until TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_used TIMESTAMPTZ
);

CREATE INDEX idx_admin_auth_locked ON admin_auth(locked_until) WHERE locked_until IS NOT NULL;
```

---

### admin_commands_log

```sql
CREATE TABLE admin_commands_log (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    admin_phone VARCHAR(20),
    command TEXT,
    risk_level VARCHAR(10),
    auth_method VARCHAR(20),
    auth_success BOOLEAN,
    execution_success BOOLEAN,
    error_message TEXT,
    metadata JSONB,
    session_id UUID,
    ip_address VARCHAR(45)
);

CREATE INDEX idx_admin_commands_timestamp ON admin_commands_log(timestamp DESC);
CREATE INDEX idx_admin_commands_admin ON admin_commands_log(admin_phone, timestamp);
CREATE INDEX idx_admin_commands_failures ON admin_commands_log(auth_success, timestamp)
    WHERE auth_success = FALSE;
```

---

### admin_sessions_log

```sql
CREATE TABLE admin_sessions_log (
    id BIGSERIAL PRIMARY KEY,
    session_id UUID,
    admin_phone VARCHAR(20),
    started_at TIMESTAMPTZ,
    ended_at TIMESTAMPTZ,
    duration_minutes INT,
    commands_used INT,
    ended_reason VARCHAR(50),
    ip_address VARCHAR(45)
);

CREATE INDEX idx_sessions_admin ON admin_sessions_log(admin_phone, started_at);
```

---

### rate_limit_log

```sql
CREATE TABLE rate_limit_log (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    layer VARCHAR(20),
    endpoint VARCHAR(50),
    identifier VARCHAR(100),
    identifier_type VARCHAR(10),  -- 'chat_id', 'phone_hash', 'ip'
    action VARCHAR(20),
    user_agent TEXT,
    request_id VARCHAR(50)
);

CREATE INDEX idx_rate_limit_timestamp ON rate_limit_log(timestamp DESC);
CREATE INDEX idx_rate_limit_blocks ON rate_limit_log(layer, action, timestamp) WHERE action != 'allowed';
CREATE INDEX idx_rate_limit_ip ON rate_limit_log(identifier_type, identifier) WHERE identifier_type = 'ip';
```

---

### webhook_security_log

```sql
CREATE TABLE webhook_security_log (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    provider VARCHAR(20),
    verified BOOLEAN,
    failure_reason TEXT,
    ip_address VARCHAR(45),
    user_agent TEXT,
    request_id VARCHAR(50)
);

CREATE INDEX idx_webhook_log_timestamp ON webhook_security_log(timestamp DESC);
CREATE INDEX idx_webhook_log_failures ON webhook_security_log(verified, timestamp) WHERE verified = FALSE;
```

---

## Data Retention

| Table | Retention |
|-------|-----------|
| customer_audit_log | 7 years (compliance) |
| orders | 7 years (financial records) |
| styxproxy_credentials | 7 years (credential audit trail) |
| error_log | 1 year |
| admin_commands_log | 1 year |
| admin_sessions_log | 1 year |
| provider_log | 90 days |
| processed_webhooks | 90 days |
| rate_limit_log | 90 days |
| webhook_security_log | 90 days |
| daily_summary | Indefinite |

---

## How Account Merging Works

### Step 1: Customer initiates link (from Telegram)

```
Customer (on Telegram): "Link my WhatsApp"
→ Bot asks: "Enter the phone number on your WhatsApp (with country code, e.g. 2347032981049)"
→ Customer types: "08031234567"
```

### Step 2: System creates merge request

```
System:
  1. Hash phone → look up platform_accounts where platform='whatsapp' and platform_user_id=hash(phone)
  2. If found:
     a. Generate 6-digit OTP
     b. Store merge_request with status='otp_sent'
     c. Send OTP to customer's WhatsApp via Styxproxy WhatsApp number
     d. Ask Telegram customer to enter OTP
  3. If NOT found:
     a. Tell customer: "No Styxproxy account found for that WhatsApp number. 
        Start an order on WhatsApp first, then come back to link."
```

### Step 3: OTP verification

```
Customer enters OTP on Telegram
→ System checks:
   - OTP matches
   - OTP not expired (10 min)
   - merge_request status is 'otp_sent'
→ If valid:
   a. Create customers record (if first merge)
   b. Update both platform_accounts: set customer_id = this customers.id
   c. Update merge_request status = 'completed'
   d. Tell customer: "✅ Your accounts are now linked! 
      Your WhatsApp and Telegram history is now together."
→ If invalid:
   a. Tell customer: "Wrong OTP. Try again or request a new one."
   b. Allow 3 attempts, then expire the request
```

### After merge

- Both platform_accounts now have the same `customer_id`
- Order history from both channels is visible under one profile
- `preferred_channel` field controls where follow-up messages go
- Customer can still message on either channel independently

---

## How Account Lookup Works

When a message comes in:

```
ON TELEGRAM (chat_id received):
  → Look up platform_accounts WHERE platform='telegram' AND platform_user_id='{chat_id}'
  → IF customer_id IS NOT NULL:
       Load customer + all their orders (both platforms)
       Process with full context
  → IF customer_id IS NULL:
       This is an unmerged Telegram account
       Create customers record + link (first-time flow)
       OR show "Link your WhatsApp?" prompt

ON WHATSAPP (phone hash received):
  → Look up platform_accounts WHERE platform='whatsapp' AND platform_user_id='{phone_hash}'
  → Same logic as above
```

---

## Setup Commands

```bash
# Install PostgreSQL
sudo apt update
sudo apt install postgresql postgresql-contrib

# Create database and user
sudo -u postgres psql

CREATE USER styxproxy WITH PASSWORD 'YOUR_STRONG_PASSWORD';
CREATE DATABASE styxproxy OWNER styxproxy;
GRANT ALL PRIVILEGES ON DATABASE styxproxy TO styxproxy;
\q

# Connect as styxproxy user
psql -U styxproxy -d styxproxy -h localhost

# Run schema (paste contents of this file)
\i schema.sql
```
