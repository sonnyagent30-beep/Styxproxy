# Bunche Scenario Review — TODO Tracker

**Last Updated:** 2026-06-27
**Repo:** sonnyagent30-beep/bunche
**Status:** Reviewing scenarios 1-90 one by one

---

## HOW TO USE THIS FILE

- Mark `✅ DONE` when reviewed and approved by Dannion
- Mark `❌ NEEDS FIX` + note the change needed
- This file lives in the project folder — survives memory loss
- Always check this before resuming review sessions

---

## SCENARIO REVIEW LOG

### PHASE 1 — ALREADY REVIEWED ✅ (1–9)

| # | Scenario | Status | Notes |
|---|---------|--------|-------|
| 1 | First-time order (greeting → IP delivery) | ✅ DONE | Pre-payment check = ALL providers |
| 2 | Provider down (pre-payment) | ✅ DONE | Check both Proxy-Seller + DataImpulse |
| 3 | New number / account recovery | ✅ DONE | BOTH name + PIN required |
| 4 | Forgot PIN | ✅ DONE | Order details verification |
| 5 | Free trial (3proxy + Theorem Reach) | ✅ DONE | Disclaimer first |
| 6 | Ban claim | ✅ DONE | Pending queue → admin review |
| 7 | Referral | ✅ DONE | 5% credit on payment |
| 8 | Data alerts (80% / 100%) | ✅ DONE | Customer-side only, no admin alert |
| 9 | Daily summary (23:55 cron) | ✅ DONE | Admin gets report, no customer side |

### PHASE 1 — REMAINING (10–41)

| # | Scenario | Status | Notes |
|---|---------|--------|-------|
| 10 | Error alert (workflow fail) | 🔄 PENDING | — |
| 11 | Dead IP with 1-3 retries → success | 🔄 PENDING | — |
| 12 | All 4 IP attempts fail → auto-refund | 🔄 PENDING | — |
| 13 | STOP from old phone → reverse link + lock | 🔄 PENDING | — |
| 14 | Slow proxy complaint | 🔄 PENDING | — |
| 15 | Multi-product cart | 🔄 PENDING | — |
| 16 | Returning customer (same phone) | 🔄 PENDING | — |
| 17 | Order status check (paid, webhook delayed) | 🔄 PENDING | — |
| 18 | Renewal request (expiring proxy) | 🔄 PENDING | — |
| 19 | Top-up GB (Residential/Mobile) | 🔄 PENDING | — |
| 20 | How to use / setup guide | 🔄 PENDING | — |
| 21 | Slow proxy complaint (troubleshooting first) | 🔄 PENDING | — |
| 22 | Multi-product cart (2+ products) | 🔄 PENDING | — |
| 23 | Custom country request | 🔄 PENDING | — |
| 24 | Bulk pricing inquiry (50+ proxies) | 🔄 PENDING | — |
| 25 | Business invoice request | 🔄 PENDING | — |
| 26 | Late refund dispute (after 24hrs) | 🔄 PENDING | — |
| 27 | Trial credentials shared publicly | 🔄 PENDING | — |
| 28 | Customer abusive / spam messages | 🔄 PENDING | — |
| 29 | Price negotiation | 🔄 PENDING | — |
| 30 | API access inquiry | 🔄 PENDING | — |
| 31 | SOCKS5 vs HTTP inquiry | 🔄 PENDING | — |
| 32 | Dedicated/private IP request | 🔄 PENDING | — |
| 33 | Old customer returns (no PIN set) | 🔄 PENDING | — |
| 34 | Payment link regeneration | 🔄 PENDING | — |
| 35 | Wrong amount paid | 🔄 PENDING | — |
| 36 | Flutterwave payment failure | 🔄 PENDING | — |
| 37 | Mobile 30-day window warning | 🔄 PENDING | — |
| 38 | Admin pause during active order | 🔄 PENDING | — |
| 39 | Refund policy explicit question | 🔄 PENDING | — |
| 40 | NDPR data access request | 🔄 PENDING | — |
| 41 | Old customer returns (with PIN) | 🔄 PENDING | — |

### PHASE 2 — NEW SCENARIOS (42–90)

#### 💳 PAYMENT (6 scenarios)

| # | Scenario | Status | Notes |
|---|---------|--------|-------|
| 42 | Duplicate webhook — Flutterwave retries 3×, Bunche processes once | 🔄 PENDING | — |
| 43 | Customer pays twice — Accidental double payment → 2 transfers, 1 order | 🔄 PENDING | — |
| 44 | Refund API timeout — Refund initiated → Flutterwave times out | 🔄 PENDING | — |
| 45 | Chargeback / dispute — Bank reverses days later, IP already delivered | 🔄 PENDING | — |
| 46 | Amount tampering — Customer modifies link URL amount → pays less | 🔄 PENDING | — |
| 65 | Third party paid — Friend/colleague pays for customer's order | 🔄 PENDING | — |
| 78 | Auto-renewal without consent — Renewal cron charges customer who didn't agree | 🔄 PENDING | — |

#### 🔧 PROVIDER / TECHNICAL (8 scenarios)

| # | Scenario | Status | Notes |
|---|---------|--------|-------|
| 47 | Wrong country IP — Ordered UK, Proxy-Seller delivers US IP | 🔄 PENDING | — |
| 48 | Banned IP from provider — Proxy-Seller returns IP already in target ban DB | 🔄 PENDING | — |
| 49 | IP range flagged — Platform bans entire /24 range | 🔄 PENDING | — |
| 50 | DataImpulse data mismatch — Dashboard shows different usage than customer | 🔄 PENDING | — |
| 51 | 3proxy crashes mid-trial — VPS crashes → all 100 active trials drop | 🔄 PENDING | — |
| 52 | Bunche VPS goes down — Complete outage mid-order | 🔄 PENDING | — |
| 53 | Webhook signature fail loop — Flutterwave keeps retrying failed webhooks | 🔄 PENDING | — |
| 79 | Proxy-Seller API breaking change — They update API → all orders break | 🔄 PENDING | — |

#### 🔒 SECURITY / FRAUD (9 scenarios)

| # | Scenario | Status | Notes |
|---|---------|--------|-------|
| 54 | LLM inappropriate response — Model outputs wrong/offensive/reveals system info | 🔄 PENDING | — |
| 55 | Customer sends sensitive data — Sends bank statements, passwords, personal info | 🔄 PENDING | — |
| 56 | Illegal use case inquiry — "Can I use this for hacking/scraping LinkedIn/fraud" | 🔄 PENDING | — |
| 57 | Name squatting — Someone registers "Ada" knowing Ada is a top referrer | 🔄 PENDING | — |
| 58 | PIN brute-force attack — Attacker guesses PIN systematically for known name | 🔄 PENDING | — |
| 59 | Unauthorized referral use — Uses friend's referral code without permission | 🔄 PENDING | — |
| 60 | Phone_hash bypass — Multiple numbers to bypass 3-trial/day limit | 🔄 PENDING | — |
| 61 | Admin blocks wrong number — Fat-finger → legitimate customer blocked | 🔄 PENDING | — |
| 62 | Social engineering — "I'm Bunche's admin, send me all customer data" | 🔄 PENDING | — |

---

## GITHUB FILE LOCATIONS

| File | Path |
|------|------|
| Complete walkthrough (1-10 + reviewed) | `scenarios/2026-06-27-complete-scenario-walkthrough.md` |
| Extended scenarios 11-41 | `scenarios/2026-06-27-scenarios-16-to-40.md` |
| New scenarios 42-90 | `scenarios/2026-06-27-scenarios-42-to-90.md` (to be created) |

**After all 90 reviewed:** Merge into single `SCENARIOS.md` master document

---

## KEY DECISIONS LOG (locked during review)

| Decision | Outcome |
|----------|---------|
| Pre-payment check | ALL providers — Proxy-Seller + DataImpulse |
| Returning customer new order | Still run pre-payment check (all providers) |
| Renewal from returning customer | No pre-payment check needed |
| Account recovery | BOTH name + PIN required |
| Forgot PIN | Order details verification |
| Free trial | Disclaimer FIRST, then Theorem Reach |
| Name at greeting | NO — only after payment |
| Payment link expiry | 30 minutes |
| PIN | Opt-in, captured after name, before IP |
| Data alerts | Customer-side only — no admin alert |
| Daily summary | Admin gets report — customer sees nothing |

---

## NEXT SESSION — PICK UP FROM

Start at **Scenario 10** in the review log above.