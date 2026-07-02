"""Tests for services."""
import pytest
import hashlib, hmac
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.flutterwave import verify_flutterwave_signature
from app.services.credential import generate_bun_username, generate_temp_password, get_available_proxy
from app.services.trial import check_trial_limit
from app.services.audit import log_audit_event
from datetime import datetime, timedelta


# ─── Flutterwave ───────────────────────────────────────────────
class TestVerifyFlutterwaveSignature:
    def test_valid_signature(self):
        payload = b'{"event":"charge.completed"}'
        secret = "my_webhook_secret"
        sig = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
        assert verify_flutterwave_signature(payload, sig, secret) is True

    def test_invalid_signature(self):
        payload = b'{"event":"charge.completed"}'
        assert verify_flutterwave_signature(payload, "wrong_sig", "secret") is False

    def test_tampered_payload(self):
        payload = b'{"event":"charge.completed"}'
        secret = "my_webhook_secret"
        sig = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
        tampered = b'{"event":"charge.failed"}'
        assert verify_flutterwave_signature(tampered, sig, secret) is False


# ─── Credential ──────────────────────────────────────────────────
class TestGenerateBunUsername:
    def test_format(self):
        username = generate_bun_username("+2348012345678", "ORD-123456")
        assert username.startswith("bun_")
        assert len(username) >= 10  # bun_ + 4 phone digits + 6 random = 11+ chars

    def test_phone_suffix(self):
        # Random suffix is inserted between phone suffix and random chars
        username = generate_bun_username("+2348012345678", "ORD-ABCDEF")
        assert "5678" in username  # last 4 digits of phone appear in username

    def test_randomness(self):
        u1 = generate_bun_username("+2348012345678", "ORD-111111")
        u2 = generate_bun_username("+2348012345678", "ORD-222222")
        assert u1 != u2  # different order IDs give different suffixes


class TestGenerateTempPassword:
    def test_length(self):
        pwd = generate_temp_password()
        assert len(pwd) == 16

    def test_characters(self):
        pwd = generate_temp_password()
        assert pwd.isalnum()  # letters and digits only

    def test_randomness(self):
        p1 = generate_temp_password()
        p2 = generate_temp_password()
        assert p1 != p2


class TestGetAvailableProxy:
    def test_known_country(self):
        proxy = get_available_proxy("NG")
        assert "ip" in proxy
        assert "port" in proxy

    def test_unknown_country_fallback(self):
        proxy = get_available_proxy("XX")
        assert "ip" in proxy
        assert "port" in proxy


# ─── Trial ──────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_check_trial_limit_under_limit():
    session = AsyncMock()
    session.execute.return_value = MagicMock(scalar=MagicMock(return_value=2))
    result = await check_trial_limit(session, "+2348012345678")
    assert result is True  # 2 < 3


@pytest.mark.asyncio
async def test_check_trial_limit_at_limit():
    session = AsyncMock()
    session.execute.return_value = MagicMock(scalar=MagicMock(return_value=3))
    result = await check_trial_limit(session, "+2348012345678")
    assert result is False  # 3 == 3, at limit


# ─── Audit ──────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_log_audit_event_with_session():
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    await log_audit_event(session, event_type="test_event", phone="+2348012345678", details={"key": "value"})
    session.add.assert_called_once()
    session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_log_audit_event_no_session():
    await log_audit_event(None, event_type="test_event", phone="+2348012345678")
    # Should not raise — returns early when db_session is None


@pytest.mark.asyncio
async def test_log_audit_event_hashes_phone():
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    await log_audit_event(session, event_type="test_event", phone="+2348012345678")
    call_args = session.add.call_args[0][0]
    assert call_args.customer_hash is not None
    expected_hash = hashlib.sha256("+2348012345678".encode()).hexdigest()[:20]
    assert call_args.customer_hash == expected_hash
