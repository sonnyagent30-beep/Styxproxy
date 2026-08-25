# Staging n8n Workflows

This directory contains staging-only n8n workflow files for the Styxproxy project. These workflows are designed to be imported into a separate staging n8n instance (port 5679) and do NOT interact with production systems.

## Files Overview

| File | Description |
|------|-------------|
| `01-channel-intent-router.json` | Template workflow with env-var driven channel routing. All paths/parameters use `$env.VAR` format. Contains a Code node that switches on `REPLY_NODE_TYPE` (telegram/baileys). |
| `02-telegram-order-staging.json` | Telegram order handler with webhook trigger at `telegram-order-staging`. Includes HMAC verification, Redis idempotency check (staging: prefix), MiniMax LLM parsing, and Telegram reply using `TELEGRAM_BOT_TOKEN_STAGING`. |
| `03-whatsapp-baileys-staging.json` | WhatsApp/Baileys handler with webhook trigger at `whatsapp-baileys-staging`. Accepts Baileys-style POST body, parses via MiniMax LLM, replies via HTTP webhook to `BAILEYS_RUNTIME_URL`. |
| `04-shared-checkout-staging.json` | Unified checkout handler at `checkout-staging`. Same business logic as 02/03 but routes to BOTH Telegram and WhatsApp replies (mirror pattern). |
| `05-channel-failover-staging.json` | Active health check running every 5 minutes via Cron. Pings Baileys + Telegram, stores health in Redis with `staging:channel:health:` prefix. Triggers alert webhook if either channel is down >5min. |

## Tagging Convention

All workflows are tagged with:
- `"staging"` — indicates this is a staging workflow
- Channel name: `"telegram"`, `"whatsapp"`, `"baileys"`, `"shared"`, or `"resilience"`

Example: `["staging", "telegram", "order"]`

## Key Design Change from Production

**All staging workflows include HMAC secret verification as the FIRST node** (before any business logic).

This is the critical difference from production workflows:

```javascript
// HMAC verification Code node (always first)
const crypto = require('crypto');
const signature = $input.item.json.headers?.['x-signature'];
const hmacSecret = process.env.HMAC_SECRET_STAGING;
const body = JSON.stringify($input.item.json.body || $input.item.json);
const expectedSignature = 'sha256=' + crypto.createHmac('sha256', hmacSecret).update(body).digest('hex');
// ... verify and throw if mismatch
```

Production workflows may have HMAC verification later in the chain or not at all. Staging workflows enforce it at entry.

## Import to n8n UI (3 Steps)

1. **Open Staging n8n**: Navigate to `http://<staging-server>:5679/` (or your configured staging URL)

2. **Import Workflow**:
   - Click "Import from File" button (or use keyboard shortcut `Ctrl+I`)
   - Select the JSON file from this directory
   - The workflow will appear in the editor

3. **Configure & Activate**:
   - Review the webhook path (must end with `-staging`)
   - Configure credentials (Telegram Bot API, PostgreSQL staging user, Redis)
   - Set required environment variables in n8n (or create credential references)
   - Click "Activate" to enable the workflow

## Environment Variables Required

| Variable | Purpose | Example |
|----------|---------|---------|
| `HMAC_SECRET_STAGING` | HMAC signing secret for webhook verification | `whsec_...` |
| `TELEGRAM_BOT_TOKEN_STAGING` | Telegram bot token (DIFFERENT from prod) | `12345:ABC...` |
| `BAILEYS_RUNTIME_URL` | Base URL for Baileys WhatsApp runtime | `http://localhost:3001` |
| `MINIMAX_API_KEY` | MiniMax LLM API key | `Bearer ...` |
| `STAGING_ERROR_ALERT_WEBHOOK_URL` | Webhook URL for error alerts | `https://.../webhook/...` |
| `IDEMPOTENCY_PREFIX` | Redis key prefix (defaults to `staging:`) | `staging:` |

## Staging vs Production Isolation

- **Webhook paths**: All end with `-staging` (e.g., `telegram-order-staging`)
- **Idempotency keys**: All prefixed with `staging:` (e.g., `staging:idempotency:telegram:123`)
- **Redis keys**: Health checks use `staging:channel:health:` prefix
- **Telegram bot**: Uses `TELEGRAM_BOT_TOKEN_STAGING` — NEVER reuse production token
- **Database**: Use `styxproxy_staging_n8n` credential (non-superuser)

## Credential Setup Notes

Before importing, ensure these credentials exist in staging n8n:

1. **PostgreSQL**: Create `styxproxy_staging_n8n` user with limited permissions
2. **Redis**: Staging instance (separate from production Redis if possible)
3. **Telegram Bot API**: Create new bot via @BotFather for staging
4. **HTTP Header Auth**: For MiniMax API calls

## Validation

Each JSON file can be validated with:

```bash
python3 -c "import json; d=json.load(open('02-telegram-order-staging.json')); print(len(d.get('nodes',[])), 'nodes')"
```

Expected outputs:
- 01-channel-intent-router.json: 16 nodes
- 02-telegram-order-staging.json: 17 nodes
- 03-whatsapp-baileys-staging.json: 18 nodes
- 04-shared-checkout-staging.json: 20 nodes
- 05-channel-failover-staging.json: 13 nodes
