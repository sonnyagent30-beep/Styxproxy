"""Tests for webhooks router."""
import hashlib, hmac, json, pytest
from unittest.mock import AsyncMock, MagicMock
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.database import get_session
from app.services.flutterwave import verify_flutterwave_signature


def make_flutterwave_signature(payload: bytes, secret: str) -> str:
    return hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()


class MockSession:
    def __init__(self, scalar_one_or_none=None):
        self._scalar_one_or_none = scalar_one_or_none

    async def execute(self, stmt):
        return MagicMock(scalar_one_or_none=MagicMock(return_value=self._scalar_one_or_none))

    async def commit(self):
        pass


@pytest.fixture
def webhook_payload():
    return {
        "event": "charge.completed",
        "data": {
            "id": 12345,
            "tx_ref": "TXF-ABCD1234",
            "status": "successful",
            "amount": 5000,
        }
    }


@pytest.mark.asyncio
async def test_flutterwave_webhook_rejects_invalid_signature(webhook_payload):
    """When Verif-Hash is present but wrong, returns 401."""
    payload_bytes = json.dumps(webhook_payload).encode()
    app.dependency_overrides.clear()
    app.dependency_overrides[get_session] = lambda: MockSession()
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/webhooks/flutterwave",
                content=payload_bytes,
                headers={"Verif-Hash": "invalid_sig"}
            )
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 401
