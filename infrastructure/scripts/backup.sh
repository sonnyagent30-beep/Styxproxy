#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────
# Styxproxy — Daily Encrypted Backup
# Schedule via cron:
#   0 2 * * * /opt/styxproxy/infrastructure/scripts/backup.sh >> /var/log/styxproxy-backup.log 2>&1
# ─────────────────────────────────────────────────────────

set -euo pipefail

COMPOSE_FILE="${COMPOSE_FILE:-/opt/styxproxy/infrastructure/docker-compose.yml}"
BACKUP_DIR="${BACKUP_DIR:-/opt/styxproxy/backups}"
RETENTION_DAYS="${RETENTION_DAYS:-14}"
ENCRYPTION_KEY="${BACKUP_ENCRYPTION_KEY:-}"
DESTINATION="${DESTINATION:-}"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="styxproxy_backup_${TIMESTAMP}"
BACKUP_PATH="${BACKUP_DIR}/${BACKUP_NAME}"

# ── Pre-flight checks ─────────────────────────────────────
if [[ ! -f "$COMPOSE_FILE" ]]; then
  echo "[ERROR] docker-compose.yml not found at $COMPOSE_FILE"
  exit 1
fi

mkdir -p "$BACKUP_DIR"

if [[ -z "$ENCRYPTION_KEY" ]]; then
  echo "[WARN] BACKUP_ENCRYPTION_KEY not set — backup will NOT be encrypted"
fi

echo "[$(date)] Starting backup: $BACKUP_NAME"

# ── Step 1: PostgreSQL dump ────────────────────────────────
CONTAINER=$(docker compose -f "$COMPOSE_FILE" ps -q postgres 2>/dev/null || true)
if [[ -z "$CONTAINER" ]]; then
  echo "[ERROR] Postgres container not running"
  exit 1
fi

PG_DUMP_PATH="${BACKUP_PATH}_pg.sql"
docker exec "$CONTAINER" pg_dump -U styxproxy -d styxproxy --no-owner --no-acl \
  > "$PG_DUMP_PATH"

echo "[OK] PostgreSQL dump: $(wc -c < "$PG_DUMP_PATH") bytes"

# ── Step 2: Redis dump ────────────────────────────────────
REDIS_DUMP_PATH=""
CONTAINER_REDIS=$(docker compose -f "$COMPOSE_FILE" ps -q redis 2>/dev/null || true)
if [[ -n "$CONTAINER_REDIS" ]]; then
  REDIS_DUMP_PATH="${BACKUP_PATH}_redis.rdb"
  docker exec "$CONTAINER_REDIS" redis-cli -a "${REDIS_PASSWORD:-}" SAVE
  docker cp "$CONTAINER_REDIS:/data/dump.rdb" "$REDIS_DUMP_PATH"
  echo "[OK] Redis dump: $(wc -c < "$REDIS_DUMP_PATH") bytes"
fi

# ── Step 3: Tar + Gzip ────────────────────────────────────
ARCHIVE_PATH="${BACKUP_PATH}.tar.gz"

tar -czf "$ARCHIVE_PATH" -C "$BACKUP_DIR" "$(basename "$PG_DUMP_PATH")"
if [[ -n "$REDIS_DUMP_PATH" ]]; then
  tar -rf "$ARCHIVE_PATH" -C "$BACKUP_DIR" "$(basename "$REDIS_DUMP_PATH")"
fi

echo "[OK] Archive created: $(wc -c < "$ARCHIVE_PATH") bytes"

# ── Step 4: Encrypt ───────────────────────────────────────
FINAL_PATH="$ARCHIVE_PATH"
if [[ -n "$ENCRYPTION_KEY" ]]; then
  ENCRYPTED_PATH="${ARCHIVE_PATH}.gpg"
  gpg --batch --yes --symmetric \
    --cipher-algo AES256 \
    --passphrase "$ENCRYPTION_KEY" \
    --output "$ENCRYPTED_PATH" \
    "$ARCHIVE_PATH"
  rm -f "$ARCHIVE_PATH"
  FINAL_PATH="$ENCRYPTED_PATH"
  echo "[OK] Encrypted: $(wc -c < "$FINAL_PATH") bytes"
fi

# ── Step 5: Upload to remote ──────────────────────────────
if [[ -n "$DESTINATION" ]] && command -v rclone &>/dev/null; then
  rclone copy "$FINAL_PATH" "${DESTINATION}/" --copy-links
  echo "[OK] Uploaded to: $DESTINATION"
fi

# ── Step 6: Cleanup old backups ──────────────────────────
find "$BACKUP_DIR" -name "styxproxy_backup_*" -type f -mtime "+${RETENTION_DAYS}" -delete
echo "[OK] Retention applied: keeping last $RETENTION_DAYS days"

# ── Step 7: Cleanup temp files ────────────────────────────
rm -f "$PG_DUMP_PATH"
[[ -n "$REDIS_DUMP_PATH" ]] && rm -f "$REDIS_DUMP_PATH"

echo "[$(date)] Backup complete: $(basename "$FINAL_PATH") — $(du -sh "$FINAL_PATH" | cut -f1)"
