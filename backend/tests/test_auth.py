"""Tests for auth module."""
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
    """Tests for DELETE /api/admin/auth/sessions/{session_id}."""

    def _make_client(self, monkeypatch):
        """Build an async httpx client for the revocation endpoint with a valid JWT."""
        from unittest.mock import AsyncMock
        from httpx import ASGITransport, AsyncClient
        from app.routers.auth import router
        from app.auth import create_access_token
        from datetime import timedelta

        admin_email = "admin@example.com"
        token = create_access_token(
            sub=admin_email,
            platform="admin",
            phone=admin_email,
            role="admin",
            expires_delta=timedelta(hours=1),
        )

        async def mock_get_session():
            yield AsyncMock()

        import app.routers.auth as auth_module
        monkeypatch.setattr(auth_module, "get_session", mock_get_session)

        return token, admin_email, ASGITransport(app=router)

    @pytest.mark.asyncio
    async def test_revoke_totp_session_not_found(self, monkeypatch):
        """Returns 404 when the session does not exist."""
        import uuid
        from unittest.mock import AsyncMock, MagicMock
        from httpx import ASGITransport, AsyncClient

        token, admin_email, transport = self._make_client(monkeypatch)

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        import app.routers.auth as auth_module
        from contextlib import asynccontextmanager

        @asynccontextmanager
        async def mock_get_session():
            yield mock_db

        monkeypatch.setattr(auth_module, "get_session", mock_get_session)

        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.delete(
                f"/api/admin/auth/sessions/{uuid.uuid4()}",
                headers={"Authorization": f"Bearer {token}"},
            )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_revoke_totp_session_forbidden_for_other_admin(self, monkeypatch):
        """Returns 403 when the session belongs to a different admin."""
        import uuid
        from unittest.mock import AsyncMock, MagicMock
        from httpx import ASGITransport, AsyncClient

        token, admin_email, transport = self._make_client(monkeypatch)

        mock_session_row = MagicMock()
        mock_session_row.admin_email = "other@example.com"
        mock_session_row.revoked_at = None

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_session_row
        mock_db.execute.return_value = mock_result

        import app.routers.auth as auth_module
        from contextlib import asynccontextmanager

        @asynccontextmanager
        async def mock_get_session():
            yield mock_db

        monkeypatch.setattr(auth_module, "get_session", mock_get_session)

        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.delete(
                f"/api/admin/auth/sessions/{uuid.uuid4()}",
                headers={"Authorization": f"Bearer {token}"},
            )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_revoke_totp_session_success(self, monkeypatch):
        """Sets revoked_at and returns 200 when session belongs to requesting admin."""
        import uuid
        from unittest.mock import AsyncMock, MagicMock
        from httpx import ASGITransport, AsyncClient

        token, admin_email, transport = self._make_client(monkeypatch)

        mock_session_row = MagicMock()
        mock_session_row.admin_email = admin_email
        mock_session_row.revoked_at = None
        mock_session_row.device_fingerprint = "fp_abc123"
        mock_session_row.ip_address = None

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_session_row
        mock_db.execute.return_value = mock_result
        mock_db.commit = AsyncMock()

        import app.routers.auth as auth_module
        monkeypatch.setattr(auth_module, "write_audit_log", AsyncMock())

        from contextlib import asynccontextmanager

        @asynccontextmanager
        async def mock_get_session():
            yield mock_db

        monkeypatch.setattr(auth_module, "get_session", mock_get_session)

        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.delete(
                f"/api/admin/auth/sessions/{uuid.uuid4()}",
                headers={"Authorization": f"Bearer {token}"},
            )
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Session revoked successfully"
        assert mock_session_row.revoked_at is not None
        mock_db.commit.assert_called_once()