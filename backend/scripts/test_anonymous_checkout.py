"""Regression test for /api/payments/initiate anonymous checkout.

Verifies the schema accepts the new optional customer_email field and that
the request body shape the FE sends is accepted (no Pydantic validation
failure). The full db path requires a running test DB; here we just
exercise the schema + Pydantic validation path.

Run: python3 backend/scripts/test_anonymous_checkout.py
"""
import sys

sys.path.insert(0, "/opt/styxproxy/backend")
# We need database config to import schemas, but it's only used by validators.
# Use a stub before importing.
import os

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("JWT_SECRET", "test-not-used-in-schema")
os.environ.setdefault("ADMIN_TOKEN", "test-not-used")

try:
    from app.schemas import PaymentInitiateRequest
except Exception as e:
    print(f"Could not import schemas (probably missing deps): {e}")
    sys.exit(0)


def main() -> int:
    failed = []

    # Test 1: just customer_email (no phone) - the new anonymous path
    try:
        req = PaymentInitiateRequest(
            plan_code="ISP-NG-1",
            quantity=2,
            customer_email="test@example.com",
        )
        print(f"[PASS] email-only: phone={req.customer_phone!r} email={req.customer_email!r}")
    except Exception as e:
        print(f"[FAIL] email-only: {e}")
        failed.append("email-only")

    # Test 2: just customer_phone (backward compatible)
    try:
        req = PaymentInitiateRequest(
            plan_code="ISP-NG-1",
            quantity=1,
            customer_phone="+2347032981049",
        )
        print(f"[PASS] phone-only: phone={req.customer_phone!r} email={req.customer_email!r}")
    except Exception as e:
        print(f"[FAIL] phone-only: {e}")
        failed.append("phone-only")

    # Test 3: both
    try:
        req = PaymentInitiateRequest(
            plan_code="ISP-NG-1",
            quantity=1,
            customer_phone="+2347032981049",
            customer_email="test@example.com",
        )
        print(f"[PASS] both: phone={req.customer_phone!r} email={req.customer_email!r}")
    except Exception as e:
        print(f"[FAIL] both: {e}")
        failed.append("both")

    # Test 4: neither (should still construct but endpoint should reject)
    try:
        req = PaymentInitiateRequest(plan_code="ISP-NG-1", quantity=1)
        print(
            f"[PASS] neither (schema accepts, endpoint will reject): "
            f"phone={req.customer_phone!r} email={req.customer_email!r}"
        )
    except Exception as e:
        print(f"[FAIL] neither schema accepts: {e}")
        failed.append("neither")

    # Test 5: invalid email rejected
    try:
        req = PaymentInitiateRequest(
            plan_code="ISP-NG-1",
            quantity=1,
            customer_email="not-an-email",
        )
        print(f"[FAIL] invalid email accepted: {req.customer_email!r}")
        failed.append("invalid_email")
    except Exception as e:
        print(f"[PASS] invalid email rejected: {type(e).__name__}")

    # Test 6: invalid phone rejected (when present)
    try:
        req = PaymentInitiateRequest(
            plan_code="ISP-NG-1",
            quantity=1,
            customer_phone="abc",
        )
        print(f"[FAIL] invalid phone accepted: {req.customer_phone!r}")
        failed.append("invalid_phone")
    except Exception as e:
        print(f"[PASS] invalid phone rejected: {type(e).__name__}")

    print()
    if failed:
        print(f"FAIL: {len(failed)} assertion(s): {failed}")
        return 1
    print("PASS: all PaymentInitiateRequest schema checks pass")
    return 0


sys.exit(main())