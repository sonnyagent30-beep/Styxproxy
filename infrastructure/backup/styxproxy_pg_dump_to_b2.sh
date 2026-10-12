#!/usr/bin/env bash
# styxproxy_pg_dump_to_b2.sh
# Daily Postgres dump → gzip → age-encrypt → local backup dir → rclone sync to B2
# Cron: 5 3 * * *  (3:05 AM UTC daily)
# Log: /var/log/styxproxy-pgdump.log

set -euo pipefail

# Load env (B2 creds, backup passphrase)
ENV_FILE="/root/.hermes/.env"
if [ ! -f "$ENV_FILE" ]; then
    echo "[FATAL] $ENV_FILE missing" >&2
    exit 1
fi
set -a; source "$ENV_FILE"; set +a

# Verify required vars present
for v in B2_KEY_ID B2_APPLICATION_KEY B2_BUCKET B2_PATH_PREFIX BACKUP_PASSPHRASE; do
    if [ -z "${!v:-}" ]; then
        echo "[FATAL] $v not set in env" >&2
        exit 1
    fi
done

# Config
LOCAL_BACKUP_DIR="/root/backups/styxproxy-pg"
LOCAL_RETENTION_DAYS=30
TIMESTAMP=$(date -u +"%Y-%m-%dT%H-%M-%SZ")
DATE_STAMP=$(date -u +"%Y-%m-%d")
DUMP_FILE="styxproxy_pgdump_${TIMESTAMP}.sql.gz"
DUMP_PATH="${LOCAL_BACKUP_DIR}/${DUMP_FILE}"
ENCRYPTED_PATH="${DUMP_PATH}.age"
LOG_PREFIX="[$(date -u +'%Y-%m-%dT%H:%M:%SZ')] pg_dump"

mkdir -p "$LOCAL_BACKUP_DIR"

log() { echo "${LOG_PREFIX} $*" | tee -a /var/log/styxproxy-pgdump.log; }
log "=== Starting backup run ==="

# 1. pg_dump from Interserver (Postgres 16, host-native per MEMORY)
# Host-native postgres uses peer auth, so run as postgres user via sudo
log "Step 1: pg_dump from Interserver (host-native postgres)"

# Stream ssh | sudo | pg_dump | gzip atomically; check exit code of FIRST stage (ssh+sudo+pg_dump)
unset PGUSER PGHOST PGPORT
ssh -i ~/.ssh/styxproxy-interserver root@162.35.184.69 \
    "sudo -u postgres pg_dump --no-owner --no-privileges --clean --if-exists styxproxy" \
    2>>/var/log/styxproxy-pgdump.log | gzip -9 > "$DUMP_PATH"

# Verify pg_dump actually produced non-empty SQL (gzip of empty stream = 20-byte gzip header)
DUMP_SIZE=$(stat -c%s "$DUMP_PATH" 2>/dev/null || echo 0)
if [ "$DUMP_SIZE" -lt 100 ]; then
    log "[FATAL] pg_dump produced empty or tiny file ($DUMP_SIZE bytes)"
    rm -f "$DUMP_PATH"
    exit 2
fi
SIZE=$(du -h "$DUMP_PATH" | cut -f1)
log "  dump size: ${SIZE} (${DUMP_SIZE} bytes)"

# 2. Encrypt with age (key-based, no TTY needed)
# Generated via `age-keygen` → stores X25519 keypair in /root/.hermes/keys/age-backup.key
# Public key (recipient): age1qdr39xzhurz58eg79n3uyumyq7enzps2mcmd30pxyycpxjamfahqpu636d
# Restore command: age -d -i /root/.hermes/keys/age-backup.key backup.age
AGE_RECIPIENT="age1qdr39xzhurz58eg79n3uyumyq7enzps2mcmd30pxyycpxjamfahqpu636d"
AGE_KEY_FILE="/root/.hermes/keys/age-backup.key"
if [ ! -f "$AGE_KEY_FILE" ]; then
    log "[FATAL] age keyfile missing: $AGE_KEY_FILE"
    exit 3
fi

log "Step 2: age-encrypt to recipient"
age -r "$AGE_RECIPIENT" -o "$ENCRYPTED_PATH" < "$DUMP_PATH" 2>>/var/log/styxproxy-pgdump.log
if [ ! -s "$ENCRYPTED_PATH" ]; then
    log "[FATAL] age encryption failed"
    exit 3
fi
ENCRYPT_SIZE=$(du -h "$ENCRYPTED_PATH" | cut -f1)
log "  encrypted size: $ENCRYPT_SIZE"

# 3. SHRED plaintext dump (don't leave it on disk)
log "Step 3: shred plaintext dump"
shred -u -z "$DUMP_PATH" 2>>/var/log/styxproxy-pgdump.log || rm -f "$DUMP_PATH"

# 4. Upload to B2
log "Step 4: rclone copyto to B2"
B2_DEST="${B2_PATH_PREFIX}${DATE_STAMP}_${DUMP_FILE}.age"
rclone copyto "$ENCRYPTED_PATH" "b2-styxproxy:${B2_BUCKET}/${B2_DEST}" \
    --progress=false \
    --retries=3 \
    --low-level-retries=5 \
    2>>/var/log/styxproxy-pgdump.log

log "  uploaded to ${B2_BUCKET}/${B2_DEST}"

# 5. Verify upload
log "Step 5: verify upload"
if rclone ls "b2-styxproxy:${B2_BUCKET}/${B2_PATH_PREFIX}" 2>>/var/log/styxproxy-pgdump.log | grep -q "$(basename "$ENCRYPTED_PATH")"; then
    log "  ✓ upload verified"
else
    log "[FATAL] upload verification failed"
    exit 4
fi

# 6. Rotate local backups (keep last LOCAL_RETENTION_DAYS days)
log "Step 6: rotate local backups (retention: ${LOCAL_RETENTION_DAYS} days)"
find "$LOCAL_BACKUP_DIR" -name "*.age" -mtime +${LOCAL_RETENTION_DAYS} -delete \
    2>>/var/log/styxproxy-pgdump.log
LOCAL_COUNT=$(find "$LOCAL_BACKUP_DIR" -name "*.age" | wc -l)
log "  local backups remaining: $LOCAL_COUNT"

# 7. Rotate B2 backups (delete anything older than 30 days)
log "Step 7: rotate B2 backups (retention: 30 days)"
CUTOFF_DATE=$(date -u -d "30 days ago" +"%Y-%m-%d" 2>/dev/null || date -u -v-30d +"%Y-%m-%d")
rclone delete "b2-styxproxy:${B2_BUCKET}/${B2_PATH_PREFIX}" \
    --min-age 30d \
    2>>/var/log/styxproxy-pgdump.log || log "  (B2 retention cleanup failed, will retry next run)"

# Summary
B2_COUNT=$(rclone ls "b2-styxproxy:${B2_BUCKET}/${B2_PATH_PREFIX}" 2>/dev/null | wc -l)
log "=== Backup complete. Local: $LOCAL_COUNT files. B2: $B2_COUNT files. ==="

# Optional: send Telegram notification
if [ -n "${TELEGRAM_BOT_TOKEN:-}" ] && [ -n "${TELEGRAM_DANNION_CHAT_ID:-}" ]; then
    MESSAGE="✅ Styxproxy pg_dump: ${DATE_STAMP} (${ENCRYPT_SIZE}) local=$LOCAL_COUNT b2=$B2_COUNT"
    curl -s -m 5 -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
        -d "chat_id=${TELEGRAM_DANNION_CHAT_ID}" \
        -d "text=${MESSAGE}" \
        >/dev/null 2>&1 || true
fi
