"""Tests for health router."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.database import get_session


class MockSession:
    def __init__(self):
        self._scalar_result = 1
        self._exception = None

    async def execute(self, *args, **kwargs):
        if self._exception:
            raise self._exception
        return MagicMock(scalar=MagicMock(return_value=self._scalar_result))


@pytest.mark.asyncio
async def test_health_check_success():
    mock_session = MockSession()
    app.dependency_overrides[get_session] = lambda: mock_session
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/health")
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["database"] == "connected"
    assert "version" in data
    assert "timestamp" in data


@pytest.mark.asyncio
async def test_health_check_db_failure():
    mock_session = MockSession()
    mock_session._exception = Exception("DB connection failed")
    app.dependency_overrides[get_session] = lambda: mock_session
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/health")
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 200
    data = response.json()
    assert data["database"] == "disconnected"
