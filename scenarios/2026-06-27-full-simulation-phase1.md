# Bunche — Full Simulation Report (Phase 1)

**Date:** 2026-06-27
**Source:** Sonny's analysis of all 5 captured scenarios + the system as currently built
**Purpose:** Identify gaps before council review
**Status:** Awaiting council feedback

---

## System State (As of 2026-06-27)

### What's built:
- 5 scenarios captured (first-time-order, provider-down-recovery, new-number-recovery, forgot-pin-recovery, free-trial)
- 15 workflows documented in WORKFLOW_SPECS.md
- 6 n8n JSON templates in `.n8n/workflows/`
- 5 ADRs (PostgreSQL, MiniMax M2, Name-as-code, Secrets Mgmt, Backup)
- DEPLOYMENT.md with 13 steps
- Backup + monitoring + security runbooks
- 3 legal docs (ToS, Privacy, AUP)
- AUP updated for 3proxy free trial terms
- 3proxy + Theorem Reach integration designed (but not deployed)

### What's deployed:
- Nothing — planning phase only

---

## Captured Scenarios Summary

| # | Scenario | Customer Journey | Rules Locked | Edge Cases NOT Covered |
|---|----------|-----------------|--------------|------------------------|
| 1 | First-time order (ISP UK) | Hi → Order → Pay → Name → PIN → IP | 10 rules | Multi-product, mobile/residential variants, referral at order time |
| 2 | Provider down + recovery | Provider check fails → alternatives + admin alert → admin funds → customer notified | 6 rules | Customer behavior between down + recovery |
| 3 | New phone recovery | New phone → name + PIN → proxies shown → phone link choice | 8 rules | Customer who never set PIN, customer who set PIN but lost it |
| 4 | Forgot PIN recovery | Forgot → order details check → receipt verification → admin verdict | 10 rules | Receipt forgery, never-set-PIN case, customer gives 2/3 correct |
| 5 | Free trial (3proxy + Theorem Reach) | Trial ask → disclaimer → survey → 3proxy credentials | 14 rules | Port exhaustion, signature failure, daily limit hit, retry cron |

---

## Gaps Identified (Bunche Internal Audit)

### Gap 1: No admin scenarios captured
- The system has 15 admin commands documented but ZERO end-to-end scenarios tested
- Missing scenarios: "admin runs daily summary", "admin processes refund", "admin handles ban claim", "admin force-stops trial user", "admin rotates API key"

### Gap 2: No mobile/residential order scenarios
- Only ISP purchase is fully captured
- Mobile order needs: 30-day warning, data tracking, expiry handling
- Residential order needs: no-expiry messaging, data tracking, top-up flow

### Gap 3: No multi-product cart scenario
- Spec supports "Order ISP UK 1, RES 5GB, MOB 5GB" as single Flutterwave payment
- No scenario captures: split cart, partial fulfillment if one product fails, total refund vs partial refund

### Gap 4: No referral-claim-by-new-customer scenario
- Referral system designed but only spec'd
- Missing: customer enters "Ada" at order time → credit captured → after fulfillment, Ada gets notification

### Gap 5: No static website spec (Dannion's new ask)
- No landing page exists
- No legal doc hosting strategy
- No WhatsApp redirect CTA design

### Gap 6: 3proxy helper scripts referenced but don't exist in repo
- `scripts/manage-3proxy-trial.sh` — referenced in DEPLOYMENT.md
- `scripts/cleanup-3proxy-trials.sh` — referenced in DEPLOYMENT.md
- Without these scripts, DEPLOYMENT.md Step 12 doesn't work

### Gap 7: Theorem Reach webhook JSON template missing
- DEPLOYMENT.md Step 13 references importing `theorem-reach-webhook.json` workflow
- That JSON file doesn't exist in `.n8n/workflows/`
- Need to create from the spec in WORKFLOW_SPECS §8 Part B

### Gap 8: Bunche Logger JSON schema missing
- WORKFLOW_SPECS §11 references a logger schema with PII redaction
- No actual schema definition
- Need to add to docs/ or as code comment in the JSON workflow file

### Gap 9: No referral redemption scenario
- Spec supports using credit on next order (₦325 off ₦6,500 = ₦6,175 pay)
- No end-to-end scenario tested
- Missing: customer with credit → orders → price recalculation → credit deduction → audit log

### Gap 10: No ban-claim scenario
- Workflow 4 documented but no scenario captures the customer-facing flow
- Missing: customer IP banned → sends screenshot → admin reviews → approve/replace or reject

### Gap 11: No data top-up scenario
- Workflow 5 has data top-up sub-step but no scenario
- Missing: residential customer at 0.5GB → "top up" → options shown → pay → GB added

### Gap 12: No renewal scenario
- Workflow 1 routes "renew" but no scenario
- Missing: ISP expires in 3 days → reminder sent → customer says "renew" → same IP extended or replaced if dead

### Gap 13: No phone_hash blocking implementation detail
- AUP §2.3 says "phone_hash added to deny-list"
- No actual implementation spec for the deny-list mechanism
- Risk: legal says one thing, engineering does another

### Gap 14: No admin workflow JSON templates in repo
- Only 6 of ~15 workflows have JSON templates
- Missing: admin-command-handler, account-recovery, ban-claim, refund-handler, expiry-cron, provider-health-logger, bunche-logger, theorem-reach-webhook, 3proxy-trial-cleanup (9 missing)

### Gap 15: WhatsApp redirect CTA pattern not specified
- When customer taps "Order on WhatsApp" on the (planned) landing page, what exact message opens the WhatsApp chat?
- Need: wa.me/234XXXXXXXXXX?text=prefilled_message
- prefilled message should be friendly + set expectations

### Gap 16: Legal doc URL structure not specified
- bunche.ng/terms? bunche.ng/legal/terms? bunche.ng/terms-of-service?
- Affects how legal notice in first Bunche message reads
- Need: pick one canonical structure

---

## Static Website — Open Questions for Council

1. **Host:** Cloudflare Pages (free, fast, integrates with existing Cloudflare setup) vs Vercel (free, fast, but adds another account) vs Netlify (free, but adds another account)
2. **Stack:** Pure HTML/CSS (lightning fast, no framework) vs Next.js (consistent with DP Generator) vs Astro (good for content sites)
3. **Domain strategy:** bunche.ng (primary) → subpaths /pricing /how-it-works /terms /privacy /aup /contact /free-trial
4. **CTA strategy:** Single big "Chat on WhatsApp" button on every page, opens wa.me with prefilled message
5. **Pricing transparency:** Show all prices on landing page? Or require WhatsApp contact? Trade-off: SEO+transparency vs. price-shopping comparison
6. **Free trial CTA:** Show "Try Free" button on landing page? Or only mention in WhatsApp after conversation?
7. **Legal docs hosting:** Static HTML versions (SEO-friendly) or PDF versions (printable, harder to modify)?
8. **Blog/content:** Phase 1 (none) or build out from day 1 for SEO? Trade-off: SEO boost vs. time investment

---

## What Council Should Review

The 3 MiniMax reviewers have been given specific angles:
- **Security reviewer:** 5 critical security gaps with concrete fixes
- **Product/marketing reviewer:** 5 conversion gaps + static website plan
- **Operations reviewer:** 5 launch-blocking ops gaps + launch readiness verdict + free trial economics sanity check

After council returns, Sonny's Chairman opinion will synthesize all 3, decide what to apply, fix the gaps, save to GitHub, archive deprecated files.

---

## Bunche Internal Recommendations (Preview — to be validated by council)

### Critical fixes (must do before launch):
1. Build the 3proxy helper scripts (DEPLOYMENT.md is broken without them)
2. Build the Theorem Reach webhook JSON workflow
3. Build missing admin workflow JSON templates (at minimum: admin-command-handler, account-recovery)
4. Pick static website host + write landing page spec
5. Document the phone_hash blocking mechanism (close gap 13)

### Important but not blocking launch:
6. Capture missing scenarios (admin ops, mobile/residential, multi-product, referral redemption, ban claim, top-up, renewal)
7. Define Bunche Logger JSON schema (gap 8)
8. Decide legal doc URL structure (gap 16)

### Nice-to-have:
9. Expand archive of all JSON workflow templates (gap 14)
10. Add 3proxy port-exhaustion scenario
11. Add referral-claim-by-new-customer scenario

---

## Files Referenced by Current Build But Missing

| File | Referenced in | Status |
|------|---------------|--------|
| `scripts/manage-3proxy-trial.sh` | DEPLOYMENT.md Step 12.4 | ✅ NOW EXISTS |
| `scripts/cleanup-3proxy-trials.sh` | DEPLOYMENT.md Step 12.5 | ✅ NOW EXISTS |
| `.n8n/workflows/theorem-reach-webhook.json` | DEPLOYMENT.md Step 13.3 | ✅ NOW EXISTS |
| `docs/PHONE_HASH_BLOCKING.md` | AUP §2.3 + scenarios | ✅ NOW EXISTS |
| `docs/BUNCHE_LOGGER_SCHEMA.md` | WORKFLOW_SPECS §11 | ✅ NOW EXISTS |
| `docs/STATIC_WEBSITE_PLAN.md` | (Dannion's new ask) | ✅ NOW EXISTS |
| `scenarios/2026-06-27-admin-operations.md` | DEPLOYMENT.md + SECURITY_RUNBOOK | ✅ NOW EXISTS |
| `.n8n/workflows/admin-command-handler.json` | DEPLOYMENT.md Step 7 | MISSING (next phase) |
| `.n8n/workflows/account-recovery.json` | (referenced in scenarios) | MISSING (next phase) |
| `.n8n/workflows/ban-claim.json` | DEPLOYMENT.md Step 7 | MISSING (next phase) |
| `.n8n/workflows/refund-handler.json` | DEPLOYMENT.md Step 7 | MISSING (next phase) |
| `.n8n/workflows/expiry-cron.json` | DEPLOYMENT.md Step 7 | MISSING (next phase) |
| `.n8n/workflows/bunche-logger.json` | (referenced everywhere) | MISSING (next phase) |

---

## Council Status

- ✅ Security reviewer: dispatched
- ✅ Product/marketing reviewer: dispatched
- ✅ Operations reviewer: dispatched

Awaiting all 3 results to synthesize final action plan.

---

## Final Summary (After Sonny Gap-Fix Phase 3)

**7 of 16 gaps closed before council feedback arrived:**

| Gap | Fix | File |
|-----|-----|------|
| 5 (static website plan) | Created STATIC_WEBSITE_PLAN.md | `docs/STATIC_WEBSITE_PLAN.md` |
| 6 (3proxy scripts) | Created 2 scripts | `scripts/manage-3proxy-trial.sh` + `scripts/cleanup-3proxy-trials.sh` |
| 7 (Theorem Reach workflow) | Created JSON template | `.n8n/workflows/theorem-reach-webhook.json` |
| 8 (Logger schema) | Created BUNCHE_LOGGER_SCHEMA.md | `docs/BUNCHE_LOGGER_SCHEMA.md` |
| 1 (admin scenarios) | Created admin operations scenario | `scenarios/2026-06-27-admin-operations.md` |
| 13 (phone_hash blocking) | Created PHONE_HASH_BLOCKING.md | `docs/PHONE_HASH_BLOCKING.md` |
| Phase 1 report | Created full simulation report | `scenarios/2026-06-27-full-simulation-phase1.md` |

**Remaining gaps (awaiting council prioritization):**

| Gap | Next step |
|-----|-----------|
| 2 (mobile/residential scenarios) | Council verdict on priority |
| 3 (multi-product cart) | Council verdict |
| 4 (referral-claim scenario) | Council verdict |
| 9 (referral redemption scenario) | Council verdict |
| 10 (ban claim scenario) | Council verdict |
| 11 (data top-up scenario) | Council verdict |
| 12 (renewal scenario) | Council verdict |
| 14 (admin JSON templates) | Build after council confirms admin scenarios |
| 15 (WhatsApp CTA wording) | Address in static website plan implementation |
| 16 (legal URL structure) | Locked in STATIC_WEBSITE_PLAN.md |