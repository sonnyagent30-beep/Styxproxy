"""Tests for payments router.

A note on the two auth-shaped tests below, because the naming is deceptive:
both endpoints are NOT equally unauthenticated, and neither test asserts an
auth requirement.

`POST /api/payments/initiate` has no `get_current_account` dependency, by
design. Guest checkout is deliberate — commit 48d8b780 ("No signup required"),
`customer_email` is optional and `device_id` supplies a stable identity when
neither is given. Adding auth here would break the revenue path, so
`test_initiate_payment_allows_anonymous_checkout` pins the guarantee that
actually holds: a well-formed anonymous request reaches the business logic.

`GET /api/orders/{order_id}/status` DOES require auth — it returns live SOCKS5
credentials, so it must. It used to live at `/api/payments/{id}/status`, which
is why an older version of the second test was failing on a 404 rather than on
the security property it was written to check.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.database import get_session
from app.auth import get_current_account


def auth_header():
    return {"Authorization": "Bearer test_token_ignored"}


class MockCustomer:
    phone = "+234****5678"


class MockPlatformAccount:
    id = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
    customer_id = 1


class MockSession:
    pass


class RecordingSession:
    """A session that records every statement it is asked to execute.

    Used to prove a request reached the business logic rather than being turned
    away at an auth boundary: if the handler never touches the DB, the endpoint
    rejected the request before doing any work.
    """

    def __init__(self):
        self.executed = []
        self.added = []

    async def execute(self, stmt, params=None):
        self.executed.append(stmt)
        result = MagicMock()
        # No checkout kill switch, no matching plan, no existing idempotent
        # order — every lookup misses, which is what an empty test DB looks
        # like.
        result.scalar_one_or_none.return_value = None
        result.mappings.return_value.first.return_value = None
        return result

    def add(self, obj):
        self.added.append(obj)

    async def commit(self):
        pass

    async def rollback(self):
        pass


async def mock_get_current_account():
    return {"customer": MockCustomer(), "platform_account": MockPlatformAccount()}


@pytest.mark.asyncio
async def test_initiate_payment_allows_anonymous_checkout():
    """A well-formed anonymous initiate reaches the business logic.

    Pinned deliberately rather than as a leftover: anonymous checkout is a
    shipped feature (commit 48d8b780), so the risk here runs the other way — a
    future "security" change that quietly adds auth to this endpoint would
    break every guest checkout in production. This test is what makes that
    regression loud instead of silent.

    Asserts the request was NOT rejected for missing auth (401/422) and that
    the handler actually ran: with an empty catalog the plan lookup misses and
    the endpoint answers 400 "Invalid plan code", a business-logic verdict.
    """
    session = RecordingSession()
    app.dependency_overrides.clear()
    app.dependency_overrides[get_session] = lambda: session
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/payments/initiate",
                json={
                    "plan_code": "ISP-NG-1",
                    "quantity": 1,
                    "customer_email": "guest@example.com",
                },
            )
    finally:
        app.dependency_overrides.clear()

    # Not an auth rejection. A missing/absent token must not produce these.
    assert response.status_code not in (401, 403), response.text
    assert response.status_code != 422, response.text

    # It reached business logic: the handler queried the DB (kill switch, plan
    # resolution) and returned a plan-verdict, not an auth verdict.
    assert len(session.executed) > 0, "handler never touched the DB — it rejected before doing any work"
    assert response.status_code == 400
    assert "plan" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_initiate_payment_still_validates_the_request_body():
    """Anonymous does not mean unvalidated: a malformed body is still a 422.

    The companion to the test above. Without it, "not 401" could be satisfied by
    an endpoint that accepted anything.
    """
    session = RecordingSession()
    app.dependency_overrides.clear()
    app.dependency_overrides[get_session] = lambda: session
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/payments/initiate",
                json={"quantity": 1},  # plan_code is required
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_payment_status_requires_auth():
    """GET /api/orders/{order_id}/status must reject an unauthenticated caller.

    This endpoint returns live SOCKS5 credentials once an order is active, so
    the 401 is a real security property — not a formality. Note the path: the
    endpoint moved from /api/payments/{order_id}/status to
    /api/orders/{order_id}/status (app/routers/payment_status.py). Hitting the
    old path returns 404 for ANY caller, which made an earlier version of this
    test "pass" or fail for the wrong reason; asserting on the real route is
    what makes it meaningful.
    """
    app.dependency_overrides.clear()
    app.dependency_overrides[get_session] = lambda: MockSession()
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/orders/TXF-123/status")
    finally:
        app.dependency_overrides.clear()
    assert response.status_code in (401, 422)


@pytest.mark.asyncio
async def test_legacy_payments_status_path_is_gone():
    """The pre-move /api/payments/{id}/status path must not resurrect.

    It is unauthenticated-adjacent dead surface: a route that 404s today could
    be reintroduced without anyone noticing. Pin that it stays a 404.
    """
    app.dependency_overrides.clear()
    app.dependency_overrides[get_session] = lambda: MockSession()
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/payments/TXF-123/status")
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 404