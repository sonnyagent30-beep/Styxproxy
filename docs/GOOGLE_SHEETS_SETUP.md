# Bunche — Google Sheets Setup — Full Column Templates
*Step-by-step guide to creating all 4 sheets with exact column headers*

---

## Step 0: Set Up Google Cloud Service Account

### 0.1 Create Google Cloud Project
1. Go to **console.cloud.google.com**
2. **Select Project** → **New Project**
3. Name: `bunche`
4. Create

### 0.2 Enable Google Sheets API
1. **APIs & Services** → **Library**
2. Search: **Google Sheets API**
3. Click → **Enable**

### 0.3 Create Service Account
1. **APIs & Services** → **Credentials**
2. **Create Credentials** → **Service Account**
3. Name: `bunche-sheets`
4. Create → Done

### 0.4 Generate Service Account Key
1. Click the service account → **Keys** → **Add Key** → **JSON**
2. Download the JSON — save securely
3. Copy the `client_email` from the JSON

### 0.5 Share All Sheets With the Service Account
For each sheet:
1. Open the sheet → **Share**
2. Add: `bunche-sheets@bunche-project.iam.gserviceaccount.com`
3. Role: **Editor**

---

## Sheet 1: Orders

**Sheet Name:** `Orders`

### Column Headers (Row 1)

| Column | Header | Format |
|--------|--------|--------|
| A | Order ID | text |
| B | Customer Phone | text |
| C | Customer Name | text |
| D | Plan | text |
| E | Quantity | number |
| F | Amount (NGN) | number |
| G | Payment Status | text |
| H | Payment Reference | text |
| I | Flutterwave TX ID | text |
| J | Paid At | datetime |
| K | Proxy Details | text |
| L | Fulfilled At | datetime |
| M | Provider | text |
| N | Provider Order ID | text |
| O | Expires At | datetime |
| P | Renewed From | text |
| Q | Created At | datetime |

**Payment Status Values:** `pending` | `paid` | `fulfilled` | `failed` | `refunded` | `cancelled`

---

## Sheet 2: Inventory

**Sheet Name:** `Inventory`

### Column Headers (Row 1)

| Column | Header | Format |
|--------|--------|--------|
| A | Provider | text |
| B | Proxy Type | text |
| C | Country | text |
| D | Country Code | text |
| E | Plan Code | text |
| F | Quantity Available | number |
| G | Cost Price (USD) | number |
| H | Retail Price (NGN) | number |
| I | Min Order | number |
| J | Max Order | number |
| K | Description | text |
| L | Auto Renew | boolean |
| M | Last Updated | datetime |

### Plan Code Reference

| Plan Code | Proxy Type | Country | Retail (NGN) | Cost (USD) |
|-----------|-----------|---------|-------------|------------|
| ISP-UK | ISP | gb | 18,000 | 7 |
| ISP-US | ISP | us | 20,000 | 8 |
| ISP-NG | ISP | ng | 8,000 | 5 |
| ISP-EU | ISP | de | 18,000 | 7 |
| RES-5GB-NG | Residential | ng | 8,000 | 30/5GB |
| RES-5GB-US | Residential | us | 10,000 | 30/5GB |
| MOB-NG | Mobile | ng | 15,000 | 10 |
| DC-US | Datacenter | us | 3,000 | 2 |

---

## Sheet 3: Customers

**Sheet Name:** `Customers`

### Column Headers (Row 1)

| Column | Header | Format |
|--------|--------|--------|
| A | Phone | text (primary key) |
| B | Name | text |
| C | Total Orders | number |
| D | Lifetime Value (NGN) | number |
| E | Last Order At | datetime |
| F | First Order At | datetime |
| G | Average Order Value | number |
| H | Most Ordered Plan | text |
| I | Support Notes | text |
| J | Blocked | boolean |
| K | Blocked Reason | text |
| L | Created At | datetime |

---

## Sheet 4: Providers

**Sheet Name:** `Providers`

### Column Headers (Row 1)

| Column | Header | Format |
|--------|--------|--------|
| A | Provider Name | text |
| B | API Key Stored In | text |
| C | Base URL | text |
| D | Account Status | text |
| E | Balance (USD) | number |
| F | Last Checked | datetime |
| G | Account Manager | text |
| H | Support Email | text |
| I | Notes | text |
| J | Products Available | text |
| K | Created At | datetime |

**Provider Account Status Values:** `active` | `low_balance` | `depleted` | `suspended` | `testing`
