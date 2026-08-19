# Styxproxy — Database Schema (PostgreSQL)

**Last Updated:** 2026-08-19
**Status:** ACTUAL — reflects `backend/app/models.py` and Alembic migrations 001–021
**Authoritative source:** `backend/app/models.py`. This document is derived from it. If you find a discrepancy, the ORM model is always right — update this document to match.

> **This file was rewritten 2026-08-19.** The previous version (2026-07-01) had the table designs, not the actual implementation. It listed columns that were never created, omitted columns that exist, used wrong PKs, and had stale `bun_username` references. All tables below match `models.py` line-for-line.

---

## Overview

PostgreSQL database for the Styxproxy proxy platform. Each customer may have 0–2 platform accounts (Telegram, WhatsApp), linked via `platform_accounts`. Phone number is not the primary identity — each channel has its own platform account.

**Key design principle:** Not every Nigerian number has WhatsApp. Phone number cannot be the common identifier between channels. Instead, each platform (Telegram, WhatsApp) has its own account record. Customers can optionally merge them when they choose.

---

## Schema

### customers

Unified customer profile. Created when the first platform account is created, or when two platform accounts are merged. A customer may have 0, 1, or 2 platform accounts.

```sql
CREATE TABLE customers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Primary identity: phone number (unique, not nullable)
    phone VARCHAR(20) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    recovery_method VARCHAR(10),  -- 'telegram' | 'whatsapp'

    -- Auth
    pin_hash TEXT,
    blocked BOOLEAN DEFAULT FALSE NOT NULL,
    blocked_reason TEXT,

    -- Free trial tracking
    free_trials_used_today INT DEFAULT 0 NOT NULL,
    free_trial_offer_sent_today BOOLEAN DEFAULT FALSE NOT NULL,
    free_trial_offer_sent_at TIMESTAMPTZ,
    free_trial_declined_today BOOLEAN DEFAULT FALSE NOT NULL,

    -- Metrics (aggregated across all platforms after merge)
    total_orders INT DEFAULT 0 NOT NULL,
    lifetime_value_ngn DECIMAL(12,2) DEFAULT 0 NOT NULL,
    last_active_subscription TIMESTAMPTZ,
    last_message_at TIMESTAMPTZ,
    last_order_at TIMESTAMPTZ,
    replacement_count INT DEFAULT 0 NOT NULL,

    -- Consent
    consent_given BOOLEAN DEFAULT FALSE NOT NULL,
    consent_version VARCHAR(20),
    consent_at TIMESTAMPTZ,

    -- Support
    support_notes TEXT,

    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE INDEX idx_customers_phone ON customers(phone);
```

> **Note:** The `customers` table uses `id UUID PRIMARY KEY` (not `phone` as the old document stated). All FK references from other tables use `customers.phone` (String), not `customers.id` (UUID), for simplicity.

---

### platform_accounts

One row per platform per customer. A customer starts with one `platform_account`. After a merge, they have two.

**Critical rule:** `customer_id` is NULL until the account is merged. Before merge, the account exists independently.

```sql
CREATE TABLE platform_accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- NULL until accounts are merged
    customer_id UUID REFERENCES customers(id),

    -- Which platform
    platform VARCHAR(50) NOT NULL,

    -- Platform identity
    -- For Telegram: this is the Telegram chat_id (as string)
    -- For WhatsApp: this is the WhatsApp phone number hash (sha256[:20])
    platform_user_id VARCHAR(100) NOT NULL,

    -- Platform-specific extra data (JSON — flexible per-platform)
    extra_data JSONB,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,

    -- Primary flag (which account is primary for this customer)
    is_primary BOOLEAN DEFAULT FALSE NOT NULL,

    -- Anonymous device session: ties anonymous website orders to a specific browser
    -- via a UUID stored in localStorage on the client. No PII — just a UUID.
    device_id VARCHAR(64),

    -- Constraints
    UNIQUE(platform, platform_user_id)
);

CREATE INDEX idx_platform_device ON platform_accounts(device_id);
CREATE INDEX idx_platform_accounts_customer ON platform_accounts(customer_id);
```

---

### merge_requests

Tracks customer-initiated account linking. Customer asks to link Telegram ↔ WhatsApp. System sends OTP to the target platform. On verify, both platform_accounts get the same `customer_id`.

```sql
CREATE TABLE merge_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    source_account_id UUID NOT NULL REFERENCES platform_accounts(id),
    target_account_id UUID NOT NULL REFERENCES platform_accounts(id),

    status VARCHAR(20) DEFAULT 'pending' NOT NULL,
    requested_by UUID REFERENCES customers(id),
    approved_by UUID REFERENCES customers(id),

    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    completed_at TIMESTAMPTZ
);
```

---

### orders

Every proxy order. Linked to `platform_accounts` (not directly to customers — preserves per-platform context).

```sql
CREATE TABLE orders (
    order_id VARCHAR(20) PRIMARY KEY,

    -- Which platform account placed this order
    platform_account_id UUID REFERENCES platform_accounts(id),

    -- Customer phone (denormalised for fast lookups — also a FK to customers.phone)
    customer_phone VARCHAR(20) REFERENCES customers(phone),

    plan_type VARCHAR(20),
    plan_code VARCHAR(50),
    country VARCHAR(10),
    quantity INT,
    amount_paid_ngn DECIMAL(12,2),
    payment_reference VARCHAR(100),
    tx_ref VARCHAR(100),
    provider VARCHAR(50),
    provider_order_id VARCHAR(100),

    -- Styxproxy credential issued for this order
    styxproxy_credential_id INT REFERENCES styxproxy_credentials(id),

    status VARCHAR(50) DEFAULT 'pending' NOT NULL,
    ip_tested BOOLEAN DEFAULT FALSE NOT NULL,
    ip_test_result VARCHAR(10),  -- 'PASS', 'FAIL', 'N/A'

    -- Data tracking
    data_total_gb DECIMAL(10,2),
    data_remaining_gb DECIMAL(10,2),
    data_expires TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,

    -- Ban tracking
    ban_reported BOOLEAN DEFAULT FALSE NOT NULL,
    screenshot_url TEXT,
    ban_verified VARCHAR(50),
    replacement_count INT DEFAULT 0 NOT NULL,
    refund_requested BOOLEAN DEFAULT FALSE NOT NULL,
    refund_reason TEXT,
    notes TEXT,

    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    fulfilled_at TIMESTAMPTZ,
    cost_usd DECIMAL(10,4),

    -- Rotation mode: 'rotating' | 'static'
    rotation_mode VARCHAR(20),

    -- Sprint 13: city picker (residential/mobile orders)
    city_id INT REFERENCES cities(id) ON DELETE SET NULL,
    city_name VARCHAR(100)
);

CREATE INDEX idx_orders_customer ON orders(customer_phone);
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_orders_expires ON orders(expires_at);
CREATE INDEX idx_orders_created ON orders(created_at);
```

---

### styxproxy_credentials

Maps Styxproxy-branded usernames to provider proxy IPs. This is the core of the auth layer.

```sql
CREATE TABLE styxproxy_credentials (
    id SERIAL PRIMARY KEY,

    -- Styxproxy username issued to customer
    styxproxy_username VARCHAR(50) UNIQUE NOT NULL,

    -- Proxy auth credential — stored as encrypted bytes (Fernet ciphertext).
    -- Use get_password() / set_password() rather than touching this attribute
    -- directly.
    styxproxy_password BYTEA,

    -- Customer linkage (via customers.phone, not via platform_account)
    customer_phone VARCHAR(20) REFERENCES customers(phone),
    order_id VARCHAR(20) REFERENCES orders(order_id),

    pool_type VARCHAR(20) DEFAULT 'paid' NOT NULL,  -- 'paid', 'free_trial', 'refunded_recycled'
    protocol VARCHAR(10) DEFAULT 'socks5' NOT NULL,

    -- The actual upstream proxy IP (from provider)
    provider_name VARCHAR(50),
    provider_order_id VARCHAR(100),
    provider_username VARCHAR(100),
    provider_password VARCHAR(100),
    upstream_proxy_ip VARCHAR(255),  -- TEXT (was INET pre-migration 018)
    upstream_proxy_port INT DEFAULT 1080 NOT NULL,

    -- Dante config
    dante_port INT,

    -- Status
    status VARCHAR(20) DEFAULT 'active' NOT NULL,  -- 'active', 'expired', 'revoked', 'suspended'

    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    expires_at TIMESTAMPTZ,
    revoked_at TIMESTAMPTZ,
    revoke_reason VARCHAR(50),
    last_used_at TIMESTAMPTZ,
    gb_used DECIMAL(10,2) DEFAULT 0 NOT NULL,
    rotation_count INT DEFAULT 0 NOT NULL,

    -- Customer proxy management (added Jul 30)
    password_rotated_at TIMESTAMPTZ,
    password_rotations_today INT DEFAULT 0 NOT NULL,
    password_rotations_reset_at TIMESTAMPTZ,

    -- Targeting + sticky session
    country_target VARCHAR(2),
    sticky_session_minutes INT DEFAULT 0 NOT NULL,
    session_id VARCHAR(50),
    session_expires_at TIMESTAMPTZ,

    -- Bandwidth alerting
    bandwidth_alert_pct INT DEFAULT 80 NOT NULL,

    -- Last seen (for activity feeds)
    last_ip_country VARCHAR(2),
    last_ip_address VARCHAR(45),  -- IPv6 max 45 chars

    -- Rotation mode + static IP pinning (added Jul 30)
    rotation_mode VARCHAR(20) DEFAULT 'rotating' NOT NULL,  -- 'rotating' | 'static'
    assigned_static_ip VARCHAR(45),
    assigned_static_session_id VARCHAR(50),
    last_static_assigned_at TIMESTAMPTZ,

    -- Daily rate-limit counters (reset at UTC midnight)
    location_change_count INT DEFAULT 0 NOT NULL,
    rotation_mode_change_count INT DEFAULT 0 NOT NULL,
    location_changes_reset_at TIMESTAMPTZ,
    rotation_mode_changes_reset_at TIMESTAMPTZ
);

CREATE INDEX idx_styxproxy_cred_username ON styxproxy_credentials(styxproxy_username);
CREATE INDEX idx_styxproxy_cred_customer ON styxproxy_credentials(customer_phone);
CREATE INDEX idx_styxproxy_cred_status ON styxproxy_credentials(status);
CREATE INDEX idx_styxproxy_cred_pool ON styxproxy_credentials(pool_type);
CREATE INDEX idx_styxproxy_cred_expires ON styxproxy_credentials(expires_at)
    WHERE expires_at IS NOT NULL AND status = 'active';
CREATE INDEX idx_styxproxy_cred_protocol ON styxproxy_credentials(protocol);
```

---

### free_trials

Tracks free trial usage. One row per completed trial session (not per survey).

```sql
CREATE TABLE free_trials (
    id SERIAL PRIMARY KEY,

    phone VARCHAR(20) REFERENCES customers(phone),
    trial_date TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    survey_id VARCHAR(50),
    reward_usd DECIMAL(10,4),

    styxproxy_credential_id INT REFERENCES styxproxy_credentials(id),

    status VARCHAR(20),
    disclaimer_accepted BOOLEAN DEFAULT FALSE NOT NULL,

    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE INDEX idx_free_trials_phone_date ON free_trials(phone, trial_date);
CREATE INDEX idx_free_trials_status ON free_trials(status);
```

---

### pending_trial_surveys

Records each Theorem Reach postback as it comes in. Customer accumulates surveys until they say "done."

```sql
CREATE TABLE pending_trial_surveys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    free_trial_id INT REFERENCES free_trials(id),
    customer_id UUID REFERENCES customers(id),

    survey_token VARCHAR(100) UNIQUE NOT NULL,
    questions JSONB,
    responses JSONB,

    status VARCHAR(20) DEFAULT 'pending' NOT NULL,

    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    completed_at TIMESTAMPTZ
);
```

---

### customer_audit_log

Immutable audit trail. Uses `customer_hash` (SHA-256 of phone, first 20 chars) — irreversible, no PII.

```sql
CREATE TABLE customer_audit_log (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    request_id VARCHAR(50),

    -- Irreversible phone hash — preserves privacy, no FK possible
    customer_hash VARCHAR(20),

    event_type VARCHAR(50),
    order_id VARCHAR(20),
    workflow VARCHAR(50),
    status VARCHAR(20),
    details JSONB
);

CREATE INDEX idx_audit_timestamp ON customer_audit_log(timestamp);
CREATE INDEX idx_audit_customer ON customer_audit_log(customer_hash);
CREATE INDEX idx_audit_event ON customer_audit_log(event_type);
```

---

### processed_webhooks

Idempotency storage for payment webhooks.

```sql
CREATE TABLE processed_webhooks (
    id SERIAL PRIMARY KEY,
    webhook_id VARCHAR(100) UNIQUE NOT NULL,
    provider VARCHAR(20),
    event_type VARCHAR(50),
    processed_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    response_sent BOOLEAN DEFAULT FALSE NOT NULL,
    extra_data JSONB
);

CREATE INDEX idx_processed_webhooks_id ON processed_webhooks(webhook_id);
```

---

### admin_auth

Admin authentication. **PK is `id UUID`** — `admin_phone` is a legacy column retained for backward compatibility during migration.

```sql
CREATE TABLE admin_auth (
    -- UUID primary key (replaces old admin_phone PK)
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Legacy: retained for backward compat during migration
    admin_phone VARCHAR(20),

    -- Primary identity (unique, used for login)
    email VARCHAR(255),

    -- Password auth (replaces pin_hash)
    password_hash TEXT,

    -- Legacy: kept for migration path
    pin_hash TEXT,
    pin_set_at TIMESTAMPTZ,

    totp_secret TEXT,
    totp_enabled BOOLEAN DEFAULT FALSE NOT NULL,
    totp_set_at TIMESTAMPTZ,

    failed_attempts INT DEFAULT 0 NOT NULL,
    locked_until TIMESTAMPTZ,

    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    last_used TIMESTAMPTZ,

    -- Role column — source of truth for admin role
    role VARCHAR(20) DEFAULT 'admin' NOT NULL,  -- 'admin', 'superadmin', 'viewer'

    -- Password reset tokens
    reset_token_hash VARCHAR(255),
    reset_token_expires TIMESTAMPTZ
);

CREATE INDEX idx_admin_auth_locked ON admin_auth(locked_until) WHERE locked_until IS NOT NULL;
CREATE UNIQUE INDEX idx_admin_auth_email ON admin_auth(email);
```

---

### admin_invites

Invite codes for new admin registration.

```sql
CREATE TABLE admin_invites (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    invite_code VARCHAR(32) UNIQUE NOT NULL,
    email VARCHAR(255),
    role VARCHAR(20) DEFAULT 'admin' NOT NULL,  -- 'admin', 'superadmin', 'viewer'
    created_by VARCHAR(255),  -- email of admin who issued the invite
    expires_at TIMESTAMPTZ,
    used_at TIMESTAMPTZ,
    used_by VARCHAR(255),  -- email of admin who consumed the invite
    max_uses INT DEFAULT 1 NOT NULL,
    uses_count INT DEFAULT 0 NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    feature_overrides JSONB  -- list of feature-flag names granted by superadmin at invite time
);

CREATE INDEX idx_admin_invites_code ON admin_invites(invite_code);
CREATE INDEX idx_admin_invites_email ON admin_invites(email);
```

---

### admin_audit_log

Immutable audit trail for admin actions.

```sql
CREATE TABLE admin_audit_log (
    id SERIAL PRIMARY KEY,
    admin_phone VARCHAR(255),
    action VARCHAR(50) NOT NULL,
    ip_address VARCHAR(45),
    user_agent TEXT,
    details TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE INDEX idx_admin_audit_log_admin_phone ON admin_audit_log(admin_phone);
CREATE INDEX idx_admin_audit_log_action ON admin_audit_log(action);
```

---

### plans

Proxy plans with pricing for each country/type combo.

```sql
CREATE TABLE plans (
    id SERIAL PRIMARY KEY,
    plan_code VARCHAR(50) UNIQUE NOT NULL,
    plan_type VARCHAR(20) NOT NULL,  -- ISP, DC, RESIDENTIAL, MOBILE
    country VARCHAR(10) NOT NULL,
    price_ngn DECIMAL(12,2) NOT NULL,
    -- per-GB price for residential/mobile. NULL for DC/ISP (price_ngn is per-IP price).
    price_per_gb DECIMAL(10,2),
    quantity INT DEFAULT 1 NOT NULL,
    duration_days INT DEFAULT 30 NOT NULL,
    features JSONB,
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    sort_order INT DEFAULT 0 NOT NULL,

    -- Rotation + location flexibility (added Jul 30)
    rotation_mode VARCHAR(20) DEFAULT 'both' NOT NULL,  -- 'rotating' | 'static' | 'both'
    supports_country_change BOOLEAN DEFAULT TRUE NOT NULL,
    static_price_multiplier DECIMAL(4,2) DEFAULT 2.50 NOT NULL,

    -- Sprint 13: pricing model + city picker
    min_gb INT DEFAULT 5 NOT NULL,
    max_gb INT DEFAULT 50 NOT NULL,
    gb_tiers INT[],
    supports_city BOOLEAN DEFAULT FALSE NOT NULL,

    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE INDEX idx_plans_code ON plans(plan_code);
CREATE INDEX idx_plans_type_country ON plans(plan_type, country);
CREATE INDEX idx_plans_active ON plans(is_active);
```

---

### cities

Provider-supported cities per country (Sprint 13). Populated from Rayobyte's residential gateway.

```sql
CREATE TABLE cities (
    id SERIAL PRIMARY KEY,
    country_code VARCHAR(2) NOT NULL,
    city_name VARCHAR(100) NOT NULL,
    state_code VARCHAR(10),
    isp_name VARCHAR(100),
    latitude DECIMAL(9,6),
    longitude DECIMAL(9,6),
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    source VARCHAR(20) DEFAULT 'rayobyte',
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE INDEX idx_cities_country ON cities(country_code);
CREATE INDEX idx_cities_active ON cities(is_active);
```

---

### plan_cities

Plan ↔ City mapping (admin can restrict cities per plan).

```sql
CREATE TABLE plan_cities (
    plan_id INT REFERENCES plans(id) ON DELETE CASCADE,
    city_id INT REFERENCES cities(id) ON DELETE CASCADE,
    is_enabled BOOLEAN DEFAULT TRUE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    PRIMARY KEY (plan_id, city_id)
);
```

---

### trigger_events

Anonymous behavioral trigger firings.

```sql
CREATE TABLE trigger_events (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(64) NOT NULL,
    trigger_id VARCHAR(50) NOT NULL,
    fired_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    outcome VARCHAR(20) NOT NULL,  -- 'opened_chat' | 'dismissed' | 'ignored' | 'converted'
    charon_msg TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE INDEX idx_trigger_events_trigger_fired ON trigger_events(trigger_id, fired_at);
CREATE INDEX idx_trigger_events_session ON trigger_events(session_id);
```

---

### trigger_weights

Aggregate learning weights per trigger.

```sql
CREATE TABLE trigger_weights (
    trigger_id VARCHAR(50) PRIMARY KEY,
    weight DECIMAL(5,3) DEFAULT 1.0 NOT NULL,
    total_fires INT DEFAULT 0 NOT NULL,
    total_opens INT DEFAULT 0 NOT NULL,
    total_dismissed INT DEFAULT 0 NOT NULL,
    total_converted INT DEFAULT 0 NOT NULL,
    positive_rate DECIMAL(5,4) DEFAULT 0 NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);
```

---

### feature_flags

Toggle features globally or per-admin.

```sql
CREATE TABLE feature_flags (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    enabled BOOLEAN DEFAULT FALSE NOT NULL,
    enabled_for VARCHAR(20),  -- 'global' | 'admin' | NULL
    admin_overrides JSONB  -- JSON array of admin emails with individual overrides
);

CREATE INDEX idx_feature_flags_name ON feature_flags(name);
```

---

### contact_submissions

Contact form submissions.

```sql
CREATE TABLE contact_submissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    email VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    phone VARCHAR(20),
    tx_ref VARCHAR(40),
    status VARCHAR(20) DEFAULT 'pending' NOT NULL,
    admin_notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE INDEX idx_contact_submissions_created ON contact_submissions(created_at);
CREATE INDEX idx_contact_submissions_email ON contact_submissions(email);
```

---

### charon_escalations

Charon AI sales agent escalation table.

```sql
CREATE TABLE charon_escalations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id VARCHAR(100) NOT NULL,
    customer_email VARCHAR(255),
    customer_phone VARCHAR(20),
    customer_message TEXT NOT NULL,
    history_summary TEXT,
    status VARCHAR(20) DEFAULT 'pending' NOT NULL,
    admin_notes TEXT,
    resolved_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE INDEX idx_charon_escalations_conversation ON charon_escalations(conversation_id);
CREATE INDEX idx_charon_escalations_created ON charon_escalations(created_at);
```

---

### charon_context

Charon AI — per-conversation rolling summary. 24-hour TTL.

```sql
CREATE TABLE charon_context (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id VARCHAR(100) NOT NULL UNIQUE,
    session_id VARCHAR(100),
    customer_email VARCHAR(255),
    customer_phone VARCHAR(20),
    summary_json TEXT NOT NULL,
    message_count INT DEFAULT 0 NOT NULL,
    last_intent VARCHAR(255),
    last_topics VARCHAR(100)[],
    received_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX idx_charon_context_conversation ON charon_context(conversation_id);
CREATE INDEX idx_charon_context_expires ON charon_context(expires_at);
CREATE INDEX idx_charon_context_customer_email ON charon_context(customer_email);
```

---

### countries

ISO 3166-1 country reference table. Seeded with all 195 entries (see `scripts/seed_countries.py`).

```sql
CREATE TABLE countries (
    id SERIAL PRIMARY KEY,
    code VARCHAR(2) UNIQUE NOT NULL,
    code3 VARCHAR(3) UNIQUE NOT NULL,
    name VARCHAR(100) UNIQUE NOT NULL,
    flag_emoji VARCHAR(8) NOT NULL,
    region VARCHAR(50),
    subregion VARCHAR(50),
    plan_type_eligible BOOLEAN DEFAULT FALSE NOT NULL,
    is_supported BOOLEAN DEFAULT FALSE NOT NULL,
    proxy_pool VARCHAR(20),
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE INDEX idx_countries_supported ON countries(is_supported);
CREATE INDEX idx_countries_eligible ON countries(plan_type_eligible);
CREATE INDEX idx_countries_region ON countries(region);
```

---

### posts

Blog posts CMS with approval workflow.

```sql
CREATE TABLE posts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(255) NOT NULL,
    slug VARCHAR(255) UNIQUE NOT NULL,
    content TEXT NOT NULL,
    excerpt TEXT,
    cover_image_url TEXT,
    author VARCHAR(100) NOT NULL,
    -- Status: draft, pending, approved, rejected, published, archived
    status VARCHAR(20) DEFAULT 'draft' NOT NULL,
    -- Approval workflow
    submitted_at TIMESTAMPTZ,
    reviewed_by VARCHAR(20),
    reviewed_at TIMESTAMPTZ,
    rejection_reason TEXT,
    -- Scheduling
    scheduled_at TIMESTAMPTZ,
    published_at TIMESTAMPTZ,
    -- SEO
    meta_description TEXT,
    tags JSONB,
    -- Featured flag
    featured BOOLEAN DEFAULT FALSE NOT NULL,
    -- Counters
    view_count INT DEFAULT 0 NOT NULL,
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE INDEX idx_posts_slug ON posts(slug);
CREATE INDEX idx_posts_status ON posts(status);
CREATE INDEX idx_posts_published ON posts(published_at);
CREATE INDEX idx_posts_scheduled ON posts(scheduled_at);
```

---

### categories

Blog categories for organizing posts.

```sql
CREATE TABLE categories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    color VARCHAR(7),  -- Hex color
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE INDEX idx_categories_slug ON categories(slug);
```

---

### post_categories

Junction table for posts ↔ categories many-to-many relationship.

```sql
CREATE TABLE post_categories (
    post_id UUID REFERENCES posts(id) ON DELETE CASCADE,
    category_id UUID REFERENCES categories(id) ON DELETE CASCADE,
    PRIMARY KEY (post_id, category_id)
);
```

---

### support_threads

Tracks customer support conversations.

```sql
CREATE TABLE support_threads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_email VARCHAR(255) NOT NULL,
    customer_name VARCHAR(100),
    subject VARCHAR(500) NOT NULL,
    status VARCHAR(20) DEFAULT 'open' NOT NULL,  -- 'open', 'replied', 'closed'
    order_id VARCHAR(20) REFERENCES orders(order_id),
    resend_last_message_id VARCHAR(100),
    last_message_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE INDEX idx_support_threads_customer_email ON support_threads(customer_email);
CREATE INDEX idx_support_threads_status ON support_threads(status);
CREATE INDEX idx_support_threads_last_message ON support_threads(last_message_at);
```

---

### support_messages

Individual messages in support threads.

```sql
CREATE TABLE support_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    thread_id UUID NOT NULL REFERENCES support_threads(id) ON DELETE CASCADE,
    direction VARCHAR(20) NOT NULL,  -- 'inbound', 'outbound'
    from_email VARCHAR(255) NOT NULL,
    to_email VARCHAR(255) NOT NULL,
    subject VARCHAR(500) NOT NULL,
    body_text TEXT,
    body_html TEXT,
    resend_id VARCHAR(100),
    in_reply_to VARCHAR(255),
    references TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE INDEX idx_support_messages_thread ON support_messages(thread_id);
CREATE INDEX idx_support_messages_created ON support_messages(created_at);
```

---

### health_snapshots

Time-series of system health probes. Written by cron job every minute.

```sql
CREATE TABLE health_snapshots (
    id SERIAL PRIMARY KEY,
    db_connected BOOLEAN NOT NULL DEFAULT FALSE,
    redis_connected BOOLEAN NOT NULL DEFAULT FALSE,
    m2_connected BOOLEAN NOT NULL DEFAULT FALSE,
    litellm_connected BOOLEAN NOT NULL DEFAULT FALSE,
    ollama_connected BOOLEAN NOT NULL DEFAULT FALSE,
    overall_status VARCHAR(20) NOT NULL DEFAULT 'unknown',
    charon_available BOOLEAN NOT NULL DEFAULT FALSE,
    total_latency_ms DECIMAL(10,2),
    error_summary TEXT,
    source VARCHAR(20) NOT NULL DEFAULT 'cron',
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE INDEX idx_health_snapshots_created ON health_snapshots(created_at);
```

---

### admin_permissions

Permission code catalog (Theme C).

```sql
CREATE TABLE admin_permissions (
    id SERIAL PRIMARY KEY,
    code VARCHAR(64) UNIQUE NOT NULL,
    category VARCHAR(50) NOT NULL,
    description TEXT NOT NULL,
    is_sensitive BOOLEAN DEFAULT FALSE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE INDEX idx_admin_permissions_category ON admin_permissions(category);
```

---

### admin_role_permissions

Role → permission defaults (superadmin/admin/viewer).

```sql
CREATE TABLE admin_role_permissions (
    id SERIAL PRIMARY KEY,
    role VARCHAR(20) NOT NULL,
    permission_code VARCHAR(64) NOT NULL,
    granted BOOLEAN DEFAULT TRUE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE INDEX idx_admin_role_permissions_role ON admin_role_permissions(role);
```

---

### admin_user_permissions

Per-admin permission overrides.

```sql
CREATE TABLE admin_user_permissions (
    id SERIAL PRIMARY KEY,
    admin_email VARCHAR(255) NOT NULL,
    permission_code VARCHAR(64) NOT NULL,
    granted BOOLEAN DEFAULT TRUE NOT NULL,
    granted_by VARCHAR(255) NOT NULL,
    granted_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    expires_at TIMESTAMPTZ,
    notes TEXT
);

CREATE INDEX idx_admin_user_permissions_email ON admin_user_permissions(admin_email);
```

---

### permission_change_requests

Permission request workflow (Theme C).

```sql
CREATE TABLE permission_change_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    requested_by VARCHAR(255) NOT NULL,
    target_email VARCHAR(255),
    target_role VARCHAR(20),
    permission_code VARCHAR(64) NOT NULL,
    desired_state BOOLEAN NOT NULL,
    justification TEXT NOT NULL,
    status VARCHAR(20) DEFAULT 'pending' NOT NULL,
    reviewed_by VARCHAR(255),
    reviewed_at TIMESTAMPTZ,
    reviewer_notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX idx_pcr_status ON permission_change_requests(status);
CREATE INDEX idx_pcr_target_email ON permission_change_requests(target_email);
CREATE INDEX idx_pcr_target_role ON permission_change_requests(target_role);
```

---

### idempotency_responses

Caches POST handler responses by key hash. Created via raw SQL on startup (see `idempotency.py`). The ORM model is for type-safe queries only; table creation is managed by the raw SQL.

```sql
CREATE TABLE idempotency_responses (
    key_hash VARCHAR(64) PRIMARY KEY,
    status_code INT,
    response_body TEXT,
    response_headers TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL
);
```

---

## Data Retention

| Table | Retention |
|-------|-----------|
| customer_audit_log | 7 years (compliance) |
| orders | 7 years (financial records) |
| styxproxy_credentials | 7 years (credential audit trail) |
| charon_context | 24 hours (TTL enforced by cleanup cron) |
| error_log | 1 year |
| admin_audit_log | 1 year |
| health_snapshots | 7 days |
| provider_log | 90 days |
| processed_webhooks | 90 days |
| permission_change_requests | 7 days (auto-expire) |
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

CREATE USER styxproxy_app WITH PASSWORD 'YOUR_STRONG_PASSWORD';
CREATE DATABASE styxproxy OWNER styxproxy_app;
GRANT ALL PRIVILEGES ON DATABASE styxproxy TO styxproxy_app;
\q

# Run Alembic migrations
cd backend
alembic upgrade head

# Verify
psql -U styxproxy_app -d styxproxy -h localhost -c "\dt"
```
