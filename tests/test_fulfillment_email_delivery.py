"""Delivery-path tests for the fulfillment worker's email fallback.

Three defects motivated these tests, all in ``app/scripts/fulfillment_worker.py``:

1. The fallback read ``data_payload["data"]["customer"]["email"]`` only. That is
   the Flutterwave shape. Paystack sends the address at ``data.email`` /
   ``data.customer_email`` with no ``customer`` object at all, so every Paystack
   order resolved to ``None`` and was silently skipped.
2. ``send_order_active_email`` returns an ``EmailResult`` and does *not* raise on
   provider failure. The worker discarded it and logged "fallback email sent"
   unconditionally, so a Resend rejection looked like a success.
3. The delivery ledger identified a send only by email subject, which truncates
   the order id to ``order_id[:8]`` — not enough to attribute a failure to an
   order.

The worker executes under systemd at
``/opt/styxproxy/backend/app/scripts/fulfillment_worker.py``; the near-identical
``backend/scripts/fulfillment_worker.py`` is NOT the one that runs. These tests
therefore import the ``app/scripts`` copy explicitly.
"""
import json
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

from app.scripts.fulfillment_worker import (  # noqa: E402
    _is_placeholder_email,
    resolve_customer_email,
)


def _order(**kwargs):
    """Minimal stand-in for an Order row."""
    defaults = dict(
        order_id="STX-TEST01",
        customer_email=None,
        customer_phone="+2348000000000",
        plan_code="NG-RES-1IP",
        status="paid",
        quantity=1,
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


# ─── resolve_customer_email ───────────────────────────────────────────────────


class TestResolveCustomerEmail:
    def test_prefers_order_row_over_gateway_payload(self):
        """The order row is what the customer typed; the gateway may differ."""
        order = _order(customer_email="real@buyer.com")
        payload = {"data": {"customer": {"email": "different@other.com"}}}
        email, source = resolve_customer_email(order, payload)
        assert email == "real@buyer.com"
        assert source == "order.customer_email"

    def test_falls_back_to_flutterwave_gateway_shape(self):
        order = _order(customer_email="")
        payload = {"event": "charge.completed", "data": {"customer": {"email": "flw@buyer.com"}}}
        email, source = resolve_customer_email(order, payload)
        assert email == "flw@buyer.com"
        assert source == "gateway_payload"

    def test_falls_back_to_paystack_gateway_shape(self):
        """Paystack has no customer object — this was the silent-skip bug."""
        order = _order(customer_email=None)
        payload = {"event": "charge.success", "data": {"email": "ps@buyer.com", "reference": "TXP-1"}}
        email, source = resolve_customer_email(order, payload)
        assert email == "ps@buyer.com"
        assert source == "gateway_payload"

    def test_paystack_customer_email_key(self):
        order = _order(customer_email=None)
        payload = {"data": {"customer_email": "ps2@buyer.com"}}
        email, _ = resolve_customer_email(order, payload)
        assert email == "ps2@buyer.com"

    def test_returns_none_when_payload_has_no_email(self):
        """NOWPayments carries no customer email at all."""
        order = _order(customer_email=None)
        payload = {"payment_status": "finished", "order_id": "TXP-1"}
        email, source = resolve_customer_email(order, payload)
        assert email is None
        assert source == "none"

    def test_rejects_placeholder_from_order_row(self):
        """A placeholder must not shadow a real gateway address."""
        order = _order(customer_email="guest-anondabc123@example.com")
        payload = {"data": {"customer": {"email": "real@buyer.com"}}}
        email, source = resolve_customer_email(order, payload)
        assert email == "real@buyer.com"
        assert source == "gateway_payload"

    def test_placeholder_only_yields_no_delivery(self):
        """Anonymous checkout: both sources placeholder → nobody to email."""
        order = _order(customer_email="guest-anondabc123@example.com")
        payload = {"data": {"customer": {"email": "guest-anondabc123@example.com"}}}
        email, source = resolve_customer_email(order, payload)
        assert email is None
        assert source == "none"

    def test_handles_malformed_payload_without_raising(self):
        """A non-dict data key used to raise AttributeError inside the worker."""
        order = _order(customer_email=None)
        for payload in ({"data": None}, {"data": "oops"}, {"data": {"customer": None}}, {}):
            email, source = resolve_customer_email(order, payload)
            assert email is None and source == "none"

    def test_empty_payload_is_not_an_error(self):
        order = _order(customer_email=None)
        assert resolve_customer_email(order, {}) == (None, "none")


class TestIsPlaceholderEmail:
    @pytest.mark.parametrize(
        "email",
        [
            "guest-anondabc@example.com",
            "x@EXAMPLE.COM",
            "someone@example.org",
            "other@example.net",
            "",
            None,
        ],
    )
    def test_detects_placeholders(self, email):
        assert _is_placeholder_email(email) is True

    @pytest.mark.parametrize("email", ["buyer@gmail.com", "a.b+c@styxproxy.co.ng"])
    def test_real_addresses_pass(self, email):
        assert _is_placeholder_email(email) is False

    def test_substring_is_not_enough(self):
        """A domain merely containing 'example.com' is a real mailbox."""
        assert _is_placeholder_email("sales@notexample.com.evil") is False


# ─── ledger attribution (DoD) ────────────────────────────────────────────────


class TestDeliveryLedger:
    """`EmailResult.success=false` must leave an attributable failure line."""

    @pytest.fixture
    def ledger(self, tmp_path, monkeypatch):
        """Point the real ledger at a temp file and exercise the real path."""
        from app.services import email as email_mod

        log_path = tmp_path / "email_delivery.log.jsonl"
        monkeypatch.setattr(email_mod, "_DELIVERY_LOG_PATH", log_path)

        # A real Resend key, so the send reaches the HTTP call and fails there
        # rather than short-circuiting on the missing-key branch.
        monkeypatch.setattr(email_mod.settings, "resend_api_key", "re_test_key", raising=False)
        return log_path

    def _entries(self, log_path):
        return [json.loads(line) for line in log_path.read_text().splitlines() if line.strip()]

    async def test_failure_writes_line_with_order_id_and_error(self, ledger):
        from app.services.email import send_order_active_email

        with patch("app.services.email.httpx.AsyncClient") as mock_client:
            resp = AsyncMock()
            resp.status_code = 422
            resp.text = '{"message":"Unprocessable entity"}'
            client = AsyncMock()
            client.__aenter__.return_value.post.return_value = resp
            mock_client.return_value = client

            result = await send_order_active_email(
                customer_email="buyer@gmail.com",
                customer_name="Buyer",
                order_id="STX-TEST01",
                tx_ref="TXF-ABC123",
                plan_code="NG-RES-1IP",
                amount=5000.0,
                currency="NGN",
                quantity=1,
                styxproxy_username="sty_1",
                styxproxy_password="pw",
                proxy_ip="1.2.3.4",
                proxy_port=1080,
                protocol="socks5",
                expires_at=EXPIRES,
            )

        assert result.success is False, "provider rejection must not report success"
        assert result.status == "api_error"

        entries = self._entries(ledger)
        assert len(entries) == 1, f"expected exactly one ledger line, got {entries}"
        line = entries[0]
        # The DoD: the failure line carries the order id and the error.
        assert line["order_id"] == "STX-TEST01"
        assert line["to"] == "buyer@gmail.com"
        assert line["status"] == "api_error"
        assert "422" in line["error"]

    async def test_success_line_also_carries_order_id(self, ledger):
        from app.services.email import send_order_active_email

        with patch("app.services.email.httpx.AsyncClient") as mock_client:
            resp = AsyncMock()
            resp.status_code = 200
            resp.json = lambda: {"id": "msg_abc123"}
            client = AsyncMock()
            client.__aenter__.return_value.post.return_value = resp
            mock_client.return_value = client

            result = await send_order_active_email(
                customer_email="buyer@gmail.com",
                customer_name="Buyer",
                order_id="STX-TEST02",
                tx_ref="TXF-DEF456",
                plan_code="NG-RES-1IP",
                amount=5000.0,
                currency="NGN",
                quantity=1,
                styxproxy_username="sty_1",
                styxproxy_password="pw",
                proxy_ip="1.2.3.4",
                proxy_port=1080,
                protocol="socks5",
                expires_at=EXPIRES,
            )

        assert result.success is True
        entry = self._entries(ledger)[0]
        assert entry["order_id"] == "STX-TEST02"
        assert entry["message_id"] == "msg_abc123"

    async def test_no_api_key_writes_attributable_failure(self, ledger, monkeypatch):
        """The missing-key branch is also a silent credential loss."""
        from app.services import email as email_mod

        monkeypatch.setattr(email_mod.settings, "resend_api_key", "", raising=False)

        result = await email_mod.send_order_active_email(
            customer_email="buyer@gmail.com",
            customer_name="Buyer",
            order_id="STX-TEST03",
            tx_ref="TXF-GHI789",
            plan_code="NG-RES-1IP",
            amount=5000.0,
            currency="NGN",
            quantity=1,
            styxproxy_username="sty_1",
            styxproxy_password="pw",
            proxy_ip="1.2.3.4",
            proxy_port=1080,
            protocol="socks5",
            expires_at=EXPIRES,
        )

        assert result.success is False
        entry = self._entries(ledger)[0]
        assert entry["order_id"] == "STX-TEST03"
        assert entry["status"] == "skipped_no_key"


# ─── the file systemd actually runs ───────────────────────────────────────────


class TestDeployedFileIsTheOneUnderTest:
    """Guard against editing the dead near-identical copy."""

    def test_imported_module_is_app_scripts_copy(self):
        import app.scripts.fulfillment_worker as mod

        assert Path(mod.__file__).resolve().parent.name == "scripts"
        assert "app" in Path(mod.__file__).resolve().parts

    def test_untested_sibling_copy_still_has_the_bug(self):
        """If this fails, the shadow copy was fixed too and the tests are stale."""
        shadow = BACKEND_DIR / "scripts" / "fulfillment_worker.py"
        if not shadow.exists():
            pytest.skip("shadow copy not present in this checkout")
        src = shadow.read_text()
        # The old, wrong pattern must still be absent from the file under test.
        under_test = (BACKEND_DIR / "app" / "scripts" / "fulfillment_worker.py").read_text()
        assert 'data_payload.get("data", {}).get("customer", {}).get("email")' not in under_test
        assert "resolve_customer_email" in under_test