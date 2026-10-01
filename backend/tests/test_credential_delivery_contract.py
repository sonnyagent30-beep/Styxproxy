"""Regression tests for the credential-delivery payload contract.

Tonight's evidence: the live `Call Charon` n8n node returned
``NodeApiError 422 — Input should be a valid string`` (exec 150), and
``deliver_credentials_direct`` in ``n8n.py`` sent the identical wrong shape.
Both were validated against ``ChatReplyRequest`` in ``app/routers/charon.py``,
which declares ``user_message`` (required) and ``customer_phone``.

The consequence that matters: **funding the LLM would not have fixed it.** The
old payload never reached the model. So this suite asserts the contract
against the real Pydantic model rather than against a hand-copied dict —
asserting a dict matches itself proves nothing, which is why the drift
survived until a production execution failed.
"""
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.routers.charon import ChatReplyRequest
from app.services.n8n import deliver_credentials_direct


SAMPLE = dict(
    order_id="STX-TEST01",
    tx_ref="TXF-TEST01",
    phone="+2348000000000",
    channel="web",
    styxproxy_username="styxproxy_abc",
    styxproxy_password="s3cret",
    proxy_ip="1.2.3.4",
    proxy_port=1080,
    expires_at=datetime(2026, 10, 30, tzinfo=timezone.utc),
    receipt_url="https://styxproxy.com/receipt/TXF-TEST01",
)


def capture_payload(post):
    """Pull the JSON body out of the mocked client's post().

    Takes the *post* mock directly. This previously took the client mock and
    read `.post` off it, which worked only because `post` was a child of the
    client. With the helper's constructor/client wiring separated, `.post` on
    the post mock auto-created a fresh child whose call_args was always None —
    so every payload assertion here was silently reading an unrelated mock.
    A payload test that inspects the wrong object asserts nothing.
    """
    assert post.call_args is not None, "post() was never called"
    return post.call_args.kwargs["json"]


class FakeResponse:
    """A REAL httpx.Response, so status handling is genuine.

    This was a hand-rolled stub whose `raise_for_status()` returned None
    unconditionally — including for a 500. That made the failure branch of
    `trigger_credentials_delivered_webhook` unreachable inside the test:
    `test_webhook_failure_is_reported_as_failure` asserted `result is False`
    and got True, not because the helper lied, but because the stub could
    never fail. Real httpx raises `HTTPStatusError` (a subclass of
    `httpx.HTTPError`) for a 4xx/5xx, which the helper catches.

    A mock that cannot fail cannot test failure reporting. Verified: with a
    real response the helper returns False on 500/503 and True on 200.
    """

    def __init__(self, status_code=200):
        self.status_code = status_code
        self.text = "ok"
        self._real = httpx.Response(
            status_code,
            text=self.text,
            request=httpx.Request("POST", "https://charon.test/api/v1/charon/reply"),
        )

    def raise_for_status(self):
        # Delegate to the genuine implementation so 4xx/5xx actually raise.
        return self._real.raise_for_status()


def fake_httpx(status_code=200):
    """Return (constructor, post) for patching httpx.AsyncClient.

    Use as `with patch("httpx.AsyncClient", ctor)` — the constructor must
    REPLACE the attribute, not be a return_value of another mock.

    Two ways this went wrong before, both of which made the tests assert
    nothing while appearing to run:

    1. The constructor was an AsyncMock. `httpx.AsyncClient(timeout=30)` is a
       *synchronous* call returning an async context manager, but AsyncMock
       returns a coroutine — so `async with` raised TypeError and post() was
       never reached.
    2. The call sites used `patch(..., return_value=ctor)`, which wraps the
       constructor in a second mock: `AsyncClient()` returned the ctor mock,
       then `async with` entered an auto-generated child of *that* mock, so
       post() was again never the mock under assertion.

    Both bugs were invisible because the helper's own `except Exception`
    swallowed the failure and returned False, and the assertions that would
    have caught it (`post.call_args`) were on the wrong object.
    """
    post = AsyncMock(return_value=FakeResponse(status_code))
    client = MagicMock()
    client.post = post
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=client)
    ctx.__aexit__ = AsyncMock(return_value=False)
    return MagicMock(return_value=ctx), post


# ── the contract itself ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_direct_delivery_payload_satisfies_chat_reply_request():
    """The payload must validate against the REAL request model.

    This is the test that would have caught the 422 before production. It
    constructs ChatReplyRequest from the captured body, so renaming a field
    on either side breaks it immediately.
    """
    client, post = fake_httpx()
    with patch("httpx.AsyncClient", client):
        await deliver_credentials_direct(**SAMPLE)

    body = capture_payload(post)
    # Raises ValidationError if any field name or type drifted.
    ChatReplyRequest(**body)


@pytest.mark.asyncio
async def test_payload_uses_the_documented_field_names():
    """Pin the exact keys. 'message'/'phone' are not ChatReplyRequest fields."""
    client, post = fake_httpx()
    with patch("httpx.AsyncClient", client):
        await deliver_credentials_direct(**SAMPLE)

    body = capture_payload(post)
    assert "user_message" in body, "missing required user_message"
    assert "customer_phone" in body
    assert "message" not in body, "legacy non-field 'message' still being sent"
    assert "phone" not in body, "legacy non-field 'phone' still being sent"


@pytest.mark.asyncio
async def test_user_message_is_always_a_string():
    """`user_message` is typed str.

    The message is built by concatenation over fields that include an int
    (proxy_port) and an Optional (receipt_url). A None leaking in produces
    the second half of "Input should be a valid string".
    """
    client, post = fake_httpx()
    args = dict(SAMPLE, receipt_url=None, proxy_port=1080)
    with patch("httpx.AsyncClient", client):
        await deliver_credentials_direct(**args)

    body = capture_payload(post)
    assert isinstance(body["user_message"], str)
    # Not the literal string "None" — that is the classic symptom.
    assert "None" not in body["user_message"]
    assert isinstance(body["customer_phone"], str)


@pytest.mark.asyncio
async def test_empty_phone_does_not_become_none():
    """Anonymous orders have no phone. Send '' not None."""
    client, post = fake_httpx()
    with patch("httpx.AsyncClient", client):
        await deliver_credentials_direct(**dict(SAMPLE, phone=""))

    body = capture_payload(post)
    assert body["customer_phone"] == ""


# ── the fallback that never worked (t_4007d162) ─────────────────────────

@pytest.mark.asyncio
async def test_direct_delivery_posts_to_the_configured_api_host():
    """Regression: the URL came from `settings.api_base_url`, a field that was
    never defined on Settings, so the line raised AttributeError on 100% of
    calls and this fallback never delivered anything at all.

    This asserts the URL is actually built from the setting, so a future
    rename of either side breaks here instead of in production.
    """
    client, post = fake_httpx()
    with patch("httpx.AsyncClient", client), \
         patch("app.services.n8n.get_settings") as settings:
        settings.return_value.api_base_url = "https://api.example.test"
        await deliver_credentials_direct(**SAMPLE)

    assert post.call_args.args[0] == "https://api.example.test/api/v1/charon/reply"


def test_api_base_url_exists_on_settings():
    """The setting must be a real field, not resolved at runtime by luck.

    Pydantic BaseSettings has no __getattr__ fallback, so a missing field is an
    AttributeError at the first read — which is exactly how this shipped.
    """
    from app.config import Settings

    fields = Settings.model_fields
    assert "api_base_url" in fields, "Settings has no api_base_url field"
    assert fields["api_base_url"].default == "https://api.styxproxy.com"


@pytest.mark.asyncio
async def test_direct_delivery_returns_false_when_config_is_broken():
    """A fallback that raises is not a fallback.

    The URL-building line sat OUTSIDE the try block, so a config error
    propagated to the caller instead of returning False. The caller records
    this bool in the delivery ledger, so raising either aborts fulfilment or
    gets swallowed behind a bare `except` into a false "delivered" row.
    """
    client, post = fake_httpx()
    with patch("httpx.AsyncClient", client), \
         patch("app.services.n8n.get_settings") as settings:
        # Reproduce the original defect exactly: attribute absent.
        del settings.return_value.api_base_url
        result = await deliver_credentials_direct(**SAMPLE)

    assert result is False, "broken config must report failure, not raise"
    post.assert_not_called()


@pytest.mark.asyncio
async def test_direct_delivery_returns_false_on_transport_error():
    """A connection failure must surface as False, not an exception."""
    client, post = fake_httpx()
    post.side_effect = httpx.ConnectError("connection refused")
    with patch("httpx.AsyncClient", client), \
         patch("app.services.n8n.get_settings") as settings:
        settings.return_value.api_base_url = "https://api.example.test"
        result = await deliver_credentials_direct(**SAMPLE)

    assert result is False


@pytest.mark.asyncio
async def test_direct_delivery_returns_false_on_error_status():
    """A non-200 from Charon is a failed delivery, and must not report success."""
    client, post = fake_httpx(status_code=422)
    with patch("httpx.AsyncClient", client), \
         patch("app.services.n8n.get_settings") as settings:
        settings.return_value.api_base_url = "https://api.example.test"
        result = await deliver_credentials_direct(**SAMPLE)

    assert result is False, "422 from Charon was reported as a successful delivery"


# ── the fire-and-forget lie ───────────────────────────────────────────

@pytest.mark.asyncio
async def test_webhook_failure_is_reported_as_failure():
    """The helper must not report success it did not observe.

    It used to `asyncio.create_task(...)` then `return True` unconditionally,
    so the fulfilment worker's `if not n8n_success:` direct-email fallback was
    unreachable: n8n could fail every time and the worker still logged
    "delivered". Zero credentials have ever been emailed in this platform's
    history, which is what that bug looks like from the outside.
    """
    from app.services.n8n import trigger_credentials_delivered_webhook

    client, post = fake_httpx(status_code=500)
    with patch("httpx.AsyncClient", client), \
         patch("app.services.n8n._record_failure", AsyncMock()), \
         patch("app.services.n8n.get_settings") as settings:
        settings.return_value.n8n_webhook_url = "https://n8n.test/webhook/x"
        # The 500 response now genuinely raises HTTPStatusError from
        # raise_for_status(), which the helper catches and reports as False.
        # (Previously an async `boom()` side_effect was installed instead; on an
        # AsyncMock that is awaited rather than raised, so it never fired.)
        result = await trigger_credentials_delivered_webhook(**SAMPLE)

    assert result is False, "webhook failed but the caller was told it succeeded"


@pytest.mark.asyncio
async def test_webhook_success_is_reported_as_success():
    """The fix must not simply invert the lie — success still returns True."""
    from app.services.n8n import trigger_credentials_delivered_webhook

    client, post = fake_httpx(status_code=200)
    with patch("httpx.AsyncClient", client), \
         patch("app.services.n8n.get_settings") as settings:
        settings.return_value.n8n_webhook_url = "https://n8n.test/webhook/x"
        result = await trigger_credentials_delivered_webhook(**SAMPLE)

    assert result is True