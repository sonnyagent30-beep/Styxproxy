# Admin Price Editor UI — Track 3 Deliverable

## Where it lives

`/admin/prices` route in the charon web dashboard (Next.js or whatever charon is built on).
Only users with `admin:write` scope can see/edit this page.

## Layout (high-level wireframe)

```
┌─────────────────────────────────────────────────────────────────┐
│  STYXPROXY ADMIN                              [user@email] [⎋]   │
├─────────────────────────────────────────────────────────────────┤
│  Catalog  Plans  Customers  Orders  Refunds  Providers  Logs    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  PLAN PRICING                                                   │
│  ─────────────────                                              │
│  [Edit mode: OFF]   Last updated: 2026-08-20 04:12 by dannion    │
│  Bulk edit changes are atomic — all updates commit together.    │
│                                                                 │
│  Filter: [All types ▾]  [All countries ▾]  [Search… 🔍]         │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Plan                  │ Type        │ GB │ Country │ Price │  │
│  ├──────────────────────────────────────────────────────────┤  │
│  │ ISP Starter           │ isp         │ 5  │ NG      │ ₦4500 │  │
│  │ ISP Pro               │ isp         │ 20 │ NG      │ ₦14000│  │
│  │ Residential 10GB      │ residential │ 10 │ ANY    │ ₦8500 │  │
│  │ Residential 50GB      │ residential │ 50 │ ANY    │ ₦38000│  │
│  │ Mobile 5GB            │ mobile      │ 5  │ NG      │ ₦3500 │  │
│  │ Mobile 20GB           │ mobile      │ 20 │ NG      │ ₦12000│  │
│  │ Datacenter 1GB        │ datacenter  │ 1  │ ANY    │ ₦1200 │  │
│  │ [+ Add plan]                                              │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  When Edit mode = ON:                                            │
│   - Price cells become inputs (with ₦ prefix kept)              │
│   - "Enabled" column shows a checkbox per row                   │
│   - Sticky footer appears:                                      │
│     [Cancel]  3 unsaved changes  [Review diff]  [Save all]      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Component tree

```
<PriceEditorPage>
  <PageHeader user={adminUser} />
  <AdminTabs active="plans" />
  <PlanPricingSection>
    <SectionToolbar>
      <EditModeToggle />
      <LastUpdated />
      <FilterBar />            // type, country, search
    </SectionToolbar>
    <PlanTable>
      <PlanRow editMode={…}>
        <PlanName />           // display + rename inline
        <TypeBadge />          // isp / residential / mobile / datacenter
        <DataGBInput />        // integer input, disabled in view mode
        <CountryDropdown />
        <PriceInput currency="NGN" />   // masked input
        <EnabledCheckbox />
        <RowActions>
          <DuplicateButton />
          <DeleteButton />     // soft-delete only
        </RowActions>
      </PlanRow>
      <AddPlanRow onClick={openCreateModal} />
    </PlanTable>
    {editMode && <EditFooter>
      <CancelButton />
      <ChangeSummary count={n} />
      <ReviewDiffButton />     // opens <DiffModal>
      <SaveAllButton onClick={callCharonAPI} />
    </EditFooter>}
  </PlanPricingSection>
  <CreatePlanModal />           // when [+ Add plan] clicked
  <DiffModal />                 // shows before/after table
  <ConfirmSaveModal />          // requires admin password re-entry
</PriceEditorPage>
```

## State model

```typescript
type EditState = "view" | "editing" | "saving" | "error";

type Plan = {
  id: string;
  type: "isp" | "residential" | "mobile" | "datacenter";
  country: string;
  data_gb: number;
  duration_days: number | null;
  price_ngn: number;
  enabled: boolean;
  max_concurrent_users: number;
  updated_at: string;
  // Local-only fields:
  dirty?: boolean;             // user changed but not saved
  originalPrice?: number;       // for diff display
};

type PendingChange = {
  plan_id: string;
  price_ngn?: number;
  enabled?: boolean;
  data_gb?: number;
};
```

## API calls (charon v1)

| When | Endpoint | Method | Notes |
|---|---|---|---|
| Page load | `/api/v1/admin/plans` (or read from `/catalog` + admin scope) | GET | Initial fetch |
| Filter change | Same as above with query params | GET | Re-fetch |
| Save (bulk) | `/api/v1/admin/plans` | PATCH | `updates[]` array, atomic |
| Create new plan | `/api/v1/admin/plans` | POST | Open CreatePlanModal |
| Soft-delete | `/api/v1/admin/plans/{id}` | DELETE | Soft-delete, sets enabled=false |
| Toggle enabled (single) | `/api/v1/admin/plans` | PATCH | One-item batch |

## Validation rules (client-side, before save)

- `price_ngn`: must be > 0, max 9999999, 2 decimal places
- `data_gb`: integer, 1–10000
- `country`: must be in supported countries list
- `duration_days`: integer or null, max 365
- `enabled`: any change requires typing "DISABLE" in confirm if disabling the only plan for a country+type combo (prevents accidental revenue loss)

## UX details

### Edit mode toggle

Click the toggle to enter edit mode. The table transforms:
- Background of all rows becomes light yellow (indicating editable)
- Inputs replace display values
- Footer with change counter appears

### Diff modal

Before saving, show user a side-by-side:
```
PLAN              | BEFORE       | AFTER        | Δ
─────────────────�─────────────┼─────────────┼─────────
ISP Starter      | ₦4500 (ON)  | ₦4900 (ON)  | +₦400
Residential 50GB | ₦38000 (ON) | ₦38000 (OFF)| DISABLED
```

### Confirm save

If changes affect more than ₦1000 total monthly revenue (rough estimate), require admin to re-type password:

```
┌────────────────────────────────────────────┐
│  Confirm price update                      │
│                                            │
│  3 plans will change.                      │
│  Estimated monthly revenue impact: +₦8400 │
│                                            │
│  Enter your password to confirm:           │
│  [••••••••••••]                            │
│                                            │
│  [Cancel]              [Confirm and save]  │
└────────────────────────────────────────────┘
```

### Optimistic updates

When user types in a price input:
1. Update local state immediately (show in yellow)
2. Don't call API yet
3. Wait for "Save all" button

### Error states

- Network error on save → show toast, restore previous values, allow retry
- Validation error from charon → show inline error on the offending row, keep other changes editable
- "Cache invalidation failed" → show warning but don't block save (catalog will refresh on next 60s tick)

## Audit log entries (auto-generated by charon)

When admin saves changes, charon logs:
```json
{
  "actor": "dannion@styxproxy.com",
  "action": "plan.price.update",
  "target": {
    "updates": [
      { "plan_id": "isp_starter_ng", "price_ngn_before": 4500, "price_ngn_after": 4900 },
      { "plan_id": "residential_50gb", "enabled_before": true, "enabled_after": false }
    ]
  },
  "ip_address": "...",
  "timestamp": "2026-08-20T..."
}
```

This shows up at `/admin/audit-log` for compliance review.

## Mobile / responsive notes

- Table becomes card-stack on narrow screens (each plan = one card)
- Edit mode toggle moves to top-right of each card
- Bulk save bar becomes a sticky bottom sheet

## What to NOT include (out of scope for v1)

- Per-customer pricing overrides (future)
- Promotional codes / discounts (future)
- A/B testing prices (future)
- Currency selection (NGN only for now — single currency model)
- Bulk import via CSV (future — manual entry is enough for v1)

## Files to create in charon repo

```
charon/
  src/
    pages/
      admin/
        prices/
          index.tsx                   # Page entry
    components/
      admin/
        PlanPricingSection.tsx
        PlanTable.tsx
        PlanRow.tsx
        PriceInput.tsx
        EditModeToggle.tsx
        EditFooter.tsx
        DiffModal.tsx
        CreatePlanModal.tsx
        ConfirmSaveModal.tsx
    hooks/
      useAdminPlans.ts                # Fetch + cache
      usePriceEditor.ts               # Edit mode state machine
    api/
      charon.ts                       # Typed charon client (generated from OpenAPI)
  tests/
    PlanPricingSection.test.tsx
    usePriceEditor.test.ts
```

## Acceptance criteria (for Sprint B+D sign-off)

- [ ] Admin can see current prices without page refresh
- [ ] Edit mode toggle works, with visual indication of unsaved changes
- [ ] Bulk save calls `PATCH /api/v1/admin/plans` atomically
- [ ] Price changes invalidate catalog cache (next `/catalog` read returns new prices within 60s)
- [ ] Audit log entry created for every save
- [ ] Password re-confirm required for changes affecting > ₦1000/mo revenue
- [ ] n8n order-handler reading `/catalog` after price change gets the new price (integration test with Squad B's deployed charon)
- [ ] Mobile responsive at 375px width
- [ ] No "edit price in DB" path exists anymore — confirmed by killing `styxproxy_n8n` direct-DB write permissions after migration
