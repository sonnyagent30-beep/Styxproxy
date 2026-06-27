#!/bin/bash
# ============================================================
# Bunche — 3proxy Free Trial User Manager
# ============================================================
# Manages dynamic trial user credentials in 3proxy config.
# Called by n8n workflow on Theorem Reach postback (add)
# and by cleanup-3proxy-trials.sh on expiry (remove).
#
# Usage:
#   manage-3proxy-trial.sh add USERNAME PASSWORD PORT
#   manage-3proxy-trial.sh remove USERNAME
#   manage-3proxy-trial.sh list
#   manage-3proxy-trial.sh count
#
# Config (env vars, with defaults):
#   THREEPROXY_CONFIG_PATH=/etc/3proxy/bunche-trial.cfg
#   THREEPROXY_PID_PATH=/var/run/3proxy-bunche.pid
#   THREEPROXY_USER_PREFIX=trial_
# ============================================================

set -euo pipefail

CONFIG_PATH="${THREEPROXY_CONFIG_PATH:-/etc/3proxy/bunche-trial.cfg}"
PID_PATH="${THREEPROXY_PID_PATH:-/var/run/3proxy-bunche.pid}"
USER_PREFIX="${THREEPROXY_USER_PREFIX:-trial_}"

LOG_PREFIX="[manage-3proxy]"

die() { echo "$LOG_PREFIX ERROR: $*" >&2; exit 1; }
log() { echo "$LOG_PREFIX $(date -Iseconds) $*"; }

# Validate config exists
[ -f "$CONFIG_PATH" ] || die "3proxy config not found at $CONFIG_PATH"

# Validate username prefix
validate_username() {
  local username="$1"
  case "$username" in
    ${USER_PREFIX}*)
      ;;
    *)
      die "Username must start with '$USER_PREFIX'"
      ;;
  esac
  # Additional validation: alphanumeric + underscore, 4-32 chars
  if ! [[ "$username" =~ ^[a-zA-Z0-9_]{4,32}$ ]]; then
    die "Invalid username format (alphanumeric + underscore, 4-32 chars)"
  fi
}

reload_3proxy() {
  if [ -f "$PID_PATH" ]; then
    local pid
    pid=$(cat "$PID_PATH")
    if kill -0 "$pid" 2>/dev/null; then
      kill -HUP "$pid"
      log "Sent SIGHUP to 3proxy (PID $pid) — config reloaded"
    else
      log "WARNING: PID file exists but 3proxy not running (PID $pid)"
      return 1
    fi
  else
    log "WARNING: PID file not found at $PID_PATH — skipping reload"
    return 1
  fi
}

case "${1:-}" in
  add)
    # Args: add USERNAME PASSWORD PORT
    username="${2:-}"
    password="${3:-}"
    port="${4:-}"

    [ -n "$username" ] || die "Usage: $0 add USERNAME PASSWORD PORT"
    [ -n "$password" ] || die "Password required"
    [ -n "$port" ] || die "Port required"

    validate_username "$username"

    # Validate port is in trial range (8001-8100)
    if ! [[ "$port" =~ ^[0-9]+$ ]] || [ "$port" -lt 8001 ] || [ "$port" -gt 8100 ]; then
      die "Port must be between 8001 and 8100"
    fi

    # Check if user already exists
    if grep -q "^users ${username}:" "$CONFIG_PATH"; then
      die "User $username already exists"
    fi

    # Add user to config (plaintext, since 3proxy supports it directly)
    # For better security, use crypt() — but plaintext is fine for 2hr trials
    echo "users ${username}:CL:${password}" >> "$CONFIG_PATH"
    log "Added user $username on port $port"

    # Reload 3proxy config (SIGHUP = hot reload, no downtime)
    reload_3proxy
    ;;

  remove)
    # Args: remove USERNAME
    username="${2:-}"
    [ -n "$username" ] || die "Usage: $0 remove USERNAME"
    validate_username "$username"

    # Check if user exists
    if ! grep -q "^users ${username}:" "$CONFIG_PATH"; then
      log "User $username not found in config — nothing to remove"
      exit 0
    fi

    # Remove the user line
    sed -i "/^users ${username}:/d" "$CONFIG_PATH"
    log "Removed user $username"

    # Reload 3proxy config
    reload_3proxy
    ;;

  list)
    # List all active trial users
    echo "Active trial users:"
    grep "^users ${USER_PREFIX}" "$CONFIG_PATH" | awk -F'[: ]' '{print "  - " $2}' || echo "  (none)"
    ;;

  count)
    # Count active trial users
    count=$(grep -c "^users ${USER_PREFIX}" "$CONFIG_PATH" || echo "0")
    echo "$count"
    ;;

  *)
    echo "Usage: $0 {add USERNAME PASSWORD PORT|remove USERNAME|list|count}" >&2
    exit 1
    ;;
esac