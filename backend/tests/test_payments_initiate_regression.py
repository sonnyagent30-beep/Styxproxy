"""Regression tests for POST /api/payments/initiate.

Four production defects lived on this one endpoint. Each test below fails
against the pre-fix code and passes after it:

1. `UnboundLocalError: total_amount` — the idempotency branch compared the
   stored order against `total_amount` 44 lines before it was assigned, so any
   retry carrying an Idempotency-Key returned 500 and the 409 guard beneath it
   was unreachable.
2. 5x undercharge — residential/mobile are priced per GB, but the frontend
   carried GB in a field the backend never read and the backend multiplied by
   `quantity` (always 1 for per-GB), billing one GB instead of N.
3. Bricked cart — a reused Idempotency-Key pointing at an expired/cancelled
   order returned 409 forever, so that device could never check out again.
4. "Optional" email was mandatory — no email and no device_id returned 400 on a
   page that says "No signup required".

These call the router function directly with a stub session; they assert on
the amount handed to the gateway, which is the only place an undercharge can
actually take money.
"""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.routers.schemas import PaymentInitiateRequest

# Import router modules BY NAME. `app.routers.<name>` on the package is
# rebound to an APIRouter by routers/__init__.py, so attribute access gives
# you the router object, not the module — monkeypatching it fails confusingly.
import importlib

payments_mod = importlib.import_module("app.routers.payments")


class FakePlan:
    def __init__(self, plan_type, price_ngn=None, price_per_gb=None,
                 quantity=1, min_gb=5, max_gb=50, country="NG"):
        self.plan_type = plan_type
        self.price_ngn = price_ngn
        self.price_per_gb = price_per_gb
        self.quantity = quantity
        self.min_gb = min_gb
        self.max_gb = max_gb
        self.country = country


class FakeCustomer:
    phone = "+23400000000"


class FakeSession:
    """Minimal async session.

    Call-order based, not statement-sniffing: call #0 is the checkout
    kill-switch FeatureFlag lookup (always "no row"), every later call is an
    Order lookup draining `existing_orders` in order.
    """

    def __init__(self, existing_orders=()):
        self.existing_orders = list(existing_orders)
        self.added = []
        self.commits = 0
        self._calls = 0

    async def execute(self, stmt):
        self._calls += 1
        if self._calls == 1:
            return SimpleNamespace(
                scalar_one_or_none=lambda: None,
                scalars=lambda: SimpleNamespace(first=lambda: None),
            )
        order = self.existing_orders.pop(0) if self.existing_orders else None
        return SimpleNamespace(
            scalar_one_or_none=lambda: order,
            scalars=lambda: SimpleNamespace(first=lambda: order),
        )

    def add(self, obj):
        self.added.append(obj)

    async def commit(self):
        self.commits += 1

    async def rollback(self):
        pass


def make_order(**kw):
    base = dict(
        order_id="STX-EXISTING",
        plan_code="ISP-DE-1IP",
        quantity=1,
        customer_email="",
        provider=None,
        amount_paid_ngn=5000.0,
        tx_ref="TXF-EXISTING",
        status="pending",
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=30),
    )
    base.update(kw)
    return SimpleNamespace(**base)


@pytest.fixture
def env(monkeypatch):
    """Stub out plan resolution, the customer lookup and both gateways."""
    orders_mod = importlib.import_module("app.routers.orders")

    plan_box = {"plan": FakePlan("ISP", price_ngn=5000.0, price_per_gb=None)}

    async def fake_resolve_plan(session, plan_code, country=None):
        return plan_box["plan"]

    monkeypatch.setattr(orders_mod, "resolve_plan", fake_resolve_plan)
    monkeypatch.setattr(orders_mod, "generate_order_id", lambda: "STX-NEW01")

    async def fake_customer(session, **kw):
        return FakeCustomer()

    monkeypatch.setattr(payments_mod, "get_or_create_customer", fake_customer)

    gateway_calls = []

    async def fake_flw(**kw):
        gateway_calls.append({"gateway": "flutterwave", **kw})
        return {"checkout_url": "https://checkout.test/abc"}

    async def fake_ps(**kw):
        gateway_calls.append({"gateway": "paystack", **kw})
        return {"checkout_url": "https://checkout.test/ps"}

    monkeypatch.setattr(payments_mod, "create_flutterwave_invoice", fake_flw)
    monkeypatch.setattr(payments_mod, "create_paystack_transaction", fake_ps)

    return SimpleNamespace(plan=plan_box, gateway_calls=gateway_calls)


async def call(session, idempotency_key=None, **body):
    req = PaymentInitiateRequest(**body)
    return await payments_mod.initiate_payment(
        request=req,
        session=session,
        idempotency_key=idempotency_key,
    )


# ── 1. the UnboundLocalError ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_retry_with_same_idempotency_key_returns_existing_order(env):
    """A retry carrying a reused Idempotency-Key must NOT 500.

    Pre-fix this raised UnboundLocalError on `total_amount`.
    """
    session = FakeSession([make_order()])
    resp = await call(
        session,
        idempotency_key="key-1",
        plan_code="ISP-DE-1IP",
        quantity=1,
        customer_email="",
        gateway="flutterwave",
    )
    assert resp.order_id == "STX-EXISTING"
    assert float(resp.amount_ngn) == 5000.0
    # Replay must not raise a second invoice at the gateway.
    assert env.gateway_calls == []


@pytest.mark.asyncio
async def test_retry_with_conflicting_payload_returns_409_not_500(env):
    """Different payload on a reused key -> the intended 409, reachable now."""
    from fastapi import HTTPException

    session = FakeSession([make_order()])
    with pytest.raises(HTTPException) as exc:
        await call(
            session,
            idempotency_key="key-1",
            plan_code="ISP-NG-2IP",   # different plan
            quantity=2,
            gateway="flutterwave",
        )
    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_price_change_does_not_invalidate_a_genuine_retry(env):
    """Compare request identity, not the money.

    An admin editing a price between two attempts of the SAME cart must not
    turn a legitimate retry into a 409. The replay returns the ORIGINAL
    invoice amount — that is what the customer was already quoted.
    """
    env.plan["plan"] = FakePlan("ISP", price_ngn=9999.0, price_per_gb=None)
    session = FakeSession([make_order(amount_paid_ngn=5000.0)])
    resp = await call(
        session,
        idempotency_key="key-1",
        plan_code="ISP-DE-1IP",
        quantity=1,
        gateway="flutterwave",
    )
    assert resp.order_id == "STX-EXISTING"
    assert float(resp.amount_ngn) == 5000.0


# ── 2. the undercharge ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_residential_charges_per_gb_not_one_gb(env):
    """5 GB at N1,000/GB must charge N5,000 — the FE previously got N1,000."""
    env.plan["plan"] = FakePlan("RESIDENTIAL", price_ngn=None, price_per_gb=1000.0)
    session = FakeSession()
    resp = await call(
        session,
        plan_code="RESI-NG",
        quantity=1,
        quantity_gb=5,
        gateway="flutterwave",
    )
    assert float(resp.amount_ngn) == 5000.0
    assert env.gateway_calls[0]["amount"] == 5000.0


@pytest.mark.asyncio
async def test_mobile_charges_per_gb(env):
    env.plan["plan"] = FakePlan("MOBILE", price_ngn=None, price_per_gb=800.0)
    session = FakeSession()
    resp = await call(
        session,
        plan_code="MOBILE-GH",
        quantity=1,
        quantity_gb=10,
        gateway="paystack",
    )
    assert float(resp.amount_ngn) == 8000.0


@pytest.mark.asyncio
async def test_residential_rejects_below_min_gb(env):
    from fastapi import HTTPException

    env.plan["plan"] = FakePlan("RESIDENTIAL", price_ngn=None, price_per_gb=1000.0)
    session = FakeSession()
    with pytest.raises(HTTPException) as exc:
        await call(session, plan_code="RESI-NG", quantity=1, quantity_gb=1)
    assert exc.value.status_code == 400
    assert env.gateway_calls == []


@pytest.mark.asyncio
async def test_datacenter_still_charges_per_ip(env):
    """The per-GB branch must not swallow DC/ISP per-IP pricing."""
    env.plan["plan"] = FakePlan("ISP", price_ngn=5000.0, price_per_gb=None)
    session = FakeSession()
    resp = await call(session, plan_code="ISP-DE-1IP", quantity=1)
    assert float(resp.amount_ngn) == 5000.0


@pytest.mark.asyncio
async def test_residential_does_not_store_gb_as_ip_count(env):
    """quantity is the IP count the fulfillment worker mints credentials from.

    A 5 GB residential plan is ONE gateway carrying 5 GB. Storing 5 here
    would make the worker create five gateways.
    """
    env.plan["plan"] = FakePlan("RESIDENTIAL", price_ngn=None, price_per_gb=1000.0)
    session = FakeSession()
    await call(session, plan_code="RESI-NG", quantity=1, quantity_gb=5)
    order = session.added[0]
    assert order.quantity == 1
    assert float(order.data_total_gb) == 5.0


# ── 3. the bricked cart ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_expired_order_does_not_lock_the_idempotency_key(env):
    """An expired order must release its key so the customer can retry."""
    session = FakeSession([
        make_order(
            status="expired",
            expires_at=datetime.now(timezone.utc) - timedelta(minutes=5),
        )
    ])
    resp = await call(
        session,
        idempotency_key="key-1",
        plan_code="ISP-DE-1IP",
        quantity=1,
        gateway="flutterwave",
    )
    assert resp.order_id == "STX-NEW01"
    assert float(resp.amount_ngn) == 5000.0
    assert len(env.gateway_calls) == 1


@pytest.mark.asyncio
async def test_cancelled_order_does_not_lock_the_idempotency_key(env):
    session = FakeSession([
        make_order(
            status="cancelled",
            expires_at=datetime.now(timezone.utc) - timedelta(minutes=5),
        )
    ])
    resp = await call(
        session, idempotency_key="key-1", plan_code="ISP-DE-1IP", quantity=1
    )
    assert resp.order_id == "STX-NEW01"


# ── 4. the "optional" email ───────────────────────────────────────────

@pytest.mark.asyncio
async def test_no_email_no_device_id_still_checks_out(env):
    """UI says email is optional and no signup is required. Honour it."""
    session = FakeSession()
    resp = await call(session, plan_code="ISP-DE-1IP", quantity=1)
    assert resp.order_id == "STX-NEW01"
    assert len(env.gateway_calls) == 1


# ── gateway provenance ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_order_records_the_gateway_it_was_raised_on(env):
    """provider was NULL on 220/220 historical orders, which is why no
    reconciliation against Flutterwave/Paystack was possible from our side."""
    session = FakeSession()
    await call(session, plan_code="ISP-DE-1IP", quantity=1, gateway="paystack")
    assert session.added[0].provider == "paystack"