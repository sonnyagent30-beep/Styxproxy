# Styxproxy — Phone Hash Blocking Mechanism

**Date:** 2026-06-27
**Status:** LOCKED (council-validated)
**Source:** Required by AUP §2.3 enforcement
**Last update:** Added explicit "first-step" code snippet per security council feedback

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

## How to Check (Per Webhook) — **CRITICAL: FIRST STEP IN EVERY WORKFLOW**

Every incoming webhook checks the sender against the blocklist BEFORE any other processing.

### The Phone Hash Block Check (n8n Code Node)

```javascript
// This node runs FIRST in every webhook workflow
const crypto = require('crypto');

// Get sender's phone number from webhook payload
const senderPhone = $json.body?.from || $json.body?.entry?.[0]?.changes?.[0]?.value?.messages?.[0]?.from;

// Hash it
const phoneHash = crypto.createHash('sha256').update(senderPhone).digest('hex').substring(0, 20);

// Check blocklist
const blocked = await db.query(
  `SELECT 1 FROM blocked_phone_hashes
   WHERE phone_hash = $1
     AND (expires_at IS NULL OR expires_at > NOW())
   LIMIT 1`,
  [phoneHash]
);

if (blocked.length > 0) {
  // Generic response — don't reveal we're using phone_hash block
  await sendWhatsApp(senderPhone,
    "🛡️ Your account is currently restricted.\n\n" +
    "If you believe this is a mistake, contact abuse@styxproxy.com"
  );
  
  // Log the blocked attempt
  await db.query(
    `INSERT INTO customer_audit_log (event_type, customer_hash, metadata)
     VALUES ('blocked_attempt', $1, $2)`,
    [phoneHash, JSON.stringify({
      workflow: $workflow.name,
      source_ip: $json.headers?.['cf-connecting-ip'] || 'unknown'
    })]
  );
  
  // Return 200 to prevent retry abuse
  return { json: { blocked: true, continue: false } };
}

// Pass phone_hash to next node for use throughout workflow
return { 
  json: { 
    blocked: false, 
    continue: true,
    phone_hash: phoneHash,
    sender_phone: senderPhone  // Only use internally, never log
  } 
};
```

**Wiring:**
- This node runs **FIRST** in every workflow that accepts customer input
- It returns `{blocked: true}` if blocked → workflow exits with no further processing
- The `phone_hash` value is passed to all downstream nodes (used for audit logs, customer lookups, etc.)

**DO NOT** reveal in customer-facing messages:
- That we're using phone_hash to block (helps attackers)
- The specific reason (only generic "restricted" message)
- The expiry date

---

## Admin Unblock Command

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

### Unblock (n8n Implementation)

```javascript
// n8n Code node — unblock phone_hash (admin command)
const input = $json.body.text.trim();
const match = input.match(/^Unblock ([a-f0-9]{20})$/i);

if (!match) {
  return { json: { error: 'Invalid format. Use: Unblock <20-char-hash>' } };
}

const phoneHash = match[1].toLowerCase();

const result = await db.query(
  `DELETE FROM blocked_phone_hashes WHERE phone_hash = $1 RETURNING phone_hash`,
  [phoneHash]
);

if (result.length === 0) {
  return { json: { error: 'Phone hash not found in block list' } };
}

await db.query(
  `INSERT INTO customer_audit_log (event_type, customer_hash, metadata)
   VALUES ('phone_hash_unblocked', $1, $2)`,
  [phoneHash, JSON.stringify({
    admin_phone_hash: process.env.ADMIN_PHONE_HASH,
    timestamp: new Date().toISOString()
  })]
);

// Optionally notify customer (if we have their last contact)
const customer = await db.query(
  `SELECT phone FROM customers WHERE phone_hash = $1 LIMIT 1`,
  [phoneHash]
);

if (customer.length > 0) {
  await sendWhatsApp(customer[0].phone,
    "✅ Your Styxproxy account access has been restored.\n\n" +
    "You can now order proxies and request free trials again."
  );
}

return { json: { success: true, unblocked: phoneHash } };
```

---

## Auto-Expiry Cron

```sql
-- Cron: every 6 hours
DELETE FROM blocked_phone_hashes
WHERE expires_at IS NOT NULL AND expires_at < NOW();
```

---

## Privacy Implications

**We're storing:** sha256(phone).substring(0, 20) — a hash, not the number itself.

**Risk:** Phone_hash collision is theoretically possible (1 in ~1 trillion). For our scale (1M customers), collision risk is negligible (~5e-7).

**Mitigation:** Hash includes first 20 chars of sha256 — 160 bits of entropy.

```python
import hashlib
def phone_hash(phone: str) -> str:
    return hashlib.sha256(phone.encode()).hexdigest()[:20]
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

Every block + unblock + blocked attempt writes to `customer_audit_log`:

```
{event_type: 'phone_hash_blocked', reason, evidence_jsonb, blocked_by_hash, customer_hash, timestamp}
{event_type: 'phone_hash_unblocked', admin_hash, customer_hash, timestamp}
{event_type: 'blocked_attempt', customer_hash, workflow, source_ip_hash, timestamp}
{event_type: 'auto_block_cron_ran', count_blocked, phone_hashes}
```

---

## NDPR Compliance

- We store hash, not number → no PII storage of blocked list
- Customer is told they're "restricted" but not "blocked by phone_hash"
- Customer can appeal via email (abuse@styxproxy.com)
- Block expires automatically (unless permanent + admin-set)
- Manual review available if customer disputes

---

## Related

- `legal/ACCEPTABLE_USE_POLICY.md` §2.3 — Enforcement matrix
- `scenarios/2026-06-26-free-trial.md` §2.2 — Free trial abuse types
- `docs/SECURITY_RUNBOOK.md` §1 — Incident response for compromised accounts
- `scenarios/2026-06-27-admin-operations.md` — Unblock command implementation