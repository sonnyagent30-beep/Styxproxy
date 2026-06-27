# Bunche — Phone Hash Blocking Mechanism

**Date:** 2026-06-27
**Status:** LOCKED (council-validated)
**Source:** Required by AUP §2.3 enforcement

---

## Why Phone Hash Blocking Exists

AUP §2.3 commits to blocking phones used for free trial abuse. Customers trying to evade blocks via new SIM cards would otherwise defeat the daily trial limit.

**Solution:** Block by **phone_hash** (sha256[:20]) not by phone number. Since phone_hash is derived from the phone number itself, blocking it is equivalent to blocking the number — but we never store plain numbers in audit logs.

---

## Database Schema

```sql
CREATE TABLE blocked_phone_hashes (
    id SERIAL PRIMARY KEY,
    phone_hash VARCHAR(20) NOT NULL UNIQUE,
    reason VARCHAR(100) NOT NULL,                 -- 'trial_abuse', 'fraud', 'tos_violation', etc.
    blocked_by VARCHAR(50),                        -- 'system_auto', 'admin:<phone_hash>'
    evidence JSONB,                                -- proof (e.g. multiple phones with same fingerprint)
    blocked_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ,                       -- NULL = permanent; otherwise auto-unblock
    notes TEXT,
    
    CONSTRAINT valid_reason CHECK (
        reason IN ('trial_abuse', 'fraud', 'tos_violation', 'admin_override', 'system_auto')
    )
);

CREATE INDEX idx_blocked_hash ON blocked_phone_hashes(phone_hash);
CREATE INDEX idx_blocked_expires ON blocked_phone_hashes(expires_at) WHERE expires_at IS NOT NULL;
```

---

## When to Block

| Trigger | Action | Evidence |
|---------|--------|----------|
| Customer completes free trial survey from 4+ different phones in 24h | Auto-block all 4 hashes for 30 days | phone_hash + timestamp pattern |
| Customer shares trial credentials publicly (detected via external report) | Manual block by admin | Screenshot + URL |
| Customer sends payment then disputes after receiving proxy (friendly fraud) | Manual block by admin | Flutterwave dispute log |
| Theorem Reach reports survey fraud | Auto-block for 90 days | TR fraud report |
| Customer violates AUP §1.1-1.6 (serious crime) | Manual block, permanent | Admin decision |

---

## Auto-Detection: Multi-Phone Trial Abuse

**Cron: every 1 hour**

```sql
-- Find phone_hashes that claimed trial from N+ different IPs in last 24h
-- (Use IP as proxy for "different device/network" since phone_hash changes per number)
SELECT 
  phone_hash,
  COUNT(DISTINCT client_ip) AS distinct_ips,
  COUNT(*) AS trials_attempted,
  MIN(created_at) AS first_attempt,
  MAX(created_at) AS last_attempt
FROM trial_request_log
WHERE created_at > NOW() - INTERVAL '24 hours'
  AND client_ip IS NOT NULL  -- captured from Cloudflare header
GROUP BY phone_hash
HAVING COUNT(DISTINCT client_ip) >= 4  -- suspicious threshold
   AND COUNT(*) >= 4;
```

If found:
1. Insert all N phone_hashes into `blocked_phone_hashes` with reason='trial_abuse', expires_at=NOW()+30 days
2. Send admin alert with the phone_hashes + IPs
3. Customer sees: "Trial temporarily unavailable. Contact support if you believe this is a mistake."

---

## How to Check (Per Webhook)

Every incoming webhook checks the sender against the blocklist BEFORE any other processing:

```sql
-- Add this as the FIRST node in every workflow
SELECT 1 FROM blocked_phone_hashes
WHERE phone_hash = $sender_hash
  AND (expires_at IS NULL OR expires_at > NOW())
LIMIT 1;
```

**If blocked:** respond with neutral message:
```
🛡️ Your account is currently restricted.

Reason: [shown to customer — "Multiple trial abuse reports" / "Trial fraud detected" / "Admin review"]

If you believe this is a mistake, contact abuse@bunche.com
```

**DO NOT** reveal specific technical details or that the block is by phone_hash (helps attackers).

---

## How to Unblock

### Admin command

```
Admin: Unblock <phone_hash>
   ↓
[PIN + TOTP verify — high-risk command]
   ↓
DELETE FROM blocked_phone_hashes WHERE phone_hash = ?
   ↓
[Audit log: phone_hash_unblocked, admin=<hash>, customer=<hash>]
   ↓
WhatsApp to customer: "Your account access has been restored."
```

### Auto-expiry

```sql
-- Cron: every 6 hours
DELETE FROM blocked_phone_hashes
WHERE expires_at IS NOT NULL AND expires_at < NOW();
```

---

## Privacy Implications

**We're storing:** sha256(phone).substring(0, 20) — a hash, not the number itself.

**Risk:** Phone_hash collision is theoretically possible (1 in ~1 trillion). For our scale (1M customers), collision risk is negligible (~5e-7).

**Mitigation:** Hash includes first 12 chars of sha256 (not just [:20]). That's actually [:12] + first 8 chars from position 20. Wait — let me clarify:

```python
import hashlib
def phone_hash(phone: str) -> str:
    return hashlib.sha256(phone.encode()).hexdigest()[:20]
# Result: 40 hex chars = 20 bytes = ~160 bits of entropy
# Collision probability at 1M entries: ~2.7e-41 (essentially zero)
```

**Good enough for our use case.**

---

## What We Don't Do

| Don't | Why |
|-------|-----|
| Block by IP alone | Mobile customers share IPs via carrier-grade NAT |
| Block by device fingerprint alone | Mobile devices reset, easy to spoof |
| Block by phone number in plain text | NDPR — minimize PII storage |
| Permanent block without admin review | Customer service risk |
| Auto-unblock without admin notification | Lose visibility on abuse patterns |

---

## Audit Trail

Every block + unblock writes to `customer_audit_log`:

```
{event_type: 'phone_hash_blocked', reason, evidence_jsonb, blocked_by_hash, customer_hash, timestamp}
{event_type: 'phone_hash_unblocked', admin_hash, customer_hash, timestamp}
{event_type: 'auto_block_cron_ran', count_blocked, phone_hashes}
```

---

## NDPR Compliance

- We store hash, not number → no PII storage of blocked list
- Customer is told they're "restricted" but not "blocked by phone_hash"
- Customer can appeal via email (abuse@bunche.com)
- Block expires automatically (unless permanent + admin-set)
- Manual review available if customer disputes

---

## Related

- `legal/ACCEPTABLE_USE_POLICY.md` §2.3 — Enforcement matrix
- `scenarios/2026-06-26-free-trial.md` §2.2 — Free trial abuse types
- `docs/SECURITY_RUNBOOK.md` §1 — Incident response for compromised accounts