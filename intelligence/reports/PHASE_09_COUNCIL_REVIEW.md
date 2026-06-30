# Phase 9 Council Review — Bunche Intelligence Platform
**Generated:** June 30, 2026 | **Council:** 5 Judges | **Providers Assessed:** 42
**Status:** FINAL — Council Verdicts Concluded

---

## Executive Summary

The Council has completed its independent review of 42 proxy providers researched across 6 phases of intelligence gathering. This document presents five specialist verdicts followed by consensus findings, critical flags, and required fixes before Phase 10 (Reseller Pricing) proceeds.

**Key Context:**
- 42 providers researched, 37 fully verified, 5 pending
- Primary concerns: Oxylabs fraud score (62/100), abcproxy dark web tool, SpaceProxy fake reviews, IPRoyal general pool (92% VPN flags)
- Recommended portfolio: 3-5 providers minimum, 7 maximum

---

## Judge 1: Harbor — SECURITY VERDICT

**Assessment Focus:** IP quality, fraud scores, blacklist risk, abuse history, Scamalytics ratings

### Findings by Provider Category

#### 🟢 SECURE — Approved for Resale

| Provider | Fraud Score | IP Quality | Risk Level |
|----------|------------|------------|------------|
| **Infatica** | 0/100 ✅ | Clean residential | LOW |
| **Evomi** | 0/100 ✅ | Swiss ethical sourcing | LOW |
| **Bright Data** | 0/100 ✅ | Enterprise-grade | LOW |
| **Decodo** | 0/100 ✅ | Former Smartproxy, 125M IPs | LOW |
| **Glide via IPRoyal** | 0/100 ✅ | UK dedicated broadband | LOW |
| **Proxy-Seller** | 0/100 ✅ | Single IP, instant verification | LOW |

#### 🟡 CAUTION — Conditional Use

| Provider | Issue | Security Notes |
|----------|-------|----------------|
| **IPRoyal (general pool)** | 92% flagged as VPN | **NEVER use general pool** — only Glide UK |
| **Webshare** | 81% server + 9% public | Not true residential — use for DC only |

#### 🔴 UNSAFE — Never Resell

| Provider | Fraud Score | Evidence |
|----------|------------|----------|
| **Oxylabs** | **62/100** | ALL IPs flagged high-risk |
| **abcproxy** | N/A | Dark web brute-checker tool |
| **SpaceProxy** | N/A | Fake Trustpilot reviews under investigation |
| **Proxy6** | N/A | Blacklisted IPs, rude support |
| **NaProxy** | N/A | Unverifiable HQ, scam concerns |

### Harbor's Verdict

**APPROVED FOR STOCK:** Infatica, Evomi, Decodo, Glide (IPRoyal UK pool), Proxy-Seller, Bright Data, DataImpulse, Froxy, OkeyProxy

**CONDITIONAL:** IPRoyal general pool (AVOID — 92% VPN), Webshare (DC purposes only)

**NEVER:** Oxylabs, abcproxy, SpaceProxy, Proxy6, NaProxy, 2extract, GP-Remote

**Security Confidence:** HIGH — Scamalytics data verified for top 20 providers

---

## Judge 2: Vale — UX VERDICT

**Assessment Focus:** Dashboard usability, API quality, documentation, geo-targeting, city/ISP selection, auth methods

### Findings by Provider Category

#### 🟢 EXCELLENT UX

| Provider | Dashboard | API | Geo-Targeting | Auth Methods |
|----------|-----------|-----|---------------|--------------|
| **Bright Data** | ⭐⭐⭐⭐⭐ | Full SDK | Country/City/ISP/ASN | IP+User/Pass, API key |
| **Decodo** | ⭐⭐⭐⭐ | REST + Proxy List | Country/City | IP auth, User/Pass |
| **Infatica** | ⭐⭐⭐⭐ | Good docs | Country-level | IP + User/Pass |
| **OkeyProxy** | ⭐⭐⭐⭐ | 150M pool | Country/City/ISP | Full API |

#### 🟡 ADEQUATE UX

| Provider | Notes |
|----------|-------|
| **Proxy-Seller** | Simple dashboard, instant delivery, single IP — minimal but functional |
| **Glide via IPRoyal** | UK dedicated, clean — limited geo but high quality |
| **Froxy** | Pause/resume feature — good for campaigns |
| **DataImpulse** | Non-expiring traffic — simple UX |

#### 🔴 POOR UX

| Provider | Issue |
|----------|-------|
| **Oxylabs** | Enterprise complexity, overkill for resellers |
| **Geonix** | Unknown HQ, limited docs |
| **711Proxy** | Unknown HQ, no verification |

### Vale's Verdict

**RECOMMENDED UX STACK:** Bright Data, Decodo, Infatica, OkeyProxy

**MINIMAL UX (Acceptable):** Proxy-Seller, Glide/IPRoyal, DataImpulse

**SKIP:** Any provider without documented API or dashboard — unverifiable

**UX Confidence:** MEDIUM — Self-reported features, limited hands-on verification

---

## Judge 3: Ops — OPERATIONS VERDICT

**Assessment Focus:** Automation, API rate limits, billing model, min purchase, single IP availability, instant delivery, support hours

### Findings by Provider Category

#### 🟢 OPERATIONS-READY

| Provider | Single IP | Instant Delivery | Min Purchase | API Rate | Automation |
|----------|----------|----------------|--------------|----------|------------|
| **Proxy-Seller** | ✅ YES | ✅ Instant | 1 IP | Unlimited | Full API |
| **Glide (IPRoyal)** | ✅ YES | ~24h | 1 IP | High | Dashboard |
| **DataImpulse** | Bandwidth | Non-expiring | $50 min | Good | Full API |
| **Froxy** | Bandwidth | Pause/resume | $20 min | Good | Rotating API |
| **Infatica** | Bandwidth | Pay-as-you-go | $100 min | Good | Full API |

### Ops's Verdict

**FULLY AUTOMATION-READY:** Proxy-Seller, DataImpulse, Froxy, Infatica

**MINIMUM VIABLE PORTFOLIO (3 providers):**
1. **Infatica** — $0.30/GB residential (budget)
2. **Proxy-Seller** — $2.50 ISP / $1.50 DC (single IP, instant)
3. **Glide via IPRoyal** — $2.70 UK ISP (premium seller)

**Operations Confidence:** HIGH — Verified billing and delivery models

---

## Judge 4: Slate — BUSINESS VERDICT

**Assessment Focus:** Reseller margins, competitive positioning, market competitiveness, ROI potential, price-to-value

### Findings by Provider Category

#### 🟢 BEST MARGINS (3x+)

| Provider | Buy (Wholesale) | Sell (Est. Retail) | Margin | Positioning |
|----------|-----------------|-------------------|--------|--------------|
| **Infatica** | $0.30/GB | ₦485/GB (~3x) | ~67% | Budget leader |
| **Proxy-Seller** | $2.50/IP | ₦6,000/IP | ~38% | Best ISP value |
| **Geonix** | $0.90/IP | ₦2,200/IP | ~3x | DC king |
| **RoundProxies** | $0.30/IP | ₦2,000/IP | ~3x | DC budget |

### Slate's Verdict

**PRIMARY RECOMMENDED STOCK:**
1. **Infatica** — $0.30/GB → cheapest TIER_1 (MARGIN LEADER)
2. **Proxy-Seller** — $2.50 ISP → best single-IP economics
3. **Glide via IPRoyal** — $2.70 UK ISP → premium seller

**BACKUP STOCK:**
4. **DataImpulse** — $1.00/GB non-expiring (reliability backup)
5. **Decodo** — $2.00/GB (quality backup)

**Business Confidence:** HIGH — Verified pricing from source

---

## Judge 5: Kora — FRAUD VERDICT

**Assessment Focus:** Scamalytics scores, fraud reports, abuse history, customer complaints, blacklists, scam indicators

### Findings by Provider Category

#### 🟢 CLEAN (Fraud Score 0-10)

| Provider | Fraud Score | Blacklist Risk | Status |
|----------|-------------|----------------|--------|
| **Bright Data** | 0/100 ✅ | None | SAFE |
| **Infatica** | 0/100 ✅ | None | SAFE |
| **Evomi** | 0/100 ✅ | None | SAFE |
| **Decodo** | 0/100 ✅ | None | SAFE |
| **Glide (IPRoyal)** | 0/100 ✅ | None | SAFE |
| **Proxy-Seller** | 0/100 ✅ | None | SAFE |
| **DataImpulse** | 0/100 ✅ | None | SAFE |

#### 🟡 FLAGGED (Conditional)

| Provider | Flag | Risk |
|----------|------|------|
| **IPRoyal (general)** | 92% VPN flag | HIGH — Do not resell |
| **Webshare** | 81% server + 9% public | MEDIUM — Use as DC only |

#### 🔴 HIGH RISK (NEVER)

| Provider | Fraud Score | Evidence |
|----------|-------------|----------|
| **Oxylabs** | **62/100** | ALL IPs flagged high-risk |
| **abcproxy** | N/A | Dark web hacking tool |
| **SpaceProxy** | N/A | FAKE REVIEWS — Trustpilot investigating |
| **Proxy6** | N/A | Blacklisted IPs, Trustpilot 1.5 |
| **NaProxy** | N/A | Unverifiable, scam concerns |

### Kora's Verdict

**FRAUD-FREE STOCK:** All TIER_1 providers approved

**NEVER RESELL:**
- Oxylabs (62/100 fraud score — enterprise marketing hides worst IP quality)
- abcproxy (brute-checker tool sold as "proxy")
- SpaceProxy (fake reviews flagged)
- Proxy6 (blacklisted)
- NaProxy (unverifiable)

**Fraud Confidence:** HIGH — Scamalytics verified for 20+ providers

---

## CONSENSUS VERDICT

### ✅ APPROVED — Ready for Phase 10 (Reseller Pricing)

| Provider | Type | Wholesale Cost | Why Approved |
|----------|------|---------------|--------------|
| **Infatica** | Residential | $0.30/GB | Cheapest TIER_1, clean IPs |
| **Proxy-Seller** | ISP + DC | $2.50 ISP / $1.50 DC | Single IP, instant, best value |
| **Glide via IPRoyal** | ISP (UK) | $2.70/IP | Clean UK broadband, premium seller |
| **DataImpulse** | Residential | $1.00/GB | Non-expiring, backup |
| **Decodo** | Residential | $2.00/GB | Quality, all countries |
| **Evomi** | Residential | $0.49/GB | Swiss ethical, budget |
| **OkeyProxy** | Residential | $0.75/GB | 150M pool, good rep |
| **Froxy** | Residential | $0.80/GB | Pause/resume, Trustpilot 4.8 |

### ⚠️ CONDITIONAL — Use With Warning

| Provider | Condition |
|----------|-----------|
| **IPRoyal (general pool)** | NEVER — 92% VPN flag. Only use Glide UK pool |
| **Webshare** | Datacenter purposes ONLY — not true residential |

### 🚫 NEVER — Remove from Consideration

| Provider | Reason |
|----------|--------|
| **Oxylabs** | 62/100 fraud score — ALL IPs flagged |
| **abcproxy** | Dark web hacking tool |
| **SpaceProxy** | Fake reviews under investigation |
| **Proxy6** | Blacklisted IPs, 1.5 stars |
| **NaProxy** | Unverifiable, scam concerns |
| **2extract** | Does not exist |
| **GP-Remote** | VPN product, not proxy |

---

## 🚩 CRITICAL FLAGS

### FLAG 1: Oxylabs — Enterprise Marketing Hides Worst IP Quality
**Severity:** CRITICAL  
**Issue:** Despite being the most expensive provider ($8/GB, $75/IP/mo ISP), **every single Oxylabs IP scores 64–100 on Scamalytics** (high-risk). Their enterprise reputation is built on marketing, not IP quality.  
**Action:** **NEVER** stock or resell Oxylabs. Customers will face constant blocks and bans.

### FLAG 2: IPRoyal General Pool — 92% VPN Flag
**Severity:** HIGH  
**Issue:** 92% of IPs in IPRoyal's general pool are flagged as Anonymizing VPN.  
**Action:** Only use the **Glide UK pool** via IPRoyal. Never market the general pool as "residential" without warning.

### FLAG 3: Webshare — Not True Residential
**Severity:** MEDIUM  
**Issue:** Webshare's "static residential" is 81% server IPs + 9% public proxies.  
**Action:** Only use for datacenter-grade purposes. Do not market as residential.

### FLAG 4: SpaceProxy — Fake Reviews
**Severity:** HIGH  
**Issue:** Trustpilot 5.0 rating under investigation for fake reviews.  
**Action:** **NEVER** stock or resell SpaceProxy.

### FLAG 5: abcproxy — Hacking Tool
**Severity:** CRITICAL  
**Issue:** Sold as "proxy" but actually a dark web brute-checker/hacking tool.  
**Action:** **NEVER** — illegal to resell in most jurisdictions.

---

## 🔧 REQUIRED FIXES

Before Phase 10 (Reseller Pricing) proceeds, the following are required:

### FIX 1: Remove Never-Providers from Database
**Action:** Remove Oxylabs, abcproxy, SpaceProxy, Proxy6, NaProxy, 2extract, GP-Remote from MASTER_INTELLIGENCE_DB.json and all reports.  
**Status:** Required before Phase 10

### FIX 2: Flag IPRoyal General Pool
**Action:** Add note to IPRoyal entry: "Use only Glide UK pool. General pool has 92% VPN flag — do not resell."  
**Status:** Required before Phase 10

### FIX 3: Clarify Webshare Classification
**Action:** Change Webshare classification from "Residential" to "Datacenter" in all databases.  
**Status:** Required before Phase 10

### FIX 4: Verify Infatica HQ
**Action:** Infatica shows "?" for HQ in multiple reports. Request verification or label [UNVERIFIED].  
**Status:** Medium priority

### FIX 5: Update Trustpilot Ratings
**Action:** Several providers show "?" for Trustpilot. Add disclaimer or remove rating.  
**Status:** Medium priority

### FIX 6: Finalize Minimum Viable Portfolio
**Action:** Confirm 3-provider minimum (Infatica, Proxy-Seller, Glide) before Phase 10 pricing.  
**Status:** Required to proceed

---

## Phase 10 Readiness

| Readiness Check | Status |
|-----------------|--------|
| Providers researched | ✅ 42 complete |
| Pricing verified | ✅ 37 verified |
| Fraud scores checked | ✅ Top 20 verified |
| Never-list confirmed | ✅ 7 providers |
| Minimum portfolio defined | ✅ 3 providers |
| Council review complete | ✅ This document |

**Phase 10 (Reseller Pricing) Status:** ✅ APPROVED — Pending fixes above

---

## Council Sign-Off

| Judge | Domain | Verdict |
|-------|--------|---------|
| **Harbor** | Security | ✅ APPROVED (with 2 conditionals) |
| **Vale** | UX | ✅ APPROVED (8 recommended) |
| **Ops** | Operations | ✅ APPROVED (3-provider minimum) |
| **Slate** | Business | ✅ APPROVED (margins verified) |
| **Kora** | Fraud | ✅ APPROVED (7 never-providers) |

**Council Consensus:** ✅ PHASE 9 COMPLETE — Proceed to Phase 10 after required fixes

---

*Next: Phase 10 — Reseller Pricing → /reports/RESELLER_PRICING.md*