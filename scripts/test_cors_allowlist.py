"""Regression test for CORS allowlist.

Sends real CORS preflight (OPTIONS with Access-Control-Request-Method +
Access-Control-Request-Headers) to each origin and asserts:

  - For each EXPECTED_ALLOWED origin, response is 200 + ACAO header matching
  - For each EXPECTED_BLOCKED origin, no ACAO header in response

Run: python3 backend/scripts/test_cors_allowlist.py
"""
import sys
import urllib.error
import urllib.request

API = "https://api.styxproxy.com/api/v1/health"
EXPECTED_ALLOWED = (
    "https://styxproxy.com",
    "https://www.styxproxy.com",
    "https://api.styxproxy.com",
    "http://localhost:3000",
)
EXPECTED_BLOCKED = (
    "https://evil.com",
    "https://attacker.example",
    "https://styxproxy-api-push.vercel.app",  # dead Vercel deployment
    "null",
    "https://styxproxycom.evil.com",  # subdomain confusion
)


def cors_test(origin: str) -> tuple[bool, str]:
    """Return (allowed, status_message).

    A preflight is allowed iff the server returns 200 + an Access-Control-
    Allow-Origin header that matches the request origin (or "*"). The CORS
    spec requires the response to be 200; any 4xx status code from nginx
    or the middleware means the request was rejected and the origin is
    effectively blocked.
    """
    req = urllib.request.Request(
        API,
        method="OPTIONS",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            acao = resp.headers.get("Access-Control-Allow-Origin", "")
            allowed = bool(acao) and (acao == origin or acao == "*")
            return allowed, f"200 acao={acao!r}"
    except urllib.error.HTTPError as e:
        acao = e.headers.get("Access-Control-Allow-Origin", "") if e.headers else ""
        # If the response somehow echoes an ACAO for our origin despite a
        # non-2xx status, treat that as allowed (some misconfigurations do
        # this). Otherwise the origin is blocked.
        if acao and (acao == origin or acao == "*"):
            return True, f"HTTP {e.code} acao={acao!r} (UNEXPECTEDLY ALLOWED)"
        return False, f"HTTP {e.code} acao={acao!r}"
    except Exception as e:
        return False, f"error: {e}"


def main() -> int:
    failed = []
    print("\n--- Should be ALLOWED ---")
    for origin in EXPECTED_ALLOWED:
        ok, msg = cors_test(origin)
        marker = "PASS" if ok else "FAIL"
        print(f"  [{marker}] {origin} -> {msg}")
        if not ok:
            failed.append(f"ALLOW {origin}")

    print("\n--- Should be BLOCKED ---")
    for origin in EXPECTED_BLOCKED:
        ok, msg = cors_test(origin)
        marker = "PASS" if not ok else "FAIL"
        print(f"  [{marker}] {origin} -> {msg}")
        if ok:
            failed.append(f"BLOCK {origin}")

    print()
    if failed:
        print(f"FAIL: {len(failed)} assertion(s) failed: {failed}")
        return 1
    print("PASS: all CORS allowlist assertions hold")
    return 0


sys.exit(main())
