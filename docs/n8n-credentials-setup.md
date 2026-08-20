# n8n Credentials Setup — Telegram Order Handler

## Status

24/25 workflows active. Only **Telegram Order Handler** is inactive because it
references credentials that don't exist yet in the n8n database.

## Why it can't auto-activate

n8n 1.123's API does not expose credential creation. Credentials must be
created through the n8n UI because the bot tokens/API keys are encrypted with
a key that only the n8n instance holds. This is by design — it prevents
credentials from being exfiltrated via the API.

## What to do

Open the n8n editor at `http://162.35.184.69:5679/` (basic auth:
`dannion:styxproxy-n8n-2026`) and create these 2 credentials:

### 1. Telegram Bot API

- Go to **Settings → Credentials → Create New**
- Type: **Telegram API**
- Name: `telegram-bot-api` (must match exactly)
- Access Token: your Telegram bot token from BotFather

### 2. MiniMax API

- Type: **MiniMax API** (or use HTTP Header Auth credential type)
- Name: `minimax-api`
- For MiniMax API: enter the API key
- For HTTP Header Auth: leave the header name empty (we wire it in the
  workflow via `Authorization: Bearer {{$credentials.minimaxApiKey}}`)

## After creating credentials

1. Go back to the Telegram Order Handler workflow
2. The nodes that previously had `id: null, name: telegram-bot-api` references
   will now show credential dropdowns — pick `telegram-bot-api` for telegram
   nodes and `minimax-api` for the LLM parser
3. Click **Save** then **Activate** the workflow
4. The workflow should now show as active

## Time estimate

~5 minutes to create both credentials via the UI.

## After this is done

Once Telegram Order Handler is active, the only remaining work is:

1. Real webhook secrets (`FLUTTERWAVE_WEBHOOK_SECRET`,
   `THEOREM_REACH_WEBHOOK_SECRET`) — change in the n8n credentials
2. Optional: validate end-to-end by sending a test message to the Telegram bot
