# Styxproxy — Production Launch Checklist

**Status:** Pending. Execute this from top to bottom when VPS + domain are purchased.

**Last Updated:** 2026-07-13

This document is the master checklist for taking Styxproxy from "build in place on Vercel + Railway" to "production on styxproxy.com with full email + admin infrastructure." Every item you need to buy, set up, configure, or hand off to someone else is listed here.

---

## Step 0 — Things you must decide before starting

| Question | Why it matters | Default (pick if unsure) |
|----------|---------------|--------------------------|
| Do you want to be the sole legal director or form a company? | Banking, tax, contracts, abuse reports. | Form a single-member LLC in Nigeria or US LLC (pick based on where your customers + providers accept payment) |
| Will you accept international customers or Nigeria only? | Pricing display currency, payment processor coverage, legal jurisdiction. | International (Flutterwave supports NGN + USD) |
| Will you sell B2B (companies buying in bulk) or only end-users? | DPA, MSAs, invoice templates, payment terms. | End-user only at launch; B2B later |
| Will you run analytics? | Privacy-policy disclosure + analytics account. | Plausible (default, privacy-friendly) |
| Will you record customer support chats? | Storage, access, retention. | No (default — keep the privacy promise) |

---

## Step 1 — Domain names to register

| Domain | Purpose | Why |
|--------|---------|-----|
| `styxproxy.com` (apex) | Marketing landing | Public face of the brand |
| `app.styxproxy.com` (or `proxy.styxproxy.com`) | Customer-facing app (order / manage / thank-you) | Per the domain-architecture plan |
| `admin.styxproxy.com` (or `dashboard.styxproxy.com`) | Admin dashboard — never publicly linked | Internal operations |
| `api.styxproxy.com` | Backend API base URL | Backend endpoints |
| `mail.styxproxy.com` | Email server hostname (MX record) | Required if self-hosting mail |
| `status.styxproxy.com` | Status page (UptimeRobot / BetterStack public status) | Optional but professional |

**Where to register:**
- **Cloudflare Registrar** — at-cost pricing, free WHOIS privacy, automatic DNS hosting. Recommended.
- **Namecheap** / **Porkbun** — also at-cost with free privacy.

**Tip:** Buy all 6 at once so the registrar doesn't hike renewal on a critical one later.

---

## Step 2 — Email addresses to create

You need an email provider that supports custom-domain addresses. Options:

| Provider | Cost | Best for |
|----------|------|----------|
| **Google Workspace** | $7/user/mo | Most professional, integrates with Calendar/Drive/Meet |
| **Microsoft 365 Business Basic** | $6/user/mo | If you're already in Microsoft land |
| **Fastmail** | $5/user/mo (or free for 30-day trial) | Cheapest reliable paid option |
| **Zoho Mail** | Free for up to 5 users, $1/user/mo after | Best free option, weaker UX than Google |
| **Titan / Proton / Tuta** | Varies | Privacy-focused, no Google tracking |

**My recommendation:** Google Workspace. Even if you don't use Google for personal use, every admin needs a Gmail-equivalent mailbox that "looks like a real company" — abuse reports, banking, receipts, all land here.

### Email addresses to provision

| Address | Purpose | Forwards to | Notes |
|---------|---------|------------|-------|
| `hello@styxproxy.com` | Default catch-all marketing | your personal | Keep on the website as the "general inquiries" address |
| `support@styxproxy.com` | Customer support | your personal (or shared inbox via Google) | Auto-responder: "we reply within X hours" |
| `billing@styxproxy.com` | Payment-related, invoices, refunds | you | Used for Flutterwave receipts, refunds, tax docs |
| `privacy@styxproxy.com` | Privacy/data deletion requests | you | Already referenced in `/cookie-policy` |
| `abuse@styxproxy.com` | Mandatory for hosting — abuse reports from upstream providers and security researchers | you or triaged by Charon bot | Required for hosting accountability (RFC 2142) |
| `security@styxproxy.com` | Coordinated vulnerability disclosure | you | Send a copy of your Security.txt in the marketing site footer |
| `legal@styxproxy.com` | DMCA, takedown notices, law-enforcement | you | Required for safe-harbor under most jurisdictions |
| `press@styxproxy.com` | Press / journalist inquiries | you | Optional, but professional |
| `admin@styxproxy.com` | Internal admin team mailbox | team alias | Used by admin dashboard login flow |
| `noreply@styxproxy.com` | Transactional email sender (Flutterwave receipts, password resets) | (no replies) | Must be a sender, not inbox |

### Catch-all behavior

Set up `*@styxproxy.com` to either:
- Forward to your personal inbox (recommended at launch — you see everything), or
- Bounce with a "this is no longer monitored" message (recommended once you add team)

### Email authentication (required before sending)

Configure these DNS records at your registrar:

```
@       TXT  "v=spf1 include:_spf.google.com ~all"          (SPF)
mail._domainkey  TXT  "v=DKIM1; k=rsa; p=<public key>"       (DKIM — get from Google Workspace admin)
_dmarc  TXT  "v=DMARC1; p=quarantine; rua=mailto:hello@styxproxy.com"
```

Without these, your email will land in spam.

---

## Step 3 — Subdomain DNS plan

| Subdomain | Type | Value | Notes |
|-----------|------|-------|-------|
| `styxproxy.com` | A + AAAA | Vercel IPs (front of marketing project) | Or use Vercel "nameservers" + add domain in dashboard |
| `app.styxproxy.com` | CNAME | `cname.vercel-dns.com` | Vercel customer app |
| `admin.styxproxy.com` | CNAME | `cname.vercel-dns.com` | Vercel admin app (separate project) |
| `api.styxproxy.com` | A + AAAA | `<VPS IPv4>` + `<VPS IPv6>` | Backend (FastAPI on Railway or new VPS) |
| `mail.styxproxy.com` | A | `<email provider IP>` | MX target |
| `status.styxproxy.com` | CNAME | `<uptime provider hostname>` | UptimeRobot / BetterStack |
| `*._domainkey.styxproxy.com` | TXT | DKIM public key | From your email provider |
| `_dmarc.styxproxy.com` | TXT | DMARC policy | See Step 2 |
| `styxproxy.com` | MX | `1 aspmx.l.google.com`, `5 alt1.aspmx.l.google.com`, etc. | Routes mail to your provider |

**Optional but recommended:**

| Subdomain | Type | Value | Notes |
|-----------|------|-------|-------|
| `cdn.styxproxy.com` | CNAME | Cloudflare CDN | If you front assets |
| `api-staging.styxproxy.com` | A | `<staging VPS>` | So you can deploy without breaking prod |
| `grafana.styxproxy.com` | CNAME | monitoring IP | Internal dashboards |
| `prometheus.styxproxy.com` | CNAME | monitoring IP | Metrics |
| `wiki.styxproxy.com` | CNAME | Notion / Outline | Internal docs |

---

## Step 4 — VPS / hosting to provision

You said "when we get a VPS + domain." Here's the spec minimum vs. recommended.

### Option A — Managed PaaS (fastest to production)

| Service | What for | Cost | Notes |
|---------|----------|------|-------|
| **Railway** | FastAPI backend (already runs there today) | $5 base + usage | Easiest — auto-deploys from this repo |
| **Vercel Pro** | Frontend (Vercel) | $20/mo per project | Staging + production tiers, custom domains |
| **Cloudflare** | DNS + CDN + DDoS protection | Free tier | Get this regardless of option |

### Option B — Self-hosted VPS (full control, harder ops)

| Spec | Minimum | Recommended |
|------|---------|-------------|
| CPU | 2 vCPU | 4 vCPU |
| RAM | 4 GB | 8 GB |
| Storage | 80 GB SSD | 200 GB NVMe |
| Bandwidth | 5 TB/mo | 10 TB/mo |
| OS | Ubuntu 22.04 LTS | Ubuntu 24.04 LTS |
| Provider | Hetzner (€4-8/mo), Vultr ($6-12/mo), DigitalOcean ($6-24/mo) | Hetzner AX/CCX line |

### What runs on the VPS (Option B)

Services you need (one or more containers via Docker Compose):

- **Caddy** — reverse proxy + automatic HTTPS
- **FastAPI backend** (this repo's `backend/`)
- **PostgreSQL 16** — primary database
- **Redis 7** — sessions, rate limiting, Celery broker
- **Qdrant / Chroma / Pinecone** — embeddings memory for Charon chatbot
- **n8n** — workflow orchestration (WhatsApp/Telegram bots)
- **Ollama** OR **OpenAI-compatible proxy** for Charon's LLM
- **Munin / Uptime Kuma / Grafana + Prometheus** — monitoring

### Why both options exist

Self-hosting = full control, but you own backups, monitoring, scaling, and any 3am outage. Managed PaaS = zero ops, fewer surprises, scales for you. **Recommendation:** start with managed PaaS (Railway + Vercel), move to self-hosted only if cost or compliance demands it.

---

## Step 5 — Tools and applications to set up

### Customer-facing (website + apps)

| Tool | Purpose | Account needed | Cost |
|------|---------|----------------|------|
| **Vercel** | Frontend hosting | GitHub OAuth | $0 Hobby, $20/mo Pro per project |
| **Cloudflare** | DNS, CDN, DDoS, security | Email signup | Free |
| **Plausible Analytics** | Privacy-friendly analytics | Email signup | $0 for <10K views/mo (self-host option available) |
| **UptimeRobot** OR **BetterStack** | Uptime monitoring | Email signup | Free tier |
| **Statuspage.io** OR **BetterStack** | Public status page | Email signup | Free tier |

### Backend / Operations

| Tool | Purpose | Cost |
|------|---------|------|
| **Railway** | Backend hosting (Postgres + n8n + FastAPI) | $5 base + usage |
| **Supabase** | Optionally for auth — but we don't log in | $0 free tier |
| **n8n Cloud** OR **self-hosted n8n** | Workflow orchestration for WhatsApp/Telegram bots | Free self-hosted; $20/mo cloud |
| **Ollama Cloud** OR **MiniMax M2/M3** OR **OpenAI** | LLM for Charon chatbot | Variable |
| **Sentry** | Error monitoring | Free tier |
| **Cron-job.org** OR **EasyCron** | Simple scheduled jobs (rotation cleanup, expiry reminders) | Free |
| **GitHub** | Source control, CI | $0 (free for public) or $4/mo Team |

### Customer support & communication

| Tool | Purpose | Cost |
|------|---------|------|
| **Telegram** | `@StyxproxyBot` customer channel | Free |
| **WhatsApp Business API** | Official support channel (via Meta-approved BSP) | Variable (Twilio/Meta Cloud free tier available) |
| **Intercom** OR **Crisp** OR **Plain** | Helpdesk (optional — chat widget already on site) | $0-$75/mo |
| **Charon chatbot** | Already built — auto-handles most questions | Free (computes via LLM) |

### Payment & finance

| Tool | Purpose | Cost |
|------|---------|------|
| **Flutterwave** | Payment processor (cards + bank transfer + USSD + QR) | 1.4% per NGN txn |
| **Wise Business** | Receive international payments, hold in USD/EUR | Variable FX |
| **Piggyvest** OR **Cowrywise** | Hold NGN, earn interest on float | Free / 8% APR |
| **Payoneer** | Receive USD from non-Flutterwave channels | Variable |
| **QuickBooks** OR **Wave** | Bookkeeping | $15/mo (QuickBooks), $0 (Wave) |

### Security & compliance

| Tool | Purpose | Cost |
|------|---------|------|
| **1Password** OR **Bitwarden** | Password manager for the team | $4/mo (1Password), $0 self-host (Bitwarden) |
| **Authy** OR **Google Authenticator** OR **Yubikey** | 2FA on every account | Yubikey $25-$50 one-time |
| **HaveIBeenPwned** | Notification when your staff emails show up in a breach | Free |
| **VirusTotal** | Scan suspicious files | Free |
| **Security.txt file** | Coordinated vuln disclosure at `styxproxy.com/.well-known/security.txt` | Free |

### Observability

| Tool | Purpose | Cost |
|------|---------|------|
| **Grafana Cloud** | Dashboards + alerting | Free tier (10K metrics) |
| **Better Stack Logs** OR **Logtail** | Centralized logs | $0-$25/mo |
| **Uptime Kuma** (self-hosted) | Simple uptime monitor | Free if self-hosted |

### Backups

| Resource | Backup frequency | Tool |
|----------|------------------|------|
| PostgreSQL | Daily, 30-day retention | `pg_dump` to S3 / R2 / Backblaze |
| VPS disk image | Weekly | Snapshot via provider |
| Domain registration | n/a | Use registrar with 2FA enabled |
| Email | Daily | Google Workspace takes care of this automatically |

---

## Step 6 — API keys and secrets you'll need

These need to live in your password manager, NOT in plaintext or git.

### Payment processor

| Key | Where to get | Where to store |
|-----|--------------|----------------|
| **Flutterwave Public Key** | dashboard.flutterwave.com → Settings → API | Vercel env: `NEXT_PUBLIC_FLUTTERWAVE_PUBLIC_KEY` |
| **Flutterwave Secret Key** | Same | Railway env: `FLUTTERWAVE_SECRET_KEY` |
| **Flutterwave Webhook Secret** | Same → Webhooks | Railway env: `FLUTTERWAVE_WEBHOOK_SECRET` |
| **Flutterwave Encryption Key** | Same → Settings | Backend `.env` |

### Upstream proxy providers (call from backend only)

| Key | Where to get | Where to store |
|-----|--------------|----------------|
| **Provider A API Key** | provider dashboard | Railway env: `PROXY_PROVIDER_A_API_KEY` |
| **Provider B API Key** | provider dashboard | Railway env: `PROXY_PROVIDER_B_API_KEY` |

(See Step 7 for which providers to sign up for.)

### Frontend & infrastructure

| Key | Where to get | Where to store |
|-----|--------------|----------------|
| **Vercel token** | vercel.com/account/tokens | Local only; deploys via GitHub |
| **Railway token** | railway.app/account/tokens | Local only |
| **Cloudflare API token** | dash.cloudflare.com → My Profile → API Tokens | Cloudflare DNS automation |
| **Plausible site ID** | plausible.io | Vercel env: `NEXT_PUBLIC_PLAUSIBLE_DOMAIN` |
| **Sentry DSN** | sentry.io | Railway env: `SENTRY_DSN` |

### LLM

| Key | Where to get | Where to store |
|-----|--------------|----------------|
| **OpenAI/MiniMax API key** | platform.openai.com or api.MiniMax.chat | Railway env: `LLM_API_KEY` |
| **Ollama Cloud token** (if used) | cloud.ollama.com | Same |

### Email sending

| Key | Where to get | Where to store |
|-----|--------------|----------------|
| **SMTP host/port/user/pass** | Mailgun OR Postmark OR Resend | Railway env |
| **Resend API key** | resend.com | Recommended for transactional |

Resend is the cleanest "send grid replacement" right now. Free up to 3K emails/mo, then $20/mo for 50K.

### Communication (Telegram + WhatsApp)

| Key | Where to get | Where to store |
|-----|--------------|----------------|
| **Telegram bot token** | @BotFather | Railway env: `TELEGRAM_BOT_TOKEN` |
| **WhatsApp Business API token** | Meta Cloud or Twilio | Railway env: `WHATSAPP_ACCESS_TOKEN` |
| **WhatsApp webhook verify token** | You pick this; configure in Meta dashboard | Railway env: `WHATSAPP_VERIFY_TOKEN` |
| **Telegram webhook URL secret** | Pick a random secret; share with BotFather webhook setup | Railway env: `TELEGRAM_WEBHOOK_SECRET` |

### Admin / Auth (backend)

| Key | Where to get | Where to store |
|-----|--------------|----------------|
| **JWT signing secret** | Generate: `openssl rand -hex 64` | Railway env: `JWT_SECRET` |
| **TOTP encryption key** | Generate: `openssl rand -hex 32` | Railway env: `TOTP_ENCRYPTION_KEY` |
| **Admin PIN bcrypt hash** | Hash your PIN: `python -c "from passlib.hash import bcrypt; print(bcrypt.hash('YOUR_PIN'))"` | Railway env: `ADMIN_PIN_HASH` |
| **Backend internal API key** | Generate random | For backend ↔ Telegram bot auth |

### Database

| Key | Where to get | Where to store |
|-----|--------------|----------------|
| **Postgres connection string** | Railway auto-generates | Railway env: `DATABASE_URL` |
| **Postgres read-only URL** (for analytics) | Built from same | Optional |

### Encryption secrets

| Key | Where to get | Where to store |
|-----|--------------|----------------|
| **Database field-level encryption key** | Generate: `openssl rand -hex 32` | Railway env: `FIELD_ENC_KEY` |
| **Session cookie signing secret** | Same as JWT secret or different | Railway env |

### Build / secrets management

- Use **Doppler** OR **Railway's built-in env** OR **Vercel env** OR **HashiCorp Vault** for secret storage. Do not store in `.env` files committed to the repo.
- Use **SOPS + age** for any secrets that must live in git (e.g., for `pnpm` deploy scripts).
- Rotate keys every 90 days. Calendar reminder.

---

## Step 7 — Accounts to create before launch

These need an account before any code deploys can actually work.

| Service | Account needed for | Time to set up |
|---------|--------------------|-----------------|
| **Cloudflare** | DNS, CDN | 5 min |
| **Vercel** | Frontend | 5 min (sign in with GitHub) |
| **Railway** | Backend | 5 min (sign in with GitHub) |
| **Flutterwave** (production mode) | Live payments | 1-3 days (KYC, business docs) |
| **Resend** | Transactional email | 10 min |
| **Google Workspace** | Email + Drive + Calendar | 30 min per account, then domain verification |
| **Telegram @BotFather** | Bot setup | 5 min |
| **Meta Cloud / Twilio** for WhatsApp | Support channel | 1-7 days (Meta verification of business) |
| **Sentry** | Error monitoring | 10 min |
| **Plausible** | Analytics | 10 min |
| **UptimeRobot / BetterStack** | Uptime alerting | 10 min |
| **1Password / Bitwarden** | Password vault for the team | 30 min |
| **GitHub** | Source control | Already set up |
| **Provider A** (upstream proxy) | Live proxy fulfillment | 1-3 days (KYC) |
| **Provider B** (upstream proxy) | Backup proxy fulfillment | 1-3 days (KYC) |
| **LLM provider** (OpenAI or MiniMax) | Chatbot intelligence | 5 min if using existing, 1 day if doing new account |
| **Domain registrar** | Own the domain | 10 min |
| **WHOIS privacy** | Hide your name on the domain registration | Free |
| **Banking** | Receive Flutterwave payouts | Depends on country |

---

## Step 8 — Provider accounts to set up (upstream proxy IPs)

You'll sign up with **at least two** upstream proxy providers so you can:
1. Have redundancy when one is down
2. Switch without customers noticing
3. Negotiate better rates as volume grows

Sign up using a business email (`billing@styxproxy.com`). Get the following:

| Account detail | What it is |
|----------------|------------|
| API key (live) | Used by backend to create IPs |
| API key (sandbox) | Used for testing |
| Webhook endpoint URL | Where they POST IP-up/ban events |
| Account ID / sub-user | For multi-tenant tracking |
| Rate limits and quotas | Document what you start with |
| Pricing sheet | Compare $/GB, $/IP, $/sub etc. |
| Account manager contact | For when things break |
| Test credits | New accounts usually get $5-$50 free |

**Once signed up:**
- Add API keys to Railway env (Step 6)
- Add provider IPs/hostnames to backend's proxy pool allowlist
- Update `docs/DOMAIN_ARCHITECTURE.md` with the actual provider names (not on website, only in this internal doc)
- Configure webhook → `/api/v1/webhooks/{provider}` on your backend

---

## Step 9 — Flutterwave production onboarding

This is the longest lead-time item. **Start it now**, in parallel with VPS/domain setup.

1. Create a **Flutterwave business account** at dashboard.flutterwave.com
2. Submit:
   - Business name (your registered company)
   - Business type (LLC / sole proprietor)
   - Tax ID / TIN
   - Director's ID (passport, NIN, or national ID)
   - Bank account where payouts go
   - Address proof
3. Wait 1-3 business days for verification
4. Set **live secret key** (not the test one)
5. Configure webhook: `https://api.styxproxy.com/api/v1/webhooks/flutterwave`
6. Add your domain (`styxproxy.com`) to the Flutterwave allowlist
7. Test a live ₦100 transaction end-to-end before opening to the public
8. Update `/api/payments` route with the production key

**What can go wrong:**
- Flutterwave holds your first ₦100,000 in reserve for 7 days as fraud protection — be aware.
- They may require a registered CAC / business entity if you haven't already registered.

---

## Step 10 — Email authentication DNS records (do this BEFORE sending email)

Add these at your registrar (or Cloudflare):

| Type | Name | Value |
|------|------|-------|
| MX | @ | `1 aspmx.l.google.com` (or your provider) |
| MX | @ | `5 alt1.aspmx.l.google.com` |
| TXT | @ | `v=spf1 include:_spf.google.com ~all` |
| TXT | `google._domainkey` | Google gives you this on workspace setup |
| TXT | `_dmarc` | `v=DMARC1; p=quarantine; rua=mailto:dmarc@styxproxy.com` |

Then **verify** at mail-tester.com (aim for 10/10) and mxtoolbox.com/spf.

---

## Step 11 — Domain cutover plan (the "go live" checklist)

When you have:
- ✅ Domain registered
- ✅ Email working (admin@styxproxy.com verified)
- ✅ VPS / Railway configured
- ✅ Flutterwave approved

Execute in this order:

### Phase 1 — Infrastructure (do on a Tuesday morning, low traffic)
1. Add `app.styxproxy.com` to Vercel project → follow Vercel DNS wizard
2. Add `admin.styxproxy.com` to a separate Vercel project (private, not linked)
3. Add `api.styxproxy.com` A record pointing to Railway public URL OR VPS IP
4. Add MX, SPF, DKIM, DMARC records for email
5. Verify email with mail-tester.com

### Phase 2 — Software deploy
1. Merge all open PRs to `main`
2. Bump version in package.json (start at `1.0.0`)
3. Tag: `git tag v1.0.0`
4. Push to trigger Vercel + Railway auto-deploys
5. Wait for both to be green (Vercel shows "Ready", Railway shows "Deployed")

### Phase 3 — Verification (don't skip)
1. Visit `https://app.styxproxy.com` — page loads
2. Place a real test order with ₦100 minimum — payment goes through
3. Receive email confirmation at `support@styxproxy.com`
4. Receive email receipt from `noreply@styxproxy.com`
5. Manage page shows the order when you enter your tx_ref
6. WhatsApp / Telegram bot still works at the new domain
7. DNS resolves correctly (dig app.styxproxy.com)
8. SSL is valid (https://, lock icon)
9. HSTS header is set
10. Plausible is recording visits

### Phase 4 — DNS switch
1. Make `styxproxy.com` redirect → `app.styxproxy.com` (or set up marketing site later)
2. If you have separate marketing site: add apex domain to marketing Vercel project
3. Monitor first 24 hours for 5xx spikes

### Phase 5 — Customer communication
1. Send email blast (if you have a list): "We're moving to styxproxy.com"
2. Update all places that reference the old URL (Twitter bio, etc.)

---

## Step 12 — Pre-launch checklist (run this the day before)

```
[ ] All env vars set in Vercel + Railway
[ ] DNS records in place (verified with dig + nslookup)
[ ] SSL certs active (no browser warnings)
[ ] HSTS enabled (Strict-Transport-Security header)
[ ] CSP set (Content-Security-Policy)
[ ] Backup of database taken (pg_dump snapshot)
[ ] Monitoring dashboards created (Grafana, Sentry, Plausible)
[ ] Uptime alerts configured (PagerDuty, OpsGenie, email, or SMS)
[ ] Admin team has logins + 2FA enforced
[ ] Status page live (status.styxproxy.com)
[ ] Privacy / Terms / Refund / AUP / Cookie pages reviewed and accurate
[ ] Abuse / legal / privacy emails working
[ ] Test transaction end-to-end with real money (₦100)
[ ] Telegram bot verified working at new domain
[ ] WhatsApp bot verified working
[ ] Backup of Cloudflare zone DNS (export)
[ ] Backup of Vercel project config (download)
[ ] Backup of Railway service config (download)
[ ] Customer support inbox created and routing to team
[ ] All-team 1Password vault with all API keys (every account, every key)
```

---

## Step 13 — Cost summary (monthly)

| Item | Min tier | Recommended |
|------|----------|-------------|
| Domain (annual, /mo) | $1 | $1 (Cloudflare at-cost) |
| Vercel hosting | $0 (Hobby) | $20 (Pro, per project) |
| Railway backend | $5 base | $5-30 base + usage |
| Cloudflare Pro (optional) | $0 free | $20 (for DDoS protection if you get attacked) |
| Email (Google Workspace) | $0 (1 user free trial) | $7/user/mo if you have team |
| Plausible | $0 free tier | $9/mo for higher tier |
| UptimeRobot | $0 free | $7/mo for SMS alerts |
| Flutterwave | 1.4% per txn | n/a (variable) |
| LLM (Chatbot) | $0 (light use) | $20-100/mo (Charon usage) |
| Resend (transactional email) | $0 free tier | $20/mo |
| Telegram bot | $0 | $0 |
| WhatsApp Business | $0 Meta free tier | metered per conversation |
| Backblaze B2 (backups) | $7/TB/mo | $1-3/mo |
| Sentry | $0 free tier | $26/mo |

**Realistic budget at launch:** $50-150/mo all-in for under 1K customers. Scales to $300-500/mo at 10K customers.

---

## Step 14 — Runbook (post-launch)

When something breaks:

1. **Status page** — check `status.styxproxy.com` for known issues
2. **Sentry** — open issues sorted by frequency
3. **Railway logs** — backend errors
4. **Vercel logs** — frontend errors
5. **Plausible** — is traffic down? (suggests DNS or marketing issue)
6. **UptimeRobot** — is anything 5xx-ing?
7. **Customer inbox** — what are people complaining about?
8. **Backblaze backups** — restore point if DB needs to roll back

Escalation:
- Self → 1Password (find creds)
- Self → Cloudflare (DNS, DDoS, WAF rules)
- Support email → if persistent, post status update
- Domain Registrar → if domain itself is down (unlikely)
- LLM provider → if Charon is wrong
- Payments provider → if Flutterwave returns errors

---

## Appendix A — Personal data deletion request flow (privacy compliance)

When someone emails `privacy@styxproxy.com` asking for deletion:

1. Look up Customer by phone / email / Telegram ID
2. Delete Customer row in DB (cascade deletes orders, credentials)
3. Delete free trial survey postbacks
4. Delete support messages older than 90 days
5. Retain only:
   - Financial records for 7 years (tax law)
   - Anonymized, aggregated analytics (no PII)
6. Send confirmation email within 30 days
7. If customer only had website orders (no phone/email): there's nothing to delete — confirm to them

---

## Appendix B — What NOT to do before launch

- ❌ Don't buy a marketing push before the platform is stable
- ❌ Don't put a phone number on the website (it's scrapable, ends up in spam)
- ❌ Don't enable auto-responder on support@ with a "thanks we'll reply in 24 hours" until you have someone on the other side
- ❌ Don't promise SLAs in legal docs until you can deliver them
- ❌ Don't publish customer testimonials before the first 10 customers
- ❌ Don't include specific provider names in any customer-facing copy
- ❌ Don't take crypto payments (defeats the purpose of buying anonymity tools)
- ❌ Don't skip the refund-policy page — required for Flutterwave

---

## Appendix C — Open questions to resolve before launch

1. What is the operating entity name? (Required for banking + Flutterwave)
2. Do you have a registered company (CAC, US LLC, etc.)? If no, which jurisdiction?
3. Are you the only director or do you have a co-founder? (Affects banking, signatures, contracts)
4. What's the support SLA you want to advertise? ("24 hours" vs "next business day")
5. Do you want money-back or replacement-only? (Currently legal docs say both are options)

---

*Last reviewed: 2026-07-13. Keep this doc updated as you add tools, accounts, or subdomains.*

*Document owner: Engineering. Walk this from top to bottom before your first real customer order.*
