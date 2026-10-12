# Styxproxy — Admin Web Dashboard Spec

**Last Updated:** 2026-07-01
**Purpose:** Define the admin web dashboard — roles, permissions, pages, and behavior.

---

## Overview

All admin operations move from Telegram to a dedicated web dashboard at `admin.styxproxy.com`.

**Telegram is no longer used for admin commands.** Admin staff log in via the web dashboard only.

**Rationale:**
- Telegram bot token exposed in n8n = security risk
- No granular permissions in Telegram commands
- Hard to audit who did what and when
- Full UI with data tables, charts, search > chat commands
- Every action logged to `admin_commands_log`

---

## Architecture

```
Admin (browser)
     │
     │ HTTPS
     ▼
admin.styxproxy.com
     │
     │ Calls
     ▼
Backend API: GET /admin/*, POST /admin/*
     │
     ├── PostgreSQL (styxproxy database)
     │     ├── instant_orders
     │     ├── platform_accounts
     │     ├── styxproxy_credentials
     │     ├── admin_auth
     │     └── admin_commands_log
     │
     ├── Flutterwave (read-only checks)
     └── Proxy providers (for status lookups)
```

**No admin data visible in the customer-facing website.**

---

## Authentication

### Login Flow

1. Admin visits `admin.styxproxy.com`
2. Enters email + password
3. Enters 6-digit TOTP code from authenticator app
4. Receives JWT access token (15-minute expiry)
5. Receives refresh token in httpOnly cookie (7-day expiry)
6. Dashboard loads

### Session Management

- **Access token:** JWT, 15-minute expiry, stored in memory (not localStorage)
- **Refresh token:** httpOnly cookie, 7-day expiry, used to get new access token
- **Logout:** Access token invalidated, refresh token deleted from cookie
- **Password reset:** Email link with 15-minute expiry token (sent to registered email)

### Failed Login Protection

- 5 failed login attempts → 15-minute lockout
- Lockout logged in `admin_commands_log`
- SuperAdmin can unlock manually

---

## Admin Roles

### SuperAdmin

Full system access. Can do everything.

| Permission | Allowed |
|---|---|
| View all orders (all channels) | ✅ |
| View all customers | ✅ |
| Issue refunds | ✅ |
| Process ban claims | ✅ |
| View all credentials | ✅ |
| Manually issue credentials | ✅ |
| Manually revoke credentials | ✅ |
| Create new Admin | ✅ |
| Delete Admin | ✅ |
| Deactivate Admin | ✅ |
| View admin audit log | ✅ |
| View provider cost reports | ✅ |
| View system settings | ✅ |
| Change system settings | ✅ |
| View all error logs | ✅ |

### Admin

Day-to-day operations. Cannot create/delete other admins or change system settings.

| Permission | Allowed |
|---|---|
| View all orders (all channels) | ✅ |
| View all customers | ✅ |
| Issue refunds | ✅ |
| Process ban claims | ✅ |
| View own issued credentials | ✅ |
| Manually issue credentials | ✅ |
| Manually revoke credentials | ✅ |
| Create new Admin | ❌ |
| Delete Admin | ❌ |
| Deactivate Admin | ❌ |
| View admin audit log | ❌ (own actions only) |
| View provider cost reports | ❌ |
| View system settings | ✅ (read only) |
| Change system settings | ❌ |
| View all error logs | ❌ |

---

## Dashboard Pages

### 1. Dashboard Home (`/`)

Overview metrics.

```
┌─────────────────────────────────────────────────────┐
│  Styxproxy Admin                              [Admin ▼]│
├─────────────────────────────────────────────────────┤
│                                                     │
│  Today's Orders        Today's Revenue              │
│  47                    ₦310,500                    │
│  ▲ 12% vs yesterday   ▲ 8% vs yesterday           │
│                                                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────┐ │
│  │ Pending  │  │ Active   │  │ Expired  │  │Ban │ │
│  │ Orders   │  │ Proxies  │  │ Today    │  │Claims│ │
│  │  3       │  │  1,249   │  │  12      │  │ 2  │ │
│  └──────────┘  └──────────┘  └──────────┘  └────┘ │
│                                                     │
│  Recent Orders (last 24 hours)                      │
│  ┌──────────────────────────────────────────────┐  │
│  │ TXF-abc123  │ ISP UK  │ ₦6,500 │ ✅ Active │  │
│  │ TXF-def456  │ DC      │ ₦2,500 │ ⏳ Pending │  │
│  │ TXF-ghi789  │ MOB 5GB │ ₦20,000│ ⚠️ Ban    │  │
│  └──────────────────────────────────────────────┘  │
│                                                     │
│  [View All Orders →]                               │
└─────────────────────────────────────────────────────┘
```

### 2. Orders (`/orders`)

Full order list with filters.

**Filters:**
- Channel: All / Instant / Telegram / WhatsApp
- Status: All / Pending / Active / Expired / Refunded / Banned
- Product: All / ISP UK / ISP US / DC / Residential / Mobile
- Date range: custom picker
- Search: tx_ref or customer identifier

**Table columns:**
| tx_ref | Channel | Product | Amount | Status | Created | Expires | Actions |

**Row actions:**
- View details → Order detail page
- Issue refund → Modal with reason field
- Mark as banned → Modal with evidence upload
- Add note → Internal note field

### 3. Order Detail (`/orders/:tx_ref`)

Full order information.

```
┌─────────────────────────────────────────────────────┐
│  Order TXF-abc123                          [Back] │
├─────────────────────────────────────────────────────┤
│                                                     │
│  Status: ✅ Active                                  │
│  Channel: 🌐 Instant                                │
│  Product: ISP UK                                    │
│  Amount: ₦6,500                                    │
│  Created: Jul 1, 2026 14:23 WAT                    │
│  Expires: Aug 1, 2026 14:23 WAT                   │
│                                                     │
│  ── Credentials ────────────────────────────────    │
│  Styxproxy Username: bun_uk_abc123                    │
│  Styxproxy Password: XxXxXxXxXx                       │
│  Proxy IP: 185.199.228.45                         │
│  Provider: Proxy-Seller                            │
│  Port: 1080                                       │
│                                                     │
│  ── Payment ────────────────────────────────────   │
│  Flutterwave Ref: FLW-mock-ref                     │
│  Paid at: Jul 1, 2026 14:24 WAT                   │
│  Payment Method: Card                              │
│                                                     │
│  ── Actions ────────────────────────────────────   │
│  [💰 Issue Refund]  [🚨 Mark Banned]  [📝 Note]  │
│                                                     │
│  ── Audit Log ──────────────────────────────────   │
│  Jul 1 14:24 — Order created — system             │
│  Jul 1 14:24 — Payment confirmed — system         │
│  Jul 1 14:25 — Credentials issued — admin_02      │
└─────────────────────────────────────────────────────┘
```

### 4. Customers (`/customers`)

Unified customer view — links Telegram, WhatsApp, and website orders by inferred identity.

**Search by:**
- tx_ref
- Telegram chat ID
- WhatsApp phone hash
- Email (if provided)

**Table columns:**
| Customer | Channels | Total Orders | Total Spent | Last Order | Actions |

**Customer detail shows:**
- All orders across all channels
- Channel identity (Telegram chat ID, WhatsApp hash)
- Lifetime value

### 5. Ban Claims (`/ban-claims`)

List of all ban claims with status.

**Status:** Pending / Under Review / Resolved (Replacement Issued) / Resolved (Refund) / Rejected

**Table columns:**
| tx_ref | Product | Reported | Status | Assigned To | Actions |

**Ban claim detail:**
- Order information
- Customer's evidence (screenshot upload)
- Admin notes field
- Decision: Issue Replacement / Issue Refund / Reject
- Replacement order link (if replacement issued)

### 6. Refunds (`/refunds`)

All refunds with status.

**Status:** Pending / Approved / Rejected / Processed

**Table columns:**
| tx_ref | Amount | Requested | Reason | Status | Processed By |

### 7. Credentials (`/credentials`)

All active Styxproxy credentials.

**Table columns:**
| Username | Product | Order tx_ref | Issued | Expires | Provider | Status | Actions |

**Actions:**
- View (see password)
- Revoke (immediately deactivates in Dante)
- Extend expiry (updates DB + sends SIGHUP to Dante)

### 8. Free Trials (`/free-trials`)

All active and expired trial sessions.

**Table columns:**
| Chat ID | Channel | Surveys Done | Time Earned | Expires | Status | Actions |

### 9. Audit Log (`/audit-log`) — SuperAdmin Only

Immutable log of all admin actions.

**Filters:**
- Admin: select specific admin or all
- Action type: All / Login / Refund / Credential / Ban Claim / Admin Management / System
- Date range

**Table columns:**
| Timestamp | Admin | Action | Details | IP Address |

**Details column shows JSON of what changed:**
```json
{
  "action": "refund_issued",
  "tx_ref": "TXF-abc123",
  "amount": "6500",
  "reason": "proxy_not_working",
  "refund_id": "REF-001"
}
```

**Export:** Download as CSV or JSON.

### 10. Providers (`/providers`) — SuperAdmin Only

Provider cost and status overview.

**Proxy-Seller:**
- Current month spend
- Active IPs by country
- Average cost per IP
- Recent orders

**DataImpulse:**
- Current month spend
- Active IPs
- Usage statistics

**Actions:**
- View cost breakdown by product
- Export invoice data

### 11. System Settings (`/settings`) — SuperAdmin Only

Read-only for Admin. Writable by SuperAdmin.

| Setting | Value | SuperAdmin can edit |
|---|---|---|
| Free trial: max surveys | 12 | ✅ |
| Free trial: hours per survey | 2 | ✅ |
| Refund window (hours) | 24 | ✅ |
| Max active proxies per customer | 5 | ✅ |
| Flutterwave webhook URL | https://api.styxproxy.com/webhook/flutterwave | ✅ |
| Theorem Reach postback URL | https://api.styxproxy.com/webhook/theorem-reach | ✅ |
| Email receipt: enabled | Yes/No | ✅ |

### 12. Admins (`/admins`) — SuperAdmin Only

Manage admin accounts.

**Table columns:**
| Name | Email | Role | Last Login | Status | Actions |

**Actions:**
- Create new Admin
- Edit Admin (change role)
- Deactivate Admin (cannot log in but history preserved)
- Delete Admin (SuperAdmin only, requires confirmation)

**Create Admin form:**
- Name
- Email
- Role: Admin / SuperAdmin
- Initial password (set by SuperAdmin, admin must change on first login)
- TOTP secret (display QR code for authenticator app setup)

---

## API Endpoints (Backend — Admin)

All require JWT authentication with appropriate role.

| Method | Path | Access |
|---|---|---|
| `POST /admin/login` | Login with email + password + TOTP | Public |
| `POST /admin/refresh` | Refresh access token | Public (cookie) |
| `POST /admin/logout` | Logout | Authenticated |
| `GET /admin/me` | Current admin profile | Authenticated |
| `GET /admin/dashboard/metrics` | Today's metrics | Authenticated |
| `GET /admin/orders` | List orders (paginated, filtered) | Authenticated |
| `GET /admin/orders/:tx_ref` | Order detail | Authenticated |
| `POST /admin/orders/:tx_ref/refund` | Issue refund | Admin |
| `POST /admin/orders/:tx_ref/ban` | Mark as banned | Admin |
| `POST /admin/orders/:tx_ref/note` | Add internal note | Admin |
| `GET /admin/customers` | List customers | Authenticated |
| `GET /admin/customers/:id` | Customer detail | Authenticated |
| `GET /admin/ban-claims` | List ban claims | Authenticated |
| `POST /admin/ban-claims/:id/decide` | Resolve ban claim | Admin |
| `GET /admin/refunds` | List refunds | Authenticated |
| `GET /admin/credentials` | List credentials | Authenticated |
| `POST /admin/credentials/revoke` | Revoke credential | Admin |
| `GET /admin/free-trials` | List free trials | Authenticated |
| `GET /admin/audit-log` | Audit log (paginated) | SuperAdmin |
| `GET /admin/providers/costs` | Provider cost report | SuperAdmin |
| `GET /admin/admins` | List admins | SuperAdmin |
| `POST /admin/admins` | Create admin | SuperAdmin |
| `PATCH /admin/admins/:id` | Update admin | SuperAdmin |
| `DELETE /admin/admins/:id` | Delete admin | SuperAdmin |
| `GET /admin/settings` | Get system settings | Authenticated |
| `PATCH /admin/settings` | Update system settings | SuperAdmin |

---

## Non-Functional Requirements

### Performance
- Dashboard page loads < 2 seconds
- Order list with 10,000 records: paginated, loads < 1 second
- All queries use database indexes

### Audit Log Immutability
- `admin_commands_log` table: no DELETE permission for any database user
- Only SuperAdmin can SELECT from audit log
- All inserts are automatic via backend middleware

### No Telegram for Admin
- The Telegram bot handles **customers only**
- No Telegram admin commands exist
- All admin operations go through the web dashboard

---

## Pages Summary

| Page | Route | Access |
|---|---|---|
| Login | `/login` | Public |
| Dashboard Home | `/` | Authenticated |
| Orders | `/orders` | Authenticated |
| Order Detail | `/orders/:tx_ref` | Authenticated |
| Customers | `/customers` | Authenticated |
| Ban Claims | `/ban-claims` | Authenticated |
| Refunds | `/refunds` | Authenticated |
| Credentials | `/credentials` | Authenticated |
| Free Trials | `/free-trials` | Authenticated |
| Audit Log | `/audit-log` | SuperAdmin |
| Providers | `/providers` | SuperAdmin |
| System Settings | `/settings` | Authenticated (read) / SuperAdmin (write) |
| Admins | `/admins` | SuperAdmin |

---

*This spec is the source of truth for the admin dashboard. Update before building.*
