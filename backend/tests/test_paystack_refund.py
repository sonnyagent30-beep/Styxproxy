"""Item 4 (t_b18feedc): Paystack refund support must exist and be real.

Scope note: `test_refund_gateway_calls.py` belongs to item 3 (t_f765263b) and
exercises the shared `refunds.py` dispatcher end-to-end. This file covers only
what item 4 owns — `app/services/paystack.py::refund_paystack_transaction` — plus
the gate-4 guard itself, which item 3's tests do not cover.

Deliberately imports NOTHING from `app/services/refunds.py` so these tests hold
on a tree where only the paystack service has landed.
"""

from __future__ import annotations

import asyncio
import re
from pathlib import Path

import pytest

from app.services.paystack import PaystackRefundError, refund_paystack_transaction

BACKEND = Path(__file__).resolve().parent.parent


class _Resp:
    """Minimal httpx.Response stand-in."""

    def __init__(self, status_code=200, payload=None, text=""):
        self.status_code = status_code
        self._payload = payload if payload is not None else {}
        self.text = text

    def json(self):
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


class _FakeClient:
    """Records every request so we can assert the exact call made."""

    def __init__(self, verify, refund):
        self._verify = verify
        self._refund = refund
        self.gets: list[tuple[str, dict]] = []
        self.posts: list[tuple[str, dict, dict]] = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def get(self, url, headers=None):
        self.gets.append((url, headers or {}))
        return self._verify(url)

    async def post(self, url, headers=None, json=None):
        self.posts.append((url, headers or {}, json or {}))
        return self._refund(url)


def _install(monkeypatch, verify_resp, refund_resp):
    client = _FakeClient(lambda _url: verify_resp, lambda _url: refund_resp)
    monkeypatch.setattr(
        "app.services.paystack.httpx.AsyncClient",
        lambda *a, **k: client,
    )
    return client


def _verify_ok(*, tx_id=900001, amount_kobo=500_000, refunded=False, status="success"):
    return _Resp(
        200,
        {
            "status": True,
            "data": {
                "id": tx_id,
                "status": status,
                "amount": amount_kobo,
                "refunded": refunded,
                "reference": "TXF-ABC123",
            },
        },
    )


def _refund_ok(*, refund_id=777, status="success"):
    return _Resp(
        200,
        {
            "status": True,
            "message": "Refund successful",
            "data": {"id": refund_id, "status": status, "reference": "TXF-ABC123"},
        },
    )


SECRET = "sk_test_0123456789abcdef"


def test_refund_success_returns_gateway_refund_id(monkeypatch):
    """Requirement 3: the gateway's refund id must reach the caller so it can be persisted."""
    monkeypatch.setattr("app.services.paystack.settings.paystack_secret_key", SECRET)
    _install(monkeypatch, _verify_ok(), _refund_ok(refund_id=4242))

    data = asyncio.run(refund_paystack_transaction("TXF-ABC123", 5000.0))

    assert data["id"] == 4242, "gateway refund id must be returned verbatim"
    assert data["status"] == "success"


def test_refund_hits_the_transaction_refund_endpoint_with_secret(monkeypatch):
    """Requirement 1: POST https://api.paystack.co/transaction/{id}/refund, secret-key auth.

    The reference we hold (TXF-/TXP-) is resolved via verify FIRST, because
    Paystack refunds against the numeric transaction id. Refunding by our own
    invoice ref directly would hit the wrong transaction or fail.
    """
    monkeypatch.setattr("app.services.paystack.settings.paystack_secret_key", SECRET)
    client = _install(monkeypatch, _verify_ok(tx_id=900001), _refund_ok())

    asyncio.run(refund_paystack_transaction("TXF-ABC123", 5000.0))

    assert client.posts, "no POST was issued to Paystack"
    url, headers, payload = client.posts[0]
    assert url == "https://api.paystack.co/transaction/900001/refund", (
        f"refund must target the resolved transaction id, got {url}"
    )
    assert headers["Authorization"] == f"Bearer {SECRET}", "must authenticate with the secret key"
    assert payload["currency"] == "NGN"


def test_partial_refund_passes_the_explicit_amount_in_kobo(monkeypatch):
    """Requirement 2: partial refunds, amount passed explicitly, never defaulted to full."""
    monkeypatch.setattr("app.services.paystack.settings.paystack_secret_key", SECRET)
    client = _install(monkeypatch, _verify_ok(amount_kobo=500_000), _refund_ok())

    asyncio.run(refund_paystack_transaction("TXF-ABC123", 1500.0))

    _, _, payload = client.posts[0]
    assert payload["amount"] == 150_000, (
        "Paystack amount is the SUBUNIT (kobo), the opposite convention from Flutterwave: "
        f"1500 NGN must be sent as 150000 kobo, got {payload['amount']}"
    )
    assert payload["amount"] != 500_000, "partial refund must not fall back to the full amount"


def test_amount_above_captured_is_refused(monkeypatch):
    """Never let a caller refund more than the gateway actually charged."""
    monkeypatch.setattr("app.services.paystack.settings.paystack_secret_key", SECRET)
    client = _install(monkeypatch, _verify_ok(amount_kobo=100_000), _refund_ok())

    with pytest.raises(PaystackRefundError, match="exceeds captured amount"):
        asyncio.run(refund_paystack_transaction("TXF-ABC123", 5000.0))

    assert not client.posts, "must fail before asking the gateway to move money"


def test_gateway_error_raises_rather_than_reporting_success(monkeypatch):
    """Requirement 4: gateway failure must raise, never a silent success."""
    monkeypatch.setattr("app.services.paystack.settings.paystack_secret_key", SECRET)
    _install(monkeypatch, _verify_ok(), _Resp(200, {"status": False, "message": "Invalid key"}))

    with pytest.raises(PaystackRefundError, match="Invalid key"):
        asyncio.run(refund_paystack_transaction("TXF-ABC123", 5000.0))


def test_http_error_status_raises(monkeypatch):
    monkeypatch.setattr("app.services.paystack.settings.paystack_secret_key", SECRET)
    _install(monkeypatch, _verify_ok(), _Resp(500, {}, text="upstream boom"))

    with pytest.raises(PaystackRefundError, match="500"):
        asyncio.run(refund_paystack_transaction("TXF-ABC123", 5000.0))


def test_unknown_reference_raises(monkeypatch):
    monkeypatch.setattr("app.services.paystack.settings.paystack_secret_key", SECRET)
    _install(monkeypatch, _Resp(404, {}, text="not found"), _refund_ok())

    with pytest.raises(PaystackRefundError):
        asyncio.run(refund_paystack_transaction("TXF-NOPE", 5000.0))


def test_unsuccessful_transaction_is_refused(monkeypatch):
    """A failed/abandoned transaction has no captured money to return."""
    monkeypatch.setattr("app.services.paystack.settings.paystack_secret_key", SECRET)
    _install(monkeypatch, _verify_ok(status="failed"), _refund_ok())

    with pytest.raises(PaystackRefundError, match="not 'success'"):
        asyncio.run(refund_paystack_transaction("TXF-ABC123", 5000.0))


def test_already_refunded_transaction_is_refused(monkeypatch):
    """Double-refund would return money twice; the verify call is what catches it."""
    monkeypatch.setattr("app.services.paystack.settings.paystack_secret_key", SECRET)
    _install(monkeypatch, _verify_ok(refunded=True), _refund_ok())

    with pytest.raises(PaystackRefundError, match="already fully refunded"):
        asyncio.run(refund_paystack_transaction("TXF-ABC123", 5000.0))


def test_response_without_refund_id_raises(monkeypatch):
    """No refund id means nothing to reconcile against later — must not count as success."""
    monkeypatch.setattr("app.services.paystack.settings.paystack_secret_key", SECRET)
    _install(monkeypatch, _verify_ok(), _Resp(200, {"status": True, "data": {}}))

    with pytest.raises(PaystackRefundError, match="no refund id"):
        asyncio.run(refund_paystack_transaction("TXF-ABC123", 5000.0))


def test_unconfigured_gateway_raises_before_any_network_call(monkeypatch):
    monkeypatch.setattr("app.services.paystack.settings.paystack_secret_key", "")
    client = _install(monkeypatch, _verify_ok(), _refund_ok())

    with pytest.raises(PaystackRefundError, match="not configured"):
        asyncio.run(refund_paystack_transaction("TXF-ABC123", 5000.0))

    assert not client.gets and not client.posts, "must not call the gateway unconfigured"


def test_zero_or_negative_amount_raises(monkeypatch):
    monkeypatch.setattr("app.services.paystack.settings.paystack_secret_key", SECRET)
    _install(monkeypatch, _verify_ok(), _refund_ok())

    for bad in (0, -100):
        with pytest.raises(PaystackRefundError):
            asyncio.run(refund_paystack_transaction("TXF-ABC123", bad))


# ── Gate 4 guard: the thing this card is actually gated on ──────────────────


def _gate_check_4(tree: Path) -> tuple[str, bool]:
    """Run go_live_gate.py check 4 against `tree`, returning (detail, passed)."""
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "gate_under_test", tree / "backend" / "scripts" / "go_live_gate.py"
    )
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    # Gate on the tree on disk, not on origin/main, and re-point it at `tree`.
    mod._GIT_REF = None
    mod.APP = tree / "backend" / "app"
    mod.BACKEND = tree / "backend"
    check = mod.check_paystack_refund_support()
    return check.detail, check.ok is True


def test_gate_check_4_passes_when_refund_function_exists():
    """Positive control."""
    verdict, passed = _gate_check_4(BACKEND.parent)
    assert passed, f"gate check 4 must pass on the fixed tree, got: {verdict}"


def test_gate_check_4_fails_when_refund_method_is_removed(tmp_path):
    """Negative control: deleting the refund method must make check 4 FAIL.

    A guard that passes on both trees proves nothing, so this asserts the
    opposite direction explicitly.
    """
    tree = tmp_path / "repo"
    (tree / "backend" / "scripts").mkdir(parents=True)
    (tree / "backend" / "app" / "services").mkdir(parents=True)
    (tree / "backend" / "app" / "routers").mkdir(parents=True)

    shutil_copy(BACKEND / "scripts" / "go_live_gate.py", tree / "backend" / "scripts" / "go_live_gate.py")

    svc = (BACKEND / "app" / "services" / "paystack.py").read_text()
    stripped = re.sub(r"\nasync def refund_paystack_transaction\(.*?(?=\n\ndef |\n\nasync def )", "\n", svc, flags=re.S)
    assert "refund_paystack_transaction" not in stripped, "test setup failed to strip the method"
    (tree / "backend" / "app" / "services" / "paystack.py").write_text(stripped)

    verdict, passed = _gate_check_4(tree)
    assert not passed, f"gate check 4 must FAIL without the refund method, got: {verdict}"


def shutil_copy(src: Path, dst: Path) -> None:
    dst.write_text(src.read_text())
