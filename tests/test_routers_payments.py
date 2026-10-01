"""Tests for payments router."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.database import get_session
from app.auth import get_current_account


def auth_header():
    return {"Authorization": "Bearer test_token_ignored"}


class MockCustomer:
    phone = "+2348012345678"


class MockPlatformAccount:
    id = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
    customer_id = 1


class MockSession:
    pass


async def mock_get_current_account():
    return {"customer": MockCustomer(), "platform_account": MockPlatformAccount()}


@pytest.mark.asyncio
async def test_initiate_payment_requires_auth():
    app.dependency_overrides.clear()
    app.dependency_overrides[get_session] = lambda: MockSession()
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/payments/initiate",
                json={"plan_code": "ISP-NG-1", "quantity": 1},
            )
    finally:
        app.dependency_overrides.clear()
    assert response.status_code in (401, 422)


@pytest.mark.asyncio
async def test_get_payment_status_requires_auth():
    app.dependency_overrides.clear()
    app.dependency_overrides[get_session] = lambda: MockSession()
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/payments/TXF-123/status")
    finally:
        app.dependency_overrides.clear()
    assert response.status_code in (401, 422)
