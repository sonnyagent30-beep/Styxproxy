# Bunche Scenario Review — TODO Tracker

**Last Updated:** 2026-06-27
**Repo:** sonnyagent30-beep/bunche
**Status:** ✅ ALL 90 SCENARIOS COMPLETE ✅

---

## ✅ REVIEW COMPLETE — ALL 90 SCENARIOS DONE

| Tier | Count | Status |
|------|-------|--------|
| Phase 1 (Scenarios 1-9, 43, 45) | 12 | ✅ DONE |
| 🔴 Critical Tier 1 | 7 | ✅ DONE |
| 🟠 High Tier 2 | 17 | ✅ DONE |
| 🟡 Medium Tier 3 | 54 | ✅ DONE |
| **Total** | **90** | **✅ COMPLETE** |

---

## SCENARIO REVIEW LOG

### ✅ Phase 1 — Scenarios 1-9, 43, 45

| # | Scenario | Notes |
|---|---------|-------|
| 1 | First-time order | Pre-payment check = ALL providers |
| 2 | Provider down | Check both Proxy-Seller + DataImpulse |
| 3 | New number / account recovery | BOTH name + PIN required |
| 4 | Forgot PIN | Order details verification |
| 5 | Free trial | Disclaimer FIRST, then Theorem Reach |
| 6 | Ban claim | Pending queue → admin review |
| 7 | Referral | 5% credit on payment |
| 8 | Data alerts | Customer-side only, no admin alert |
| 9 | Daily summary | Admin gets report, customer sees nothing |
| 43 | Double payment | Auto-refund second payment immediately |
| 45 | Chargeback / dispute | Investigate first → partial if live, full if dead, deny if repeat |

---

### ✅ 🔴 PRIORITY TIER 1 — CRITICAL (7/7)

| # | Scenario | Decision |
|---|---------|---------|
| 46 | Amount tampering | HMAC + server-side verification → auto-refund |
| 58 | PIN brute-force attack | Escalating: 15min → 24hr → blacklist |
| 60 | Phone_hash bypass | Behavioral detection: 3+ phones/IP/hr → flag + block |
| 61 | Admin blocks wrong number | Pre-check + PIN/TOTP + customer UNBLOCK |
| 62 | Social engineering | Laugh-off + admin notification |
| 64 | Impersonation refund | Name+PIN + proxy check + 24hr cutoff |
| 77 | Trial then lie | Webhook verification + order ID check |

---

### ✅ 🟠 PRIORITY TIER 2 — HIGH (17/17)

| # | Scenario | Decision |
|---|---------|---------|
| 10 | Workflow fail | Customer "something went wrong" → admin alert → resolve/refund |
| 11 | Dead IP 1-3 retries → success | Completely invisible to customer |
| 12 | All 4 IPs dead → auto-refund | Auto-refund, customer notified |
| 13 | STOP from old phone | Reverse + lock + appeal + 3-day review + both numbers banned |
| 42 | Duplicate webhook | Idempotency key — silently ignored |
| 44 | Refund API timeout | Mark pending → check 5min → retry → admin if stuck |
| 47 | Wrong country IP | Auto-detect geo + retry before delivery + customer can report |
| 48 | Banned IP (platform) | 24hr + right platform = free replacement; wrong platform = denied |
| 51 | 3proxy crash | Detect → admin alert → restore → notify + extend TTL |
| 52 | Bunche VPS down | WhatsApp queues → admin alert → restore → process queue → notify |
| 53 | Webhook signature fail | Cron monitor → >5 fails/hr → admin alert |
| 54 | LLM inappropriate | Auto-detect → reject + retry → fallback → admin alert |
| 56 | Illegal use case | Decline + offer legitimate alternatives |
| 59 | Unauthorized referral | Auto credited — no policing |
| 66 | Proxy dies within 1hr | Replace free + log provider quality → >10% = admin alert |
| 73 | Balance runs out mid-order | Auto-pause + admin alert + resume after funding |
| 79 | Proxy-Seller API breaking change | Health check → 3 fails → admin alert + pause orders |

---

### ✅ 🟡 PRIORITY TIER 3 — MEDIUM (54/54)

| # | Scenario | Decision |
|---|---------|---------|
| 14 | Slow proxy complaint | Troubleshooting first |
| 15 | Multi-product cart | Separate orders |
| 16 | Returning customer (same phone) | Skip name/PIN |
| 17 | Order status check | Expedite pending order |
| 18 | Renewal request | Extend from current expiry |
| 19 | Top-up GB | Same proxy, just more data |
| 20 | How to use / setup guide | LLM-generated |
| 21 | Slow proxy complaint | Troubleshooting first |
| 22 | Multi-product cart | Separate or combined payment |
| 23 | Custom country request | Check both providers |
| 24 | Bulk pricing inquiry | Manual admin quote |
| 25 | Business invoice request | Admin-prepared |
| 26 | Late refund dispute | Resend + ban claim + refund request |
| 27 | Trial credentials shared publicly | AUP violation |
| 28 | Customer abusive / spam | De-escalate → admin outreach |
| 29 | Price negotiation | Redirect to referral/alternatives |
| 30 | API access inquiry | Phase 2 waitlist |
| 31 | SOCKS5 vs HTTP | HTTP only |
| 32 | Dedicated / private IP | Phase 2 |
| 33 | Old customer returns (no PIN) | Order details verification |
| 34 | Payment link regeneration | Max 2 regenerations |
| 35 | Wrong amount paid | Auto-refund + new link |
| 36 | Flutterwave payment failure | Check status → deliver or reassure |
| 37 | Mobile 30-day window warning | Auto-reminder + top-up offer |
| 38 | Admin pause during active order | Reassure + resume |
| 39 | Refund policy explicit question | Full policy explained |
| 40 | NDPR data access request | Admin compiles export |
| 41 | Old customer returns (with PIN) | PIN verified immediately |
| 49 | IP range flagged | Individual claims + admin spots pattern |
| 50 | DataImpulse data mismatch | DataImpulse is source of truth |
| 55 | Customer sends sensitive data | Warning + auto-delete |
| 57 | Name squatting | Unique names — no duplicates allowed |
| 63 | Former admin tries credentials | Formal offboarding — keys rotated, audit taken |
| 65 | Third party paid | Order goes to ordering account, payer has no claim |
| 67 | Platform detects datacenter IP | Bunche delivers exactly what ordered — wrong product = recommend right plan |
| 68 | Receipt for refunded order | Credit note / cancellation receipt |
| 69 | Competitor intelligence | Deflect + never share provider info |
| 70 | Reseller inquiry | Personal use only + bulk pricing |
| 71 | DataImpulse data depletion | DataImpulse is source of truth + top-up |
| 72 | Custom proxy configuration | HTTP only — Phase 2 feature request |
| 74 | Law enforcement data request | Official letterhead + court order + legal review |
| 75 | EU customer and GDPR | NDPR applies but same data rights offered |
| 76 | Wrong product delivered | System prevents + correct if happens |
| 78 | Auto-renewal without consent | Explicit consent only — never auto-charge |
| 80 | Unsupported file sent | Screenshots only — no external links |
| 81 | Receipt to different email | Flutterwave email only |
| 82 | Cancel before payment | Link expires in 30min — just don't pay |
| 83 | Uptime SLA question | 99% target, no formal SLA |
| 84 | Data retention question | 7 years orders, 90 days chat logs |
| 85 | IP rotation question | ISP = static; Rotating = Phase 2 |
| 86 | Team/multi-device usage | One proxy per account/device, not per person |
| 87 | Protocol version question | HTTP/1.1 only |
| 88 | Bunche number flagged as spam | WhatsApp Business handles delisting; Telegram backup |
| 89 | Customer in restricted country | Telegram @bunche_ng as alternative |
| 90 | Works in browser not app | Troubleshooting first → if only Instagram = proxy detection |

---

## GITHUB FILE LOCATIONS

| File | Content |
|------|---------|
| `scenarios/2026-06-27-complete-scenario-walkthrough.md` | Scenarios 1-9 |
| `scenarios/2026-06-27-scenarios-16-to-40.md` | Scenarios 10-41 |
| `scenarios/2026-06-27-scenarios-42-to-90.md` | Scenarios 42-90 (all new scenarios) |

---

## KEY DECISIONS LOG

| Category | Decision |
|----------|---------|
| Pre-payment check | ALL providers — Proxy-Seller + DataImpulse |
| Returning customer new order | Still run pre-payment check |
| Renewal from returning customer | No pre-payment check needed |
| Account recovery | BOTH name + PIN required |
| Free trial | Disclaimer FIRST, then Theorem Reach |
| PIN | Opt-in, captured after name, before IP |
| Data alerts | Customer-side only — no admin alert |
| Daily summary | Admin gets report — customer sees nothing |
| Double payment | Auto-refund second payment immediately |
| Chargeback | Investigate first — partial if IP live, full if dead, deny if repeat abuse |
| Amount tampering | HMAC prevention + server-side verification → auto-refund |
| PIN brute-force | Escalating: 15min → 30min → 1hr → 2hr → 4hr → 8hr → 16hr → 24hr → blacklist |
| Phone_hash bypass | Behavioral detection: 3+ phones/IP/hr → flag + block |
| Admin block wrong number | Pre-check + PIN+TOTP + customer UNBLOCK |
| Social engineering | Laugh-off + admin notification |
| Impersonation refund | Name+PIN + proxy check + 24hr cutoff |
| Trial then lie | Webhook verification + order ID check |
| STOP from old phone | Reverse + lock + appeal + 3-day review + both numbers banned |
| Banned IP | 24hr + right platform = free replacement; wrong platform = denied |
| Bunche IP delivered wrong product | System prevents — never happens |
| Unique names | No duplicates allowed |
| Referral | Auto credited — no policing |
| Third party paid | Order goes to ordering account |
| Data source of truth | DataImpulse dashboard is authoritative |
| Sensitive data | Warning + auto-delete |
| Law enforcement | Official letterhead + court order + legal review |
| Customer data rights | Same rights for all customers regardless of jurisdiction |
| Auto-renewal | Explicit consent only |
| Bunche channels | WhatsApp primary, Telegram @bunche_ng backup |
| Proxy protocol | HTTP/1.1 only |
| IP type | ISP = static; Rotating = Phase 2 |

---

## 📋 NEXT: BUILD + DEPLOY

All 90 scenarios documented. Ready for:
1. Build static website (bunche-web repo)
2. Provision VPS (Hetzner CX21)
3. Execute DEPLOYMENT.md Steps 1-13
4. Soft launch: 10 friends/family test
5. Register dedicated Bunche WhatsApp number