# Bunche Scenario Review — TODO Tracker

**Last Updated:** 2026-06-27
**Repo:** sonnyagent30-beep/bunche
**Status:** In progress — reviewing scenarios 1-41 one by one

---

## HOW TO USE THIS FILE

- Mark `✅ DONE` when reviewed and approved by Dannion
- Mark `❌ NEEDS FIX` + note the change needed
- This file lives in the project folder — survives memory loss
- Always check this before resuming review sessions

---

## SCENARIO REVIEW LOG

| # | Scenario | Status | Notes |
|---|---------|--------|-------|
| 1 | First-time order (greeting → IP delivery) | ✅ DONE | Pre-payment check = ALL providers |
| 2 | Provider down (pre-payment) | ✅ DONE | Check both Proxy-Seller + DataImpulse |
| 3 | New number / account recovery | ✅ DONE | BOTH name + PIN required |
| 4 | Forgot PIN | ✅ DONE | Order details verification |
| 5 | Free trial (3proxy + Theorem Reach) | ✅ DONE | Disclaimer first |
| 6 | Ban claim | ✅ DONE | Pending queue → admin review |
| 7 | Referral | ✅ DONE | 5% credit on payment |
| 8 | Data alerts (80% / 100%) | 🔄 PENDING | — |
| 9 | Daily summary (23:55 cron) | 🔄 PENDING | — |
| 10 | Error alert (workflow fail) | 🔄 PENDING | — |
| 11 | Dead IP (1-3 retries → success) | 🔄 PENDING | — |
| 12 | All 4 IPs fail → auto-refund | 🔄 PENDING | — |
| 13 | STOP from old phone → reverse link + lock | 🔄 PENDING | — |
| 14 | Slow proxy complaint | 🔄 PENDING | — |
| 15 | Multi-product cart | 🔄 PENDING | — |
| 16 | Returning customer (same phone) | 🔄 PENDING | — |
| 17 | Order status check (paid, no IP) | 🔄 PENDING | — |
| 18 | Renewal request | 🔄 PENDING | — |
| 19 | Top-up GB | 🔄 PENDING | — |
| 20 | How to use / setup guide | 🔄 PENDING | — |
| 21 | Slow proxy complaint | 🔄 PENDING | — |
| 22 | Multi-product cart (2+ products) | 🔄 PENDING | — |
| 23 | Custom country request | 🔄 PENDING | — |
| 24 | Bulk pricing inquiry | 🔄 PENDING | — |
| 25 | Business invoice request | 🔄 PENDING | — |
| 26 | Late refund dispute (after 24hrs) | 🔄 PENDING | — |
| 27 | Trial credentials shared publicly | 🔄 PENDING | — |
| 28 | Abusive / spam messages | 🔄 PENDING | — |
| 29 | Price negotiation | 🔄 PENDING | — |
| 30 | API access inquiry | 🔄 PENDING | — |
| 31 | SOCKS5 vs HTTP inquiry | 🔄 PENDING | — |
| 32 | Dedicated / private IP request | 🔄 PENDING | — |
| 33 | Old customer returns (no PIN) | 🔄 PENDING | — |
| 34 | Payment link regeneration | 🔄 PENDING | — |
| 35 | Wrong amount paid | 🔄 PENDING | — |
| 36 | Flutterwave payment failure | 🔄 PENDING | — |
| 37 | Mobile 30-day window warning | 🔄 PENDING | — |
| 38 | Admin pause during active order | 🔄 PENDING | — |
| 39 | Refund policy explicit question | 🔄 PENDING | — |
| 40 | NDPR data access request | 🔄 PENDING | — |
| 41 | Old customer returns (with PIN) | 🔄 PENDING | — |

---

## GITHUB FILE LOCATIONS

| File | Path |
|------|------|
| Complete walkthrough (1-10 + admin table) | `scenarios/2026-06-27-complete-scenario-walkthrough.md` |
| Extended scenarios 11-15 | `scenarios/2026-06-26-first-time-order.md` through `scenarios/2026-06-26-free-trial.md` |
| Extended scenarios 16-41 | `scenarios/2026-06-27-scenarios-16-to-40.md` |

**After all 41 reviewed:** Merge into single `SCENARIOS.md` master document

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

---

## NEXT SESSION — PICK UP FROM

Start at **Scenario 8** in the review log above.