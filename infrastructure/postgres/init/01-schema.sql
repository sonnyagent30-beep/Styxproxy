-- ─────────────────────────────────────────────────────────
-- Bunche — PostgreSQL Schema
-- Version: 1.0
-- ─────────────────────────────────────────────────────────

BEGIN;

-- ── ENUM Types ────────────────────────────────────────────
CREATE TYPE order_status AS ENUM (
  'pending', 'paid', 'processing', 'fulfilled', 'failed', 'refunded'
);

CREATE TYPE product_category AS ENUM (
  'ISP', 'RESIDENTIAL', 'DATACENTER', 'MOBILE'
);

CREATE TYPE support_ticket_status AS ENUM (
  'open', 'in_progress', 'resolved', 'closed'
);

-- ── Customers ─────────────────────────────────────────────
CREATE TABLE customers (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  phone       VARCHAR(20) UNIQUE NOT NULL,
  email       VARCHAR(255) UNIQUE,
  name        VARCHAR(255),
  referrer_id UUID REFERENCES customers(id),
  created_at  TIMESTAMPTZ DEFAULT NOW(),
  updated_at  TIMESTAMPTZ DEFAULT NOW(),
  is_active   BOOLEAN DEFAULT TRUE
);

CREATE INDEX idx_customers_phone ON customers(phone);
CREATE INDEX idx_customers_referrer ON customers(referrer_id);

-- ── Products / Proxy SKUs ────────────────────────────────
CREATE TABLE products (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  sku          VARCHAR(50) UNIQUE NOT NULL,
  name         VARCHAR(255) NOT NULL,
  category     product_category NOT NULL,
  description  TEXT,
  buy_cost_usd NUMERIC(10,4) NOT NULL,
  sell_price   NUMERIC(12,2) NOT NULL,
  stock_qty    INTEGER DEFAULT 0,
  is_active    BOOLEAN DEFAULT TRUE,
  created_at   TIMESTAMPTZ DEFAULT NOW(),
  updated_at   TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_products_sku ON products(sku);
CREATE INDEX idx_products_category ON products(category);

-- ── Proxy Credentials ─────────────────────────────────────
CREATE TABLE proxy_credentials (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  product_id    UUID REFERENCES products(id) ON DELETE SET NULL,
  ip_address    INET,
  port          INTEGER,
  username      VARCHAR(255),
  password_hash VARCHAR(255),
  protocol      VARCHAR(10) DEFAULT 'http',
  country_code  CHAR(2),
  provider      VARCHAR(50),
  provider_ref  VARCHAR(255),
  is_active     BOOLEAN DEFAULT TRUE,
  assigned_at   TIMESTAMPTZ,
  expires_at    TIMESTAMPTZ,
  created_at    TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_proxy_product ON proxy_credentials(product_id);
CREATE INDEX idx_proxy_active ON proxy_credentials(is_active) WHERE is_active = TRUE;
CREATE INDEX idx_proxy_ip ON proxy_credentials(ip_address) WHERE ip_address IS NOT NULL;

-- ── Orders ────────────────────────────────────────────────
CREATE TABLE orders (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  customer_id         UUID REFERENCES customers(id) ON DELETE SET NULL,
  product_id          UUID REFERENCES products(id) ON DELETE SET NULL,
  status              order_status DEFAULT 'pending',
  quantity            INTEGER DEFAULT 1,
  amount              NUMERIC(12,2) NOT NULL,
  provider_cost_usd   NUMERIC(10,4),
  currency            CHAR(3) DEFAULT 'NGN',
  flutterwave_ref     VARCHAR(100) UNIQUE,
  provider_order_id   VARCHAR(255),
  delivered_creds     UUID[],
  created_at          TIMESTAMPTZ DEFAULT NOW(),
  updated_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_orders_customer ON orders(customer_id);
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_orders_flutterwave ON orders(flutterwave_ref);
CREATE INDEX idx_orders_created ON orders(created_at DESC);

-- ── Transactions (immutable ledger) ──────────────────────
CREATE TABLE transactions (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  order_id    UUID REFERENCES orders(id),
  type        VARCHAR(20) NOT NULL,
  amount      NUMERIC(12,2) NOT NULL,
  currency    CHAR(3) DEFAULT 'NGN',
  provider    VARCHAR(50),
  reference   VARCHAR(255),
  metadata    JSONB,
  created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_transactions_order ON transactions(order_id);
CREATE INDEX idx_transactions_created ON transactions(created_at DESC);

-- ── Support Tickets ───────────────────────────────────────
CREATE TABLE support_tickets (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  customer_id UUID REFERENCES customers(id) ON DELETE SET NULL,
  order_id    UUID REFERENCES orders(id) ON DELETE SET NULL,
  subject     VARCHAR(500) NOT NULL,
  body        TEXT,
  status      support_ticket_status DEFAULT 'open',
  priority    VARCHAR(10) DEFAULT 'normal',
  assigned_to VARCHAR(255),
  created_at  TIMESTAMPTZ DEFAULT NOW(),
  updated_at  TIMESTAMPTZ DEFAULT NOW(),
  resolved_at TIMESTAMPTZ
);

CREATE INDEX idx_tickets_customer ON support_tickets(customer_id);
CREATE INDEX idx_tickets_status ON support_tickets(status);
CREATE INDEX idx_tickets_created ON support_tickets(created_at DESC);

-- ── System Events (audit log) ─────────────────────────────
CREATE TABLE system_events (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  event_type VARCHAR(50) NOT NULL,
  actor      VARCHAR(255),
  subject_id UUID,
  payload    JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_events_type ON system_events(event_type);
CREATE INDEX idx_events_created ON system_events(created_at DESC);
CREATE INDEX idx_events_subject ON system_events(subject_id);

-- ── Updated_at trigger ───────────────────────────────────
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_customers_updated_at   BEFORE UPDATE ON customers          FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trg_products_updated_at    BEFORE UPDATE ON products           FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trg_orders_updated_at       BEFORE UPDATE ON orders            FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trg_support_tickets_updated_at BEFORE UPDATE ON support_tickets FOR EACH ROW EXECUTE FUNCTION update_updated_at();

COMMIT;
