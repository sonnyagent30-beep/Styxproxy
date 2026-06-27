# Bunche Scenario Review — TODO Tracker

**Last Updated:** 2026-06-27
**Repo:** sonnyagent30-beep/bunche
**Status:** Tier 2 🟠 HIGH COMPLETE ✅ — Moving to Tier 3 🟡

---

## HOW TO USE THIS FILE

- Mark `✅ DONE` when reviewed and approved by Dannion
- Mark `❌ NEEDS FIX` + note the change needed
- Organized by priority tier (user-specified)
- This file lives in the project folder — survives memory loss
- Always check this before resuming review sessions

---

## ✅ PHASE 1 — SCENARIOS 1-9, 43, 45

| # | Scenario | Status |
|---|---------|--------|
| 1-9 | First-time order, provider down, recovery, forgot PIN, free trial, ban claim, referral, data alerts, daily summary | ✅ DONE |
| 43 | Double payment | ✅ DONE |
| 45 | Chargeback / dispute | ✅ DONE |

---

## ✅ 🔴 PRIORITY TIER 1 — CRITICAL: COMPLETE ✅

| # | Scenario | Status | Notes |
|---|---------|--------|-------|
| 46 | Amount tampering | ✅ DONE | HMAC + server-side verification → auto-refund |
| 58 | PIN brute-force attack | ✅ DONE | Escalating: 15min → 24hr → blacklist |
| 60 | Phone_hash bypass | ✅ DONE | Behavioral detection: 3+ phones/IP/hr → flag + block |
| 61 | Admin blocks wrong number | ✅ DONE | Pre-check + PIN/TOTP + customer UNBLOCK |
| 62 | Social engineering | ✅ DONE | Laugh-off + admin notification |
| 64 | Impersonation refund | ✅ DONE | Name+PIN + proxy check + 24hr cutoff |
| 77 | Trial then lie | ✅ DONE | Webhook verification + order ID check |

---

## ✅ 🟠 PRIORITY TIER 2 — HIGH: COMPLETE ✅

| # | Scenario | Status | Notes |
|---|---------|--------|-------|
| 10 | Workflow fail | ✅ DONE | Admin alert → customer "something went wrong" |
| 11 | Dead IP 1-3 retries → success | ✅ DONE | Completely invisible to customer |
| 12 | All 4 IPs dead → auto-refund | ✅ DONE | Auto-refund, customer notified |
| 13 | STOP from old phone | ✅ DONE | Reverse + lock + appeal + 3-day review + both numbers banned during review |
| 42 | Duplicate webhook | ✅ DONE | Idempotency key = silent ignore |
| 44 | Refund API timeout | ✅ DONE | Mark pending → check in 5 min → retry → admin if still stuck |
| 47 | Wrong country IP | ✅ DONE | Auto-detect geo before delivery + customer can report |
| 48 | Banned IP (platform) | ✅ DONE | 24hr + right platform = free replacement; wrong platform = denied |
| 51 | 3proxy crash mid-trial | ✅ DONE | Detect → admin alert → restore → notify + extend |
| 52 | Bunche VPS down | ✅ DONE | WhatsApp queues + admin alert → restore → process queue + notify |
| 53 | Webhook signature fail loop | ✅ DONE | Cron monitor → >5 fails/hr → admin alert |
| 54 | LLM inappropriate response | ✅ DONE | Auto-detect → reject + retry → fallback → admin alert |
| 56 | Illegal use case | ✅ DONE | Decline + offer legitimate alternatives |
| 59 | Unauthorized referral use | ✅ DONE | Auto credited — no policing |
| 66 | Proxy dies within 1hr | ✅ DONE | Replace free + log provider quality → >10% = admin alert |
| 73 | Proxy-Seller balance runs out | ✅ DONE | Pre-check catches most + mid-order → auto-pause → admin → resume |
| 79 | Proxy-Seller API breaking change | ✅ DONE | Health check → 3 fails → admin alert with error details + pause orders |

**Total reviewed so far: 34/90**

---

## 🟡 PRIORITY TIER 3 — MEDIUM (Next: pick up from Scenario 14)

| # | Scenario | Status | Notes |
|---|---------|--------|-------|
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
| 49 | IP range flagged — Platform bans entire /24 range | 🔄 PENDING | — |
| 50 | DataImpulse data mismatch — Dashboard vs customer | 🔄 PENDING | — |
| 55 | Customer sends sensitive data | 🔄 PENDING | — |
| 57 | Name squatting | 🔄 PENDING | — |
| 63 | Former admin tries credentials | 🔄 PENDING | — |
| 65 | Third party paid | 🔄 PENDING | — |
| 67 | Platform detects datacenter IP | 🔄 PENDING | — |
| 68 | Receipt for refunded order | 🔄 PENDING | — |
| 69 | Competitor intelligence | 🔄 PENDING | — |
| 70 | Reseller inquiry | 🔄 PENDING | — |
| 71 | DataImpulse data depletion | 🔄 PENDING | — |
| 72 | Custom proxy configuration | 🔄 PENDING | — |
| 74 | Law enforcement data request | 🔄 PENDING | — |
| 75 | EU customer and GDPR | 🔄 PENDING | — |
| 76 | Wrong product delivered | 🔄 PENDING | — |
| 78 | Auto-renewal without consent | 🔄 PENDING | — |
| 80 | Unsupported file sent | 🔄 PENDING | — |
| 81 | Receipt to different email | 🔄 PENDING | — |
| 82 | Cancel before payment | 🔄 PENDING | — |
| 83 | Uptime SLA question | 🔄 PENDING | — |
| 84 | Data retention question | 🔄 PENDING | — |
| 85 | IP rotation question | 🔄 PENDING | — |
| 86 | Team/multi-device usage | 🔄 PENDING | — |
| 87 | Protocol version question | 🔄 PENDING | — |
| 88 | Bunche number flagged as spam | 🔄 PENDING | — |
| 89 | Customer in restricted country | 🔄 PENDING | — |
| 90 | Works in browser not app | 🔄 PENDING | — |

---

## GITHUB FILE LOCATIONS

| File | Path |
|------|------|
| Scenarios 1-9 | `scenarios/2026-06-27-complete-scenario-walkthrough.md` |
| Scenarios 10-41 | `scenarios/2026-06-27-scenarios-16-to-40.md` |
| Scenarios 42-90 (Tier 1 + Tier 2) | `scenarios/2026-06-27-scenarios-42-to-90.md` |

---

## KEY DECISIONS LOG

| Decision | Outcome |
|----------|---------|
| Pre-payment check | ALL providers — Proxy-Seller + DataImpulse |
| Returning customer new order | Still run pre-payment check |
| Renewal from returning customer | No pre-payment check needed |
| Account recovery | BOTH name + PIN required |
| Forgot PIN | Order details verification |
| Free trial | Disclaimer FIRST, then Theorem Reach |
| Name at greeting | NO — only after payment |
| Payment link expiry | 30 minutes |
| PIN | Opt-in, captured after name, before IP |
| Data alerts | Customer-side only — no admin alert |
| Daily summary | Admin gets report — customer sees nothing |
| Double payment | Auto-refund second payment immediately |
| Chargeback | Investigate first — partial if IP live, full if dead, deny if repeat abuse |
| Amount tampering | HMAC prevention + server-side verification → auto-refund |
| PIN brute-force | Escalating: 15min → 30min → 1hr → 2hr → 4hr → 8hr → 16hr → 24hr → blacklist |
| Phone_hash bypass | Behavioral detection: 3+ phones/IP/hr → flag + block |
| Admin block wrong number | Pre-check verifies against order → PIN+TOTP → customer UNBLOCK |
| Social engineering | Laugh-off + admin notification; admin chooses block/ban/ignore |
| Impersonation refund | Name+PIN + proxy check + 24hr cutoff → no refund on working IP |
| Trial then lie | Webhook verification + order ID cross-check |
| Workflow fail | Customer "something went wrong" → admin alert → resolve/refund |
| Dead IP 1-3 retries | Completely invisible to customer |
| STOP from old phone | Reverse + lock + security alert + appeal + 3-day admin review |
| Duplicate webhook | Idempotency key — silently ignored |
| Refund API timeout | Mark pending → check 5min → retry → admin if stuck |
| Wrong country IP | Auto-detect geo + retry before delivery + customer can report |
| Banned IP | 24hr + right platform = free replacement; wrong platform = denied |
| 3proxy crash | Detect → admin alert → restore → notify + extend TTL |
| Bunche VPS down | WhatsApp queues → admin alert → restore → process queue → notify |
| Webhook signature fail | Cron monitor → >5 fails/hr → admin alert |
| LLM inappropriate | Auto-detect → reject + retry → fallback → admin alert |
| Illegal use case | Decline + offer legitimate alternatives |
| Unauthorized referral | Auto credited — no policing |
| Proxy dies within 1hr | Replace free + log provider quality → >10% = admin alert |
| Balance runs out mid-order | Auto-pause + admin alert + resume after funding |
| Proxy-Seller API breaking change | Health check → 3 fails → admin alert + pause orders |

---

## NEXT SESSION — PICK UP FROM

**Scenario 14** (🟡 Tier 3 Medium — next in queue)