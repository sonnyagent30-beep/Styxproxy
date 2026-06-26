# Bunche — Provider Setup Guide
*Step-by-step guide for setting up proxy provider API accounts*

---

## Provider Strategy

| Provider | Role | Best For |
|----------|------|---------|
| **IPRoyal** | Primary | ISP proxies (UK, US, NG) |
| **NodeMaven** | Secondary | Residential proxies |
| **Proxy-Seller** | Tertiary | Mobile, wide country coverage |
| **Bright Data / Oxylabs** | Enterprise backup | Rare countries, large volume |

---

## 1. IPRoyal Setup (Primary)

### 1.1 Create Account
1. Go to **iproyal.com**
2. Sign Up → Create reseller account
3. Use a dedicated email: `proxies@yourdomain.com`

### 1.2 Fund Account
1. Dashboard → **Billing**
2. Minimum deposit: **$25** (recommended: $50-100 to start)
3. Payment: Card, Crypto, Bank transfer

### 1.3 Get API Key
1. Dashboard → **API**
2. Copy your **Reseller API Key**
3. Add to n8n as `iproyal-api` credential

### 1.4 Test API

```bash
curl -X GET "https://api.iproyal.com/v2/reseller/account" \
  -H "Authorization: Bearer YOUR_API_KEY"
# Expected: {"balance": 50.00, "currency": "USD"}
```

### 1.5 Order Test Proxy

```bash
curl -X POST "https://api.iproyal.com/v2/reseller/orders" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"product_id": "isp", "country": "gb", "quantity": 1, "months": 1}'

# Response:
# {
#   "order_id": "ORD-12345",
#   "status": "active",
#   "credentials": [{"ip": "203.0.113.42", "port": 8080, "username": "cust12345", "password": "secretpass"}]
# }
```

### 1.6 IPRoyal Product IDs

| Product | product_id |
|---------|-----------|
| ISP Proxy | `isp` |
| Residential | `residential` |
| Datacenter | `datacenter` |
| Mobile | `mobile` |

---

## 2. NodeMaven Setup (Secondary)

### 2.1 Create Account
1. **nodemaven.com** → Get Started
2. Create reseller account

### 2.2 Fund + Get API Key
1. Dashboard → Billing → Add Funds (min $25)
2. Dashboard → API Access → Generate API key

### 2.3 Test API

```bash
curl -X GET "https://api.nodemaven.com/v1/account" \
  -H "Authorization: Bearer YOUR_API_KEY"
# Response: {"status": "ok", "balance": 25.00}
```

### 2.4 Order Test Proxy

```bash
curl -X POST "https://api.nodemaven.com/v1/orders" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"product": "residential", "country": "ng", "quantity": 1, "session": true}'
```

---

## 3. Proxy-Seller Setup (Tertiary)

### 3.1 Create Account
1. **proxy-seller.com**
2. Register → choose Reseller Program

### 3.2 Get API Key
1. Dashboard → API section
2. Enable API access
3. Copy API key

### 3.3 Test API

```bash
curl -X GET "https://api.proxy-seller.com/v1/account" \
  -H "X-API-Key: YOUR_API_KEY"
```

---

## 4. n8n Credential Setup

Create credentials in **n8n → Settings → Credentials**:

| Credential Name | Type | Auth |
|---------------|------|------|
| `iproyal-api` | HTTP Header Auth | `Authorization: Bearer YOUR_IPROYAL_KEY` |
| `nodemaven-api` | HTTP Query Auth | `Authorization: Bearer YOUR_NODEMAVEN_KEY` |
| `proxyseller-api` | HTTP Query Auth | `X-API-Key: YOUR_PROXYSELLER_KEY` |

---

## 5. Nigeria-Specific Notes

- **NG (Nigeria) ISP proxies:** IPRoyal has these. Important for local e-commerce (Jumia, Jiji).
- **NG Mobile proxies:** Check Proxy-Seller or NodeMaven for MTN/Airtel 4G IPs.
- **Exchange rate:** Check current NGN/USD rate before pricing. NGN weakness = raise prices.
- **Jumia:** Nigerian e-commerce. Good target customer. They detect proxies aggressively — recommend ISP > Residential for this use case.
