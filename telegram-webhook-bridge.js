#!/usr/bin/env node
/**
 * Bunche Telegram Webhook Bridge
 * Receives Telegram updates → forwards to n8n for processing
 * 
 * Run: node telegram-webhook-bridge.js
 * Set webhook: https://api.telegram.org/bot<TOKEN>/setWebhook?url=https://your-public-url/telegram
 */

const https = require('https');
const http = require('http');
const crypto = require('crypto');
const express = require('express');

const app = express();
app.use(express.json());

const PORT = process.env.TELEGRAM_WEBHOOK_PORT || 3099;
const N8N_URL = process.env.N8N_URL || 'http://127.0.0.1:5678';
const TELEGRAM_BOT_TOKEN = process.env.TELEGRAM_BOT_TOKEN;
const TELEGRAM_SECRET = process.env.TELEGRAM_SECRET || crypto.randomBytes(32).toString('hex');
const ALLOWED_CHAT_IDS = (process.env.ALLOWED_CHAT_IDS || '').split(',').filter(Boolean);
const ADMIN_CHAT_ID = process.env.ADMIN_CHAT_ID;

// ─── Telegram API helper ────────────────────────────────────────────────────

function telegramApi(method, data = {}) {
  return new Promise((resolve, reject) => {
    if (!TELEGRAM_BOT_TOKEN) {
      return reject(new Error('TELEGRAM_BOT_TOKEN not set'));
    }
    const body = JSON.stringify(data);
    const options = {
      hostname: 'api.telegram.org',
      port: 443,
      path: `/bot${TELEGRAM_BOT_TOKEN}/${method}`,
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Content-Length': Buffer.byteLength(body),
      },
    };
    const req = https.request(options, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        try {
          const json = JSON.parse(data);
          resolve(json);
        } catch (e) {
          reject(e);
        }
      });
    });
    req.on('error', reject);
    req.setTimeout(10000, () => { req.destroy(); reject(new Error('Telegram API timeout')); });
    req.end(body);
  });
}

// ─── Forward to n8n ────────────────────────────────────────────────────────

async function forwardToN8n(payload) {
  return new Promise((resolve, reject) => {
    const body = JSON.stringify(payload);
    const url = new URL('/webhook/telegram-incoming', N8N_URL);
    const options = {
      hostname: url.hostname,
      port: url.port || 443,
      path: url.pathname,
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Content-Length': Buffer.byteLength(body),
      },
    };
    const req = https.request(options, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => resolve({ status: res.statusCode, body: data }));
    });
    req.on('error', reject);
    req.setTimeout(30000, () => { req.destroy(); reject(new Error('n8n timeout')); });
    req.end(body);
  });
}

// ─── Send message to customer ───────────────────────────────────────────────

async function sendMessage(chatId, text, replyMarkup = null) {
  const data = { chat_id: chatId, text, parse_mode: 'HTML' };
  if (replyMarkup) data.reply_markup = replyMarkup;
  return telegramApi('sendMessage', data);
}

// ─── Send to admin ─────────────────────────────────────────────────────────

async function notifyAdmin(message) {
  if (!ADMIN_CHAT_ID) return;
  try {
    await sendMessage(ADMIN_CHAT_ID, message);
  } catch (e) {
    console.error('Admin notification failed:', e.message);
  }
}

// ─── Webhook verification (Telegram sets webhook) ─────────────────────────

app.get('/webhook', async (req, res) => {
  if (req.query.secret !== TELEGRAM_SECRET) {
    return res.status(403).send('Forbidden');
  }
  res.send('OK');
});

// ─── Telegram webhook receiver ─────────────────────────────────────────────

app.post('/telegram', async (req, res) => {
  // Acknowledge immediately
  res.send('OK');

  try {
    const update = req.body;
    
    // Ignore non-message updates
    if (!update.message && !update.edited_message && !update.callback_query) {
      return;
    }

    const message = update.message || update.edited_message || update.callback_query;
    const chatId = message.chat.id;
    const text = message.text || '';
    const firstName = message.from.first_name || 'there';

    // Anti-loop: ignore bot's own messages
    if (message.from.is_bot) {
      console.log(`[${new Date().toISOString()}] Ignoring bot message`);
      return;
    }

    console.log(`[${new Date().toISOString()}] Telegram from ${chatId}: ${text}`);

    // Forward to n8n for full processing
    const n8nPayload = {
      update_id: update.update_id,
      message: {
        chat: { id: chatId },
        from: { first_name: firstName },
        text: text,
        date: message.date,
      },
      source: 'telegram',
    };

    await forwardToN8n(n8nPayload);
    console.log(`[${new Date().toISOString()}] Forwarded update ${update.update_id} to n8n`);

    // Admin notification for new conversations
    if (text.startsWith('/start')) {
      await notifyAdmin(`🆕 New Telegram customer: ${firstName} (${chatId})`);
    }

  } catch (error) {
    console.error(`[${new Date().toISOString()}] Error:`, error.message);
  }
});

// ─── Health check ───────────────────────────────────────────────────────────

app.get('/health', (req, res) => {
  res.json({
    status: 'ok',
    uptime: process.uptime(),
    timestamp: new Date().toISOString(),
    telegram_bot: TELEGRAM_BOT_TOKEN ? 'configured' : 'missing',
    n8n_target: N8N_URL,
  });
});

// ─── Channel status (used by failover router) ───────────────────────────────

app.get('/channel-status', async (req, res) => {
  try {
    // Check Telegram
    let telegramOk = false;
    try {
      const tg = await telegramApi('getMe');
      telegramOk = tg.ok === true;
    } catch {}

    res.json({
      timestamp: new Date().toISOString(),
      telegram: { available: telegramOk },
      primary: telegramOk ? 'telegram' : 'none',
      failover_cta: 'https://wa.me/2347032981049',
    });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// ─── Admin commands ───────────────────────────────────────────────────────

app.post('/admin', async (req, res) => {
  const { chat_id, command } = req.body;
  
  if (String(chat_id) !== String(ADMIN_CHAT_ID)) {
    return res.status(403).json({ error: 'Unauthorized' });
  }

  try {
    switch (command) {
      case 'stats':
        const tg = await telegramApi('getMe');
        const updates = await telegramApi('getUpdates', { limit: 1 });
        res.json({
          bot_name: tg.result?.first_name,
          username: tg.result?.username,
          last_update_id: updates.result?.[0]?.update_id || 'none',
        });
        break;
      case 'broadcast':
        // TODO: broadcast to all customers
        res.json({ message: 'Broadcast not yet implemented' });
        break;
      default:
        res.json({ available_commands: ['stats', 'broadcast'] });
    }
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// ─── Start server ─────────────────────────────────────────────────────────

if (!TELEGRAM_BOT_TOKEN) {
  console.error('ERROR: TELEGRAM_BOT_TOKEN environment variable is required');
  console.error('Get it from @BotFather on Telegram');
  process.exit(1);
}

app.listen(PORT, '0.0.0.0', () => {
  console.log(`Bunche Telegram Webhook Bridge`);
  console.log(`Listening on port ${PORT}`);
  console.log(`Forwarding to n8n at ${N8N_URL}`);
  console.log(`Webhook secret: ${TELEGRAM_SECRET}`);
  console.log();
  console.log(`To set Telegram webhook, run this curl command:`);
  console.log(`curl "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/setWebhook?url=https://YOUR_PUBLIC_DOMAIN/telegram&secret_token=${TELEGRAM_SECRET}"`);
  console.log();
  console.log(`Health check: http://localhost:${PORT}/health`);
  console.log(`Channel status: http://localhost:${PORT}/channel-status`);
});

// Graceful shutdown
process.on('SIGTERM', () => {
  console.log('Shutting down...');
  process.exit(0);
});
