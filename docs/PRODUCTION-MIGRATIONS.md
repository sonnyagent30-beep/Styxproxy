# How schema reaches Styxproxy production

**Read this before adding a table or column.** The short version: **`models.py`
is authoritative. A migration alone will not reach production.**

## Why the migration chain is not the answer

Two independent facts, both verified 2026-10-01:

1. **`alembic upgrade head` cannot build a clean database.** It fails on the
   *first* revision. `001_initial` creates `orders` with foreign keys to tables
   it has not created yet:

   ```
   asyncpg.exceptions.UndefinedTableError: relation "bunche_credentials" does not exist
   ```

   So a fresh environment provisioned by migrations is broken before revision 2,
   whatever you add at the end of the chain.

2. **Production's alembic ledger is not truthful.** `alembic_version` is frozen
   at `merge_20260819_three_heads` (since 2026-08-19) and does not describe the
   actual schema. `deploy-backend.yml` runs `alembic upgrade heads` under
   `set +e ... | tail -20`, which discards both the exit code and the error text,
   so the failure has been silent on every deploy.

`docs/STAGING-WORKFLOW-PLAN.md` and `alembic/versions/` both describe an intent
that the running system does not implement. Trust the database, not the ledger.

## The path that actually works

`backend/app/main.py` lifespan, on every boot:

```python
async with engine.begin() as conn:
    await conn.run_sync(Base.metadata.create_all)
```

`create_all` creates any table in `Base.metadata` that does not exist and leaves
existing tables alone. **So an ORM model in `backend/app/models.py` is what
provisions a fresh environment.** Adding a migration on top is still worth doing
— it documents the schema and covers a migration-based restore — but it is not
load-bearing.

Verified on production 2026-10-01: the app connects as `styxproxy_app`, which
holds `CREATE` on schema `public`, so this path can create tables.

### Known trap: the startup ALTER loop does not work

`main.py` also runs `ALTER TABLE orders ADD COLUMN IF NOT EXISTS ...` on every
boot. It has **never succeeded**. The app connects as `styxproxy_app`, which does
not own `orders`, so Postgres rejects the first ALTER with `InsufficientPrivilege`
and the whole block is swallowed by `logger.warning("Orders column migration
skipped")` — indistinguishable from success in an aggregated log. Table ownership
is split across four roles (`styxproxy_migrate`, `postgres`, `styxproxy_app`,
`styxproxy_n8n`), so no single non-superuser role owns everything.

**Consequence:** for a table whose owner is *not* `styxproxy_app`, `create_all`
cannot create it either. `country_plan_types` happens to be owned by
`styxproxy_app`, so it is covered; check ownership before assuming.

```sql
SELECT relname, pg_get_userbyid(relowner) FROM pg_class WHERE relname = '<table>';
```

## Rules for a new table or column

1. Declare it in `backend/app/models.py`. This is what makes it exist.
2. Copy the schema from the live table. Do not design it — the live table is what
   production already serves traffic against. Compare with `\d+ <table>`, not
   `information_schema` (it drops the typmod and reports a bare `character varying`
   for a `varchar(2)`).
3. Declare index and constraint names explicitly. `create_all` will otherwise emit
   `ix_<table>_<column>` and leave production's names as a second, divergent set.
4. Add an idempotent migration (`CREATE TABLE IF NOT EXISTS` / `ADD COLUMN IF NOT
   EXISTS`) for migration-based restores. Append to the current single head; a
   second head makes `alembic upgrade head` refuse to run at all.
5. Do not write `DROP TABLE` in a `downgrade()`. A rollback must not become an
   outage.
6. Verify against a real database. `SELECT 1` proves nothing — a full-model
   `select(Model)` is what surfaces a missing column.

## Verifying a fresh environment

`create_all` against an empty database is the exact fresh-deploy scenario:

```bash
psql -c "CREATE DATABASE fresh_check;"
DATABASE_URL=postgresql+asyncpg://…@localhost/fresh_check python3 -c "
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from app.models import Base
async def m():
    e = create_async_engine('postgresql+asyncpg://…@localhost/fresh_check')
    async with e.begin() as c:
        await c.run_sync(Base.metadata.create_all)
    await e.dispose()
asyncio.run(m())"
psql -d fresh_check -c '\d country_plan_types'
```

`backend/tests/test_country_plan_types_postgres.py` does this as a test, and
`test_country_plan_types_schema.py` asserts the declared schema matches
production column for column.