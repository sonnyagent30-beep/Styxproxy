# Cloudflare Worker: n8n Webhook Router

## Why

n8n 1.123.x registers webhooks at URLs like:

```
/webhook/UZ88jqIYhWGndEyC/free%20trial%20whatsapp%20trigger/free-trial
```

But Flutterwave, WhatsApp, Telegram, and our existing infrastructure all
call webhooks at the legacy format:

```
/webhook/free-trial
```

This Worker sits in front of n8n on Cloudflare's edge and rewrites the
incoming legacy URL to the format n8n expects.

## Setup

### 1. Create the Worker

```bash
cd cloudflare-workers
wrangler init n8n-router --type javascript
# copy n8n-webhook-router.js into src/index.js
```

### 2. Create the KV namespace

```bash
wrangler kv:namespace create N8N_WEBHOOK_MAP
wrangler kv:namespace create N8N_WEBHOOK_MAP --preview
```

Update `wrangler.toml`:

```toml
name = "n8n-router"
main = "src/index.js"
compatibility_date = "2026-08-01"

[[kv_namespaces]]
binding = "N8N_WEBHOOK_MAP"
id = "<your-kv-id>"
preview_id = "<your-preview-kv-id>"

[triggers]
crons = ["*/5 * * * *"]  # every 5 minutes

[vars]
CHARON_INTERNAL_URL = "https://charon.styxproxy.com"
```

Set secrets:

```bash
wrangler secret put CHARON_INTERNAL_KEY
# paste your charon internal API key
```

### 3. Deploy

```bash
wrangler deploy
```

### 4. Configure DNS / Route

Add the Worker route to your Cloudflare zone for `styxproxy.com`:

```
n8n-router.styxproxy.com/*  →  Worker
```

Or, route the existing webhook path:

```
api.styxproxy.com/webhook/* → Worker (this worker)
api.styxproxy.com/api/*     → direct to backend
```

## How the routing works

### Manual seed (one-time, per workflow)

For each workflow with a webhook trigger, after it's created in n8n:

```bash
# Find the workflow's webhook URL from n8n's DB:
psql -d styxproxy -c "SELECT \"webhookPath\" FROM n8n_webhook_entity WHERE \"workflowId\" = '<wf_id>'"
# Returns: "UZ88jqIYhWGndEyC/free%20trial%20whatsapp%20trigger/free-trial"

# Parse it: workflowId = UZ88jqIYhWGndEyC, nodeSlug = free trial whatsapp trigger, path = free-trial
# Slugify the node name with the same rules n8n uses

wrangler kv:key put --binding N8N_WEBHOOK_MAP 'webhook:free-trial' '{
  "workflowId": "UZ88jqIYhWGndEyC",
  "nodeSlug": "free-trial-whatsapp-trigger",
  "methodsAllowed": ["POST"]
}'
```

### Automated sync (every 5 min)

The Worker's `scheduled` handler calls `syncWebhookMap`, which:
1. Fetches all active webhooks from charon's `/admin/internal/webhooks` endpoint
2. Parses the n8n URL format to extract `{workflowId, nodeSlug, actualPath}`
3. Writes each entry to KV

The KV lookup at request time uses just the `actualPath` to find the routing entry.

### What happens on a request

```
1. POST /webhook/free-trial (from Flutterwave)
   ↓
2. Worker: extract "free-trial" as webhookPath
3. KV lookup: webhook:free-trial → { workflowId, nodeSlug }
4. Rewrite URL to /webhook/<wfId>/<nodeSlug>/free-trial
5. Forward to n8n origin
   ↓
6. n8n matches the workflow and runs it
```

## Failure modes

| Scenario | Behavior |
|---|---|
| KV lookup miss | Return 404 with JSON error (don't leak to origin) |
| KV lookup timeout | Fall through to origin with original URL — better than dropping on KV outage |
| Method not allowed | Return 405 with `Allow` header |
| Webhook path empty | Return 400 |
| charon sync fails | Log error, continue serving from existing KV |
| KV stale entry | Stale entry persists until manual delete or next sync overwrites it (KV values for a key are replaced on put, so duplicates collapse) |

## Why this is the right call vs other options

- **Downgrade to n8n 1.69.2:** Risky — unknown webhook behavior, possible other incompatibilities with our 25 workflow JSONs
- **Skip Track 1 entirely:** Defers production webhooks indefinitely
- **Change provider webhook URLs to n8n's new pattern:** Brittle — workflow IDs are random, change on every reimport, and we'd have to update 25+ provider configs every time

The Worker is the smallest blast-radius fix that:
- Keeps n8n current and secure
- Lets us update workflows without touching provider configs
- Gives us one place to add rate limiting / auth / logging later

## Future improvements (out of scope for v1)

- HMAC signature verification before KV lookup (reject bad signatures early)
- Per-webhook rate limiting (KV counter with TTL)
- Webhook replay protection (Redis-backed)
- Method whitelisting per workflow
- Path templates (e.g., `/webhook/order/{order_id}` → dynamic n8n path)
