#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────
# Bunche — Daily Encrypted Backup
# Schedule via cron:
#   0 2 * * * /opt/bunche/infrastructure/scripts/backup.sh
# ─────────────────────────────────────────────────────────

set -euo pipefail

COMPOSE_FILE="${COMPOSE_FILE:-/opt/bunche/infrastructure/docker-compose.yml}"
BACKUP_DIR="${BACKUP_DIR:-/opt/bunche/backups}"
RETENTION_DAYS="${RETENTION_DAYS:-14}"
ENCRYPTION_KEY="${BACKUP_ENCRYPTION_KEY:-}"
DESTINATION="${BACKUP_DESTINATION:-}"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="bunche_backup_${TIMESTAMP}"
BACKUP_PATH="${BACKUP_DIR}/${BACKUP_NAME}"

# ── Pre-flight ─────────────────────────────────────────────
if [[ ! -f "$COMPOSE_FILE" ]]; then
  echo "[ERROR] docker-compose.yml not found at $COMPOSE_FILE"
  exit 1
fi
if [[ -z "$ENCRYPTION_KEY" ]]; then
  echo "[WARN] BACKUP_ENCRYPTION_KEY not set — backup will NOT be encrypted"
fi
mkdir -p "$BACKUP_DIR"

echo "[$(date)] Starting backup: $BACKUP_NAME"

# ── Step 1: PostgreSQL dump ────────────────────────────────
CONTAINER=$(docker compose -f "$COMPOSE_FILE" ps -q postgres 2>/dev/null || true)
if [[ -z "$CONTAINER" ]]; then
  echo "[ERROR] Postgres container not running"
  exit 1
fi
PG_DUMP_PATH="${BACKUP_PATH}_pg.sql"
docker exec "$CONTAINER" pg_dump -U bunche -d bunche --no-owner --no-acl > "$PG_DUMP_PATH"
echo "[OK] PostgreSQL dump: $(wc -c < "$PG_DUMP_PATH") bytes"

# ── Step 2: Redis dump ────────────────────────────────────
CONTAINER=$(docker compose -f "$COMPOSE_FILE" ps -q redis 2>/dev/null || true)
if [[ -n "$CONTAINER" ]]; then
  REDIS_DUMP_PATH="${BACKUP_PATH}_redis.rdb"
  docker exec "$CONTAINER" redis-cli -a "$REDIS_PASSWORD" SAVE
  docker cp "$CONTAINER":/data/dump.rdb "$REDIS_DUMP_PATH"
  echo "[OK] Redis dump: $(wc -c < "$REDIS_DUMP_PATH") bytes"
fi

# ── Step 3: Tar + Gzip ───────────────────────────────────
ARCHIVE_PATH="${BACKUP_PATH}.tar.gz"
tar -czf "$ARCHIVE_PATH" -C "$BACKUP_DIR" "$(basename "$PG_DUMP_PATH")"
[[ -f "${REDIS_DUMP_PATH:-}" ]] && tar -rf "$ARCHIVE_PATH" -C "$BACKUP_DIR" "$(basename "$REDIS_DUMP_PATH")"
echo "[OK] Archive created: $(wc -c < "$ARCHIVE_PATH") bytes"

# ── Step 4: Encrypt ───────────────────────────────────────
if [[ -n "$ENCRYPTION_KEY" ]]; then
  ENCRYPTED="${ARCHIVE_PATH}.gpg"
  gpg --batch --yes --symmetric --cipher-algo AES256 \
    --passphrase "$ENCRYPTION_KEY" \
    --output "$ENCRYPTED" "$ARCHIVE_PATH"
  rm "$ARCHIVE_PATH"
  ARCHIVE_PATH="$ENCRYPTED"
  echo "[OK] Encrypted: $(wc -c < "$ARCHIVE_PATH") bytes"
fi

# ── Step 5: Upload to remote ──────────────────────────────
if [[ -n "$DESTINATION" ]] && command -v rclone &>/dev/null; then
  rclone copy "$ARCHIVE_PATH" "${DESTINATION}/" --copy-links
  echo "[OK] Uploaded to: $DESTINATION"
fi

# ── Step 6: Cleanup old backups ──────────────────────────
find "$BACKUP_DIR" -name "bunche_backup_*" -type f -mtime "+${RETENTION_DAYS}" -delete
echo "[OK] Retention applied: keeping last $RETENTION_DAYS days"

# ── Step 7: Cleanup temp files ────────────────────────────
rm -f "$PG_DUMP_PATH" "${REDIS_DUMP_PATH:-}"
echo "[$(date)] Backup complete: $(basename "$ARCHIVE_PATH") — $(du -sh "$ARCHIVE_PATH" | cut -f1)"
