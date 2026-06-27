# Bunche — Scenario Replay: Admin Operations

**Date captured:** 2026-06-27
**Source:** Sonny's simulation pass + council-validated gaps
**Status:** LOCKED — covers all admin commands + risk levels
**Last update:** Added TOTP verification code snippet + n8n implementation per council feedback

---

## Purpose

The admin command handler has 15+ documented commands across 3 risk levels but ZERO end-to-end scenarios tested. This doc captures the canonical admin workflows so QA + future operators can test the full surface area.

---

## Admin Authentication Flow

```
Admin sends WhatsApp message from ADMIN_PHONE
        ↓
[Workflow 3 — Admin Command Handler triggered]
        ↓
[Check session]
        ↓
   ┌────────────────────────────────────┐
   │ Session state                      │
   ├────────────────────────────────────┤
   │ Active session (within 30 min)     │ → continue
   │ Session expired > 30 min           │ → re-prompt PIN
   │ No session (first command)         │ → prompt PIN
   │ Locked out (failed 3x)             │ → admin alert, deny
   └────────────────────────────────────┘
        ↓
[Parse command] → [Determine risk level]
        ↓
[Execute command] → [Log to admin_commands_log]
        ↓
[Send WhatsApp response to admin]
```

---

## PIN Verification (Medium Risk Trigger)

```
Admin enters PIN
        ↓
[bcrypt.compare(input, customers.pin_hash)]
        ↓
   ┌────────────────────────────────────┐
   │ Outcome                           │
   ├────────────────────────────────────┤
   │ ✅ Match → 30-min session starts    │
   │ ❌ Fail #1 → "2 attempts left"     │
   │ ❌ Fail #2 → "1 attempt. Admin alerted if fail again." │
   │ ❌ Fail #3 → LOCKED 15min + admin  │
   └────────────────────────────────────┘
```

### PIN Verification — n8n Implementation

```javascript
// n8n Code node — verify admin PIN
const bcrypt = require('bcrypt');

const input = $json.body.text.trim();
const adminPhoneHash = process.env.ADMIN_PHONE_HASH; // from env
const storedHash = await db.query(
  'SELECT pin_hash FROM admin_users WHERE phone_hash = $1',
  [adminPhoneHash]
);

if (!storedHash) {
  throw new Error('Admin not configured');
}

const valid = await bcrypt.compare(input, storedHash[0].pin_hash);

if (valid) {
  // Create 30-min session in Redis
  await redis.setex(`admin_session:${adminPhoneHash}`, 1800, JSON.stringify({
    started_at: new Date().toISOString(),
    last_command: new Date().toISOString(),
    command_count: 0
  }));
  
  await db.query(
    `UPDATE admin_users SET failed_pin_attempts = 0, locked_until = NULL WHERE phone_hash = $1`,
    [adminPhoneHash]
  );
  
  return { json: { auth_result: 'pin_valid', session_active: true } };
} else {
  // Increment failed attempts, possibly lock
  const result = await db.query(
    `UPDATE admin_users 
     SET failed_pin_attempts = failed_pin_attempts + 1,
         locked_until = CASE
           WHEN failed_pin_attempts + 1 >= 10 THEN NOW() + INTERVAL '24 hours'
           WHEN failed_pin_attempts + 1 >= 5  THEN NOW() + INTERVAL '1 hour'
           WHEN failed_pin_attempts + 1 >= 3  THEN NOW() + INTERVAL '15 minutes'
           ELSE locked_until
         END
     WHERE phone_hash = $1
     RETURNING failed_pin_attempts, locked_until`,
    [adminPhoneHash]
  );
  
  const remaining = 3 - result[0].failed_pin_attempts;
  
  return {
    json: {
      auth_result: 'pin_invalid',
      remaining_attempts: remaining > 0 ? remaining : 0,
      locked_until: result[0].locked_until
    }
  };
}
```

---

## TOTP Verification (High Risk Trigger) — n8n Implementation

```javascript
// n8n Code node — verify admin TOTP for high-risk commands
const speakeasy = require('speakeasy');

const input = $json.body.text.trim();
const adminPhoneHash = process.env.ADMIN_PHONE_HASH;

// Fetch admin's encrypted TOTP secret
const adminRecord = await db.query(
  `SELECT totp_secret_encrypted FROM admin_users WHERE phone_hash = $1`,
  [adminPhoneHash]
);

if (!adminRecord[0] || !adminRecord[0].totp_secret_encrypted) {
  throw new Error('TOTP not configured for admin');
}

// Decrypt the TOTP secret using AES-256-GCM with TOTP_ENCRYPTION_KEY
const crypto = require('crypto');
const masterKey = Buffer.from(process.env.TOTP_ENCRYPTION_KEY, 'hex');
const encryptedData = JSON.parse(adminRecord[0].totp_secret_encrypted);

const decipher = crypto.createDecipheriv(
  'aes-256-gcm',
  masterKey,
  Buffer.from(encryptedData.iv, 'hex')
);
decipher.setAuthTag(Buffer.from(encryptedData.tag, 'hex'));
let decryptedSecret = decipher.update(encryptedData.encrypted, 'hex', 'utf8');
decryptedSecret += decipher.final('utf8');

// Verify TOTP code (allow ±30 second window)
const verified = speakeasy.totp.verify({
  secret: decryptedSecret,
  encoding: 'base32',
  token: input,
  window: 1  // ±1 interval (30 sec each way = 90 sec total tolerance)
});

if (verified) {
  // Log high-risk command execution
  await db.query(
    `INSERT INTO admin_commands_log
     (admin_phone_hash, command, risk_level, auth_method, executed_at)
     VALUES ($1, $2, 'high', 'pin_totp', NOW())`,
    [adminPhoneHash, $json.body.command]
  );
  
  return { json: { totp_valid: true, allowed: true } };
} else {
  return { json: { totp_valid: false, allowed: false } };
}
```

**TOTP Setup (one-time, per admin):**

```javascript
// Run once during admin onboarding
const speakeasy = require('speakeasy');
const QRCode = require('qrcode');

const secret = speakeasy.generateSecret({
  name: 'Bunche Admin',
  issuer: 'Bunche',
  length: 32
});

// Encrypt with AES-256-GCM before storing
const masterKey = Buffer.from(process.env.TOTP_ENCRYPTION_KEY, 'hex');
const iv = crypto.randomBytes(16);
const cipher = crypto.createCipheriv('aes-256-gcm', masterKey, iv);

let encrypted = cipher.update(secret.base32, 'utf8', 'hex');
encrypted += cipher.final('hex');
const tag = cipher.getAuthTag();

const encryptedData = {
  encrypted: encrypted,
  iv: iv.toString('hex'),
  tag: tag.toString('hex')
};

await db.query(
  `UPDATE admin_users SET totp_secret_encrypted = $1 WHERE phone_hash = $2`,
  [JSON.stringify(encryptedData), adminPhoneHash]
);

// Generate QR code for Google Authenticator
const qrCodeUrl = await QRCode.toDataURL(secret.otpauth_url);
// Send QR code to admin via WhatsApp
```

---

## Low-Risk Commands (Session Auth Only)

### `Daily Summary`

**What admin sees:**
```
📊 Daily Summary — June 27

💰 Revenue: ₦312,500 (47 orders)
👥 New customers: 8
⚠️ Errors: 2 (1 critical)
💸 Refunds: 1
🎁 Free trials: 3 (₦4.50 revenue from Theorem Reach)
🔗 Referral purchases: 2 (₦650 credit paid out)

Full details: https://n8n.yourdomain.com/executions/...
```

### `Errors`

**What admin sees:**
```
🚨 Recent Errors (last 24h)

1. ERR-20260627-1423-001 | CRITICAL
   Order: ORD-20260627-0947
   Workflow: Payment Confirmation
   Message: "Provider API returned 503 after 4 attempts. Auto-refunded."
   Time: 14:23:18 Lagos

2. ERR-20260627-1124-002 | HIGH
   Workflow: Theorem Reach Webhook
   Message: "Invalid HMAC signature — possible attack"
   Time: 11:24:05 Lagos

[3 more errors]
```

### `Provider Status`

**What admin sees:**
```
🔍 Provider Health

✅ Proxy-Seller: Working
   Balance: $45.20
   Countries available: UK, US, DE, FR, JP, AU, BR, SG, CA
   Last check: 14:23 (3 sec ago)

✅ DataImpulse: Working
   Balance: $32.10
   Last data fetch: 14:08 (15 min ago)

⚠️ 3proxy Trial: Working
   Active trials: 12/100
   Last cleanup: 14:20 (3 min ago)
```

### `Trial Stats`

**What admin sees:**
```
🎁 Free Trial Stats — Today

Trials granted: 47
Trials rejected (daily limit): 8
Trials rejected (slots busy): 2
Trials expired (natural): 31
Theorem Reach revenue: $70.50

Active trials right now: 12/100
Avg trial duration: 87 min (out of 120 max)

Multi-phone abuse blocks today: 2 phone_hashes
```

### `Referral Stats`

**What admin sees:**
```
🔗 Referral Stats — Last 30 Days

Total referral purchases: 47
Total credit earned by referrers: ₦58,250
Total credit used: ₦42,800
Credit outstanding (saved for later): ₦15,450

Top referrers:
1. Chidi — 12 referrals — ₦15,000 credit earned
2. Ada — 8 referrals — ₦9,500 credit earned
3. Tunde — 5 referrals — ₦6,250 credit earned

Top referred product: ISP UK (most referrals)
Conversion rate: 23% (referral name entered ÷ orders placed)
```

### `Pending`

**What admin sees:**
```
⏳ Pending Actions

1. BAN-CLAIM-001: Order ORD-20260627-0917
   Customer: a3f2b9... (Dan hash)
   Screenshot: https://files.bunche.ng/bans/xxx.jpg
   Reported: 2 hours ago

2. REFUND-NEEDED-001: Order ORD-20260627-0947
   Customer: 8d7e4f... (?)
   Reason: "All 3 IP retries failed"
   Reported: 5 min ago

[Type the action ID to handle: e.g. "Approve BAN-CLAIM-001"]
```

### `Admin Status`

**What admin sees:**
```
🔐 Admin Session Active

Started: 14:18 Lagos (5 min ago)
Expires: 14:48 (25 min remaining)
Risk level last command: low
Last command: Daily Summary
Commands this session: 3
Failed PIN attempts this hour: 0
```

---

## Medium-Risk Commands (Fresh PIN Required)

### `Block <phone_hash> <reason>`

**What admin does:**
```
Admin: Block a3f2b9c1e8d4f5a6b7c8 trial_abuse
```

**System response:**
```
⚠️ Medium-risk command. Confirm PIN.
```

**Admin enters PIN:**
```
1234
```

**System response:**
```
✅ Phone hash blocked.

Customer: a3f2b9c1e8d4f5a6b7c8
Reason: trial_abuse
Duration: 30 days (auto-expires)
Expires: 2026-07-27

Customer will see: "Your account is currently restricted."

[Audit log: phone_hash_blocked, admin=<hash>, reason, evidence]
```

### `Unblock <phone_hash>`

**What admin does:**
```
Admin: Unblock a3f2b9c1e8d4f5a6b7c8
```

**System response:**
```
⚠️ Medium-risk command. Confirm PIN.
```

**After PIN:**
```
✅ Phone hash unblocked.

Customer: a3f2b9c1e8d4f5a6b7c8
Unblocked by: admin (you)
Time: 14:25 Lagos

Customer can now use Bunche normally.
[WhatsApp sent to customer: "Your account access has been restored."]
```

### `Resolve ERR-XXXXX`

**What admin does:**
```
Admin: Resolve ERR-20260627-1423-001
```

**System response:**
```
⚠️ Medium-risk command. Confirm PIN.
```

**After PIN:**
```
✅ Error marked as resolved.

Error: ERR-20260627-1423-001
Resolution: "Auto-refunded, customer notified"
Notes: [admin can add notes]
```

### `Details ORD-XXXXX`

**What admin does:**
```
Admin: Details ORD-20260627-0917
```

**System response:**
```
⚠️ Medium-risk command. Confirm PIN.
```

**After PIN:**
```
📋 Order Details — ORD-20260627-0917

Customer: a3f2b9... (Dan hash)
Name: Dan
Product: ISP UK × 1
Amount: ₦6,500
Status: fulfilled
Created: 2026-06-27 09:17 Lagos
Fulfilled: 2026-06-27 09:17 (2 min later)
Provider: Proxy-Seller
Provider order: PS-8392
Proxy IP hash: 5a4b3c2d... (hashed)
Expires: 2026-07-27
Referred by: Ada (earned ₦325 credit)
```

---

## High-Risk Commands (PIN + TOTP Required)

### `Refund ORD-XXXXX`

**What admin does:**
```
Admin: Refund ORD-20260627-0917
```

**System response:**
```
🔐 High-risk command. Confirm PIN + TOTP.
```

**Admin enters both:**
```
1234
847293
```

**System response:**
```
✅ Refund initiated.

Order: ORD-20260627-0917
Amount: ₦6,500
Refund method: Flutterwave API
Estimated arrival: 5-7 business days
Customer notified.

[Audit log: refund_executed, admin=<hash>, pin_verified, totp_verified]
```

### `Force-Refund ORD-XXXXX <reason>`

**What admin does:**
```
Admin: Force-Refund ORD-20260627-0917 customer_complaint_unresolved
```

**System response:**
```
🔐 High-risk command. Confirm PIN + TOTP.
```

**After auth:**
```
✅ Force-refund executed.

Order: ORD-20260627-0917
Amount: ₦6,500
Reason: customer_complaint_unresolved
Override eligibility: yes (admin)
Customer notified.
Admin alert logged.
```

### `Approve BAN-CLAIM-XXX`

**What admin does:**
```
Admin: Approve BAN-CLAIM-001
```

**System response:**
```
🔐 High-risk command. Confirm PIN + TOTP.
```

**After auth:**
```
✅ Ban claim approved. Generating replacement...

Order: ORD-20260627-0917
New IP: 185.123.45.99 (different from banned 185.123.45.67)
Credentials sent to customer.
Old proxy marked: replaced_via_admin
```

### `Reject BAN-CLAIM-XXX <reason>`

**What admin does:**
```
Admin: Reject BAN-CLAIM-001 not_actually_banned
```

**System response:**
```
🔐 High-risk command. Confirm PIN + TOTP.
```

**After auth:**
```
✅ Ban claim rejected.

Order: ORD-20260627-0917
Reason: not_actually_banned
Customer notified with reason.
```

### `Revoke Trial <user_id>`

**What admin does:**
```
Admin: Revoke Trial trial_a7b9c2
```

**System response:**
```
🔐 High-risk command. Confirm PIN + TOTP.
```

**After auth:**
```
✅ Trial revoked.

User: trial_a7b9c2
Reason: admin_revoke
3proxy credentials removed.
Phone_hash added to blocklist (optional — confirm?)

Reply 'yes' to add block, 'no' to just revoke this trial.
```

---

## Logout Commands

### `Admin Status` (already covered)

### `Admin Logout`

**What admin does:**
```
Admin: Admin Logout
```

**System response:**
```
✅ Admin session ended.

Next command requires PIN re-entry.
```

---

## Emergency Commands

### `Pause Everything`

**What admin does:**
```
Admin: Pause Everything
```

**System response:**
```
🔐 CRITICAL command. Confirm PIN + TOTP.

⚠️ This will:
- Stop n8n (all webhooks return 503)
- Stop 3proxy (all trial proxies stop working)
- Alert customers that Bunche is paused

Continue? (yes/no)
```

After auth + yes:
```
🔴 Bunche PAUSED.

Status: Webhooks 503, 3proxy stopped, customers notified.

To resume: "Resume Everything" (requires same auth)
```

### `Resume Everything`

**What admin does:**
```
Admin: Resume Everything
```

Same auth + execute:
```
🟢 Bunche RESUMED.

n8n started, 3proxy started, webhooks accepting.

Customers can resume orders.
```

---

## Critical Rules Locked

| # | Rule | Source |
|---|------|--------|
| 1 | Session timeout: 30 min inactivity | WORKFLOW_SPECS §3 |
| 2 | Lockout × 3 failed PIN: 15 min | WORKFLOW_SPECS §3 |
| 3 | Lockout × 5 failed PIN: 1 hour | WORKFLOW_SPECS §3 |
| 4 | Lockout × 10 failed PIN: 24 hours | WORKFLOW_SPECS §3 |
| 5 | TOTP window: ±1 interval (30 sec each way) | This doc + WORKFLOW_SPECS §3 |
| 6 | TOTP secret encrypted with AES-256-GCM before storage | This doc |
| 7 | All admin commands logged to admin_commands_log | SECURITY_PLAN |
| 8 | Low-risk = session only | WORKFLOW_SPECS §3 |
| 9 | Medium-risk = fresh PIN (2 min) | WORKFLOW_SPECS §3 |
| 10 | High-risk = PIN + TOTP | WORKFLOW_SPECS §3 |
| 11 | Critical (pause) = PIN + TOTP + confirmation | This doc |
| 12 | Failed lockouts trigger admin alert via WhatsApp | SECURITY_RUNBOOK |
| 13 | TOTP secret NEVER logged, only used for verify | This doc |

---

## Admin Command Risk Matrix

| Command | Risk | Auth | Notes |
|---------|------|------|-------|
| Daily Summary | Low | Session | Auto-sent anyway via cron |
| Errors | Low | Session | - |
| Provider Status | Low | Session | - |
| Trial Stats | Low | Session | - |
| Referral Stats | Low | Session | - |
| Pending | Low | Session | Read-only |
| Admin Status | Low | Session | - |
| Admin Logout | Low | Session | - |
| Block phone | Medium | Fresh PIN | 30-day default block |
| Unblock phone | Medium | Fresh PIN | - |
| Resolve error | Medium | Fresh PIN | - |
| Details order | Medium | Fresh PIN | Read-only |
| Refund order | High | PIN + TOTP | - |
| Force-Refund | High | PIN + TOTP | Override eligibility |
| Approve ban claim | High | PIN + TOTP | - |
| Reject ban claim | High | PIN + TOTP | - |
| Revoke trial | High | PIN + TOTP | - |
| Pause Everything | Critical | PIN + TOTP + confirm | Stops Bunche |
| Resume Everything | Critical | PIN + TOTP | Restarts Bunche |

---

## Database Schema (Admin)

```sql
CREATE TABLE admin_users (
    id SERIAL PRIMARY KEY,
    phone_hash VARCHAR(20) UNIQUE NOT NULL,
    pin_hash VARCHAR(255) NOT NULL,
    totp_secret_encrypted TEXT,                   -- AES-256-GCM encrypted
    failed_pin_attempts INT DEFAULT 0,
    locked_until TIMESTAMPTZ,
    last_login_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE admin_commands_log (
    id SERIAL PRIMARY KEY,
    admin_phone_hash VARCHAR(20),
    command VARCHAR(100),
    risk_level VARCHAR(20),
    auth_method VARCHAR(50),
    target_id VARCHAR(50),                         -- order_id, user_id, phone_hash, etc.
    result VARCHAR(20),
    executed_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_admin_commands_log_admin ON admin_commands_log(admin_phone_hash, executed_at);
CREATE INDEX idx_admin_commands_log_command ON admin_commands_log(command, executed_at);
```

---

## npm Dependencies (in n8n)

Add to n8n's package.json (via `docker exec -it n8n bash && npm install ...`):

```json
{
  "dependencies": {
    "bcrypt": "^5.1.0",
    "speakeasy": "^2.0.0",
    "qrcode": "^1.5.3",
    "crypto": "1.0.0"  // built-in
  }
}
```

---

## Related

- `workflows/WORKFLOW_SPECS.md` §3 — Admin Command Handler spec
- `docs/SECURITY_RUNBOOK.md` — Incident response
- `docs/PHONE_HASH_BLOCKING.md` — Block mechanism
- `scenarios/2026-06-26-first-time-order.md` — Customer-side flow (paired with admin)
- `docs/BUNCHE_LOGGER_SCHEMA.md` — admin_command_executed event schema