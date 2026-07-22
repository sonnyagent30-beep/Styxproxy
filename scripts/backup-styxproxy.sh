#!/bin/bash
# ============================================================
# Styxproxy — Daily PostgreSQL Backup
# ============================================================
# Usage: backup-styxproxy.sh [--verify]
#
# What it does:
#   1. pg_dump the styxproxy database (compressed custom format)
#   2. Encrypt with age using the Styxproxy backup public key
#   3. Upload to Cloudflare R2 via rclone
#   4. Delete local backups older than 7 days
#   5. Alert admin via n8n webhook if backup size changed >50%
#      from 7-day average (suggests something wrong)
#
# Cron: 0 2 * * * /usr/local/bin/backup-styxproxy.sh >> /var/log/styxproxy-backup.log 2>&1
#
# Config: /etc/styxproxy/backup.conf
#   POSTGRES_USER, POSTGRES_DB, POSTGRES_HOST
#   BACKUP_DIR, BACKUP_PUBLIC_KEY
#   RCLONE_REMOTE (e.g. "r2:styxproxy-backups/daily")
#   ALERT_WEBHOOK_URL
#   RETENTION_DAYS_LOCAL
# ============================================================

set -euo pipefail

CONFIG_FILE="/etc/styxproxy/backup.conf"
if [ ! -f "$CONFIG_FILE" ]; then
  echo "FATAL: $CONFIG_FILE not found" >&2
  exit 1
fi
# shellcheck disable=SC1090
source "$CONFIG_FILE"

DATE=$(date +%Y-%m-%d)
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/styxproxy_${DATE}.dump"
BACKUP_FILE_ENC="${BACKUP_FILE}.age"

# Ensure backup dir exists
mkdir -p "$BACKUP_DIR"

echo "[$(date)] Starting backup..."

# 1. Dump database
echo "[$(date)] pg_dump → ${BACKUP_FILE}"
pg_dump \
  --host="$POSTGRES_HOST" \
  --username="$POSTGRES_USER" \
  --dbname="$POSTGRES_DB" \
  --format=custom \
  --compress=9 \
  --no-owner \
  --no-privileges \
  --file="$BACKUP_FILE"

DUMP_SIZE=$(stat -c%s "$BACKUP_FILE")
echo "[$(date)] Dump size: $((DUMP_SIZE / 1024 / 1024))MB"

# 2. Encrypt with age
echo "[$(date)] Encrypting → ${BACKUP_FILE_ENC}"
age --recipient="$BACKUP_PUBLIC_KEY" --output="$BACKUP_FILE_ENC" "$BACKUP_FILE"
# Remove unencrypted file
rm -f "$BACKUP_FILE"
shred -u "$BACKUP_FILE" 2>/dev/null || rm -f "$BACKUP_FILE"

ENC_SIZE=$(stat -c%s "$BACKUP_FILE_ENC")
echo "[$(date)] Encrypted size: $((ENC_SIZE / 1024 / 1024))MB"

# 3. Upload to R2
echo "[$(date)] Uploading to ${RCLONE_REMOTE}/${DATE}/"
rclone copy "$BACKUP_FILE_ENC" "${RCLONE_REMOTE}/${DATE}/" \
  --log-level=INFO \
  --stats=30s

# 4. Delete local backups older than retention
echo "[$(date)] Cleaning local backups older than ${RETENTION_DAYS_LOCAL} days"
find "$BACKUP_DIR" -name "styxproxy_*.dump.age" -mtime +"$RETENTION_DAYS_LOCAL" -delete

# 5. Verify mode — restore to a temp file and check it's valid PostgreSQL
if [ "${1:-}" = "--verify" ]; then
  echo "[$(date)] VERIFY MODE — restoring to temp"
  TEMP_DUMP="/tmp/styxproxy_verify_$$.dump"
  age --decrypt --output="$TEMP_DUMP" "$BACKUP_FILE_ENC"

  # Spin up a throwaway Postgres container, restore, sanity check
  docker run --rm -d --name styxproxy-verify \
    -e POSTGRES_PASSWORD=verify \
    -e POSTGRES_DB=styxproxy \
    postgres:16 >/dev/null

  sleep 10  # Wait for postgres to be ready

  docker exec styxproxy-verify pg_restore \
    --username=postgres \
    --dbname=styxproxy \
    --no-owner \
    --no-privileges \
    < "$TEMP_DUMP" 2>/dev/null || true

  CUSTOMER_COUNT=$(docker exec styxproxy-verify psql -U postgres -d styxproxy -tA \
    -c "SELECT COUNT(*) FROM customers" 2>/dev/null || echo "0")

  ORDER_COUNT=$(docker exec styxproxy-verify psql -U postgres -d styxproxy -tA \
    -c "SELECT COUNT(*) FROM orders" 2>/dev/null || echo "0")

  docker stop styxproxy-verify >/dev/null 2>&1 || true
  rm -f "$TEMP_DUMP"

  echo "[$(date)] VERIFY: customers=$CUSTOMER_COUNT orders=$ORDER_COUNT"

  if [ "$CUSTOMER_COUNT" = "0" ] || [ "$ORDER_COUNT" = "0" ]; then
    echo "[$(date)] WARNING: verification restored empty tables" >&2
  fi
fi

# 6. Size sanity check (compare to 7-day average)
echo "[$(date)] Checking backup size vs 7-day average"
AVG_SIZE=$(find "$BACKUP_DIR" -name "styxproxy_*.dump.age" -mtime -7 \
  -exec stat -c%s {} \; | awk '{sum+=$1; count++} END {if(count>0) print int(sum/count); else print 0}')

if [ "$AVG_SIZE" -gt 0 ]; then
  RATIO=$(awk "BEGIN {printf \"%.0f\", ($ENC_SIZE * 100) / $AVG_SIZE}")
  echo "[$(date)] Current/avg ratio: ${RATIO}%"

  if [ "$RATIO" -lt 50 ] || [ "$RATIO" -gt 200 ]; then
    echo "[$(date)] WARNING: backup size outside ±50% of average" >&2
    if [ -n "${ALERT_WEBHOOK_URL:-}" ]; then
      curl -sS -X POST "$ALERT_WEBHOOK_URL" \
        -H "Content-Type: application/json" \
        -d "{\"severity\":\"high\",\"source\":\"backup\",\"message\":\"Backup size is ${RATIO}% of 7-day average. Encrypted: ${ENC_SIZE} bytes. Investigate.\"}" \
        || true
    fi
  fi
fi

echo "[$(date)] Backup complete ✓"