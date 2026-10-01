"""Tests for auth module."""
import importlib
import pytest
from unittest.mock import patch, MagicMock
from datetime import timedelta
from fastapi import HTTPException
from app.auth import (
    verify_password,
    get_password_hash,
    create_access_token,
    decode_access_token,
    verify_admin_token,
    JWTBearer,
)


class TestVerifyPassword:
    def test_verify_password_correct(self):
        hashed = get_password_hash("correct-password")
        assert verify_password("correct-password", hashed) is True

    def test_verify_password_wrong(self):
        hashed = get_password_hash("correct-password")
        assert verify_password("wrong-password", hashed) is False


class TestGetPasswordHash:
    def test_hash_different_from_plain(self):
        hashed = get_password_hash("my-password")
        assert hashed != "my-password"

    def test_hash_is_string(self):
        hashed = get_password_hash("test")
        assert isinstance(hashed, str)

    def test_hash_uniqueness(self):
        h1 = get_password_hash("same")
        h2 = get_password_hash("same")
        assert h1 != h2


class TestCreateAccessToken:
    def test_create_access_token_default_expiry(self):
        token = create_access_token(sub="user123", platform="whatsapp", phone="+2348012345678")
        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_access_token_custom_expiry(self):
        token = create_access_token(
            sub="user123",
            platform="whatsapp",
            phone="+2348012345678",
            expires_delta=timedelta(hours=2),
        )
        assert isinstance(token, str)
        payload = decode_access_token(token)
        assert payload["sub"] == "user123"

    def test_create_access_token_payload_fields(self):
        token = create_access_token(sub="user123", platform="whatsapp", phone="+2348012345678")
        payload = decode_access_token(token)
        assert payload["sub"] == "user123"
        assert payload["platform"] == "whatsapp"
        assert payload["phone"] == "+2348012345678"
        assert "exp" in payload
        assert "iat" in payload


class TestDecodeAccessToken:
    def test_decode_valid_token(self):
        token = create_access_token(sub="user123", platform="whatsapp", phone="+2348012345678")
        payload = decode_access_token(token)
        assert payload["sub"] == "user123"

    def test_decode_invalid_token_raises_401(self):
        with pytest.raises(HTTPException) as exc_info:
            decode_access_token("invalid.token.here")
        assert exc_info.value.status_code == 401

    def test_decode_tampered_token_raises_401(self):
        token = create_access_token(sub="user123", platform="whatsapp", phone="+2348012345678")
        tampered = token[:-5] + "xxxxx"
        with pytest.raises(HTTPException) as exc_info:
            decode_access_token(tampered)
        assert exc_info.value.status_code == 401


class TestVerifyAdminToken:
    def test_valid_token(self):
        """verify_admin_token expects full 'Bearer <token>' format."""
        with patch("app.auth.settings") as mock_settings:
            mock_settings.admin_token = "secret-admin-token"
            result = verify_admin_token("Bearer secret-admin-token")
            assert result is True

    def test_wrong_token_raises_403(self):
        with patch("app.auth.settings") as mock_settings:
            mock_settings.admin_token = "secret-admin-token"
            with pytest.raises(HTTPException) as exc_info:
                verify_admin_token("Bearer wrong-token")
            assert exc_info.value.status_code == 403

    def test_missing_header_raises_401(self):
        with pytest.raises(HTTPException) as exc_info:
            verify_admin_token(None)
        assert exc_info.value.status_code == 401

    def test_empty_string_raises_401(self):
        with pytest.raises(HTTPException) as exc_info:
            verify_admin_token("")
        assert exc_info.value.status_code == 401

    def test_only_bearer_raises_401(self):
        with pytest.raises(HTTPException) as exc_info:
            verify_admin_token("Bearer")
        assert exc_info.value.status_code == 401


class TestJWTBearer:
    @pytest.mark.asyncio
    async def test_jwtbearer_returns_credentials(self):
        token = create_access_token(sub="user123", platform="whatsapp", phone="+2348012345678")
        bearer = JWTBearer()
        result = await bearer(credentials=MagicMock(scheme="Bearer", credentials=token))
        assert result.credentials == token

    @pytest.mark.asyncio
    async def test_jwtbearer_raises_401_when_absent(self):
        bearer = JWTBearer(auto_error=False)
        with pytest.raises(HTTPException) as exc_info:
            await bearer(credentials=None)
        assert exc_info.value.status_code == 401




class TestRevokeTOTPSession:
    """Tests for DELETE /api/admin/auth/sessions/{session_id}.

    These needed two repairs beyond the obvious `importlib` one, both found by
    running them:

    1. ``ASGITransport(app=router)`` cannot work. FastAPI's route handler reads
       ``request.scope["fastapi_middleware_astack"]``, which is only injected by
       the ``AsyncExitStackMiddleware`` that a *FastAPI application* installs. An
       ``APIRouter`` has no middleware stack, so every request died with
       ``AssertionError: fastapi_middleware_astack not found in request scope``.
       The app is what must be handed to the transport.

    2. ``monkeypatch.setattr(auth_module, "get_session", ...)`` never took effect
       even once the module resolved, because the router's dependencies were
       built at import time and already hold a reference to the real
       ``get_session``. FastAPI's supported seam is
       ``app.dependency_overrides[get_session]``. ``require_viewer`` needs the
       same treatment — it runs a DB query of its own, and letting it through
       reaches a live Postgres connection.
    """

    ADMIN_EMAIL = "admin@example.com"

    def _build(self, monkeypatch, totp_session):
        """Wire the app to mocks and return (token, admin_email, mock_db)."""
        from unittest.mock import AsyncMock, MagicMock
        from app.main import app
        from app.routers.auth import require_viewer
        from app.database import get_session
        from app.auth import create_access_token
        from datetime import timedelta

        auth_module = importlib.import_module("app.routers.auth")

        token = create_access_token(
            sub=self.ADMIN_EMAIL,
            platform="admin",
            phone=self.ADMIN_EMAIL,
            role="admin",
            expires_delta=timedelta(hours=1),
        )

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = totp_session
        mock_db.execute.return_value = mock_result

        async def mock_get_session():
            yield mock_db

        async def mock_require_viewer():
            return {
                "email": self.ADMIN_EMAIL,
                "role": "admin",
                "admin": MagicMock(),
            }

        app.dependency_overrides.clear()
        app.dependency_overrides[get_session] = mock_get_session
        app.dependency_overrides[require_viewer] = mock_require_viewer
        monkeypatch.setattr(auth_module, "write_audit_log", AsyncMock())

        return token, mock_db

    def _client(self, app):
        from httpx import ASGITransport, AsyncClient

        return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")

    @pytest.mark.asyncio
    async def test_revoke_totp_session_not_found(self, monkeypatch):
        """Returns 404 when the session does not exist."""
        import uuid
        from unittest.mock import MagicMock
        from app.main import app

        token, _ = self._build(monkeypatch, None)
        try:
            async with self._client(app) as client:
                response = await client.delete(
                    f"/api/admin/auth/sessions/{uuid.uuid4()}",
                    headers={"Authorization": f"Bearer {token}"},
                )
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 404
        assert response.json()["detail"] == "Session not found"

    @pytest.mark.asyncio
    async def test_revoke_totp_session_forbidden_for_other_admin(self, monkeypatch):
        """Returns 403 when the session belongs to a different admin."""
        import uuid
        from unittest.mock import MagicMock
        from app.main import app

        row = MagicMock()
        row.admin_email = "other@example.com"
        row.revoked_at = None

        token, _ = self._build(monkeypatch, row)
        try:
            async with self._client(app) as client:
                response = await client.delete(
                    f"/api/admin/auth/sessions/{uuid.uuid4()}",
                    headers={"Authorization": f"Bearer {token}"},
                )
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 403
        assert "does not belong to you" in response.json()["detail"]
        # Ownership must be enforced BEFORE the row is mutated, otherwise a
        # cross-admin revoke would still succeed in marking the row revoked.
        assert row.revoked_at is None

    @pytest.mark.asyncio
    async def test_revoke_totp_session_success(self, monkeypatch):
        """Sets revoked_at and returns 200 when session belongs to requesting admin."""
        import uuid
        from unittest.mock import MagicMock
        from app.main import app

        row = MagicMock()
        row.admin_email = self.ADMIN_EMAIL
        row.revoked_at = None
        row.device_fingerprint = "fp_abc123"
        row.ip_address = None

        token, mock_db = self._build(monkeypatch, row)
        try:
            async with self._client(app) as client:
                response = await client.delete(
                    f"/api/admin/auth/sessions/{uuid.uuid4()}",
                    headers={"Authorization": f"Bearer {token}"},
                )
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Session revoked successfully"
        assert row.revoked_at is not None
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_revoke_totp_session_invalid_uuid_is_400(self, monkeypatch):
        """A non-UUID session_id is a client error, not a 404 or a 500."""
        from unittest.mock import MagicMock
        from app.main import app

        token, _ = self._build(monkeypatch, MagicMock())
        try:
            async with self._client(app) as client:
                response = await client.delete(
                    "/api/admin/auth/sessions/not-a-uuid",
                    headers={"Authorization": f"Bearer {token}"},
                )
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 400
        assert response.json()["detail"] == "Invalid session ID"