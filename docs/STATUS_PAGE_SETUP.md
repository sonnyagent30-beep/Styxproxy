# Status Page Setup Guide (Betterstack)

**Owner:** Operations  
**Last updated:** 2026-08-03

---

## Overview

This guide covers setting up and maintaining a status page using Betterstack (formerly Cachet). The status page provides real-time service availability information to customers, reducing support volume during incidents.

---

## Why Betterstack?

- **Free tier** available for up to 10 monitors
- **Custom domain** support (`status.styxproxy.com`)
- **Incident timeline** with customer-facing updates
- **SMS/Email notifications** to your team
- **Uptime monitoring** for HTTP endpoints

---

## Setup Steps

### 1. Create Account

1. Go to https://betterstack.com (or https://cachet.com)
2. Sign up with your Google account or email
3. Verify your email

### 2. Add Monitors

Add monitors for each critical endpoint:

| Endpoint | URL | Interval | Type |
|----------|-----|----------|------|
| API Health | `https://api.styxproxy.com/api/v1/health` | 1 min | HTTPS |
| Frontend | `https://styxproxy.com` | 1 min | HTTPS |
| Status Page | `https://status.styxproxy.com` | 1 min | HTTPS |
| Charon Bot | `https://api.styxproxy.com/api/charon/health` | 2 min | HTTPS |

**Setup via Betterstack Dashboard:**
```
Dashboard → Add Monitor → HTTPS → Enter URL → Set interval → Save
```

### 3. Configure Status Page

1. Go to **Dashboard → Status Page → Settings**
2. Configure:
   - **Custom domain:** `status.styxproxy.com`
   - **Timezone:** Africa/Lagos (WAT)
   - **Brand colors:** Match Styxproxy theme
   - **Logo:** Upload `/chatbot-logo.png`

3. Get your **status page ID** from the URL: `https://api.statuspage.io/v1/pages/{page_id}`

### 4. Set Up Custom Domain (Optional)

If using a custom domain (`status.styxproxy.com`):

1. In Betterstack: Go to **Status Page → Settings → Custom Domain**
2. Add CNAME record in your DNS provider:
   ```
   Type: CNAME
   Name: status
   Value: statuspage.io
   ```
3. Wait ~5 minutes for propagation
4. Enable HTTPS (Betterstack provides automatic SSL)

### 5. Configure Notifications

Set up team notifications so you're alerted when services go down:

1. **Dashboard → Settings → Notifications**
2. Add phone numbers for on-call team
3. Configure escalation rules:
   - 0 min: SMS to on-call
   - 5 min: If unacknowledged, SMS to Dannion

### 6. Add to Frontend

Link to the status page from the footer:

```tsx
// In Footer.tsx or similar
<a href="https://status.styxproxy.com" target="_blank" rel="noopener">
  Status
</a>
```

---

## Incident Workflow

### When Service Goes Down

1. **Acknowledge the alert** in Betterstack dashboard
2. **Post incident** from Betterstack:
   - Title: "Payment Processing Issues"
   - Status: "Investigating"
   - Components affected: "Checkout API"
3. **Update regularly** as you learn more:
   - "Identified: Flutterwave API timeout"
   - "Monitoring: Fix deployed"
   - "Resolved: All systems operational"
4. **Schedule incident** to auto-resolve after recovery

### Customer Communication

Customers check the status page **before** emailing support. When posting an incident:

- Be transparent about the issue
- Give realistic ETA if known
- Don't over-promise on resolution time
- Update when status changes

---

## Embedding Status Badge (Optional)

Add a "All Systems Operational" badge to your site:

```html
<a href="https://status.styxproxy.com">
  <img src="https://status.styxproxy.com/api/v1/badge" alt="Status" />
</a>
```

Or use the API for custom badge:

```bash
curl https://api.statuspage.io/v1/pages/{page_id}/components.json
```

---

## Integration with Incident Response

### Update INCIDENT_RESPONSE.md

Replace the TODO in `docs/INCIDENT_RESPONSE.md`:

```diff
- Status page: `https://styxproxy.com/status` (TODO — implement)
+ Status page: https://status.styxproxy.com
+ 
+ During P0/P1 incidents:
+ 1. Acknowledge alert in Betterstack
+ 2. Post incident with affected components
+ 3. Update as status changes
+ 4. Resolve when fully operational
```

### Betterstack API (Optional)

For programmatic incident posting:

```bash
# Create incident
curl -X POST https://api.statuspage.io/v1/pages/{page_id}/incidents \
  -H "Authorization: OAuth {api_key}" \
  -H "Content-Type: application/json" \
  -d '{
    "incident": {
      "name": "Payment Issues",
      "status": "investigating",
      "body": "We are investigating payment failures",
      "component_ids": ["abc123"]
    }
  }'
```

---

## Cost

| Tier | Price | Features |
|------|-------|----------|
| Free | $0 | 10 monitors, 1 user, status page |
| Team | $9/mo | 50 monitors, 5 users, SMS alerts |
| Business | $29/mo | Unlimited monitors, 10 users, SLA |

**Recommendation:** Start with Free tier. Upgrade when the team grows.

---

## Troubleshooting

### Monitor Not Working

1. Check endpoint returns 200 OK
2. Verify SSL certificate is valid
3. Check firewall allows Betterstack IPs

### Custom Domain Not Working

1. Verify CNAME record is correct
2. Check SSL provision status in Betterstack
3. Try with `www.status.styxproxy.com` as fallback

### Not Receiving Alerts

1. Verify phone/email in notification settings
2. Check spam folder
3. Test with "Run Check" in Betterstack dashboard

---

## Related Docs

- [INCIDENT_RESPONSE.md](./INCIDENT_RESPONSE.md) — Customer communication scripts
- [MONITORING.md](./MONITORING.md) — Internal monitoring setup
- [RUNBOOKS.md](./RUNBOOKS.md) — Operational procedures
