# Bunche — Provider Setup Guide (Archived)
*This file is obsolete. Kept for historical reference only.*

---

## Current Providers

Bunche now uses only two providers:

| Provider | Products | Website |
|----------|---------|---------|
| **Proxy-Seller** | ISP, Datacenter | proxy-seller.com |
| **DataImpulse** | Residential, Mobile 4G | dataimpulse.com |

**OkeyProxy, IPRoyal, NodeMaven, and OkeyProxy Residential have been removed from the system.**

---

## Proxy-Seller Setup

### Create Account
1. Go to proxy-seller.com → Reseller Program
2. Sign up with email + password
3. Fund account ($20–30 minimum)

### API Key
Found at: proxy-seller.com → Dashboard → API

```
Base URL: https://api.proxy-seller.com/v1.0
Authentication: X-API-KEY header
```

### Test Connection
```bash
curl -H "X-API-KEY: YOUR_KEY" https://api.proxy-seller.com/v1.0/balance
```

---

## DataImpulse Setup

### Create Account
1. Go to dataimpulse.com → Reseller
2. Sign up
3. Fund account ($15–20 minimum)

### API Key
Found at: dataimpulse.com → Dashboard → API

```
Base URL: https://api.dataimpulse.com
Authentication: Bearer token
```

### Test Connection
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" https://api.dataimpulse.com/account
```

### Note on Credit
DataImpulse credit **never expires**. Residential proxies last until GB is used up.

---

## Products Summary

| Product | Provider | Tracking |
|---------|----------|----------|
| ISP | Proxy-Seller | Time-based (expires on date) |
| DC | Proxy-Seller | Time-based (expires on date) |
| Residential | DataImpulse | Data-based (no time expiry) |
| Mobile 4G | DataImpulse | Data-based (30-day window) |

---

## This file was moved from `docs/PROVIDER_SETUP_GUIDE.md` on 2026-06-26.
OkeyProxy has been removed from the system.
