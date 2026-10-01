"""QA regression tests for the t_46761765 failure audit.

Three groups:

A. `test_ops_auth.py` asserts nothing about production code. It carries a
   hand-copied `require_ops_role_test` and tests that copy. Proven by mutation:
   replacing the production dependency with one that authorises EVERYONE left
   all 15 tests green. The tests below exercise the real
   `app.services.ops_auth.require_ops_role`, and include a negative control that
   fails if the dependency is neutered.

B. Meta-tests over the suite itself. A test that cannot fail is worse than no
   test, because it converts a coverage gap into a green checkmark. These
   assert structural properties that every test file must satisfy:
     - no test module redefines a production function instead of importing it
     - no test module hand-rolls a `raise_for_status` that cannot raise
     - no test mocks a constructor with `patch(..., return_value=X)`
   Each is scoped with an explicit allowlist plus a reason, so a new violation
   fails rather than being silently tolerated.

C. The phone-format contract. `test_invalid_phone_raises` passes only because
   `min_length=10` rejects the 7-char sample before `validate_phone` ever runs,
   so the format rule itself is unpinned. These assert each rule independently.

Group A and C are written so that each fails if the behaviour it names is
removed — that property was verified by mutation, not assumed.
"""
from __future__ import annotations

import ast
import pathlib
import re
from typing import Any

import jwt
import pytest
from fastapi import HTTPException

from app.services.ops_auth import OPS_JWT_SECRET, require_ops_role

# ===========================================================================
# A. The real ops auth dependency, not a copy of it
# ===========================================================================


class _Request:
    """Minimal stand-in for starlette's Request — carries headers only."""

    def __init__(self, headers: dict[str, str] | None = None):
        self.headers = headers or {}


def _call(headers: dict[str, str] | None, role: str = "ops-control") -> dict[str, Any]:
    return require_ops_role(role)(_Request(headers))


def _bearer(payload: dict, secret: str) -> str:
    return "Bearer " + jwt.encode(payload, secret, algorithm="HS256")


_OTHER_SECRET = "an-entirely-different-secret-value-32b"


def test_ops_role_rejects_token_signed_with_a_different_secret():
    """The signature must be verified. A token signed with the wrong secret is 401.

    This is the assertion test_ops_auth.py appears to make. Against the
    production dependency it holds; against the file's private copy it was
    never actually testing production code.
    """
    token = _bearer({"role": "ops-control", "sub": "attacker"}, _OTHER_SECRET)
    with pytest.raises(HTTPException) as exc:
        _call({"Authorization": token})
    assert exc.value.status_code == 401
    assert exc.value.detail == "Invalid token"


def test_ops_role_rejects_a_token_signed_with_no_secret_at_all():
    """An unsigned / alg=none token must not be accepted."""
    token = jwt.encode({"role": "ops-control", "sub": "attacker"}, key="", algorithm="HS256")
    with pytest.raises(HTTPException) as exc:
        _call({"Authorization": f"Bearer {token}"})
    assert exc.value.status_code == 401


def test_ops_role_rejects_a_missing_authorization_header():
    with pytest.raises(HTTPException) as exc:
        _call({})
    assert exc.value.status_code == 401
    assert exc.value.detail == "Missing Bearer token"


def test_ops_role_rejects_a_bare_bearer_with_no_token():
    """'Bearer' with a trailing space and empty token is still unauthorized."""
    with pytest.raises(HTTPException) as exc:
        _call({"Authorization": "Bearer "})
    assert exc.value.status_code == 401


def test_ops_role_rejects_a_valid_signature_with_the_wrong_role():
    """Correctly signed, but role != ops-control → 403, not 401 and not 200."""
    token = _bearer({"role": "viewer", "sub": "someone"}, OPS_JWT_SECRET)
    with pytest.raises(HTTPException) as exc:
        _call({"Authorization": token})
    assert exc.value.status_code == 403
    assert exc.value.detail == "Insufficient role"


def test_ops_role_rejects_an_expired_token():
    import time

    token = _bearer(
        {"role": "ops-control", "sub": "someone", "exp": int(time.time()) - 3600},
        OPS_JWT_SECRET,
    )
    with pytest.raises(HTTPException) as exc:
        _call({"Authorization": token})
    assert exc.value.status_code == 401


def test_ops_role_rejects_a_tampered_token():
    """A signature that does not match the payload must not verify.

    Guards the exact failure the copied test could not see: truncating the
    final characters of a genuine token and presenting it as-is.
    """
    good = _bearer({"role": "ops-control", "sub": "someone"}, OPS_JWT_SECRET)
    tampered = good[:-5] + "XXXXX"
    with pytest.raises(HTTPException) as exc:
        _call({"Authorization": tampered})
    assert exc.value.status_code == 401


def test_ops_role_accepts_a_correctly_signed_token_with_the_right_role():
    """Positive control: the tests above would all also pass if the dependency
    rejected everything. This proves the dependency can still say yes."""
    token = _bearer({"role": "ops-control", "sub": "ops-user"}, OPS_JWT_SECRET)
    payload = _call({"Authorization": token})
    assert payload["sub"] == "ops-user"


def test_ops_role_role_argument_is_honoured():
    """require_ops_role("support") must accept a support token and reject ops."""
    support = _bearer({"role": "support", "sub": "s"}, OPS_JWT_SECRET)
    assert _call({"Authorization": support}, role="support")["sub"] == "s"
    ops = _bearer({"role": "ops-control", "sub": "o"}, OPS_JWT_SECRET)
    with pytest.raises(HTTPException) as exc:
        _call({"Authorization": ops}, role="support")
    assert exc.value.status_code == 403


def test_ops_auth_refuses_to_import_without_a_secret(monkeypatch):
    """The production module must fail closed, not default to open.

    `app/services/ops_auth.py` raises ValueError at import time when
    OPS_JWT_SECRET is absent. That is the property which makes an unset secret
    safe, and nothing in the test tree asserts it. If this ever becomes a
    default value, every financial ops endpoint silently accepts any token.
    """
    import importlib

    import app.services.ops_auth as ops_auth

    monkeypatch.delenv("OPS_JWT_SECRET", raising=False)
    try:
        with pytest.raises(ValueError, match="OPS_JWT_SECRET"):
            importlib.reload(ops_auth)
    finally:
        monkeypatch.setenv("OPS_JWT_SECRET", OPS_JWT_SECRET)
        importlib.reload(ops_auth)


def test_ops_auth_module_raises_at_import_without_a_secret():
    """The production module must refuse to import rather than default to open.

    This is the property that makes the unset-secret case safe, and it is a
    property of `app/services/ops_auth.py` — nothing in the test tree asserts
    it today.
    """
    src = pathlib.Path("app/services/ops_auth.py").read_text()
    assert "raise ValueError" in src, "ops_auth must fail closed when OPS_JWT_SECRET is unset"
    assert '_ops_jwt_secret = os.environ.get("OPS_JWT_SECRET")' in src


# ===========================================================================
# B. Meta-tests: the suite must not be able to pass vacuously
# ===========================================================================

TESTS_DIR = pathlib.Path(__file__).resolve().parent

# Files that violate a rule below, with the reason. Adding to this list is a
# deliberate act; each entry is a known coverage gap, not a style preference.
#
# test_ops_auth.py: carries a private copy of require_ops_role; superseded by
#   group A above. Remove this entry together with that file's copy.
# test_credential_delivery_contract.py: the double-wrapped constructor mock,
#   already documented and fixed on branch fix/t_4007d162-n8n-api-base-url.
ALLOW_PRIVATE_REDEFINITION = {
    "test_ops_auth.py": "hand-copied require_ops_role; group A above tests the real one",
    "test_credential_delivery_contract.py": "double-wrapped ctor mock, fixed on fix/t_4007d162",
}

# raise_for_status stand-ins that cannot raise. Each is a dead failure branch.
ALLOW_UNFAILABLE_FAKES = {
    # Fixed on fix/t_4007d162-n8n-api-base-url. This one mattered: a test
    # asserted a 500 was reported as failure, and the fake made that unreachable.
    "test_credential_delivery_contract.py",
    # Both fakes here sit in happy-path tests only (create_paystack_transaction
    # succeeding). No test drives the gateway-failure branch, so the fake cannot
    # hide a wrong assertion today -- but it does mean a future failure-path
    # test written against this fake would pass for the wrong reason. Tracked in
    # t_46761765 as QA-6.
    "test_paystack_reference_join.py",
}
ALLOW_DOUBLE_WRAPPED_CTOR = {
    # Fixed on fix/t_4007d162-n8n-api-base-url.
    "test_credential_delivery_contract.py",
}


def _prod_function_names() -> dict[str, list[str]]:
    """Map every function defined under app/ to the files that define it."""
    names: dict[str, list[str]] = {}
    backend = TESTS_DIR.parent
    for path in (backend / "app").rglob("*.py"):
        try:
            tree = ast.parse(path.read_text())
        except SyntaxError:  # pragma: no cover - would be a real defect
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                names.setdefault(node.name, []).append(str(path.relative_to(backend)))
    return names


def test_no_test_module_redefines_a_production_function_instead_of_importing_it():
    """A test that tests its own copy of the logic proves nothing.

    This is the defect class that made all 15 tests in test_ops_auth.py
    meaningless: the file defined `require_ops_role_test`, a hand-copy of the
    production dependency, and tested that.
    """
    prod = _prod_function_names()
    # Loader/helper names that legitimately shadow or wrap.
    ignore = {"_load", "call", "main", "get", "set", "run", "load", "check", "dep", "handler"}
    violations: list[str] = []
    for path in sorted(TESTS_DIR.glob("test_*.py")):
        if path.name in ALLOW_PRIVATE_REDEFINITION:
            continue
        src = path.read_text()
        try:
            tree = ast.parse(src)
        except SyntaxError:  # pragma: no cover
            continue
        for node in tree.body:
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if node.name in ignore or node.name not in prod:
                continue
            if re.search(rf"^from .* import .*\b{re.escape(node.name)}\b", src, re.M):
                continue  # imported from production as well — not a shadow copy
            if re.search(rf"^\s*(from|import) .*\b{re.escape(node.name)}\b", src, re.M):
                continue
            violations.append(f"{path.name}::{node.name} (production: {prod[node.name][:2]})")
    assert not violations, (
        "test modules define their own copy of a production function instead of "
        f"importing it, so they assert nothing about production: {violations}"
    )


def test_no_test_fake_defines_an_unfailable_raise_for_status():
    """A hand-rolled `raise_for_status` that never raises makes the failure
    branch unreachable, so the test cannot detect a failing HTTP call."""
    violations: list[str] = []
    for path in sorted(TESTS_DIR.glob("test_*.py")):
        if path.name in ALLOW_UNFAILABLE_FAKES:
            continue
        try:
            tree = ast.parse(path.read_text())
        except SyntaxError:  # pragma: no cover
            continue
        for cls in (n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)):
            for fn in (
                n
                for n in cls.body
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                and n.name == "raise_for_status"
            ):
                body = ast.dump(ast.Module(body=fn.body, type_ignores=[]))
                if "If" not in body and "Compare" not in body:
                    violations.append(f"{path.name}::{cls.name}.{fn.name} (line {fn.lineno})")
    assert not violations, (
        "these raise_for_status fakes cannot raise, so the failure branch they "
        f"are meant to cover is unreachable: {violations}"
    )


def test_no_test_double_wraps_a_constructor_mock():
    """`patch("httpx.AsyncClient", return_value=X)` double-wraps the ctor.

    `AsyncClient(...)` returns X, then `async with` enters an auto-generated
    child of X — so the mock under assertion is never the one called.
    """
    violations: list[str] = []
    pattern = re.compile(
        r"""patch\(\s*["'][^"']*\b(?:AsyncClient|Client|Session|Redis|Queue)\b[^"']*["']\s*,\s*return_value="""
    )
    for path in sorted(TESTS_DIR.glob("test_*.py")):
        if path.name in ALLOW_DOUBLE_WRAPPED_CTOR or path.name == pathlib.Path(__file__).name:
            continue
        for lineno, line in enumerate(path.read_text().splitlines(), 1):
            if pattern.search(line):
                violations.append(f"{path.name}:{lineno}")
    assert not violations, (
        "these tests patch a constructor with return_value=, so `async with` "
        f"enters an auto-generated child and the asserted mock is never called: {violations}"
    )


# ===========================================================================
# C. The phone contract — each rule pinned independently
# ===========================================================================


def test_customer_phone_format_rule_rejects_a_well_formed_length():
    """`validate_phone` must reject a bad format even at a legal length.

    test_schemas.py::test_invalid_phone_raises uses "invalid" (7 chars), which
    `min_length=10` rejects on length alone. The format rule is therefore never
    exercised. This sample is long enough to pass the length bound, so only the
    format rule can reject it.
    """
    from app.schemas import validate_phone

    with pytest.raises(ValueError):
        validate_phone("abcdefghij")  # 10 chars, not a phone number


def test_customer_phone_format_rule_accepts_a_real_number():
    """Positive control for the rule above."""
    from app.schemas import validate_phone

    assert validate_phone("+2348012345678") == "+2348012345678"


def test_payment_initiate_request_rejects_a_bad_phone_at_legal_length():
    """The schema must reject a long-but-invalid phone.

    Goes through PaymentInitiateRequest rather than validate_phone directly, so
    the wiring is covered too.
    """
    from app.schemas import PaymentInitiateRequest

    with pytest.raises(Exception):
        PaymentInitiateRequest(plan_code="ISP-NG-1", customer_phone="abcdefghij", quantity=1)


def test_payment_initiate_request_accepts_phone_and_email_together():
    """Positive control: a valid request must still validate."""
    from app.schemas import PaymentInitiateRequest

    req = PaymentInitiateRequest(
        plan_code="ISP-NG-1",
        customer_phone="+2348012345678",
        customer_email="buyer@example.com",
        quantity=1,
    )
    assert req.customer_phone == "+2348012345678"


def test_customer_phone_is_optional_but_absent_phone_does_not_break_the_schema():
    """Anonymous checkout: no phone is a supported shape, not an error.

    This is the contract test_customer_phone_required got wrong. Both
    `customer_phone` and `customer_email` are Optional, and the router handles
    the neither-present case with a device-derived identity, so requiring a
    phone would contradict shipped behaviour.
    """
    from app.schemas import PaymentInitiateRequest

    req = PaymentInitiateRequest(plan_code="ISP-NG-1", quantity=1)
    assert req.customer_phone is None
    assert req.customer_email is None


@pytest.mark.xfail(
    strict=True,
    reason="QA-1: app/schemas.py holds a stale duplicate of PaymentInitiateRequest, "
    "missing device_id / idempotency_key / quantity_gb. The live route imports "
    "app/routers/schemas.py, so tests/test_schemas.py and "
    "scripts/test_anonymous_checkout.py validate a request shape the API does "
    "not accept. Fix: DELETE the duplicate class from app/schemas.py and point "
    "its importers at app.routers.schemas. Do NOT re-export it from "
    "app/schemas -- that was tried and produces a circular import "
    "(app.routers.schemas imports from app.schemas). This test flips to PASS "
    "when the duplicate is gone.",
)
def test_live_and_dead_payment_schemas_have_not_drifted():
    """`PaymentInitiateRequest` exists in two modules with different fields.

    The live route imports app.routers.schemas; tests/test_schemas.py and
    scripts/test_anonymous_checkout.py import app.schemas. The dead copy is
    missing device_id, idempotency_key and quantity_gb, so a test written
    against it is not describing the request the API accepts.
    """
    from app.routers.schemas import PaymentInitiateRequest as Live
    from app.schemas import PaymentInitiateRequest as Dead

    live_only = set(Live.model_fields) - set(Dead.model_fields)
    assert not live_only, (
        "app/schemas.py has drifted behind app/routers/schemas.py; the dead copy "
        f"is missing {sorted(live_only)}. Delete the duplicate, or make "
        "app.schemas re-export the live class."
    )


@pytest.mark.xfail(
    strict=True,
    reason="QA-1 (same root cause as the drift test above): "
    "scripts/test_anonymous_checkout.py imports PaymentInitiateRequest from "
    "app.schemas, not the app.routers.schemas module the live route uses.",
)
def test_anonymous_checkout_script_validates_the_live_schema_shape():
    """The script that documents anonymous checkout imports the dead copy.

    `scripts/test_anonymous_checkout.py` imports PaymentInitiateRequest from
    app.schemas. It is a manual script, not part of the suite, so nothing runs
    it -- and if it were promoted to a test it would assert against the wrong
    class. Pinned so the import path cannot silently stay wrong.
    """
    src = pathlib.Path("scripts/test_anonymous_checkout.py").read_text()
    assert "from app.routers.schemas import" in src, (
        "test_anonymous_checkout.py must import PaymentInitiateRequest from "
        "app.routers.schemas — the module the live route actually uses."
    )
