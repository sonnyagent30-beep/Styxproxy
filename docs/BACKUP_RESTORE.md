# Backup & Restore — Styxproxy

## Backup Inventory

| Backup | Frequency | Local Retention | B2 Retention |
|---|---|---|---|
| pg_basebackup (tar.gz) | Weekly Sunday 04:00 UTC | 7 days | 30 days |
| pg_dump (SQL.gz) | Daily 02:00 UTC | 30 days | 30 days |
| WAL archiving | Continuous | — | 3 days |
| Verify restore | Weekly Monday 06:00 UTC | — | — |

Scripts:
- 
- 
- 
- 

B2 bucket: 
-  — weekly tar backups
-  — daily SQL dumps
-  — WAL archives

## Restoring from pg_dump (SQL)

### From B2
```bash
DATE=20260809
rclone copy "b2-styxproxy:styxproxy-backups/pg_dump/styxproxy-${DATE}.sql.gz" /tmp/
gunzip < /tmp/styxproxy-${DATE}.sql.gz | sudo -u postgres psql -d styxproxy
```

### From local
```bash
DATE=20260809
gunzip < /opt/styxproxy/backups/pg_dump/styxproxy-${DATE}.sql.gz | sudo -u postgres psql -d styxproxy
```

## RTO & RPO

- **RTO**: ~15 min (pg_dump restore)
- **RPO**: Last pg_dump = up to 24 hours ago
- **WAL PITR**: < 1 hour RPO where WAL archiving is running

## Emergency

Check  and .
Notify: POST /_ops/v1/alert with ops JWT.
