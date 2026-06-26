# Bunche — Tools & Requirements Checklist
*Everything you need to get before building. Get these first.*

---

## Account Setup Order

Get these in this order. Some depend on each other.

---

### Tier 1 — MUST Have Before Building (Week 1)

#### 1. VPS (Virtual Private Server)
| | |
|--|--|
| **What** | A cloud server to host n8n 24/7 |
| **Provider** | Hetzner Cloud (recommended) or DigitalOcean |
| **Link** | hetzner.com/cloud or digitalocean.com |
| **Spec needed** | CX21: 2 vCPU, 4 GB RAM, 80 GB SSD, ~€6-10/month |
| **SSH access** | You need root password OR SSH key — save this carefully |
| **Cost** | ~$10–20/month |
| **Action** | Spin up Ubuntu 22.04 LTS instance, note the IPv4 address |

#### 2. Domain Name
| | |
|--|--|
| **What** | A domain for n8n UI and webhook URLs |
| **Purpose** | `n8n.yourdomain.com` — WhatsApp webhooks need HTTPS |
| **Registrar** | Namecheap, Cloudflare, Porkbun |
| **Suggested name** | `bunche.ng` or `bunche.com` |
| **Cost** | $10–15/year |
| **Action** | Register domain, create A record pointing to VPS IP |

#### 3. Google Account (for Google Sheets)
| | |
|--|--|
| **What** | Free Google account to access Google Sheets |
| **Already have?** | Yes — use your existing Gmail/account |
| **Purpose** | Orders, Inventory, Customers, Providers sheets |
| **Cost** | Free |

---

### Tier 2 — Accounts for Payments & Messaging (Week 2)

#### 4. Flutterwave Merchant Account
| | |
|--|--|
| **What** | Nigerian payment processor — accepts transfer, card, USSD, QR |
| **Link** | flutterwave.com |
| **Cost** | 1.5% per transaction |
| **Settlement** | Bank transfer to Nigerian account within 24h |
| **Requirements** | CAC business registration, Nigerian bank account |
| **Webhook URL** | `https://n8n.yourdomain.com/webhook/flutterwave` |

#### 5. WhatsApp Business API
| | |
|--|--|
| **What** | Receive and send WhatsApp messages programmatically |
| **Provider** | Meta WhatsApp Business Cloud API |
| **Link** | business.whatsapp.com |
| **Cost** | Free to receive messages. Outbound: ~$0.05–0.10/message |
| **Alternative (easier)** | **Twilio WhatsApp** — twilio.com/whatsapp |

#### 6. Google Cloud Service Account (for Sheets API)
| | |
|--|--|
| **What** | Allows n8n to read/write Google Sheets programmatically |
| **Link** | console.cloud.google.com |
| **Cost** | Free (Google Sheets API has generous free quota) |

---

### Tier 3 — Proxy Provider APIs (Week 2)

| Provider | Best For | Sign Up | Wholesale Cost |
|----------|---------|---------|---------------|
| **IPRoyal** | ISP + Residential | iproyal.com | ~$7-10/IP/month |
| **NodeMaven** | Residential + ISP | nodemaven.com | ~$8-12/IP/month |
| **Proxy-Seller** | ISP + DC + Mobile | proxy-seller.com | ~$5-8/IP/month |

---

## What to Get vs What Sonny Will Build

| You Get | Sonny Will Build |
|---------|----------------|
| VPS + domain + DNS | n8n workflows (all 4) |
| Flutterwave account + API keys | Google Sheets templates |
| WhatsApp Business API setup | Legal documents (ToS, PP, AUP) |
| Google Cloud service account | Nginx reverse proxy config |
| IPRoyal/NodeMaven API accounts | Operational runbook |
| Google Sheets (4 tabs) | Provider API integration specs |
| CAC registration | |

---

## Budget Estimate (Month 1)

| Item | Cost |
|------|------|
| VPS (Hetzner/DO) | $10–20/month |
| Domain name | $10–15 (one-time) |
| Flutterwave | Free to sign up (1.5% per transaction) |
| WhatsApp outbound | ~$5–20/month |
| IPRoyal credit (starting) | $25–50 |
| CAC registration (Nigeria) | ~₦50,000–100,000 |
| **Total Month 1** | **~$80–165 + provider credit** |

---

## Quick-Start: What to Do Today

1. **Get a VPS** → Hetzner.com → spin up Ubuntu 22.04 → note IP address
2. **Buy domain** → Namecheap → point to that IP
3. **Create Flutterwave account** → flutterwave.com → sign up now (verification takes days)
4. **Create Google Sheets** → 4 tabs with column headers

While you wait for Flutterwave verification, we build the n8n workflows.
