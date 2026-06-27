# Bunche — Database Schema (PostgreSQL)

**Last Updated:** 2026-06-27  
**Status:** Planning Complete — Ready for Implementation

---

## Overview

Replaces Google Sheets with self-hosted PostgreSQL for scalability and reliability. Includes the `bunche_credentials` table for mapping Bunche usernames to provider IPs via the Dante auth layer.

---

## Schema

### customers

Primary identity table. Phone number is the primary key (no account creation).

```sql
CREATE TABLE customers (
    phone VARCHAR(20) PRIMARY KEY,
    name VARCHAR(100),
    recovery_method VARCHAR(10),  -- 'PIN' or 'OTP'
    pin_hash TEXT,  -- bcrypt hash of recovery PIN
    created_at TIMESTAMPTZ DEFAULT NOW(),
    blocked BOOLEAN DEFAULT FALSE,
    blocked_reason TEXT,
    
    -- Free trial tracking
    free_trials_used_today INT DEFAULT 0,
    free_trial_offer_sent_today BOOLEAN DEFAULT FALSE,
    free_trial_offer_sent_at TIMESTAMPTZ,
    free_trial_declined_today BOOLEAN DEFAULT FALSE,
    
    -- Metrics
    total_orders INT DEFAULT 0,
    lifetime_value_ngn DECIMAL(12,2) DEFAULT 0,
    last_active_subscription TIMESTAMPTZ,
    last_message_at TIMESTAMPTZ,
    last_order_at TIMESTAMPTZ,
    replacement_count INT DEFAULT 0,
    
    -- Consent
    consent_given BOOLEAN DEFAULT FALSE,
    consent_version VARCHAR(20),
    consent_at TIMESTAMPTZ,
    support_notes TEXT
);

CREATE INDEX idx_customers_blocked ON customers(blocked);
CREATE INDEX idx_customers_last_message ON customers(last_message_at);
```

---

### bunche_credentials

Maps Bunche-branded usernames to provider proxy IPs. This is the core of the auth layer.

```sql
CREATE TABLE bunche_credentials (
    id SERIAL PRIMARY KEY,
    
    -- Bunche username issued to customer
    bun_username VARCHAR(50) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,  -- bcrypt hash of the Bunche password
    
    -- Customer linkage
    customer_phone VARCHAR(20) REFERENCES customers(phone),
    order_id VARCHAR(20) REFERENCES orders(order_id),
    
    -- Pool type: 'paid', 'free_trial', 'refunded_recycled'
    pool_type VARCHAR(20) DEFAULT 'paid',
    
    -- The actual upstream proxy IP (from provider)
    provider_name VARCHAR(50),  -- 'Proxy-Seller', 'DataImpulse', 'Rayobyte'
    provider_order_id VARCHAR(100),  -- order ID from provider
    provider_username VARCHAR(100),  -- username from provider (for auth)
    provider_password VARCHAR(100),  -- password from provider (for auth)
    upstream_proxy_ip INET,  -- e.g. 185.199.228.45
    upstream_proxy_port INT DEFAULT 1080,
    
    -- Dante config
    dante_port INT,  -- Dante listens on this port for this user
    
    -- Status
    status VARCHAR(20) DEFAULT 'active',  -- 'active', 'expired', 'revoked', 'suspended'
    
    -- Tracking
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ,  -- NULL = never expires (paid). Set for free trials.
    revoked_at TIMESTAMPTZ,
    revoke_reason VARCHAR(50),  -- 'refund', 'expiry', 'abuse', 'manual'
    
    -- For free trial recycling
    last_used_at TIMESTAMPTZ,
    gb_used DECIMAL(10,2) DEFAULT 0  -- for data-based products
);

CREATE INDEX idx_bunche_cred_username ON bunche_credentials(bun_username);
CREATE INDEX idx_bunche_cred_customer ON bunche_credentials(customer_phone);
CREATE INDEX idx_bunche_cred_status ON bunche_credentials(status);
CREATE INDEX idx_bunche_cred_pool ON bunche_credentials(pool_type, status);
CREATE INDEX idx_bunche_cred_expires ON bunche_credentials(expires_at) 
    WHERE expires_at IS NOT NULL AND status = 'active';
```

---

### orders

Every proxy order. Linked to customers by phone and to bunche_credentials.

```sql
CREATE TABLE orders (
    order_id VARCHAR(20) PRIMARY KEY,
    customer_phone VARCHAR(20) REFERENCES customers(phone),
    plan_type VARCHAR(20),  -- 'ISP', 'DC', 'RESIDENTIAL', 'MOBILE'
    plan_code VARCHAR(50),
    country VARCHAR(10),
    quantity INT,
    amount_paid_ngn DECIMAL(12,2),
    payment_reference VARCHAR(100),
    provider VARCHAR(50),  -- 'Proxy-Seller', 'DataImpulse', 'Rayobyte'
    provider_order_id VARCHAR(100),
    
    -- Bunche credential issued for this order
    bunche_credential_id INT REFERENCES bunche_credentials(id),
    
    status VARCHAR(50),  -- 'pending', 'paid', 'fulfilled', 'active', 'expired', 'cancelled', 'refunded'
    ip_tested BOOLEAN DEFAULT FALSE,
    ip_test_result VARCHAR(10),  -- 'PASS', 'FAIL', 'N/A'
    
    -- Data tracking (for RESIDENTIAL and MOBILE)
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
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    fulfilled_at TIMESTAMPTZ,
    cost_usd DECIMAL(10,4)
);

CREATE INDEX idx_orders_customer ON orders(customer_phone);
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_orders_expires ON orders(expires_at) WHERE expires_at IS NOT NULL;
CREATE INDEX idx_orders_data_expires ON orders(data_expires) WHERE data_expires IS NOT NULL;
CREATE INDEX idx_orders_created ON orders(created_at DESC);
```

---

### free_trials

Tracks free trial usage. Linked to bunche_credentials for the credential lifecycle.

```sql
CREATE TABLE free_trials (
    id SERIAL PRIMARY KEY,
    phone VARCHAR(20) REFERENCES customers(phone),
    trial_date TIMESTAMPTZ DEFAULT NOW(),
    survey_id VARCHAR(50),
    reward_usd DECIMAL(10,4),
    
    -- Link to the Bunche credential (for 2hr TTL tracking)
    bunche_credential_id INT REFERENCES bunche_credentials(id),
    
    status VARCHAR(20),  -- 'active', 'expired', 'dead'
    disclaimer_accepted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_free_trials_phone_date ON free_trials(phone, trial_date);
CREATE INDEX idx_free_trials_status ON free_trials(status);
```

---

### customer_audit_log

Immutable audit trail. PII is hashed — never store plain phone/name.

```sql
CREATE TABLE customer_audit_log (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    request_id VARCHAR(50),
    customer_hash VARCHAR(20),  -- sha256(phone)[:20]
    event_type VARCHAR(50),
    order_id VARCHAR(20),
    workflow VARCHAR(50),
    status VARCHAR(20),
    details JSONB
);

CREATE INDEX idx_audit_timestamp ON customer_audit_log(timestamp DESC);
CREATE INDEX idx_audit_customer ON customer_audit_log(customer_hash);
CREATE INDEX idx_audit_event ON customer_audit_log(event_type, timestamp);
```

---

### error_log

System errors with severity classification.

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
    customer_hash VARCHAR(20),
    order_id VARCHAR(20),
    severity VARCHAR(20),
    status VARCHAR(20),
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

Tracks provider API health and performance.

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

Aggregated metrics per day.

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

Idempotency storage. Prevents duplicate webhook processing.

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

Admin authentication and lockout state.

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

Audit trail of all admin actions.

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

Session history for audit and security.

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

Tracks rate limiting events for monitoring and analysis.

```sql
CREATE TABLE rate_limit_log (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    layer VARCHAR(20),
    endpoint VARCHAR(50),
    identifier VARCHAR(100),
    identifier_type VARCHAR(10),
    action VARCHAR(20),
    user_agent TEXT,
    request_id VARCHAR(50)
);

CREATE INDEX idx_rate_limit_timestamp ON rate_limit_log(timestamp DESC);
CREATE INDEX idx_rate_limit_blocks ON rate_limit_log(layer, action, timestamp) 
    WHERE action != 'allowed';
CREATE INDEX idx_rate_limit_ip ON rate_limit_log(identifier_type, identifier) 
    WHERE identifier_type = 'ip';
```

---

### webhook_security_log

Tracks webhook verification attempts.

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
CREATE INDEX idx_webhook_log_failures ON webhook_security_log(verified, timestamp) 
    WHERE verified = FALSE;
```

---

## Data Retention

| Table | Retention |
|-------|-----------|
| customer_audit_log | 7 years (compliance) |
| error_log | 1 year |
| provider_log | 90 days |
| processed_webhooks | 90 days |
| admin_commands_log | 1 year |
| admin_sessions_log | 1 year |
| rate_limit_log | 90 days |
| webhook_security_log | 90 days |
| daily_summary | Indefinite |
| orders | 7 years (financial records) |
| bunche_credentials | 7 years (credential audit trail) |
| customers | Until deleted |

---

## PII Handling

**Rule: Never store plain PII in logs. Always hash first.**

```javascript
// Hash phone before logging
const phoneHash = crypto.createHash('sha256').update(phone).digest('hex').substring(0, 20);

// Hash IP before logging (if needed)
const ipHash = crypto.createHash('sha256').update(ip).digest('hex').substring(0, 20);

// Never log:
// - Plain phone number
// - Plain IP address
// - Plain names
// - PIN or OTP codes
// - Proxy credentials (use password_hash only)
// - API keys or secrets
```

---

## How bunche_credentials Works with Dante

When a customer order is fulfilled:

1. n8n calls provider API → gets provider IP + credentials
2. n8n inserts row into `bunche_credentials` with Bunche username/password
3. n8n calls `manage-bunche-credentials.sh add USERNAME PASSWORD`
4. Dante is reloaded with new user
5. Customer receives Bunche-branded credentials

When a refund happens:

1. Admin approves refund in Flutterwave
2. n8n updates `bunche_credentials.status = 'revoked'`, `revoke_reason = 'refund'`
3. n8n calls `manage-bunche-credentials.sh revoke USERNAME`
4. Dante reloads — old credentials no longer work
5. Credential moved to free_trial pool with new temp password

---

## Setup Commands

```bash
# Install PostgreSQL
sudo apt update
sudo apt install postgresql postgresql-contrib

# Create database and user
sudo -u postgres psql

CREATE USER bunche WITH PASSWORD 'YOUR_STRONG_PASSWORD';
CREATE DATABASE bunche OWNER bunche;
GRANT ALL PRIVILEGES ON DATABASE bunche TO bunche;
\q

# Connect as bunche user
psql -U bunche -d bunche -h localhost

# Run schema (paste contents of this file)
\i schema.sql
```
