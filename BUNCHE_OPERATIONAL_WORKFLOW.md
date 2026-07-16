# BUNCHE OPERATIONAL WORKFLOW
## Monthly Single-Unit Proxy Reseller Operations

---

**Document Type:** Operational Playbook  
**Role:** Operations Manager  
**Date:** June 29, 2026  
**Classification:** Internal Use

---

## ADMIN ACCESS SECURITY

**Hardened Admin Path — OPTION C (Codename + Token)**

| Item | Value |
|------|-------|
| Admin URL | `styxproxy.com/powerhold` |
| Token | `rsu1JwfywmIZNIPiIWxy8VOu3oRZR0vnI2kfcq/6WlI=` |
| Token ENV var | `ADMIN_TOKEN` |
| Allowed IPs | Home + Bunche VPS itself + open for additions |

```
styxproxy.com/powerhold        ← team bookmark (codename)
     ↓ (?token=rsu1JwfywmIZNIPiIWxy8VOu3oRZR0vnI2kfcq/6WlI=)
styxproxy.com/powerhold/admin  ← actual admin panel
```

**Security Stack:**
1. Obscure codename path — bots/scanners can't find it
2. Secret token — second gate, rotatable via env var
3. IP allowlist — firewall restricts to approved IPs only
4. Basic Auth prompt — cheap static gate in front of admin app

**Adding team IPs later:**
```bash
# Add IP to firewall allowlist
sudo ufw allow from <NEW_IP> to any port 443
```

**Rotating the token:**
```bash
# Generate new token
openssl rand -base64 32
# Update ~/.bunche_secrets.env
# Update all team bookmarks
```

---
