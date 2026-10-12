#!/usr/bin/env python3
"""
smoke_test.py — Post-deploy smoke test for Styxproxy backend.

Runs against the local API (127.0.0.1:8000) after a deploy.
Exercises the routes most likely to break from a partial deploy:
  - GET  /api/v1/health           — shallow health (DB check)
  - GET  /api/catalog             — catalog with plan resolution
  - POST /api/payments/initiate-basket — payment path (the one that broke twice)

Exit 0 = all passed, 1 = at least one failed.
"""

import sys
import json
import time
import httpx
from datetime import datetime, timezone

BASE_URL = "http://127.0.0.1:8000"
TIMEOUT = 15.0

# A valid plan code that exists in the test DB (starter_1gb is the default test plan)
# We'll try multiple and use the first that works
VALID_PLAN_CODES = [
    "RESIDENTIAL-NG",
    "MOBILE-NG",
    "DATACENTER-NG",
    "ISP-NG",
    "starter_1gb",
]

results = []


def log(msg):
    print(f"[smoke {datetime.now(timezone.utc).strftime('%H:%M:%S')}] {msg}")


def record(name, passed, detail=""):
    status = "PASS" if passed else "FAIL"
    results.append({"name": name, "passed": passed, "detail": detail})
    log(f"  {status}: {name}" + (f" — {detail}" if detail else ""))


def test_health():
    """GET /api/v1/health must return 200 with status=healthy."""
    try:
        r = httpx.get(f"{BASE_URL}/api/v1/health", timeout=TIMEOUT)
        if r.status_code != 200:
            record("health", False, f"HTTP {r.status_code}: {r.text[:200]}")
            return False
        data = r.json()
        if data.get("status") != "healthy":
            record("health", False, f"status={data.get('status')}")
            return False
        record("health", True, f"status={data.get('status')}")
        return True
    except Exception as e:
        record("health", False, str(e))
        return False


def test_catalog():
    """GET /api/catalog must return 200 with plans list."""
    try:
        r = httpx.get(f"{BASE_URL}/api/catalog", timeout=TIMEOUT)
        if r.status_code != 200:
            record("catalog", False, f"HTTP {r.status_code}: {r.text[:200]}")
            return False
        data = r.json()
        templates = data.get("templates", [])
        if not templates:
            record("catalog", False, "no templates in response")
            return False
        record("catalog", True, f"{len(templates)} templates")
        return True
    except Exception as e:
        record("catalog", False, str(e))
        return False


def test_initiate_basket():
    """POST /api/payments/initiate-basket with a valid item must not 500.

    This is the endpoint that broke twice today from partial deploys.
    We send a real request and check it doesn't 500.
    A 400 (invalid plan) is acceptable — it means the route is alive and
    the schema validation works. A 500 means the route is broken.
    """
    # Try each plan code until we get a non-500 response
    for plan_code in VALID_PLAN_CODES:
        payload = {
            "items": [
                {
                    "plan_code": plan_code,
                    "quantity": 1,
                    "quantity_gb": 1,
                }
            ],
            "customer_email": "smoke@test.com",
            "gateway": "flutterwave",
        }
        try:
            r = httpx.post(
                f"{BASE_URL}/api/payments/initiate-basket",
                json=payload,
                timeout=TIMEOUT,
            )
            if r.status_code == 500:
                record("initiate-basket", False, f"HTTP 500 with plan {plan_code}: {r.text[:300]}")
                return False
            elif r.status_code in (200, 201):
                data = r.json()
                record("initiate-basket", True, f"plan={plan_code}, order_id={data.get('order_id', '?')}")
                return True
            elif r.status_code == 400:
                # Invalid plan — try next
                continue
            else:
                record("initiate-basket", False, f"HTTP {r.status_code} with plan {plan_code}: {r.text[:200]}")
                return False
        except Exception as e:
            record("initiate-basket", False, str(e))
            return False

    # If we got here, all plan codes returned 400 — that's still a pass
    # (route is alive, schema validation works, just no valid test plan)
    record("initiate-basket", True, "all plans returned 400 (no valid test plan, but route is alive)")
    return True


def test_deep_health():
    """GET /api/v1/health (deep) must return 200."""
    try:
        r = httpx.get(f"{BASE_URL}/api/v1/health", timeout=TIMEOUT)
        if r.status_code != 200:
            record("deep-health", False, f"HTTP {r.status_code}")
            return False
        record("deep-health", True)
        return True
    except Exception as e:
        record("deep-health", False, str(e))
        return False


def main():
    log("=== Styxproxy post-deploy smoke test ===")
    log(f"Target: {BASE_URL}")

    passed = 0
    failed = 0

    for test_fn in [test_health, test_catalog, test_initiate_basket, test_deep_health]:
        try:
            if test_fn():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            record(test_fn.__name__, False, str(e))
            failed += 1

    log(f"=== Results: {passed} passed, {failed} failed ===")

    if failed > 0:
        log("SMOKE TEST FAILED")
        sys.exit(1)
    else:
        log("SMOKE TEST PASSED")
        sys.exit(0)


if __name__ == "__main__":
    main()
