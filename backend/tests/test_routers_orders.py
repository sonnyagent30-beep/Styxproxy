"""Tests for orders router."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.database import get_session
from app.auth import get_current_account


def auth_header():
    return {"Authorization": "Bearer test_token_ignored"}


class MockCustomer:
    id = 1
    phone = "+2348012345678"
    blocked = False


class MockPlatformAccount:
    id = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
    customer_id = 1


class MockSession:
    def __init__(self, scalar_one_or_none=None, scalars_all=None):
        self._scalar_one_or_none = scalar_one_or_none
        self._scalars_all = scalars_all or []
        # Recorded rather than dropped, so a test can assert that a rejected
        # request persisted nothing.
        self.added = []

    async def execute(self, stmt, params=None):
        # `params` is not optional: resolve_plan()'s final fallback query is a
        # text() statement with bound params (app/routers/orders.py), so this
        # mock must accept the second positional argument or every test that
        # drives resolve_plan() to that branch dies with a TypeError.
        #
        # mappings() must answer too — that branch reads cpt_result.mappings()
        # .first() to build a _VirtualPlan. Returning None means "no catalog
        # row", which is what an unknown plan code should look like.
        result = MagicMock(
            scalar_one_or_none=MagicMock(return_value=self._scalar_one_or_none),
            scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=self._scalars_all))),
        )
        result.mappings.return_value.first.return_value = None
        return result

    def add(self, obj):
        self.added.append(obj)

    async def commit(self):
        pass

    async def refresh(self, obj):
        pass


async def mock_get_current_account():
    """Bypasses JWT decode and DB lookup — returns mock account directly."""
    return {"customer": MockCustomer(), "platform_account": MockPlatformAccount()}


@pytest.mark.asyncio
async def test_create_order_requires_auth():
    app.dependency_overrides.clear()
    app.dependency_overrides[get_session] = lambda: MockSession()
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/api/orders/create", json={
                "plan_code": "ISP-NG-1", "country": "NG", "quantity": 1
            })
    finally:
        app.dependency_overrides.clear()
    # Without auth override, returns 401/422 from JWT decode failure
    assert response.status_code in (401, 422)


@pytest.mark.asyncio
async def test_create_order_invalid_plan_code():
    """An unknown plan_code must be rejected with 400, never created.

    Load-bearing: mutation-proven to be the only test in the suite that fails
    when `create_order` stops rejecting an unresolvable plan. While it was red
    on a stale assertion, that coverage was silently gone.
    """
    session = MockSession()
    app.dependency_overrides.clear()
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[get_current_account] = mock_get_current_account
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/orders/create",
                json={"plan_code": "INVALID-PLAN", "country": "NG", "quantity": 1},
                headers=auth_header()
            )
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 400
    # The message names the offending code and country so the storefront can
    # tell the customer which selection was wrong.
    detail = response.json()["detail"]
    assert "INVALID-PLAN" in detail
    assert "NG" in detail
    # Nothing may be persisted on the rejected path.
    assert session.added == []


@pytest.mark.asyncio
async def test_cancel_order_not_found():
    session = MockSession(scalar_one_or_none=None)
    app.dependency_overrides.clear()
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[get_current_account] = mock_get_current_account
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/orders/ORD-NOTFOUND/cancel",
                json={"reason": "Changed mind"},
                headers=auth_header()
            )
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_report_dead_ip_order_not_active():
    order = MagicMock()
    order.order_id = "ORD-TEST01"
    order.status = "pending"  # not active

    session = MockSession(scalar_one_or_none=order)
    app.dependency_overrides.clear()
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[get_current_account] = mock_get_current_account
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/orders/ORD-TEST01/report-dead",
                json={"screenshot_url": "http://x.com/s.png", "issue_description": "banned"},
                headers=auth_header()
            )
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 400
    assert "not active" in response.json()["detail"]
