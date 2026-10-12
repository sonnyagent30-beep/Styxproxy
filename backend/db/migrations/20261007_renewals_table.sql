-- 2026-10-07  Renewal feature — add renewals table
--
-- Tracks renewal orders for existing proxy subscriptions.
-- Each renewal links to an original order. For residential/mobile,
-- a new credential is created for the extra GB. For DC/ISP, only expiry extends.

CREATE TABLE IF NOT EXISTS renewals (
    id SERIAL PRIMARY KEY,
    order_id VARCHAR(20) NOT NULL REFERENCES orders(order_id),
    quantity_gb NUMERIC(10, 2),
    amount_paid_ngn NUMERIC(12, 2) NOT NULL,
    payment_reference VARCHAR(100),
    tx_ref VARCHAR(100),
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    credential_id INTEGER REFERENCES styxproxy_credentials(id),
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_renewals_order_id ON renewals(order_id);
CREATE INDEX IF NOT EXISTS idx_renewals_payment_reference ON renewals(payment_reference);
CREATE INDEX IF NOT EXISTS idx_renewals_tx_ref ON renewals(tx_ref);
CREATE INDEX IF NOT EXISTS idx_renewals_status ON renewals(status);
