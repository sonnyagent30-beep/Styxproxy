# Payment Flow SOP — QA Findings

## Sprint: 2026-09-29

### 1. Webhook HMAC Signing

**Status:** ✅ WORKING — No auth bugs

**Finding:** The HMAC-SHA256 signing logic in the Flutterwave webhook endpoint is correct. The signing and verification work as expected.

**Test harness pitfalls (NOT bugs):**
- **Replay window:** Webhook payloads must have `created_at` within 5 minutes of current time. Hardcoded timestamps cause HTTP 400 "Webhook payload outside replay window" — this is a test harness issue, not a signing bug.
- **Byte-exact signing:** The same JSON bytes must be signed and POSTed. Use `json.dumps(..., separators=(',', ':'))` for compact JSON, sign those exact bytes, and send the same string as the request body.

**Correct test pattern:**
```python
import json, hmac, hashlib, time
from datetime import datetime, timezone

now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
payload = json.dumps({
    "event": "charge.completed",
    "data": {
        "id": int(time.time()),
        "tx_ref": "TXF-...",
        "status": "successful",
        "amount": 2500,
        "currency": "NGN",
        "customer": {"email": "test@example.com"},
        "created_at": now
    }
}, separators=(',', ':'))

signature = hmac.new(
    webhook_secret.encode('utf-8'),
    payload.encode('utf-8'),
    hashlib.sha256
).hexdigest()

requests.post(url, data=payload, headers={
    "Content-Type": "application/json",
    "Verif-Hash": signature
})
```

### 2. Order Lookup Endpoint

**Status:** ✅ FIXED — Commit `ad32278`

**Bug:** The lookup endpoint required both `order_id` AND `email` to match exactly. If the email didn't match (or was NULL), the endpoint returned 404 even though the order existed.

**Fix:** Email is now optional. Lookup by `order_id` alone works for all orders regardless of email state (NULL, empty, matching, or mismatched). Email is only used for sending receipts/proxies, not for lookup.

**Test matrix (all pass):**
| Test | Result |
|------|--------|
| order_id + correct email | 200 ✅ |
| order_id + wrong email | 200 ✅ |
| order_id only | 200 ✅ |
| order_id + invalid email | 400 ✅ |
| non-existent order_id | 404 ✅ |
| Legacy order (NULL email) | 200 ✅ |

### 3. Plan Code Suffix Stripping

**Status:** ✅ WORKING — Confirmed fixed

**Finding:** `resolve_plan()` correctly strips quantity suffixes (e.g., `DC-NG-1IP` → `DC-NG`) at the top of the function. All five call sites use the cleaned `lookup_code`. No path bypasses the stripping.

### 4. Full Payment Chain Verification

**Status:** ✅ VERIFIED END-TO-END

**Chain:** Order created → webhook accepted (HMAC verified) → order paid → fulfilled → credentials delivered → lookup works by order_id alone.

**Test order:** `STX-8DQ11C` — DC-NG-1IP, ₦2,500, fulfilled, credentials delivered.

---

## Summary

| Item | Status | Notes |
|------|--------|-------|
| HMAC signing | ✅ Working | No auth bugs |
| Replay window | ✅ Working | Test harness must use current timestamps |
| Order lookup | ✅ Fixed | `ad32278` — email optional |
| Plan code suffix | ✅ Working | `resolve_plan()` strips suffix correctly |
| Full chain | ✅ Verified | Order → webhook → paid → fulfilled → delivered |
