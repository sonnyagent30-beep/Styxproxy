# Bunche — Database Schema (PostgreSQL)

**Last Updated:** 2026-06-26  
**Status:** Planning Complete — Ready for Implementation

---

## Overview

Replaces Google Sheets with self-hosted PostgreSQL for scalability and reliability.

**Why PostgreSQL over Google Sheets:**
- 100x faster (5ms vs 1500ms per read)
- Handles 10,000+ concurrent users
- Proper transactions (no race conditions)
- Full indexing and query optimization
- $0 cost (self-hosted on VPS)

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

### orders

Every proxy order. Linked to customers by phone.

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
    provider VARCHAR(50),  -- 'Proxy-Seller', 'DataImpulse', 'Geonode'
    provider_order_id VARCHAR(100),
    proxy_credentials TEXT,  -- IP:Port:User:Pass (encrypted)
    status VARCHAR(50),  -- 'pending', 'paid', 'fulfilled', 'active', 'expired', 'cancelled', 'refunded'
    ip_tested BOOLEAN DEFAULT FALSE,
    ip_test_result VARCHAR(10),  -- 'PASS', 'FAIL', 'N/A'
    
    -- Data tracking (for RESIDENTIAL and MOBILE)
    data_total_gb DECIMAL(10,2),
    data_remaining_gb DECIMAL(10,2),
    data_expires TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,  -- Normalized to earliest for same-order items
    
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

Tracks free trial usage and proxy delivery.

```sql
CREATE TABLE free_trials (
    id SERIAL PRIMARY KEY,
    phone VARCHAR(20) REFERENCES customers(phone),
    trial_date TIMESTAMPTZ DEFAULT NOW(),
    survey_id VARCHAR(50),
    reward_usd DECIMAL(10,4),
    proxy_ip TEXT,
    proxy_port INT,
    status VARCHAR(20),  -- 'active', 'dead'
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
    request_id VARCHAR(50),  -- Correlation ID from WhatsApp
    customer_hash VARCHAR(20),  -- sha256(phone)[:20]
    event_type VARCHAR(50),  -- 'order_placed', 'payment_received', 'proxy_delivered', etc.
    order_id VARCHAR(20),
    workflow VARCHAR(50),  -- Which n8n workflow handled this
    status VARCHAR(20),  -- 'success', 'failure'
    details JSONB  -- Additional context (PII hashed)
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
    error_type VARCHAR(50),  -- 'provider_down', 'payment_failed', 'ip_test_failed', etc.
    error_message TEXT,
    error_stack TEXT,
    execution_id VARCHAR(50),
    customer_hash VARCHAR(20),
    order_id VARCHAR(20),
    severity VARCHAR(20),  -- 'critical', 'high', 'medium', 'low'
    status VARCHAR(20),  -- 'open', 'investigating', 'resolved', 'ignored'
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
    provider VARCHAR(50),  -- 'Proxy-Seller', 'DataImpulse', 'Geonode', 'CPAGrip'
    event_type VARCHAR(50),  -- 'health_check', 'order', 'replacement', 'api_error'
    status VARCHAR(20),  -- 'success', 'failure'
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
    provider_downtime_min INT
);
```

---

### processed_webhooks

Idempotency storage. Prevents duplicate webhook processing.

```sql
CREATE TABLE processed_webhooks (
    id BIGSERIAL PRIMARY KEY,
    webhook_id VARCHAR(100) UNIQUE NOT NULL,  -- tx_ref, message_id, etc.
    provider VARCHAR(20),  -- 'flutterwave', 'whatsapp', 'cpagrip'
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
    pin_hash TEXT,  -- bcrypt hash
    pin_set_at TIMESTAMPTZ,
    totp_secret TEXT,  -- AES-256-GCM encrypted
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
    risk_level VARCHAR(10),  -- 'low', 'medium', 'high'
    auth_method VARCHAR(20),  -- 'none', 'pin', 'pin_totp'
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
    ended_reason VARCHAR(50),  -- 'logout', 'timeout', 'lockout'
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
    layer VARCHAR(20),  -- 'cloudflare', 'nginx', 'redis'
    endpoint VARCHAR(50),
    identifier VARCHAR(100),  -- IP or phone hash
    identifier_type VARCHAR(10),  -- 'ip' or 'phone'
    action VARCHAR(20),  -- 'allowed', 'blocked', 'challenged'
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
    provider VARCHAR(20),  -- 'whatsapp', 'flutterwave', 'cpagrip'
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
// - Proxy credentials
// - API keys or secrets
```

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

---

## Migration from Google Sheets

```python
# migrate_sheets_to_postgres.py
import psycopg2
from googleapiclient.discovery import build

# Read all sheets
sheets_service = build('sheets', 'v4', credentials=creds)

# Connect to PostgreSQL
conn = psycopg2.connect(
    host='localhost',
    database='bunche',
    user='bunche',
    password='YOUR_PASSWORD'
)
cur = conn.cursor()

# Migrate customers
result = sheets_service.spreadsheets().values().get(
    spreadsheetId='YOUR_SHEET_ID',
    range='Customers!A:Z'
).execute()

for row in result.get('values', [])[1:]:
    cur.execute("""
        INSERT INTO customers (phone, name, recovery_method, created_at, ...)
        VALUES (%s, %s, %s, %s, ...)
        ON CONFLICT (phone) DO NOTHING
    """, row)

conn.commit()
cur.close()
conn.close()
```
