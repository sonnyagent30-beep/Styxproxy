# 🔴 B2 key broken — Action required

**Status (Jul 28 22:00 UTC):** The B2 application key `K003XGQO2AlOcFFABX9FUFrmcuPZNyI` (kid `003adb5d87d19930000000006`) is **read-only or expired**. Listing the bucket works, but writing fails with 401 unauthorized.

**This blocks:** PITR from being backed up to B2, `pg_basebackup` from being backed up to B2, pg_dump backup cron from working.

**Every other part of the pipeline is wired correctly:**
- ✅ rclone v1.74.4 installed on Interserver (newer than the v1.69.0 originally installed — that was the visible "API version 1" error)
- ✅ `/usr/local/bin/sync_wal_to_b2.sh` runs every 15 min via cron
- ✅ `/usr/local/bin/weekly_pg_basebackup.sh` runs Sundays 04:00 UTC
- ✅ Cron logs failures to `/var/log/pitr-wal-sync.log` and `/var/log/pitr-pgbase.log`
- ✅ Scripts degrade gracefully (log + continue, don't crash)
- ✅ Local WAL staging at `/var/lib/postgresql/wal-archive/` (14d retention)
- ✅ Local base backups at `/opt/styxproxy/backups/pg_basebackup/` (7d retention)

## How to fix

1. **Log into B2 dashboard** (https://secure.backblaze.com/b2_buckets.htm)
2. **App Keys** → Create new key
3. **Bucket:** select `styxproxy-backups`
4. **Capabilities:** Read + Write + Delete + List (full access, scoped to the bucket)
5. **Save the new key** (it will only be shown ONCE)
6. Replace the key on **both** hosts:
   - Contabo: `/root/.config/rclone/rclone.conf` → `[b2-styxproxy] key = K003...`
   - Interserver: same file (was installed by this session)
7. Test: `rclone copy /tmp/test.txt b2-styxproxy:styxproxy-backups/ && rclone ls b2-styxproxy:styxproxy-backups/`

## Temporary mitigation

Until the key is rotated, local retention is the only safety net:
- Postgres WAL archived locally for 14 days → can replay up to 14 days of changes via `pg_basebackup` + WAL replay (if both live on the same disk that survives)
- Weekly base backups kept 7 days → can do PITR if a recent base backup survives

**If Interserver's disk dies right now, we lose everything** because the backups are on the same disk. This is the imminent risk.
