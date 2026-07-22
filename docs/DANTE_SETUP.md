# Dante SOCKS5 Server Setup for Styxproxy

**Last Updated:** 2026-07-01
**Purpose:** Configure Dante as Styxproxy's proxy auth layer.

---

## What Dante Does in Styxproxy

```
Customer connects:  proxy1.styxproxy.com:1080
                   username: bun_ayomide7
                   password: SecureP@ss123
                          │
                          ▼
                Dante SOCKS5 Server (VPS)
                          │
             Looks up bun_ayomide7 in /etc/danted.users
                          │
             Maps to: 185.199.228.45:1080 (provider IP)
                          │
                          ▼
                Customer gets the data through the provider proxy
```

Customer thinks they're using `proxy1.styxproxy.com`. They're actually using the provider IP underneath. Styxproxy controls access via Dante's username/password auth.

---

## Installation

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Dante
sudo apt install dante-server

# Verify installation
danted --version
```

---

## Configuration

### Main Config: /etc/danted.conf

```conf
# Internal network interface (all interfaces)
internal: 0.0.0.0 port = 1080

# External interface (outbound)
external: eth0

# Authentication method — username/password from userfile
method: none

# Allow authenticated users
client pass {
    from: 0.0.0.0/0 to: 0.0.0.0/0
}

# Log settings
logoutput: syslog

# SOCKS protocol
socksprotocol: socks_v5

# Authentication — username from /etc/danted.users
# Dante verifies the password by computing MD5 of what the client sent
# and comparing against the stored $apr1$ hash
socksmethod: username

# Privileged user (for Dante internal operations)
user.privileged: root
user.unprivileged: nobody

# Error handling
socks block {
    from: 0.0.0.0/0 to: 0.0.0.0/0
    sockserr: "Access denied"
}

# Timeout
timeout: 3600
```

---

## User Management

Dante uses a simple userlist file: `/etc/danted.users`

Format: `username:$apr1$salt$hash` (MD5-based hash — NOT plain text)

### Generate Password Hash

Use `htpasswd` from apache2-utils:

```bash
# Install htpasswd
sudo apt install apache2-utils

# Generate MD5 hash for a new credential
# -n  : output to stdout
# -b  : batch mode (password on command line)
# -d  : force CRYPT/DES (creates $apr1$ MD5 variant on modern systems)
sudo htpasswd -nbd <username> '<password>'

# Example
sudo htpasswd -nbd bun_ayomide7 'SecureP@ss123'
# Output: bun_ayomide7:$apr1$rAnd0MsAlT$9VH1xYZABCDEFGHIJKLMNOPQ

# Add to Dante userlist
echo "bun_ayomide7:$apr1$rAnd0MsAlT$9VH1xYZABCDEFGHIJKLMNOPQ" | \
  sudo tee -a /etc/danted.users
```

### What Hash Format Dante Accepts

Dante reads `/etc/danted.users` and computes the hash of the password the client sends, then compares:

| Format | Example | Dante compatible? |
|--------|---------|------------------|
| Plain text | `user:password` | ✅ Yes (not recommended) |
| **MD5 `$apr1$`** | `user:$apr1$salt$hash` | ✅ **Yes — use this** |
| SHA `$sha$` | `user:$sha$...` | ✅ Yes |
| CRYPT/DES | `user:VXUf7EPr5wLw.` | ✅ Yes (legacy) |
| bcrypt `$2b$` | `user:$2b$...` | ❌ No — Dante doesn't support bcrypt |

> **Note:** Dante does NOT support bcrypt. Dante only supports MD5/SHA/CRYPT hashes. Do NOT generate bcrypt hashes for Dante credentials.

### Password Requirements for Dante Credentials

- Dante username: alphanumeric + underscore, 3-32 chars, starts with `bun_`
- Dante password: 8-64 chars, must match what Dante verifies via MD5
- Dante has no built-in policy enforcement — enforce password rules in the Styxproxy app before creating the credential

---

## Credential Lifecycle

### Add Credential (order fulfilled)

```bash
# 1. Generate hash
HASH=$(sudo htpasswd -nbd bun_ayomide7 'SecureP@ss123')

# 2. Add to Dante userlist
echo "$HASH" | sudo tee -a /etc/danted.users

# 3. Hot reload Dante (no downtime)
sudo killall -HUP danted
```

### Revoke Credential (order expires or refund)

```bash
# Remove from Dante userlist
sudo grep -v '^bun_ayomide7:' /etc/danted.users | \
  sudo tee /etc/danted.users.tmp && \
  sudo mv /etc/danted.users.tmp /etc/danted.users

# Hot reload (customer access cut off immediately)
sudo killall -HUP danted
```

### Credential Script (scripts/manage-styxproxy-credentials.sh)

The script handles Dante userlist management:

```bash
# Add
./manage-styxproxy-credentials.sh add bun_ayomide7 'SecureP@ss123'

# Revoke
./manage-styxproxy-credentials.sh revoke bun_ayomide7

# List active
./manage-styxproxy-credentials.sh list
```

---

## Dante Service Management

```bash
# Start Dante
sudo systemctl start danted

# Enable on boot
sudo systemctl enable danted

# Check status
sudo systemctl status danted

# Test config syntax
sudo danted -t

# Reload config (no restart needed — hot reload)
sudo killall -HUP danted

# View logs
sudo tail -f /var/log/syslog | grep danted
```

---

## Connect Dante to Provider Proxies (Parent Proxy)

Dante routes customer traffic through upstream parent proxies (Proxy-Seller, DataImpulse, etc.).

```conf
# Route through parent proxy
socks pass {
    from: 0.0.0.0/0 to: 0.0.0.0/0
    socksmethod: username
    command: connect
    protocol: socks_v5
    parent: proxy.proxy-salesman.com:1080
}

# Parent proxy authentication
socks parent {
    from: 0.0.0.0/0 to: 0.0.0.0/0
    protocol: socks_v5
    parent: proxy.proxy-salesman.com:1080 login: provider_username:provider_password
}
```

---

## Security Hardening

### Bind to Cloudflare Only

```conf
# Only listen on Cloudflare IP ranges
internal: 172.66.0.0/16 port = 1080
internal: 104.16.0.0/12 port = 1080
```

Block direct non-Cloudflare access via UFW:
```bash
sudo ufw deny 1080
sudo ufw allow from 172.66.0.0/16 to any port 1080
sudo ufw allow from 104.16.0.0/12 to any port 1080
```

### Non-Standard Port

```conf
# Use high random port instead of 1080
internal: 0.0.0.0 port = 48291
```

### Fail2Ban for Brute Force

```bash
# /etc/fail2ban/jail.local
[dante-auth]
enabled = true
port = 1080
filter = dante-auth
logpath = /var/log/syslog
maxretry = 3
bantime = 3600
findtime = 600
```

---

## Cloudflare Tunnel (Recommended)

Instead of exposing Dante directly, use Cloudflare Tunnel to hide your VPS IP:

```bash
# Install cloudflared
curl -L https://github.com/cloudflare/cloudflared/releases/download/latest/cloudflared-linux-amd64 \
  -o /usr/local/bin/cloudflared
chmod +x /usr/local/bin/cloudflared

# Authenticate
cloudflared tunnel login

# Create tunnel
cloudflared tunnel create styxproxy-proxy

# Route subdomain
cloudflared tunnel route dns styxproxy-proxy proxy.styxproxy.com

# Run tunnel
cloudflared tunnel run --token YOUR_TOKEN proxy.styxproxy.com
```

---

## Testing

### Test Dante is Running

```bash
# Check port is listening
sudo ss -tlnp | grep 1080

# Test with curl
curl --socks5 username:password@localhost:1080 http://checkip.amazonaws.com
```

### Test Credential Addition

```bash
# Add test user
sudo bash scripts/manage-styxproxy-credentials.sh add testuser 'TestPass123'

# Test it works
curl --socks5 testuser:TestPass123@localhost:1080 http://checkip.amazonaws.com

# Revoke test user
sudo bash scripts/manage-styxproxy-credentials.sh revoke testuser
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Dante won't start | Check config syntax: `danted -t` |
| Auth fails | Verify hash in `/etc/danted.users` — use `htpasswd -nbd` not bcrypt |
| Can't connect | Check UFW/firewall allows port 1080 |
| Parent proxy fails | Verify provider credentials work directly |
| High latency | Check Dante logs for timeouts |

---

## See Also

- `scripts/manage-styxproxy-credentials.sh` — credential management
- `docs/DATABASE_SCHEMA.md` — `styxproxy_credentials` table tracks Dante username → provider IP mapping
- `workflows/WORKFLOW_SPECS.md` — how n8n creates credentials
