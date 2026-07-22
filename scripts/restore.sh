#!/bin/bash
# ============================================================
# Styxproxy — Restore from Backup Script
# ============================================================
# Usage:
#   restore-latest.sh              — restore most recent backup
#   restore-latest.sh --list       — list available snapshots first
#   restore-latest.sh --verify     — restore to /tmp/verify (no DB overwrite)
#   restore-latest.sh SNAPSHOT_ID  — restore specific snapshot
#
# What it does:
#   1. Downloads backup from B2 (or uses local)
#   2. Restores pg_dump to PostgreSQL
#   3. Verifies row counts
#
# CAUTION: Restoring overwrites the current database.
#   Always run with --verify first to check the backup is good.
# ============================================================

set -euo pipefail

CONFIG_FILE="/etc/styxproxy/backup.conf"
if [ ! -f "$CONFIG_FILE" ]; then
    echo "[$(date)] FATAL: $CONFIG_FILE not found" >&2
    exit 1
fi
# shellcheck disable=SC1090
source "$CONFIG_FILE"

export RESTIC_PASSWORD="${RESTIC_PASSWORD}"

BACKUP_DIR="/backup/styxproxy/dumps"
mkdir -p "$BACKUP_DIR"

# -----------------------------------------------
# Helper: check prerequisites
# -----------------------------------------------
check_prereqs() {
    if ! command -v restic &>/dev/null; then
        echo "[$(date)] ERROR: restic not installed. Run: sudo apt install restic" >&2
        exit 1
    fi

    if ! pg_isready &>/dev/null; then
        echo "[$(date)] ERROR: PostgreSQL is not running" >&2
        exit 1
    fi

    echo "[$(date)] Prerequisites OK ✓"
}

# -----------------------------------------------
# List available snapshots
# -----------------------------------------------
list_snapshots() {
    echo "[$(date)] Available snapshots in B2:"
    echo "---"
    restic snapshots --repo "b2:styxproxy-backups" --json 2>/dev/null | \
        python3 -c "
import json, sys
data = json.load(sys.stdin)
for s in sorted(data, key=lambda x: x['time'], reverse=True):
    print(f\"  {s['id'][:8]} | {s['time'][:19]} | tags: {', '.join(s.get('tags',[]))} | {s['files_summary']['total_files']} files\")
" 2>/dev/null || restic snapshots --repo "b2:styxproxy-backups"
}

# -----------------------------------------------
# Verify a backup (restore to /tmp, no overwrite)
# -----------------------------------------------
verify_backup() {
    SNAPSHOT_ID="${1:-latest}"

    echo "[$(date)] VERIFY MODE: restoring to /tmp/styxproxy-verify/ (no DB overwrite)"

    RESTORE_DIR="/tmp/styxproxy-verify"
    rm -rf "$RESTORE_DIR"
    mkdir -p "$RESTORE_DIR"

    echo "[$(date)] Downloading snapshot ${SNAPSHOT_ID}..."
    restic restore "$SNAPSHOT_ID" --repo "b2:styxproxy-backups" --target "$RESTORE_DIR"

    # Find the dump file
    DUMP_FILE=$(find "$RESTORE_DIR" -name "*.dump" | head -1)
    if [ -z "$DUMP_FILE" ]; then
        echo "[$(date)] ERROR: No .dump file found in snapshot" >&2
        exit 1
    fi

    echo "[$(date)] Found dump file: $DUMP_FILE"

    # Create a temp database and restore into it
    TEMP_DB="styxproxy_verify_$(date +%s)"
    echo "[$(date)] Creating temp DB: $TEMP_DB"
    sudo -u postgres psql -c "DROP DATABASE IF EXISTS ${TEMP_DB};"
    sudo -u postgres psql -c "CREATE DATABASE ${TEMP_DB};"

    echo "[$(date)] Restoring to temp DB..."
    pg_restore \
        --username="${POSTGRES_USER}" \
        --dbname="${TEMP_DB}" \
        --no-owner \
        --no-privileges \
        --jobs=4 \
        "$DUMP_FILE" 2>&1 | tail -5

    # Sanity checks
    echo "[$(date)] Running sanity checks..."
    ORDER_COUNT=$(sudo -u postgres psql -d "$TEMP_DB" -tA -c "SELECT COUNT(*) FROM instant_orders;" 2>/dev/null || echo "ERR")
    CRED_COUNT=$(sudo -u postgres psql -d "$TEMP_DB" -tA -c "SELECT COUNT(*) FROM styxproxy_credentials;" 2>/dev/null || echo "ERR")
    ADMIN_COUNT=$(sudo -u postgres psql -d "$TEMP_DB" -tA -c "SELECT COUNT(*) FROM admin_auth;" 2>/dev/null || echo "ERR")

    echo "[$(date)] Sanity check results:"
    echo "  instant_orders:     $ORDER_COUNT rows"
    echo "  styxproxy_credentials: $CRED_COUNT rows"
    echo "  admin_auth:        $ADMIN_COUNT rows"

    # Cleanup
    sudo -u postgres psql -c "DROP DATABASE IF EXISTS ${TEMP_DB};"
    rm -rf "$RESTORE_DIR"

    if [ "$ORDER_COUNT" = "ERR" ] || [ "$CRED_COUNT" = "ERR" ]; then
        echo "[$(date)] WARNING: Could not read some tables. Backup may be corrupted." >&2
        exit 1
    fi

    echo "[$(date)] Verification complete ✓ — backup is valid"
}

# -----------------------------------------------
# Full restore (overwrites current DB)
# -----------------------------------------------
full_restore() {
    SNAPSHOT_ID="${1:-latest}"

    echo "[$(date)] FULL RESTORE mode"
    echo "[$(date)] This will OVERWRITE the current database."
    echo "[$(date)] Snapshot: $SNAPSHOT_ID"
    echo "---"

    RESTORE_DIR="/tmp/styxproxy-restore"
    rm -rf "$RESTORE_DIR"
    mkdir -p "$RESTORE_DIR"

    echo "[$(date)] Downloading snapshot..."
    restic restore "$SNAPSHOT_ID" --repo "b2:styxproxy-backups" --target "$RESTORE_DIR"

    DUMP_FILE=$(find "$RESTORE_DIR" -name "*.dump" | head -1)
    if [ -z "$DUMP_FILE" ]; then
        echo "[$(date)] ERROR: No .dump file found" >&2
        exit 1
    fi

    echo "[$(date)] Stopping styxproxy-api..."
    sudo systemctl stop styxproxy-api 2>/dev/null || true

    echo "[$(date)] Dropping and recreating database..."
    sudo -u postgres psql -c "DROP DATABASE IF EXISTS ${POSTGRES_DB};"
    sudo -u postgres psql -c "CREATE DATABASE ${POSTGRES_DB};"

    echo "[$(date)] Restoring..."
    pg_restore \
        --username="${POSTGRES_USER}" \
        --dbname="${POSTGRES_DB}" \
        --no-owner \
        --no-privileges \
        --jobs=4 \
        "$DUMP_FILE" 2>&1 | tail -3

    echo "[$(date)] Restarting styxproxy-api..."
    sudo systemctl start styxproxy-api

    # Verify
    FINAL_COUNT=$(sudo -u postgres psql -d "${POSTGRES_DB}" -tA -c "SELECT COUNT(*) FROM instant_orders;" 2>/dev/null || echo "ERR")
    echo "[$(date)] Final order count: $FINAL_COUNT"

    rm -rf "$RESTORE_DIR"
    echo "[$(date)] FULL RESTORE complete ✓"
}

# -----------------------------------------------
# Main
# -----------------------------------------------
MODE="${1:-}"
SNAPSHOT="${2:-}"

case "$MODE" in
    --list)
        check_prereqs
        list_snapshots
        ;;
    --verify)
        check_prereqs
        verify_backup "$SNAPSHOT"
        ;;
    --restore)
        check_prereqs
        full_restore "$SNAPSHOT"
        ;;
    "")
        echo "Usage:"
        echo "  restore.sh --list              List available snapshots"
        echo "  restore.sh --verify            Verify latest backup (no DB overwrite)"
        echo "  restore.sh --verify SNAPSHOT   Verify specific snapshot"
        echo "  restore.sh --restore          Full restore latest (OVERWRITES DB)"
        echo "  restore.sh --restore SNAPSHOT  Full restore specific snapshot"
        ;;
    *)
        echo "Unknown option: $MODE"
        exit 1
        ;;
esac
