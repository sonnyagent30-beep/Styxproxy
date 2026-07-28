"""Test Flutterwave replay-window check.

Sends test webhooks to /api/webhooks/flutterwave.
Expected behavior:
- fresh (now)            - HTTP 200 (within 300s window)
- 200s ago               - HTTP 200 (within 300s window)
- 320s ago               - HTTP 400 (outside 300s window)
- 1hr ago                - HTTP 400 (outside 300s window)
- missing created_at     - HTTP 400 (missing timestamp)
"""
import hashlib
import hmac
import json
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

SECRET = ""  # current value of flutterwave_webhook_secret in env


def test(label, ts):
    """Send one webhook and print result."""
    base = {"event": "charge.completed", "data": {"id": 12348, "tx_ref": f"TXF-{label}", "status": "successful"}}
    if ts is not None:
        base["data"]["created_at"] = ts
    payload = json.dumps(base)
    payload_bytes = payload.encode()
    sig = hmac.new(SECRET.encode(), payload_bytes, hashlib.sha256).hexdigest()
    req = urllib.request.Request(
        "http://127.0.0.1:8000/api/webhooks/flutterwave",
        data=payload_bytes,
        headers={"Content-Type": "application/json", "Verif-Hash": sig},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            print(f"[{label}] HTTP={resp.status} body={resp.read().decode()[:200]}")
    except urllib.error.HTTPError as e:
        print(f"[{label}] HTTP={e.code} body={e.read().decode()[:200]}")


def iso_offset(seconds_ago):
    """Return ISO 8601 timestamp for `seconds_ago` before now."""
    return (datetime.now(timezone.utc) - timedelta(seconds=seconds_ago)).isoformat().replace("+00:00", "Z")


fresh = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
old_200s = iso_offset(200)
old_320s = iso_offset(320)
old_3600s = iso_offset(3600)

print("=== test 1: fresh (just now) - expect 200 ===")
test("fresh", fresh)
print("=== test 2: 200s ago - expect 200 (within 300s window) ===")
test("200s", old_200s)
print("=== test 3: 320s ago - expect 400 (outside 300s window) ===")
test("320s", old_320s)
print("=== test 4: 1 hour ago - expect 400 (outside 300s window) ===")
test("1hr", old_3600s)
print("=== test 5: no created_at - expect 400 ===")
test("missing", None)
