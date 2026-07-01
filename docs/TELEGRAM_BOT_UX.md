# Bunche Telegram Bot — UX Design Document

> **Project:** Bunche Proxy Reseller Bot  
> **Version:** 1.0  
> **Date:** July 2026  
> **Author:** UX Design for Conversational AI

---

## Table of Contents

1. [Overview](#1-overview)
2. [Command Tree](#2-command-tree)
3. [Message Flows](#3-message-flows)
4. [Keyboard/Inline Markup Layouts](#4-keyboardinline-markup-layouts)
5. [Error States](#5-error-states)
6. [Fallback Behaviour](#6-fallback-behaviour)
7. [Handler Architecture](#7-handler-architecture)
8. [Quick Reference Cards](#8-quick-reference-cards)

---

## 1. Overview

### 1.1 Bot Purpose

**Bunche** is a proxy reseller Telegram bot that enables customers to:
- Browse and purchase proxy services (ISP, DC, Residential, Mobile 4G)
- Check account balance and order history
- Report dead/rotated IPs for replacement
- Link WhatsApp for order notifications
- Get support via help/FAQ

### 1.2 Product Catalog & Pricing

| Product Type | Variants | Price Range (₦) |
|--------------|----------|-----------------|
| **ISP Proxy** | UK, US, DE, FR, CA, JP, AU, BR, SG, KR | ₦5,000 – ₦6,500 |
| **Datacenter (DC)** | IPv4, IPv6, Rotating | ₦2,500 – ₦4,500 |
| **Residential** | IPv4, IPv6 | ₦1,500 – ₦1,950/GB |
| **Mobile 4G** | 4G GB-based | ₦6,000/GB |

### 1.3 User Roles

| Role | Description | Access Level |
|------|-------------|--------------|
| **Customer** | End user purchasing proxies | All customer commands |
| **Admin** | Bunche staff managing orders | All customer commands + admin commands |
| **New User** | First-time visitor | Limited to /start, /help, /trial |

---

## 2. Command Tree

### 2.1 Customer Commands

| Command | Description | Access | Trigger |
|---------|-------------|--------|---------|
| `/start` | Welcome flow, account creation | All | `/start` |
| `/order` | Start new proxy order | Customer | `/order` |
| `/balance` | Check wallet balance | Customer | `/balance` |
| `/status` | Check active orders / IP status | Customer | `/status` |
| `/help` | FAQ and support options | All | `/help` |
| `/report-dead` | Report a dead IP for replacement | Customer | `/report-dead` |
| `/link-whatsapp` | Connect WhatsApp for notifications | Customer | `/link-whatsapp` |
| `/cancel` | Cancel pending order | Customer | `/cancel` |
| `/trial` | Claim free trial proxy | New users | `/trial` |
| `/myorders` | View order history | Customer | `/myorders` |
| `/referral` | Get referral link | Customer | `/referral` |

### 2.2 Admin Commands

| Command | Description | Access |
|---------|-------------|--------|
| `/admin` | Admin dashboard entry | Admin only |
| `/broadcast` | Send message to all users | Admin only |
| `/orders` | View all orders (filterable) | Admin only |
| `/refund` | Process refund for order | Admin only |
| `/add-balance` | Manually add funds to user | Admin only |
| `/ip-manage` | View/replace IPs | Admin only |

### 2.3 Keyword Triggers (Alternative Input)

| Keyword | Maps To | Example |
|---------|---------|---------|
| `buy proxy` | `/order` | "I want to buy proxy" |
| `check balance` | `/balance` | "What's my balance?" |
| `my ip` | `/status` | "Show my IP" |
| `report ip` | `/report-dead` | "IP not working" |
| `whatsapp` | `/link-whatsapp` | "Link my WhatsApp" |
| `help` | `/help` | "I need help" |
| `trial` | `/trial` | "Free trial" |

---

## 3. Message Flows

### 3.1 `/start` — Welcome Flow

**Trigger:** `/start`  
**Access:** All users (new + returning)  
**Endpoint:** `POST /api/users/register` (FastAPI)

#### Step-by-Step Flow

```
User                              Bot
  │                                 │
  ├─ /start ──────────────────────► │
  │                                 │
  │    ┌──────────────────────────────────────────┐
  │    │ 🛡️.proxy                                  │
  │    │                                          │
  │    │ Welcome to Bunche! 👋                    │
  │    │                                          │
  │    │ Your premium proxy reseller.            │
  │    │                                          │
  │    │ ┌─────────────────────────────────────┐ │
  │    │ │ 🛒 Order Proxy    💰 Check Balance │ │
  │    │ │ 📦 My Orders     📋 Help / FAQ    │ │
  │    │ └─────────────────────────────────────┘ │
  │    │                                          │
  │    │ Want a free trial? Tap /trial           │
  │    └──────────────────────────────────────────┘
```

#### New User Detection Logic

1. Bot receives `/start`
2. Query database: `SELECT * FROM users WHERE telegram_id = ?`
3. **If user exists:** Show welcome back + main menu
4. **If new user:**
   - Create record: `INSERT INTO users (telegram_id, username, created_at) VALUES (?, ?, NOW())`
   - Send welcome message
   - Offer free trial prompt

---

### 3.2 `/order` — Order Placement Flow

**Trigger:** `/order`  
**Access:** Customer (registered)  
**Endpoint:** `POST /api/orders/create` (FastAPI)

#### Step-by-Step Flow

```
User                              Bot
  │                                 │
  ├─ /order ──────────────────────► │
  │                                 │
  │    ┌──────────────────────────────────────────┐
  │    │ 🛒 Select Proxy Type                     │
  │    │                                          │
  │    │ [ISP Proxy]  [Datacenter]               │
  │    │ [Residential]  [Mobile 4G]              │
  │    └──────────────────────────────────────────┘
  │                                 │
  ├─ "ISP Proxy" ──────────────────►│
  │                                 │
  │    ┌──────────────────────────────────────────┐
  │    │ 🌐 Select Country                        │
  │    │                                          │
  │    │ [UK] [US] [DE] [FR] [CA]                │
  │    │ [JP] [AU] [BR] [SG] [KR]                │
  │    └──────────────────────────────────────────┘
  │                                 │
  ├─ "US" ─────────────────────────►│
  │                                 │
  │    ┌──────────────────────────────────────────┐
  │    │ 📅 Select Duration                       │
  │    │                                          │
  │    │ [1 Month - ₦5,500]                       │
  │    │ [3 Months - ₦15,000] (Save ₦1,500)      │
  │    │ [6 Months - ₦28,000] (Save ₦5,000)      │
  │    │ [1 Year - ₦50,000]  (Save ₦16,000)      │
  │    └──────────────────────────────────────────┘
  │                                 │
  ├─ "1 Month - ₦5,500" ──────────►│
  │                                 │
  │    ┌──────────────────────────────────────────┐
  │    │ 🛒 Order Summary                          │
  │    │                                          │
  │    │ Type: ISP Proxy                          │
  │    │ Country: United States                   │
  │    │ Duration: 1 Month                        │
  │    │ Price: ₦5,500                            │
  │    │                                          │
  │    │ Your Balance: ₦12,000                    │
  │    │                                          │
  │    │ [✅ Confirm & Pay]  [❌ Cancel]          │
  │    └──────────────────────────────────────────┘
  │                                 │
  ├─ "Confirm & Pay" ──────────────►│
  │                                 │
  │    (Deduct from balance or     │
  │     initiate payment flow)     │
  │                                 │
  │    ┌──────────────────────────────────────────┐
  │    │ ✅ Order Placed Successfully!           │
  │    │                                          │
  │    │ Order ID: #ORD-2026-0701-001            │
  │    │                                          │
  │    │ 🔐 Credentials:                          │
  │    │ IP: 192.168.x.x                         │
  │    │ Port: 8080                               │
  │    │ Username: user_abc123                   │
  │    │ Password: ********                      │
  │    │                                          │
  │    │ [📋 Copy Credentials]                   │
  │    │ [📦 View All Orders]                    │
  │    └──────────────────────────────────────────┘
```

---

### 3.3 `/balance` — Check Wallet Balance

**Trigger:** `/balance`  
**Access:** Customer  
**Endpoint:** `GET /api/users/{telegram_id}/balance`

```
User                              Bot
  │                                 │
  ├─ /balance ────────────────────► │
  │                                 │
  │    ┌──────────────────────────────────────────┐
  │    │ 💰 Your Wallet                           │
  │    │                                          │
  │    │ Available: ₦12,000                       │
  │    │ Pending: ₦0                              │
  │    │                                          │
  │    │ ─────────────────────────────────────   │
  │    │ Total Spent: ₦45,000                     │
  │    │ Orders: 12                               │
  │    │                                          │
  │    │ [💳 Add Funds]  [📜 Transaction History]│
  │    └──────────────────────────────────────────┘
```

---

### 3.4 `/help` — FAQ & Support

**Trigger:** `/help`  
**Access:** All users  
**Endpoint:** `GET /api/faq` (n8n workflow trigger: `faq-handler`)

```
User                              Bot
  │                                 │
  ├─ /help ───────────────────────►│
  │                                 │
  │    ┌──────────────────────────────────────────┐
  │    │ 📋 How can I help you?                   │
  │    │                                          │
  │    │ [❓ How to use proxies]                  │
  │    │ [💳 Payment methods]                    │
  │    │ [🔄 How to replace IP]                  │
  │    │ [📞 Contact support]                     │
  │    │ [🔙 Back to main menu]                  │
  │    └──────────────────────────────────────────┘
  │                                 │
  ├─ "How to use proxies" ────────►│
  │                                 │
  │    ┌──────────────────────────────────────────┐
  │    │ 📖 How to Use Your Proxy                 │
  │    │                                          │
  │    │ 1. Copy credentials from /status         │
  │    │ 2. Configure in your tool:               │
  │    │    - HTTP Proxy: ip:port                 │
  │    │    - Auth: username:password             │
  │    │ 3. Test connectivity                     │
  │    │                                          │
  │    │ [🔙 Back]  [📞 Contact Support]         │
  │    └──────────────────────────────────────────┘
```

---

### 3.5 `/report-dead` — Dead IP Reporting

**Trigger:** `/report-dead`  
**Access:** Customer  
**Endpoint:** `POST /api/ip/report-dead` (FastAPI)

```
User                              Bot
  │                                 │
  ├─ /report-dead ────────────────►│
  │                                 │
  │    ┌──────────────────────────────────────────┐
  │    │ 🔴 Report Dead IP                        │
  │    │                                          │
  │    │ Select the proxy with the dead IP:       │
  │    │                                          │
  │    │ [1] US ISP - expires in 20 days         │
  │    │ [2] UK DC IPv4 - expires in 5 days      │
  │    │ [3] Residential NG - 1.5GB left         │
  │    │                                          │
  │    │ [🔙 Back]                                │
  │    └──────────────────────────────────────────┘
  │                                 │
  ├─ "1" (select US ISP) ────────►│
  │                                 │
  │    ┌──────────────────────────────────────────┐
  │    │ ⚠️ Confirm IP Replacement               │
  │    │                                          │
  │    │ Order: #ORD-2026-0628-003                │
  │    │ Current IP: 45.33.x.x                    │
  │    │                                          │
  │    │ A new IP will be assigned automatically. │
  │    │ This uses 1 of your 3 free replacements.│
  │    │                                          │
  │    │ [✅ Confirm]  [❌ Cancel]                │
  │    └──────────────────────────────────────────┘
  │                                 │
  ├─ "Confirm" ──────────────────►│
  │                                 │
  │    (Trigger n8n workflow:      │
  │     ip-replacement-handler)    │
  │                                 │
  │    ┌──────────────────────────────────────────┐
  │    │ ✅ IP Replacement Initiated             │
  │    │                                          │
  │    │ A new IP is being assigned.              │
  │    │ You will receive credentials in ~2 mins. │
  │    │                                          │
  │    │ ℹ️ Check /status to see new IP            │
  │    │                                          │
  │    │ [📦 My Orders]  [🏠 Main Menu]          │
  │    └──────────────────────────────────────────┘
```

---

### 3.6 `/link-whatsapp` — WhatsApp Linking

**Trigger:** `/link-whatsapp`  
**Access:** Customer  
**Endpoint:** `POST /api/users/link-whatsapp` (FastAPI)

```
User                              Bot
  │                                 │
  ├─ /link-whatsapp ──────────────►│
  │                                 │
  │    ┌──────────────────────────────────────────┐
  │    │ 📱 Link WhatsApp                         │
  │    │                                          │
  │    │ Get order notifications on WhatsApp!    │
  │    │                                          │
  │    │ Enter your WhatsApp number:              │
  │    │ (e.g., 2348012345678)                    │
  │    │                                          │
  │    │ [❌ Cancel]                               │
  │    └──────────────────────────────────────────┘
  │                                 │
  ├─ "2348012345678" ────────────►│
  │                                 │
  │    (Validate format: 10-15 digits)
  │                                 │
  │    ┌──────────────────────────────────────────┐
  │    │ ✅ WhatsApp Linked!                      │
  │    │                                          │
  │    │ Number: +234 801 234 5678               │
  │    │                                          │
  │    │ You will now receive:                    │
  │    │   • Order confirmations                 │
  │    │   • IP replacement notifications         │
  │    │   • Expiry reminders                     │
  │    │                                          │
  │    │ [🔙 Back to Menu]                        │
  │    └──────────────────────────────────────────┘
```

---

### 3.7 `/status` — Order & IP Status

**Trigger:** `/status`  
**Access:** Customer  
**Endpoint:** `GET /api/orders/active` (FastAPI)

```
User                              Bot
  │                                 │
  ├─ /status ──────────────────────► │
  │                                 │
  │    ┌──────────────────────────────────────────┐
  │    │ 📦 Your Active Orders                   │
  │    │                                          │
  │    │ ─────────────────────────────────────    │
  │    │                                          │
  │    │ #1 🇺🇸 US ISP Proxy                     │
  │    │    IP: 45.33.22.11:8080                 │
  │    │    Expires: 20 days                     │
  │    │    [🔄 Refresh] [⚠️ Report Dead]       │
  │    │                                          │
  │    │ ─────────────────────────────────────    │
  │    │                                          │
  │    │ #2 🇬🇧 UK DC IPv4                       │
  │    │    IP: 185.x.x.x:3128                   │
  │    │    Expires: 5 days                      │
  │    │    [🔄 Refresh] [⚠️ Report Dead]       │
  │    │                                          │
  │    │ [📜 Order History]  [🏠 Main Menu]      │
  │    └──────────────────────────────────────────┘
```

---

### 3.8 `/cancel` — Cancel Pending Order

**Trigger:** `/cancel`  
**Access:** Customer  
**Endpoint:** `POST /api/orders/{order_id}/cancel`

```
User                              Bot
  │                                 │
  ├─ /cancel ─────────────────────►│
  │                                 │
  │    ┌──────────────────────────────────────────┐
  │    │ ❌ Cancel Order                          │
  │    │                                          │
  │    │ Select order to cancel:                  │
  │    │                                          │
  │    │ [1] US ISP - Pending payment            │
  │    │ [2] UK DC - Processing                  │
  │    │                                          │
  │    │ [🔙 Back]                                │
  │    └──────────────────────────────────────────┘
  │                                 │
  ├─ "1" ─────────────────────────►│
  │                                 │
  │    ┌──────────────────────────────────────────┐
  │    │ ⚠️ Confirm Cancellation                 │
  │    │                                          │
  │    │ Order: #ORD-2026-0701-005               │
  │    │ Amount: ₦5,500                          │
  │    │                                          │
  │    │ This will be refunded to your wallet.   │
  │    │                                          │
  │    │ [✅ Yes, Cancel]  [❌ No, Keep It]      │
  │    └──────────────────────────────────────────┘
  │                                 │
  ├─ "Yes, Cancel" ───────────────►│
  │                                 │
  │    ┌──────────────────────────────────────────┐
  │    │ ✅ Order Cancelled                        │
  │    │                                          │
  │    │ ₦5,500 refunded to your wallet.         │
  │    │                                          │
  │    │ [💰 Check Balance]  [🏠 Main Menu]       │
  │    └──────────────────────────────────────────┘
```

---

### 3.9 `/trial` — Free Trial Flow

**Trigger:** `/trial`  
**Access:** New users (one trial per user)  
**Endpoint:** `POST /api/orders/trial` (FastAPI)

```
User                              Bot
  │                                 │
  ├─ /trial ───────────────────────►│
  │                                 │
  │    (Check: has_user_used_trial?)│
  │                                 │
  │    ┌──────────────────────────────────────────┐
  │    │ 🎁 Free Trial - 100MB                   │
  │    │                                          │
  │    │ Try before you buy!                      │
  │    │                                          │
  │    │ Includes:                                │
  │    │   ✓ 100MB Residential proxy             │
  │    │   ✓ Valid for 24 hours                   │
  │    │   ✓ Instant delivery                     │
  │    │                                          │
  │    │ [✅ Claim My Trial]  [❌ Maybe Later]    │
  │    └──────────────────────────────────────────┘
  │                                 │
  ├─ "Claim My Trial" ────────────►│
  │                                 │
  │    (Create trial order)        │
  │                                 │
  │    ┌──────────────────────────────────────────┐
  │    │ 🎉 Trial Activated!                     │
  │    │                                          │
  │    │ 🔐 Credentials:                          │
  │    │ IP: 103.x.x.x                           │
  │    │ Port: 8080                               │
  │    │ Username: trial_abc123                  │
  │    │ Password: ********                      │
  │    │                                          │
  │    │ ⏱️ Valid for 24 hours                   │
  │    │ 📊 100MB data limit                     │
  │    │                                          │
  │    │ [🛒 Upgrade to Full]  [📦 My Orders]   │
  │    └──────────────────────────────────────────┘
```

---

## 4. Keyboard/Inline Markup Layouts

### 4.1 Main Menu Keyboard

```python
main_menu_keyboard = InlineKeyboardMarkup([
    [
        InlineKeyboardButton("🛒 Order Proxy", callback_data="cmd:order"),
        InlineKeyboardButton("💰 Check Balance", callback_data="cmd:balance")
    ],
    [
        InlineKeyboardButton("📦 My Orders", callback_data="cmd:myorders"),
        InlineKeyboardButton("📋 Help / FAQ", callback_data="cmd:help")
    ],
    [
        InlineKeyboardButton("🎁 Free Trial", callback_data="cmd:trial"),
        InlineKeyboardButton("🔗 Link WhatsApp", callback_data="cmd:link-whatsapp")
    ]
])
```

### 4.2 Product Selection Keyboard

```python
product_keyboard = InlineKeyboardMarkup([
    [
        InlineKeyboardButton("🌐 ISP Proxy", callback_data="product:isp"),
        InlineKeyboardButton("🏢 Datacenter", callback_data="product:dc")
    ],
    [
        InlineKeyboardButton("🏠 Residential", callback_data="product:residential"),
        InlineKeyboardButton("📱 Mobile 4G", callback_data="product:mobile")
    ]
])
```

### 4.3 ISP Country Keyboard

```python
isp_country_keyboard = InlineKeyboardMarkup([
    [
        InlineKeyboardButton("🇬🇧 UK", callback_data="country:uk"),
        InlineKeyboardButton("🇺🇸 US", callback_data="country:us"),
        InlineKeyboardButton("🇩🇪 DE", callback_data="country:de"),
        InlineKeyboardButton("🇫🇷 FR", callback_data="country:fr"),
        InlineKeyboardButton("🇨🇦 CA", callback_data="country:ca")
    ],
    [
        InlineKeyboardButton("🇯🇵 JP", callback_data="country:jp"),
        InlineKeyboardButton("🇦🇺 AU", callback_data="country:au"),
        InlineKeyboardButton("🇧🇷 BR", callback_data="country:br"),
        InlineKeyboardButton("🇸🇬 SG", callback_data="country:sg"),
        InlineKeyboardButton("🇰🇷 KR", callback_data="country:kr")
    ]
])
```

### 4.4 Duration Selection Keyboard

```python
duration_keyboard = InlineKeyboardMarkup([
    [
        InlineKeyboardButton("1 Month - ₦5,500", callback_data="duration:1"),
        InlineKeyboardButton("3 Months - ₦15,000", callback_data="duration:3")
    ],
    [
        InlineKeyboardButton("6 Months - ₦28,000", callback_data="duration:6"),
        InlineKeyboardButton("1 Year - ₦50,000", callback_data="duration:12")
    ]
])
```

### 4.5 Confirmation Keyboard

```python
confirm_keyboard = InlineKeyboardMarkup([
    [
        InlineKeyboardButton("✅ Confirm & Pay", callback_data="action:confirm"),
        InlineKeyboardButton("❌ Cancel", callback_data="action:cancel")
    ]
])
```

### 4.6 Order Status Keyboard (Per Order)

```python
order_action_keyboard = InlineKeyboardMarkup([
    [
        InlineKeyboardButton("🔄 Refresh IP", callback_data="order:refresh:123"),
        InlineKeyboardButton("⚠️ Report Dead", callback_data="order:report:123")
    ]
])
```

### 4.7 FAQ Keyboard

```python
keyboard_faq = InlineKeyboardMarkup([
    [
        InlineKeyboardButton("❓ How to use proxies", callback_data="faq:001"),
        InlineKeyboardButton("💳 Payment methods", callback_data="faq:002")
    ],
    [
        InlineKeyboardButton("🔄 How to replace IP", callback_data="faq:003"),
        InlineKeyboardButton("📞 Contact support", callback_data="faq:support")
    ],
    [
        InlineKeyboardButton("🔙 Back to Menu", callback_data="cmd:back_main")
    ]
])
```

---

## 5. Error States

### 5.1 Invalid Input Errors

| Scenario | Bot Response | Action |
|----------|--------------|--------|
| Non-numeric phone number | "Please enter a valid phone number (10-15 digits, no + or spaces)." | Re-prompt input |
| Invalid country selection | "Invalid country. Please select from the options below." | Re-show country keyboard |
| Invalid order selection | "I couldn't find that order. Please select from your active orders." | Re-show order list |
| Invalid duration selection | "Please select a valid duration option." | Re-show duration keyboard |

### 5.2 Order Failure Errors

| Scenario | Bot Response | Action |
|----------|--------------|--------|
| Insufficient balance | "Insufficient balance. You need ₦5,500 but have ₦3,000. Add funds to continue." | Show "Add Funds" button |
| Payment timeout | "Payment pending. Please check your bank transfer and try again, or use /balance to verify." | Show pending status |
| Product out of stock | "Sorry, US ISP proxies are temporarily out of stock. Try another country or check back later." | Suggest alternatives |
| Order creation failed | "Something went wrong creating your order. Our team has been notified. Try again in 5 minutes." | Log error, retry prompt |

### 5.3 Payment Pending State

```
User                              Bot
  │                                 │
  ├─ (Payment initiated) ─────────►│
  │                                 │
  │    ┌──────────────────────────────────────────┐
  │    │ ⏳ Payment Pending                       │
  │    │                                          │
  │    │ Order: #ORD-2026-0701-008               │
  │    │ Amount: ₦5,500                          │
  │    │                                          │
  │    │ Please transfer ₦5,500 to:              │
  │    │ Bank: First Bank                        │
  │    │ Account: 3124567890                     │
  │    │                                          │
  │    │ Reference: BUN-2026-0701-008            │
  │    │                                          │
  │    │ ℹ️ Send proof to @bunche_admin          │
  │    │                                          │
  │    │ [🔄 Check Payment]  [❌ Cancel Order]   │
  │    └──────────────────────────────────────────┘
```

---

## 6. Fallback Behaviour

### 6.1 NLP Fallback Strategy

When bot doesn't understand user input:

```
User: "I want to scrape some websites"
        │
        ▼
┌─────────────────────────────────────────────┐
│           FALLBACK HANDLER                  │
├─────────────────────────────────────────────┤
│ 1. Check keyword match                     │
│    → "buy proxy" → /order                   │
│    → "my balance" → /balance               │
│                                             │
│ 2. If no keyword match →                   │
│    Send clarification message               │
│                                             │
│ 3. Log unknown input for NLP training      │
└─────────────────────────────────────────────┘
        │
        ▼
Bot:
    ┌──────────────────────────────────────────┐
    │ 🤔 I didn't quite understand that.        │
    │                                          │
    │ Here are things I can help you with:    │
    │                                          │
    │ • /order - Buy a proxy                  │
    │ • /balance - Check your balance          │
    │ • /status - View your proxies            │
    │ • /help - Get help and FAQ               │
    │                                          │
    │ Or type a keyword like "buy", "proxy",  │
    │ "balance", "help"                        │
    │                                          │
    │ [🛒 Order] [💰 Balance] [📋 Help]        │
    └──────────────────────────────────────────┘
```

### 6.2 Keyword Matching Rules

| Input Pattern | Maps To | Example |
|---------------|---------|---------|
| `buy*proxy` | `/order` | "buy proxy", "I want to buy a proxy" |
| `check*balance` | `/balance` | "check balance", "my balance" |
| `my*order*status` | `/status` | "order status", "show my IP" |
| `report*dead` | `/report-dead` | "IP not working", "dead IP" |
| `link*whatsapp` | `/link-whatsapp` | "connect whatsapp" |
| `help*me` | `/help` | "help", "need help" |
| `trial*proxy` | `/trial` | "free trial", "try before buy" |

### 6.3 Unrecognized Callback Data

If user clicks invalid inline button:

```
Bot: "Something went wrong. Returning to main menu."
     [Main Menu Keyboard]
```

---

## 7. Handler Architecture

### 7.1 Command-to-Endpoint Mapping

| Command | FastAPI Endpoint | n8n Workflow Trigger |
|---------|------------------|---------------------|
| `/start` | `POST /api/users/register` | — |
| `/order` | `POST /api/orders/create` | `order-creation-handler` |
| `/balance` | `GET /api/users/{telegram_id}/balance` | — |
| `/status` | `GET /api/orders/active` | `order-status-handler` |
| `/help` | `GET /api/faq` | `faq-handler` |
| `/report-dead` | `POST /api/ip/report-dead` | `ip-replacement-handler` |
| `/link-whatsapp` | `POST /api/users/link-whatsapp` | `whatsapp-link-handler` |
| `/cancel` | `POST /api/orders/{order_id}/cancel` | `order-cancel-handler` |
| `/trial` | `POST /api/orders/trial` | `trial-activation-handler` |
| `/myorders` | `GET /api/orders/history` | — |
| `/referral` | `GET /api/users/referral` | — |

### 7.2 Admin Command Mapping

| Admin Command | FastAPI Endpoint | n8n Workflow |
|---------------|------------------|---------------|
| `/admin` | `GET /api/admin/dashboard` | — |
| `/broadcast` | `POST /api/admin/broadcast` | `broadcast-handler` |
| `/orders` | `GET /api/admin/orders` | — |
| `/refund` | `POST /api/admin/refund` | `refund-handler` |
| `/add-balance` | `POST /api/admin/add-balance` | — |
| `/ip-manage` | `GET /api/admin/ip-list` | — |

### 7.3 n8n Workflow Triggers

| Workflow Name | Trigger Type | Purpose |
|--------------|--------------|---------|
| `order-creation-handler` | Webhook | Validate order, deduct balance, provision proxy |
| `order-status-handler` | Webhook | Fetch current IP status from provider |
| `ip-replacement-handler` | Webhook | Queue IP replacement, notify user |
| `trial-activation-handler` | Webhook | Create trial credentials, track usage |
| `whatsapp-link-handler` | Webhook | Validate and store WhatsApp number |
| `broadcast-handler` | Webhook | Send bulk messages to user segment |
| `refund-handler` | Webhook | Process refund to wallet |
| `faq-handler` | Webhook | Fetch FAQ from knowledge base |

---

## 8. Quick Reference Cards

### 8.1 New User Welcome Card

```
┌─────────────────────────────────────────┐
│  🛡️.proxy — BUNCHE                        │
│                                         │
│  Welcome! 👋                            │
│                                         │
│  Premium proxies for:                   │
│  • Web scraping                        │
│  • Ad verification                     │
│  • Sneaker copping                     │
│  • Social media management             │
│                                         │
│  Quick Start:                          │
│  /trial  → Free 100MB trial            │
│  /order  → Buy your first proxy        │
│  /help   → Learn how it works          │
└─────────────────────────────────────────┘
```

### 8.2 Order Status Notification Card

```
┌─────────────────────────────────────────┐
│  📦 Order Update                        │
│                                         │
│  #ORD-2026-0701-001                    │
│                                         │
│  🇺🇸 US ISP Proxy                      │
│  IP: 45.33.22.11:8080                  │
│  Username: user_abc123                  │
│                                         │
│  Expires: 20 days                      │
│  Status: ✅ Active                     │
│                                         │
│  [🔄 Refresh]  [⚠️ Report Dead]         │
└─────────────────────────────────────────┘
```

### 8.3 Payment Received Notification Card

```
┌─────────────────────────────────────────┐
│  ✅ Payment Confirmed!                  │
│                                         │
│  Order: #ORD-2026-0701-005             │
│  Amount: ₦5,500                        │
│                                         │
│  Your proxy is ready:                  │
│                                         │
│  IP: 103.45.67.89                      │
│  Port: 8080                            │
│  User: bunche_user_xyz                 │
│  Pass: ••••••••                       │
│                                         │
│  [📋 Copy Credentials]                  │
│  [📦 View in /status]                   │
└─────────────────────────────────────────┘
```

### 8.4 Dead IP Replacement Notification Card

```
┌─────────────────────────────────────────┐
│  🔄 IP Replaced                         │
│                                         │
│  Your dead IP has been replaced!       │
│                                         │
│  Old IP: 45.33.x.x (dead)              │
│  New IP: 78.91.123.x                   │
│                                         │
│  Port: 8080                             │
│  Username: (unchanged)                  │
│                                         │
│  Check /status for full credentials.   │
│                                         │
│  Remaining replacements: 2/3           │
└─────────────────────────────────────────┘
```

---

## Appendix A: Database Schema (Reference)

### Users Table

```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    telegram_id BIGINT UNIQUE NOT NULL,
    username VARCHAR(255),
    whatsapp VARCHAR(20),
    balance DECIMAL(10,2) DEFAULT 0,
    used_trial BOOLEAN DEFAULT FALSE,
    referral_code VARCHAR(20) UNIQUE,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### Orders Table

```sql
CREATE TABLE orders (
    id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(id),
    order_id VARCHAR(50) UNIQUE NOT NULL,
    product_type VARCHAR(20) NOT NULL,
    country VARCHAR(10),
    duration_months INT,
    ip_address INET,
    port INT,
    username VARCHAR(100),
    password_hash VARCHAR(255),
    status VARCHAR(20) DEFAULT 'pending',
    amount DECIMAL(10,2),
    flutterwave_ref VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW(),
    fulfilled_at TIMESTAMP
);
```
