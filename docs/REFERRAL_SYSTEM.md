# Styxproxy — Referral System

**Last Updated:** 2026-06-26
**SHA:** referral-v1

---

## How It Works

| Element | Detail |
|---------|--------|
| **Referral code** | Customer's own name/nickname (unique) |
| **Reward** | Referrer earns **5%** of referred person's first order value |
| **Credit form** | Discount on referrer's next IP purchase |
| **Who can refer** | Any customer with a name saved in Styxproxy |
| **Applies to** | First-time referral purchases only |
| **Credit expiry** | Never — stays until used |
| **Self-referral** | Blocked — can't use your own name |

---

## The Flow

### Step 1 — Customer Gets Their Name

During first purchase, after payment:

```
Styxproxy: "✅ Payment confirmed!
What should we call you? 👇"

Customer: "Chidi"
  ↓
[Check: Is 'Chidi' already taken?]
  ↓
[IF taken]
  → "Sorry, 'Chidi' is already taken.
     Try: Chidi_22, ChidiProxy, RealChidi"
  ↓
[IF available]
  → Save name = 'Chidi'
  → "Great! Your name is Chidi.
     Your referral name is: Chidi
     Share it with friends! 🎁"
```

**Rules for names:**
- Letters, numbers, underscores
- 3–20 characters
- Case-insensitive uniqueness (Chidi = CHIDI = chidi)
- System recommends alternatives if taken

---

### Step 2 — Friend Places Order Using Referrer's Name

```
Customer: "Order ISP UK 1"
  ↓
Styxproxy: "Got it! UK's finest ISP proxy.

Price: ₦6,500

Were you referred by someone?
Enter their name or say 'No'. 👇"
  ↓
Customer: "Chidi"
  ↓
[Check: Does 'Chidi' exist in customers table?]
  ↓
[IF yes AND NOT same phone]
  → "✅ Referred by Chidi!
     They'll earn ₦325 credit when
     you complete your order."
  → Store: referred_by = Chidi's phone
  → Store: referral_code_used = 'Chidi'
  ↓
[IF no / same phone / already referred]
  → "No referral applied."
```

**Self-referral blocked:**
```
Customer: "Chidi" (their own name)
  ↓
Styxproxy: "That's your own name!
No self-referrals. Let's continue with your order."
```

---

### Step 3 — Referred Order Completes

```
🎉 ORDER COMPLETE — Chidi!

Your ISP UK proxy is ready:
IP: [X.X.X.X]
Port: [XXXX]
Username: [X]
Password: [X]
Expires: [DATE]

━━━━━━━━━━━━━━━━━━
💡 Referred by [NAME].
   They just earned credit! 🎁
━━━━━━━━━━━━━━━━━━
```

---

### Step 4 — Referrer Earns Credit

Notified immediately after referred purchase:

```
🎉 You earned referral credit!

[Name] just completed their first order.

They bought: ISP UK
Order value: ₦6,500

Your credit earned: ₦325

Your total referral credit: ₦325

Keep sharing your name — every first
purchase = more credit for you! 🔗
```

---

### Step 5 — Referrer Uses Credit on Next Purchase

```
Customer (Chidi): "Order ISP UK 1"
  ↓
Styxproxy checks: referral_credit_ngn > 0?
  ↓
[IF credit = ₦325]
  → "📢 You have ₦325 referral credit!

Your order:
🇬🇧 ISP UK × 1

Original: ₦6,500
Referral credit: -₦325
━━━━━━━━━━━━━━━━━━
To pay: ₦6,175

Proceed? Reply 'Yes' 👇"
  ↓
[Customer: "Yes"]
  → Payment link for ₦6,175
  → After payment:
     referral_credit_ngn = 0
     referral_credit_used_ngn += 325
```

**Credit is used fully in one purchase or across multiple:**
- ₦100 credit + ₦6,500 order → ₦100 off, ₦0 credit remaining
- ₦2,000 credit + ₦6,500 order → ₦2,000 off, ₦0 credit remaining
- ₦500 credit + ₦2,500 order → ₦500 off, ₦0 credit remaining
- **Credit never expires until used**

---

## Referral Share Message

Customer can ask "How do I refer?" or "Share my name":

```
🔗 YOUR REFERRAL NAME: [NAME]

Share it with friends.

When someone uses your name
when ordering, you earn
5% of their first order!

Example:
Friend buys ISP UK (₦6,500)
→ You earn ₦325 credit
Friend buys Mobile (₦20,000)
→ You earn ₦1,000 credit

Your current credit: ₦[X]

Share your name: [NAME]
```

---

## Credit Calculation

| Referred Order | Credit to Referrer |
|----------------|-------------------|
| ISP UK ₦6,500 | ₦325 |
| Premium ISP ₦7,500 | ₦375 |
| DC ₦2,500 | ₦125 |
| Residential 5GB ₦5,000 | ₦250 |
| Mobile 5GB ₦20,000 | ₦1,000 |

---

## Name Uniqueness Logic

```javascript
function checkName(name) {
  const normalized = name.toLowerCase().trim();
  
  // Check if taken
  const existing = db.query(
    "SELECT phone FROM customers WHERE LOWER(name) = $1",
    [normalized]
  );
  
  if (existing.length === 0) {
    return { available: true, name: name };
  }
  
  // If same phone, it's their own name — allowed
  if (existing[0].phone === currentPhone) {
    return { available: true, name: name };
  }
  
  // Suggest alternatives
  const suggestions = [
    normalized + '_' + Math.floor(Math.random() * 99),
    normalized + Math.floor(Math.random() * 999),
    'Real' + name,
    name + Math.floor(Math.random() * 99)
  ].filter(s => s.length <= 20);
  
  return { 
    available: false, 
    suggestions: suggestions 
  };
}
```

---

## Database Additions

```sql
-- customers table
ALTER TABLE customers
ADD COLUMN name VARCHAR(30) UNIQUE,          -- referral name
ADD COLUMN referral_credit_ngn DECIMAL(12,2) DEFAULT 0,
ADD COLUMN referred_by VARCHAR(20);          -- phone of person who referred them
-- Note: customers.phone is already the primary key

-- orders table
ALTER TABLE orders
ADD COLUMN referred_by_phone VARCHAR(20),   -- phone of referrer
ADD COLUMN referral_name_used VARCHAR(30),  -- name they typed
ADD COLUMN referral_credit_earned_ngn DECIMAL(12,2) DEFAULT 0,
ADD COLUMN referral_credit_used_ngn DECIMAL(12,2) DEFAULT 0;
```

---

## Rules Summary

| Rule | Detail |
|------|--------|
| **Name = referral code** | Customer's saved name is their referral identifier |
| **Who can refer** | Any customer with a name saved |
| **Who can be referred** | New customer placing their first order |
| **Referred gets no benefit** | Only the referrer earns credit |
| **Credit is personal** | Can't transfer to another phone |
| **No cap** | Unlimited referral credit accumulation |
| **Credit never expires** | Stays until used on a purchase |
| **Self-referral blocked** | Can't use your own name |
| **One referral per customer** | First referral purchase only counts |
| **Credit applied at checkout** | Can't withdraw as cash |

---

## Admin Commands (New)

| Command | Risk | Description |
|---------|------|-------------|
| Referral stats | Low | Show referral totals, top referrers, total credit paid out |

```
Admin: "Referral stats"
  ↓
Styxproxy: "📊 Referral Stats

Top Referrers:
1. Chidi — 12 referrals — ₦15,000 credit earned
2. Ada — 8 referrals — ₦9,500 credit earned
3. Tunde — 5 referrals — ₦6,250 credit earned

Total referral purchases: 47
Total credit paid out: ₦58,250
Referral conversion rate: 23%

Top referral: ISP UK (most referred product)"
```

---

## Workflow Additions

### Workflow 15: Referral Credit Processor

**Trigger:** After order payment confirmed — Workflow 2 runs this as a sub-step

```
[Order fulfilled — payment confirmed]
        ↓
[Check: Is this a referred order? (referred_by_phone exists?)]
        ↓
[IF yes AND customer.total_orders == 1 (first order)]
  → Calculate: referral_credit = order_amount × 0.05
  → Add credit to referrer's account:
    UPDATE customers 
    SET referral_credit_ngn = referral_credit_ngn + $credit
    WHERE phone = referred_by_phone
  → UPDATE orders SET referral_credit_earned_ngn = $credit
  → Send WhatsApp to referrer: "🎉 You earned referral credit!"
  → Log event
  ↓
[IF no referral]
  → Continue normally
```

### Name Check Sub-Step (in Order Flow — Workflow 1)

```
[New customer — first message after payment confirmed]
        ↓
Styxproxy: "✅ Payment confirmed!
What should we call you? 👇"
        ↓
[Customer enters name]
        ↓
[Check uniqueness]
  → Available → Save → "Great! Your name is [Name]. Share it to earn credit!"
  → Taken → Show suggestions
```
