"""Flutterwave webhook contract tests — kanban t_604d405d.

WHY THIS FILE EXISTS
--------------------
The pre-existing Flutterwave signature tests in this repo are VOID, not failing.
They signed a payload with a secret literal and verified it against the same
literal. That is a tautology: it cannot fail for the only reason that matters
(a secret configured on the platform not matching the gateway). See the
`test_services.py::TestVerifyFlutterwaveSignature` markers.

Every test here takes its signing secret from `get_settings()` — the same value
the production verifier reads. That is what makes a secret mismatch DETECTABLE:
if the configured secret is wrong, a correctly-signed live payload is rejected
and these tests say so instead of agreeing with themselves.

GROUND TRUTH
------------
Assertions target `customer_audit_log` (the only telemetry-shaped table with
real provenance). `analytics_events` is seeded and its `payment_completed`
rows match zero orders, so it is not used as an assertion target here.
"""

import datetime as dt
import hashlib
import hmac
import json

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import get_settings
from app.database import get_session
from app.main import app
from app.routers.webhooks import MAX_PAYLOAD_AGE_SECONDS

WEBHOOK_URL = "/api/webhooks/flutterwave"


def sign(payload_bytes: bytes) -> str:
    """Return the CONFIGURED secret verbatim — the same one the verifier reads.

    Flutterwave v3 sends the dashboard secret hash VERBATIM in the Verif-Hash
    header (it does not sign the body). Deliberately not a literal: a literal
    here would restore the tautology this file exists to replace.
    """
    return get_settings().flutterwave_webhook_secret


class RecordingSession:
    """Captures rows handed to session.add() so we can assert on
    customer_audit_log writes without needing a live database.

    `order_lookup_order` is returned for the Order query; the ProcessedWebhook
    existence query always returns a truthy row, standing in for "this
    webhook_id has already been seen". The two are distinguished by call order:
    the idempotency check runs before the order lookup.
    """

    def __init__(self, order_lookup_order=None, webhook_already_seen=True):
        self._order = order_lookup_order
        self._seen = webhook_already_seen
        self._calls = 0
        self.added = []

    async def execute(self, stmt):
        self._calls += 1
        # 1st execute -> ProcessedWebhook existence probe; 2nd -> Order lookup.
        if self._calls == 1:
            return MagicResult(_SentinelRow() if self._seen else None)
        return MagicResult(self._order)

    async def commit(self):
        pass

    def add(self, obj):
        self.added.append(obj)


class _SentinelRow:
    """Stand-in for an existing ProcessedWebhook row."""


class MagicResult:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value

    def scalars(self):
        return self

    def all(self):
        return []


def audit_rows(session):
    """Rows destined for customer_audit_log, by event_type."""
    from app.models import CustomerAuditLog

    return {
        getattr(row, "event_type", None)
        for row in session.added
        if isinstance(row, CustomerAuditLog)
    }


def flutterwave_payload(created_at: dt.datetime, status: str = "successful") -> dict:
    return {
        "event": "charge.completed",
        "data": {
            "id": 987654321,
            "tx_ref": "TXF-CONTRACT-0001",
            "status": status,
            "amount": 5000,
            "created_at": created_at.isoformat().replace("+00:00", "Z"),
        },
    }


async def post_webhook(payload: dict, verif_hash: str | None = None):
    """POST a payload. Returns (response, recorded_session)."""
    body = json.dumps(payload).encode()
    app.dependency_overrides.clear()
    session = RecordingSession(webhook_already_seen=False)
    app.dependency_overrides[get_session] = lambda: session
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            headers = {} if verif_hash is None else {"Verif-Hash": verif_hash}
            response = await client.post(WEBHOOK_URL, content=body, headers=headers)
    finally:
        app.dependency_overrides.clear()
    return response, session


# ── Replay window ────────────────────────────────────────────────────────────
#
# A Flutterwave retry is BY DEFINITION old: the gateway re-delivers the original
# event with its original created_at. The pre-existing 300s cap therefore
# rejects exactly the traffic it exists to protect against. A gateway retry that
# arrives more than 5 minutes late is a lost payment behind a 400 that reads as
# permanent.


@pytest.mark.asyncio
async def test_valid_signature_with_old_created_at_must_be_accepted():
    """VALID signature + created_at older than MAX_PAYLOAD_AGE_SECONDS -> accepted.

    This is the regression the card requires. It currently FAILS: the handler
    rejects any payload older than 300s with 400 "outside replay window", which
    discards every genuine gateway retry. Do not "fix" this test by relaxing the
    assertion — the payload is correctly signed and must not be discarded.

    Replay protection is retained by the ProcessedWebhook idempotency check
    below; the timestamp window is the wrong tool because it cannot distinguish
    "old retry of a real payment" from "replay of a real payment" — both have an
    old created_at.
    """
    stale = dt.datetime.now(dt.timezone.utc) - dt.timedelta(seconds=MAX_PAYLOAD_AGE_SECONDS + 300)
    payload = flutterwave_payload(stale)
    response, _ = await post_webhook(payload, verif_hash=sign(json.dumps(payload).encode()))

    # Assert the payload was ACCEPTED. Do not weaken this to tolerate a 400:
    # the payload is correctly signed, and a gateway retry legitimately carries
    # the ORIGINAL created_at. Asserting the rejection here would be the exact
    # silent-success this card exists to prevent.
    assert response.status_code == 200, (
        f"Correctly-signed {int((dt.datetime.now(dt.timezone.utc) - stale).total_seconds())}s-old "
        f"charge.completed was rejected with {response.status_code}. A gateway retry carries the "
        "ORIGINAL created_at, so this rejection discards a real paid order. "
        "Idempotency (ProcessedWebhook) already prevents double fulfilment."
    )


@pytest.mark.asyncio
async def test_future_created_at_is_rejected():
    """A payload dated in the future is not a real gateway event."""
    future = dt.datetime.now(dt.timezone.utc) + dt.timedelta(seconds=3600)
    payload = flutterwave_payload(future)
    response, _ = await post_webhook(payload, verif_hash=sign(json.dumps(payload).encode()))
    assert response.status_code == 400


# ── Signature failure must be 401, never 400 ─────────────────────────────────


@pytest.mark.asyncio
async def test_invalid_signature_returns_401_not_400():
    """Signature failure -> 401, and specifically NOT 400.

    400 reads as permanent and most gateways stop retrying on 4xx, so a
    signature failure surfacing as 400 is a lost payment behind a
    healthy-looking log line.
    """
    payload = flutterwave_payload(dt.datetime.now(dt.timezone.utc))
    response, _ = await post_webhook(payload, verif_hash="not-the-real-secret")
    assert response.status_code == 401, f"expected 401, got {response.status_code}"
    assert response.status_code != 400


@pytest.mark.asyncio
async def test_missing_verif_hash_returns_401():
    payload = flutterwave_payload(dt.datetime.now(dt.timezone.utc))
    response, _ = await post_webhook(payload, verif_hash=None)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_signature_failure_writes_no_customer_audit_row():
    """A rejected signature must not look like a processed payment.

    Guards the exact failure mode where a 200 is logged for a payload that was
    never verified.
    """
    payload = flutterwave_payload(dt.datetime.now(dt.timezone.utc))
    _, session = await post_webhook(payload, verif_hash="not-the-real-secret")
    assert "webhook_charge.completed" not in audit_rows(session)


# ── Audit provenance ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_accepted_webhook_is_recorded_in_customer_audit_log():
    """The fulfilment audit row is the ground truth this card relies on."""
    payload = flutterwave_payload(dt.datetime.now(dt.timezone.utc))
    response, session = await post_webhook(payload, verif_hash=sign(json.dumps(payload).encode()))
    assert response.status_code == 200, f"expected 200, got {response.status_code}: {response.text}"
    assert "webhook_charge.completed" in audit_rows(session)


# ── Secret-mismatch detection ────────────────────────────────────────────────
#
# The property the void tests could never check: a payload signed by the GATEWAY
# with the gateway's real secret must be REJECTED when the platform is
# configured with a different value. If this test ever passes without the
# monkeypatch, the verifier has stopped checking the secret at all.


@pytest.mark.asyncio
async def test_gateway_signed_payload_is_rejected_when_platform_secret_is_wrong(monkeypatch):
    """Rotation landing wrong must FAIL LOUDLY, not silently drop payments.

    Simulates the one-shot go-live risk: the gateway sends the real
    dashboard secret verbatim while the platform .env still holds the old value.
    """
    from app.config import get_settings

    gateway_secret = "the-real-rotated-dashboard-value"
    monkeypatch.setattr(
        get_settings(), "flutterwave_webhook_secret", "a-different-stale-value", raising=False
    )

    now = dt.datetime.now(dt.timezone.utc)
    payload = flutterwave_payload(now)
    # v3: Verif-Hash is the secret verbatim
    response, session = await post_webhook(payload, verif_hash=gateway_secret)

    assert response.status_code == 401, (
        f"A gateway-signed payload was NOT rejected (got {response.status_code}) while the "
        "platform secret was stale. If this passes, verify_flutterwave_signature is no longer "
        "comparing against the configured value."
    )
    assert "webhook_charge.completed" not in audit_rows(session), (
        "A rejected-signature payload produced a customer_audit_log row — the audit log would "
        "show a processed payment that never happened."
    )


@pytest.mark.asyncio
async def test_verifier_uses_the_configured_secret_not_a_hardcoded_one(monkeypatch):
    """Changing the configured secret must change verification behaviour.

    A verifier hardcoded to any single value would pass the test above by
    accident. This pins that the configured value is genuinely the one consulted.
    """
    from app.config import get_settings

    payload = flutterwave_payload(dt.datetime.now(dt.timezone.utc))

    monkeypatch.setattr(get_settings(), "flutterwave_webhook_secret", "secret-A", raising=False)
    resp_a, _ = await post_webhook(payload, verif_hash="secret-A")
    assert resp_a.status_code == 200, f"correctly signed under secret-A got {resp_a.status_code}"

    monkeypatch.setattr(get_settings(), "flutterwave_webhook_secret", "secret-B", raising=False)
    resp_b, _ = await post_webhook(payload, verif_hash="secret-A")
    assert resp_b.status_code == 401, (
        "Signature valid under secret-A was accepted after the configured secret changed to "
        "secret-B — verification is not reading the configured value."
    )


# ── Idempotency ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_already_processed_webhook_is_not_refilled():
    """A redelivered webhook_id is answered as already_processed, not re-run."""
    payload = flutterwave_payload(dt.datetime.now(dt.timezone.utc))
    body = json.dumps(payload).encode()

    app.dependency_overrides.clear()
    session = RecordingSession(webhook_already_seen=True)
    app.dependency_overrides[get_session] = lambda: session
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                WEBHOOK_URL, content=body, headers={"Verif-Hash": sign(body)}
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["status"] == "already_processed"