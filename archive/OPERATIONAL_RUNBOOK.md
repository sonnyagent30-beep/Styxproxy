# Bunche — Operational Runbook (Archived)
*This file is obsolete. Kept for historical reference only.*

---

## Daily Operations

### Morning Check (9 AM)
- [ ] Check Flutterwave dashboard for yesterday's revenue
- [ ] Check provider credit balances (Proxy-Seller + DataImpulse)
- [ ] Confirm all n8n workflows are active

### Error Monitoring
- WhatsApp alerts from n8n Error Trigger for any workflow failures
- Check error_log for patterns

### Provider Balance Checks
| Provider | Min Balance | Alert If Below |
|----------|------------|----------------|
| Proxy-Seller | $10 | $10 |
| DataImpulse | $10 | $10 |

---

## Common Issues

### Payment webhook not firing
1. Check Flutterwave dashboard → Webhooks → URL is correct
2. Test webhook from dashboard
3. Check n8n execution log

### WhatsApp messages not reaching n8n
1. Check Meta Business Console → Webhooks → subscribed events
2. Confirm webhook URL is HTTPS
3. Check verify token matches

### Proxy test failing after payment
1. Check provider API is responding
2. Check provider balance
3. Check n8n execution log for specific error

---

## This file was moved from `docs/OPERATIONAL_RUNBOOK.md` on 2026-06-26.
Daily operations now documented in `docs/DEPLOYMENT.md`.
The provider list (OkeyProxy) in this file is obsolete.
