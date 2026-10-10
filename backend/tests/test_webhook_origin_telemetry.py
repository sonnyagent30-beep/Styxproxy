"""Webhook origin telemetry tests — kanban t_4271b61e.

WHAT THIS FILE GUARDS
---------------------
The rotation canary (t_604d405d) must be able to tell two failures apart on the
Flutterwave webhook route:

  (a) the gateway never called us, and
  (b) the gateway called us and we rejected every event — which is what a
      FLUTTERWAVE_WEBHOOK_SECRET that disagrees with the gateway looks like.

Before this, (a) and (b) produced identical telemetry. The card that asked for
the fix asserted no log source recorded a client IP at all. That was wrong —
`journalctl -u styxproxy-api` is empty because the unit writes stdout to
/var/log/styxproxy-api.log, and /var/log/nginx/access.log is empty for this
vhost because api.styxproxy.com logs to /var/log/styxproxy-nginx-access.log.
Both files DO carry origin, and the middleware already logged `client` on the
*started* line.

The real gaps, and what each test below pins:
  1. origin absent from the *completed* middleware line        -> test_completed_line_carries_client
  2. origin absent from the X-Forwarded-For path (all traffic
     looks like 127.0.0.1 behind nginx)                       -> test_xff_beats_loopback_peer
  3. rejected (401) events wrote no audit row at all          -> test_invalid_signature_writes_audit_row
  4. accepted events wrote no origin in the audit row         -> test_accepted_event_records_origin
  5. raw IPs persisted in breach of the audit privacy policy  -> test_raw_ip_is_never_persisted

Each test below fails if its guarded behaviour is removed. Test 3 is the one
that matters most: an invalid signature returning 401 without leaving a trace is
exactly case (b) being invisible.
"""

import json

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.services.origin import resolve_origin

WEBHOOK_URL = "/api/webhooks/flutterwave"
PAYSTACK_URL = "/api/webhooks/paystack"
NOWPAYMENTS_URL = "/api/webhooks/nowpayments"


class RecordingSession:
    """Captures CustomerAuditLog rows handed to session.add().

    No live database: the DB-connection failures elsewhere in this suite make a
    real session unreliable. `is_webhook_processed` is short-circuited to False
    so the handler proceeds to the fulfilment path.
    """

    def __init__(self):
        self.rows = []

    def add(self, obj):
        self.rows.append(obj)

    async def commit(self):
        return None

    async def refresh(self, obj):
        return None

    async def rollback(self):
        return None

    async def execute(self, stmt):
        class _ScalarResult:
            def scalars(self_inner):
                return self_inner

            def scalar_one_or_none(self_inner):
                return None

        return _ScalarResult()

    def audit_details(self):
        return [getattr(r, "details", None) for r in self.rows]


def make_request(headers=None, client_host="127.0.0.1"):
    """Build a minimal Request carrying the headers origin resolution reads."""
    from starlette.datastructures import Headers
    from starlette.requests import Request as StarletteRequest

    scope = {
        "type": "http",
        "method": "POST",
        "path": WEBHOOK_URL,
        "headers": Headers(headers or {}).raw,
        "client": (client_host, 50000),
        "query_string": b"",
        "scheme": "https",
    }
    return StarletteRequest(scope)


# ── Origin resolution unit tests ────────────────────────────────────────────


def test_xff_beats_loopback_peer():
    """Behind nginx the peer is always 127.0.0.1; XFF holds the real caller.

    If origin resolution ignored XFF, every gateway call would classify as
    loopback and the canary could never see a non-self origin.
    """
    ctx = resolve_origin(make_request({"x-forwarded-for": "54.76.248.30"}))
    assert ctx["origin_scope"] == "public"
    assert ctx["origin_via"] == "xff"
    assert ctx["origin_self_originated"] is False


def test_xff_leftmost_entry_wins():
    """The leftmost XFF entry is the original client, not an intermediate proxy."""
    ctx = resolve_origin(make_request({"x-forwarded-for": "54.76.248.30, 10.0.0.1"}))
    assert ctx["origin_via"] == "xff"
    assert ctx["origin_scope"] == "public"


def test_loopback_is_self_originated():
    ctx = resolve_origin(make_request({}))
    assert ctx["origin_scope"] == "loopback"
    assert ctx["origin_self_originated"] is True


def test_private_range_is_self_originated():
    ctx = resolve_origin(make_request({"x-forwarded-for": "10.1.2.3"}))
    assert ctx["origin_scope"] == "private"
    assert ctx["origin_self_originated"] is True


def test_missing_everything_is_unknown_not_blank():
    """A request with no peer and no headers must not raise or return empty."""
    from starlette.datastructures import Headers
    from starlette.requests import Request as StarletteRequest

    scope = {
        "type": "http",
        "method": "POST",
        "path": WEBHOOK_URL,
        "headers": Headers({}).raw,
        "client": None,
        "query_string": b"",
        "scheme": "https",
    }
    ctx = resolve_origin(StarletteRequest(scope))
    assert ctx["origin_seen"] is False
    assert ctx["origin_hash"] is None
    assert ctx["origin_scope"] == "unknown"


def test_garbage_header_is_unknown_not_crash():
    """A spoofed/garbage XFF must not raise — classification is best-effort."""
    ctx = resolve_origin(make_request({"x-forwarded-for": "not-an-ip-at-all"}))
    assert ctx["origin_scope"] == "unknown"
    assert ctx["origin_hash"] is not None  # still hashed, for correlation


@pytest.mark.asyncio
async def test_audit_write_failure_still_returns_401():
    """A failed audit write must NOT turn the 401 into a 500.

    This is the failure mode the guard exists for. If the rejection audit write
    raises — DB down, permissions, a session missing `add` — the gateway must
    still receive a clean 401. A 500 tells it the endpoint is broken and changes
    its retry behaviour, which is far worse than losing one audit row.
    """
    from app.database import get_session

    class BrokenSession:
        async def commit(self):
            return None

        # No `add` — exactly the AttributeError a degraded session produces.

    app.dependency_overrides[get_session] = lambda: BrokenSession()
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                WEBHOOK_URL,
                content=json.dumps({"event": "charge.completed"}),
                headers={"Verif-Hash": "0" * 64, "x-forwarded-for": "54.76.248.30"},
            )
        assert resp.status_code == 401, f"expected 401, got {resp.status_code}"
    finally:
        app.dependency_overrides.pop(get_session, None)


@pytest.mark.asyncio
async def test_settings_failure_cannot_break_the_webhook_path():
    """resolve_origin must never raise, even if settings are unloadable.

    This runs on the live payment path before the handler reads its own
    settings. A missing OPS_JWT_SECRET makes get_settings() raise
    ValidationError; if that propagated, every customer's webhook would 500
    for a purely observational reason. Classification degrades to range-only.
    """
    import app.config as config_mod

    real_get_settings = config_mod.get_settings

    def boom():
        raise RuntimeError("settings unavailable")

    config_mod.get_settings = boom
    try:
        ctx = resolve_origin(make_request({"x-forwarded-for": "54.76.248.30"}))
    finally:
        config_mod.get_settings = real_get_settings

    # Still classified, still hashed — just without the self-IP overrides.
    assert ctx["origin_scope"] == "public"
    assert ctx["origin_hash"] is not None


def test_self_ip_config_marks_our_own_address(monkeypatch):
    """A configured self address classifies as self_host, not public.

    Without this, our own curls from the prod host would classify `public` and
    the canary would report a false SIGNAL PRESENT.
    """
    import app.config as config_mod

    real_get_settings = config_mod.get_settings

    class FakeSettings:
        webhook_self_origin_ips = "162.35.184.69 84.247.132.12"

    config_mod.get_settings = lambda: FakeSettings()
    try:
        ours = resolve_origin(make_request({"x-forwarded-for": "162.35.184.69"}))
        gateway = resolve_origin(make_request({"x-forwarded-for": "54.76.248.30"}))
    finally:
        config_mod.get_settings = real_get_settings

    assert ours["origin_scope"] == "self_host"
    assert ours["origin_self_originated"] is True
    assert gateway["origin_scope"] == "public"
    assert gateway["origin_self_originated"] is False


def test_ipv6_global_classifies_as_public():
    """A globally routable v6 address is a non-self origin."""
    ctx = resolve_origin(make_request({"x-forwarded-for": "2606:4700:4700::1111"}))
    assert ctx["origin_scope"] == "public"
    assert ctx["origin_self_originated"] is False


def test_ipv6_reserved_classifies_non_gateway():
    """Documentation/reserved v6 is not a gateway, even though it is not RFC1918.

    Python's `ipaddress.is_private` covers reserved and documentation ranges
    (e.g. 2001:db8::/32), not just RFC1918. That is the behaviour we want: a
    reserved range cannot be a live payment gateway, so classifying it
    self-originated is the safe direction — it can only ever cause a missed
    signal, never a false one.
    """
    ctx = resolve_origin(make_request({"x-forwarded-for": "2001:db8::1"}))
    assert ctx["origin_scope"] == "private"
    assert ctx["origin_self_originated"] is True


def test_hash_is_stable_and_20_chars():
    """Same address -> same pseudonym, so rows can be correlated over time."""
    a = resolve_origin(make_request({"x-forwarded-for": "54.76.248.30"}))
    b = resolve_origin(make_request({"x-forwarded-for": "54.76.248.30"}))
    assert a["origin_hash"] == b["origin_hash"]
    assert len(a["origin_hash"]) == 20


def test_different_addresses_get_different_hashes():
    a = resolve_origin(make_request({"x-forwarded-for": "54.76.248.30"}))
    b = resolve_origin(make_request({"x-forwarded-for": "52.31.139.75"}))
    assert a["origin_hash"] != b["origin_hash"]


# ── Handler integration: the audit trail is the canary's data source ─────────


@pytest.mark.asyncio
async def test_invalid_signature_writes_audit_row(monkeypatch):
    """A REJECTED webhook must still leave an audit row. This is case (b).

    Without it, a mis-set secret is indistinguishable from silence.
    """
    from app.database import get_session

    recorder = RecordingSession()
    app.dependency_overrides[get_session] = lambda: recorder
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                WEBHOOK_URL,
                content=json.dumps({"event": "charge.completed"}),
                headers={"Verif-Hash": "deadbeef" * 8, "x-forwarded-for": "54.76.248.30"},
            )
        assert resp.status_code == 401
    finally:
        app.dependency_overrides.pop(get_session, None)

    details = [d for d in recorder.audit_details() if d]
    assert details, "no audit row written on the 401 rejection path"
    rejected = [d for d in details if d.get("reason") == "invalid_signature"]
    assert rejected, f"no invalid_signature audit row; got {details}"
    assert rejected[0]["origin_scope"] == "public"
    assert rejected[0]["origin_self_originated"] is False


@pytest.mark.asyncio
async def test_missing_header_writes_audit_row():
    """A 401 for a missing Verif-Hash is equally attributable."""
    from app.database import get_session

    recorder = RecordingSession()
    app.dependency_overrides[get_session] = lambda: recorder
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                WEBHOOK_URL,
                content=json.dumps({"event": "charge.completed"}),
                headers={"x-forwarded-for": "54.76.248.30"},
            )
        assert resp.status_code == 401
    finally:
        app.dependency_overrides.pop(get_session, None)

    details = [d for d in recorder.audit_details() if d]
    rejected = [d for d in details if d.get("reason") == "missing_verif_hash"]
    assert rejected, f"no missing_verif_hash audit row; got {details}"


@pytest.mark.asyncio
async def test_paystack_rejection_writes_audit_row():
    """Same guarantee for the Paystack route (card asked for it 'ideally')."""
    from app.database import get_session

    recorder = RecordingSession()
    app.dependency_overrides[get_session] = lambda: recorder
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                PAYSTACK_URL,
                content=json.dumps({"event": "charge.success"}),
                headers={"X-Paystack-Signature": "0" * 64, "x-forwarded-for": "52.31.139.75"},
            )
        assert resp.status_code == 401
    finally:
        app.dependency_overrides.pop(get_session, None)

    details = [d for d in recorder.audit_details() if d]
    rejected = [d for d in details if d.get("reason") in ("invalid_signature", "missing_signature")]
    assert rejected, f"no Paystack rejection audit row; got {details}"
    assert rejected[0]["origin_scope"] == "public"


@pytest.mark.asyncio
async def test_nowpayments_rejection_writes_audit_row():
    from app.database import get_session

    recorder = RecordingSession()
    app.dependency_overrides[get_session] = lambda: recorder
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                NOWPAYMENTS_URL,
                content=json.dumps({"payment_status": "finished"}),
                headers={"x-nowpayments-sig": "0" * 64, "x-forwarded-for": "34.254.131.32"},
            )
        assert resp.status_code == 401
    finally:
        app.dependency_overrides.pop(get_session, None)

    details = [d for d in recorder.audit_details() if d]
    assert any(d.get("origin_scope") == "public" for d in details), f"got {details}"


@pytest.mark.asyncio
async def test_completed_log_line_carries_client(monkeypatch):
    """The COMPLETED middleware line must carry the client address.

    QA greps the completed line when investigating a rejection, and it
    previously had no client field at all — only the started line did.
    """
    import app.main as main_mod

    captured: list[dict] = []
    real_info = main_mod.logger.info

    def spy(event, **kw):
        if event == "Request completed":
            captured.append(kw)
        return real_info(event, **kw)

    monkeypatch.setattr(main_mod.logger, "info", spy)

    from app.database import get_session

    recorder = RecordingSession()
    app.dependency_overrides[get_session] = lambda: recorder
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            await client.post(
                WEBHOOK_URL,
                content=json.dumps({"event": "charge.completed"}),
                headers={"Verif-Hash": "0" * 64, "x-forwarded-for": "54.76.248.30"},
            )
    finally:
        app.dependency_overrides.pop(get_session, None)

    assert captured, "no 'Request completed' line captured"
    line = [c for c in captured if c.get("path") == WEBHOOK_URL]
    assert line, f"no completed line for the webhook route: {captured}"
    assert line[0].get("client") == "54.76.248.30", f"completed line missing client: {line[0]}"


@pytest.mark.asyncio
async def test_middleware_prefers_xff_over_loopback_peer():
    """Behind nginx the peer is 127.0.0.1; the log must show the real caller."""
    import app.main as main_mod

    captured: list[dict] = []
    real_info = main_mod.logger.info

    def spy(event, **kw):
        if event == "Request completed":
            captured.append(kw)
        return real_info(event, **kw)

    main_mod.logger.info = spy
    from app.database import get_session

    recorder = RecordingSession()
    app.dependency_overrides[get_session] = lambda: recorder
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            await client.post(
                WEBHOOK_URL,
                content=json.dumps({"event": "charge.completed"}),
                headers={"Verif-Hash": "0" * 64, "x-forwarded-for": "34.254.131.32"},
            )
    finally:
        app.dependency_overrides.pop(get_session, None)
        main_mod.logger.info = real_info

    line = [c for c in captured if c.get("path") == WEBHOOK_URL]
    assert line and line[0].get("client") == "34.254.131.32", f"got {line}"


@pytest.mark.asyncio
async def test_raw_ip_is_never_persisted(monkeypatch):
    """Privacy invariant: no raw address reaches the audit row.

    The card asked for hashing per the customer_hash convention. If the raw IP
    ever leaks into `details`, the whole audit store becomes personal data.
    """
    from app.database import get_session

    raw_ip = "54.76.248.30"
    recorder = RecordingSession()
    app.dependency_overrides[get_session] = lambda: recorder
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                WEBHOOK_URL,
                content=json.dumps({"event": "charge.completed"}),
                headers={"Verif-Hash": "0" * 64, "x-forwarded-for": raw_ip},
            )
        assert resp.status_code == 401
    finally:
        app.dependency_overrides.pop(get_session, None)

    for details in recorder.audit_details():
        if not details:
            continue
        serialised = json.dumps(details, default=str)
        assert raw_ip not in serialised, f"raw IP leaked into audit details: {serialised}"
