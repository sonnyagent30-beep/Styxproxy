"""Tests for admin router."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.database import get_session
from app.auth import get_current_account


def admin_header():
    return {"Authorization": "Bearer admin_token_ignored"}


class MockCustomer:
    phone = "+2348012345678"


class MockPlatformAccount:
    id = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
    customer_id = 1


class MockSession:
    def __init__(self, scalar_result=0, scalars_result=None):
        self._scalar_result = scalar_result
        self._scalars_result = scalars_result or []

    async def execute(self, stmt):
        return MagicMock(
            scalar=MagicMock(return_value=self._scalar_result),
            scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=self._scalars_result)))
        )

    async def commit(self):
        pass


async def mock_get_current_account():
    return {"customer": MockCustomer(), "platform_account": MockPlatformAccount()}


@pytest.mark.asyncio
async def test_admin_health_requires_admin():
    app.dependency_overrides.clear()
    app.dependency_overrides[get_session] = lambda: MockSession()
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/admin/health")
    finally:
        app.dependency_overrides.clear()
    # admin_only checks the real JWT first, so invalid token → 401
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_admin_list_customers_requires_admin():
    app.dependency_overrides.clear()
    app.dependency_overrides[get_session] = lambda: MockSession()
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/admin/customers?page=1&limit=20")
    finally:
        app.dependency_overrides.clear()
    assert response.status_code in (401, 403)
