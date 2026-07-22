# Styxproxy — Static Website Plan

**Date:** 2026-06-27
**Source:** Sonny's recommendation + Dannion's request for landing page + legal docs before WhatsApp redirect + product council feedback
**Status:** LOCKED (recommendation, awaiting Dannion's review)

---

## Decision Summary

| Item | Choice | Rationale |
|------|--------|-----------|
| **Host** | Cloudflare Pages | Free, fast, already using Cloudflare (DNS + DDoS + R2) |
| **Stack** | Pure HTML + CSS (no framework) | Lightning fast, no build step, no npm deps, easy to host |
| **Repo** | New repo: `sonnyagent30-beep/styxproxy-web` | Separate from backend repo (different lifecycle) |
| **Domain** | `styxproxy.com` (already planned) | Primary domain |
| **CTA** | Single WhatsApp button: `wa.me/234XXXXXXXXXX?text=prefilled` | One-tap to conversation |
| **Legal hosting** | Static HTML pages at `/terms`, `/privacy`, `/aup` | SEO-friendly, fast, easy to update |
| **Pricing transparency** | YES — show all prices on landing page | Reduces price-shopping comparison friction |
| **Product differentiation** | Use-case matching section ("Which proxy do I need?") | Council feedback — first-time buyers don't know proxy types |
| **Free trial CTA** | "Try Free" button on landing page → same WhatsApp flow | Single CTA, clear path |
| **Blog/content** | NONE for Phase 1 | Defer until product-market fit |

---

## Site Map

```
styxproxy.com/
├── /                    → Landing page (hero + pricing + use-cases + how-it-works + CTA)
├── /pricing             → Pricing table (optional, can fold into landing)
├── /how-it-works        → Step-by-step explainer (optional)
├── /faq                 → Common questions (Phase 2)
├── /terms               → Terms of Service (static HTML)
├── /privacy             → Privacy Policy (static HTML)
├── /aup                 → Acceptable Use Policy (static HTML)
└── /contact             → WhatsApp CTA + abuse@styxproxy.com email
```

**For Phase 1: only `/`, `/terms`, `/privacy`, `/aup` are required.**

---

## Landing Page — Copy Blueprint

### Above the Fold (Hero)

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🇳🇬 Styxproxy — Your Plug for Proxies in Nigeria

Buy ISP, Datacenter, Residential & Mobile proxies
on WhatsApp. Pay in Naira. Get your proxy in 2 minutes.

📱 [Chat on WhatsApp — Free Trial Available]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### Section 2: Why Styxproxy (3 bullets)

```
✅ No inventory, no upfront — pay only when you buy
✅ Pay in Naira — Flutterwave (transfer, card, USSD, QR)
✅ Instant delivery — credentials in <2 minutes on WhatsApp
```

### Section 3: Products & Pricing (table)

```
┌─────────────────────┬──────────────┬──────────────┐
│ Product             │ Price        │ Best for     │
├─────────────────────┼──────────────┼──────────────┤
│ ISP (UK/US/DE/FR/CA)│ ₦6,500/mo    │ Social media │
│ ISP (JP/AU/BR/SG)   │ ₦7,500/mo    │ International│
│ Datacenter          │ ₦2,500/mo    │ Budget       │
│ Residential 5GB     │ ₦5,000       │ Scraping     │
│ Residential 10GB    │ ₦9,000       │ Scraping     │
│ Mobile 4G 5GB       │ ₦20,000      │ Mobile-only  │
│ Mobile 4G 10GB      │ ₦35,000      │ Mobile-only  │
└─────────────────────┴──────────────┴──────────────┘

💡 Try free for 2 hours — no card required.
[Try Free on WhatsApp →]
```

### Section 3b: Use-Case Matching (Product Differentiation)

Below the pricing table, add a "Which proxy do I need?" section that matches use cases to products:

```
🤔 WHICH PROXY DO I NEED?
━━━━━━━━━━━━━━━━━━━━━━━━━

📱 "I run multiple Instagram/TikTok accounts"
   → ISP UK/US — stable IPs, long-lasting
   → Recommended: ISP UK @ ₦6,500/mo

💬 "I do social media outreach / DM campaigns"
   → Residential — looks like real users
   → Recommended: Residential 5GB @ ₦5,000

🛒 "I run a sneaker bot or e-commerce automation"
   → Datacenter — fast, cheap
   → Recommended: Datacenter @ ₦2,500/mo

📊 "I scrape websites / collect data"
   → Residential — pool of IPs
   → Recommended: Residential 10GB @ ₦9,000

📱 "I manage TikTok/mobile-only platforms"
   → Mobile 4G — real mobile carrier IPs
   → Recommended: Mobile 5GB @ ₦20,000

🎮 "I play games or use mobile apps"
   → Mobile 4G
   → Recommended: Mobile 5GB @ ₦20,000
```

**Why this section matters:** First-time buyers don't know the difference between ISP, Residential, Mobile, Datacenter. Without this matching, they pick randomly or abandon. With this, they self-identify and order with confidence.

---

### Section 4: How It Works (3 steps)

```
1️⃣  Open WhatsApp, tap "Chat on Styxproxy"
2️⃣  Tell us what you want (e.g. "Order ISP UK 1")
3️⃣  Pay via Flutterwave → proxy in your chat in 2 min
```

### Section 5: Footer

```
🇳🇬 Made in Lagos · WhatsApp-first · [Terms] · [Privacy] · [AUP]
Abuse: abuse@styxproxy.com
```

---

## WhatsApp CTA — Prefilled Message

The CTA button uses `wa.me/234XXXXXXXXXX?text=URL_ENCODED_MESSAGE`.

**Default prefilled message:**

```
Hi Styxproxy! I'd like to try your proxies.
```

**Why this works:**
- Friendly, not pushy
- Tells Styxproxy customer wants trial (triggers free trial flow)
- Customer can edit before sending
- Short enough to fit WhatsApp preview

---

## Legal Docs Hosting

### Approach: Static HTML rendered from .md files

The 3 legal docs exist in `/legal/` in the backend repo (TERMS_OF_SERVICE.md, PRIVACY_POLICY.md, ACCEPTABLE_USE_POLICY.md).

**Workflow:**
1. Write doc in markdown (already done)
2. Convert to HTML via pandoc or simple static site generator (or just paste into HTML template)
3. Deploy to `styxproxy.com/{doc-name}` via Cloudflare Pages

**Alternative: just paste the markdown as plain HTML with a CSS stylesheet.** Simplest possible setup.

### URL Structure (locked)

```
styxproxy.com/terms       → TERMS_OF_SERVICE.md rendered
styxproxy.com/privacy     → PRIVACY_POLICY.md rendered
styxproxy.com/aup         → ACCEPTABLE_USE_POLICY.md rendered
```

**Rationale:** Short URLs are easier to share on WhatsApp (no truncation worries). The legal notice in first Styxproxy message says "styxproxy.com/terms" — this matches.

---

## Repo Structure: `styxproxy-web`

```
sonnyagent30-beep/styxproxy-web/
├── index.html              → Landing page
├── terms.html              → Terms of Service
├── privacy.html            → Privacy Policy
├── aup.html                → Acceptable Use Policy
├── contact.html            → Contact info (optional)
├── css/
│   └── style.css           → Single stylesheet
├── js/
│   └── main.js             → (Phase 2 if needed)
└── README.md
```

**No build step. No framework. No npm dependencies.**

---

## Cloudflare Pages Setup

### Step 1: Create the repo

```bash
# Create new repo on GitHub
gh repo create styxproxy-web --public --description "Styxproxy landing page"

# Clone locally
git clone git@github.com:sonnyagent30-beep/styxproxy-web.git
cd styxproxy-web

# Create initial files
mkdir -p css
echo "/* Styxproxy styles */" > css/style.css
git add .
git commit -m "Initial commit"
git push
```

### Step 2: Connect to Cloudflare Pages

1. Go to: dash.cloudflare.com → Pages
2. Click **Create application** → **Pages** → **Connect to Git**
3. Select `sonnyagent30-beep/styxproxy-web` repo
4. Build settings:
   - **Build command:** (leave empty — no build needed)
   - **Build output directory:** `/` (or `.`)
   - **Root directory:** (leave empty)
5. Click **Save and Deploy**
6. Cloudflare gives a `*.styxproxy-web.pages.dev` URL

### Step 3: Add custom domain

1. Cloudflare Pages → styxproxy-web → Custom domains
2. Add: `styxproxy.com` (and `www.styxproxy.com` if you want)
3. Cloudflare auto-creates DNS records (you'll see them in DNS)

### Step 4: SSL

Cloudflare Pages auto-provisions SSL via Let's Encrypt. No action needed.

---

## CTA Button — Exact HTML

```html
<a href="https://wa.me/234XXXXXXXXXX?text=Hi%20Styxproxy!%20I%27d%20like%20to%20try%20your%20proxies."
   class="cta-button"
   target="_blank"
   rel="noopener">
  📱 Chat on WhatsApp
</a>
```

**Styling:**
- Background: #0070F4 (matches Styxproxy brand blue from DP Generator)
- Color: white
- Padding: 16px 32px
- Border-radius: 8px
- Font-size: 18px
- Hover: slight scale + shadow

---

## Phone Number Strategy

**Open question for Dannion:** What WhatsApp number does Styxproxy use?

Options:
- Personal WhatsApp number (simplest, no Meta Business setup)
- Dedicated WhatsApp Business number (more professional, harder to lose access)
- Twilio WhatsApp number (programmatic, more setup)

**Recommendation:** Start with personal WhatsApp Business number. Upgrade to Twilio when volume justifies.

---

## What's NOT in the Static Site (Phase 1)

| Feature | Why not | When to add |
|---------|---------|-------------|
| Blog | Time investment, no SEO benefit at start | After 1,000 customers |
| FAQ page | Customer can just message Styxproxy | After 100 FAQ messages pile up |
| Pricing transparency calculator | Just show prices in table | If customers ask |
| Live chat | WhatsApp IS the live chat | Never |
| Testimonials | Need real customers first | After 50+ customers |
| Affiliate dashboard | Referrals tracked in WhatsApp + DB | When referral volume justifies |
| API docs | Not relevant — this is a consumer product | Never |
| Interactive WhatsApp menu | WhatsApp Business doesn't support rich UI; defer to v2 | v2 if customer feedback demands |

---

## Cost (Cloudflare Pages)

| Item | Cost |
|------|------|
| Cloudflare Pages hosting | $0 (free tier: unlimited sites, unlimited requests, 500 builds/month) |
| Custom domain | $0 (uses existing styxproxy.com) |
| SSL | $0 (Let's Encrypt via Cloudflare) |
| Bandwidth | $0 (unlimited on free tier) |
| **Total** | **$0/mo** |

---

## Files to Create (New Repo)

| File | Purpose | Status |
|------|---------|--------|
| `styxproxy-web/index.html` | Landing page (hero + pricing + use-cases + CTA) | TODO |
| `styxproxy-web/terms.html` | ToS rendered | TODO |
| `styxproxy-web/privacy.html` | Privacy rendered | TODO |
| `styxproxy-web/aup.html` | AUP rendered | TODO |
| `styxproxy-web/contact.html` | Contact info | TODO |
| `styxproxy-web/css/style.css` | Stylesheet | TODO |
| `styxproxy-web/README.md` | Repo docs | TODO |
| `styxproxy-web/.gitignore` | Standard | TODO |

**This doc (STATIC_WEBSITE_PLAN.md) is the design blueprint. Implementation comes next.**

---

## Open Decisions for Dannion

1. **WhatsApp number:** personal or dedicated?
2. **Site name:** `styxproxy-web` repo OK or different?
3. **CTA wording:** "Chat on WhatsApp" vs "Try Free Now" vs other?
4. **Default language:** English only or add pidgin/yoruba/igbo later?
5. **Phase 1 pages:** just `/`, `/terms`, `/privacy`, `/aup` or also `/pricing`, `/how-it-works`, `/faq`?
6. **Payment link expiry: 30 min (current) or 2 hours (Sonny rec) or 24 hours (Product reviewer)?** ← Council feedback (Product reviewer #5)

### Payment Link Expiry Decision

**Current spec:** Flutterwave payment link expires after **30 minutes** (per DEPLOYMENT.md §6.1).

**Product reviewer's concern:**
> "1-Hour Payment Expiry Creates Abandonment — Customers who need to verify with boss/partner lose the link. Fix: Extend to 24 hours OR offer 'Save Cart' feature via WhatsApp."

**Three options:**

| Option | Expiry | Pros | Cons |
|--------|--------|------|------|
| **A** (current) | 30 min | Forces quick decision; low abandoned-cart risk | High bounce rate for cautious buyers |
| **B** | 2 hours | Sweet spot — enough time to confirm, not too long | Still some bounce |
| **C** | 24 hours | Maximum conversion; customers can come back | Order details (price, IP) might change in DB between creation and payment; abandoned carts accumulate |

**Sonny's recommendation: 2 hours.**

**Rationale:**
- Flutterwave supports custom expiry per transaction
- 2hr captures most "I need to think about it" customers
- Lower risk than 24hr of price drift / product unavailability
- Aligns with industry standard for high-consideration digital purchases

**Implementation:** Add `expires_in: 7200` (seconds) to the Flutterwave API call in Workflow 2 (Payment Confirmation) and the first-message payment link generation in Workflow 1.

**Decision pending Dannion's review.**

---

## Related

- `legal/TERMS_OF_SERVICE.md` — source content for styxproxy.com/terms
- `legal/PRIVACY_POLICY.md` — source content for styxproxy.com/privacy
- `legal/ACCEPTABLE_USE_POLICY.md` — source content for styxproxy.com/aup
- `README.md` — links to legal docs (will be updated when site is live)
- `workflows/WORKFLOW_SPECS.md` §1 — first-message legal notice references these URLs