# BUNCHE OPERATIONAL WORKFLOW
## Monthly Single-Unit Proxy Reseller Operations

---

**Document Type:** Operational Playbook  
**Role:** Operations Manager  
**Date:** June 29, 2026  
**Classification:** Internal Use

---

## Table of Contents

1. [Product Catalog & Provider Mapping](#1-product-catalog--provider-mapping)
2. [Ordering Workflow](#2-ordering-workflow)
3. [Customer Delivery Workflow](#3-customer-delivery-workflow)
4. [Dead IP Replacement Workflow](#4-dead-ip-replacement-workflow)
5. [Refund Handling Process](#5-refund-handling-process)
6. [Minimum Stock Requirements](#6-minimum-stock-requirements)
7. [ SLA Targets](#7-sla-targets)

---

## 1. Product Catalog & Provider Mapping

### Provider TIER Classification

| TIER | Providers | Verification Status |
|-----|-----------|----------------------|
| **TIER_1** | Bright Data, Gecko | Verified - Production Ready |
| **TIER_2** | Proxy-Seller, Decodo, Evomi | Standard - Backup/Secondary |

> **TIER DEFINITIONS:**
> - **TIER_1:** Verified providers with proven track record, instant replacement, 99%+ uptime SLA
> - **TIER_2:** Standard providers, backup use, 24-48hr replacement SLA

### Product-to-Provider Reference Table

| Product Category | Bunche SKU | Primary Provider | Backup Provider | TIER | Buy Cost (USD) | Sell Price (₦) | Margin % |
|-----------------|-----------|-----------------|-----------------|------|----------------|----------------|-----------------|
| ISP UK Clean (Glide) | ISP-UK-GLIDE | IPRoyal (Glide) | Bright Data | TIER_1 | $2.70/IP | 6,500/mo | 37% |
| ISP UK Standard | ISP-UK-STD | Bright Data | Proxy-Seller | TIER_1 | $1.30/IP | 5,000/mo | 26-61% |
| ISP Standard (US/DE/FR/CA) | ISP-STD | Bright Data | Proxy-Seller | TIER_1 | $1.30/IP | 5,000/mo | 26-61% |
| ISP Premium (JP/AU/BR/SG/KR) | ISP-PRM | Decodo | Rayobyte | TIER_2 | $2.10/IP | 6,500/mo | 52% |
| ISP IPv6 | ISP-V6 | Proxy-Seller | Bright Data | TIER_2 | $0.15/IP | 3,500/mo | 91-94% |
| DC Static IPv4 (Datacenter) | DC-IPv4 | Webshare | ProxyScrape | TIER_2 | $0.05/IP | 3,000/mo | 85-99% |
| DC Static IPv6 | DC-IPv6 | Webshare | ProxyScrape | TIER_2 | $0.02/IP | 2,500/mo | 90-99% |
| DC Rotating | DC-ROT | ProxyScrape | Decodo | TIER_2 | $0.02/IP | 4,500/GB | 20-99% |
| Residential IPv4 | RES-IPv4 | DataImpulse | FloppyData | TIER_2 | $1.00/GB | 1,950/GB | 35-54% |
| Residential IPv6 | RES-IPv6 | DataImpulse | IPRoyal | TIER_2 | $1.00/GB | 1,500/GB | 40-50% |
| Mobile 4G | MOB-4G | IPRoyal | NetNut | TIER_2 | $2.00/GB | 6,000/GB | 50%+ |
| ISP US (Gecko - Scamalytics 0) | ISP-US-GECKO | Gecko | - | TIER_1 | TBD | TBD | TBD% |

> **NOTE:** Mobile 4G pricing increased from ₦4,000 to ₦6,000/GB per market intelligence.

### Market Gap Analysis

#### 🚨 Identified Gaps

| Gap Category | Description | Impact | Recommended Action |
|--------------|-------------|--------|---------------------|
| **Mobile 4G/LTE** | Limited Tier-1 mobile providers in Nigeria market | High - Premium pricing, single source risk | Evaluate NetNut, Oxylabs as secondary |
| **Budget Tier** | Infatica at ₦2,100 vs market ₦1,500-2,000 | Medium - Price competitiveness gap | Monitor Infatica pricing, consider for budget segment |
| **Nigerian Local IPs** | No verified Nigerian ISP proxies available | High - Local market need unmet | Research local ISP partnerships |
| **Gecko Integration** | US-only, Scamalytics 0 - verified clean | Low - New provider, testing phase | Pilot program before full integration |

#### ⚠️ Pricing Drift Risk

> **WARNING:** Provider pricing is subject to change without notice. Monitor wholesale costs monthly. Recent increases observed:
> - Mobile 4G: ₦4,000 → ₦6,000/GB (+50%)
> - ISP Premium: $1.80 → $2.10/IP (+17%)
>
> **Mitigation:** Maintain 30%+ margin buffer, review pricing quarterly, diversify provider mix.

---

## 2. Ordering Workflow

### 2.1 ISP Proxies (Static Residential)

**Workflow 2.1: Ordering ISP Proxies**

```
STEP 1: Check Stock Inventory
        ↓
   [Stock ≥ Minimum?] → NO → STEP 2
                     → YES → END (no order needed)
        
STEP 2: Select Provider
        ├─ ISP UK CLEAN (Glide): IPRoyal → dashboard.iproyal.com
        ├─ ISP UK Standard: Bright Data → dashboard.brightdata.com
        ├─ ISP US (Gecko): Gecko → dashboard.gecko.io
        └─ ISP Other Countries: Proxy-Seller → dashboard.proxy-seller.com
        
STEP 3: Place Order
        ├─ IPROYAL (Glide):
        │   ├─ URL: dashboard.iproyal.com → ISP Proxies
        │   ├─ Country: United Kingdom
        │   ├─ Quantity: 1 IP minimum
        │   └─ Plan: 30 days ($2.70/IP)
        │
        ├─ BRIGHT DATA:
        │   ├─ Method: Dashboard or API
        │   ├─ URL: dashboard.brightdata.com → Residential/ISP
        │   └─ Quantity: 1 IP minimum, bulk discount at 10+
        │
        ├─ GECKO (TIER_1):
        │   ├─ Method: Dashboard
        │   ├─ URL: dashboard.gecko.io
        │   ├─ Country: United States only
        │   └─ Note: Scamalytics 0 (verified clean)
        │
        └─ PROXY-SELLER (TIER_2):
            ├─ Method: Dashboard
            ├─ URL: dashboard.proxy-seller.com
            └─ Quantity: 1 IP minimum
            
STEP 4: Payment
        ├─ Auto-debit from prepaid account
        └─ Or: Invoice + bank transfer (enterprise)
        
STEP 5: Provisioning
        ├─ IPRoyal: Instant (< 1 minute)
        ├─ Bright Data: Instant (< 1 minute)
        ├─ Gecko: Instant (< 1 minute)
        └─ Proxy-Seller: 5-15 minutes
        
STEP 6: Record & Stock Update
        └─ Update inventory spreadsheet → END
```

**Step-by-Step Instructions:**

| Step | Action | Tool/URL | SLA |
|------|-------|----------|-----|
| 1 | Check current stock | `/inventory` sheet | Real-time |
| 2 | Login to provider dashboard | dashboard.brightdata.com | N/A |
| 3 | Select ISP type, country, quantity | Dashboard UI | N/A |
| 4 | Confirm payment | Auto-debit | N/A |
| 5 | Wait for provisioning | Email/webhook | < 15 min |
| 6 | Record in inventory | Google Sheets | Immediate |

### 2.2 Residential Proxies (GB-Based)

**Workflow 2.2: Ordering Residential Proxies**

```
STEP 1: Check Data Usage
        ↓
   [Remaining GB ≤ 20GB?] → NO → STEP 2
                         → YES → Order more
        
STEP 2: Select Provider
        ├─ Primary: DataImpulse (verify no billing issues)
        └─ Backup: FloppyData or PacketStream
        
STEP 3: Place Order
        ├─ DATAIMPULSE:
        │   ├─ Method: Dashboard
        │   ├─ URL: dashboard.dataimpulse.com
        │   └─ Quantity: 50GB minimum (min order)
        │
        └─ FLOPPYDATA:
            ├─ Method: Dashboard
            └─ URL: dashboard.floppydata.io
            
STEP 4: Payment
        └─ Prepaid balance or card on file
        
STEP 5: Activation
        └─ Instant → Update credentials → END
```

**Step-by-Step Instructions:**

| Step | Action | Tool/URL | SLA |
|------|-------|----------|-----|
| 1 | Check data balance | Provider dashboard | Real-time |
| 2 | Verify billing status | Check recent transactions | Before order |
| 3 | Add funds/purchase GB | Dashboard → Add Funds | N/A |
| 4 | Generate new credentials | Dashboard → Credentials | Instant |
| 5 | Record in inventory | Google Sheets | Immediate |

### 2.3 Datacenter Proxies

**Workflow 2.3: Ordering Datacenter Proxies**

```
STEP 1: Check Stock
        ↓
   [Stock < Minimum?] → Order
        
STEP 2: Select Provider
        ├─ Primary: Webshare (free tier available) - Datacenter IPv4
        └─ Backup: ProxyScrape
        
STEP 3: Order Method
        ├─ WEBSHARE (Datacenter IPv4):
        │   ├─ Method: Dashboard
        │   ├─ URL: dashboard.webshare.io
        │   ├─ Type: Datacenter IPv4 (NOT ISP)
        │   └─ Free tier: 10 proxies ongoing
        │
        └─ PROXYSCRAPE:
            ├─ Method: Dashboard/API
            └─ URL: dashboard.proxyscrape.com
            
STEP 4: Delivery
        └─ Credentials via dashboard/API → END
```

> **NOTE:** Webshare provides **Datacenter IPv4** (static datacenter IPs), NOT ISP/residential proxies. Use for different use cases.

### 2.4 Mobile 4G Proxies

**Workflow 2.4: Ordering Mobile 4G Proxies**

```
STEP 1: Check Data/Stock
        ↓
   [Need more capacity?]
        
STEP 2: Select Provider
        ├─ Primary: IPRoyal
        └─ Backup: NetNut (premium)
        
STEP 3: Order
        ├─ IPROYAL:
        │   ├─ Method: Dashboard
        │   └─ URL: dashboard.iproyal.com
        │
        └─ NETNUT:
            └─ Method: Dashboard (enterprise)
            
STEP 4: Payment & Provisioning
        └─ Note: Higher cost, ensure margin → END
```

> **⚠️ GAP WARNING:** Mobile 4G/LTE has limited Tier-1 options. Current primary (IPRoyal) is single source for Nigeria market. Monitor NetNut/Oxylabs as backup.

---

## 3. Customer Delivery Workflow

### 3.1 Automated Delivery (Preferred)

**Delivery Workflow 3A: Automated via Dashboard/Link**

```
CUSTOMER PURCHASE
       ↓
PAYMENT CONFIRMED (Flutterwave/Paya)
       ↓
AUTO-TRIGGER: Order Fulfillment Script
       ↓
[In Stock?] → NO → Manual intervention
           → YES → Generate credentials
       ↓
SEND TO CUSTOMER
├─ Email: credentials + setup guide
├─ WhatsApp: quick delivery
└─ Dashboard: self-service portal
       ↓
COMPLETION: Log transaction → END
```

**Automated Delivery Steps:**

| Step | Action | Automation | SLA |
|------|-------|------------|-----|
| 1 | Payment notification | Webhook from payment gateway | Real-time |
| 2 | Stock check | Script checks inventory | < 30 sec |
| 3 | Generate credentials | Provider API | < 1 min |
| 4 | Send delivery email | Automated email sequence | < 2 min |
| 5 | Log transaction | Google Sheets update | Instant |

### 3.2 Manual Delivery (Backup)

**Delivery Workflow 3B: Manual Delivery**

```
CUSTOMER PURCHASE
       ↓
PAYMENT CONFIRMED
       ↓
MANUAL REVIEW
       ↓
[In Stock?] → NO → Order from provider (see Workflow 2)
         → YES → Manual credential generation
       ↓
DELIVER TO CUSTOMER
├─ Email delivery
├─ WhatsApp message
└─ Screen share setup (if needed)
       ↓
LOG & COMPLETE
```

### 3.3 Delivery Formats by Product

| Product | Delivery Format | Content Sent |
|----------|------------------|--------------|
| ISP Static | Credentials + guide | IP:Port:User:Pass + country setup |
| Residential | Proxy link + credentials | Gateway URL + user:pass |
| Datacenter (IPv4) | IP list + credentials | IP list + port + auth |
| Mobile | Credentials + SIM info | IP + carrier + APN settings |

---

## 4. Dead IP Replacement Workflow

### 4.1 Customer Reports Dead IP

**Replacement Workflow 4.1: Customer-Initiated**

```
CUSTOMER REPORTS: "IP not working"
       ↓
STEP 1: Verify Issue
       ├─ Test IP ourselves
       └─ Ask customer for error message
       ↓
[Confirmed Dead?] → NO → Troubleshooting
                 → YES → STEP 2
       ↓
STEP 2: Replace from Stock
       ├─ Check inventory for replacement
       └─ [Have spare?] → YES → Replace
       └─ [No spare?] → Order new (see Workflow 2)
       ↓
STEP 3: Deliver Replacement
       └─ Send new credentials → STEP 4
       ↓
STEP 4: Provider Refund/Replacement
       ├─ Request from provider (dashboard/ticket)
       └─ Or: Automatic via API
       ↓
STEP 5: Log & Close
       └─ Update ticket → END
```

### 4.2 Proactive Replacement

**Replacement Workflow 4.2: Proactive (Weekly Check)**

```
WEEKLY SCHEDULED TASK
       ↓
CHECK ALL ACTIVE IPs
├─ Test via API/script
└─ Mark failures
       ↓
IDENTIFY DEAD IPs
       ↓
[Dead IPs Found?] → NO → END
               → YES → STEP 3
       ↓
STEP 3: Bulk Replace
       ├─ Request from provider (SLA: see table below)
       └─ Or: API call for new IPs
       ↓
STEP 4: Update Customers
       └─ Notify affected customers → END
```

### 4.3 Provider Replacement SLAs

| Provider | TIER | Replacement SLA | Monthly Cap | How to Request |
|----------|------|------------------|------------|-----------------|
| Bright Data | TIER_1 | Instant | Unlimited | Dashboard/API |
| Gecko | TIER_1 | Instant | Unlimited | Dashboard |
| Decodo | TIER_2 | < 1 hour | Unlimited | Dashboard |
| DataImpulse | TIER_2 | < 24 hours | Unlimited | Dashboard |
| IPRoyal | TIER_2 | 24-48 hours | 10% pool | Dashboard |
| Webshare | TIER_2 | 24-48 hours | Varies | Dashboard |
| Proxy-Seller | TIER_2 | 24-48 hours | Unlimited | Dashboard |
| PacketStream | TIER_2 | 24-72 hours | Varies | Ticket |

### 4.4 Replacement Request Methods

| Provider | Method | URL/Contact |
|----------|--------|------------|
| Bright Data | API | `api.brightdata.com` |
| Gecko | Dashboard | dashboard.gecko.io |
| Decodo | Dashboard | dashboard.decodo.com |
| DataImpulse | Dashboard | dashboard.dataimpulse.com |
| IPRoyal | Dashboard | dashboard.iproyal.com |
| Webshare | Dashboard | dashboard.webshare.io |
| Proxy-Seller | Dashboard | dashboard.proxy-seller.com |

---

## 5. Refund Handling Process

### 5.1 Refund Eligibility Matrix

| Condition | Eligible? | Notes |
|-----------|-----------|-------|
| IP dead on delivery | ✅ Yes | Immediate replacement or refund |
| Doesn't work for use case | ⚠️ Case-by-case | May require proof |
| Changed mind | ❌ No | 24-hour window only |
| Better price elsewhere | ❌ No | Not a valid reason |
| Provider outage | ⚠️ Pro-rata | Credit for downtime |

### 5.2 Refund Workflow

**Refund Workflow 5: Customer Refund Request**

```
CUSTOMER REQUESTS REFUND
       ↓
STEP 1: Validate Request
       ├─ Check purchase date
       ├─ Check usage (GB consumed)
       └─ Check reason
       ↓
[Eligible?] → NO → Deny politely
          → YES → STEP 2
       ↓
STEP 2: Calculate Refund
       ├─ Unused GB at pro-rata
       └─ Minus processing fee (if applicable)
       ↓
STEP 3: Process Refund
       ├─ Original payment method
       └─ Or: Account credit (preferred)
       ↓
STEP 4: Log & Close
       └─ Update records → END
```

### 5.3 Provider-Level Refund Recovery

| Provider | TIER | Refund Window | How to Claim | Notes |
|----------|------|-------------|-------------|-------------|
| DataImpulse | TIER_2 | N/A | Traffic never expires | No refund needed |
| Decodo | TIER_2 | 3 days | Dashboard request | First purchase only |
| Bright Data | TIER_1 | 7 days | Support ticket | Enterprise plans |
| IPRoyal | TIER_2 | 3 days | Dashboard | Unused traffic |
| PacketStream | TIER_2 | 7 days | Support | Pro-rated |
| Rayobyte | TIER_2 | 7 days | Dashboard | Unused bandwidth |
| ProxyEmpire | TIER_2 | ❌ None | N/A | **Avoid** |

### 5.4 Refund Processing Steps

| Step | Action | Who | SLA |
|------|-------|-----|-----|
| 1 | Acknowledge request | Ops | < 4 hours |
| 2 | Review eligibility | Ops | < 24 hours |
| 3 | Calculate amount | Ops | < 24 hours |
| 4 | Approve | Manager | < 24 hours |
| 5 | Process payment | Finance | 3-5 days |
| 6 | Confirm to customer | Ops | < 24 hours |

---

## 6. Minimum Stock Requirements

### 6.1 Stock Calculation Method

```
DAILY AVERAGE ORDERS (last 30 days)
       ↓
× REPLENISHMENT LEAD TIME (days)
       ↓
+ SAFETY STOCK (20%)
       ↓
= MINIMUM STOCK LEVEL
```

### 6.2 Recommended Minimum Stock

| Product | TIER | Daily Avg Demand | Lead Time | Safety | Min Stock |
|---------|------|------------------|-----------|--------|----------|
| ISP UK Clean (Glide) | TIER_1 | 1 IP/day | 1 day | 20% | 3 IPs |
| ISP UK Standard | TIER_1 | 1 IP/day | 2 days | 20% | 3 IPs |
| ISP Standard (US/DE/FR/CA) | TIER_1 | 1 IP/day | 2 days | 20% | 3 IPs |
| ISP US (Gecko) | TIER_1 | 1 IP/day | 1 day | 20% | 3 IPs |
| ISP Premium | TIER_2 | 1 IP/day | 2 days | 20% | 3 IPs |
| ISP IPv6 | TIER_2 | 1 IP/day | 2 days | 20% | 3 IPs |
| DC Static IPv4 | TIER_2 | 5 IPs/day | 1 day | 20% | 7 IPs |
| DC Static IPv6 | TIER_2 | 3 IPs/day | 1 day | 20% | 4 IPs |
| DC Rotating | TIER_2 | 2 IPs/day | 1 day | 20% | 3 IPs |
| Residential | TIER_2 | 10 GB/day | 1 day | 20% | 15 GB |
| Mobile 4G | TIER_2 | 5 GB/day | 2 days | 20% | 13 GB |

### 6.3 Stock Reorder Points

| Product | Reorder Point | Action |
|---------|--------------|--------|
| ISP UK Clean (Glide) | 2 IPs | Order 5 |
| ISP UK Standard | 2 IPs | Order 5 |
| ISP Standard (US/DE/FR/CA) | 2 IPs | Order 5 |
| ISP US (Gecko) | 2 IPs | Order 5 |
| ISP Premium | 2 IPs | Order 5 |
| ISP IPv6 | 2 IPs | Order 5 |
| DC Static IPv4 | 5 IPs | Order 20 |
| DC Static IPv6 | 3 IPs | Order 10 |
| DC Rotating | 2 IPs | Order 10 |
| Residential | 10 GB | Order 50 |
| Mobile 4G | 8 GB | Order 20 |

---

## 7. SLA Targets

### 7.1 Internal SLA Targets

| Process | Target | Maximum | Who |
|---------|--------|---------|-----|
| Order fulfillment | < 15 min | 1 hour | Ops |
| Payment confirmation | < 1 min | 5 min | System |
| Dead IP replacement | < 2 hours | 24 hours | Ops |
| Refund acknowledgment | < 4 hours | 8 hours | Ops |
| Refund completion | < 3 days | 5 days | Finance |
| Customer reply | < 2 hours | 4 hours | Support |
| Data alert response | < 30 min | 1 hour | Ops |

### 7.2 Provider SLA Summary

| Provider | Uptime SLA | Replacement SLA | Support SLA |
|----------|-----------|-----------------|-------------|
| Bright Data | 99.9% | Instant | 24hr business |
| Gecko | 99.5% | Instant | Email |
| DataImpulse | 99% | 24 hours | Email |
| IPRoyal | 98% | 24-48 hours | Email |
| Proxy-Seller | 99% | 24-48 hours | Ticket |
| Decodo | 99% | < 1 hour | 24/7 chat |

---

*Document managed by Bunche Operations. Update quarterly or when provider terms change.*