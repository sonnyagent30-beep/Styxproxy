# Relay Operations Runbook

**Audience:** On-call engineers, admins
**Last updated:** 2026-07-29

This is the operational playbook for the Interserver gost relay that handles paid customers and the Contabo socks-auth-proxy that handles free trials.

## TL;DR — What lives where

| Service | Where | Port | Customers |
|---|---|---|---|
| **gost relay (paid)** | Interserver 162.35.184.69 | 1080 (SOCKS5), 8080 (HTTP) | All paid customers |
| **socks-auth-proxy (trial)** | Contabo 84.247.132.12 | 1081 (SOCKS5) | Free trial users |
| **danted (no auth)** | Contabo 84.247.132.12 | 1080 (internal) | Hop for socks-auth-proxy |
| **FastAPI backend** | Interserver 162.35.184.69 | 9000 (admin) | Internal only |
| **rayobyte (residential)** | Rayobyte LA | 8000 | Upstream pool |

## Common Operations

### 1. Rotate a customer's password

**Customer-initiated** (rate limit: 3/day):
- Endpoint: `POST /api/credentials/{id}/rotate-password` (customer auth)
- Backend: generates new random password, updates `styxproxy_credentials.styxproxy_password`, calls Rayobyte `/users/edit` if upstream_type is rayobyte_*, audit log entry
- relay_sync.py picks up within 30s, gost reloads
- Customer gets new password via email + Telegram/WhatsApp

**Admin-initiated** (no rate limit):
- Endpoint: `POST /api/admin/relay/{user_id}/rotate` (admin auth)
- Same flow, no rate limit

**Manual** (ssh into Interserver):
```bash
# Edits Postgres directly
sudo -u postgres psql -d styxproxy -c "
UPDATE styxproxy_credentials 
SET styxproxy_password = decode('newpass', 'escape')
WHERE styxproxy_username = 'jibola_styxproxy';
"
# relay_sync.py will pick up within 30s
```

### 2. Revoke a customer

**Customer expired/cancelled:**
- Backend marks `status = 'expired'` on `styxproxy_credentials`
- relay_sync.py picks up within 30s, removes from gost auth.json

**Force revoke (admin):**
```bash
sudo -u postgres psql -d styxproxy -c "
UPDATE styxproxy_credentials 
SET status = 'revoked', revoked_at = NOW(), revoke_reason = 'admin_force'
WHERE styxproxy_username = 'jibola_styxproxy';
"
# Verify
sudo -u postgres psql -d styxproxy -c "
SELECT styxproxy_username, status, revoked_at, revoke_reason FROM styxproxy_credentials WHERE styxproxy_username = 'jibola_styxproxy';
"
```

### 3. Monthly bandwidth reset

Cron at 02:00 UTC on the 1st of each month:
```bash
sudo -u postgres psql -d styxproxy -c "
UPDATE styxproxy_credentials 
SET gb_used = 0,
    monthly_bandwidth_used_bytes = 0
WHERE status = 'active';
"
```

### 4. Add a new provider (e.g., Bright Data)

1. Add provider to `.env`:
   ```
   BRIGHT_DATA_HOST=brd.superproxy.io
   BRIGHT_DATA_PORT=22225
   BRIGHT_DATA_USER=brd-customer-xxx
   BRIGHT_DATA_PASS=***
   ```

2. Update `app/services/rayobyte.py` (or create `app/services/bright_data.py`):
   ```python
   async def create_bright_data_customer(...):
       # Call Bright Data API
       pass
   ```

3. Update `app/services/relay_entries.py`:
   ```python
   UPSTREAM_TYPES = {
       'rayobyte_resi': ...,
       'bright_data_resi': (host, port, user, pass, protocol),
       'bright_data_isp': ...,
   }
   ```

4. Update `relay_sync.py` to render the new upstream type

5. Test with a single customer before rolling out

### 5. Rayobyte outage degradation

If Rayobyte is down:
1. relay_sync.py still writes auth.json (with same upstream)
2. gost tries to connect to upstream, fails
3. Customers get 503 from gost
4. **Backend action:** mark all rayobyte_*` rows as `status='suspended'`, set `suspend_reason='rayobyte_outage'`
5. Send WhatsApp blast to affected customers
6. When Rayobyte recovers: restore status, send recovery message

### 6. Postgres + relay sync desync

If `auth.json` is stale (more than 5 min old):
```bash
# Force regenerate
systemctl restart styxproxy-relay-sync
# Verify
cat /etc/styxproxy/auth.json | jq '.users | length'
```

Last successful sync timestamp is in `/var/log/styxproxy-relay-sync.log`.

### 7. Customer can't connect

**Step 1: Check credential is valid**
```bash
sudo -u postgres psql -d styxproxy -c "
SELECT styxproxy_username, status, expires_at FROM styxproxy_credentials WHERE styxproxy_username = 'jibola_styxproxy';
"
```
- Status must be 'active'
- expires_at must be in future

**Step 2: Check upstream is reachable**
```bash
# From Interserver
curl -x socks5://styx_t1:12345-country-US@la.residential.rayobyte.com:8000 https://ipinfo.io/json
```

**Step 3: Check auth.json has the user**
```bash
cat /etc/styxproxy/auth.json | jq '.users[] | select(.username == "jibola_styxproxy")'
```

**Step 4: Check gost log**
```bash
tail -50 /var/log/gost/audit.log
```

**Step 5: Force re-sync**
```bash
curl -X POST http://127.0.0.1:18080/api/config/reload -H "Authorization: Bearer $GOST_API_KEY"
```

### 8. Rabbit hole: customer sees different IP than expected

If customer is using `-country-GB` but exits through US:
- Check the upstream password in relay_entries has `-country-GB` suffix
- Verify country code matches the customer's profile
- The `-country-XX` substring is part of the upstream password, not the styxproxy password

## When to escalate

Escalate to PagerDuty (or wake someone) if:
- **Page** for: relay_sync.py failing for >5min, gost down, all customers can't connect
- **Slack** for: One customer can't connect, single-country IP issues
- **Email** for: Ban claim, refund request, slow customer issue

## Audit trail

Every operation is logged to `styxproxy_audit_log`:
- Customer-initiated rotations
- Admin-initiated rotations  
- Revocations
- Bandwidth resets
- Provider outages

Query the audit log:
```sql
SELECT created_at, actor, action, target_user, details
FROM styxproxy_audit_log
WHERE created_at > NOW() - INTERVAL '7 days'
ORDER BY created_at DESC;
```

## Dead-IP replacement

Policy: customer reports a dead proxy → backend auto-checks reputation:
1. If IP is dead (AbuseIPDB score > 50, target site blocks it): auto-rotate
2. If IP is alive but target site blocks it: send to admin queue for manual review
3. If IP works fine: not a dead-IP case (probably customer's app)

The rotation logic is in `app/services/credential.py:rotate_on_failure()`.

## See Also

- [PAID_PROXY_RELAY.md](./PAID_PROXY_RELAY.md) — relay implementation
- [TRIAL_PROXY_SETUP.md](./TRIAL_PROXY_SETUP.md) — trial pool setup
- [RUNBOOKS.md](../../RUNBOOKS.md) — general ops
- [INCIDENT_RESPONSE.md](./INCIDENT_RESPONSE.md) — incident playbook
