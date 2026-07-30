-- 018_relay_upstream_text.sql
-- Change upstream_proxy_ip from INET to TEXT so it can hold hostnames
-- (Rayobyte gateway la.residential.rayobyte.com is a multi-IP anycast LB,
-- hostname is the canonical form; resolution happens at connect time)
ALTER TABLE styxproxy_credentials
  ALTER COLUMN upstream_proxy_ip TYPE TEXT USING upstream_proxy_ip::text;
