#!/bin/bash
# ============================================================
# Styxproxy — Hourly Backup Script
# ============================================================
# Runs: 0 * * * * (every hour at :00)
#
# What it does:
#   1. pg_dump the styxproxy database (custom format, compressed)
#   2. Restic backup to Backblaze B2 (deduplication = only changed blocks uploaded)
#   3. Delete local dumps older than 6 hours
#   4. Prune B2 snapshots: keep last 72 hourly snapshots (3 days)
#
# Cron: 0 * * * * /usr/local/bin/backup-hourly.sh >> /var/log/styxproxy-backup.log 2>&1
#
# Config: /etc/styxproxy/backup.conf
#   POSTGRES_USER, POSTGRES_DB
#   RESTIC_PASSWORD (repo encryption key — store in 1Password)
#   RCLONE_REMOTE=b2
#
# Prerequisites:
#   - Backblaze B2 account (free tier: 5GB)
#   - rclone configured with 'b2' remote
#   - Restic repo initialized: restic -r b2:styxproxy-backups init
#   - /backup/styxproxy/dumps/ directory exists
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

DATE=$(date +%Y%m%d_%H00)
DUMP_FILE="${BACKUP_DIR}/styxproxy_${DATE}.dump"

echo "[$(date)] Starting hourly backup..."

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

# 2. Restic backup (deduplication = only changed blocks uploaded)
echo "[$(date)] Restic backup → B2 (dedup)..."
export RESTIC_PASSWORD="${RESTIC_PASSWORD}"
restic backup \
    "$DUMP_FILE" \
    --repo "b2:styxproxy-backups" \
    --tag hourly \
    --tag "date=${DATE}"

echo "[$(date)] Restic backup complete ✓"

# 3. Delete local dumps older than 6 hours
echo "[$(date)] Cleaning local dumps older than 6 hours..."
find "$BACKUP_DIR" -name "*.dump" -mmin +360 -delete
echo "[$(date)] Local cleanup complete"

# 4. Prune old B2 snapshots (keep last 72 hourly = 3 days)
echo "[$(date)] Pruning B2 snapshots (keep last 72 hourly)..."
restic forget \
    --repo "b2:styxproxy-backups" \
    --keep-hourly 72 \
    --prune

SNAPSHOT_COUNT=$(restic snapshots --repo "b2:styxproxy-backups" --tag hourly 2>/dev/null | grep -c "hourly" || echo "0")
echo "[$(date)] Current hourly snapshots in B2: $SNAPSHOT_COUNT"

echo "[$(date)] Hourly backup complete ✓"
echo "---"
