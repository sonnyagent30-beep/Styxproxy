# Dante SOCKS5 Server Setup for Bunche

**Last Updated:** 2026-06-27
**Purpose:** Configure Dante as Bunche's proxy auth layer.

---

## What Dante Does in Bunche

```
Customer connects:  proxy1.bunche.ng:1080
                    username: bun_001
                    password: P@ssw0rd!
                           │
                           ▼
                 Dante SOCKS5 Server (Hetzner)
                           │
              Looks up bun_001 in auth backend
                           │
              Maps to: 185.199.228.45:1080 (provider IP)
                           │
                           ▼
                 Provider proxy responds
                           │
                           ▼
                 Customer gets the data
```

Customer thinks they're using `proxy1.bunche.ng`. They're actually using the provider IP underneath. Bunche controls access.

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

```
# Internal network interface (all interfaces)
internal: 0.0.0.0 port = 1080

# External interface (outbound)
external: eth0

# Authentication method — username/password from system
method: none

# Allow authenticated users
client pass {
    from: 0.0.0.0/0 to: 0.0.0.0/0
}

# Log settings
logoutput: syslog

# SOCKS protocol
socksprotocol: socks_v5

# Authentication — use /etc/danted.users for credentials
socks pass {
    from: 0.0.0.0/0 to: 0.0.0.0/0
    socksmethod: username.none
}

# Error handling
socks block {
    from: 0.0.0.0/0 to: 0.0.0.0/0
    sockserr: "Access denied"
}

# Timeout
timeout: 3600
```

### Enable System User Authentication

For Dante to authenticate against `/etc/danted.users` (not system users):

```
# Change socksmethod to use the userfile
socksmethod: username

# Add userfile directive
user.privileged: root
user.unprivileged: nobody

# Point to our user file
socks pass {
    from: 0.0.0.0/0 to: 0.0.0.0/0
    socksmethod: username
}
```

---

## User Management

Dante uses a simple userfile: `/etc/danted.users`

Format: `username:password` (colon-separated)

Passwords should be in the same format Dante expects. Use `htpasswd` or `danted`'s built-in tools.

### Generate Password Hash

```bash
# Install apache2-utils for htpasswd
sudo apt install apache2-utils

# Generate hash
htpasswd -nbd username password
# Returns: username:$apr1$xxxx$xxxx
```

For Dante, use the DES or MD5 hash format. Dante's `socksmethod: username` accepts multiple hash formats.

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

# Reload config (no restart needed)
sudo killall -HUP danted

# View logs
sudo tail -f /var/log/syslog | grep danted
```

---

## Connect Dante to Providers (Parent Proxy)

Dante can route through upstream parent proxies. This is how Bunche connects to Proxy-Seller/DataImpulse.

### Config with Parent Proxy

```
# Route everything through parent proxy
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
    parent: proxy.proxy-salesman.com:1080 login: username:password
}
```

---

## Bunche Credential Script Integration

Bunche uses `scripts/manage-bunche-credentials.sh` to add/revoke credentials. Dante reads from `/etc/danted.users`.

When a credential is added:
1. Script adds `username:hash` to `/etc/danted.users`
2. Script sends `SIGHUP` to Dante → hot reload, no downtime
3. Customer can immediately use credentials

When a credential is revoked:
1. Script removes the line from `/etc/danted.users`
2. Script sends `SIGHUP` to Dante → instant cutoff
3. Customer's Bunche credentials no longer work

---

## Security Hardening

### Bind to Cloudflare Only

```
# Only listen on Cloudflare IP ranges (add your ranges)
internal: 172.66.0.0/16 port = 1080
internal: 104.16.0.0/12 port = 1080

# Block direct non-Cloudflare access via UFW
sudo ufw deny 1080
sudo ufw allow from 172.66.0.0/16 to any port 1080
sudo ufw allow from 104.16.0.0/12 to any port 1080
```

### Non-Standard Port

```
# Use high random port instead of 1080
internal: 0.0.0.0 port = 48291
```

### Fail2Ban for Brute Force

Dante logs failed auth attempts. Configure fail2ban:

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

Create filter `/etc/fail2ban/filter.d/danted-auth.conf`:

```
[Definition]
failregex = danted: pam_unix.*auth.*failure.*<HOST>
ignoreregex =
```

---

## Cloudflare Tunnel (Recommended)

Instead of exposing Dante directly, use Cloudflare Tunnel to hide your VPS IP:

```bash
# Install cloudflared
curl -L https://github.com/cloudflare/cloudflared/releases/download/latest/cloudflared-linux-amd64 -o /usr/local/bin/cloudflared
chmod +x /usr/local/bin/cloudflared

# Authenticate
cloudflared tunnel login

# Create tunnel
cloudflared tunnel create bunche-proxy

# Route subdomain
cloudflared tunnel route dns bunche-proxy proxy.bunche.com

# Run tunnel
cloudflared tunnel run --token YOUR_TOKEN proxy.bunche.com:1080
```

This way Dante's port is never exposed publicly. Cloudflare handles DDoS protection, hiding your real IP, and SSL.

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
sudo bash scripts/manage-bunche-credentials.sh add testuser TestPass123

# Test it works
curl --socks5 testuser:TestPass123@localhost:1080 http://checkip.amazonaws.com

# Revoke test user
sudo bash scripts/manage-bunche-credentials.sh revoke testuser
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Dante won't start | Check config syntax: `danted -t` |
| Auth fails | Verify user in `/etc/danted.users` format |
| Can't connect | Check UFW/firewall allows port 1080 |
| Parent proxy fails | Verify provider credentials work directly |
| High latency | Check Dante logs for timeouts |

---

## See Also

- `scripts/manage-bunche-credentials.sh` — credential management
- `docs/ARCHITECTURE_PLAN.md` — full system architecture
- `workflows/WORKFLOW_SPECS.md` — how n8n creates credentials
