"""Regression tests for the Paystack webhook↔order join.

Every Paystack order was permanently unfulfillable. Not a delivery bug — a join
that could never match:

  * `payments.py` minted `TXF-<hex12>` and stored it on `orders.payment_reference`
  * `paystack.py` ignored that value, minted its OWN `TXP-<hex8>`, and sent
    that as the Paystack `"reference"`
  * Paystack charges and echoes back the `"reference"` it was given, so the
    webhook arrived carrying `TXP-…`
  * the webhook looked up `Order.payment_reference == tx_ref`, i.e. `TXP-…`
    against a column holding `TXF-…` — never a match
  * `order is None`, so the entire fulfillment block was skipped, and the
    handler still returned a clean `200 {"status": "received"}`

A successful-looking webhook that changed nothing while a customer had paid.

THE INVARIANT these tests protect: the reference we store on the order is the
reference the gateway actually charged and will echo back. They assert that
equality directly — never the prefix or the format — because the prefix was
never the point. The prefix merely made the mismatch legible after the fact.

Three required behaviours, one per test section:
  1. the stored reference EQUALS the reference sent to Paystack
  2. a matching `charge.success` enqueues fulfillment and leaves `pending`
  3. an unmatched `charge.success` does NOT return a bare 200 having done
     nothing — the silent success was part of the harm

On (3) and retries: Paystack retries non-2xx deliveries (every 3 min for the
first 4 attempts, then hourly for up to 72h), so returning 409 is what lets a
late-committing order still be picked up. The handler deliberately does not
mark the webhook processed on a no-match, or the retry would be rejected as a
duplicate and the retry would be useless.
"""
import hashlib
import hmac
import json
import time
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

# Import router modules BY NAME: `app.routers.<name>` on the package is
# rebound to the APIRouter by routers/__init__.py.
import importlib

payments_mod = importlib.import_module("app.routers.payments")
webhooks_mod = importlib.import_module("app.routers.webhooks")
paystack_mod = importlib.import_module("app.services.paystack")


# ── 1. the stored reference equals the charged reference ────────────────


class FakePlan:
    def __init__(self):
        self.plan_type = "ISP"
        self.price_ngn = 5000.0
        self.price_per_gb = None
        self.quantity = 1
        self.min_gb = 5
        self.max_gb = 50
        self.country = "NG"


class FakeCustomer:
    phone = "+2348000000000"


class FakeSession:
    """Async session that reports "no existing order" for every lookup."""

    def __init__(self):
        self.added = []
        self.commits = 0

    async def execute(self, stmt):
        return SimpleNamespace(
            scalar_one_or_none=lambda: None,
            scalars=lambda: SimpleNamespace(first=lambda: None),
        )

    def add(self, obj):
        self.added.append(obj)

    async def commit(self):
        self.commits += 1

    async def rollback(self):
        pass


@pytest.fixture
def initiate_env(monkeypatch):
    """Stub plan resolution, customer lookup, and both gateways.

    The Paystack stub records the `tx_ref` it was handed and echoes back a
    reference derived from it — exactly what the real gateway does. It also
    returns the numeric transaction id the live API returns, so the order row
    carries the gateway's own key.
    """
    orders_mod = importlib.import_module("app.routers.orders")

    async def fake_resolve_plan(session, plan_code, country=None):
        return FakePlan()

    monkeypatch.setattr(orders_mod, "resolve_plan", fake_resolve_plan)
    monkeypatch.setattr(orders_mod, "generate_order_id", lambda: "STX-PS0001")

    async def fake_customer(session, **kw):
        return FakeCustomer()

    monkeypatch.setattr(payments_mod, "get_or_create_customer", fake_customer)

    calls = []

    async def fake_paystack(**kw):
        calls.append(kw)
        # A real gateway echoes the reference it was given.
        charged = kw.get("tx_ref") or "TXP-DEADBEEF"
        return {
            "checkout_url": "https://checkout.test/ps/abc",
            "tx_ref": charged,
            "payment_id": "ACC_PS_0001",
            "provider_order_id": "6612575449",
        }

    async def fake_flw(**kw):
        calls.append(kw)
        return {"checkout_url": "https://checkout.test/flw/abc", "tx_ref": kw.get("tx_ref")}

    monkeypatch.setattr(payments_mod, "create_paystack_transaction", fake_paystack)
    monkeypatch.setattr(payments_mod, "create_flutterwave_invoice", fake_flw)

    return SimpleNamespace(calls=calls)


async def _initiate(gateway="paystack"):
    from app.routers.schemas import PaymentInitiateRequest

    req = PaymentInitiateRequest(
        plan_code="ISP-NG-1IP", quantity=1, customer_email="", gateway=gateway
    )
    session = FakeSession()
    resp = await payments_mod.initiate_payment(request=req, session=session)
    return session.added[0], session, resp


@pytest.mark.asyncio
async def test_stored_reference_equals_the_reference_sent_to_paystack(initiate_env):
    """THE invariant. The order must store what the gateway was told.

    Pre-fix, `tx_ref` was never passed to `create_paystack_transaction`, so the
    gateway charged a `TXP-` reference while this row kept `TXF-…`. Asserting
    equality — not prefix, not format — is what actually pins the bug down.
    """
    order, _session, _resp = await _initiate("paystack")

    sent_reference = initiate_env.calls[0]["tx_ref"]
    assert sent_reference is not None, "backend-owned reference was not passed to the gateway"
    assert order.payment_reference == sent_reference
    assert order.tx_ref == sent_reference


@pytest.mark.asyncio
async def test_paystack_reference_is_not_minted_independently(initiate_env):
    """The gateway must not be free to invent its own reference.

    A gateway-side reference that differs from the stored one is the exact
    shape of the original defect, so it is worth asserting directly even
    though test 1 already implies it.
    """
    order, _session, _resp = await _initiate("paystack")
    sent = initiate_env.calls[0]["tx_ref"]
    assert order.payment_reference == sent


@pytest.mark.asyncio
async def test_order_records_the_gateways_transaction_id(initiate_env):
    """Persist the gateway's own numeric id.

    Finance's reconciliation need: without it, a payment captured at the
    gateway cannot be tied back to an order row from our side at all. It is
    also the fallback key for recovering orders whose stored reference never
    reached the gateway.
    """
    order, _session, _resp = await _initiate("paystack")
    assert order.provider_order_id == "6612575449"


@pytest.mark.asyncio
async def test_gateway_confirmed_reference_wins_over_our_request(initiate_env):
    """If the gateway echoes a DIFFERENT reference, store the gateway's.

    A gateway that charges something other than what we asked for has recorded
    that other value as the truth. Storing our request instead leaves the
    charged reference recorded nowhere, which is what makes a payment
    impossible to reconcile afterwards.
    """
    async def paystack_that_normalises(**kw):
        return {
            "checkout_url": "https://checkout.test/ps/xyz",
            # The gateway decided on its own reference — not what we asked for.
            "tx_ref": "TXP-NORMALISED",
            "provider_order_id": "6612575449",
        }

    payments_mod.create_paystack_transaction = paystack_that_normalises
    try:
        order, _session, _resp = await _initiate("paystack")
    finally:
        importlib.reload(payments_mod)

    assert order.payment_reference == "TXP-NORMALISED"
    assert order.tx_ref == "TXP-NORMALISED"


@pytest.mark.asyncio
async def test_flutterwave_still_joins_on_its_own_reference(initiate_env):
    """The pre-existing working path must not regress.

    Flutterwave's `TXF-` refs always joined. Passing an explicit tx_ref must
    leave that path exactly as it was.
    """
    order, _session, _resp = await _initiate("flutterwave")
    sent = initiate_env.calls[0]["tx_ref"]
    assert order.payment_reference == sent


@pytest.mark.asyncio
async def test_paystack_service_honours_a_supplied_reference(monkeypatch):
    """`create_paystack_transaction` must SEND the reference it is given.

    Testing the router alone would not catch a service that accepted `tx_ref`
    and still minted its own — which is precisely the original bug. So assert
    on the wire payload.
    """
    sent_bodies = []

    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {
                "status": True,
                "data": {
                    "id": 6612575449,
                    "reference": "TXF-ABCDEF123456",
                    "access_code": "ACC_PS_0001",
                    "authorization_url": "https://checkout.test/ps/abc",
                },
            }

    class FakeClient:
        def __init__(self, *a, **kw):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def post(self, url, headers=None, json=None):
            sent_bodies.append(json)
            return FakeResponse()

    monkeypatch.setattr(paystack_mod.httpx, "AsyncClient", FakeClient)
    monkeypatch.setattr(paystack_mod.settings, "paystack_secret_key", "sk_test_x")

    result = await paystack_mod.create_paystack_transaction(
        amount_ngn=5000.0,
        customer_email="a@b.test",
        customer_phone="+2348000000000",
        callback_url="https://styxproxy.com/thank-you?order_id=STX-PS0001",
        tx_ref="TXF-ABCDEF123456",
    )

    assert sent_bodies[0]["reference"] == "TXF-ABCDEF123456"
    assert result["tx_ref"] == "TXF-ABCDEF123456"
    # The numeric id is what the webhook falls back to.
    assert result["provider_order_id"] == "6612575449"


@pytest.mark.asyncio
async def test_paystack_service_still_mints_a_reference_when_given_none(monkeypatch):
    """The fallback keeps any other caller working.

    `tx_ref=None` must not raise or send an empty reference — Paystack rejects
    an empty `"reference"`. This is the guard that made the added parameter
    safe to introduce.
    """
    sent_bodies = []

    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"status": True, "data": {"authorization_url": "https://x.test"}}

    class FakeClient:
        def __init__(self, *a, **kw):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def post(self, url, headers=None, json=None):
            sent_bodies.append(json)
            return FakeResponse()

    monkeypatch.setattr(paystack_mod.httpx, "AsyncClient", FakeClient)
    monkeypatch.setattr(paystack_mod.settings, "paystack_secret_key", "sk_test_x")

    result = await paystack_mod.create_paystack_transaction(
        amount_ngn=5000.0,
        customer_email="a@b.test",
        customer_phone="+2348000000000",
        callback_url="https://styxproxy.com/thank-you",
    )

    assert sent_bodies[0]["reference"], "an empty reference would be rejected by Paystack"
    assert result["tx_ref"] == sent_bodies[0]["reference"]


# ── 2 & 3. the webhook's behaviour on match and no-match ────────────────


def paystack_signature(payload: bytes, secret: str) -> str:
    return hmac.new(secret.encode(), payload, hashlib.sha512).hexdigest()


def charge_success_payload(reference: str, tx_id: int = 6612575449, amount_kobo: int = 500000):
    return {
        "event": "charge.success",
        "data": {
            "id": tx_id,
            "reference": reference,
            "status": "success",
            "amount": amount_kobo,
            "paid_at": time.time(),
        },
    }


class FakeWebhookSession:
    """Session whose Order lookups return a scripted sequence of results.

    The handler does two lookups at most: first by `payment_reference`, then —
    only if that missed — by `provider_order_id`. This returns `None` for the
    reference lookup and `fallback_order` for the id lookup, which is what a
    legacy straggler looks like.
    """

    def __init__(self, reference_order=None, fallback_order=None):
        self.reference_order = reference_order
        self.fallback_order = fallback_order
        self.added = []
        self.commits = 0
        self._lookups = 0

    async def execute(self, stmt):
        self._lookups += 1
        if self._lookups == 1:
            result = self.reference_order
        else:
            result = self.fallback_order
        return SimpleNamespace(scalar_one_or_none=lambda: result)

    def add(self, obj):
        self.added.append(obj)

    async def commit(self):
        self.commits += 1

    async def rollback(self):
        pass


class FakeRequest:
    """Minimal Request stand-in.

    Carries `.client` and `.headers` because the webhook path calls
    `resolve_origin()` (app/services/origin.py), which reads
    `request.client.host`, `X-Real-IP` and `X-Forwarded-For`. Without them
    every webhook test in this file dies with AttributeError before it reaches
    the payment logic. `client`/`headers` default to the anonymous, headerless
    shape so a caller only supplies them when it means to.
    """

    def __init__(self, payload: dict, client=None, headers=None):
        self._body = json.dumps(payload).encode()
        self.client = client
        self.headers = headers or {}

    async def body(self):
        return self._body


def fake_peer(host: str = "198.51.100.7"):
    """A socket-peer stand-in for `request.client` (TEST-NET-2, never routable)."""
    return type("P", (), {"host": host})()


@pytest.fixture
def webhook_env(monkeypatch):
    """Stub signature verification, dedup, audit and the RQ queue."""
    secret = "sk_test_webhook_secret"
    monkeypatch.setattr(paystack_mod.settings, "paystack_secret_key", secret)

    processed = set()
    audits = []
    enqueued = []

    async def fake_is_processed(session, webhook_id):
        return webhook_id in processed

    async def fake_mark_processed(session, webhook_id, provider, event_type, extra_data=None):
        processed.add(webhook_id)
        await session.commit()

    async def fake_audit(session, event_type, **kw):
        audits.append(event_type)

    async def fake_enqueue(tx_ref, order_id, payload):
        enqueued.append({"tx_ref": tx_ref, "order_id": order_id})
        return "rq-job-1"

    queue_mod = importlib.import_module("app.routers._webhook_queue")
    monkeypatch.setattr(queue_mod, "enqueue_fulfillment", fake_enqueue)
    monkeypatch.setattr(webhooks_mod, "is_webhook_processed", fake_is_processed)
    monkeypatch.setattr(webhooks_mod, "mark_webhook_processed", fake_mark_processed)
    monkeypatch.setattr(webhooks_mod, "log_audit_event", fake_audit)

    return SimpleNamespace(
        secret=secret, processed=processed, audits=audits, enqueued=enqueued
    )


async def _post(payload, session, secret, peer_host="198.51.100.7", headers=None):
    body = json.dumps(payload).encode()
    return await webhooks_mod.paystack_webhook(
        request=FakeRequest(payload, client=fake_peer(peer_host), headers=headers or {}),
        x_paystack_signature=paystack_signature(body, secret),
        session=session,
    )


def make_order(**kw):
    base = dict(
        order_id="STX-PS0001",
        payment_reference="TXF-ABCDEF123456",
        tx_ref="TXF-ABCDEF123456",
        provider="paystack",
        provider_order_id="6612575449",
        status="pending",
        amount_paid_ngn=5000.0,
    )
    base.update(kw)
    return SimpleNamespace(**base)


@pytest.mark.asyncio
async def test_matching_charge_success_fulfills_and_leaves_pending(webhook_env):
    """The happy path that has never once run in production.

    A `charge.success` carrying the reference the order actually stores must
    enqueue fulfillment and move the order off `pending`.
    """
    order = make_order()
    session = FakeWebhookSession(reference_order=order)

    result = await _post(
        charge_success_payload("TXF-ABCDEF123456"), session, webhook_env.secret
    )

    assert result["status"] == "received"
    assert order.status == "paid", "order never left pending — this is the customer-visible bug"
    assert webhook_env.enqueued == [
        {"tx_ref": "TXF-ABCDEF123456", "order_id": "STX-PS0001"}
    ]
    assert "webhook_fulfillment_enqueued" in webhook_env.audits


@pytest.mark.asyncio
async def test_legacy_order_recovers_via_provider_order_id(webhook_env):
    """An order whose stored reference never reached the gateway.

    This is the real-world recovery path for stragglers created before the
    fix: the reference cannot join, but the gateway's own numeric id can.
    """
    order = make_order()
    session = FakeWebhookSession(reference_order=None, fallback_order=order)

    await _post(charge_success_payload("TXP-A8B5F1F3"), session, webhook_env.secret)

    assert order.status == "paid"
    assert webhook_env.enqueued, "a recoverable payment was still not fulfilled"
    assert "paystack_webhook_matched_on_provider_order_id" in webhook_env.audits


@pytest.mark.asyncio
async def test_unmatched_charge_success_does_not_return_a_bare_200(webhook_env):
    """A paid-but-unfulfillable webhook must never look like a success.

    This is the silent-success that hid the whole defect. Returning a clean
    200 told Paystack "received" while no credential, no status change and no
    email happened. A customer had paid and the platform reported all clear.
    """
    session = FakeWebhookSession(reference_order=None, fallback_order=None)

    with pytest.raises(HTTPException) as exc:
        await _post(charge_success_payload("TXP-NOSUCHORDER"), session, webhook_env.secret)

    # Non-2xx, so Paystack retries the delivery.
    assert exc.value.status_code >= 400
    # Loudly recorded — the failure is visible without reading logs.
    assert "paystack_webhook_unmatched_charge_success" in webhook_env.audits
    # Nothing was enqueued for an order that does not exist.
    assert webhook_env.enqueued == []


@pytest.mark.asyncio
async def test_unmatched_webhook_is_not_marked_processed(webhook_env):
    """The retry must not be rejected as a duplicate.

    Marking the webhook processed on a no-match would convert our own 409 into
    a `200 {"status": "already_processed"}` on Paystack's retry — reintroducing
    the silent success one hop later, and making the retry pointless.
    """
    session = FakeWebhookSession(reference_order=None, fallback_order=None)
    payload = charge_success_payload("TXP-NOSUCHORDER")

    with pytest.raises(HTTPException):
        await _post(payload, session, webhook_env.secret)

    assert not webhook_env.processed, "no-match must stay retryable"


@pytest.mark.asyncio
async def test_expired_order_still_rejects_before_fulfillment(webhook_env):
    """The expiry guard must survive the new lookup path."""
    order = make_order(status="expired")
    session = FakeWebhookSession(reference_order=order)

    with pytest.raises(HTTPException) as exc:
        await _post(charge_success_payload("TXF-ABCDEF123456"), session, webhook_env.secret)

    assert exc.value.status_code == 400
    assert webhook_env.enqueued == []


@pytest.mark.asyncio
async def test_already_fulfilled_order_is_not_re_fulfilled(webhook_env):
    """A duplicate for a live order must not enqueue a second fulfillment."""
    order = make_order(status="fulfilled")
    session = FakeWebhookSession(reference_order=order)

    await _post(charge_success_payload("TXF-ABCDEF123456"), session, webhook_env.secret)

    assert webhook_env.enqueued == []
