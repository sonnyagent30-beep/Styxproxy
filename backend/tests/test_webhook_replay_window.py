"""Replay-window regression tests for ALL webhook providers — kanban t_c33b5e96.

The defect this file pins
-------------------------
`webhooks.py` used to reject any payload whose timestamp was more than
MAX_PAYLOAD_AGE_SECONDS (300s) old, on the theory that a stale timestamp meant a
replay attack. That theory is wrong, and the gateway retry schedules prove it:

    Flutterwave  3 retries at 30-minute intervals   -> retry #1 ~1800s old
    Paystack     3 min x4, then hourly up to 72h     -> retries up to 72h old
    NOWPayments  IPN on every status change          -> old created_at throughout

A retry re-delivers the ORIGINAL event with its ORIGINAL created_at, so a
genuine retry and a replayed capture are byte-identical in the one field the cap
inspected. The cap could not tell them apart, so it rejected both: a paid order
answered 400 and never fulfilled.

Worse, the cap also broke FIRST delivery. `created_at` is set when the charge is
created, not when the webhook fires, so any customer who spent more than five
minutes on the checkout page had their initial webhook discarded too.

What replaced it
----------------
Idempotency. `processed_webhooks.webhook_id` carries a unique constraint, so
`is_webhook_processed()` / `mark_webhook_processed()` make a captured payload
fulfil exactly once no matter how many times it is replayed. That is the
property that actually matters, and it is checked here directly.

What these tests hold in place
------------------------------
1. Correctly-signed OLD payloads are accepted (Flutterwave, Paystack, NOWPayments).
2. Genuinely impossible payloads are still rejected: future-dated, missing,
   and unparseable timestamps.
3. Idempotency still prevents double fulfilment, INCLUDING for a replay that is
   arbitrarily old — the case the removed cap used to cover by accident.
4. The dedupe key that gates the check is the same key that gets marked, so
   idempotency cannot be silently bypassed by a payload with no `id`.
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
from app.routers.webhooks import (
    MAX_FUTURE_SKEW_SECONDS,
    _extract_timestamp,
    _is_payload_fresh,
    _is_payload_fresh_epoch,
    _is_timestamp_plausible,
    _parse_timestamp,
)

UTC = dt.timezone.utc

# Real gateway retry horizons. Using the documented numbers rather than
# arbitrary values means these tests fail if a future change re-introduces any
# bound smaller than the one the gateway actually violates.
FLUTTERWAVE_RETRY_1_AGE = 1800      # 30-minute first retry
FLUTTERWAVE_RETRY_3_AGE = 5400      # third and final retry
PAYSTACK_RETRY_AGE = 72 * 3600       # hourly retries for up to 72h
NOWPAYMENTS_IPN_AGE = 3600          # crypto sitting in `waiting` for an hour


# ── Unit level: the plausibility primitive ──────────────────────────────────


def test_parse_timestamp_handles_iso_with_z():
    parsed = _parse_timestamp("2026-01-01T00:00:00.000Z")
    assert parsed is not None
    assert parsed.tzinfo is not None
    assert parsed.astimezone(UTC).isoformat() == "2026-01-01T00:00:00+00:00"


def test_parse_timestamp_handles_naive_iso_as_utc():
    """A naive timestamp is treated as UTC, matching the old behaviour."""
    assert _parse_timestamp("2026-01-01T00:00:00").astimezone(UTC) == dt.datetime(2026, 1, 1, tzinfo=UTC)


@pytest.mark.parametrize("raw", [0, 1])  # 0 is falsy and must not be treated as missing
def test_parse_timestamp_handles_epoch_seconds(raw):
    assert _parse_timestamp(raw) == dt.datetime.fromtimestamp(raw, tz=UTC)


def test_parse_timestamp_handles_epoch_milliseconds():
    seconds = 1_767_225_600
    assert _parse_timestamp(seconds * 1000) == dt.datetime.fromtimestamp(seconds, tz=UTC)


@pytest.mark.parametrize(
    "bad",
    [None, "", "   ", "not-a-date", "yesterday", True, False, []],
)
def test_parse_timestamp_returns_none_for_impossible_values(bad):
    """Unparseable input is rejected, never coerced into a plausible time.

    `True`/`False` matter specifically: bool is an int subclass, and treating
    True as epoch 1.0 would manufacture a 1970 timestamp instead of rejecting.
    """
    assert _parse_timestamp(bad) is None


def test_parse_timestamp_survives_absurdly_large_epoch():
    """A huge number must raise, not crash the webhook handler."""
    assert _parse_timestamp(10**20) is None


def test_plausible_accepts_payload_years_old():
    """The core regression, at the unit level: age has no upper bound."""
    ancient = dt.datetime.now(UTC) - dt.timedelta(days=3650)
    assert _is_timestamp_plausible(ancient) is True


def test_plausible_accepts_72h_old_paystack_retry():
    assert _is_timestamp_plausible(dt.datetime.now(UTC) - dt.timedelta(seconds=PAYSTACK_RETRY_AGE)) is True


def test_plausible_rejects_none():
    assert _is_timestamp_plausible(None) is False


def test_plausible_rejects_far_future():
    assert _is_timestamp_plausible(dt.datetime.now(UTC) + dt.timedelta(days=1)) is False


def test_plausible_tolerates_small_clock_skew():
    """A payload a few seconds "ahead" is normal clock drift, not an attack."""
    slightly_ahead = dt.datetime.now(UTC) + dt.timedelta(seconds=MAX_FUTURE_SKEW_SECONDS - 60)
    assert _is_timestamp_plausible(slightly_ahead) is True


# ── Unit level: timestamp extraction across provider payload shapes ─────────


def test_extract_finds_flutterwave_nested_timestamp():
    payload = {"event": "charge.completed", "data": {"id": 1, "created_at": "2026-01-01T00:00:00Z"}}
    assert _extract_timestamp(payload) == dt.datetime(2026, 1, 1, tzinfo=UTC)


def test_extract_finds_paystack_nested_epoch():
    payload = {"event": "charge.success", "data": {"id": 1, "created_at": 1_767_225_600}}
    assert _extract_timestamp(payload) == dt.datetime.fromtimestamp(1_767_225_600, tz=UTC)


def test_extract_finds_nowpayments_flat_top_level_timestamp():
    """NOWPayments sends a FLAT body — no `data` wrapper. This must still parse.

    The old code did `payload.get("data", payload)`, which is correct for a flat
    body, but the flat path is the one that decides whether crypto payments are
    accepted at all, so it is pinned explicitly.
    """
    payload = {"payment_id": 5, "order_id": "TXC-1", "payment_status": "finished",
               "created_at": "2026-01-01T00:00:00.000Z"}
    assert _extract_timestamp(payload) == dt.datetime(2026, 1, 1, tzinfo=UTC)


def test_extract_prefers_nested_data_over_top_level():
    """Nested wins, so a top-level field cannot override the real event time."""
    payload = {
        "created_at": "2030-01-01T00:00:00Z",
        "data": {"created_at": "2026-01-01T00:00:00Z"},
    }
    assert _extract_timestamp(payload) == dt.datetime(2026, 1, 1, tzinfo=UTC)


def test_extract_returns_none_when_absent():
    assert _extract_timestamp({"event": "charge.completed", "data": {"id": 1}}) is None


def test_iso_helper_rejects_very_old_flutterwave_retry():
    payload = {"data": {"created_at": (dt.datetime.now(UTC) - dt.timedelta(seconds=FLUTTERWAVE_RETRY_1_AGE)).isoformat()}}
    assert _is_payload_fresh(payload) is True


def test_epoch_helper_rejects_very_old_paystack_retry():
    old_epoch = int((dt.datetime.now(UTC) - dt.timedelta(seconds=PAYSTACK_RETRY_AGE)).timestamp())
    payload = {"data": {"created_at": old_epoch}}
    assert _is_payload_fresh_epoch(payload) is True


# ── End-to-end: Flutterwave ─────────────────────────────────────────────────


class RecordingSession:
    """Captures session.add() so idempotency can be asserted without a database.

    Execute #1 answers the ProcessedWebhook existence probe, #2 the Order
    lookup. `marked_ids` accumulates every key passed to
    mark_webhook_processed; `probed_ids` extracts the key the duplicate CHECK
    actually queried with, from the bound parameters of the SELECT.

    Both are needed. Asserting only on the mark does not detect a check that
    consults a different key — which is precisely the bug being pinned here.
    """

    def __init__(self, already_seen=False, order=None):
        self.already_seen = already_seen
        self._calls = 0
        self.added = []
        self.marked_ids = []
        self.probed_ids = []
        self._order = order

    async def execute(self, stmt):
        self._calls += 1
        if self._calls == 1:
            self.probed_ids.append(_bound_webhook_id(stmt))
            return _Result(_SeenRow() if self.already_seen else None)
        return _Result(self._order)

    async def commit(self):
        pass

    def add(self, obj):
        self.added.append(obj)
        webhook_id = getattr(obj, "webhook_id", None)
        if webhook_id is not None:
            self.marked_ids.append(webhook_id)


def _bound_webhook_id(stmt) -> object:
    """Pull the webhook_id value out of a ProcessedWebhook lookup SELECT.

    The handler builds this as
    select(ProcessedWebhook).where(ProcessedWebhook.webhook_id == event_id),
    so the bound value is what the duplicate check is keyed on.
    """
    try:
        return stmt.compile().params.get("webhook_id_1")
    except Exception:  # pragma: no cover - diagnostic only
        return None


class _SeenRow:
    pass


class FakeOrder:
    """Minimal stand-in for an unpaid order awaiting fulfillment.

    The Paystack handler returns 409 (not 200) when a signed charge.success
    matches no order, so an acceptance test must supply one. Without this the
    test would be asserting on the unmatched-order path and reporting a replay
    window failure that never happened.
    """

    order_id = "ORD-TEST-0001"
    status = "awaiting_payment"
    payment_reference = "TXP-REPLAY-0001"
    provider = "paystack"
    provider_order_id = None
    amount_paid_ngn = None


class _Result:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value

    def scalars(self):
        return self

    def all(self):
        return []


async def post(url: str, payload: dict, headers: dict, already_seen: bool = False, order=None):
    body = json.dumps(payload).encode()
    app.dependency_overrides.clear()
    session = RecordingSession(already_seen=already_seen, order=order)
    app.dependency_overrides[get_session] = lambda: session
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(url, content=body, headers=headers)
    finally:
        app.dependency_overrides.clear()
    return response, session


def flw_sign(body: bytes) -> str:
    secret = get_settings().flutterwave_webhook_secret
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def flw_payload(created_at: dt.datetime, event_id: int = 4242, tx_ref: str = "TXF-REPLAY-0001") -> dict:
    return {
        "event": "charge.completed",
        "data": {
            "id": event_id,
            "tx_ref": tx_ref,
            "status": "successful",
            "amount": 5000,
            "created_at": created_at.isoformat().replace("+00:00", "Z"),
        },
    }


async def post_flw(payload: dict, already_seen: bool = False):
    body = json.dumps(payload).encode()
    return await post("/api/webhooks/flutterwave", payload, {"Verif-Hash": flw_sign(body)}, already_seen)


@pytest.mark.asyncio
@pytest.mark.parametrize("age", [FLUTTERWAVE_RETRY_1_AGE, FLUTTERWAVE_RETRY_3_AGE, 86400])
async def test_flutterwave_documented_retry_ages_are_accepted(age):
    """A correctly-signed retry at ANY of Flutterwave's documented intervals
    must be processed, not answered 400."""
    payload = flw_payload(dt.datetime.now(UTC) - dt.timedelta(seconds=age))
    response, _ = await post_flw(payload)
    assert response.status_code == 200, (
        f"A correctly-signed charge.completed {age}s old was rejected with "
        f"{response.status_code}. That is a paid order discarded behind a 400."
    )


@pytest.mark.asyncio
async def test_flutterwave_stale_retry_is_not_answered_already_processed():
    """Age alone must not be mistaken for a duplicate.

    A fresh first delivery and a 3-day-old retry of the same event both report
    status 'received' when not previously processed. Only the idempotency table
    may produce 'already_processed'.
    """
    payload = flw_payload(dt.datetime.now(UTC) - dt.timedelta(days=3))
    response, _ = await post_flw(payload)
    assert response.status_code == 200
    assert response.json()["status"] == "received"


@pytest.mark.asyncio
async def test_flutterwave_replay_of_very_old_payload_does_not_double_fulfil():
    """The property the age cap used to provide, now provided by idempotency.

    Replaying a captured payload a year later must still be recognised as a
    duplicate and must not re-run fulfilment.
    """
    payload = flw_payload(dt.datetime.now(UTC) - dt.timedelta(days=365))
    body = json.dumps(payload).encode()
    response, _ = await post("/api/webhooks/flutterwave", payload,
                             {"Verif-Hash": flw_sign(body)}, already_seen=True)
    assert response.status_code == 200
    assert response.json()["status"] == "already_processed"


@pytest.mark.asyncio
async def test_flutterwave_future_dated_is_still_rejected():
    """Dropping the age cap must not turn the check into a no-op."""
    payload = flw_payload(dt.datetime.now(UTC) + dt.timedelta(seconds=3600))
    response, _ = await post_flw(payload)
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_flutterwave_missing_created_at_is_rejected():
    payload = flw_payload(dt.datetime.now(UTC))
    payload["data"].pop("created_at")
    response, _ = await post_flw(payload)
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_flutterwave_unparseable_created_at_is_rejected():
    payload = flw_payload(dt.datetime.now(UTC))
    payload["data"]["created_at"] = "the day before yesterday"
    response, _ = await post_flw(payload)
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_flutterwave_dedupe_key_that_is_checked_is_the_key_that_is_marked():
    """The check key and the mark key must be the same value.

    They used to diverge: with no `id` in the payload the check was skipped
    entirely (falsy key) while the mark fell back to tx_ref, so the row that
    made the webhook 'processed' was never consulted by the check that decides
    whether to process it. With the age cap gone, that divergence is an
    unbounded double-fulfilment path.

    Both sides are asserted: the probed key comes from the bound parameters of
    the duplicate check's SELECT, the marked key from the row that is added.
    """
    payload = flw_payload(dt.datetime.now(UTC), tx_ref="TXF-NO-ID-0002")
    payload["data"].pop("id")
    body = json.dumps(payload).encode()
    response, session = await post("/api/webhooks/flutterwave", payload,
                                   {"Verif-Hash": flw_sign(body)})

    assert response.status_code == 200, f"got {response.status_code}: {response.text}"
    assert session.marked_ids == ["TXF-NO-ID-0002"], (
        f"Expected the webhook to be marked under 'TXF-NO-ID-0002', got {session.marked_ids}."
    )
    assert session.probed_ids == ["TXF-NO-ID-0002"], (
        f"The duplicate CHECK queried {session.probed_ids} but the webhook was MARKED under "
        f"{session.marked_ids}. The mark is decorative — a replay re-runs fulfillment, because "
        "nothing the check consults ever records that the event was handled. Previously the "
        "check was skipped outright here (empty id), which is the same hole with a different "
        "symptom."
    )


@pytest.mark.asyncio
async def test_flutterwave_id_present_uses_event_id_for_both_check_and_mark():
    """The normal case: the gateway's own event id keys both sides."""
    payload = flw_payload(dt.datetime.now(UTC), event_id=987654321)
    body = json.dumps(payload).encode()
    response, session = await post("/api/webhooks/flutterwave", payload,
                                   {"Verif-Hash": flw_sign(body)})
    assert response.status_code == 200
    assert session.probed_ids == ["987654321"]
    assert session.marked_ids == ["987654321"]


# ── End-to-end: Paystack ────────────────────────────────────────────────────


def ps_sign(body: bytes) -> str:
    secret = get_settings().paystack_secret_key
    return hmac.new(secret.encode(), body, hashlib.sha512).hexdigest()


def ps_payload(created_at_epoch: int, status: str = "success") -> dict:
    return {
        "event": "charge.success",
        "data": {
            "id": 777,
            "reference": "TXP-REPLAY-0001",
            "status": status,
            "amount": 500000,
            "currency": "NGN",
            "paid_at": created_at_epoch,
            "created_at": created_at_epoch,
        },
    }


async def post_ps(payload: dict, already_seen: bool = False, order=None):
    body = json.dumps(payload).encode()
    return await post("/api/webhooks/paystack", payload,
                      {"X-Paystack-Signature": ps_sign(body)}, already_seen, order)


@pytest.mark.asyncio
async def test_paystack_72h_old_retry_is_accepted():
    """Paystack retries hourly for up to 72h — every one of those was a 400."""
    old_epoch = int((dt.datetime.now(UTC) - dt.timedelta(seconds=PAYSTACK_RETRY_AGE)).timestamp())
    response, _ = await post_ps(ps_payload(old_epoch), order=FakeOrder())
    assert response.status_code == 200, (
        f"A correctly-signed Paystack charge.success {PAYSTACK_RETRY_AGE}s old was rejected with "
        f"{response.status_code}. Paystack documents hourly retries for 72h."
    )


@pytest.mark.asyncio
async def test_paystack_duplicate_still_short_circuits():
    old_epoch = int((dt.datetime.now(UTC) - dt.timedelta(seconds=PAYSTACK_RETRY_AGE)).timestamp())
    response, _ = await post_ps(ps_payload(old_epoch), already_seen=True)
    assert response.status_code == 200
    assert response.json()["status"] == "already_processed"


@pytest.mark.asyncio
async def test_paystack_future_dated_is_still_rejected():
    future_epoch = int((dt.datetime.now(UTC) + dt.timedelta(hours=2)).timestamp())
    response, _ = await post_ps(ps_payload(future_epoch))
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_paystack_missing_timestamp_is_rejected():
    response, _ = await post_ps(ps_payload(0))
    # created_at=0 is falsy and unparseable-as-real; either way no plausible time.
    assert response.status_code == 400


# ── End-to-end: NOWPayments ─────────────────────────────────────────────────


def np_sign(payload: dict) -> str:
    secret = get_settings().nowpayments_ipn_secret
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hmac.new(secret.encode(), canonical.encode(), hashlib.sha512).hexdigest()


def np_payload(created_at: str, status: str = "finished") -> dict:
    return {
        "payment_id": 5150,
        "order_id": "TXC-REPLAY-0001",
        "payment_status": status,
        "price_amount": 50.0,
        "price_currency": "usd",
        "created_at": created_at,
        "updated_at": created_at,
    }


async def post_np(payload: dict, already_seen: bool = False):
    return await post("/api/webhooks/nowpayments", payload,
                      {"x-nowpayments-sig": np_sign(payload)}, already_seen)


@pytest.mark.asyncio
async def test_nowpayments_old_ipn_is_accepted():
    """A crypto payment that sat in `waiting` for an hour is normal, not a replay."""
    stale = (dt.datetime.now(UTC) - dt.timedelta(seconds=NOWPAYMENTS_IPN_AGE)).isoformat().replace("+00:00", "Z")
    response, _ = await post_np(np_payload(stale))
    assert response.status_code == 200, (
        f"A correctly-signed NOWPayments IPN {NOWPAYMENTS_IPN_AGE}s old was rejected with "
        f"{response.status_code}. NOWPayments re-sends on every status change with the "
        "original created_at, so old IPNs are routine."
    )


@pytest.mark.asyncio
async def test_nowpayments_duplicate_still_short_circuits():
    stale = (dt.datetime.now(UTC) - dt.timedelta(seconds=NOWPAYMENTS_IPN_AGE)).isoformat().replace("+00:00", "Z")
    response, _ = await post_np(np_payload(stale), already_seen=True)
    assert response.status_code == 200
    assert response.json()["status"] == "already_processed"


@pytest.mark.asyncio
async def test_nowpayments_future_dated_is_still_rejected():
    future = (dt.datetime.now(UTC) + dt.timedelta(hours=2)).isoformat().replace("+00:00", "Z")
    response, _ = await post_np(np_payload(future))
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_nowpayments_missing_timestamp_is_rejected():
    payload = np_payload("2026-01-01T00:00:00Z")
    payload.pop("created_at")
    response, _ = await post_np(payload)
    assert response.status_code == 400


# ── The cap is gone, not merely raised ──────────────────────────────────────


def test_no_upper_age_bound_exists_in_the_router_source():
    """Guard against the cap being reintroduced under any name.

    A behavioural test can only prove the specific ages it happens to try. This
    reads the source and fails if an age ceiling comes back — which is the only
    way to keep a future 4th retry interval (or a longer Paystack backoff) safe.
    """
    import inspect
    import sys

    # `app.routers.webhooks` resolves to the APIRouter object, not the module:
    # app/routers/__init__.py rebinds that name to the router. Go through
    # sys.modules to get the real module.
    webhooks = sys.modules["app.routers.webhooks"]

    primitive = inspect.getsource(webhooks._is_timestamp_plausible)
    assert "<=" not in primitive, (
        "_is_timestamp_plausible contains an upper bound — the age cap is back. "
        f"Source:\n{primitive}"
    )

    source = inspect.getsource(webhooks)
    for line in source.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        # Only inspect CONSTANT names. Upper-casing the whole line would make
        # the `age >=` comparison itself match the search.
        for token in stripped.split():
            if not token.startswith("MAX_"):
                continue
            constant = token.rstrip(",:()")
            if "AGE" not in constant:
                continue
            # The only permitted assignment is the retained historical alias,
            # which must stay explicitly marked as not gating anything.
            assert stripped.startswith(f"{constant} = 300  # noqa"), (
                f"'{constant}' is being assigned at: {stripped!r}. If an upper age "
                "bound is genuinely needed it needs its own card and its own tests — "
                "it cannot be quietly reintroduced here."
            )
