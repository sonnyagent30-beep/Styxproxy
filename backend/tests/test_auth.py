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
