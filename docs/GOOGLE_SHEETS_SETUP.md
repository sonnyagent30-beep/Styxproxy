# Bunche — Google Sheets Setup
*Zero-inventory model. No stock held. Everything sourced on-demand.*

---

## Google Cloud Service Account Setup

### 1. Create Project
1. Go to **console.cloud.google.com**
2. New Project → name: `bunche`
3. Create

### 2. Enable Google Sheets API
1. APIs & Services → Library → Search "Google Sheets API"
2. Enable

### 3. Create Service Account
1. APIs & Services → Credentials → Create Credentials → Service Account
2. Name: `bunche-sheets` → Create → Done

### 4. Generate JSON Key
1. Click the service account → Keys → Add Key → JSON → Download
2. Save the JSON securely
3. Copy the `client_email` value (looks like: `bunche-sheets@bunche-project.iam.gserviceaccount.com`)

### 5. Share All Sheets With the Service Account
For each sheet you create:
1. Open the sheet → Share
2. Add the `client_email` → Role: **Editor**

---

## Sheet 1: Pending Orders

**Sheet Name:** `Pending_Orders`

Tracks orders being sourced. IPs are bought via API only after customer pays.

| Column | Header | Format |
|--------|--------|--------|
| A | Order ID | text |
| B | Customer Phone | text |
| C | Plan Code | text |
| D | Country | text |
| E | Quantity | number |
| F | Amount Paid (NGN) | number |
| G | Payment Reference | text |
| H | Provider | text |
| I | Provider Order ID | text |
| J | Proxy Credentials | text |
| K | Status | text |
| L | Created At | datetime |
| M | Fulfilled At | datetime |
| N | Cost (USD) | number |
| O | Profit (NGN) | number |

**Status Values:** `awaiting_payment` | `paid_pending_fulfillment` | `fulfilled` | `failed` | `refunded`

---

## Sheet 2: Customers

**Sheet Name:** `Customers`

| Column | Header | Format |
|--------|--------|--------|
| A | Phone | text (primary key) |
| B | Name | text |
| C | Total Orders | number |
| D | Lifetime Value (NGN) | number |
| E | Last Order At | datetime |
| F | First Order At | datetime |
| G | Most Ordered Plan | text |
| H | Support Notes | text |
| I | Blocked | boolean |
| J | Blocked Reason | text |
| K | Created At | datetime |

---

## Sheet 3: Providers

**Sheet Name:** `Providers`

| Column | Header | Format |
|--------|--------|--------|
| A | Provider Name | text |
| B | API Credential Name | text |
| C | Base URL | text |
| D | Account Status | text |
| E | Balance (USD) | number |
| F | Last Checked | datetime |
| G | Countries Available | text |
| H | Support Email | text |
| I | Notes | text |
| J | Created At | datetime |

**Status Values:** `active` | `low_balance` | `depleted` | `suspended`

---

## Sheet 4: Pricing

**Sheet Name:** `Pricing`

Master price list. All on-demand — no pre-stocked inventory.

| Column | Header | Format |
|--------|--------|--------|
| A | Plan Code | text |
| B | Product Type | text |
| C | Country | text |
| D | Country Code | text |
| E | Retail Price (NGN) | number |
| F | Cost Price (USD) | number |
| G | Provider | text |
| H | Description | text |
| I | Available | boolean |
| J | Last Updated | datetime |

### On-Demand Price List

| Plan Code | Product | Country | Retail (NGN) | Cost (USD) | Provider |
|-----------|---------|---------|-------------|------------|----------|
| ISP-US | ISP | United States | 6,500 | 2.50 | Proxy-Seller |
| ISP-UK | ISP | United Kingdom | 6,500 | 2.50 | Proxy-Seller |
| ISP-DE | ISP | Germany | 6,500 | 2.50 | Proxy-Seller |
| ISP-FR | ISP | France | 6,500 | 2.50 | Proxy-Seller |
| ISP-CA | ISP | Canada | 6,500 | 2.50 | Proxy-Seller |
| ISP-NL | ISP | Netherlands | 6,500 | 2.50 | Proxy-Seller |
| ISP-IT | ISP | Italy | 6,500 | 2.50 | Proxy-Seller |
| ISP-ES | ISP | Spain | 6,500 | 2.50 | Proxy-Seller |
| ISP-PL | ISP | Poland | 6,500 | 2.50 | Proxy-Seller |
| ISP-JP | ISP | Japan | 7,500 | 3.00 | Proxy-Seller |
| ISP-AU | ISP | Australia | 7,500 | 3.00 | Proxy-Seller |
| ISP-BR | ISP | Brazil | 7,500 | 3.00 | Proxy-Seller |
| ISP-IN | ISP | India | 6,500 | 2.50 | Proxy-Seller |
| ISP-SG | ISP | Singapore | 7,500 | 3.00 | Proxy-Seller |
| ISP-ZA | ISP | South Africa | 6,500 | 2.50 | Proxy-Seller |
| ISP-MX | ISP | Mexico | 6,500 | 2.50 | Proxy-Seller |
| ISP-KR | ISP | South Korea | 7,500 | 3.00 | Proxy-Seller |
| RES-5GB | Residential | Global (200+) | 5,000 | 1.75 | OkeyProxy |
| MOB-5GB | Mobile 4G | Global | 20,000 | 10.00 | DataImpulse |
| DC-US | Datacenter | United States | 2,500 | 0.70 | Proxy-Seller |
| DC-UK | Datacenter | United Kingdom | 2,500 | 0.70 | Proxy-Seller |

**Countries marked Available = `TRUE` if provider supports them via API. Proxy-Seller covers 220+ countries on-demand.**
