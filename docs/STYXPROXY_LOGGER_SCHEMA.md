# Styxproxy Logger — JSON Schema

**Date:** 2026-06-27
**Status:** LOCKED
**Source:** Required by WORKFLOW_SPECS §11 + DEAD_IP_REPLACEMENT_POLICY retry logging

---

## Purpose

Styxproxy's central logger writes structured events to PostgreSQL `customer_audit_log` table. Every workflow execution logs at least one event. The schema below defines what fields are written.

---

## Base Schema (All Events)

```json
{
  "event_id": "uuid-v4-string",
  "timestamp": "2026-06-27T14:23:18Z",
  "workflow": "Workflow 2 - Payment Confirmation",
  "workflow_id": "wf-payment-confirmation",
  "event_type": "order_fulfilled",
  "status": "success",
  "customer_hash": "a3f2b9c1e8d4f5a6b7c8",
  "duration_ms": 1234,
  "order_id": "ORD-20260627-0917",
  "correlation_id": "req-uuid-1234",
  "n8n_execution_id": "exec-5678",
  "metadata": {}
}
```

---

## Event Types + Metadata

### Customer Events

#### `customer_created`
```json
{
  "metadata": {
    "source": "whatsapp_first_message",
    "phone_hash": "a3f2b9c1e8d4f5a6b7c8",
    "name": null
  }
}
```

#### `name_set`
```json
{
  "metadata": {
    "old_name_hash": "5d4e3c2b1a0987654321",
    "new_name": "Dan",
    "is_unique": true
  }
}
```

#### `pin_set`
```json
{
  "metadata": {
    "pin_hash_prefix": "$2b$10$",
    "is_change": false
  }
}
```

#### `pin_failed`
```json
{
  "metadata": {
    "attempt_number": 1,
    "remaining_attempts": 2,
    "locked_after": false
  }
}
```

### Order Events

#### `order_created`
```json
{
  "metadata": {
    "product": "ISP_UK",
    "quantity": 1,
    "amount_ngn": 6500,
    "referred_by_name": "Ada",
    "tx_ref": "ORD-20260627-0917"
  }
}
```

#### `order_fulfilled`
```json
{
  "metadata": {
    "product": "ISP_UK",
    "provider": "Proxy-Seller",
    "provider_order_id": "PS-8392",
    "proxy_ip_hash": "5a4b3c2d1e0987654321",
    "proxy_port": 8000,
    "expires_at": "2026-07-27T00:00:00Z",
    "retry_count": 0
  }
}
```

#### `order_fulfilled_after_retry`
```json
{
  "metadata": {
    "product": "ISP_UK",
    "provider": "Proxy-Seller",
    "retry_count": 1,
    "first_failure_reason": "ip_timeout_5s"
  }
}
```

#### `order_refunded_dead_ip`
```json
{
  "metadata": {
    "product": "ISP_UK",
    "provider": "Proxy-Seller",
    "amount_refunded_ngn": 6500,
    "attempt_count": 4,
    "failure_reasons": ["ip_timeout_5s", "ip_timeout_5s", "ip_timeout_5s", "ip_timeout_5s"],
    "refund_status": "completed"
  }
}
```

### Free Trial Events

#### `trial_requested`
```json
{
  "metadata": {
    "survey_provider": "theorem_reach",
    "trial_count_today": 1
  }
}
```

#### `trial_granted`
```json
{
  "metadata": {
    "order_id": "TRIAL-20260627-1042",
    "user_id": "trial_a7b9c2",
    "proxy_port": 8001,
    "expires_at": "2026-06-27T16:42:00Z",
    "survey_payout_usd": 1.50,
    "survey_transaction_id": "TR-987654"
  }
}
```

#### `trial_rejected_daily_limit`
```json
{
  "metadata": {
    "trial_count_today": 3,
    "limit": 3,
    "next_available_at": "2026-06-28T00:00:00Z"
  }
}
```

#### `trial_rejected_signature_invalid`
```json
{
  "metadata": {
    "signature_received_hash": "5a4b3c2d1e0987654321",
    "transaction_id": "TR-987654"
  }
}
```

#### `trial_expired`
```json
{
  "metadata": {
    "order_id": "TRIAL-20260627-1042",
    "user_id": "trial_a7b9c2",
    "duration_minutes": 120,
    "natural_expiry": true
  }
}
```

### Provider Events

#### `provider_health_check`
```json
{
  "metadata": {
    "provider": "Proxy-Seller",
    "endpoint": "GET /balance",
    "response_time_ms": 234,
    "success": true,
    "consecutive_failures": 0
  }
}
```

#### `provider_health_alert`
```json
{
  "metadata": {
    "provider": "Proxy-Seller",
    "consecutive_failures": 3,
    "last_success_at": "2026-06-27T13:55:00Z",
    "admin_alert_sent": true
  }
}
```

### Admin Events

#### `admin_command_executed`
```json
{
  "metadata": {
    "command": "Refund ORD-20260627-0917",
    "risk_level": "high",
    "auth_method": "pin_totp",
    "result": "success"
  }
}
```

### System Events

#### `phone_hash_blocked`
```json
{
  "metadata": {
    "reason": "trial_abuse",
    "evidence": {"distinct_ips_in_24h": 4, "trial_attempts": 4},
    "expires_at": "2026-07-27T14:23:18Z",
    "blocked_by": "system_auto"
  }
}
```

#### `webhook_signature_invalid`
```json
{
  "metadata": {
    "webhook_source": "theorem_reach",
    "signature_received_hash": "5a4b3c2d1e0987654321",
    "ip_hash": "8a7b6c5d4e3f2a1b0c9d",
    "admin_alert_sent": true
  }
}
```

---

## PII Rules — NEVER Log These in Plain Text

| Field | Why dangerous | Hash instead? |
|-------|---------------|---------------|
| `phone` | NDPR, identifier | ✅ sha256[:20] |
| `name` | NDPR | ❌ don't log names at all (use customer_hash) |
| `ip` | Could deanonymize user | ✅ sha256[:20] |
| `proxy_credentials` | Full takeover if leaked | ❌ never log at all |
| `api_key` / `secret` | Full compromise | ❌ never log at all |
| `pin` | Account takeover | ❌ bcrypt hash only, never plain |
| `signature` | Could enable forgery | ✅ sha256[:20] |
| `credit_card_number` | PCI-DSS | ❌ we don't touch cards |

---

## Implementation in n8n

Each workflow calls a shared sub-workflow at the start and end:

```javascript
// n8n Code node — shared logger
const event = {
  event_id: crypto.randomUUID(),
  timestamp: new Date().toISOString(),
  workflow: $workflow.name,
  workflow_id: $workflow.id,
  event_type: $env.EVENT_TYPE,
  status: $env.STATUS || 'info',
  customer_hash: $env.CUSTOMER_HASH || null,
  duration_ms: Date.now() - $env.START_TIME,
  order_id: $env.ORDER_ID || null,
  correlation_id: $env.CORRELATION_ID || crypto.randomUUID(),
  n8n_execution_id: $execution.id,
  metadata: $env.METADATA || {}
};

// INSERT INTO customer_audit_log ...
return event;
```

---

## Query Patterns (For SECURITY_RUNBOOK.md §2)

### Find all events for one customer_hash

```sql
SELECT * FROM customer_audit_log
WHERE customer_hash = ?
ORDER BY timestamp DESC
LIMIT 100;
```

### Find all failed events in last 24h

```sql
SELECT event_type, COUNT(*) AS count
FROM customer_audit_log
WHERE timestamp > NOW() - INTERVAL '24 hours'
  AND status IN ('failure', 'warning')
GROUP BY event_type
ORDER BY count DESC;
```

### Find all trial grants in last 7 days + revenue

```sql
SELECT 
  DATE(timestamp) AS day,
  COUNT(*) FILTER (WHERE event_type = 'trial_granted') AS trials,
  SUM((metadata->>'survey_payout_usd')::numeric) AS tr_revenue_usd
FROM customer_audit_log
WHERE timestamp > NOW() - INTERVAL '7 days'
GROUP BY DATE(timestamp);
```

---

## Database Schema

```sql
CREATE TABLE customer_audit_log (
    id SERIAL PRIMARY KEY,
    event_id UUID UNIQUE,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    workflow VARCHAR(100),
    workflow_id VARCHAR(50),
    event_type VARCHAR(50) NOT NULL,
    status VARCHAR(20),
    customer_hash VARCHAR(20),
    order_id VARCHAR(30),
    correlation_id VARCHAR(50),
    n8n_execution_id VARCHAR(50),
    duration_ms INT,
    metadata JSONB,
    
    INDEX idx_log_customer (customer_hash, timestamp),
    INDEX idx_log_event_type (event_type, timestamp),
    INDEX idx_log_status (status, timestamp),
    INDEX idx_log_correlation (correlation_id),
    INDEX idx_log_order (order_id)
);
```

---

## Retention Policy

- **Hot:** 0-7 days — queryable in PostgreSQL
- **Cold:** 7-90 days — archived to R2 (compressed JSON dump)
- **Archive:** 90 days - 1 year — R2 (lifecycle: infrequent access)
- **Deleted:** >1 year — auto-purged (compliance)

Daily cron handles the tier transitions.

---

## Related

- `workflows/WORKFLOW_SPECS.md` §11 — Styxproxy Logger workflow spec
- `docs/SECURITY_RUNBOOK.md` §2 — Audit query patterns
- `docs/DEAD_IP_REPLACEMENT_POLICY.md` — Retry logging spec
- `docs/PHONE_HASH_BLOCKING.md` — phone_hash_blocked event