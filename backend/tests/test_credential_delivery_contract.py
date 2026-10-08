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
from unittest.mock import AsyncMock, patch

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


def capture_payload(mock_client):
    """Pull the JSON body out of the mocked httpx client."""
    return mock_client.post.call_args.kwargs["json"]


class FakeResponse:
    """A response that honours its status code.

    This used to have `raise_for_status` returning None for every status, so
    `fake_httpx(status_code=500)` could not produce a failure — the parameter
    existed and did nothing. A failure-path test written against that would
    pass for the wrong reason, which is the defect
    `test_credential_delivery_contract.py` already shipped once.

    Delegates to a real `httpx.Response` so the harness cannot drift from the
    contract `app/services/n8n.py` is written against.
    """

    def __init__(self, status_code=200, text="ok"):
        self._response = httpx.Response(
            status_code,
            text=text,
            request=httpx.Request("POST", "https://n8n.test/webhook/x"),
        )

    @property
    def status_code(self) -> int:
        return self._response.status_code

    @property
    def text(self) -> str:
        return self._response.text

    def raise_for_status(self):
        return self._response.raise_for_status()


def fake_httpx(status_code=200):
    """Patch httpx.AsyncClient so post() records the body and returns 200."""
    post = AsyncMock(return_value=FakeResponse(status_code))
    client = AsyncMock()
    client.post = post
    ctx = AsyncMock()
    ctx.__aenter__.return_value = client
    ctx.__aexit__.return_value = False
    return AsyncMock(return_value=ctx), post


# ── the harness itself must be able to fail ───────────────────────────
#
# The bug this file already shipped once: `fake_httpx(status_code=500)` took a
# status code, ignored it, and `raise_for_status` returned None for every
# response. A failure-path test written against it would assert nothing at all
# while looking exactly like a passing one. These tests pin that the fake can
# fail, so the next failure-path test written here is testing product code.


def test_fake_response_raises_on_5xx():
    """`fake_httpx(status_code=500)` must actually produce a failure."""
    _client, post = fake_httpx(status_code=500)
    with pytest.raises(httpx.HTTPStatusError) as exc:
        post.return_value.raise_for_status()
    assert exc.value.response.status_code == 500


@pytest.mark.parametrize("status", [400, 401, 404, 422, 500, 502, 503])
def test_fake_response_raises_on_every_error_status(status):
    with pytest.raises(httpx.HTTPStatusError):
        FakeResponse(status).raise_for_status()


@pytest.mark.parametrize("status", [200, 201, 202, 204])
def test_fake_response_does_not_raise_on_success_status(status):
    """Success must not raise — otherwise the fix is just always-fail."""
    FakeResponse(status).raise_for_status()


# ── the contract itself ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_direct_delivery_payload_satisfies_chat_reply_request():
    """The payload must validate against the REAL request model.

    This is the test that would have caught the 422 before production. It
    constructs ChatReplyRequest from the captured body, so renaming a field
    on either side breaks it immediately.
    """
    client, post = fake_httpx()
    with patch("httpx.AsyncClient", return_value=client):
        await deliver_credentials_direct(**SAMPLE)

    body = capture_payload(post)
    # Raises ValidationError if any field name or type drifted.
    ChatReplyRequest(**body)


@pytest.mark.asyncio
async def test_payload_uses_the_documented_field_names():
    """Pin the exact keys. 'message'/'phone' are not ChatReplyRequest fields."""
    client, post = fake_httpx()
    with patch("httpx.AsyncClient", return_value=client):
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
    with patch("httpx.AsyncClient", return_value=client):
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
    with patch("httpx.AsyncClient", return_value=client):
        await deliver_credentials_direct(**dict(SAMPLE, phone=""))

    body = capture_payload(post)
    assert body["customer_phone"] == ""


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
    with patch("httpx.AsyncClient", return_value=client), \
         patch("app.services.n8n.get_settings") as settings:
        settings.return_value.n8n_webhook_url = "https://n8n.test/webhook/x"
        settings.return_value.api_base_url = "https://api.test"
        # A 500 makes raise_for_status raise, which the helper catches.
        async def boom():
            raise RuntimeError("500 Server Error")
        post.side_effect = boom
        result = await trigger_credentials_delivered_webhook(**SAMPLE)

    assert result is False, "webhook failed but the caller was told it succeeded"


@pytest.mark.asyncio
async def test_webhook_success_is_reported_as_success():
    """The fix must not simply invert the lie — success still returns True."""
    from app.services.n8n import trigger_credentials_delivered_webhook

    client, post = fake_httpx(status_code=200)
    with patch("httpx.AsyncClient", return_value=client), \
         patch("app.services.n8n.get_settings") as settings:
        settings.return_value.n8n_webhook_url = "https://n8n.test/webhook/x"
        settings.return_value.api_base_url = "https://api.test"
        result = await trigger_credentials_delivered_webhook(**SAMPLE)

    assert result is True