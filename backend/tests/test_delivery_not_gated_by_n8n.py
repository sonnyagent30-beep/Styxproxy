"""The n8n webhook must never gate credential delivery.

## The defect this pins shut

``app/scripts/fulfillment_worker.py`` fired the n8n ``credentials-delivered``
webhook first and only emailed the credential when that returned false::

    n8n_success = await trigger_credentials_delivered_webhook(...)
    if not n8n_success:
        await send_order_active_email(...)

That made delivery conditional on a channel which cannot deliver. The live
workflow ``Sy0H7iuGMaDg1Af5`` is ``Webhook -> Parse Payload -> Call Charon``
with no send node, and Charon answers **HTTP 200** with an escalation string
when Longcat is out of credit::

    {"status":"degraded",
     "services":{"longcat":{"status":"quota_exhausted",
                           "error":"HTTP 402 - provider account out of credit"}},
     "charon_routing":{"primary":"longcat","fallback":"none"},
     "charon_available":false}

HTTP 200 means the ``Call Charon`` node succeeds, so the n8n execution is
recorded ``status: success``, so ``n8n_success`` is True, so the email branch is
**unreachable**. Verified live 2026-10-01: n8n executions 166/167/168 all
``success``, ``lastNodeExecuted: "Call Charon"``, with the customer's real
``styxproxy_username`` / ``styxproxy_password`` in the request going nowhere.

The generalisable lesson, and what these tests assert rather than the specific
call graph: **a channel that cannot deliver must not be able to suppress a
channel that can.** Every test below drives the real ``fulfill_order_job`` and
varies only what n8n does.

The invariant asserted throughout:

    for a fulfilled order with a deliverable email, exactly one channel
    actually emitted the credential, and the outcome says which.

Note on ``orders.emails_sent``: it is NOT asserted anywhere here. Only
``app/services/renewal.py`` writes it, for renewal reminders;
``send_order_active_email`` never touches it. An assertion on that column
passes or fails for a reason unrelated to delivery.
"""

import sys
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

BACKEND_DIR = Path(__file__).resolve().parent.parent
EXPIRES = datetime(2030, 1, 1, tzinfo=timezone.utc)
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

WORKER = "app.scripts.fulfillment_worker"

# fulfill_order_job imports resolve_plan, create_credential, log_audit_event and
# send_order_active_email INSIDE the function body, so patching them by dotted
# string only works once the defining modules are imported.
#
# app.routers.orders cannot be imported normally: app/routers/__init__.py pulls
# in app.routers.admin, which imports RefundApprovalResponse from app.schemas —
# a name that module does not define, so the whole package fails to import.
# That is a pre-existing, unrelated import bug (tracked on the import-gate
# branch); load the one module we need straight from its file instead of
# widening this card's scope to fix it.
import importlib.util as _ilu  # noqa: E402

import app.services.audit  # noqa: E402,F401
import app.services.credential  # noqa: E402,F401
import app.services.email  # noqa: E402,F401

_spec = _ilu.spec_from_file_location(
    "app.routers.orders", BACKEND_DIR / "app" / "routers" / "orders.py"
)
_orders = _ilu.module_from_spec(_spec)
sys.modules["app.routers.orders"] = _orders
_spec.loader.exec_module(_orders)


def _order(**kwargs):
    defaults = dict(
        order_id="STX-GATE01",
        customer_email="buyer@gmail.com",
        customer_phone="+2348010000000",
        plan_code="NG-RES-1IP",
        country="NG",
        status="awaiting_payment",
        quantity=1,
        amount_paid_ngn=5000.0,
        styxproxy_credential_id=None,
        payment_reference="TXF-INL01",
        referred_by=None,
        referral_code=None,
        discount_amount=0.0,
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def _credential():
    return SimpleNamespace(
        id=7,
        styxproxy_username="sty_abc123",
        upstream_proxy_ip="1.2.3.4",
        upstream_proxy_port=1080,
        expires_at=EXPIRES,
    )


class _FakeSession:
    """Just enough AsyncSession for the worker: one row, commits are no-ops."""

    def __init__(self, order):
        self._order = order
        self.committed = 0

    async def execute(self, *_args, **_kwargs):
        result = SimpleNamespace()
        result.scalar_one_or_none = lambda: self._order
        result.scalar_one = lambda: self._order
        return result

    async def commit(self):
        self.committed += 1

    async def flush(self):
        return None

    async def refresh(self, *_a, **_k):
        return None

    def add(self, *_a, **_k):
        return None


async def _run_worker(order=None, n8n=None, email=None, data_payload=None):
    """Drive the real fulfill_order_job with n8n and email mocked.

    ``n8n``/``email`` are the awaited return values of the two collaborators.
    Passing an Exception instance makes the collaborator raise it.

    ``data_payload`` defaults to a Flutterwave body whose customer email matches
    the order row — the production shape. Pass an explicit payload to exercise
    the "no address anywhere" and Paystack-shape cases.
    """
    order = order or _order()
    session = _FakeSession(order)

    if isinstance(n8n, BaseException):
        n8n_mock = AsyncMock(side_effect=n8n)
    else:
        n8n_mock = AsyncMock(return_value=n8n)

    # Default: a successful send. Passing an EmailResult-shaped object
    # overrides it; passing an Exception makes the send raise.
    email_result = (
        email
        if email is not None and not isinstance(email, BaseException)
        else SimpleNamespace(success=True, message_id="msg_1",
                             status="queued", error=None)
    )
    if isinstance(email, BaseException):
        email_mock = AsyncMock(side_effect=email)
    else:
        email_mock = AsyncMock(return_value=email_result)

    async def _fake_create_credential(**_kwargs):
        return _credential(), "plaintext-pw"

    async def _fake_audit(*_a, **_k):
        return None

    async def _fake_resolve_plan(*_a, **_k):
        return SimpleNamespace(plan_type="residential")

    import app.scripts.fulfillment_worker as mod

    with patch.object(mod, "AsyncSessionLocal", lambda: _ctx(session)), \
         patch(f"{WORKER}.trigger_credentials_delivered_webhook", n8n_mock), \
         patch("app.services.credential.create_credential", _fake_create_credential), \
         patch("app.services.email.send_order_active_email", email_mock), \
         patch("app.services.audit.log_audit_event", _fake_audit), \
         patch.object(_orders, "resolve_plan", _fake_resolve_plan):
        payload = (
            data_payload
            if data_payload is not None
            else {"data": {"customer": {"email": order.customer_email}}}
        )
        result = await mod.fulfill_order_job(
            tx_ref="TXF-GATE01",
            order_id=order.order_id,
            data_payload=payload,
            job_id="test",
        )

    return result, n8n_mock, email_mock


class _ctx:
    def __init__(self, session):
        self._s = session

    async def __aenter__(self):
        return self._s

    async def __aexit__(self, *_exc):
        return False


# ── the core defect ───────────────────────────────────────────────────────────


class TestN8nCannotSuppressEmail:
    """The regression that hid for the entire life of the delivery path."""

    async def test_email_is_sent_even_when_n8n_reports_success(self):
        """This is the exact production condition: Charon 402 -> HTTP 200.

        n8n returning True used to mean "delivered", so email was skipped. Now
        n8n returning True is just a notification and email still goes out.
        """
        result, n8n_mock, email_mock = await _run_worker(n8n=True)

        assert n8n_mock.await_count == 1, "n8n should still be notified"
        assert email_mock.await_count == 1, (
            "n8n returning True must NOT suppress the email — this is the "
            "defect: the workflow has no send node, so its 'success' means "
            "nothing was delivered"
        )
        assert result["delivered_via"] == "email"

    async def test_email_is_sent_when_n8n_fails(self):
        result, _, email_mock = await _run_worker(n8n=False)

        assert email_mock.await_count == 1
        assert result["delivered_via"] == "email"

    async def test_email_is_sent_when_n8n_raises(self):
        result, _, email_mock = await _run_worker(n8n=RuntimeError("n8n down"))

        assert email_mock.await_count == 1
        assert result["delivered_via"] == "email"

    async def test_delivery_survives_a_channel_that_can_never_deliver(self):
        """n8n saying True must not change the delivered channel at all.

        Identical inputs, n8n True vs False vs raising: the outcome must be the
        same. If this fails, some channel regained the power to suppress.
        """
        outcomes = []
        for n8n in (True, False, RuntimeError("boom")):
            result, _, email_mock = await _run_worker(n8n=n8n)
            outcomes.append((result["delivered_via"], email_mock.await_count))

        assert outcomes == [("email", 1), ("email", 1), ("email", 1)], outcomes

    async def test_n8n_is_notified_after_delivery_not_before(self):
        """Ordering matters: a hung n8n must not delay the customer.

        If n8n fired first and took 10s, the credential would sit undelivered
        for 10s on every order. Delivery is now first, notification second.
        """
        calls: list[str] = []

        async def _slow_n8n(**_kwargs):
            calls.append("n8n")
            return True

        async def _email(**_kwargs):
            calls.append("email")
            return SimpleNamespace(success=True, message_id="m", status="queued", error=None)

        import app.scripts.fulfillment_worker as mod

        with patch.object(mod, "AsyncSessionLocal", lambda: _ctx(_FakeSession(_order()))), \
             patch(f"{WORKER}.trigger_credentials_delivered_webhook", _slow_n8n), \
             patch("app.services.credential.create_credential",
                   AsyncMock(return_value=(_credential(), "pw"))), \
             patch("app.services.email.send_order_active_email", _email), \
             patch("app.services.audit.log_audit_event", AsyncMock()), \
             patch.object(_orders, "resolve_plan",
                          AsyncMock(return_value=SimpleNamespace(plan_type="residential"))):
            await mod.fulfill_order_job(
                tx_ref="TXF-ORDER", order_id="STX-GATE01",
                data_payload={"data": {"customer": {"email": "buyer@gmail.com"}}},
                job_id="t",
            )

        assert calls == ["email", "n8n"], (
            f"delivery must precede notification, got {calls}"
        )


# ── the outcome must be observable, not log-only ─────────────────────────────


class TestDeliveryOutcomeIsQueryable:
    """'fulfilled' in the DB does not mean 'delivered'. These distinguish them."""

    async def test_success_reports_the_channel(self):
        result, _, _ = await _run_worker(n8n=True)
        assert result["delivered_via"] == "email"
        assert result["delivery_error"] is None

    async def test_provider_rejection_is_not_reported_as_delivered(self):
        """send_order_active_email returns EmailResult and does not raise."""
        rejected = SimpleNamespace(
            success=False, message_id=None, status="api_error",
            error="422 Unprocessable entity",
        )
        result, _, email_mock = await _run_worker(n8n=True, email=rejected)

        assert email_mock.await_count == 1, "the send must still be attempted"
        assert result["delivered_via"] is None, (
            "a provider rejection must not be recorded as a delivery"
        )
        assert "422" in result["delivery_error"]

    async def test_send_exception_is_not_reported_as_delivered(self):
        result, _, _ = await _run_worker(
            n8n=True, email=RuntimeError("resend exploded"),
        )
        assert result["delivered_via"] is None
        assert "resend exploded" in result["delivery_error"]

    async def test_no_address_is_an_explicit_undelivered(self):
        """Silent skip is how this hid for 238 orders."""
        result, _, email_mock = await _run_worker(
            order=_order(customer_email=None, status="awaiting_payment"),
            n8n=True,
            data_payload={"data": {}},
        )

        assert email_mock.await_count == 0
        assert result["delivered_via"] is None
        assert result["delivery_error"] == "no_deliverable_email"

    async def test_placeholder_address_is_not_treated_as_delivered(self):
        """Resend accepts example.com and returns 200. It reaches nobody."""
        result, _, email_mock = await _run_worker(
            order=_order(customer_email="guest-anond@example.com",
                         status="awaiting_payment"),
            n8n=True,
            data_payload={"data": {"customer": {"email": "guest-anond@example.com"}}},
        )

        assert email_mock.await_count == 0
        assert result["delivered_via"] is None


# ── the second delivery path had the same gate ────────────────────────────────


class TestInlineFallbackPathAlsoUngated:
    """``flutterwave.process_payment_webhook`` is a live second delivery path.

    It runs when the RQ enqueue fails — i.e. when the worker is down — so it is
    the path taken exactly when the primary path is unavailable. It also read
    ``event_data["customer"]["email"]`` (Flutterwave shape only), so a Paystack
    order resolved to None and delivered nothing, silently.
    """

    def _payload(self, order):
        return {
            "event": "charge.completed",
            "data": {
                "tx_ref": "TXF-INLINE1",
                "status": "successful",
                "amount": 5000,
                "customer": {"email": "buyer@gmail.com"},
            },
        }

    async def _run_inline(self, order, n8n, event_data=None):
        import app.services.flutterwave as fw

        session = _FakeSession(order)
        email_mock = AsyncMock(
            return_value=SimpleNamespace(success=True, message_id="m",
                                         status="queued", error=None)
        )

        async def _fake_create(**_k):
            return _credential(), "plaintext-pw"

        async def _fake_audit(*_a, **_k):
            return None

        with patch.object(fw, "create_credential", _fake_create), \
             patch.object(fw, "trigger_credentials_delivered_webhook", n8n), \
             patch("app.services.email.send_order_active_email", email_mock), \
             patch("app.services.audit.log_audit_event", _fake_audit), \
             patch.object(fw, "_flutterwave_refund", AsyncMock(return_value={})), \
             patch("app.services.flutterwave.apply_referral_credit",
                   AsyncMock(return_value=None), create=True):
            await fw.process_payment_webhook(
                session, event_data if event_data is not None else self._payload(order)
            )

        return email_mock

    async def test_inline_email_sends_even_when_n8n_succeeds(self):
        order = _order(order_id="STX-INL01")
        email_mock = await self._run_inline(order, AsyncMock(return_value=True))
        assert email_mock.await_count == 1, (
            "the inline fallback must not gate email on n8n either"
        )

    async def test_inline_email_sends_when_n8n_raises(self):
        order = _order(order_id="STX-INL02")
        email_mock = await self._run_inline(
            order, AsyncMock(side_effect=RuntimeError("n8n down")),
        )
        assert email_mock.await_count == 1

    async def test_inline_reads_the_order_row_not_just_the_payload(self):
        """Paystack sends no `customer` object; the order row has the address."""
        order = _order(order_id="STX-INL03", customer_email="row@gmail.com")
        payload = {
            "event": "charge.completed",
            "data": {"tx_ref": "TXF-INL03", "status": "successful", "amount": 5000},
        }
        email_mock = await self._run_inline(order, AsyncMock(return_value=True), payload)

        assert email_mock.await_count == 1, (
            "order.customer_email must be used when the payload has no customer object"
        )
        assert email_mock.await_args.kwargs["customer_email"] == "row@gmail.com"


# ── structural guards ─────────────────────────────────────────────────────────


class TestNoGateRemains:
    """Belt-and-braces: the gate cannot come back unnoticed."""

    @pytest.mark.parametrize(
        "relpath",
        ["app/scripts/fulfillment_worker.py", "app/services/flutterwave.py"],
    )
    def test_no_conditional_delivery_on_webhook_result(self, relpath):
        """Parse, don't grep: these files document the old gate in comments.

        A substring check over raw source matches the comment explaining why the
        gate was removed. Strip comments and docstrings, then look at code only.
        """
        import ast
        import io
        import tokenize

        path = BACKEND_DIR / relpath
        raw = path.read_text()

        # Drop every comment and docstring, keeping executable lines.
        code_only = []
        prev_end = (1, 0)
        prev_toktype = tokenize.INDENT
        for tok in tokenize.generate_tokens(io.StringIO(raw).readline):
            if tok.type == tokenize.COMMENT:
                continue
            if tok.type == tokenize.STRING and prev_toktype in (
                tokenize.INDENT, tokenize.NEWLINE, tokenize.NL, tokenize.DEDENT,
            ):
                continue  # docstring
            if tok.start[0] > prev_end[0]:
                code_only.extend(["\n"] * (tok.start[0] - prev_end[0]))
            code_only.append(tok.string)
            prev_end = tok.end
            if tok.type not in (tokenize.NL, tokenize.COMMENT):
                prev_toktype = tok.type
        code = "".join(code_only)

        ast.parse(raw)  # must still be syntactically valid

        assert "if not n8n_success" not in code, (
            f"{relpath} gates credential delivery on the n8n webhook result again"
        )
        assert "n8n_success" not in code, (
            f"{relpath} assigns the webhook result to a gate variable again — "
            "the notification result must not be stored for a delivery decision"
        )

    def test_worker_is_the_file_systemd_runs(self):
        """The shadow copy at backend/scripts/ is not executed — do not drift."""
        import app.scripts.fulfillment_worker as mod

        assert "app" in Path(mod.__file__).resolve().parts