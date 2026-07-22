# Styxproxy — Static Website Design (styxproxy.com)

**Document Type:** Design Specification
**Date:** July 1, 2026
**Status:** Planning Complete
**Stack:** Static HTML/CSS/JS only — zero business logic, zero DB

---

## Overview

Styxproxy is a display-only static site. No business logic, no database, no payment processing. Its single job: convert visitors into WhatsApp/Telegram customers.

**Stack rule:** Static HTML/CSS/JS served by Nginx. CDN-ready. No React, no Next.js, no backend.

---

## Site Map

| Page | URL | Purpose |
|------|-----|---------|
| Homepage | `/` | Convert visitor → customer |
| Products | `/products.html` | Showcase all proxy products |
| Pricing | `/pricing.html` | NGN prices, plan comparison |
| How It Works | `/how-it-works.html` | 3-step process |
| FAQ | `/faq.html` | Common questions |
| Contact | `/contact.html` | Reach Styxproxy |
| Terms | `/terms.html` | Legal |
| Privacy | `/privacy.html` | Legal |
| AUP | `/acceptable-use.html` | Legal |

---

## Homepage (`/`)

**Above the fold (mobile):**
```
[Logo] Styxproxy Digital

🌍 Nigeria's Most Trusted Proxy Reseller

ISP • Datacenter • Residential • Mobile 4G

[Order on WhatsApp 🛡️]   [Try Telegram 🤖]

⚡ Instant Delivery  🏦 NGN Payments  📱 Mobile-First
```

**Social proof strip:**
```
✓ 2,000+ active customers  ✓ 99.9% uptime  ✓ 24/7 support  ✓ NDPR compliant
```

**Product category cards (4):**
```
[🌍 ISP] [💾 DC] [🏠 Residential] [📱 Mobile 4G]
 ₦5,000/mo  ₦2,500/mo   ₦1,500/GB    ₦6,000/GB
 [Learn More] [Learn More]  [Learn More]  [Learn More]
```

**Footer:**
```
Styxproxy Digital © 2026
Nigeria | hello@styxproxy.com | +234 703 298 1049
[Terms] [Privacy] [AUP]
```

---

## Products Page (`/products.html`)

Grid of product cards:

```html
<!-- ISP UK Clean -->
<div class="product-card">
  <span class="badge tier-1">TIER 1</span>
  <h3>ISP UK Clean</h3>
  <p class="provider">via Gecko • Scamalytics 0</p>
  <ul>
    <li>🇬🇧 United Kingdom</li>
    <li>Static IP — never rotates</li>
    <li>Scamalytics score: 0 (verified clean)</li>
    <li>Instant replacement</li>
    <li>1 IP minimum</li>
  </ul>
  <div class="price">₦6,500<span>/month</span></div>
  <a href="https://wa.me/234XXXXXXXXX?text=Hi%2C%20I%20want%20ISP%20UK%20Clean%20proxy" 
     class="btn whatsapp">Order on WhatsApp</a>
</div>
```

Product cards for: ISP UK Clean, ISP UK Standard, ISP Standard (Multi-Country), ISP Premium, DC IPv4, DC IPv6, DC Rotating, Residential IPv4, Residential IPv6, Mobile 4G.

---

## Pricing Page (`/pricing.html`)

Quick comparison table:

| Product | Price | Type | Min Order | Order |
|---------|-------|------|-----------|-------|
| 🌍 ISP UK Clean | ₦6,500/mo | Static IP | 1 IP | [WhatsApp →] |
| 🌍 ISP UK Standard | ₦5,000/mo | Static IP | 1 IP | [WhatsApp →] |
| 🌍 ISP US/DE/FR/CA | ₦5,000/mo | Static IP | 1 IP | [WhatsApp →] |
| 🌍 ISP Premium | ₦6,500/mo | Static IP | 1 IP | [WhatsApp →] |
| 💾 DC IPv4 | ₦3,000/mo | Static IP | 1 IP | [WhatsApp →] |
| 💾 DC IPv6 | ₦2,500/mo | Static IP | 1 IP | [WhatsApp →] |
| 💾 DC Rotating | ₦4,500/GB | Rotating | 1 GB | [WhatsApp →] |
| 🏠 Residential IPv4 | ₦1,950/GB | Residential | 1 GB | [WhatsApp →] |
| 🏠 Residential IPv6 | ₦1,500/GB | Residential | 1 GB | [WhatsApp →] |
| 📱 Mobile 4G | ₦6,000/GB | Mobile LTE | 1 GB | [WhatsApp →] |

---

## How It Works (`/how-it-works.html`)

```
1️⃣ Choose Your Proxy
   Browse products. Tell us type + country + quantity.
   [View Products]

2️⃣ Pay Securely
   Bank Transfer or Debit Card via Flutterwave.
   All in NGN.

3️⃣ Receive Credentials
   ⚡ Instant delivery on WhatsApp or Telegram.
   Username + password + proxy address.
   SLA: Within 30 minutes.
```

---

## FAQ Page (`/faq.html`)

Using `<details>` HTML elements:

- What is a proxy?
- What's the difference between ISP and Datacenter proxies?
- Do you offer refunds?
- How do I pay?
- How long does delivery take?
- My proxy is not working. What do I do?
- Can I get Nigerian IPs?
- What payment methods do you accept?

---

## Contact Page (`/contact.html`)

```
📱 WhatsApp (Preferred)
   Fastest response. Message us anytime.
   [Open WhatsApp] → https://wa.me/2347032981049

🤖 Telegram Bot
   Automated ordering 24/7.
   [Open Telegram] → https://t.me/BuncheBot

📧 Email
   hello@styxproxy.com
   Response: 1-4 hours

🌍 Business Hours
   24/7 automated ordering.
   Manual support: Mon-Sat, 8am-8pm (Africa/Lagos)
```

---

## User Flows

### New visitor → WhatsApp customer
```
Visitor lands on styxproxy.com
         ↓
Clicks "Order on WhatsApp" (primary CTA)
         ↓
WhatsApp opens with pre-filled message:
  "Hi, I want to buy a proxy"
         ↓
Operator/automated bot responds
         ↓
Customer selects product → pays → receives credentials
```

### Research visitor → Telegram customer
```
Visitor lands on styxproxy.com
         ↓
Browses Products + Pricing pages
         ↓
Clicks "Try Telegram Bot"
         ↓
Telegram opens to @BuncheBot
         ↓
Clicks /start → /order flow
         ↓
Pays via Flutterwave inline → credentials delivered instantly
```

---

## SEO Strategy

### Meta tags (every page)

```html
<title>Styxproxy Digital — Nigeria's Most Trusted Proxy Reseller | ISP, DC, Residential, Mobile 4G</title>
<meta name="description" content="Buy ISP, Datacenter, Residential & Mobile 4G proxies in Nigeria. Instant delivery on WhatsApp. NGN payments. Starting ₦1,500.">
<meta name="keywords" content="Nigeria proxy, ISP proxy Nigeria, datacenter proxy Nigeria, residential proxy Nigeria, mobile 4G proxy, proxy reseller Nigeria, buy proxy NGN">
```

### Target keywords per page

| Page | Target Keywords |
|------|----------------|
| Homepage | "Nigeria proxy", "buy proxy Nigeria", "proxy reseller Lagos" |
| Products | "ISP proxy Nigeria", "datacenter proxy", "residential proxy Nigeria" |
| Pricing | "proxy price Nigeria", "cheap proxy NGN", "ISP proxy price" |
| FAQ | "proxy FAQ Nigeria", "best proxy for web scraping" |

---

## Mobile-First Requirements

**Nigeria context:** 70%+ of web traffic is mobile.

| Requirement | Implementation |
|------------|----------------|
| Viewport | `<meta name="viewport" content="width=device-width, initial-scale=1">` |
| Tap targets | Minimum 48px × 48px |
| Font size | Minimum 16px body text |
| WhatsApp button | Sticky bottom bar on mobile |
| No horizontal scroll | Tables scroll horizontally or collapse to cards |

### Mobile sticky CTA bar

```html
<div class="mobile-sticky-cta">
  <a href="https://wa.me/2347032981049" class="btn-whatsapp">
    📱 Order on WhatsApp
  </a>
</div>

<style>
.mobile-sticky-cta {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  background: white;
  padding: 12px 16px;
  box-shadow: 0 -2px 10px rgba(0,0,0,0.1);
  z-index: 1000;
  display: none;
}
@media (max-width: 768px) { .mobile-sticky-cta { display: block; } }
</style>
```

---

## Design System

### Colors

| Role | Color | Hex |
|------|-------|-----|
| Primary | Green | `#25D366` |
| Secondary | Blue | `#0088CC` |
| Dark | Charcoal | `#1A1A2E` |
| Light | Off-white | `#F8F9FA` |
| Text | Dark gray | `#333333` |
| Accent | Gold | `#F5A623` |

### Typography

- **Headings + Body:** Inter (Google Fonts)
- **Fallback:** -apple-system, BlinkMacSystemFont, sans-serif

### File Structure

```
styxproxy.com/
├── index.html
├── products.html
├── pricing.html
├── how-it-works.html
├── faq.html
├── contact.html
├── legal/
│   ├── terms.html
│   ├── privacy.html
│   └── acceptable-use.html
├── css/
│   └── style.css
├── js/
│   └── main.js
└── assets/
    ├── og-image.png
    ├── favicon.ico
    └── logo.svg
```

---

## WhatsApp / Telegram Integration

### Pre-filled WhatsApp messages

| Product | Pre-filled message |
|---------|-------------------|
| ISP UK Clean | `Hi, I want ISP UK Clean proxy` |
| ISP Standard | `Hi, I want ISP Standard proxy` |
| DC IPv4 | `Hi, I want DC IPv4 proxy` |
| Mobile 4G | `Hi, I want Mobile 4G proxy` |
| Free Trial | `Hi, I want to try the free trial` |
| General | `Hi, I want to buy a proxy` |

URL encoded: `https://wa.me/234XXXXXXXXX?text=Hi%2C%20I%20want%20ISP%20UK%20Clean%20proxy`
