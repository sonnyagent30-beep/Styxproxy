-- Migration 021: Pricing model + city picker
-- Adds:
--   1. plans.price_per_gb  — for per-GB plans (residential/mobile)
--   2. cities              — provider-supported cities per country
--   3. plan_cities         — admin-managed mapping of cities per plan
--
-- User directive (Jul 30 2026):
--   - Residential = per-GB (customer picks country + city, or random)
--   - Mobile      = per-GB (same model)
--   - Datacenter  = per-IP (admin sets per-country)
--   - ISP         = per-IP (admin sets per-country)
--
-- Backwards compatibility:
--   - plans.price_ngn stays for per-IP plans (DC/ISP)
--   - plans.price_per_gb is the per-GB price for residential/mobile
--   - NOT NULL constraint added via migration 022 after backfill

BEGIN;

-- 1. Add price_per_gb column (nullable initially — backfilled below)
ALTER TABLE plans ADD COLUMN IF NOT EXISTS price_per_gb NUMERIC(10,2);

-- 2. Cities table: provider-supported cities per country
--    Populated from Rayobyte's residential gateway (https://residential.rayobyte.com)
--    for residential plans. Customers can pick a city for exact targeting or
--    skip (="random") to get a pool IP from the country.
CREATE TABLE IF NOT EXISTS cities (
    id              SERIAL PRIMARY KEY,
    country_code    VARCHAR(2) NOT NULL,                -- ISO 3166-1 alpha-2
    city_name       VARCHAR(100) NOT NULL,              -- e.g. "London", "Lagos"
    state_code      VARCHAR(10),                       -- e.g. "CA", "TX" (US states)
    isp_name        VARCHAR(100),                      -- e.g. "BT", "Verizon", "MTN"
    latitude        NUMERIC(9,6),
    longitude       NUMERIC(9,6),
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    source          VARCHAR(20) DEFAULT 'rayobyte',    -- 'rayobyte', 'admin', 'manual'
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (country_code, city_name, state_code)
);

CREATE INDEX IF NOT EXISTS idx_cities_country ON cities(country_code);
CREATE INDEX IF NOT EXISTS idx_cities_active ON cities(is_active);

-- 3. Plan <-> City mapping (admins can restrict cities per plan if needed)
--    For most residential plans, all cities in the country are available.
CREATE TABLE IF NOT EXISTS plan_cities (
    id              SERIAL PRIMARY KEY,
    plan_id         INTEGER NOT NULL REFERENCES plans(id) ON DELETE CASCADE,
    city_id         INTEGER NOT NULL REFERENCES cities(id) ON DELETE CASCADE,
    is_enabled      BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (plan_id, city_id)
);

CREATE INDEX IF NOT EXISTS idx_plan_cities_plan ON plan_cities(plan_id);

-- 4. Backfill: compute price_per_gb from existing price_ngn for residential/mobile plans
--    Existing residential plans have quantity=5GB and price_ngn=15000 (e.g. RESI-UK-5GB=15000)
--    So price_per_gb = price_ngn / quantity
UPDATE plans
SET price_per_gb = ROUND(price_ngn / NULLIF(quantity, 0), 2)
WHERE plan_type IN ('residential', 'mobile')
  AND price_per_gb IS NULL
  AND quantity > 0;

-- 5. Backfill: for Datacenter/ISP, ensure price_ngn is the per-IP price (no change needed)
--    Existing DC plans are already per-IP at quantity=1 (DC-US-5GB has quantity=5 though).
--    We'll keep quantity as "GB included" for DC plans and price_ngn as the base price.
--    Frontend will compute "per IP" pricing differently.

-- 6. Add rotation_mode enum check (rotating vs static) — already exists since migration 020
--    No change needed.

-- 7. Add city column to orders (so we know where to provision)
ALTER TABLE orders ADD COLUMN IF NOT EXISTS city_id INTEGER REFERENCES cities(id);
ALTER TABLE orders ADD COLUMN IF NOT EXISTS city_name VARCHAR(100);

-- 8. Seed initial cities from Rayobyte's trial coverage (Jul 30 2026)
--    These are the major cities we tested in the 8-country residential trial.
INSERT INTO cities (country_code, city_name, isp_name, latitude, longitude, source) VALUES
    -- US (tested New York, Los Angeles during trial)
    ('US', 'New York',     'Verizon',         40.7128,  -74.0060, 'rayobyte'),
    ('US', 'Los Angeles',  'Spectrum',        34.0522,  -118.2437, 'rayobyte'),
    ('US', 'Chicago',      'Comcast',         41.8781,  -87.6298, 'rayobyte'),
    ('US', 'Dallas',       'AT&T',            32.7767,  -96.7970, 'rayobyte'),
    ('US', 'Miami',        'Comcast',         25.7617,  -80.1918, 'rayobyte'),
    -- UK
    ('GB', 'London',       'BT',              51.5074,  -0.1278, 'rayobyte'),
    ('GB', 'Manchester',   'Virgin Media',    53.4808,  -2.2426, 'rayobyte'),
    ('GB', 'Birmingham',   'Sky',             52.4862,  -1.8904, 'rayobyte'),
    -- DE
    ('DE', 'Berlin',       'Deutsche Telekom', 52.5200, 13.4050, 'rayobyte'),
    ('DE', 'Munich',       'Vodafone',        48.1351,  11.5820, 'rayobyte'),
    ('DE', 'Frankfurt',    '1&1',             50.1109,  8.6821, 'rayobyte'),
    -- CA
    ('CA', 'Toronto',      'Bell',            43.6532,  -79.3832, 'rayobyte'),
    ('CA', 'Vancouver',    'Telus',           49.2827,  -123.1207, 'rayobyte'),
    ('CA', 'Montreal',     'Videotron',       45.5017,  -73.5673, 'rayobyte'),
    -- AU
    ('AU', 'Sydney',       'Telstra',         -33.8688, 151.2093, 'rayobyte'),
    ('AU', 'Melbourne',    'Optus',           -37.8136, 144.9631, 'rayobyte'),
    -- FR
    ('FR', 'Paris',        'Orange',          48.8566,  2.3522, 'rayobyte'),
    ('FR', 'Lyon',         'SFR',             45.7640,  4.8357, 'rayobyte'),
    -- BR
    ('BR', 'São Paulo',    'Vivo',            -23.5505, -46.6333, 'rayobyte'),
    ('BR', 'Rio de Janeiro', 'Claro',         -22.9068, -43.1729, 'rayobyte'),
    -- IN
    ('IN', 'Mumbai',       'Jio',             19.0760,  72.8777, 'rayobyte'),
    ('IN', 'Delhi',        'Airtel',          28.7041,  77.1025, 'rayobyte'),
    ('IN', 'Bangalore',    'BSNL',            12.9716,  77.5946, 'rayobyte')
ON CONFLICT (country_code, city_name, state_code) DO NOTHING;

COMMIT;
