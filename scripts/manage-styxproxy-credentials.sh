#!/bin/bash
#===============================================================================
# manage-styxproxy-credentials.sh
# Manages Styxproxy Dante SOCKS5 credentials.
# Adds, revokes, rotates, and lists credentials in /etc/danted.users.
#
# Usage:
#   ./manage-styxproxy-credentials.sh add    <username> <password>
#   ./manage-styxproxy-credentials.sh revoke <username>
#   ./manage-styxproxy-credentials.sh rotate <username> <new_password>
#   ./manage-styxproxy-credentials.sh list
#   ./manage-styxproxy-credentials.sh free_trial <username> <password>
#
# Author: Styxproxy
# Last Updated: 2026-06-27
#===============================================================================

set -e

DANTED_USERS_FILE="/etc/danted.users"
DANTED_PID_FILE="/var/run/danted.pid"
LOG_FILE="/var/log/styxproxy-credentials.log"

#-------------------------------------------------------------------------------
# Logging
#-------------------------------------------------------------------------------
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

#-------------------------------------------------------------------------------
# Generate password hash (DES, compatible with Dante)
#-------------------------------------------------------------------------------
generate_hash() {
    local password="$1"
    # Use openssl to generate DES hash
    local hash
    hash=$(openssl passwd -1 -salt "Bu" "$password" 2>/dev/null || \
           openssl passwd -des -salt "Bu" "$password" 2>/dev/null)
    echo "$hash"
}

#-------------------------------------------------------------------------------
# Reload Dante (hot reload without restart)
#-------------------------------------------------------------------------------
reload_dante() {
    if [ -f "$DANTED_PID_FILE" ]; then
        kill -HUP $(cat "$DANTED_PID_FILE") 2>/dev/null && \
            log "Dante reloaded successfully" || \
            log "WARNING: Could not reload Dante (PID file may be wrong)"
    else
        # Try finding Dante PID another way
        local pid
        pid=$(pgrep danted 2>/dev/null | head -1)
        if [ -n "$pid" ]; then
            kill -HUP "$pid" 2>/dev/null && log "Dante reloaded (PID: $pid)"
        else
            log "WARNING: Dante not running, no reload needed"
        fi
    fi
}

#-------------------------------------------------------------------------------
# Add a new credential
#-------------------------------------------------------------------------------
add_credential() {
    local username="$1"
    local password="$2"

    if [ -z "$username" ] || [ -z "$password" ]; then
        echo "Usage: $0 add <username> <password>"
        exit 1
    fi

    # Check if user already exists
    if grep -q "^${username}:" "$DANTED_USERS_FILE" 2>/dev/null; then
        log "ERROR: User '$username' already exists"
        exit 1
    fi

    # Generate hash and add user
    local hash
    hash=$(generate_hash "$password")
    if [ -z "$hash" ]; then
        log "ERROR: Could not generate password hash"
        exit 1
    fi

    echo "${username}:${hash}" >> "$DANTED_USERS_FILE"
    log "ADDED: $username (hash: ${hash:0:20}...)"
    
    # Reload Dante
    reload_dante
    
    echo "SUCCESS: User '$username' added and Dante reloaded"
}

#-------------------------------------------------------------------------------
# Revoke a credential
#-------------------------------------------------------------------------------
revoke_credential() {
    local username="$1"

    if [ -z "$username" ]; then
        echo "Usage: $0 revoke <username>"
        exit 1
    fi

    # Check if user exists
    if ! grep -q "^${username}:" "$DANTED_USERS_FILE" 2>/dev/null; then
        log "ERROR: User '$username' not found"
        exit 1
    fi

    # Remove user
    local temp_file
    temp_file=$(mktemp)
    grep -v "^${username}:" "$DANTED_USERS_FILE" > "$temp_file" || true
    mv "$temp_file" "$DANTED_USERS_FILE"
    log "REVOKED: $username"
    
    # Reload Dante
    reload_dante
    
    echo "SUCCESS: User '$username' revoked and Dante reloaded"
}

#-------------------------------------------------------------------------------
# Rotate a credential (change password)
#-------------------------------------------------------------------------------
rotate_credential() {
    local username="$1"
    local new_password="$2"

    if [ -z "$username" ] || [ -z "$new_password" ]; then
        echo "Usage: $0 rotate <username> <new_password>"
        exit 1
    fi

    # Check if user exists
    if ! grep -q "^${username}:" "$DANTED_USERS_FILE" 2>/dev/null; then
        log "ERROR: User '$username' not found"
        exit 1
    fi

    # Generate new hash
    local new_hash
    new_hash=$(generate_hash "$new_password")
    if [ -z "$new_hash" ]; then
        log "ERROR: Could not generate new password hash"
        exit 1
    fi

    # Replace old hash with new
    local temp_file
    temp_file=$(mktemp)
    sed "s|^${username}:.*|${username}:${new_hash}|" "$DANTED_USERS_FILE" > "$temp_file"
    mv "$temp_file" "$DANTED_USERS_FILE"
    log "ROTATED: $username (new hash: ${new_hash:0:20}...)"
    
    # Reload Dante
    reload_dante
    
    echo "SUCCESS: User '$username' rotated and Dante reloaded"
}

#-------------------------------------------------------------------------------
# List all credentials (without showing full hashes)
#-------------------------------------------------------------------------------
list_credentials() {
    echo "=== Styxproxy Dante Credentials ==="
    echo "File: $DANTED_USERS_FILE"
    echo ""
    
    if [ ! -f "$DANTED_USERS_FILE" ]; then
        echo "(No credentials file found)"
        exit 0
    fi
    
    local count=0
    while IFS=: read -r user hash; do
        if [ -n "$user" ]; then
            echo "  $user"
            count=$((count + 1))
        fi
    done < "$DANTED_USERS_FILE"
    
    echo ""
    echo "Total: $count credentials"
}

#-------------------------------------------------------------------------------
# Add free trial credential (shorter TTL logic handled by cron, not Dante)
#-------------------------------------------------------------------------------
add_free_trial() {
    local username="$1"
    local password="$2"

    if [ -z "$username" ] || [ -z "$password" ]; then
        echo "Usage: $0 free_trial <username> <password>"
        exit 1
    fi

    # Same as add, but logs as free_trial type
    local hash
    hash=$(generate_hash "$password")
    if [ -z "$hash" ]; then
        log "ERROR: Could not generate password hash"
        exit 1
    fi

    echo "${username}:${hash}" >> "$DANTED_USERS_FILE"
    log "FREE_TRIAL_ADDED: $username (expires in 2 hours)"
    
    # Reload Dante
    reload_dante
    
    echo "SUCCESS: Free trial user '$username' added"
}

#-------------------------------------------------------------------------------
# Main command router
#-------------------------------------------------------------------------------
case "$1" in
    add)
        add_credential "$2" "$3"
        ;;
    revoke)
        revoke_credential "$2"
        ;;
    rotate)
        rotate_credential "$2" "$3"
        ;;
    list)
        list_credentials
        ;;
    free_trial)
        add_free_trial "$2" "$3"
        ;;
    *)
        echo "Styxproxy Credential Manager"
        echo "=========================="
        echo ""
        echo "Usage:"
        echo "  $0 add        <username> <password>   # Add new credential"
        echo "  $0 revoke     <username>              # Revoke credential"
        echo "  $0 rotate     <username> <new_pass>   # Rotate password"
        echo "  $0 list                               # List all credentials"
        echo "  $0 free_trial <username> <password>   # Add free trial"
        echo ""
        echo "Examples:"
        echo "  $0 add bun_001 P@ssw0rd!2024"
        echo "  $0 revoke bun_001"
        echo "  $0 rotate bun_001 N3wP@ss!5678"
        echo "  $0 free_trial trial_a7b9c2 Kx9mNp2qR8sT4wY7"
        exit 1
        ;;
esac
