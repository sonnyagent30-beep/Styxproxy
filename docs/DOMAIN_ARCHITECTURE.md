# Domain Architecture Plan — Styxproxy

**Status:** Decision document. Not yet implemented. Implementation happens when domain(s) are purchased.

---

## The split

| Domain | Purpose | Stack | Owner |
|--------|---------|-------|-------|
| `styxproxy.com` (apex) | Marketing landing — hero, products, pricing, FAQ, blog, SEO pages | **Separate Next.js project** (static export, no /api) OR pure Astro/HTML | Marketing team |
| `app.styxproxy.com` | The transactional app — order, checkout, manage, thank-you, account | **Current Next.js project** (Vercel `bunche-api-push`) | Engineering |
| `admin.styxproxy.com` | Admin login + dashboard — no marketing, no public links | Route group inside app project, **gated by JWT + TOTP + IP allowlist** | Engineering (internal only) |

---

## Why three, not one

### Marketing wants speed, not engineering

If `styxproxy.com` lives in the same repo as the app:
- Marketing can't change hero copy without PR review
- Marketing can't A/B test (would need CMS)
- Blog content mixes with checkout logic in source control
- Risk of breaking the checkout every time someone tweaks a landing page

Separate repo for marketing: marketers push, engineers sleep.

### Admin is a security boundary

`admin.styxproxy.com` is **never publicly linked**. Customers don't know it exists. Only staff with credentials reach it.

Implementation:
- Route group `(admin)` with its own layout (no Header, no Footer, no ChatWidget, no ConsentGate)
- Custom auth check in layout: reads `admin_token` httpOnly cookie, also checks for TOTP step-up token
- If either is missing → 302 to `/login`
- Mounted via Vercel **Environment-based routing**: `if (host === 'admin.styxproxy.com') render only the admin group`

Optional belt-and-suspenders:
- IP allowlist (your office IP only, configurable in env vars)
- Audit-log every admin action (already in `audit_log` table)
- TOTP 2FA (backend already has `totp_encryption_key` env var)

---

## What's in each domain

### `styxproxy.com` — Marketing

Initial scope (small, focused):
- Hero (the "Cross the Styx" hero)
- Product cards (ISP / DC / Residential / Mobile)
- Pricing
- FAQ
- About
- Blog/content stubs (Blog post model, marked Upcoming)

Pages to be removed from the app project and copied to marketing project:
- `/` (or keep a thinner version in app project for first-time visitors)
- `/about`
- `/legal/terms`
- `/legal/privacy`
- `/legal/aup`
- `/refund-policy`
- `/cookie-policy`
- `/products` (or keep thin for nav)

Pages that stay in **app project only**:
- `/order`, `/order/checkout`
- `/thank-you`, `/manage`
- `/preview` (internal, not even linked)
- `/contact` (or in marketing — TBD)

### `app.styxproxy.com` — App

Standard app shell — full Header, Footer, ChatWidget, ConsentGate.

Routes:
- `/order` — order flow
- `/order/checkout` — checkout flow
- `/thank-you?tx_ref=...` — receipt + credentials
- `/manage` — order lookup + history
- `/preview` — internal preview dashboard (could gate this later)
- `/contact` — contact form (or move to marketing)

When user clicks "Get Proxy" from `styxproxy.com` → `app.styxproxy.com/order`.

### `admin.styxproxy.com` — Admin

Gated app shell — minimal layout.

Routes (existing `/admin` becomes gated):
- `/admin/login` — admin email + password + TOTP
- `/admin/dashboard` — overview
- `/admin/orders` — all orders
- `/admin/customers` — all customers
- `/admin/credentials` — credential management
- `/admin/refunds` — refund queue
- `/admin/audit` — audit log viewer
- `/admin/settings` — system config

---

## Implementation steps (when domain arrives)

1. **Buy domains** at your preferred registrar:
   - `styxproxy.com` (apex)
   - `app.styxproxy.com` (or `proxy.styxproxy.com`)
   - `admin.styxproxy.com`

2. **Add custom domains to current Vercel project**:
   - Vercel dashboard → Settings → Domains → add all three
   - Vercel will provide DNS records; add them at your registrar

3. **Create the marketing repo** (separate):
   - `git init styxproxy-marketing`
   - Copy only Hero + Footer components + design tokens
   - Initial pages: `/`, `/about`, `/legal/*`, `/refund-policy`, `/cookie-policy`, `/products`
   - Deploy to Vercel as a separate project → maps to `styxproxy.com`

4. **Implement admin gating in current repo**:
   - Create `app/(admin)/admin/layout.tsx` (route group) with auth check
   - Create `app/(admin)/layout.tsx` that does the same but lighter (no Footer)
   - Move existing `app/admin/page.tsx` to `app/(admin)/admin/login/page.tsx` etc.

5. **Environment-based admin routing** (optional):
   - `middleware.ts`: if `host === 'admin.styxproxy.com'`, rewrite `/` → `/admin/dashboard`, etc.
   - This lets us keep `admin/` as a normal route while being invisible from the public app

6. **Update env vars everywhere**:
   - `NEXT_PUBLIC_API_URL` stays pointing to `bunche.railway.app` (or new prod URL after VPS)
   - `NEXT_PUBLIC_FRONTEND_URL` on backend: `app.styxproxy.com`
   - Marketing repo may not need any backend env vars (pure static)

7. **DNS cutover** — point all three domains at Vercel at your registrar

8. **Verify** — visit each domain, test the full flow

---

## What I'll build in the current repo **now** to be ready

Even without the domains, I can structure the code so domain split is trivial later.

### Route groups (proposed)

- `app/(marketing)/` — public marketing pages (`/`, `/about`, `/legal/*`, `/refund-policy`, `/cookie-policy`, `/products`)
  - Layout: no ChatWidget, no ConsentGate, lighter Header (no "Manage" link)
- `app/(app)/` — transactional (`/order`, `/order/checkout`, `/thank-you`, `/manage`, `/preview`)
  - Layout: full Header + Footer + ChatWidget + ConsentGate
- `app/(admin)/` — admin (`/admin/*`)
  - Layout: minimal, full-screen, auth-gated
  - Currently the entire app is in `(app)/` (no group) — admin is flat next to other pages

When the domains land, adding route groups is a `git mv` operation, not a rewrite.

### What stays as-is

- `lib/` — pure logic, domain-agnostic
- `components/` — domain-agnostic (Header, Footer, ChatWidget, ConsentGate)
- `backend/` — separate, hosts /api/* — no changes needed for domain split

---

## Cost-of-ownership impact

| Setup | Vercel cost | Repo overhead | Marketing speed |
|-------|------------|---------------|-----------------|
| **One repo, one domain** (today) | 1 project | 0 | Slow (engineering bottleneck) |
| **Two repos, two domains** (split) | 2 projects (~$20/mo each on Pro) | Medium (shared component lib) | Fast (marketing owns repo) |
| **Three repos, three domains** (+admin) | 3 projects (~$60/mo Pro, or 1 on Pro + 2 on Hobby) | Higher (need shared package) | Fastest, admin isolated |

For now: stay on one repo. Move when pain arises (i.e., when marketing starts asking to update copy daily, or admin needs its own access controls).

---

## Open questions

1. **Marketing CMS**: build into the marketing repo, or external (Sanity / Contentful / Notion)? Recommendation: **Notion-driven MDX** for low-cost, marketer-friendly content editing.
2. **Blog scope**: is `blog.styxproxy.com` a 4th domain, or does marketing host it?
3. **Admin DNS**: do we want a more obscure name like `dashboard.styxproxy.com` to obscure it further, or is `admin.styxproxy.com` standard enough?
4. **Support docs**: do we need a `docs.styxproxy.com` for technical integration guides? (Relevant if you ever open a B2B side.)

---

*Document owner: Engineering. Last updated: 2026-07-13.*
