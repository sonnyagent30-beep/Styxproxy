# PITR (Point-In-Time Recovery) Setup — Theme C

**Status (Jul 28 2026):** Configured but B2 sync is degraded. README below.

## What is PITR?

PITR lets us restore the DB to any point in time within the WAL retention window. It needs two things:

1. **WAL archive** — every completed WAL segment is copied out of `pg_wal/` to a safe location
2. **Base backup** — a periodic full snapshot of the cluster that the WAL can be replayed against

With both in place, we can restore to any second in the last `wal_keep_size` worth of WAL (currently 5GB ≈ 5-7 days of normal traffic).

## Current configuration

### Postgres (`/etc/postgresql/16/main/conf.d/01-pitr-wal-archive.conf`)

```
wal_level = replica           # already default
archive_mode = on             # was 'off'
archive_command = 'cp %p /var/lib/postgresql/wal-archive/%f && echo "archived %f at $(date -Iseconds)" >> /var/log/pitr-wal-archive.log'
archive_timeout = 300         # 5 minutes — force WAL switch
wal_keep_size = 5GB           # keep 5GB WAL locally for safety
```

### Scripts

- `/usr/local/bin/sync_wal_to_b2.sh` — runs every 15 min, syncs `/var/lib/postgresql/wal-archive/` → B2
- `/usr/local/bin/weekly_pg_basebackup.sh` — runs Sundays 04:00 UTC, takes a fresh base backup

### Cron

```
*/15 * * * * /usr/local/bin/sync_wal_to_b2.sh
0 4 * * 0 /usr/local/bin/weekly_pg_basebackup.sh
```

### Logs

- `/var/log/pitr-wal-archive.log` — one line per archived WAL segment
- `/var/log/pitr-wal-sync.log` — sync attempts to B2
- `/var/log/pitr-pgbase.log` — base backup runs

## KNOWN ISSUE: B2 sync failing from Interserver (Jul 28 22:00)

**Root cause (fully diagnosed):** The B2 application key is **read-only or expired**. Listing works, writing fails with 401.

The initial "API version number 1 (400 bad_request)" error was a red herring — caused by rclone v1.69.0 being too old. Upgraded to v1.74.4 made listing work, but writing still fails.

**Action required:** See `B2_KEY_BROKEN.md` for replacement steps. This is a HUMAN task.

**Impact:** WAL files archived locally only. Local retention 14d WAL + 7d base backups on SAME disk — if Interserver disk dies, we lose everything.

## How to restore from PITR

(TODO — write the actual restore procedure once B2 sync is fixed. For now, see Postgres docs: https://www.postgresql.org/docs/16/continuous-archiving.html)

### Quick checklist (after B2 sync is working)

- [ ] Add restore procedure to RUNBOOKS.md §11
- [ ] Test restore in staging (not against prod)
- [ ] Document the drill schedule
