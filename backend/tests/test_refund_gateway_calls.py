"""The refund path must move money before it says it moved money (t_f765263b).

`admin.py::_process_refund()` used to flip `status='refunded'`, revoke the
credential and email the customer WITHOUT contacting a gateway. All 46
`refunded` rows in production are exactly that: payment_reference set, tx_ref
NULL — the gateway was never consulted. Had these been real payments, 46
customers would have been told their money came back when it had not.

The property under test:

    status becomes `refunded` if and only if the gateway confirmed, and the
    gateway's refund id is persisted whenever it does.

Plus a negative control: reintroducing the old no-call body must make the gate
fail. A guard that passes on both the broken and the fixed tree proves nothing.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.services.refunds import GatewayRefundError, refund_at_gateway

BACKEND = Path(__file__).resolve().parent.parent
ADMIN = BACKEND / "app" / "routers" / "admin.py"


# ── Fakes ──────────────────────────────────────────────────────────────────────


def _order(**overrides):
    """A stand-in order row. Defaults are a refundable Paystack order."""
    base = dict(
        order_id="ORD-TEST1",
        status="fulfilled",
        provider="paystack",
        tx_ref="TXP-ABCD1234",
        payment_reference="TXP-ABCD1234",
        amount_paid_ngn=2500.0,
        customer_phone="+2348000000000",
        styxproxy_credential_id=None,
        gateway_refund_id=None,
        gateway_refund_status=None,
        gateway_refund_amount=None,
        gateway_refunded_at=None,
        refund_requested=False,
        refund_reason=None,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


class _FakeSession:
    """Minimal AsyncSession stand-in.

    `found` is what `scalar_one_or_none()` returns for the row lookup the ops
    router does; the credential lookup always finds nothing.
    """

    def __init__(self, found=None):
        self.commits = 0
        self._found = found

    async def execute(self, stmt):
        return SimpleNamespace(scalar_one_or_none=lambda: self._found)

    async def commit(self):
        self.commits += 1

    def add(self, obj):
        pass

    async def refresh(self, obj):
        pass


def _confirmed(refund_id="2001", status="success"):
    from app.services.refunds import GatewayRefund

    return GatewayRefund(
        provider="paystack",
        gateway_refund_id=refund_id,
        gateway_status=status,
        reference="TXP-ABCD1234",
        amount_ngn=2500.0,
    )


def _router_module(name: str):
    """Import a router MODULE.

    `from app.routers import admin` yields the APIRouter object (the package
    re-exports it as `router as admin`), not the module — so patching an
    attribute on it silently patches nothing useful.
    """
    import importlib

    return importlib.import_module(f"app.routers.{name}")


def _run_admin_refund(order, gateway):
    """Drive the real `_process_refund` with the gateway mocked out."""
    admin_module = _router_module("admin")

    session = _FakeSession()
    with (
        patch.object(admin_module, "refund_at_gateway", gateway),
        patch.object(admin_module, "write_audit_log", AsyncMock()),
        patch.object(admin_module, "send_refund_approved_notification", AsyncMock()),
        patch.object(admin_module, "send_refund_processed_email", AsyncMock()),
    ):
        coro = admin_module._process_refund(
            session, order, "admin@test.com", "customer request", SimpleNamespace(headers={})
        )
        return asyncio.run(coro)


# ── The harm itself: status must not outrun the gateway ────────────────────────


def test_gateway_success_flips_status_and_persists_refund_id():
    order = _order()
    result = _run_admin_refund(order, AsyncMock(return_value=_confirmed("2001")))

    assert order.status == "refunded"
    assert order.refund_requested is True
    # The reconciliation handle. Without it a refund cannot be checked later.
    assert order.gateway_refund_id == "2001"
    assert order.gateway_refund_status == "success"
    assert order.gateway_refund_amount == 2500.0
    assert order.gateway_refunded_at is not None
    assert result["gateway_refund_id"] == "2001"


def test_gateway_failure_leaves_order_actionable_and_raises():
    """The exact harm: a refund that never happened must not read as refunded."""
    order = _order()
    gateway = AsyncMock(side_effect=GatewayRefundError("Paystack refund failed: gateway 503"))

    with pytest.raises(GatewayRefundError) as exc:
        _run_admin_refund(order, gateway)

    assert "gateway 503" in str(exc.value)
    # Not refunded, not flagged as refund-requested, no refund id invented.
    assert order.status == "fulfilled"
    assert order.refund_requested is False
    assert order.gateway_refund_id is None


def test_gateway_response_without_id_is_not_a_refund():
    """A 200 from the gateway carrying no refund id is not reconciliation."""
    from app.services.refunds import _refund_flutterwave

    async def _fake_flw_refund(tx_ref, amount, secret):
        return {"status": "success", "message": "Refund queued", "data": {}}

    with patch("app.services.flutterwave._flutterwave_refund", _fake_flw_refund):
        with pytest.raises(GatewayRefundError) as exc:
            asyncio.run(refund_at_gateway(_order(provider="flutterwave"), reason="r"))
    assert "no refund id" in str(exc.value)


def test_order_without_provider_cannot_be_refunded():
    """Never guess a gateway — a refund against the wrong transaction is worse."""
    with pytest.raises(GatewayRefundError) as exc:
        asyncio.run(refund_at_gateway(_order(provider=None), reason="r"))
    assert "no provider" in str(exc.value)


def test_order_without_any_reference_cannot_be_refunded():
    with pytest.raises(GatewayRefundError) as exc:
        asyncio.run(refund_at_gateway(_order(tx_ref=None, payment_reference=None), reason="r"))
    assert "no gateway reference" in str(exc.value)


def test_refund_amount_prefers_capture_record_over_invoice_amount():
    """amount_paid_ngn is the INVOICE amount. Capture, when present, wins."""
    order = _order(amount_paid_ngn=9999.0)
    order.captured_amount_ngn = 2500.0
    order.captured_at = "2026-10-01T00:00:00Z"

    from app.services.refunds import _resolve_captured_amount

    amount, source = _resolve_captured_amount(order)
    assert amount == 2500.0
    assert source == "captured_amount_ngn"


def test_invoice_fallback_is_labelled_not_silent():
    """No capture column yet (item 2, t_c0b38088) => say so rather than imply proof."""
    from app.services.refunds import _resolve_captured_amount

    amount, source = _resolve_captured_amount(_order(amount_paid_ngn=2500.0))
    assert amount == 2500.0
    assert source == "invoice_fallback"


# ── Paystack refund service ────────────────────────────────────────────────────


class _Resp:
    def __init__(self, status_code=200, payload=None, text=""):
        self.status_code = status_code
        self._payload = payload if payload is not None else {}
        self.text = text

    def json(self):
        return self._payload


class _FakeAsyncClient:
    """Records calls and replays queued responses (verify, then refund)."""

    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def get(self, url, headers=None):
        self.calls.append(("GET", url, None))
        return self._responses.pop(0)

    async def post(self, url, headers=None, json=None):
        self.calls.append(("POST", url, json))
        return self._responses.pop(0)


def _paystack(monkeypatch, responses):
    """Install a fake AsyncClient that replays `responses` in order."""
    from app.services import paystack as ps

    client = _FakeAsyncClient(responses)
    monkeypatch.setattr(ps.httpx, "AsyncClient", lambda *a, **k: client)
    return client


def _refund(responses, monkeypatch, amount=2500.0):
    """Run refund_paystack_transaction against `responses`; return (data, client)."""
    client = _paystack(monkeypatch, responses)
    from app.services.paystack import refund_paystack_transaction

    data = asyncio.run(
        refund_paystack_transaction("TXP-ABCD1234", amount, reason="test", secret_key="sk_test_x")
    )
    return data, client


def test_paystack_refund_posts_to_transaction_refund_endpoint(monkeypatch):
    """Paystack refunds against the numeric TRANSACTION ID, in kobo."""
    data, client = _refund(
        [
            _Resp(200, {"status": True, "data": {"id": 77, "status": "success", "amount": 250000}}),
            _Resp(200, {"status": True, "data": {"id": 900, "status": "successful"}}),
        ],
        monkeypatch,
    )
    assert data["id"] == 900
    method, url, payload = client.calls[1]
    assert method == "POST"
    assert url.endswith("/transaction/77/refund")
    # kobo, not naira — Flutterwave is the opposite convention.
    assert payload["amount"] == 250000
    assert payload["currency"] == "NGN"


def test_paystack_refund_rejects_unsuccessful_transaction(monkeypatch):
    with pytest.raises(Exception) as exc:
        _refund([_Resp(200, {"status": True, "data": {"id": 77, "status": "failed"}})], monkeypatch)
    assert "not 'success'" in str(exc.value)


def test_paystack_refund_rejects_already_refunded_transaction(monkeypatch):
    with pytest.raises(Exception) as exc:
        _refund(
            [_Resp(200, {"status": True, "data": {"id": 77, "status": "success", "amount": 250000, "refunded": True}})],
            monkeypatch,
        )
    assert "already fully refunded" in str(exc.value)


def test_paystack_refund_refuses_amount_above_capture(monkeypatch):
    """Never refund more than the gateway says it captured."""
    with pytest.raises(Exception) as exc:
        _refund(
            [_Resp(200, {"status": True, "data": {"id": 77, "status": "success", "amount": 100000}})],
            monkeypatch,
            amount=5000.0,
        )
    assert "exceeds captured amount" in str(exc.value)


def test_paystack_refund_error_response_raises(monkeypatch):
    with pytest.raises(Exception) as exc:
        _refund(
            [
                _Resp(200, {"status": True, "data": {"id": 77, "status": "success", "amount": 250000}}),
                _Resp(200, {"status": False, "message": "Refund not allowed"}),
            ],
            monkeypatch,
        )
    assert "Refund not allowed" in str(exc.value)


def test_paystack_refund_response_without_id_raises(monkeypatch):
    with pytest.raises(Exception) as exc:
        _refund(
            [
                _Resp(200, {"status": True, "data": {"id": 77, "status": "success", "amount": 250000}}),
                _Resp(200, {"status": True, "data": {}}),
            ],
            monkeypatch,
        )
    assert "no refund id" in str(exc.value)


def test_paystack_refund_requires_configured_secret(monkeypatch):
    from app.services.paystack import PaystackRefundError, refund_paystack_transaction

    monkeypatch.setattr("app.services.paystack.settings.paystack_secret_key", "", raising=False)
    with pytest.raises(PaystackRefundError) as exc:
        asyncio.run(refund_paystack_transaction("TXP-X", 100.0, secret_key=""))
    assert "not configured" in str(exc.value)


# ── Ops path carries the gateway response through ──────────────────────────────


def test_ops_refund_persists_gateway_refund_id():
    """`routers/ops.py` used to discard the gateway result (`_ = await ...`)."""
    ops_module = _router_module("ops")

    order = _order(status="fulfilled")
    session = _FakeSession(found=order)
    gateway = AsyncMock(return_value=_confirmed("rf-flw-1", status="SUCCESSFUL"))

    with (
        patch.object(ops_module, "refund_at_gateway", gateway),
        patch.object(ops_module, "write_audit_log", AsyncMock()),
    ):
        result = asyncio.run(
            ops_module.ops_refund_order(
                order_id=order.order_id,
                request=SimpleNamespace(headers={}),
                reason="ops",
                session=session,
                jwt_payload={"sub": "ops-service"},
            )
        )

    assert order.status == "refunded"
    assert order.gateway_refund_id == "rf-flw-1"
    assert order.gateway_refund_status == "SUCCESSFUL"
    assert result["gateway_refund_id"] == "rf-flw-1"


def test_ops_refund_failure_leaves_order_untouched():
    from fastapi import HTTPException

    ops_module = _router_module("ops")

    order = _order(status="fulfilled")
    session = _FakeSession(found=order)
    gateway = AsyncMock(side_effect=GatewayRefundError("gateway down"))

    with (
        patch.object(ops_module, "refund_at_gateway", gateway),
        patch.object(ops_module, "write_audit_log", AsyncMock()),
    ):
        with pytest.raises(HTTPException) as exc:
            asyncio.run(
                ops_module.ops_refund_order(
                    order_id=order.order_id,
                    request=SimpleNamespace(headers={}),
                    reason="ops",
                    session=session,
                    jwt_payload={"sub": "ops-service"},
                )
            )

    assert exc.value.status_code == 502
    assert order.status == "fulfilled"
    assert order.gateway_refund_id is None


# ── Gate check 3: positive + negative control ──────────────────────────────────


def _load_gate():
    import importlib.util

    spec = importlib.util.spec_from_file_location("go_live_gate", BACKEND / "scripts" / "go_live_gate.py")
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def test_gate_check_3_passes_on_the_fixed_tree():
    gate = _load_gate()
    gate._GIT_REF = None  # read the working tree, not a git ref
    check = gate.check_admin_refund_calls_gateway()
    assert check.ok is True, check.detail


def test_gate_check_3_fails_when_the_no_call_body_is_reintroduced(tmp_path, monkeypatch):
    """Negative control. A guard that passes on both trees proves nothing."""
    gate = _load_gate()
    root = tmp_path / "backend"
    (root / "app" / "routers").mkdir(parents=True)
    (root / "app" / "models.py").parent.mkdir(parents=True, exist_ok=True)
    (root / "app" / "models.py").write_text("class Order(Base):\n    pass\n")
    # The exact pre-fix body: status flip, no gateway call, no refund id.
    (root / "app" / "routers" / "admin.py").write_text(
        "async def _process_refund(session, order, admin_email, reason, http_request):\n"
        '    """status flip + revoke + email, no gateway call."""\n'
        '    order.status = "refunded"\n'
        '    order.refund_requested = True\n'
        '    return {"status": "refunded", "refund_amount": 0}\n'
    )
    monkeypatch.setattr(gate, "APP", root / "app")
    check = gate.check_admin_refund_calls_gateway()
    assert check.ok is False
    assert "NO gateway call" in check.detail
