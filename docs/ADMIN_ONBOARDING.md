# Admin Onboarding Guide

**Last updated:** 2026-08-03  
**Audience:** Dannion and any future admin users

---

## Getting Access

Access requires an invite. If you haven't received one, contact the superadmin.

1. Go to `admin.styxproxy.com`
2. Click **Accept Invite**
3. Enter your email + create a password
4. Set up **TOTP** (authenticator app) — required for all admin logins
5. Done — you're in

---

## How Login Works

Every admin login requires:
- Email + password
- TOTP code from your authenticator app (6 digits, changes every 30s)

If you lose your TOTP device, contact the superadmin to reset it.

---

## Roles & What Each Can Do

| Role | What it can do |
|---|---|
| **Superadmin** | Everything + invite other admins + view audit logs |
| **Admin** | View orders, customers, credentials; issue refunds; manage trial flags |
| **Support** | View orders + customer conversations; escalate to admin |
| **Viewer** | Read-only dashboard — no write actions |

---

## Key Admin Pages

### `/admin`

Main dashboard — overview of today's orders, revenue, trial conversions.

---

### `/admin/orders`

All orders. Filter by:
- Status: `pending`, `paid`, `fulfilled`, `refunded`, `failed_unfulfilled`
- Date range
- Customer phone

**To look up a specific order:** Search by `tx_ref` (Flutterwave transaction ID) or `order_id` (ORD-XXXXXX).

**To refund an order:**
1. Click the order
2. Scroll to bottom
3. Click **Issue Refund** → confirm
4. Reason is logged automatically

---

### `/admin/customers`

All customers. Shows phone, name, lifetime value, trial status, order count.

**To flag a customer:**
1. Open the customer record
2. Toggle **Blocked** → add a reason
3. Blocked customers can't create new orders

---

### `/admin/proxies`

Proxy inventory — which IPs are live, which are dead, bandwidth used.

**To test a proxy manually:**
1. Go to the proxy record
2. Click **Run Test**
3. See speed grade, abuse score, fraud score

---

### `/admin/trials`

Trial queue — shows all trial requests today, their status.

**To approve a trial manually:**
1. Find the pending trial
2. Click **Approve** or **Reject**

---

### `/admin/audit`

Everything every admin did — refunds, blocks, credential resets. Timestamp + admin email + action.

Use this to figure out what happened if something looks wrong.

---

## Common Tasks

### Issue a manual refund

1. Go to `/admin/orders`
2. Find the order (search by tx_ref)
3. Click into the order
4. **Issue Refund** → confirm

Refund takes 5-7 business days to appear on customer's account.

---

### Reset a customer's TOTP

1. Go to `/admin/customers`
2. Find the customer
3. Click **Reset TOTP**
4. Customer receives a new invite email

---

### Block a customer

1. Go to `/admin/customers`
2. Find the customer
3. Toggle **Blocked** → enter reason
4. Customer's next order attempt will fail

---

### View Charon (support bot) logs

Go to `/admin/charon` — see conversations, escalation queue, LLM cost, error rates.

---

## Security Rules

- Never share your admin password or TOTP codes
- Every action is logged — don't do anything you can't explain
- If you suspect unauthorized access: change your password immediately and contact the superadmin
- Refunds over ₦50,000 require superadmin approval

---

## Emergency: The Site is Down

1. Check **Status page** (TODO: `status.styxproxy.com`)
2. SSH to the VPS: `ssh root@162.35.184.69`
3. Check API: `systemctl status styxproxy-api`
4. Check DB: `sudo -u postgres psql -d styxproxy -c "SELECT 1"`
5. Check logs: `journalctl -u styxproxy-api --since "30 minutes ago" | tail -50`

If you can't fix it quickly, enable maintenance mode:
```
POST /api/v1/maintenance-mode
{"mode": "soft-block", "message": "Site under maintenance. Back shortly."}
```

Full incident response → see `docs/INCIDENT_RESPONSE.md`

---

## Contacts

- **Dannion (superadmin):** `oyebiyiayomide30@gmail.com`
- **Sonny (automated monitoring):** monitors 24/7 via Hermes
