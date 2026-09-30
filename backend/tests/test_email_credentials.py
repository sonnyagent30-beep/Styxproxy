"""Regression tests for send_proxy_credentials_email and the NameError-by-construction class of bug.

Context: ``send_proxy_credentials_email`` used to pass ``receipt_url=receipt_url`` into
``_render_proxy_credentials_email`` without ever declaring ``receipt_url`` as a parameter.
It was dead code (zero callers), so nothing caught it — it failed at call time, not import
time. It now delegates to ``send_order_active_email``.

``test_no_undeclared_names_in_app`` runs the same static analysis that found the bug, over
the whole ``app/`` tree, so any future drift of this shape fails the suite instead of
production.
"""
import ast
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from app.services.email import (
    EmailRecipient,
    EmailResult,
    send_order_active_email,
    send_proxy_credentials_email,
)

APP_DIR = Path(__file__).resolve().parent.parent / "app"


# ─── send_proxy_credentials_email ──────────────────────────────────────────────
SAMPLE = dict(
    customer_email="buyer@example.com",
    customer_name="Test Buyer",
    order_id="ORD-000001",
    tx_ref="TXF-ABC123",
    plan_code="NG-RES-1IP",
    amount=5000.0,
    currency="NGN",
    quantity=1,
    styxproxy_username="sty_0123456789",
    styxproxy_password="s3cret-pass",
    proxy_ip="102.89.33.12",
    proxy_port=1080,
    protocol="socks5",
    expires_at=datetime.now(timezone.utc) + timedelta(days=30),
)


def _capturing_send():
    """Patch _send_via_resend so the test exercises rendering but makes no HTTP call."""
    captured = {}

    async def _fake(recipient, subject, html, text=None):
        captured["recipient"] = recipient
        captured["subject"] = subject
        captured["html"] = html
        captured["text"] = text
        return EmailResult(success=True, message_id="<test@test>", status="sent")

    return captured, patch("app.services.email._send_via_resend", side_effect=_fake)


class TestSendProxyCredentialsEmail:
    @pytest.mark.asyncio
    async def test_returns_email_result(self):
        """Regression: this call used to raise NameError: name 'receipt_url' is not defined."""
        captured, mock = _capturing_send()
        with mock:
            result = await send_proxy_credentials_email(**SAMPLE)

        assert isinstance(result, EmailResult)
        assert result.success is True
        assert result.message_id == "<test@test>"

    @pytest.mark.asyncio
    async def test_no_nameerror_with_or_without_receipt_url(self):
        """receipt_url is optional; both shapes must render without raising."""
        for kwargs in ({}, {"receipt_url": "https://styxproxy.com/receipt/TXF-ABC123"}):
            captured, mock = _capturing_send()
            with mock:
                result = await send_proxy_credentials_email(**SAMPLE, **kwargs)
            assert isinstance(result, EmailResult)
            assert result.success is True, f"failed with {kwargs}"

    @pytest.mark.asyncio
    async def test_renders_credentials_into_body(self):
        """A green EmailResult is useless if the body is empty — assert real content."""
        captured, mock = _capturing_send()
        with mock:
            await send_proxy_credentials_email(**SAMPLE)

        assert isinstance(captured["recipient"], EmailRecipient)
        assert captured["recipient"].email == SAMPLE["customer_email"]
        html = captured["html"]
        assert SAMPLE["styxproxy_username"] in html
        assert SAMPLE["styxproxy_password"] in html
        assert SAMPLE["proxy_ip"] in html

    @pytest.mark.asyncio
    async def test_receipt_url_rendered_when_supplied(self):
        """receipt_url must actually reach the template, not just be accepted."""
        captured, mock = _capturing_send()
        with mock:
            await send_proxy_credentials_email(
                **SAMPLE, receipt_url="https://styxproxy.com/receipt/TXF-ABC123"
            )
        assert "https://styxproxy.com/receipt/TXF-ABC123" in captured["html"]

    @pytest.mark.asyncio
    async def test_delegates_to_canonical_sender(self):
        """It is an alias — it must go through send_order_active_email, not re-render."""
        with patch(
            "app.services.email.send_order_active_email", new=AsyncMock(return_value=EmailResult(success=True))
        ) as canonical:
            result = await send_proxy_credentials_email(**SAMPLE)

        assert result.success is True
        canonical.assert_awaited_once()
        assert canonical.await_args.kwargs["receipt_url"] is None

    @pytest.mark.asyncio
    async def test_alias_signature_matches_canonical(self):
        """Signature drift between the two names is what caused the bug — pin them together."""
        import inspect

        alias_params = inspect.signature(send_proxy_credentials_email).parameters
        canonical_params = inspect.signature(send_order_active_email).parameters
        assert list(alias_params) == list(canonical_params)


# ─── Static guard: no NameError-by-construction anywhere in app/ ───────────────
class TestNoUndeclaredNames:
    def test_app_tree_has_no_undeclared_references(self):
        """Every name read in app/ must be bound in an enclosing scope, a module global,
        or a builtin. Anything else is a runtime NameError waiting for a caller."""
        sys.path.insert(0, str(APP_DIR.parent / "scripts"))
        try:
            from ast_undeclared_name_scan import scan_source
        finally:
            sys.path.pop(0)

        failures: list[str] = []
        for path in sorted(APP_DIR.rglob("*.py")):
            source = path.read_text(encoding="utf-8")
            try:
                ast.parse(source, filename=str(path))
            except SyntaxError as exc:  # pragma: no cover - surfaced as a failure
                failures.append(f"{path}: SyntaxError {exc}")
                continue
            for lineno, scope, severity, name in scan_source(source, str(path)):
                if severity == "NameError":
                    failures.append(f"{path}:{lineno}: {scope} references undefined '{name}'")

        assert not failures, "NameError-by-construction found:\n" + "\n".join(failures)
