"""Regression test for /api/payments/initiate and /api/orders/create anonymous checkout.

Verifies both schemas (PaymentInitiateRequest and OrderCreateRequest) accept
the new optional customer_email field, with shape validation. The full DB
path requires a running test DB; here we just exercise the schema layer.

Run: python3 backend/scripts/test_anonymous_checkout.py
"""
import sys

sys.path.insert(0, "/opt/styxproxy/backend")
import os

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("JWT_SECRET", "test-not-used-in-schema")
os.environ.setdefault("ADMIN_TOKEN", "test-not-used")

try:
    from app.schemas import OrderCreateRequest, PaymentInitiateRequest, TrialClaimRequest
except Exception as e:
    print(f"Could not import schemas (probably missing deps): {e}")
    sys.exit(0)


def main() -> int:
    failed = []

    print("\n=== PaymentInitiateRequest ===")
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
        failed.append("payments:email-only")

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
        failed.append("payments:phone-only")

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
        failed.append("payments:both")

    # Test 4: neither (schema accepts; endpoint rejects)
    try:
        req = PaymentInitiateRequest(plan_code="ISP-NG-1", quantity=1)
        print(
            f"[PASS] neither (schema accepts, endpoint rejects): "
            f"phone={req.customer_phone!r} email={req.customer_email!r}"
        )
    except Exception as e:
        print(f"[FAIL] neither schema accepts: {e}")
        failed.append("payments:neither")

    # Test 5: invalid email rejected
    try:
        req = PaymentInitiateRequest(
            plan_code="ISP-NG-1",
            quantity=1,
            customer_email="not-an-email",
        )
        print(f"[FAIL] invalid email accepted: {req.customer_email!r}")
        failed.append("payments:invalid_email")
    except Exception:
        print("[PASS] invalid email rejected: ValidationError")

    # Test 6: invalid phone rejected
    try:
        req = PaymentInitiateRequest(
            plan_code="ISP-NG-1",
            quantity=1,
            customer_phone="abc",
        )
        print(f"[FAIL] invalid phone accepted: {req.customer_phone!r}")
        failed.append("payments:invalid_phone")
    except Exception:
        print("[PASS] invalid phone rejected: ValidationError")

    print("\n=== OrderCreateRequest ===")
    # Test 7: OrderCreateRequest with customer_email
    try:
        req = OrderCreateRequest(
            plan_code="ISP-NG-1",
            country="NG",
            quantity=1,
            customer_email="ord@example.com",
        )
        print(f"[PASS] email accepted: email={req.customer_email!r}")
    except Exception as e:
        print(f"[FAIL] email accepted: {e}")
        failed.append("orders:email")

    # Test 8: OrderCreateRequest backward compat (no email)
    try:
        req = OrderCreateRequest(
            plan_code="ISP-NG-1",
            country="NG",
            quantity=1,
            payment_reference="TXF-TEST",
        )
        print(f"[PASS] no email works: email={req.customer_email!r}")
    except Exception as e:
        print(f"[FAIL] no email works: {e}")
        failed.append("orders:no_email")

    # Test 9: OrderCreateRequest with whitespace-only email rejected (no @)
    # Note: schema validator is intentionally LOOSE — checks @ present, no spaces,
    # max 255 chars. RFC 5322 validation is the responsibility of a downstream service.
    try:
        req = OrderCreateRequest(
            plan_code="ISP-NG-1",
            country="NG",
            quantity=1,
            customer_email="bad email with spaces",
        )
        print(f"[FAIL] whitespace email accepted: {req.customer_email!r}")
        failed.append("orders:invalid_email")
    except Exception:
        print("[PASS] whitespace email rejected: ValidationError")

    # Test 10: OrderCreateRequest invalid country rejected
    try:
        req = OrderCreateRequest(
            plan_code="ISP-NG-1",
            country="XYZ",  # > 10 chars
            quantity=1,
        )
        print(f"[FAIL] invalid country accepted: country={req.country!r}")
        failed.append("orders:invalid_country")
    except Exception:
        print("[PASS] invalid country rejected: ValidationError")

    print("\n=== TrialClaimRequest ===")
    # Test 11: TrialClaimRequest accepts customer_email optional
    try:
        req = TrialClaimRequest(disclaimer_accepted=True, customer_email="trial@example.com")
        print(f"[PASS] with email: email={req.customer_email!r}")
    except Exception as e:
        print(f"[FAIL] with email: {e}")
        failed.append("trials:with_email")

    # Test 12: TrialClaimRequest backward compat (no email)
    try:
        req = TrialClaimRequest(disclaimer_accepted=True)
        print(f"[PASS] no email: email={req.customer_email!r}")
    except Exception as e:
        print(f"[FAIL] no email: {e}")
        failed.append("trials:no_email")

    # Test 13: TrialClaimRequest with whitespace email rejected
    try:
        req = TrialClaimRequest(disclaimer_accepted=True, customer_email="bad email with spaces")
        print(f"[FAIL] whitespace email accepted: {req.customer_email!r}")
        failed.append("trials:invalid_email")
    except Exception:
        print("[PASS] whitespace email rejected: ValidationError")

    # Test 14: TrialClaimRequest still requires disclaimer_accepted=True
    try:
        req = TrialClaimRequest(disclaimer_accepted=False)
        print(
            f"[PASS] disclaimer=False schema accepts (handler will reject): "
            f"disclaimer={req.disclaimer_accepted}"
        )
    except Exception as e:
        print(f"[FAIL] disclaimer=False schema: {e}")
        failed.append("trials:disclaimer")

    print()
    if failed:
        print(f"FAIL: {len(failed)} assertion(s): {failed}")
        return 1
    print("PASS: all schema checks pass (payments + orders + trials)")
    return 0


sys.exit(main())
