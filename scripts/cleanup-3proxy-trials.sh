#!/bin/bash
# ============================================================
# Bunche — 3proxy Free Trial Cleanup Cron
# ============================================================
# Removes expired trial users from 3proxy config + marks
# them as 'expired' in PostgreSQL.
#
# Cron: */5 * * * * (every 5 minutes)
#   /usr/local/bin/cleanup-3proxy-trials.sh
#
# Required env vars:
#   POSTGRES_HOST, POSTGRES_USER, POSTGRES_DB, PGPASSWORD
#   THREEPROXY_CONFIG_PATH
#   MANAGE_SCRIPT=/usr/local/bin/manage-3proxy-trial.sh
# ============================================================

set -euo pipefail

LOG_PREFIX="[cleanup-3proxy]"
MANAGE_SCRIPT="${MANAGE_SCRIPT:-/usr/local/bin/manage-3proxy-trial.sh}"
LOG_FILE="${LOG_FILE:-/var/log/bunche-trial-cleanup.log}"

log() {
  echo "$LOG_PREFIX $(date -Iseconds) $*" | tee -a "$LOG_FILE"
}

log "Starting cleanup cycle"

# Check manage script exists
[ -x "$MANAGE_SCRIPT" ] || {
  log "ERROR: $MANAGE_SCRIPT not found or not executable"
  exit 1
}

# Query PostgreSQL for expired trials
EXPIRED=$(PGPASSWORD="$PGPASSWORD" psql \
  --host="${POSTGRES_HOST:-localhost}" \
  --username="${POSTGRES_USER:-bunche}" \
  --dbname="${POSTGRES_DB:-bunche}" \
  --tuples-only \
  --no-align \
  --command="SELECT user_id FROM free_trials WHERE status = 'active' AND expires_at < NOW();" 2>/dev/null || echo "")

if [ -z "$EXPIRED" ]; then
  log "No expired trials to clean up"
  exit 0
fi

# Count expired trials
count=0
while IFS= read -r username; do
  [ -z "$username" ] && continue

  log "Expiring trial: $username"

  # Remove from 3proxy config
  if "$MANAGE_SCRIPT" remove "$username" 2>&1 | tee -a "$LOG_FILE"; then
    # Mark as expired in DB
    PGPASSWORD="$PGPASSWORD" psql \
      --host="${POSTGRES_HOST:-localhost}" \
      --username="${POSTGRES_USER:-bunche}" \
      --dbname="${POSTGRES_DB:-bunche}" \
      --command="UPDATE free_trials SET status = 'expired' WHERE user_id = '$username' AND status = 'active';" \
      2>&1 | tee -a "$LOG_FILE"

    count=$((count + 1))
  else
    log "ERROR: Failed to remove $username from 3proxy — leaving in DB for retry"
  fi
done <<< "$EXPIRED"

log "Cleanup complete: $count expired trials processed"

# Optional: log active trial count for monitoring
ACTIVE=$(PGPASSWORD="$PGPASSWORD" psql \
  --host="${POSTGRES_HOST:-localhost}" \
  --username="${POSTGRES_USER:-bunche}" \
  --dbname="${POSTGRES_DB:-bunche}" \
  --tuples-only \
  --no-align \
  --command="SELECT COUNT(*) FROM free_trials WHERE status = 'active';" 2>/dev/null || echo "?")

log "Active trials remaining: $ACTIVE"