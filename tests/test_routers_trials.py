"""Tests for trials router."""
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
    def __init__(self, scalar_one_or_none=None):
        self._scalar_one_or_none = scalar_one_or_none

    async def execute(self, stmt):
        return MagicMock(scalar_one_or_none=MagicMock(return_value=self._scalar_one_or_none))


async def mock_get_current_account():
    return {"customer": MockCustomer(), "platform_account": MockPlatformAccount()}


@pytest.mark.asyncio
async def test_claim_trial_disclaimer_not_accepted():
    app.dependency_overrides.clear()
    app.dependency_overrides[get_session] = lambda: MockSession()
    app.dependency_overrides[get_current_account] = mock_get_current_account
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/trials/claim",
                json={"disclaimer_accepted": False},
                headers=auth_header()
            )
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 400
    assert "disclaimer" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_submit_survey_trial_not_found():
    app.dependency_overrides.clear()
    app.dependency_overrides[get_session] = lambda: MockSession()
    app.dependency_overrides[get_current_account] = mock_get_current_account
    try:
        with MagicMock() as mock_get_trial:
            mock_get_trial.return_value = None
            from app.services import trial
            original = trial.get_trial_by_id
            trial.get_trial_by_id = mock_get_trial
            try:
                transport = ASGITransport(app=app)
                async with AsyncClient(transport=transport, base_url="http://test") as client:
                    response = await client.post(
                        "/api/trials/99/survey",
                        json={"rating": 5, "feedback": "Great!", "would_recommend": True},
                        headers=auth_header()
                    )
            finally:
                trial.get_trial_by_id = original
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 404
