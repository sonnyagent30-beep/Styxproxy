-- Seed the homepage stat feature flags.
--
-- All five default to enabled=false, which is the point: while a flag is OFF
-- the homepage renders placeholder copy instead of a number. Flipping a flag
-- in the admin dashboard (Feature Flags) swaps in the real, computed figure
-- with no deploy.
--
-- Idempotent: re-running will not clobber a flag an admin has already turned on.
--
-- Which flags can actually go live:
--   stat_customers  -> computable (distinct paying emails)   READY to flip
--   stat_countries  -> computable (enabled-for-sale codes)   READY to flip
--   stat_revenue    -> NO honest source (naira -> "$" would be an unbacked claim)
--   stat_rating     -> NO review source exists in the system
--   stat_uptime     -> no public SLA; real uptime lives in Grafana
-- The last three have no computed value by design, so turning them on changes
-- nothing until a real source exists. See app/routers/stats.py.

INSERT INTO feature_flags (id, name, description, enabled, enabled_for, admin_overrides)
VALUES
  (gen_random_uuid(), 'stat_revenue',   'Homepage stats: total processed. OFF = placeholder copy. No honest source yet.',            false, NULL, NULL),
  (gen_random_uuid(), 'stat_customers', 'Homepage stats: customer count. OFF = placeholder copy. Real value = distinct paying emails.', false, NULL, NULL),
  (gen_random_uuid(), 'stat_rating',    'Homepage stats: rating. OFF = placeholder copy. No review source exists.',                 false, NULL, NULL),
  (gen_random_uuid(), 'stat_countries', 'Homepage stats: country coverage. OFF = placeholder copy. Real value = enabled-for-sale codes.', false, NULL, NULL),
  (gen_random_uuid(), 'stat_uptime',    'Homepage stats: uptime. OFF = placeholder copy. No public SLA offered.',                     false, NULL, NULL)
ON CONFLICT (name) DO NOTHING;
