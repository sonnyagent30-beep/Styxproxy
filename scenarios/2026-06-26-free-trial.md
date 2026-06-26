# Bunche — Scenario Replay: Free Trial (Public Proxy)

**Date captured:** 2026-06-26
**Source:** Live roleplay session between Dannion (customer) and Sonny (as Bunche)
**Status:** Rules extracted + locked for v3

---

## Purpose

Free trial is Bunche's customer acquisition tool. Goal: let new customers test Bunche UX with zero risk. Constraint: prevent abuse + don't promise reliability we can't deliver.

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

This free trial uses PUBLIC PROXIES from
external sources. By accepting, you agree:

❌ NOT guaranteed to work
❌ NOT guaranteed stable
❌ May stop working at any moment
❌ Not for production/critical use
❌ No replacement if proxy dies
❌ Used entirely at YOUR OWN RISK

✅ Bunche is NOT responsible for proxy
   performance during free trial
✅ For testing our service only
✅ Upgrade to paid plan for reliability

━━━━━━━━━━━━━━━━━━

Complete ONE survey to unlock your IP:

[SURVEY LINK]

After completing, reply DONE
```

**Rules extracted:**
- ✅ Free trial uses PUBLIC PROXIES (not Bunche's paid IP pool)
- ✅ Full disclaimer shown BEFORE customer accepts
- ✅ Disclaimer is explicit: 6 things it CAN'T do, 3 things it CAN
- ✅ Customer must complete survey (anti-abuse)
- ✅ Survey link + DONE reply mechanism
- ❌ No mention of "Bitlock.ai" (we're using generic survey for now)

---

### Turn 3 — Customer: `Done`

**System:**
- Verify survey completion (placeholder — real impl hits survey API)
- Check daily counter: `SELECT COUNT(*) FROM free_trials WHERE phone_hash = ? AND DATE(created_at) = CURRENT_DATE`
- If >= 3 → reject (see Turn 3a)
- Internal: pull public proxy from external source
- Test up to 10 retries (invisible to customer)
- One of two outcomes:

**Customer-facing (PROXY AVAILABLE — success path):**

```
✅ Survey verified!

━━━━━━━━━━━━━━━━━━
🌐 PUBLIC PROXY TRIAL
━━━━━━━━━━━━━━━━━━

🔗 IP: [PUBLIC_IP]
🔌 Port: [PUBLIC_PORT]
👤 User: [if required]
🔑 Pass: [if required]

⚠️ REMINDER: This is a PUBLIC proxy.
• May stop working anytime — that's normal
• Not for production use
• No replacement if it dies

🛡️ You've used [X/3] free trials today.

💡 Want reliable proxies? Reply menu to see paid plans.
```

**Customer-facing (NO PROXY AVAILABLE — failure path):**

```
⚠️ No public proxy available right now.

We'll keep trying — you'll get a WhatsApp ping the moment one works
(typically within 30 minutes).

🛡️ You've used [X/3] free trials today.

💡 Want reliable proxies now? Reply menu.
```

**Customer-facing (DAILY LIMIT HIT — turn 3a):**

```
🛡️ Daily limit reached — you've used 3/3 free trials today.

Come back tomorrow, or skip the wait with a paid plan:
• ISP UK/US: ₦6,500/mo (private, reliable)
• Residential 5GB: ₦5,000 (data never expires)
• Mobile 5GB: ₦20,000 (4G)

Reply menu to order, or wait until tomorrow for another free trial.
```

**Rules extracted (CRITICAL):**
- ❌ **NEVER show retry attempts to customer** — internal mechanics are invisible
- ✅ Max 10 retries on dead public proxy (all hidden)
- ✅ All 10 fail → "No public proxy available" + scheduled retry cron
- ✅ Customer-facing message is ONE of three clean outcomes (success / no-stock / daily-limit)
- ✅ Daily counter visible: "You've used X/3 free trials today"
- ✅ No expiration time (public proxies stop on their own)
- ✅ 3 free trials per phone number per day

---

### Turn 4 — (Optional) Customer: Proxy died / doesn't work

**Customer-facing:**

```
Yeah, that's the trade-off with public proxies — they stop working without warning.

Options:
• Wait a bit and reply retry — I'll try to grab you another
• Reply menu to see paid plans (private, reliable, guaranteed up)

🛡️ You've used [X/3] free trials today.
```

**Rules extracted:**
- Public proxies dying = expected, not a bug
- Always offer retry (counts against daily limit)
- Always upsell paid plans

---

### Turn 5 — (Optional, hours later) Customer: `retry`

**System:**
- Check daily counter — if >= 3 → reject (same Turn 3a message)
- Pull public proxy + test (up to 10 retries, invisible)
- Same outcomes as Turn 3

---

### Turn 6 — (Optional, scheduled) Background: Retry cron finds a proxy

**System (when customer phone_hash has open trial request + cron finds working proxy):**

```
✅ Got one for you!

━━━━━━━━━━━━━━━━━━
🌐 PUBLIC PROXY TRIAL
━━━━━━━━━━━━━━━━━━

🔗 IP: [PUBLIC_IP]
🔌 Port: [PUBLIC_PORT]
👤 User: [if required]
🔑 Pass: [if required]

⚠️ Public proxy — may stop anytime.

🛡️ You've used [X/3] free trials today.
```

---

## Free Trial Flow (Locked)

```
[Customer says "free trial" / "free plan"]
   ↓
[Show disclaimer — customer reads]
   ↓
[Customer agrees (implied by continuing) + survey link]
   ↓
[Customer replies DONE]
   ↓
[Verify survey completion]
   ↓
[Check daily counter — 3/3 hit? → reject]
   ↓
[Pull public proxy from external source]
   ↓
[Test #1]
   ❌ → pull another → Test #2
   ❌ → pull another → Test #3
   ... (up to 10 attempts, ALL invisible to customer)
   ↓
   ┌─────────────────────────────────────────┐
   │ Final outcome                           │
   ├─────────────────────────────────────────┤
   │ ✅ Got working proxy → Deliver           │
   │ ❌ All 10 failed → Tell customer         │
   │    + Schedule retry cron (every 30 min)  │
   └─────────────────────────────────────────┘
```

---

## Daily Limit Logic

```sql
-- Before any free trial attempt:
SELECT COUNT(*) AS trials_today
FROM free_trials
WHERE phone_hash = ?
  AND created_at >= CURRENT_DATE;

-- If trials_today >= 3 → reject with daily limit message
-- Else → proceed with proxy fetch
```

**What counts as a "trial":**
- A trial where a proxy was successfully delivered to the customer
- Failed attempts (no proxy available) DO count (prevents "let me spam retry until something works" abuse)

---

## Retry Cron (When All 10 Fail)

```sql
-- Insert into retry_queue when all 10 fail:
INSERT INTO free_trial_retry_queue
  (phone_hash, requested_at, status, retry_count)
VALUES
  (?, NOW(), 'pending', 0);

-- Cron: every 30 minutes
SELECT phone_hash
FROM free_trial_retry_queue
WHERE status = 'pending'
  AND requested_at > NOW() - INTERVAL '24 hours';

-- For each:
--   1. Check daily counter — if >= 3 → mark as 'expired'
--   2. Try to fetch + test public proxy
--   3. If success → send WhatsApp notification to customer + mark as 'delivered'
--   4. If fail → increment retry_count, leave as 'pending'
```

**Cleanup:** Remove queue entries older than 24 hours (customer can re-request by messaging again).

---

## Public Proxy Source

**Where do public proxies come from?**

Options:
- Public proxy lists (free-proxy-list.net, hide-my-ip free lists)
- Free-tier API from a paid provider (e.g., Proxy-Seller's 500MB/3-day trial)
- Bunche's own pool of "demo" IPs

**Decision: TBD.** Free tier API is most reliable. Free lists are flaky.

**For now:** Placeholder — Bunche uses whatever proxy source is configured in `.env` as `FREE_PROXY_API_URL`.

---

## Database Schema (New)

```sql
CREATE TABLE free_trials (
    id SERIAL PRIMARY KEY,
    phone_hash VARCHAR(20) NOT NULL,
    order_id VARCHAR(30) UNIQUE,                  -- TRIAL-20260627-1042
    survey_provider VARCHAR(50),                  -- 'bitlock', 'cpa', 'manual', etc.
    survey_completion_id VARCHAR(100),            -- provider's verification ID
    proxy_ip VARCHAR(45),
    proxy_port INT,
    proxy_user VARCHAR(50),
    proxy_pass_encrypted TEXT,                    -- AES-256-GCM if applicable
    proxy_source VARCHAR(100),                    -- which provider API
    delivered_at TIMESTAMPTZ,
    customer_reported_dead BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_free_trials_phone_date
  ON free_trials(phone_hash, created_at);

CREATE TABLE free_trial_retry_queue (
    id SERIAL PRIMARY KEY,
    phone_hash VARCHAR(20) NOT NULL,
    requested_at TIMESTAMPTZ DEFAULT NOW(),
    status VARCHAR(20) DEFAULT 'pending',          -- 'pending', 'delivered', 'expired'
    retry_count INT DEFAULT 0,
    delivered_at TIMESTAMPTZ,
    INDEX idx_retry_status (status, requested_at)
);
```

---

## Critical Rules Locked

| # | Rule | Where it lives |
|---|------|---------------|
| 1 | Free trial uses PUBLIC PROXIES, not paid Bunche IP pool | WORKFLOW_SPECS §8 |
| 2 | Full disclaimer shown BEFORE customer accepts trial | WORKFLOW_SPECS §8 |
| 3 | Disclaimer includes 6 "can't" + 3 "can" | WORKFLOW_SPECS §8 |
| 4 | Customer must complete survey + reply DONE | WORKFLOW_SPECS §8 |
| 5 | Max 10 retries on dead proxy (ALL invisible to customer) | WORKFLOW_SPECS §8 |
| 6 | Customer NEVER sees internal retry mechanics | WORKFLOW_SPECS §8 |
| 7 | All 10 retries fail → "No proxy available" + schedule retry cron | WORKFLOW_SPECS §8 |
| 8 | Retry cron runs every 30 min | WORKFLOW_SPECS §8 |
| 9 | When retry succeeds, send WhatsApp notification to customer | WORKFLOW_SPECS §8 |
| 10 | **3 free trials per phone number per day** | WORKFLOW_SPECS §8 |
| 11 | Failed attempts COUNT toward daily limit (anti-abuse) | WORKFLOW_SPECS §8 |
| 12 | Daily counter visible to customer ("X/3 used") | WORKFLOW_SPECS §8 |
| 13 | NO expiration time on free trial proxy (public proxies die on their own) | WORKFLOW_SPECS §8 |
| 14 | When public proxy dies mid-use, Bunche tells customer it's expected | WORKFLOW_SPECS §8 |
| 15 | Always upsell paid plans when free proxy fails | WORKFLOW_SPECS §8 |

---

## What This Means for Costs

| Scenario | Cost to Bunche |
|----------|---------------|
| Free trial succeeds | ~$0 (using public/free-tier proxy) |
| Free trial fails after 10 retries | $0 (just time spent, no IP purchased) |
| Customer upgrades after trial | $$$ — this is the ROI |
| Customer abuses daily limit | $0 (rejected) |

**ROI:** Free trial is essentially free. Conversion to paid = revenue.

---

## Edge Cases NOT Covered

| Case | What should happen |
|------|-------------------|
| Customer has 0 trials left but asks for one | Daily limit message + show paid plans |
| Customer waits hours after "no proxy" notification | Cron finds proxy → sends WhatsApp if customer is in `retry_queue` |
| Customer sends DONE without actually doing survey | Survey verification fails → ask to actually complete |
| Customer tries different numbers to bypass daily limit | Phone hash + phone validation (NDPR concerns) — defer |
| Public proxy works for 5 min then dies | Customer reports dead → standard "expected for public" response |
| Customer wants 5GB free trial | NOT offered — free trial is single IP, not data |

---

## Admin Visibility

Daily summary should include:
```
🎁 Free trials today: X delivered, Y failed (10-retry exhaustion)
🛡️ Top trial-abusing phones: [phone hash] (3/3 daily limit hit X times)
📊 Trial → paid conversion: X% (track via orders from trial phone_hash)
```

---

## Related

- `workflows/WORKFLOW_SPECS.md` §8 — Free Trial flow
- `scenarios/2026-06-26-first-time-order.md` — paid first-time flow
- `docs/SECURITY_RUNBOOK.md` §4 — incident response for proxy issues
- `legal/ACCEPTABLE_USE_POLICY.md` — AUP covers "no refunds on free trials"