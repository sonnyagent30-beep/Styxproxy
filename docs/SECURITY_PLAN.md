# Bunche — Security Plan

**Last Updated:** 2026-06-26  
**Status:** Planning Complete — Ready for Implementation

---

## Overview

Security for Bunche is implemented in layers. No single layer is sufficient — together they provide defense in depth.

```
Layer 1: Cloudflare — Network edge protection
Layer 2: Nginx — TLS + per-endpoint rate limits
Layer 3: n8n — Application logic + verification
Layer 4: Redis — Session + rate limit enforcement
Layer 5: PostgreSQL — Audit trail + immutable logs
```

---

## Layer 1: Cloudflare (Free Tier)

### What It Does
- DDoS protection at network edge
- Bot detection (Bot Fight Mode)
- Rate limiting per IP
- Blocks traffic before it reaches VPS

### Setup (30 minutes — Dashboard only)

**Rule 1: WhatsApp Webhook**
```
Field: Request URI
Operator: contains
Value: /webhook/whatsapp-incoming

Rate: 20 requests/minute per IP
Action: Challenge (CAPTCHA)
```

**Rule 2: Flutterwave Webhook**
```
Field: Request URI
Operator: contains
Value: /webhook/flutterwave-payment

Rate: 100 requests/minute per IP
Action: Block
```

**Rule 3: CPAGrip Postback**
```
Field: Request URI
Operator: contains
Value: /webhook/cpagrip-postback

Rate: 50 requests/minute per IP
Action: Challenge
```

**Enable:** Security → Bots → Bot Fight Mode → On

---

## Layer 2: Nginx

### What It Does
- TLS termination (HTTPS)
- Per-endpoint rate limiting
- Security headers
- Basic auth for admin area

### Configuration

```nginx
# Rate limit zones
limit_req_zone $binary_remote_addr zone=whatsapp_ip:10m rate=20r/m;
limit_req_zone $binary_remote_addr zone=flutterwave_ip:10m rate=100r/m;
limit_req_zone $binary_remote_addr zone=cpagrip_ip:10m rate=50r/m;
limit_req_zone $binary_remote_addr zone=general_ip:10m rate=60r/m;
limit_conn_zone $binary_remote_addr zone=conn_limit:10m;

# HTTPS server
server {
    listen 443 ssl http2;
    server_name n8n.bunche.com;
    
    ssl_certificate /etc/letsencrypt/live/n8n.bunche.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/n8n.bunche.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    
    # Security headers
    add_header Strict-Transport-Security "max-age=31536000" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    
    # Max concurrent connections per IP
    limit_conn conn_limit 10;
    
    # WhatsApp webhook
    location /webhook/whatsapp-incoming {
        limit_req zone=whatsapp_ip burst=10 nodelay;
        proxy_pass http://localhost:5678;
    }
    
    # Flutterwave webhook
    location /webhook/flutterwave-payment {
        limit_req zone=flutterwave_ip burst=20 nodelay;
        proxy_pass http://localhost:5678;
    }
    
    # CPAGrip postback
    location /webhook/cpagrip-postback {
        limit_req zone=cpagrip_ip burst=10 nodelay;
        proxy_pass http://localhost:5678;
    }
    
    # Admin area — basic auth required
    location /admin/ {
        auth_basic "Admin Area";
        auth_basic_user_file /etc/nginx/.htpasswd;
        limit_req zone=general_ip burst=5 nodelay;
        proxy_pass http://localhost:5678;
    }
}
```

### HTTP → HTTPS Redirect

```nginx
server {
    listen 80;
    server_name n8n.bunche.com;
    return 301 https://$server_name$request_uri;
}
```

---

## Layer 3: Webhook Signature Verification

### What It Does
Verifies that webhooks actually come from the claimed provider (Meta, Flutterwave, CPAGrip). Prevents anyone from forging webhooks.

### Providers & Verification Methods

| Provider | Header | Algorithm | Secret |
|----------|--------|-----------|--------|
| WhatsApp | X-Hub-Signature-256 | HMAC-SHA256 | WhatsApp App Secret |
| Flutterwave | verif-hash | HMAC-SHA256 | Flutterwave Secret Hash |
| CPAGrip | signature (query param) | HMAC-SHA256 | CPAGrip Secret |

### Implementation (n8n Code Node)

```javascript
// Runs FIRST in every webhook workflow (before any other logic)
const crypto = require('crypto');

function verifyWebhookSignature(headers, body, secret, provider) {
  let signature;
  
  if (provider === 'whatsapp') {
    signature = headers['x-hub-signature-256'];
    if (!signature?.startsWith('sha256=')) {
      return { valid: false, reason: 'Missing signature header' };
    }
    signature = signature.replace('sha256=', '');
  } 
  else if (provider === 'flutterwave') {
    signature = headers['verif-hash'];
    if (!signature) {
      return { valid: false, reason: 'Missing verif-hash header' };
    }
  }
  else if (provider === 'cpagrip') {
    signature = headers['signature'] || body?.signature;
    if (!signature) {
      return { valid: false, reason: 'Missing signature parameter' };
    }
  }
  
  const expected = crypto
    .createHmac('sha256', secret)
    .update(JSON.stringify(body))
    .digest('hex');
  
  // Constant-time comparison (prevents timing attacks)
  const valid = crypto.timingSafeEqual(
    Buffer.from(signature),
    Buffer.from(expected)
  );
  
  return { valid, reason: valid ? 'OK' : 'Signature mismatch' };
}

// Main execution
const headers = $input.first().json.headers;
const body = $input.first().json.body;
const webhookPath = headers['x-webhook-path'] || '';

let provider, secret;
if (webhookPath.includes('whatsapp')) {
  provider = 'whatsapp';
  secret = process.env.WHATSAPP_APP_SECRET;
} else if (webhookPath.includes('flutterwave')) {
  provider = 'flutterwave';
  secret = process.env.FLUTTERWAVE_SECRET_HASH;
} else if (webhookPath.includes('cpagrip')) {
  provider = 'cpagrip';
  secret = process.env.CPAGRIP_SECRET;
}

const result = verifyWebhookSignature(headers, body, secret, provider);

if (!result.valid) {
  // Log failed attempt
  await db.query(`
    INSERT INTO webhook_security_log 
    (provider, verified, failure_reason, ip_address, user_agent, request_id)
    VALUES ($1, false, $2, $3, $4, $5, NOW())
  `, [provider, result.reason, headers['x-forwarded-for'], headers['user-agent'], crypto.randomUUID()]);
  
  return {
    statusCode: 401,
    body: JSON.stringify({ error: 'Invalid signature' })
  };
}

// Signature valid — continue
return { json: { verified: true, body } };
```

### Anti-Replay Check

```javascript
// Reject webhooks older than 5 minutes
const webhookTimestamp = body?.entry?.[0]?.changes?.[0]?.value?.messages?.[0]?.timestamp;
const now = Math.floor(Date.now() / 1000);

if (webhookTimestamp && Math.abs(now - parseInt(webhookTimestamp)) > 300) {
  return {
    statusCode: 401,
    body: JSON.stringify({ error: 'Webhook timestamp too old' })
  };
}
```

---

## Layer 4: Payment Webhook Idempotency

### What It Does
Prevents duplicate processing when the same webhook is received multiple times (retries, network issues).

### Storage: Redis (Fast) + PostgreSQL (Permanent)

### Redis Keys
```
webhook:processed:{provider}:{webhook_id} → Timestamp (TTL: 24h)
```

### PostgreSQL Table
```sql
CREATE TABLE processed_webhooks (
    id BIGSERIAL PRIMARY KEY,
    webhook_id VARCHAR(100) UNIQUE NOT NULL,
    provider VARCHAR(20),
    event_type VARCHAR(50),
    processed_at TIMESTAMPTZ DEFAULT NOW(),
    response_sent BOOLEAN DEFAULT FALSE,
    metadata JSONB
);
```

### Implementation

```javascript
async function isWebhookProcessed(provider, webhookId) {
  const redisKey = `webhook:processed:${provider}:${webhookId}`;
  
  // Fast check: Redis
  const cached = await redis.get(redisKey);
  if (cached) return { processed: true, source: 'redis' };
  
  // Permanent check: PostgreSQL
  const result = await pgClient.query(
    'SELECT id FROM processed_webhooks WHERE webhook_id = $1 AND provider = $2',
    [webhookId, provider]
  );
  
  if (result.rows.length > 0) {
    await redis.setex(redisKey, 86400, new Date().toISOString());
    return { processed: true, source: 'postgres' };
  }
  
  return { processed: false };
}

async function markWebhookProcessed(provider, webhookId, eventType, metadata) {
  const redisKey = `webhook:processed:${provider}:${webhookId}`;
  
  await redis.setex(redisKey, 86400, new Date().toISOString());
  
  await pgClient.query(`
    INSERT INTO processed_webhooks (webhook_id, provider, event_type, metadata)
    VALUES ($1, $2, $3, $4)
    ON CONFLICT (webhook_id) DO NOTHING
  `, [webhookId, provider, eventType, JSON.stringify(metadata)]);
}
```

### Race Condition Protection

```javascript
async function atomicMarkProcessing(provider, webhookId) {
  const redisKey = `webhook:processing:${provider}:${webhookId}`;
  
  // SETNX = Set if Not eXists (atomic)
  const acquired = await redis.set(redisKey, '1', 'NX', 'EX', 60);
  
  if (!acquired) {
    return { acquired: false, reason: 'concurrent_processing' };
  }
  
  return { acquired: true };
}
```

### Webhook IDs by Provider

| Provider | Unique ID Used |
|----------|---------------|
| Flutterwave | `tx_ref` |
| WhatsApp | `message_id` |
| CPAGrip | `{user_id}:{survey_id}` |

---

## Layer 5: Admin Command Authentication

### Session Flow

```
Admin sends message
        ↓
No session → "🔒 Enter PIN to access admin panel"
        ↓
Admin enters PIN → 30-min session starts
        ↓
Session active → Execute command
        ↓
30 min inactivity → Session expires
        ↓
Admin sends message → "🔒 Session expired. Enter PIN."
```

### Command Risk Levels

| Level | Commands | Auth Required |
|-------|----------|---------------|
| **Low** | Pending, Provider Status, Errors, Daily summary | Active session |
| **Medium** | Block, Unblock, Resolve, Details | Fresh PIN (2 min) |
| **High** | Refund, Force-Refund, Approve, Reject | PIN + TOTP every time |

### Session Rules

| Rule | Value |
|------|-------|
| Session timeout | 30 minutes inactivity |
| Timer reset | Every successful command |
| High-risk auth | PIN + TOTP (every time, no session caching) |
| Alert delivery | Always sent — admin must PIN to respond |

### Lockout Policy

| Failed Attempts | Lockout |
|----------------|---------|
| 3 in 10 minutes | 15 minutes |
| 5 in 1 hour | 1 hour |
| 10 in 24 hours | 24 hours |

### Session Management (Redis)

```javascript
// Create session after PIN verification
async function createAdminSession(adminPhone, ipAddress) {
  const sessionId = crypto.randomUUID();
  const sessionKey = `admin:session:${adminPhone}`;
  
  const sessionData = {
    session_id: sessionId,
    admin_phone: adminPhone,
    created_at: new Date().toISOString(),
    last_activity: new Date().toISOString(),
    ip_address: ipAddress,
    commands_used: 0
  };
  
  // 30-minute TTL
  await redis.setex(sessionKey, 1800, JSON.stringify(sessionData));
  await redis.sadd('admin:active_sessions', adminPhone);
  
  return { success: true, session_id: sessionId, expires_in: 1800 };
}

// Validate session before command
async function validateAdminSession(adminPhone) {
  const sessionKey = `admin:session:${adminPhone}`;
  const sessionData = await redis.get(sessionKey);
  
  if (!sessionData) return { valid: false, reason: 'no_session' };
  
  const session = JSON.parse(sessionData);
  const minutesSinceActivity = (Date.now() - new Date(session.last_activity)) / 60000;
  
  if (minutesSinceActivity > 30) {
    await redis.del(sessionKey);
    return { valid: false, reason: 'expired' };
  }
  
  // Update activity (resets timer)
  session.last_activity = new Date().toISOString();
  session.commands_used += 1;
  await redis.setex(sessionKey, 1800, JSON.stringify(sessionData));
  
  return { valid: true, session_id: session.session_id };
}
```

### PIN Verification (bcrypt)

```javascript
const bcrypt = require('bcrypt');

async function verifyPIN(adminPhone, pin) {
  const result = await pgClient.query(
    'SELECT pin_hash, failed_attempts, locked_until FROM admin_auth WHERE admin_phone = $1',
    [adminPhone]
  );
  
  if (result.rows.length === 0) return { valid: false, reason: 'admin_not_found' };
  
  const auth = result.rows[0];
  
  // Check lockout
  if (auth.locked_until && new Date() < auth.locked_until) {
    return { 
      valid: false, 
      reason: 'locked',
      remaining_minutes: Math.ceil((auth.locked_until - new Date()) / 60000)
    };
  }
  
  const valid = await bcrypt.compare(pin, auth.pin_hash);
  
  if (valid) {
    await pgClient.query(`
      UPDATE admin_auth SET failed_attempts = 0, locked_until = NULL, last_used = NOW()
      WHERE admin_phone = $1
    `, [adminPhone]);
    return { valid: true };
  }
  
  // Increment failed attempts
  const newAttempts = auth.failed_attempts + 1;
  let lockedUntil = null;
  
  if (newAttempts >= 10) lockedUntil = new Date(Date.now() + 24 * 60 * 60 * 1000);
  else if (newAttempts >= 5) lockedUntil = new Date(Date.now() + 60 * 60 * 1000);
  else if (newAttempts >= 3) lockedUntil = new Date(Date.now() + 15 * 60 * 1000);
  
  await pgClient.query(`
    UPDATE admin_auth SET failed_attempts = $1, locked_until = $2 WHERE admin_phone = $3
  `, [newAttempts, lockedUntil, adminPhone]);
  
  return { valid: false, attempts_left: Math.max(0, 3 - newAttempts) };
}
```

### TOTP Verification (speakeasy)

```javascript
const speakeasy = require('speakeasy');

function decryptTOTPSecret(encrypted) {
  const key = Buffer.from(process.env.TOTP_ENCRYPTION_KEY, 'hex');
  const [iv, authTag, ciphertext] = encrypted.split(':');
  const decipher = crypto.createDecipheriv('aes-256-gcm', key, Buffer.from(iv, 'hex'));
  decipher.setAuthTag(Buffer.from(authTag, 'hex'));
  let decrypted = decipher.update(Buffer.from(ciphertext, 'hex'));
  decrypted = Buffer.concat([decrypted, decipher.final()]);
  return decrypted.toString();
}

async function verifyTOTP(adminPhone, totpCode) {
  const result = await pgClient.query(
    'SELECT totp_secret, totp_enabled FROM admin_auth WHERE admin_phone = $1',
    [adminPhone]
  );
  
  if (!result.rows[0]?.totp_enabled) return { valid: false, reason: 'totp_not_enabled' };
  
  const secret = decryptTOTPSecret(result.rows[0].totp_secret);
  
  const valid = speakeasy.totp.verify({
    secret: secret,
    encoding: 'hex',
    token: totpCode,
    window: 1  // 30 seconds before/after
  });
  
  return { valid };
}
```

### Admin Commands (Updated)

| Command | Risk Level | Auth |
|---------|-----------|------|
| Pending | Low | Session |
| Provider Status | Low | Session |
| Errors | Low | Session |
| Daily Summary | Low | Session |
| Block [phone] [reason] | Medium | Fresh PIN |
| Unblock [phone] | Medium | Fresh PIN |
| Resolve ERR-XXXXX | Medium | Fresh PIN |
| Details ORD-XXXXX | Medium | Fresh PIN |
| Refund ORD-XXXXX | High | PIN + TOTP |
| Force-Refund ORD-XXXXX | High | PIN + TOTP |
| Approve ORD-XXXXX | High | PIN + TOTP |
| Reject ORD-XXXXX | High | PIN + TOTP |
| Admin Status | Low | Session |
| Admin Logout | Low | Session |
| Change PIN | High | PIN + TOTP |

---

## Layer 6: Redis Rate Limiting (Phone-Based)

### What It Does
Per-customer rate limiting in n8n. Catches customers who bypass Cloudflare/Nginx by using different IPs.

### Limits

| Endpoint | Phone Limit | Window |
|----------|-------------|--------|
| WhatsApp incoming | 20 messages | 1 minute |
| Flutterwave payment | N/A (IP-based only) | — |
| CPAGrip postback | 10 surveys | 1 minute |

### Implementation

```javascript
async function checkPhoneRateLimit(phone, endpoint, limit, windowSeconds) {
  const key = `ratelimit:phone:${endpoint}:${phone}`;
  const now = Date.now();
  const windowStart = now - (windowSeconds * 1000);
  
  const pipe = redis.multi();
  pipe.zremrangebyscore(key, 0, windowStart);
  pipe.zcard(key);
  pipe.zadd(key, now, `${now}-${Math.random()}`);
  pipe.expire(key, windowSeconds + 10);
  
  const results = await pipe.exec();
  const currentCount = results[1];
  
  return {
    allowed: currentCount < limit,
    current: currentCount,
    limit: limit,
    remaining: Math.max(0, limit - currentCount - 1)
  };
}

// Customer message when blocked
if (!result.allowed) {
  return {
    json: {
      rate_limited: true,
      message: "You're sending messages too quickly. Please wait 1 minute.",
      retry_after: 60
    }
  };
}
```

---

## Security Checklist

| Item | Status |
|------|--------|
| HTTPS enabled (Let's Encrypt) | Required |
| HTTP redirects to HTTPS | Required |
| TLS 1.2+ only | Required |
| Cloudflare rate limiting | Required |
| Nginx rate limiting | Required |
| Redis phone rate limiting | Required |
| Webhook signature verification | Required |
| Payment webhook idempotency | Required |
| n8n basic auth enabled | Required |
| Strong admin password (32+ chars) | Required |
| User accounts with roles | Required |
| 2FA on admin account | Required |
| Admin PIN + TOTP system | Required |
| Session timeout (30 min) | Required |
| Lockout policy | Required |
| PostgreSQL SSL enabled | Required |
| Redis password enabled | Required |
| TOTP secrets encrypted at rest | Required |
| API keys in environment variables | Required |
| Certificate auto-renewal | Required |
| Daily backup to R2 | Required |

---

## What This Prevents

| Attack | Layers That Block |
|--------|------------------|
| DDoS attack | Cloudflare + Nginx |
| Bot scraping | Cloudflare (Bot Fight Mode) |
| Webhook forgery | Signature verification |
| Duplicate payments | Idempotency |
| Customer spam | All 3 rate limit layers |
| SIM swap (admin) | PIN + TOTP |
| Brute force PIN | Lockout policy |
| Session hijacking | 30-min timeout, HTTPS |
| Man-in-the-middle | TLS 1.2+, HSTS |
| Database breach | SSL, encrypted secrets |
| Data scraping | Rate limiting, session auth |

---

## Effort Breakdown

| Component | Time |
|-----------|------|
| Cloudflare setup | 30 min |
| Nginx + HTTPS | 2 hours |
| Webhook signature verification | 4 hours |
| Payment idempotency | 4 hours |
| Rate limiting (3 layers) | 7 hours |
| Admin auth (PIN + TOTP) | 8 hours |
| Redis session management | 4 hours |
| n8n authentication | 1 hour |
| Testing | 4 hours |
| **Total** | **~35 hours** |
