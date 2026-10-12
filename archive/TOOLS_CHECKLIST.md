# Bunche — Tools Checklist (Archived)
*This file is obsolete. Kept for historical reference only.*

---

## Must Have Before Building

| Tool | Purpose | Where | Cost |
|------|---------|-------|------|
| VPS (Ubuntu 22.04) | Host n8n, PostgreSQL, Redis | Hetzner / DigitalOcean | ~$10–20/mo |
| Domain | n8n webhooks + UI | Namecheap / Cloudflare | ~$10–15/yr |
| Flutterwave merchant | Accept payments in Nigeria | rave.flutterwave.com | 1.5% per tx |
| WhatsApp Business API | Customer messaging | business.whatsapp.com | Free receive |
| GitHub account | Store code + workflows | github.com | Free |
| Railway or Render | Alternative to VPS (not used) | railway.app | Free tier |

---

## Provider Accounts

| Provider | Products | Sign Up | Min. Credit |
|----------|---------|---------|-------------|
| Proxy-Seller | ISP, Datacenter | proxy-seller.com | $20 |
| DataImpulse | Residential, Mobile 4G | dataimpulse.com | $15 |

---

## n8n (Workflow Engine)

Installed via Docker on VPS.
Access: `https://n8n.yourdomain.com`

---

## PostgreSQL + Redis

Self-hosted on VPS.
PostgreSQL: database + customer/order records
Redis: caching + sessions + rate limiting

---

## LLM (Obsolete — See Below)

~~Ollama (local)~~ — Replaced by MiniMax M2 Cloud API.
MiniMax M2 is API-compatible with OpenAI — no local model needed.

---

## Cloudflare R2 (File Storage)

Used for: ban screenshots, PDF receipts
$0/month for 10GB storage + bandwidth

---

## This file was moved from `docs/TOOLS_CHECKLIST.md` on 2026-06-26.
The provider list it contains (IPRoyal, NodeMaven, OkeyProxy) is obsolete.
Current providers: Proxy-Seller + DataImpulse only.
