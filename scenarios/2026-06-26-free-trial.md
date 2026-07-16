# Bunche — Scenario Replay: Free Trial (3proxy + Theorem Reach)

**Date captured:** 2026-06-26
**Source:** Live roleplay session between Dannion (customer) and Sonny (as Bunche)
**Status:** Rules extracted + locked for v3
**Last update:** Decisions 1-4 finalized — 3proxy self-hosted + Theorem Reach survey

---

## Purpose

Free trial is Bunche's customer acquisition tool. Goal: let new customers test Bunche UX with zero risk. Constraint: prevent abuse + don't promise reliability we can't deliver.

---

## Locked Decisions (This Session)

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **1. Public proxy source** | Self-hosted **3proxy** on Bunche VPS | Full control, reliable, cheap |
| **1a. Trial time limit** | **2 hours** (auto-expire via cron) | Long enough to test, short enough to limit abuse |
| **2. Survey provider** | **Theorem Reach** | Highest anti-bot (behavioral), highest payout ($1-4/survey), API-first |
| **2a. Validation** | HMAC-signed postback + status=completed only | Prevents fake completions |
| **3. NDPR/multi-number abuse** | **F: Accept the cost** | ~$0.10-$0.60/day worst case vs engineering cost |
| **4. Extra bot protection** | **None** — Theorem Reach built-in is enough (~95% block rate) | Cost-benefit doesn't justify |

---

## The Scenario (Verbatim)

### Customer persona: New phone, never seen, price-sensitive, wants to try before buying

---

### Turn 1 — Customer: `Hi`

**Customer-facing:** Standard first-time greeting (services + prices + legal notice + tip). Free trial NOT mentioned at this stage.

---

### Turn 2 — Customer: `Do you have a free plan, your produce seems expensive for me right now`

**Customer-facing:**

```
🎁 FREE TRIAL — DISCLAIMER

Before we send your free IP, please read:

━━━━━━━━━━━━━━━━━━
⚠️ FREE TRIAL TERMS ⚠️
━━━━━━━━━━━━━━━━━━

This free trial uses a Bunche-hosted proxy
shared with other trial users. By accepting, you agree:

❌ NOT for production/critical use
❌ Not guaranteed private (shared with other trials)
❌ IP shared = if one user misbehaves, IP could get flagged
❌ No replacement if proxy dies or expires
❌ Used entirely at YOUR OWN RISK

✅ Bunche-hosted proxy — generally reliable
✅ Auto-expires after 2 hours
✅ For testing our service only
✅ Upgrade to paid plan for reliability + privacy

━━━━━━━━━━━━━━━━━━

Complete ONE survey to unlock your IP:

[SURVEY LINK]

After completing, reply DONE
```

**Rules extracted:**
- ✅ Free trial uses Bunche VPS 3proxy (NOT public proxies, NOT paid Bunche pool)
- ✅ Updated disclaimer reflects self-hosted (no longer "may stop anytime")
- ✅ Customer must complete Theorem Reach survey (anti-abuse)
- ✅ Survey link + DONE reply mechanism
- ✅ 2-hour TTL (not 30 min, not no-time-limit)

---

### Turn 3 — Customer: `Done`

**System (backend, invisible to customer):**

```
1. Verify survey completion via Theorem Reach postback OR DONE reply
   ↓
2. Check daily counter:
   SELECT COUNT(*) FROM free_trials
   WHERE phone_hash = ? AND DATE(created_at) = CURRENT_DATE;
   ↓
3. If >= 3 → reject (daily limit)
   ↓
4. Generate unique trial user_id: trial_a7b9c2 (16 chars alphanumeric)
   ↓
5. Generate random password: 16 chars
   ↓
6. Add to 3proxy config with TTL 2hr
   ↓
7. Save to free_trials table:
   - order_id = TRIAL-20260627-1042
   - phone_hash, user_id, password_hash
   - proxy_ip = VPS_PUBLIC_IP
   - proxy_port = next available (8001-8100)
   - expires_at = NOW() + 2 hours
   - survey_transaction_id = from Theorem Reach
   - survey_payout_usd = 1.50 (recorded)
   ↓
8. Cron schedules credential cleanup at expires_at
   ↓
9. Audit log: free_trial_delivered
```

**Customer-facing (PROXY READY — success path):**

```
✅ Survey verified! Trial ready.

━━━━━━━━━━━━━━━━━━
🌐 BUNCHE TRIAL PROXY — 2 HOURS
━━━━━━━━━━━━━━━━━━

🔗 IP: styxproxy.com
🔌 Port: 8001
👤 User: trial_a7b9c2
🔑 Pass: Kx9mNp2qR8sT4wY7

⏰ Expires: [current time + 2hrs]

⚠️ Shared proxy — other trial users share this IP.
For private/production use, upgrade to a paid plan.

🛡️ You've used [X/3] free trials today.

💡 Want reliable private proxies? Reply menu to see paid plans.
```

**Customer-facing (NO PROXY AVAILABLE — port exhaustion, all 100 in use):**

```
⚠️ All trial slots busy right now.

We'll ping you the moment one opens up (usually within 30 minutes).

🛡️ You've used [X/3] free trials today.

💡 Want reliable proxies now? Reply menu.
```

**Customer-facing (DAILY LIMIT HIT):**

```
🛡️ Daily limit reached — you've used 3/3 free trials today.

Come back tomorrow, or skip the wait with a paid plan:
• ISP UK/US: ₦6,500/mo (private, reliable)
• Residential 5GB: ₦5,000 (data never expires)
• Mobile 5GB: ₦20,000 (4G)

Reply menu to order, or wait until tomorrow for another free trial.
```

**Rules extracted (CRITICAL):**
- ❌ **NEVER show internal mechanics to customer** (retry attempts, port allocation, etc.)
- ✅ Max 1 trial granted per survey completion (no "retry 10 times" — survey is the gate)
- ✅ Daily limit visible: "You've used X/3 free trials today"
- ✅ 2-hour TTL displayed explicitly to customer
- ✅ Remind customer proxy is shared (so they don't think it's private)

---

### Turn 4 — (Optional, hours later) Customer: `Trial died`

**Customer-facing:**

```
⏰ Your trial expired after 2 hours (or stopped working).

That's expected for free trials. Want to:

• Try another free trial (you've used [X/3] today)
• Upgrade to a paid plan (private proxies, longer-lasting)

Reply menu or trial.
```

---

### Turn 5 — (Background) Cron: 2-hour credential cleanup

**System:**

```
[Cron: every 5 minutes]
SELECT user_id, expires_at FROM free_trials
WHERE status = 'active' AND expires_at < NOW();

-- For each expired:
1. Remove from 3proxy config (user can't authenticate anymore)
2. UPDATE free_trials SET status = 'expired'
3. Audit log: free_trial_expired
```

---

## 3proxy Setup

### Install on Bunche VPS

```bash
# Install 3proxy
apt install 3proxy -y

# Or build from source (more control):
# https://github.com/3proxy/3proxy

# Generate Bunche trial config
cat > /etc/3proxy/bunche-trial.cfg << 'EOF'
#!/usr/local/3proxy/bin/3proxy

# Trial proxy configuration
daemon
pidfile /var/run/3proxy-bunche.pid
nscache 65536
nserver 8.8.8.8

# Authentication: username/password
auth strong
users trial_a7b9c2:CL:bcrypt_hash_here
users trial_x9k2m4p:CL:bcrypt_hash_here
# ... up to 100 users

# Allow only authenticated users
allow trial_*

# HTTP/HTTPS proxy on ports 8001-8100
external YOUR_VPS_IP
internal 0.0.0.0
flip $0
no log

# Trial sessions expire after 2hr (handled by cron removing users)
proxy -p8001-8100
EOF

# Run
3proxy /etc/3proxy/bunche-trial.cfg
```

### Dynamic user management

n8n workflow (or cron + script) adds/removes users from `users trial_XXX:CL:hash` line based on `free_trials` table state.

**Add user (on trial delivery):**
```bash
# Generate: openssl rand -hex 8
USERNAME="trial_$(openssl rand -hex 4)"
PASSWORD="$(openssl rand -hex 8)"
HASH=$(3proxy --help 2>&1 | grep -i crypt | head -1 || echo "plaintext")

# Append to config
echo "users ${USERNAME}:CL:${PASSWORD}" >> /etc/3proxy/bunche-trial.cfg
```

**Remove user (on trial expiry):**
```bash
# Find and remove the line
sed -i "/^users ${USERNAME}:/d" /etc/3proxy/bunche-trial.cfg

# Reload 3proxy
kill -HUP $(cat /var/run/3proxy-bunche.pid)
```

---

## Theorem Reach Setup

### Account setup

1. Sign up at theoremreach.com
2. Get API key + survey wall URL
3. Configure postback URL: `https://n8n.yourdomain.com/webhook/theorem-reach`
4. Get HMAC secret for postback signature verification

### Webhook handler (n8n workflow)

```javascript
// POST /webhook/theorem-reach
// Body:
// {
//   "user_id": "trial_a7b9c2",
//   "survey_id": "SRV-12345",
//   "status": "completed",
//   "payout_usd": 1.50,
//   "transaction_id": "TR-987654",
//   "signature": "abc123..."
// }

const crypto = require('crypto');

// 1. Verify HMAC signature
const expectedSig = crypto
  .createHmac('sha256', process.env.THEOREM_REACH_SECRET)
  .update(JSON.stringify({
    user_id: req.body.user_id,
    transaction_id: req.body.transaction_id,
    payout_usd: req.body.payout_usd
  }))
  .digest('hex');

if (req.body.signature !== expectedSig) {
  return { statusCode: 401, body: 'Invalid signature' };
}

// 2. Check status
if (req.body.status !== 'completed') {
  return { statusCode: 200, body: 'Survey not completed' };
}

// 3. Check idempotency
const existing = await db.query(
  'SELECT id FROM free_trials WHERE survey_transaction_id = $1',
  [req.body.transaction_id]
);
if (existing.length > 0) {
  return { statusCode: 200, body: 'Already processed' };
}

// 4. Generate trial credentials
// ... (call 3proxy add-user logic)
// ... (save to free_trials table)
// ... (send WhatsApp to customer with credentials)

return { statusCode: 200, body: 'Trial granted' };
```

---

## Daily Limit Logic

```sql
-- Before granting trial:
SELECT COUNT(*) AS trials_today
FROM free_trials
WHERE phone_hash = ?
  AND created_at >= CURRENT_DATE
  AND status IN ('active', 'expired');

-- If trials_today >= 3 → reject with daily limit message
-- Else → proceed with 3proxy credential generation
```

**What counts:**
- Granted trials (status = 'active' or 'expired')
- **Does NOT count:** Failed attempts (survey not completed, port exhaustion)

---

## Database Schema

```sql
CREATE TABLE free_trials (
    id SERIAL PRIMARY KEY,
    phone_hash VARCHAR(20) NOT NULL,
    order_id VARCHAR(30) UNIQUE,                  -- TRIAL-20260627-1042
    user_id VARCHAR(20) UNIQUE,                   -- trial_a7b9c2 (for 3proxy auth)
    password_hash VARCHAR(255),                   -- bcrypt
    proxy_ip VARCHAR(45),
    proxy_port INT,
    expires_at TIMESTAMPTZ,
    status VARCHAR(20) DEFAULT 'active',          -- 'active', 'expired', 'revoked'
    survey_provider VARCHAR(50) DEFAULT 'theorem_reach',
    survey_transaction_id VARCHAR(100),           -- idempotency key
    survey_payout_usd DECIMAL(8,2),
    survey_completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    revoked_reason VARCHAR(100)
);

CREATE INDEX idx_free_trials_phone_date
  ON free_trials(phone_hash, created_at);

CREATE INDEX idx_free_trials_status_expires
  ON free_trials(status, expires_at);

CREATE TABLE theorem_reach_postbacks (
    id SERIAL PRIMARY KEY,
    transaction_id VARCHAR(100) UNIQUE,           -- idempotency
    user_id VARCHAR(20),
    survey_id VARCHAR(50),
    status VARCHAR(20),
    payout_usd DECIMAL(8,2),
    signature VARCHAR(255),
    signature_valid BOOLEAN,
    processed_at TIMESTAMPTZ DEFAULT NOW(),
    raw_payload JSONB
);
```

---

## Critical Rules Locked

| # | Rule | Where it lives |
|---|------|---------------|
| 1 | Free trial uses self-hosted 3proxy on Bunche VPS | WORKFLOW_SPECS §8 |
| 2 | **2-hour TTL** on every trial | WORKFLOW_SPECS §8 |
| 3 | Updated disclaimer (shared proxy, not public, not private) | WORKFLOW_SPECS §8 |
| 4 | Customer must complete Theorem Reach survey + reply DONE | WORKFLOW_SPECS §8 |
| 5 | Theorem Reach postback verified via HMAC signature | WORKFLOW_SPECS §8 |
| 6 | Only `status=completed` from Theorem Reach grants trial | WORKFLOW_SPECS §8 |
| 7 | Idempotency via `survey_transaction_id` | WORKFLOW_SPECS §8 |
| 8 | Max **3 free trials per phone number per day** | WORKFLOW_SPECS §8 |
| 9 | Daily counter visible to customer ("X/3 used") | WORKFLOW_SPECS §8 |
| 10 | Customer NEVER sees internal mechanics | WORKFLOW_SPECS §8 |
| 11 | Port range 8001-8100 (max 100 concurrent trials) | WORKFLOW_SPECS §8 |
| 12 | Cron every 5 min cleans expired credentials | WORKFLOW_SPECS §8 |
| 13 | 3proxy config dynamically updated via shell script | WORKFLOW_SPECS §8 |
| 14 | Theorem Reach payout tracked in `survey_payout_usd` | WORKFLOW_SPECS §8 |

---

## What This Means for Costs (FINAL)

| Component | Cost per trial | 100 trials/day |
|-----------|----------------|----------------|
| 3proxy bandwidth | ~$0.001 | $0.10 |
| Theorem Reach (we GET paid) | -$1.50 | -$150 (revenue!) |
| Survey verification (one webhook) | $0 | $0 |
| **Net per 100 trials** | **+$1.49/trial** | **+$149/day** |

**Wait — this is REVENUE, not cost.** Theorem Reach pays us for every completed survey. Free trials become a profit center if the survey payout > trial cost (which it does, ~$1.50/trial vs $0.001 trial cost).

---

## Edge Cases NOT Covered

| Case | What should happen |
|------|-------------------|
| Customer completes survey but never replies DONE | Wait for Theorem Reach postback (don't require DONE reply) |
| 3proxy down | Tell customer "trial service temporarily unavailable, try later" + alert admin |
| All 100 ports in use | "All trial slots busy, try in 30 min" + add customer to waitlist |
| Customer shares trial credentials publicly | Revoke + block phone (anti-abuse) |
| Survey completes but customer phone is already in daily limit | Refuse grant, log attempt, no payout dispute |
| Theorem Reach postback signature invalid | Log + alert admin (possible attack) |
| Customer asks "can I get a longer trial?" | "Upgrade to paid plan — reply menu" |

---

## Admin Visibility

Daily summary should include:
```
🎁 Free trials today: X delivered, Y expired
💰 Theorem Reach revenue: $X.XX (paid to Bunche)
🛡️ Port utilization: X/100 currently active
⚠️ Signature failures: X (potential attack signal)
```

---

## Related

- `workflows/WORKFLOW_SPECS.md` §8 — Free Trial flow
- `docs/DEPLOYMENT.md` — 3proxy + Theorem Reach setup
- `.env.example` — `THEOREM_REACH_API_KEY`, `THEOREM_REACH_SECRET`
- `scenarios/2026-06-26-first-time-order.md` — paid first-time flow
- `legal/ACCEPTABLE_USE_POLICY.md` — AUP covers trial abuse