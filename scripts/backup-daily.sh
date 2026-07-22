#!/bin/bash
# ============================================================
# Styxproxy — Daily Backup Script
# ============================================================
# Runs: 0 3 * * * (every day at 3am)
#
# What it does:
#   1. pg_dump the styxproxy database (custom format, compressed)
#   2. Restic backup with 'daily' tag to B2
#   3. Prune B2 snapshots: keep last 30 daily snapshots (30 days)
#
# Cron: 0 3 * * * /usr/local/bin/backup-daily.sh >> /var/log/styxproxy-backup.log 2>&1
#
# Config: /etc/styxproxy/backup.conf
#   POSTGRES_USER, POSTGRES_DB
#   RESTIC_PASSWORD
#
# Note: Also keep hourly snapshots (from backup-hourly.sh).
#   This daily script creates a longer-retention tag for
#   situations where you need to restore from a specific day.
# ============================================================

set -euo pipefail

CONFIG_FILE="/etc/styxproxy/backup.conf"
if [ ! -f "$CONFIG_FILE" ]; then
    echo "[$(date)] FATAL: $CONFIG_FILE not found" >&2
    exit 1
fi
# shellcheck disable=SC1090
source "$CONFIG_FILE"

BACKUP_DIR="/backup/styxproxy/dumps"
mkdir -p "$BACKUP_DIR"

DATE=$(date +%Y%m%d)
DUMP_FILE="${BACKUP_DIR}/styxproxy_daily_${DATE}.dump"

echo "[$(date)] Starting daily backup..."

# 1. pg_dump
echo "[$(date)] pg_dump → ${DUMP_FILE}"
pg_dump \
    --username="${POSTGRES_USER}" \
    --dbname="${POSTGRES_DB}" \
    --format=custom \
    --compress=9 \
    --no-owner \
    --no-privileges \
    --file="$DUMP_FILE"

DUMP_SIZE=$(stat -c%s "$DUMP_FILE")
echo "[$(date)] Dump size: $((DUMP_SIZE / 1024 / 1024))MB"

# 2. Restic backup with daily tag
echo "[$(date)] Restic backup (daily) → B2..."
export RESTIC_PASSWORD="${RESTIC_PASSWORD}"
restic backup \
    "$DUMP_FILE" \
    --repo "b2:styxproxy-backups" \
    --tag daily \
    --tag "date=${DATE}"

echo "[$(date)] Restic daily backup complete ✓"

# 3. Prune old daily snapshots (keep last 30 days)
echo "[$(date)] Pruning B2 daily snapshots (keep last 30)..."
restic forget \
    --repo "b2:styxproxy-backups" \
    --keep-daily 30 \
    --prune

DAILY_COUNT=$(restic snapshots --repo "b2:styxproxy-backups" --tag daily 2>/dev/null | grep -c "daily" || echo "0")
echo "[$(date)] Current daily snapshots in B2: $DAILY_COUNT"

echo "[$(date)] Daily backup complete ✓"
echo "---"
