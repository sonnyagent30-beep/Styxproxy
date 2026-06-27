# Bunche — Pricing Intelligence (UPDATED)

**Last Updated:** 2026-06-27
**Effective Date:** Upon rollout
**Purpose:** Buy price, sell price, exchange rate, and profit margins for all products.

---

## Exchange Rate

| Rate | Value | Source | Notes |
|------|-------|--------|-------|
| **Official NGN/USD** | ₦1,500/$1 | CBN official rate |
| **Parallel market** | ₦1,550–1,600/$1 | LocalFX / unofficial |
| **Safe working rate** | **₦1,500/$1** | Used for margin calculations |

**⚠️ FX Risk:** If parallel market moves to ₦1,700+/$1, margins compress. Monitor monthly.

---

## Buy Price (What Bunche Pays Providers)

### Proxy-Seller (ISP & Datacenter)

| Product | Buy Price | Notes |
|---------|----------|-------|
| ISP IPv4 (UK/US/DE/FR/CA) | $1.50/IP/month | Standard countries |
| ISP IPv4 (JP/AU/BR/SG/KR) | $2.00/IP/month | Premium countries |
| ISP IPv6 | $0.50/IP/month | Lower cost |
| Datacenter IPv4 | $0.70/IP/month | Standard DC |
| Datacenter IPv6 | $0.50/IP/month | Lower cost |
| DC Rotating | $0.45/GB | Via Rayobyte |

### DataImpulse (Residential & Mobile)

| Product | Buy Price | Notes |
|---------|----------|-------|
| Residential IPv4 | $1.00/GB | No expiry |
| Residential IPv6 | $0.80/GB | Lower cost |
| Mobile 4G/LTE | $2.00/GB | 30-day window |

---

## Sell Price (What Customers Pay)

### ISP Proxies (Monthly, Static IP)

| Product | Price | Expiry | IP Type | Protocols |
|---------|-------|-------|--------|----------|-----------|
| ISP UK | ₦5,000/mo | 30 days | IPv4 | SOCKS5, HTTP, HTTPS |
| ISP US | ₦5,000/mo | 30 days | IPv4 | SOCKS5, HTTP, HTTPS |
| ISP Germany | ₦5,000/mo | 30 days | IPv4 | SOCKS5, HTTP, HTTPS |
| ISP France | ₦5,000/mo | 30 days | IPv4 | SOCKS5, HTTP, HTTPS |
| ISP Canada | ₦5,000/mo | 30 days | IPv4 | SOCKS5, HTTP, HTTPS |
| ISP Japan | ₦6,500/mo | 30 days | IPv4 | SOCKS5, HTTP, HTTPS |
| ISP Australia | ₦6,500/mo | 30 days | IPv4 | SOCKS5, HTTP, HTTPS |
| ISP Brazil | ₦6,500/mo | 30 days | IPv4 | SOCKS5, HTTP, HTTPS |
| ISP Singapore | ₦6,500/mo | 30 days | IPv4 | SOCKS5, HTTP, HTTPS |
| ISP South Korea | ₦6,500/mo | 30 days | IPv4 | SOCKS5, HTTP, HTTPS |
| ISP IPv6 (UK) | ₦3,500/mo | 30 days | IPv6 | SOCKS5, HTTP, HTTPS |
| ISP IPv6 (US) | ₦3,500/mo | 30 days | IPv6 | SOCKS5, HTTP, HTTPS |

### Datacenter Proxies (Monthly)

| Product | Price | Expiry | Type | Protocols |
|---------|-------|-------|------|----------|
| DC Static IPv4 | ₦3,000/mo | 30 days | IPv4 | SOCKS5, HTTP, HTTPS |
| DC Static IPv6 | ₦2,500/mo | 30 days | IPv6 | SOCKS5, HTTP, HTTPS |
| DC Rotating | ₦4,500/GB | Per GB | IPv4 | SOCKS5, HTTP, HTTPS |

### Residential Proxies (GB-Based, No Expiry)

| Product | Price | Notes | Protocols |
|---------|-------|-------|----------|
| Residential IPv4 | ₦1,950/GB | No time expiry | SOCKS5, HTTP, HTTPS |
| Residential IPv6 | ₦1,500/GB | No time expiry | SOCKS5, HTTP, HTTPS |

### Mobile Proxies (4G/LTE, 30-Day Window)

| Product | Price | Notes | Protocols |
|---------|-------|-------|----------|
| Mobile 4G | ₦4,000/GB | 30-day window to use | SOCKS5, HTTP, HTTPS |

---

## Protocols Explained

### HTTP / HTTPS
- **Best for:** Web browsing, browser automation, scraping
- **Port:** 3128 (default)
- **Format:** `http://IP:port` or `https://IP:port`

### SOCKS5
- **Best for:** All traffic types (TCP/UDP), applications that don't support HTTP proxy
- **Port:** 1080 (default)
- **Format:** `socks5://IP:port`

**Both protocols are supported on all products.** You can use whichever works with your application.

---

## IPv4 vs IPv6 — Which Should You Choose?

### IPv4 (Recommended for Most Users)
| Pros | Cons |
|------|------|
| ✅ 99% of websites/apps support it | Slightly more expensive |
| ✅ Works everywhere | |
| ✅ Most popular type | |
| ✅ Best compatibility | |

### IPv6
| Pros | Cons |
|------|------|
| ✅ Cheaper | ⚠️ Not all websites/apps support it |
| ✅ Better for privacy (less tracked) | ⚠️ Some platforms block it |
| ✅ Future-proof | ⚠️ Limited availability |

### Recommendation
- **New users:** Start with **IPv4** — best compatibility
- **Advanced users:** IPv6 is fine if you know your target supports it
- **Budget-conscious:** IPv6 if supported by your target

---

## Use Case Guide

| Your Goal | Recommended Product |
|----------|-----------------|
| Social media accounts (Instagram, TikTok, etc.) | **ISP IPv4** |
| E-commerce (Amazon, eBay stores) | **ISP IPv4** |
| Web scraping / data collection | **Residential IPv4** |
| Browser automation | **Residential IPv4** |
| SEO tools / rank checking | **DC Static IPv4** |
| High-speed data collection | **DC Rotating** |
| Social media mobile app testing | **Mobile 4G** |
| Budget automation / testing | **IPv6** (if supported) |

---

## Refund Policy

| Product | Refund Window | Conditions |
|---------|--------------|------------|
| **Residential** | 7 days | From delivery, unused GB |
| **Mobile** | 7 days | From delivery, unused GB |
| **ISP** | 24 hours | Only if dead on arrival |
| **DC** | 24 hours | Only if dead on arrival |

**Note:** ISP and DC are time-based products. After 24 hours, no refunds — only IP replacement if dead.

---

## Profit Margins (at ₦1,500/USD)

### ISP Products

| Product | Sell | Buy (₦) | Profit | Margin |
|---------|------|---------|--------|--------|
| ISP UK/US/DE/FR/CA | ₦5,000 | ₦2,250 | **₦2,750** | **55%** |
| ISP JP/AU/BR/SG/KR | ₦6,500 | ₦3,000 | **₦3,500** | **54%** |
| ISP IPv6 | ₦3,500 | ₦750 | **₦2,750** | **79%** |

### Datacenter

| Product | Sell | Buy (₦) | Profit | Margin |
|---------|------|---------|--------|--------|
| DC Static IPv4 | ₦3,000 | ₦1,050 | **₦1,950** | **65%** |
| DC Static IPv6 | ₦2,500 | ₦750 | **₦1,750** | **70%** |
| DC Rotating | ₦4,500 | ₦675 | **₦3,825** | **85%** |

### Residential

| Product | Sell | Buy (₦) | Profit | Margin |
|---------|------|---------|--------|--------|
| Residential IPv4 | ₦1,950/GB | ₦1,500 | **₦450** | **23%** |
| Residential IPv6 | ₦1,500/GB | ₦1,200 | **₦300** | **20%** |

### Mobile

| Product | Sell | Buy (₦) | Profit | Margin |
|---------|------|---------|--------|--------|
| Mobile 4G | ₦4,000/GB | ₦3,000 | **₦1,000** | **33%** |

---

## Full Product Catalog

| # | Product | Provider | Buy | Sell | Margin |
|---|---------|----------|-----|------|--------|
| 1 | ISP UK | Proxy-Seller | $1.50 | ₦5,000 | 55% |
| 2 | ISP US | Proxy-Seller | $1.50 | ₦5,000 | 55% |
| 3 | ISP DE | Proxy-Seller | $1.50 | ₦5,000 | 55% |
| 4 | ISP FR | Proxy-Seller | $1.50 | ₦5,000 | 55% |
| 5 | ISP CA | Proxy-Seller | $1.50 | ₦5,000 | 55% |
| 6 | ISP JP | Proxy-Seller | $2.00 | ₦6,500 | 54% |
| 7 | ISP AU | Proxy-Seller | $2.00 | ₦6,500 | 54% |
| 8 | ISP BR | Proxy-Seller | $2.00 | ₦6,500 | 54% |
| 9 | ISP SG | Proxy-Seller | $2.00 | ₦6,500 | 54% |
| 10 | ISP KR | Proxy-Seller | $2.00 | ₦6,500 | 54% |
| 11 | ISP IPv6 UK | Proxy-Seller | $0.50 | ₦3,500 | 79% |
| 12 | ISP IPv6 US | Proxy-Seller | $0.50 | ₦3,500 | 79% |
| 13 | DC Static IPv4 | Proxy-Seller | $0.70 | ₦3,000 | 65% |
| 14 | DC Static IPv6 | Proxy-Seller | $0.50 | ₦2,500 | 70% |
| 15 | DC Rotating | Rayobyte | $0.45/GB | ₦4,500 | 85% |
| 16 | Residential IPv4 | DataImpulse | $1.00/GB | ₦1,950/GB | 23% |
| 17 | Residential IPv6 | DataImpulse | $0.80/GB | ₦1,500/GB | 20% |
| 18 | Mobile 4G | DataImpulse | $2.00/GB | ₦4,000/GB | 33% |

**Total Products:** 18

---

## Break-Even Analysis

| Product | Break-even FX | Current FX | Buffer |
|---------|--------------|------------|--------|
| ISP UK | ₦3,333/USD | ₦1,500 | +122% |
| DC Static | ₦2,857/USD | ₦1,500 | +90% |
| Residential | ₦1,625/USD | ₦1,500 | +8% |
| Mobile | ₦2,000/USD | ₦1,500 | +33% |

**⚠️ Watch:** Residential is most sensitive to FX. If NGN weakens past ₦1,625/$, residential becomes loss-making.

---

## Volume Discounts from Providers

### DataImpulse Volume Tiers

| GB Purchased | Rate/GB | 5GB Cost | 10GB Cost |
|-------------|---------|---------|----------|
| PAYG | $1.00 | $5.00 | $10.00 |
| 50GB+ | $0.80 | $4.00 | $8.00 |
| 100GB+ | $0.65 | $3.25 | $6.50 |
| 500GB+ | $0.55 | $2.75 | $5.50 |
| 1TB+ | $0.50 | $2.50 | $5.00 |

### Proxy-Seller Volume Tiers

| Product | 1 IP | 10 IPs | 50 IPs |
|---------|------|--------|--------|
| ISP | $1.50/IP | $1.35/IP | $1.20/IP |
| DC | $0.70/IP | $0.63/IP | $0.55/IP |

---

## IP Replacement Policy

| Provider | Replacement Window | How |
|----------|-------------------|-----|
| Proxy-Seller | 24 hours | API call for new IP |
| DataImpulse | 7 days | Auto-rotates, refund available |
| Rayobyte | N/A | Rotating, no replacement needed |

---

## Notes

- All ISP/DC prices include unlimited bandwidth within 30-day period
- Residential/Mobile data never expires (Residential) or 30-day window (Mobile)
- IPv6 products are newer and may have limited availability
- Monitor FX rate monthly — adjust prices if NGN weakens past ₦1,700/$
- All products support both SOCKS5 and HTTP/HTTPS protocols