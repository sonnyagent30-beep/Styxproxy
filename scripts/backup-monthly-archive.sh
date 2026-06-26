#!/bin/bash
# ============================================================
# Bunche — Monthly Archive (First Backup of Month)
# ============================================================
# Duplicates the first daily backup of each month to
# r2:bunche-backups/monthly/ for long-term (1 year) retention.
#
# Cron: 5 2 1 * * /usr/local/bin/backup-monthly-archive.sh >> /var/log/bunche-backup.log 2>&1
# (Runs at 02:05 on the 1st of each month — 5 min after daily backup completes)
# ============================================================

set -euo pipefail
CONFIG_FILE="/etc/bunche/backup.conf"
# shellcheck disable=SC1090
source "$CONFIG_FILE"

YEAR_MONTH=$(date +%Y-%m)
TODAY=$(date +%Y-%m-%d)

DAILY_FILE="${BACKUP_DIR}/bunche_${TODAY}.dump.age"

if [ ! -f "$DAILY_FILE" ]; then
  echo "[$(date)] FATAL: no daily backup found at $DAILY_FILE"
  exit 1
fi

echo "[$(date)] Archiving $DAILY_FILE → ${RCLONE_REMOTE//daily/monthly}/${YEAR_MONTH}/"

# Copy to monthly bucket (lifecycle: 365 day retention there)
rclone copy "$DAILY_FILE" \
  "${RCLONE_REMOTE//daily/monthly}/${YEAR_MONTH}/" \
  --log-level=INFO \
  --stats=30s

echo "[$(date)] Monthly archive complete ✓"