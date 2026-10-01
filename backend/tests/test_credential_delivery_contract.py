"""Regression tests for the credential-delivery payload contract.

Tonight's evidence: the live `Call Charon` n8n node returned
``NodeApiError 422 - Input should be a valid string`` (exec 150), and
``deliver_credentials_direct`` in ``n8n.py`` sent the identical wrong shape.
Both were validated against ``ChatReplyRequest`` in ``app/routers/charon.py``,
which declares ``user_message`` (required) and ``customer_phone``.

The consequence that matters: **funding the LLM would not have fixed it.** The
old payload never reached the model. So this suite asserts the contract
against the real Pydantic model rather than against a hand-copied dict -
asserting a dict matches itself proves nothing, which is why the drift
survived until a production execution failed.

`deliver_credentials_direct` has since been DELETED (t_2a4daeda) - it had zero
callers and read a `settings.api_base_url` field that does not exist on
`Settings`. The four payload tests that exercised it are replaced by
`test_direct_delivery_is_not_reintroduced`, which pins its absence and, more
importantly, pins *why* it must not come back: it posted the customer proxy
username and plaintext password as `user_message`, which the Charon agent
forwards to an external LLM provider. The live-payload half of the contract is
covered separately, against the real workflow, by
`test_n8n_charon_contract_drift.py`.
"""
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

from app.routers.charon import ChatReplyRequest


SAMPLE = dict(
    order_id="STX-TEST01",
    tx_ref="TXF-TEST01",
    phone="+234****0000",
    channel="web",
    styxproxy_username="styxproxy_abc",
    styxproxy_password="s3cret",
    proxy_ip="1.2.3.4",
    proxy_port=1080,
    expires_at=datetime(2026, 10, 30, tzinfo=timezone.utc),
    receipt_url="https://styxproxy.com/receipt/TXF-TEST01",
)


class FakeResponse:
    def __init__(self, status_code=200):
        self.status_code = status_code
        self.text = "ok"

    def raise_for_status(self):
        return None


def fake_httpx(status_code=200):
    """Patch httpx.AsyncClient so post() records the body and returns 200.

    The return value is the async context manager ITSELF, not a factory whose
    return value is the context manager.

    That distinction is why the failure-path test below was wrong for its
    entire life. `httpx.AsyncClient(...)` is called and its result is entered
    with `async with`. Returning `AsyncMock(return_value=ctx)` therefore makes
    `async with` enter the OUTER mock, whose `__aenter__` yields a fresh child
    mock - not `client`. Every attribute on that child is an auto-created
    AsyncMock, so `post()` returned a truthy mock, `raise_for_status()` returned
    another mock instead of raising, and the helper logged success and returned
    True. The test asserted `result is False` and failed - while the product
    code was correct all along and the harness was asserting nothing. The mock
    has to be patched at the object that is actually entered.
    """
    post = AsyncMock(return_value=FakeResponse(status_code))
    client = AsyncMock()
    client.post = post
    ctx = AsyncMock()
    ctx.__aenter__.return_value = client
    ctx.__aexit__.return_value = False
    return ctx, post


# -- the deleted direct-delivery path -----------------------------------

def test_direct_delivery_is_not_reintroduced():
    """`deliver_credentials_direct` must stay deleted, with its reason pinned.

    It had zero callers and crashed on its first statement (`settings.api_base_url`
    is not a field on `Settings`). Fixing it was rejected on purpose: its body
    posted the proxy username and PLAINTEXT PASSWORD as `user_message`, which
    `app/services/charon/agent.py` persists and forwards to an external LLM
    provider. Re-adding it would reconnect live customer credentials to a
    third-party model request.

    Asserting the attribute is absent is the regression guard: a future change
    that re-adds the function fails here instead of shipping a latent crash
    behind a test suite that reads as coverage of a live path.
    """
    import app.services.n8n as n8n

    assert not hasattr(n8n, "deliver_credentials_direct"), (
        "deliver_credentials_direct was removed as dead code that could not run "
        "(settings.api_base_url does not exist) and that would forward proxy "
        "credentials to an external LLM provider. If credential delivery must "
        "go somewhere new, use email (send_order_active_email) - do not "
        "reintroduce this."
    )


def test_no_code_path_posts_credentials_to_the_charon_llm_endpoint():
    """No module may build a Charon /reply URL for credential delivery.

    The endpoint is LLM-backed: `post_reply` -> `agent.reply` -> llm.py ->
    https://api.longcat.ai/chat/completions. Any code that posts proxy
    credentials there is handing them to a third-party model provider.
    This is the general guard behind the deletion above - it also fails on a
    re-introduction that uses a different helper name or builds the URL with an
    f-string, which the `hasattr` check alone would miss.
    """
    import pathlib

    import app

    app_root = pathlib.Path(app.__file__).resolve().parent
    offenders = [
        str(p.relative_to(app_root))
        for p in app_root.rglob("*.py")
        if "charon/reply" in p.read_text(encoding="utf-8", errors="replace")
        and p.name != "charon.py"
    ]

    assert not offenders, (
        "non-router module references the Charon /reply endpoint: "
        f"{offenders}. That endpoint forwards its user_message to an external "
        "LLM provider; never post proxy credentials to it."
    )


# -- the fire-and-forget lie --------------------------------------------

@pytest.mark.asyncio
async def test_webhook_failure_is_reported_as_failure():
    """The helper must not report success it did not observe.

    It used to `asyncio.create_task(...)` then `return True` unconditionally,
    so the fulfilment worker direct-email fallback was unreachable: n8n could
    fail every time and the worker still logged "delivered". Zero credentials
    have ever been emailed in this platform history, which is what that bug
    looks like from the outside.
    """
    from app.services.n8n import trigger_credentials_delivered_webhook

    ctx, post = fake_httpx(status_code=500)
    with patch("httpx.AsyncClient", return_value=ctx), \
         patch("app.services.n8n.get_settings") as settings:
        settings.return_value.n8n_webhook_url = "https://n8n.test/webhook/x"
        # A 500 makes raise_for_status raise, which the helper catches.
        async def boom():
            raise RuntimeError("500 Server Error")
        post.side_effect = boom
        result = await trigger_credentials_delivered_webhook(**SAMPLE)

    assert post.await_count == 1, (
        "the mocked post() was never awaited - the harness is not intercepting "
        "the real call, so this assertion could pass for the wrong reason"
    )
    assert result is False, "webhook failed but the caller was told it succeeded"


@pytest.mark.asyncio
async def test_webhook_success_is_reported_as_success():
    """The fix must not simply invert the lie - success still returns True."""
    from app.services.n8n import trigger_credentials_delivered_webhook

    ctx, post = fake_httpx(status_code=200)
    with patch("httpx.AsyncClient", return_value=ctx), \
         patch("app.services.n8n.get_settings") as settings:
        settings.return_value.n8n_webhook_url = "https://n8n.test/webhook/x"
        result = await trigger_credentials_delivered_webhook(**SAMPLE)

    assert post.await_count == 1, (
        "the mocked post() was never awaited - the harness is not intercepting "
        "the real call, so this assertion could pass for the wrong reason"
    )
    assert result is True


@pytest.mark.asyncio
async def test_webhook_payload_identifies_the_order_and_iso_dates():
    """The webhook body must identify the order, and expires_at must be ISO.

    `_record_failure` strips styxproxy_password before writing to Redis, so the
    payload legitimately carries it - but the URL, order id and tx_ref are what
    an operator needs to find the failure again.
    """
    from app.services.n8n import trigger_credentials_delivered_webhook

    ctx, post = fake_httpx(status_code=200)
    with patch("httpx.AsyncClient", return_value=ctx), \
         patch("app.services.n8n.get_settings") as settings:
        settings.return_value.n8n_webhook_url = "https://n8n.test/webhook/x"
        await trigger_credentials_delivered_webhook(**SAMPLE)

    assert post.await_args.args[0] == "https://n8n.test/webhook/x"
    body = post.await_args.kwargs["json"]
    assert body["order_id"] == "STX-TEST01"
    assert body["tx_ref"] == "TXF-TEST01"
    assert body["expires_at"] == "2026-10-30T00:00:00+00:00", (
        "expires_at must be ISO-8601 - the n8n workflow parses it as a date"
    )


# -- the request model itself -------------------------------------------

def test_chat_reply_request_requires_user_message():
    """The field the 422 was about, asserted on the model directly.

    Kept after the direct-delivery deletion because it documents the contract
    the live n8n `Call Charon` node is validated against by
    test_n8n_charon_contract_drift.py.
    """
    assert "user_message" in ChatReplyRequest.model_fields
    assert ChatReplyRequest.model_fields["user_message"].is_required()

    with pytest.raises(Exception):
        ChatReplyRequest(customer_phone="+234****0000")

    ok = ChatReplyRequest(user_message="hello", customer_phone="+234****0000")
    assert ok.customer_phone == "+234****0000"


def test_chat_reply_request_ignores_legacy_credential_keys():
    """'message'/'phone' are not fields on the model.

    A payload built with them sends NO prompt at all: `user_message` is
    required, so the request 422s on the missing field. That is the drift the
    production 422 came from, and it is loud rather than silent.
    """
    with pytest.raises(Exception) as excinfo:
        ChatReplyRequest.model_validate({"message": "creds", "phone": "+234****0000"})

    assert "user_message" in str(excinfo.value), (
        "the legacy payload must fail on the missing required field, so the "
        "breakage surfaces as a 422 instead of reaching the model as no prompt"
    )


def test_legacy_phone_key_does_not_populate_customer_phone():
    """'phone' must not quietly populate `customer_phone`.

    If it did, a legacy payload would appear to half-work and lose the contact
    address for escalation instead of failing loudly on the missing prompt.
    """
    assert "phone" not in ChatReplyRequest.model_fields

    body = ChatReplyRequest.model_validate(
        {"user_message": "hello", "phone": "+234****0000"}
    )
    assert body.customer_phone is None, (
        "'phone' must not silently populate customer_phone - a legacy payload "
        "loses the contact address instead of failing"
    )
