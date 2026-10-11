#!/usr/bin/env bash
# Relay authentication setup for Styxproxy 3proxy relay.
#
# This script:
# 1. Generates a secure password for the relay (if not already set)
# 2. Configures 3proxy with authentication (not anonymous)
# 3. Creates the passwd file with the relay credentials
#
# The relay is INTERNAL ONLY — customers connect directly to upstream IP:port.
# This auth prevents the relay from becoming an open relay on a public IP.
#
# Usage:
#   bash setup_relay_auth.sh [--force]
#
# The password is stored in /etc/styxproxy/relay-passwd (root-only, 0600).

set -euo pipefail

RELAY_PASSWD_FILE="/etc/3proxy/passwd"
RELAY_USER_FILE="/etc/styxproxy/relay-user"
RELAY_PASSWD_SECRET="/etc/styxproxy/relay-passwd"
PROXY_CONFIG="/etc/3proxy/3proxy.cfg"

log() { echo "[$(date -Iseconds)] $*"; }

# ── Generate or load relay password ─────────────────────────────────────────
load_or_generate_password() {
    if [[ -f "$RELAY_PASSWD_SECRET" ]] && [[ "${1:-}" != "--force" ]]; then
        log "Using existing relay password from $RELAY_PASSWD_SECRET" >&2
        cat "$RELAY_PASSWD_SECRET"
        return 0
    fi

    # Generate a 32-character password (alphanumeric only, no special chars)
    local password
    password=$(head -c 32 /dev/urandom | base64 | tr -d '/+=' | head -c 32)
    
    # Store it securely
    echo -n "$password" > "$RELAY_PASSWD_SECRET"
    chmod 600 "$RELAY_PASSWD_SECRET"
    chown root:root "$RELAY_PASSWD_SECRET"
    
    log "Generated new relay password (32 chars)" >&2
    echo "$password"
}

# ── Configure 3proxy with authentication ────────────────────────────────────
configure_3proxy() {
    local relay_user="$1"
    local relay_passwd="$2"

    # Create passwd file for 3proxy
    # 3proxy passwd file format: username:password:flags
    # flags: CL = crypt login (username + crypt password)
    # We store plaintext in the passwd file — 3proxy accepts it for SOCKS5 auth
    cat > "$RELAY_PASSWD_FILE" <<EOF
${relay_user}:${relay_passwd}:CL
EOF
    chmod 600 "$RELAY_PASSWD_FILE"
    chown root:root "$RELAY_PASSWD_FILE"
    
    log "Created passwd file: $RELAY_PASSWD_FILE"

    # Update 3proxy config to require authentication
    # 3proxy auth model:
    #   auth strong = require username/password
    #   passwd file at /etc/3proxy/passwd maps users
    #   allow username = only this user can connect
    #   passwd file format: username:password:flags (CL = crypt login)
    
    cat > "$PROXY_CONFIG" <<EOF
# Styxproxy SOCKS5 Relay Configuration (AUTHENTICATED)
# Internal-only — customers connect directly to upstream IP:port.
# Auth added $(date -Iseconds) — anonymous access removed.

nserver 8.8.8.8
nserver 8.4.4.4
nscache 65536

log /var/log/3proxy/3proxy.log
logformat "L%t.%. %N.%p %E %U %C:%c %I %O %T %R:%r %X %h %y %s:%S %e"

# Authentication — require username/password
auth strong

# Allow only the relay user (defined in /etc/3proxy/passwd)
allow ${relay_user}

# Listeners (authenticated, no -a flag)
proxy -p8080
socks -p1080

config /etc/3proxy/block.conf
EOF

    chmod 600 "$PROXY_CONFIG"
    chown root:root "$PROXY_CONFIG"
    
    log "Updated 3proxy config: $PROXY_CONFIG"
}

# ── Verify the configuration ───────────────────────────────────────────────
verify_config() {
    log "Verifying 3proxy configuration..."
    
    if [[ ! -s "$PROXY_CONFIG" ]]; then
        log "ERROR: 3proxy config is empty"
        return 1
    fi
    
    # Check that auth is enabled (no -a flag on listeners)
    if grep -q 'socks.*-a' "$PROXY_CONFIG" || grep -q 'proxy.*-a' "$PROXY_CONFIG"; then
        log "ERROR: anonymous auth flag (-a) still present in config"
        return 1
    fi
    
    if ! grep -q 'auth strong' "$PROXY_CONFIG"; then
        log "ERROR: auth strong directive not found"
        return 1
    fi
    
    log "Config verification passed"
    return 0
}

# ── Main ────────────────────────────────────────────────────────────────────
main() {
    log "Setting up relay authentication..."
    
    # Generate or load password
    local relay_passwd
    relay_passwd=$(load_or_generate_password "$@")
    
    # Relay user (fixed — this is a single-user relay)
    local relay_user="styxproxy_relay"
    
    # Store username for reference
    echo "$relay_user" > "$RELAY_USER_FILE"
    chmod 600 "$RELAY_USER_FILE"
    
    # Configure 3proxy
    configure_3proxy "$relay_user" "$relay_passwd"
    
    # Verify
    verify_config
    
    # Restart 3proxy to apply changes
    log "Restarting 3proxy..."
    systemctl restart styxproxy-3proxy
    
    # Wait and verify it's running
    sleep 3
    if systemctl is-active --quiet styxproxy-3proxy; then
        log "3proxy is active"
        
        # Verify listeners are up
        if ss -tlnp | grep -q ':1080'; then
            log "SOCKS5 listener on :1080 is up"
        else
            log "WARNING: SOCKS5 listener on :1080 not found"
        fi
        if ss -tlnp | grep -q ':8080'; then
            log "HTTP proxy listener on :8080 is up"
        else
            log "WARNING: HTTP proxy listener on :8080 not found"
        fi
    else
        log "ERROR: 3proxy failed to start — check journalctl:"
        journalctl -u styxproxy-3proxy --no-pager -n 30 || true
        return 1
    fi
    
    log "Relay authentication setup complete."
    log ""
    log "IMPORTANT: The relay password is stored in $RELAY_PASSWD_SECRET"
    log "This is for INTERNAL USE ONLY — customers connect directly to upstream IP:port."
}

main "$@"
