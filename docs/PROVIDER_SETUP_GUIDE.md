# Bunche — Provider Setup Guide
*Zero-inventory, on-demand only. Three providers cover all product types.*

---

## Provider Strategy

| Provider | Role | Product Types | Countries |
|----------|------|--------------|-----------|
| **Proxy-Seller** | Primary | ISP, Datacenter | 220+ |
| **OkeyProxy** | Secondary | Residential | 200+ |
| **DataImpulse** | Tertiary | Mobile 4G | Global |

---

## 1. Proxy-Seller (Primary — ISP + Datacenter)

**Best for:** ISP proxies (all countries), Datacenter proxies
**Why:** Cheapest ISP at $1.50–3/IP, 220+ countries, instant API

### 1.1 Create Account
1. Go to **proxy-seller.com**
2. Sign Up → Reseller account
3. Use a dedicated email

### 1.2 Fund Account
1. Dashboard → Billing
2. Minimum deposit: **$20** to start
3. Payment: Card, Crypto, Bank transfer

### 1.3 Get API Key
1. Dashboard → API section
2. Enable API access
3. Copy the API key
4. Add to n8n as `proxyseller-api`

### 1.4 Test API

```bash
curl -X GET "https://api.proxy-seller.com/v1/account" \
  -H "Authorization: Bearer YOUR_API_KEY"
# Expected: {"balance": 20.00, "currency": "USD"}
```

### 1.5 Order Test Proxy

```bash
curl -X POST "https://api.proxy-seller.com/v1/orders" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"type": "isp", "country": "gb", "quantity": 1, "period": 30}'

# Response:
# {
#   "order_id": "PS-12345",
#   "status": "active",
#   "proxies": [{"ip": "203.0.113.42", "port": 8080, "username": "user", "password": "pass", "expires_at": "2026-07-26"}]
# }
```

---

## 2. OkeyProxy (Secondary — Residential)

**Best for:** Residential proxies, global coverage
**Why:** 150M+ IPs, $0.35/GB, 200+ countries, fast API

### 2.1 Create Account
1. Go to **okeyproxy.com**
2. Sign Up

### 2.2 Fund + Get API Key
1. Dashboard → Billing → Add Funds (min $10)
2. Dashboard → API → Copy API key
3. Add to n8n as `okeyproxy-api`

### 2.3 Test API

```bash
curl -X GET "https://api.okeyproxy.com/v1/account" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

### 2.4 Order Test Proxy

```bash
curl -X POST "https://api.okeyproxy.com/v1/order" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"type": "residential", "country": "us", "traffic": "5GB"}'
```

---

## 3. DataImpulse (Tertiary — Mobile 4G)

**Best for:** Mobile 4G/LTE proxies
**Why:** $2/GB, credit never expires, global coverage

### 3.1 Create Account
1. Go to **dataimpulse.com**
2. Sign Up

### 3.2 Fund + Get API Key
1. Dashboard → Billing → Add Funds (min $15)
2. Dashboard → API → Copy key
3. Add to n8n as `dataimpulse-api`

### 3.3 Test API

```bash
curl -X GET "https://api.dataimpulse.com/v1/account" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

### 3.4 Order Test Proxy

```bash
curl -X POST "https://api.dataimpulse.com/v1/order" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"type": "mobile", "country": "us", "traffic": "5GB"}'
```

---

## n8n Credentials Setup

Create these in **n8n → Settings → Credentials**:

| Name | Type | Auth |
|------|------|------|
| `proxyseller-api` | HTTP Header Auth | `Authorization: Bearer YOUR_KEY` |
| `okeyproxy-api` | HTTP Header Auth | `Authorization: Bearer YOUR_KEY` |
| `dataimpulse-api` | HTTP Header Auth | `Authorization: Bearer YOUR_KEY` |

---

## Country Coverage Summary

| Provider | Countries | Notes |
|---------|-----------|-------|
| Proxy-Seller | 220+ | ISP + DC. All major countries. |
| OkeyProxy | 200+ | Residential. Global. |
| DataImpulse | Global | Mobile 4G. Credit never expires. |

---

## Initial Credit to Load

| Provider | Minimum | Recommended |
|---------|---------|-------------|
| Proxy-Seller | $20 | $30 |
| OkeyProxy | $10 | $15 |
| DataImpulse | $15 | $20 |
| **Total** | **$45** | **$65** |

Load $65 across all three. This covers ~20–30 orders before you need to top up.
