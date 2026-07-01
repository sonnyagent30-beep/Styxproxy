-- ─────────────────────────────────────────────────────────
-- Bunche — Seed Data
-- Run AFTER 01-schema.sql
-- ─────────────────────────────────────────────────────────

BEGIN;

-- ── Products ─────────────────────────────────────────────
INSERT INTO products (sku, name, category, description, buy_cost_usd, sell_price, stock_qty) VALUES

  ('ISP-UK-GLIDE',  'ISP UK Clean (Glide)',        'ISP',        'Premium UK ISP proxy via IPRoyal Glide.',                   2.70, 6500.00, 0),
  ('ISP-UK-STD',   'ISP UK Standard',              'ISP',        'Standard UK ISP proxy via Bright Data.',                   1.30, 5000.00, 0),
  ('ISP-STD-US',   'ISP US Standard',              'ISP',        'US ISP proxy via Bright Data.',                            1.30, 5000.00, 0),
  ('ISP-STD-DE',   'ISP Germany Standard',         'ISP',        'Germany ISP proxy via Bright Data.',                      1.30, 5000.00, 0),
  ('ISP-STD-FR',   'ISP France Standard',          'ISP',        'France ISP proxy via Bright Data.',                       1.30, 5000.00, 0),
  ('ISP-STD-CA',   'ISP Canada Standard',          'ISP',        'Canada ISP proxy via Bright Data.',                       1.30, 5000.00, 0),
  ('ISP-PRM-JP',   'ISP Japan Premium',            'ISP',        'Premium Japan ISP proxy via Decodo.',                      2.10, 6500.00, 0),
  ('ISP-PRM-AU',   'ISP Australia Premium',         'ISP',        'Premium Australia ISP proxy via Decodo.',                  2.10, 6500.00, 0),
  ('ISP-PRM-BR',   'ISP Brazil Premium',           'ISP',        'Premium Brazil ISP proxy via Decodo.',                     2.10, 6500.00, 0),
  ('ISP-PRM-SG',   'ISP Singapore Premium',         'ISP',        'Premium Singapore ISP proxy via Decodo.',                   2.10, 6500.00, 0),
  ('ISP-PRM-KR',   'ISP South Korea Premium',      'ISP',        'Premium South Korea ISP proxy via Decodo.',               2.10, 6500.00, 0),
  ('ISP-V6',       'ISP IPv6',                     'ISP',        'IPv6 ISP proxy via Proxy-Seller.',                        0.15, 3500.00, 0),
  ('ISP-US-GECKO', 'ISP US (Gecko)',                'ISP',        'US ISP proxy via Gecko. Scamalytics 0 — verified clean.',  3.00, 8000.00, 0),
  ('DC-IPv4',      'DC Static IPv4',               'DATACENTER', 'Static datacenter IPv4 proxy.',                            0.05, 3000.00, 0),
  ('DC-IPv6',      'DC Static IPv6',               'DATACENTER', 'Static datacenter IPv6 proxy.',                            0.02, 2500.00, 0),
  ('DC-ROT',       'DC Rotating',                  'DATACENTER', 'Rotating datacenter proxy.',                               0.02, 4500.00, 0),
  ('RES-IPv4',     'Residential IPv4',             'RESIDENTIAL','Residential IPv4 proxy via DataImpulse.',                  1.00, 1950.00, 0),
  ('RES-IPv6',     'Residential IPv6',             'RESIDENTIAL', 'Residential IPv6 proxy via DataImpulse.',                  1.00, 1500.00, 0),
  ('MOB-4G',       'Mobile 4G LTE',               'MOBILE',     '4G mobile proxy via IPRoyal.',                             2.00, 6000.00, 0);

-- ── Admin customer ─────────────────────────────────────────
INSERT INTO customers (id, phone, email, name, is_active) VALUES
  ('00000000-0000-0000-0000-000000000001', '+2347032981049', 'admin@bunche.ng', 'Bunche Admin', TRUE)
ON CONFLICT (phone) DO NOTHING;

-- ── System event ─────────────────────────────────────────
INSERT INTO system_events (event_type, actor, payload) VALUES
  ('system.seeded', 'system', '{"version": "1.0", "products": 19}');

COMMIT;
