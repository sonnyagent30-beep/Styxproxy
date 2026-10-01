# Schema drift: `alembic upgrade head` vs `app/models.py`

**Status as of t_2af95a6b (2026-10-01), branch `devops/ci-gate-t_2af95a6b`.**

## The short version

`alembic upgrade head` now succeeds on a clean Postgres 16 (exit 0, all 27
revisions) after nine defects were fixed. But reaching `head` is not the same
as producing the schema the application expects. The migration chain and
`app/models.py` still disagree substantially, and that disagreement is why
three tests in `tests/test_routers_products.py` remain red.

This document records the gap so it is not rediscovered from scratch. It is
**not** fixed here — closing it is a separate, larger piece of work.

## Why the two disagree

This is not random drift. It is structural:

- `app/models.py` is the authoritative schema. Production was grown by hand
  and by `Base.metadata.create_all` at application startup.
- `alembic/versions/` was written largely *after the fact*, as a historical
  record. `008_add_admin_role` says so explicitly: its changes "were applied
  directly to production Postgres ... this migration exists purely to record
  that in version history."
- Several migrations were written against an **older** model than the one
  deployed (that is why `20260827_missing_indexes` asked to index
  `orders.customer_id`, a column that never existed in either).

So the chain is a record of production, not a recipe for building production.
That is workable, but it means a clean `alembic upgrade head` will never by
itself produce a working schema until the missing DDL is written down.

## Measured drift

Measured by comparing `Base.metadata` against a database built purely by
`alembic upgrade head` on Postgres 16.15 (`backend/scripts/schema_drift_report.py`).

**14 model tables are never created by any migration:**

    admin_webhooks            categories
    charon_ab_assignments     charon_ab_outcomes
    cities                    email_unsubscribes
    idempotency_responses     trigger_events
    trigger_weights           admin_webhook_logs
    plan_cities               post_categories
    referral_credits          refund_approvals

**11 tables are missing columns the model declares:**

| table | missing columns |
|---|---|
| `admin_auth` | `id`, `email`, `password_hash`, `allowed_ips` |
| `admin_invites` | `feature_overrides` |
| `charon_escalations` | `customer_message`, `resolved_at`, `updated_at` |
| `contact_submissions` | `updated_at` |
| `customers` | `referral_code` |
| `free_trials` | `styxproxy_credential_id` |
| `orders` | `tx_ref`, `rotation_mode`, `city_id`, `city_name`, `customer_email`, `emails_sent`, `idempotency_key`, `referral_tx_ref`, `reminder_sent_at`, `styxproxy_credential_id` |
| `plans` | `price_per_gb`, `min_gb`, `max_gb`, `gb_tiers`, `rotation_mode`, `static_price_multiplier`, `supports_city`, `supports_country_change` |
| `posts` | `featured` |
| `rls_policy` | `role_name`, `using_clause`, `with_check`, `policy_status`, `created_by` |
| `styxproxy_credentials` | `socks_port`, `rotation_mode`, `assigned_static_ip`, `assigned_static_session_id`, `last_static_assigned_at`, `location_change_count`, `location_changes_reset_at`, `rotation_mode_change_count`, `rotation_mode_changes_reset_at` |

## What this breaks

`plans.price_per_gb` and its siblings are the reason three tests are red:

```
tests/test_routers_products.py::test_list_products_returns_all
tests/test_routers_products.py::test_products_have_required_fields
tests/test_routers_products.py::test_products_prices_are_correct
```

They fail with `UndefinedColumnError: column plans.price_per_gb does not exist`
— not an assertion mismatch. `/api/products` selects the full `Plan` model, and
the migrated table does not have those columns.

That endpoint is separately dead (QA-3, card `t_6edcf426`): it returns
`{"products": []}` in production and nothing in the frontend calls it — the
storefront uses `/api/catalog`, which is live and serves 33 enabled plans. So
these three tests are in the known-failure baseline for two independent
reasons, and both need fixing before the entries can be removed.

## What was fixed in t_2af95a6b

Nine defects that made `alembic upgrade head` fail on a clean database:

| revision | defect |
|---|---|
| 001 | `orders` declares an FK to `bunche_credentials` before that table exists — and the two tables reference each other, so reordering cannot fix it. FK moved to a deferred `create_foreign_key`. |
| 001 | `alembic_version.version_num` is `varchar(32)` but two revision ids are longer (`003_add_admin_invites_feature_flags` is 35) — stamping them raised `StringDataRightTruncationError`. Column widened to 64. |
| 009 | `ALTER TABLE admin_audit_log` on a table **no migration ever created**. `001` creates `customer_audit_log`; `admin_audit_log` exists only in the model and in production. Now created (guarded) in 009. |
| 010 | Renamed `bun_password`, but `001` creates that column as `password_hash`. Raised `UndefinedColumnError`. Both source names now handled. |
| 019 | `ADD COLUMN` on three columns `001` already creates. The inline comment claimed "Postgres ignores no-op ALTER" — it does not. Now `IF NOT EXISTS`. |
| 021 | `op.create_index(..., postgresql_only=True)` — not a valid SQLAlchemy argument. Raised `ArgumentError` before emitting any SQL. Removed. |
| 20260809_rls | Policies joined `orders.id`, but `orders`' PK is `order_id`. Raised `UndefinedColumnError`. Corrected. |
| 20260809_referral | A batch of six `COMMENT ON` statements in one `execute()`. asyncpg rejects that: "cannot insert multiple commands into a prepared statement". Split. |
| 20260827_missing_indexes | Indexed `orders.customer_id` and `styxproxy_credentials.customer_id`, which exist in neither the model nor `001` (the model uses `customer_phone`). Also indexed `tx_ref`, which no migration creates. Corrected, and index creation is now skipped when the column is absent. |

## Two more defects outside the migration chain

Both were found while verifying the above, and both had been invisible for the
same reason the tests were: `continue-on-error` on the job.

1. **`pip install -e ".[dev]"` failed outright.** No `[tool.setuptools]` section
   meant flat-layout auto-discovery found eight top-level packages under
   `backend/` and hard-failed the build. The step that installs the
   dependencies the tests need was failing on every run.
2. **`pyjwt` was undeclared.** `app/services/ops_auth.py:6` does `import jwt`,
   which is PyJWT — a different distribution from the declared
   `python-jose` (whose module is `jose`). On a clean install, 15 test modules
   died at import with `ModuleNotFoundError: No module named 'jwt'`.

Together these mean the backend-test job was not merely tolerant of failure;
it could not have run the suite successfully at all. Fixing them is a
precondition for the gate in `ci.yml` meaning anything.

## What is left to do

Closing the drift itself is **not** in t_2af95a6b and is not a CI-config
change. It needs a decision that is not the devops caller's to make:

1. Decide the source of truth going forward — either bring the migration chain
   up to the model (write the missing DDL as new revisions, which is the
   safer default because it does not touch production), or accept that
   migrations are a historical record only and generate a clean schema some
   other way.
2. Only then can `tests/test_routers_products.py` be un-baselined, and only
   then can `/api/products` be judged dead-or-not with real evidence
   (`t_6edcf426`).

Until then, the `20260827_missing_indexes` guards make the chain tolerant: it
skips an index whose column is absent and prints what it skipped, rather than
aborting the whole migration.
