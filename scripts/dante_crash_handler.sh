#!/bin/bash
# dante_crash_handler.sh — runs after every danted restart attempt
# NOTE: installed at /usr/local/bin/ because /opt is InaccessibleDirectories in danted.service

LOGFILE="/var/log/dante_watchdog.log"
STATEFILE="/var/run/dante_watchdog.state"
MAX_RESTARTS=5
WINDOW_SECS=60

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') DANTE_WATCHDOG: $1" >> "$LOGFILE"
}

# Check if danted is actually running now
if systemctl is-active danted > /dev/null 2>&1; then
    log "danted restarted successfully"
    echo "0" > "$STATEFILE"
    exit 0
fi

# danted is still down — count this as a crash
CRASHES=$(cat "$STATEFILE" 2>/dev/null || echo "0")
CRASHES=$((CRASHES + 1))
echo "$CRASHES" > "$STATEFILE"

log "danted restart attempt $CRASHES failed — still not healthy"

if [ "$CRASHES" -ge "$MAX_RESTARTS" ]; then
    log "CRITICAL: Dante crashed $CRASHES times in ${WINDOW_SECS}s — alerting"
    # Alert via Betterstack webhook if configured, else email
    if [ -n "$DANTE_ALERT_WEBHOOK" ]; then
        curl -s -X POST "$DANTE_ALERT_WEBHOOK"           -H 'Content-Type: application/json'           -d "{\"text\": \"[ALERT] Dante unstable on $(hostname) — $CRASHES crashes in ${WINDOW_SECS}s\"}"           2>/dev/null
    fi
    # Fallback: send email
    echo "Dante SOCKS5 is unstable on $(hostname): $CRASHES crashes in ${WINDOW_SECS}s. Manual intervention required." | \
        mail -s "[CRITICAL] Dante unstable $(hostname)" oyebiyiayomide30@gmail.com 2>/dev/null
    echo "0" > "$STATEFILE"
fi
