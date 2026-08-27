# Order Status & Actions Page — Design Document

**Status:** Draft for implementation  
**Author:** Design synthesis from existing `/manage`, `/thank-you`, `/receipt`, and admin order pages  
**Target route:** `/order/status` (new) — deep-linkable, replaces the thin `/manage` experience  
**Design system:** Existing CSS variables in `globals.css` (`--primary`, `--card`, `--border`, `--success`, `--warning`, `--error`, `--muted`, etc.)  
**Mobile-first:** Yes — all layouts start at 360px and scale up

---

## 1. Order Status Definitions & Visual Indicators

The canonical status set (from `OrderStatus` in `src/types/index.ts` plus `payment_failed`):

| Status | Group | Icon | Color token | Badge style | Meaning |
|---|---|---|---|---|---|
| `pending` | In-progress | `Clock` (animated pulse) | `--warning` | `bg-[var(--warning)]/20 text-[var(--warning)] border-[var(--warning)]/30` | Awaiting payment confirmation |
| `paid` | In-progress | `Check` | `--primary` | `bg-[var(--primary)]/20 text-[var(--primary)] border-[var(--primary)]/30` | Payment received, provisioning proxy |
| `processing` | In-progress | `Spinner` / `ArrowsClockwise` | `--primary` | `bg-[var(--primary)]/20 text-[var(--primary)] border-[var(--primary)]/30` | Proxy being provisioned upstream |
| `fulfilled` | Success | `CheckCircle` | `--success` | `bg-[var(--success)]/20 text-[var(--success)] border-[var(--success)]/30` | Credentials issued, proxy live |
| `active` | Success | `CheckCircle` | `--success` | `bg-[var(--success)]/20 text-[var(--success)] border-[var(--success)]/30` | Proxy active and in use |
| `expired` | Terminal-bad | `ClockCounterClockwise` | `--muted` | `bg-[var(--muted)]/20 text-[var(--muted)] border-[var(--muted)]/30` | Proxy past `expires_at` |
| `cancelled` | Terminal-bad | `XCircle` | `--error` | `bg-[var(--error)]/20 text-[var(--error)] border-[var(--error)]/30` | Order cancelled (user or system) |
| `refunded` | Terminal-bad | `ArrowCounterClockwise` | `--error` | `bg-[var(--error)]/20 text-[var(--error)] border-[var(--error)]/30` | Payment refunded |
| `payment_failed` | Terminal-bad | `WarningCircle` | `--error` | `bg-[var(--error)]/20 text-[var(--error)] border-[var(--error)]/30` | Payment attempt failed |

> **Note:** `fulfilled` and `active` are treated identically in the UI — both mean "proxy is live." The distinction is backend-only (fulfilled = just provisioned, active = ongoing).

### Status grouping for UI logic

```ts
const STATUS_GROUPS = {
  inProgress: ['pending', 'paid', 'processing'],
  success: ['fulfilled', 'active'],
  terminalBad: ['expired', 'cancelled', 'refunded', 'payment_failed'],
} as const;
```

---

## 2. Available Actions Per Status

Actions are surfaced as **primary** (filled green `--primary` bg) and **secondary** (outlined border) buttons. The `next_action` field from the API is the source of truth for which action to emphasize.

| Status | Primary action | Secondary actions | Condition |
|---|---|---|---|
| `pending` | Retry payment (`/order/checkout?renew={order_id}`) | Cancel order, Contact support | — |
| `paid` | — (auto-provisioning) | Contact support | Show "provisioning…" state |
| `processing` | — (auto-provisioning) | Contact support | Show spinner + ETA |
| `fulfilled` | Rotate proxy key | Renew (if near expiry), Contact support | `rotation_count < max_rotations` |
| `active` | Rotate proxy key | Renew (if near expiry), Contact support | `rotation_count < max_rotations` |
| `expired` | Renew (`/order/checkout?renew={order_id}`) | Reorder, Contact support | `is_renewable === true` |
| `cancelled` | Reorder (`/order`) | Contact support | — |
| `refunded` | Reorder (`/order`) | Contact support | — |
| `payment_failed` | Retry payment (`/order/checkout?renew={order_id}`) | Reorder, Contact support | — |

### Action definitions (for the `<ActionBar>` component)

```ts
type Action =
  | { kind: 'rotate'; label: string; disabled?: boolean; reason?: string }
  | { kind: 'renew'; label: string; href: string }
  | { kind: 'retry_payment'; label: string; href: string }
  | { kind: 'reorder'; label: string; href: string }
  | { kind: 'cancel'; label: string; confirm: true }
  | { kind: 'contact_support'; label: string; href: string }
  | { kind: 'download_receipt'; label: string; href: string }
  | { kind: 'view_timeline'; label: string }; // expand/collapse timeline
```

### Rotation gating logic (from existing `/manage`)

```ts
const rotationsLeft = (max_rotations ?? 3) - (rotation_count ?? 0);
const canRotate = rotationsLeft > 0 && STATUS_GROUPS.success.includes(status);
```

### Renewal gating logic

```ts
const isNearExpiry = expires_at
  ? new Date(expires_at).getTime() - Date.now() < 7 * 24 * 60 * 60 * 1000
  : false;
const canRenew = is_renewable || isNearExpiry;
```

---

## 3. UI Component Design

### 3.1 Page layout — "Status Card + Timeline" hybrid

The page is a **single-column card stack** (mobile-first). Each card is a `rounded-2xl bg-[var(--card)] border border-[var(--border)]` block. The order:

```
┌─────────────────────────────────────────┐
│  HEADER: "Order Status"                 │
│  order_id · tx_ref                      │
├─────────────────────────────────────────┤
│  STATUS BANNER                          │
│  [icon]  Status label                   │
│  user_message / next_action text        │
│  animated pulse if in-progress          │
├─────────────────────────────────────────┤
│  ACTION BAR                             │
│  [Primary action]  [Secondary action]   │
├─────────────────────────────────────────┤
│  ORDER DETAILS                          │
│  Plan · Country · Amount · Dates        │
├─────────────────────────────────────────┤
│  PROXY CREDENTIALS (if fulfilled/active)│
│  Username · Password · Address · Port   │
│  [Rotate] [Copy full format]            │
├─────────────────────────────────────────┤
│  ORDER TIMELINE (collapsible)           │
│  ● Created → ● Paid → ● Fulfilled      │
│  ○ Expires (future)                     │
├─────────────────────────────────────────┤
│  HELP FOOTER                            │
│  "Need help? [Chat with Charon]"        │
└─────────────────────────────────────────┘
```

### 3.2 Status Banner

The banner is the hero element. It changes background tint and border color based on status group:

```tsx
<div className={`rounded-2xl p-5 border ${
  STATUS_GROUPS.inProgress.includes(status)
    ? 'bg-[var(--warning)]/10 border-[var(--warning)]/30'
    : STATUS_GROUPS.success.includes(status)
    ? 'bg-[var(--success)]/10 border-[var(--success)]/30'
    : 'bg-[var(--error)]/10 border-[var(--error)]/30'
}`}>
  <div className="flex items-center gap-3">
    <StatusIcon status={status} />
    <div className="flex-1">
      <p className="font-semibold text-sm">{statusLabel}</p>
      <p className="text-xs text-[var(--muted)] mt-0.5">{user_message || defaultMessage}</p>
    </div>
    <StatusBadge status={status} />
  </div>
</div>
```

**In-progress animation:** When status is `pending`/`paid`/`processing`, the icon has a subtle CSS pulse (reuse `@keyframes charon-glow` pattern or a simple `animate-pulse`).

### 3.3 Action Bar

A horizontal flex container that wraps on mobile. Primary action is always first.

```tsx
<div className="flex flex-col sm:flex-row gap-3">
  {actions.primary && (
    <ActionButton {...actions.primary} variant="primary" />
  )}
  {actions.secondary.map((a) => (
    <ActionButton {...a} variant="secondary" />
  ))}
</div>
```

**Button variants:**

| Variant | Classes |
|---|---|
| Primary | `bg-[var(--primary)] hover:bg-[var(--primary-dark)] text-black font-semibold` |
| Secondary | `border border-[var(--border)] hover:border-[var(--primary)] text-[var(--foreground)] font-medium` |
| Danger | `border border-[var(--error)]/30 text-[var(--error)] hover:bg-[var(--error)]/10` |

### 3.4 Order Details Card

Same key-value row pattern as existing `/manage`. Each row is `flex items-center justify-between py-2 border-b border-[var(--border)]`.

Fields shown:
- Order ID (monospace, copyable)
- Transaction Ref (monospace, copyable)
- Plan type
- Country (with flag emoji)
- Amount Paid (₦ formatted, `--primary` color)
- Created date
- Expires date (with live countdown if active)

### 3.5 Credentials Card

Only rendered when `status ∈ ['fulfilled', 'active']` AND `styxproxy_credential` is present. Reuses the existing `CredentialField` pattern from `/manage`:

- Username (copyable)
- Password (sensitive, blurred by default, toggle to reveal)
- Proxy Address (`ip:port`)
- Protocol (`HTTP / SOCKS5`)
- Full format string (copyable)
- Expiry countdown bar (amber if < 7 days)
- Rotate button (if `rotationsLeft > 0`)
- Renew button (if `canRenew`)

### 3.6 Order Timeline (collapsible)

A vertical timeline showing the order's journey. Each step is a circle + label. Completed steps are filled, current step is pulsing, future steps are dimmed.

```
●  Order placed        Jan 15, 2026
│
●  Payment confirmed   Jan 15, 2026
│
●  Proxy provisioned   Jan 15, 2026
│
○  Expires             Feb 15, 2026
```

**Implementation:**

```tsx
<div className="space-y-0">
  {timelineSteps.map((step, i) => (
    <div key={step.key} className="flex gap-3">
      <div className="flex flex-col items-center">
        <div className={`w-3 h-3 rounded-full ${
          step.state === 'done'
            ? 'bg-[var(--success)]'
            : step.state === 'current'
            ? 'bg-[var(--primary)] animate-pulse'
            : 'bg-[var(--border)]'
        }`} />
        {i < timelineSteps.length - 1 && (
          <div className={`w-0.5 h-8 ${
            step.state === 'done' ? 'bg-[var(--success)]' : 'bg-[var(--border)]'
          }`} />
        )}
      </div>
      <div className="pb-4">
        <p className="text-sm font-medium">{step.label}</p>
        <p className="text-xs text-[var(--muted)]">{step.date}</p>
      </div>
    </div>
  ))}
</div>
```

**Timeline steps derived from status:**

| Status | Steps shown |
|---|---|
| `pending` | Order placed ●, Payment confirmed ○, Proxy provisioned ○, Expires ○ |
| `paid` / `processing` | Order placed ●, Payment confirmed ●, Proxy provisioned ○ (pulsing), Expires ○ |
| `fulfilled` / `active` | Order placed ●, Payment confirmed ●, Proxy provisioned ●, Expires ○ |
| `expired` | Order placed ●, Payment confirmed ●, Proxy provisioned ●, Expired ● |
| `cancelled` | Order placed ●, Cancelled ● |
| `refunded` | Order placed ●, Payment confirmed ●, Refunded ● |
| `payment_failed` | Order placed ●, Payment failed ● |

### 3.7 Help Footer

```tsx
<div className="text-center pt-4 border-t border-[var(--border)]">
  <p className="text-sm text-[var(--muted)]">
    Need help with this order?{' '}
    <button
      onClick={() => window.dispatchEvent(new CustomEvent('open-chat-widget', { detail: { context: 'support', orderId } }))}
      className="text-[var(--primary)] hover:underline font-medium"
    >
      Chat with Charon →
    </button>
  </p>
</div>
```

---

## 4. Integration with Existing `/manage` Page

### 4.1 Migration strategy

The new `/order/status` page **supersedes** `/manage`. The migration:

1. **Create** `/order/status` as the new canonical order lookup page.
2. **Redirect** `/manage` → `/order/status` (301 or Next.js `redirect()` in `next.config.js`).
3. **Preserve** `/manage` as a redirect target for any existing links (receipts, emails, etc.).
4. **Update** all internal links (`/manage` → `/order/status`) across the codebase.

### 4.2 Route structure

```
/order/status              → new page (search + results)
/order/status/[order_id]   → deep-linkable: skip search, show order directly
/manage                    → redirect to /order/status
```

### 4.3 Search flow

The search card at the top accepts:
- Order ID (e.g., `STX-XXXXX` or `ADMIN-XXXXX`)
- Transaction reference (e.g., `TXF-XXXXX`)

On submit:
1. Resolve to `order_id` via existing `/api/orders/by-payment-reference/{tx_ref}` or use directly.
2. Fetch full order via `/api/orders/{order_id}/status` (the `OrderPaymentStatus` endpoint).
3. Render the status page with the response.

### 4.4 Local order history

Reuse the existing `getOrderHistory()` from `src/lib/device-id.ts` to show recent orders below the search card (same pattern as current `/manage`).

### 4.5 API endpoints used

| Endpoint | Purpose |
|---|---|
| `GET /api/orders/by-payment-reference/{tx_ref}` | Resolve tx_ref → order_id |
| `GET /api/orders/{order_id}/status` | Full order status + next_action + credential |
| `POST /api/orders/{order_id}/rotate` | Rotate proxy key |
| `GET /api/orders/{order_id}/receipt` | Receipt data (for PDF download) |

### 4.6 Shared components to extract

Before building `/order/status`, extract these from `/manage` into reusable components:

| Component | Location | Notes |
|---|---|---|
| `CredentialField` | `src/components/order/CredentialField.tsx` | Label + value + copy + optional reveal |
| `StatusBadge` | `src/components/order/StatusBadge.tsx` | Colored pill per status |
| `StatusBanner` | `src/components/order/StatusBanner.tsx` | Full-width status header |
| `ActionBar` | `src/components/order/ActionBar.tsx` | Primary + secondary action buttons |
| `OrderDetails` | `src/components/order/OrderDetails.tsx` | Key-value order fields |
| `OrderTimeline` | `src/components/order/OrderTimeline.tsx` | Vertical timeline |
| `ExpiryCountdown` | `src/components/order/ExpiryCountdown.tsx` | Live countdown timer |

---

## 5. Data Flow & State Machine

### 5.1 Fetch logic

```ts
// Pseudocode for the page component
const [order, setOrder] = useState<OrderPaymentStatus | null>(null);
const [loading, setLoading] = useState(false);
const [error, setError] = useState<string | null>(null);

async function loadOrder(orderId: string) {
  setLoading(true);
  const res = await fetch(`/api/orders/${orderId}/status`);
  const data: OrderPaymentStatus = await res.json();
  setOrder(data);
  setLoading(false);

  // If still polling, schedule next fetch
  if (data.next_action === 'poll') {
    setTimeout(() => loadOrder(orderId), 3500);
  }
}
```

### 5.2 next_action → UI mapping

| `next_action` | UI behavior |
|---|---|
| `poll` | Show spinner, auto-refresh every 3.5s |
| `redirect_to_proxy_details` | Show success, render credentials |
| `show_retry` | Show payment-failed banner + retry button |
| `show_failure` | Show terminal-bad banner + reorder button |
| `provider_down` | Show warning banner + contact support |

### 5.3 Live updates

- **In-progress statuses** (`pending`, `paid`, `processing`): poll every 3.5s (same as `PaymentStatusPoller`).
- **Success statuses** (`fulfilled`, `active`): no polling. Show static page with rotate/renew.
- **Terminal statuses** (`expired`, `cancelled`, `refunded`, `payment_failed`): no polling. Show static page with reorder/contact.

---

## 6. Responsive Behavior

### Mobile (< 640px)
- Single column, full-width cards
- Action buttons stack vertically (primary on top)
- Credential fields stack 1-column
- Timeline is always visible (no collapse)

### Tablet (640px–1024px)
- Max-width container (`max-w-2xl`)
- Action buttons in a row
- Credential fields in 2-column grid

### Desktop (> 1024px)
- Max-width container (`max-w-3xl`)
- Same as tablet, more breathing room

---

## 7. Dark Theme & CSS Variables

All styling uses the existing CSS variable system. No new variables needed.

```css
/* Already defined in globals.css */
--background: #000000;
--card: #141414;
--border: #252525;
--foreground: #f5f5f5;
--muted: #737373;
--primary: #0AD25A;
--success: #22c55e;
--warning: #f59e0b;
--error: #ef4444;
```

Status-specific colors are composed inline:
```tsx
// Example: success banner
className="bg-[var(--success)]/10 border-[var(--success)]/30 text-[var(--success)]"
```

---

## 8. Accessibility

- All interactive elements are `<button>` or `<Link>` (no divs with onClick).
- `aria-label` on icon-only buttons (copy, reveal, rotate).
- Focus-visible outline via existing `:focus-visible` rule.
- Color is never the sole indicator — icons and text labels accompany every status.
- Live countdown uses `aria-live="polite"` for screen readers.

---

## 9. File Structure (Proposed)

```
src/app/(public)/order/status/
  page.tsx                    — main page (search + render)
  [order_id]/
    page.tsx                  — deep-linkable order view

src/components/order/
  StatusBadge.tsx             — colored status pill
  StatusBanner.tsx            — full-width status header
  StatusIcon.tsx              — icon per status
  ActionBar.tsx               — primary + secondary action buttons
  ActionButton.tsx            — single action button (variant-aware)
  OrderDetails.tsx            — key-value order fields
  CredentialField.tsx         — label + value + copy + reveal
  CredentialsCard.tsx         — full credentials block
  OrderTimeline.tsx           — vertical timeline
  ExpiryCountdown.tsx         — live countdown timer
  OrderSearchCard.tsx         — search input + button
  RecentOrders.tsx            — local device history

src/lib/order-status.ts       — pure helpers (status group, actions, timeline steps)
```

---

## 10. Implementation Phases

### Phase 1 — Core page + status display
- Create `/order/status` with search
- Render `StatusBanner` + `OrderDetails`
- Redirect `/manage` → `/order/status`

### Phase 2 — Actions
- Add `ActionBar` with rotate, renew, retry, reorder, cancel
- Wire up existing rotate API
- Add confirmation dialogs for destructive actions

### Phase 3 — Credentials + Timeline
- Add `CredentialsCard` (extract from `/manage`)
- Add `OrderTimeline` (collapsible)
- Add `ExpiryCountdown` live timer

### Phase 4 — Polish
- Deep-linkable `/order/status/[order_id]`
- Recent orders from local history
- Loading skeletons
- Error states (not found, network error, provider down)

---

## 11. Open Questions

1. **Cancel order** — Is there a `POST /api/orders/{order_id}/cancel` endpoint? If not, cancel may need to be a support action only.
2. **Receipt download** — Should the receipt PDF button be on this page or only on `/receipt/[tx_ref]`? Proposed: include a "Download receipt" secondary action.
3. **Multiple orders** — Should `/order/status` support viewing multiple orders at once (list view) or one at a time? Proposed: one at a time, with recent-orders list below for quick switching.
4. **Auto-redirect** — When `next_action === 'redirect_to_proxy_details'`, should we auto-navigate or let the user click? Proposed: render the page directly (no redirect needed since this IS the proxy details page now).

---

## 12. Summary of Key Design Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Layout | Card stack, single column | Matches existing `/manage` pattern, mobile-first |
| Status display | Banner + badge + icon | Immediate visual recognition |
| Actions | Computed from status + next_action | Single source of truth from API |
| Credentials | Reuse `/manage` pattern | Already tested, users familiar |
| Timeline | Vertical, collapsible | Shows progress without clutter |
| Integration | `/manage` redirects to `/order/status` | Clean migration, no broken links |
| Theming | Existing CSS variables | No new design tokens needed |
| Polling | 3.5s for in-progress only | Same as `PaymentStatusPoller` |