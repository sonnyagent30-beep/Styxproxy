# Applying schema migrations in production

**Read this before adding a column to `app/models.py`.**

## The one-paragraph version

Production's schema is managed by `Base.metadata.create_all` at application
startup (`app/main.py`) plus hand-written `ALTER TABLE` statements, **not** by
`alembic upgrade`. `alembic_version` on production is frozen at
`merge_20260819_three_heads` and has been since 2026-08-19, and
`alembic upgrade head` **fails and rolls back** on production. So adding a
migration file alone does nothing to production. The deploy gate
(`backend/scripts/schema_gate.py`) is what tells you this.

## Why alembic cannot be trusted here

Verified 2026-10-01 against a restored copy of production:

- `alembic upgrade head` fails on the **first** pending revision
  (`20260827_missing_indexes`) and is **atomic** — it applies nothing.
  9 of its 27 statements fail because it indexes `orders.customer_id`, a
  column that exists in neither production nor the model (`Order` uses
  `platform_account_id`).
- The repo currently has **multiple alembic heads**, so `upgrade head` is
  ambiguous even before the above.
- The deploy workflow runs `set +e` around `alembic upgrade heads 2>&1 |
  tail -20` (`.github/workflows/deploy-backend.yml`), discarding both the exit
  code and the error text. The same anti-pattern is in `ci.yml`. This is why
  migrations have been failing silently on every deploy since 2026-08-27 and
  nobody noticed.

`app/models.py` is the authoritative schema definition, not
`alembic/versions/`.

## Telling `create_all` apart from migrations

Fingerprint: `create_all` names `index=True` columns `ix_<table>_<col>`, so
production carries `ix_charon_conversations_session_id` and
`ix_orders_bunche_credential_id`, while migrations name them by hand
(`idx_charon_conv_session`). Production has `idx_orders_created` (the model's
`__table_args__` name); the migration wants `idx_orders_created_at` — that
migration was written against an **older** model than the one deployed.

## Ownership: why the app cannot migrate its own schema

Table ownership on production is **split across four roles**, which is the
root cause of the silent failure this document exists to prevent:

| owner | tables |
|---|---|
| `styxproxy_migrate` | 44 (includes `orders`, `free_trials`) |
| `postgres` | 13 (includes `trial_sessions`, `admin_webhook_logs`, `referral_credits`) |
| `styxproxy_app` | 7 (includes `alembic_version`, `products`) |
| `styxproxy_n8n` | 52 (all `n8n_*`) |

The app connects as `styxproxy_app`. Postgres only permits `ALTER TABLE` to
the **owner** of the table. So the startup `ALTER TABLE orders ADD COLUMN IF
NOT EXISTS ...` loop in `app/main.py` has **never once succeeded** — it fails
on its first statement with `InsufficientPrivilegeError: must be owner of
table orders`.

That failure was logged only as `logger.warning("Orders column migration
skipped: ...")`, which in an aggregated log is indistinguishable from the
success line `Orders table columns verified/updated`. Verified on production:
the success string appears **zero** times across all five rotated log files,
while the warning appears on every single boot.

Note that `styxproxy_migrate` is **also** insufficient: 13 tables are owned
by `postgres`, so even the dedicated migrate role cannot alter
`trial_sessions` or `admin_webhook_logs`. Schema changes therefore need a
superuser (or an ownership change — see "Recommended fix", not yet done).

## The supported migration path

**For an additive, nullable column (the common case):**

```bash
ssh -i ~/.ssh/styxproxy-interserver root@162.35.184.69
sudo -u postgres psql -d styxproxy
```

```sql
-- Always IF NOT EXISTS so a re-run is harmless, and never backfill:
-- a fabricated value is worse than NULL.
ALTER TABLE orders ADD COLUMN IF NOT EXISTS captured_at TIMESTAMP WITH TIME ZONE;
```

Then verify with a **real ORM query**, never an HTTP health probe:

```bash
cd /opt/styxproxy/backend
eval "$(grep -E '^Environment="' /etc/systemd/system/styxproxy-api.service \
  | sed -E 's/^Environment="(.*)"$/export \1/')"
./venv/bin/python scripts/schema_gate.py    # exit 0 = schema agrees
```

`OPS_JWT_SECRET` lives in the systemd unit's `Environment=` line, not in
`.env`, so the `eval` is required or `Settings` validation fails. Never
`source /opt/styxproxy/.env` — it contains unquoted values with commas and
spaces that choke the shell.

## Why `/health` returning 200 means nothing

On 2026-10-01 a deploy shipped six `orders` columns that production did not
have. Every orders query raised
`asyncpg.exceptions.UndefinedColumnError: column orders.captured_at does not
exist`, and `/api/v1/health` returned **200 for the entire duration**, because
that endpoint only runs `SELECT 1`.

`schema_gate.py` is the replacement signal. It diffs `Base.metadata` against
`information_schema` **and** issues a full-model `SELECT` per mapped class —
a full-model select is required because `select(TrialSession.id)` succeeds
while `select(TrialSession)` raises, so a narrow probe reports a broken table
as healthy.

`/api/v1/health` now also returns a `schema` block and reports
`status: unhealthy` on drift, but treat the gate as authoritative: it is the
thing that should run in CI/deploy.

## Adding a column: checklist

1. Add the nullable column to `app/models.py`.
2. Add an idempotent `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` to the
   startup list in `app/main.py` **and** write a migration file (for
   environments where alembic does work, e.g. CI).
3. Apply it on production as `postgres` (above).
4. Run `scripts/schema_gate.py` on production. Exit 0 required.
5. Only then consider the deploy complete.

## Recommended fix (not yet done)

Consolidate ownership so a migration path stops needing a superuser: transfer
the 13 `postgres`-owned tables to `styxproxy_migrate`, then make that role the
owner of every application table. That would let `styxproxy_migrate` apply
migrations without superuser, and would let the startup DDL path work for the
tables the app owns. This is a deliberate, reviewable schema change — it is
tracked on its own card rather than being done as a side effect of a deploy.