# HARBOR SECURITY VERDICT — Phase 9 Council Review
## Bunche Proxy Intelligence Platform
**Date:** June 30, 2026
**Task:** Security judgment on proxy provider intelligence for Bunche Harbor operations

---

## EXECUTIVE VERDICT

### 🚫 SUPPLY CHAIN EXCLUSION — IMMEDIATE

| Provider | Reason | Risk Level |
|----------|--------|------------|
| **abcproxy** | Dark web hacking tool (brute checker sold on forums) | **CRITICAL** |
| **oxylabs** | Scamalytics 62/100 fraud score (62% fraudulent traffic) | **CRITICAL** |
| **proxy6** | Trustpilot 1.5/5, blacklisted IPs, scam concerns | **HIGH** |
| **spaceproxy** | Fake reviews under investigation, Russia jurisdiction | **HIGH** |
| **naproxy** | Scam detector flags, Hong Kong jurisdiction | **HIGH** |

**VERDICT:** These 5 providers must be EXCLUDED from Bunche's supply chain. Reselling these proxies exposes Bunche to:
- Reputation damage (abcproxy associated with credential theft)
- Customer fraud losses (oxylabs high-fraud IPs trigger target site blocks)
- Legal liability (spaceproxy Russia jurisdiction)
- Chargeback fraud (no-refund providers)

---

## PHASE 6-8 FINDINGS ANALYSIS

### Phase 6 — Policy Review (KYC, Refund, ToS)

#### KYC EXPOSURE MATRIX

| Provider | KYC Required | Risk Assessment |
|----------|-------------|----------------|
| Bright Data | Yes (Enterprise) | ✅ Verifiable corporate |
| Oxylabs | Yes (Corporate) | ⚠️ High-risk customers |
| IPRoyal | Partial (Email) | ⚠️ Low barrier |
| Smartproxy/Decodo | Partial | ⚠️ Low barrier |
| DataImpulse | No | ✅ Anonymous acceptable |
| V-Proxies | No | ✅ Anonymous acceptable |

**HARBOR ASSESSMENT:** KYC requirements create customer friction but reduce fraud risk. For Bunche:
- **Low-value orders (<₦50K):** Email + payment verification only
- **Medium-value (₦50K-₦500K):** Phone + email
- **High-value (>₦500K):** Require ID verification

#### REFUND POLICY RISKS

| Provider | Refund Policy | Bunche Business Risk |
|----------|---------------|----------------------|
| IPFoxy | **NO REFUNDS** | ⚠️ Customer chargebacks |
| ProxyMesh | No refund | ⚠️ Dispute risk |
| SpaceProxy | Not detailed | ⚠️ Unknown exposure |
| IPRoyal | 24-hour window | ✅ Manageable |
| Webshare | 2-day window | ✅ Low risk |
| Smartproxy | 14-day window | ✅ Customer-friendly |

**HARBOR ASSESSMENT:** No-refund providers create business risk:
- Customer disputes lead to chargebacks
- Payment processor penalties
- Negative reviews from refund denials

**RECOMMENDATION:** Avoid providers with absolute no-refund policies. Bunche should maintain own 24-hour refund window for technical issues only.

#### ToS RESTRICTIONS FLAGS

| Restriction | Providers | Bunche Impact |
|------------|-----------|--------------|
| No email harvesting | Bright Data, Oxylabs, Smartproxy, NetNut | ⚠️ Customer use cases |
| No illegal activities | All | ✅ Universal |
| No proxy reselling | Some (verify individually) | ⚠️ White-label risk |
| Usage monitoring | Bright Data, Oxylabs | ⚠️ Account termination |

**HARBOR ASSESSMENT:** Bunche ToS must include:
1. No email harvesting/scraping
2. No illegal activities under Nigerian law
3. No brute-force/credential stuffing
4. Customer responsible for compliance
5. Bunche reserves termination right

---

### Phase 7-8 — Provider Database Security

#### DATABASE SECURITY STATUS

| Category | Count | Security Status |
|----------|-------|----------------|
| TIER_1_RECOMMENDED | 8 | ✅ Verified safe |
| TIER_2_USE_WITH_CAUTION | 24 | ⚠️ Minor flags |
| TIER_3_AVOID | 9 | 🚫 Excluded |
| TIER_UNKNOWN | 1 | ⚠️ Unverifiable |

#### TIER 1 (VERIFIED SAFE)

| Provider | Type | Scamalytics | Trustpilot | Notes |
|----------|------|-------------|------------|-------|
| Bright Data | All | 0 | 4.8/5 | Enterprise leader |
| Infatica | Residential | 0 | 4.5/5 | Cheapest verified |
| Decodo | All | 0 | 4.2/5 | Former Smartproxy |
| Evomi | Residential | 0 | 4.5/5 | Swiss ethical |
| NodeMaven | ISP | 0 | 4.6/5 | Quality focus |
| OkeyProxy | Residential | 0 | 4.6/5 | 150M pool |
| V-Proxies | Residential | 0 | N/A | 196+ countries |
| ProxyRack | Residential | 0 | N/A | Established |

---

## CRITICAL SECURITY FINDINGS

### 1. ABCPROXY — DARK WEB HACKING TOOL ⚠️

**EVIDENCE:**
- "abcproxy.com Brute & Checker" sold on dark web forums
- Tool used for credential stuffing and CAPTCHA bypass
- No Trustpilot presence
- Linked to hacking/credential theft ecosystem

**HARBOR VERDICT:** 🚫 **EXCLUDE IMMEDIATELY**

Reselling abcproxy exposes Bunche to:
- Association with criminal activity
- Customer account compromises (enabling attacks)
- Legal liability for facilitating hacking
- Reputation destruction if discovered

### 2. OXYLABS — SCAMALYTICS 62/100 ⚠️

**EVIDENCE:**
- Scamalytics fraud score: 62/100
- 62% of IPs associated with fraudulent activity
- Trustpilot 3.7/5 (mixed reviews)
- Premium pricing ($8/GB) doesn't match quality

**HARBOR VERDICT:** 🚫 **EXCLUDE IMMEDIATELY**

High-fraud IPs cause:
- Customer targets block traffic immediately
- Customer accounts banned from websites
- Wasted customer spend = chargebacks
- Support burden for Bunche

### 3. INACTIVE/UNVERIFIABLE PROVIDERS

| Provider | Status | Action |
|----------|--------|--------|
| 2extract | Unverifiable | 🚫 Exclude |
| GP-Remote | Not a proxy provider | 🚫 Remove |
| ProxyEmpire | Unknown HQ | ⚠️ Test first |
| ProxyLite | Unknown HQ | ⚠️ Test first |

### 4. NO-REFUND BUSINESS RISK

Providers with absolute no-refund or restrictive policies create chargeback risk:

| Provider | Policy | Bunche Risk |
|----------|--------|-------------|
| IPFoxy | No refunds | ⚠️ HIGH |
| ProxyMesh | No refund | ⚠️ HIGH |
| SpaceProxy | Not detailed | ⚠️ MEDIUM |

---

## WEBHOOK/API SECURITY CONCERNS

### Provider API Patterns

| Security Aspect | Status |
|----------------|--------|
| API key rotation | Most providers support |
| IP whitelisting | Most providers support |
| Rate limiting | Varies by provider |
| Webhook signatures | Rare (not standard) |

**HARBOR RECOMMENDATION:**
- Rotate API keys every 90 days
- Use IP whitelisting where available
- Monitor rate limits to avoid account suspension
- No webhook security (not industry standard) — use polling instead

---

## REFUND DATA HANDLING

### Bunche Refund Policy (Draft)

| Scenario | Policy |
|----------|--------|
| Technical not working | 24-hour full refund |
| Blocked by target | No refund (out of control) |
| Changed mind | No refund after 24 hours |
| Non-expiring traffic | No refund once used |
| Provider outage | Credit toward next purchase |

### Provider Refund Data for Bunche Operations

**SAFE PROVIDERS (customer-friendly refunds):**
- Smartproxy: 14-day window ✅
- IPBurger: 30-day window ✅
- Froxy: 7-day window ✅
- LumiProxy: 14-day window ✅

**RISK PROVIDERS (chargeback exposure):**
- IPFoxy: No refunds ⚠️
- ProxyMesh: No refund ⚠️

---

## PROVIDER STABILITY ASSESSMENT

### Stable Providers (Established, Verified)

| Provider | Founded | Status |
|----------|---------|--------|
| Bright Data | 2014 | ✅ Enterprise |
| IPRoyal | 2015 | ✅ Established |
| Oxylabs | 2015 | ⚠️ High-risk (flagged) |
| Smartproxy | 2014 | ✅ Rebranded as Decodo |
| Webshare | 2015 | ✅ Acquired by Oxylabs |

### Unstable/New Providers (Higher Risk)

| Provider | Founded | Risk |
|----------|---------|------|
| FloppyData | 2024 | ⚠️ Unproven |
| DataImpulse | 2020 | ⚠️ Small |
| V-Proxies | Unknown | ⚠️ Unverified |

---

## FINAL VERDICT

### ✅ APPROVED FOR BUNCHE SUPPLY CHAIN

**TIER 1 — PRIMARY:**
1. **Infatica** — $0.30/GB cheapest verified residential
2. **Bright Data** — Enterprise-grade, largest network
3. **Decodo** — Rebranded Smartproxy, reliable
4. **Evomi** — Swiss ethical proxies

**TIER 1 — ISP SPECIALISTS:**
5. **Glide via IPRoyal** — UK dedicated ISP ($2.70/IP)
6. **NodeMaven** — Quality ISP focus
7. **Proxy-Seller** — Cheapest single ISP ($2.50/IP)

### ⚠️ USE WITH CAUTION (Test First)

- V-Proxies, OkeyProxy, FloppyData, Froxy, Geonix
- DataImpulse (non-expiring but mixed quality)

### 🚫 PERMANENTLY EXCLUDED

1. **abcproxy** — Dark web hacking tool
2. **oxylabs** — Scamalytics 62/100
3. **proxy6** — Trustpilot 1.5/5
4. **spaceproxy** — Fake reviews, Russia jurisdiction
5. **naproxy** — Scam concerns, Hong Kong
6. **2extract** — Unverifiable
7. **gp-remote** — Not a proxy provider

---

## SECURITY SCORECARD

| Category | Score | Assessment |
|----------|-------|------------|
| **Critical Exclusions** | 5/5 | ✅ abcproxy, oxylabs, proxy6, spaceproxy, naproxy excluded |
| **KYC Controls** | 4/5 | ⚠️ Need tiered verification policy |
| **Refund Risk** | 3/5 | ⚠️ Avoid no-refund providers |
| **API Security** | 4/5 | ⚠️ Rotation needed |
| **ToS Compliance** | 4/5 | ⚠️ Customer use case monitoring needed |

**OVERALL HARBOR RATING:** **SECURE — WITH CONDITIONS**

Bunche can proceed with TIER_1 providers. Implement KYC tiering and refund policy before launch. Monitor customer use cases for ToS compliance.

---

*Prepared for Bunche Council — Phase 9 Harbor Security Review*
*Data Source: MASTER_INTELLIGENCE_DB.json (42 providers, June 30, 2026)*