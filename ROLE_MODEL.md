# Database Role Model — Theme C closure

Three Postgres roles, three distinct purposes:

| Role | Created | Permissions | Used by |
|---|---|---|---|
|  | Initial cluster | SUPERUSER, CREATEDB, CREATEROLE, BYPASSRLS | Emergency repair only |
|  | Jul 22 era | NOSUPERUSER, all DML on tables, NO schema perms | API app (DATABASE_URL user) |
|  | Jul 29 (migration 016) | NOSUPERUSER, CREATE on schema, owns all tables | Migration scripts (db-migrate.py default) |

## Why three roles?

**Defense in depth.** A bug in a migration script can run as  (escape hatch to the whole DB) or as  (can break schema but cannot  or ). Picking the middle role means most migration bugs can only corrupt the schema, not the whole server.

## How migrations work now

Default invocation:


Override to superuser (only for emergencies):


## Reversibility

If styxproxy_migrate causes problems:


That moves all 23 owned tables back to styxproxy. App behavior unchanged (styxproxy has all DML perms regardless of who owns the tables).

## Files

- Migration 016:  — creates role + transfers ownership
- Migration 016b:  — re-grants styxproxy perms after REASSIGN OWNED BY
- Script:  — defaults to styxproxy_migrate, falls back to sudo -u postgres on override
- Env:  in  (chmod 644 for postgres user readability)
