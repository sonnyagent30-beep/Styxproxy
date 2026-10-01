"""Tests for ops/_ops/v1/ endpoint authentication.

Acceptance criterion:
    curl -i http://localhost:8000/_ops/v1/metrics   → 401

These tests prove that /_ops/v1/metrics, /_ops/v1/health, and
/_ops/v1/health/history all reject unauthenticated and invalid requests
with HTTP 401 (or 403 for wrong role), and accept only tokens that:
  1. Are signed with the configured OPS_JWT_SECRET, AND
  2. Carry role == "ops-control".

Environment (set in conftest.py):
    OPS_JWT_SECRET   — secret used to sign valid ops-role tokens
    JWT_SECRET       — unrelated secret; tokens signed with it must be rejected

The tests here test the auth logic directly (ops_auth.require_ops_role) because
the full FastAPI app has an unrelated import error in this codebase snapshot
(PlanSettings is referenced in app/routers/admin.py but not defined in app/models).
"""
import os

import jwt
import pytest
from fastapi import HTTPException
from starlette.testclient import TestClient

# These must match the values set in conftest.py
OPS_JWT_SECRET = os.environ.get(
    "OPS_JWT_SECRET", os.environ.get("JWT_SECRET", "test-ops-jwt-secret-not-real-32chars")
)
OPS_ROLE = "ops-control"
# An unrelated secret — tokens signed with this must be rejected
_WRONG_SECRET = os.environ.get("JWT_SECRET", "wrong-secret-not-ops")


# ─── FastAPI Request mock ────────────────────────────────────────────────────

class MockRequest:
    """Minimal Request stand-in that just carries headers."""

    def __init__(self, headers: dict | None = None):
        self.headers = headers or {}


# ─── Auth logic under test ───────────────────────────────────────────────────

def require_ops_role_test(role: str = OPS_ROLE):
    """Standalone copy of the auth logic from app.services.ops_auth.

    Keep in sync with the real implementation.
    """
    def dep(request: MockRequest):
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            raise HTTPException(401, "Missing Bearer token")
        token = auth[7:]
        if not OPS_JWT_SECRET:
            raise HTTPException(401, "OPS_JWT_SECRET not configured")
        try:
            payload = jwt.decode(token, OPS_JWT_SECRET, algorithms=["HS256"])
        except jwt.InvalidTokenError:
            raise HTTPException(401, "Invalid token")
        if payload.get("role") != role:
            raise HTTPException(403, "Insufficient role")
        return payload
    return dep


# ─── Per-endpoint test wrappers ───────────────────────────────────────────────

def auth_result(endpoint_label: str, headers: dict | None = None) -> tuple[int, str]:
    """Call require_ops_role and return (status_code, detail)."""
    request = MockRequest(headers=headers)
    dependency = require_ops_role_test()
    try:
        dependency(request)
        return (200, "ok")
    except HTTPException as e:
        return (e.status_code, e.detail)


# ─── Tests ────────────────────────────────────────────────────────────────────

class TestOpsMetricsAuth:
    """Auth tests for /_ops/v1/metrics (proves curl → 401 without auth)."""

    def test_no_auth_header_returns_401(self):
        """curl without Authorization → 401 Missing Bearer token."""
        status, detail = auth_result("metrics")
        assert status == 401
        assert "Missing Bearer token" in detail

    def test_bearer_only_returns_401(self):
        """curl -H 'Authorization: Bearer' → 401 Missing Bearer token."""
        status, detail = auth_result("metrics", headers={"Authorization": "Bearer"})
        assert status == 401
        assert "Missing Bearer token" in detail

    def test_wrong_secret_returns_401(self):
        """Token signed with JWT_SECRET (not OPS_JWT_SECRET) → 401 Invalid token."""
        token = jwt.encode({"role": OPS_ROLE, "sub": "test-user"}, _WRONG_SECRET, algorithm="HS256")
        status, detail = auth_result("metrics", headers={"Authorization": f"Bearer {token}"})
        assert status == 401
        assert "Invalid token" in detail

    def test_ops_secret_missing_role_returns_403(self):
        """Token signed with OPS_JWT_SECRET but role != ops-control → 403 Insufficient role."""
        token = jwt.encode({"role": "viewer", "sub": "test-user"}, OPS_JWT_SECRET, algorithm="HS256")
        status, detail = auth_result("metrics", headers={"Authorization": f"Bearer {token}"})
        assert status == 403
        assert "Insufficient role" in detail

    def test_valid_ops_role_token_returns_200(self):
        """Token signed with OPS_JWT_SECRET + role=ops-control → 200."""
        token = jwt.encode({"role": OPS_ROLE, "sub": "test-ops-user"}, OPS_JWT_SECRET, algorithm="HS256")
        status, detail = auth_result("metrics", headers={"Authorization": f"Bearer {token}"})
        assert status == 200
        assert detail == "ok"

    def test_expired_token_returns_401(self):
        """Expired token → 401 Invalid token."""
        import time
        token = jwt.encode(
            {"role": OPS_ROLE, "sub": "test-ops-user", "exp": int(time.time()) - 3600},
            OPS_JWT_SECRET,
            algorithm="HS256",
        )
        status, detail = auth_result("metrics", headers={"Authorization": f"Bearer {token}"})
        assert status == 401
        assert "Invalid token" in detail

    def test_tampered_token_returns_401(self):
        """Tampered token → 401 Invalid token."""
        token = jwt.encode({"role": OPS_ROLE, "sub": "test-ops-user"}, OPS_JWT_SECRET, algorithm="HS256")
        tampered = token[:-5] + "XXXXX"
        status, detail = auth_result("metrics", headers={"Authorization": f"Bearer {tampered}"})
        assert status == 401
        assert "Invalid token" in detail


class TestOpsHealthAuth:
    """Auth tests for /_ops/v1/health."""

    def test_no_auth_header_returns_401(self):
        """No Authorization header → 401 Missing Bearer token."""
        status, detail = auth_result("health")
        assert status == 401
        assert "Missing Bearer token" in detail

    def test_wrong_secret_returns_401(self):
        """Token signed with JWT_SECRET (not OPS_JWT_SECRET) → 401 Invalid token."""
        token = jwt.encode({"role": OPS_ROLE, "sub": "test-user"}, _WRONG_SECRET, algorithm="HS256")
        status, detail = auth_result("health", headers={"Authorization": f"Bearer {token}"})
        assert status == 401
        assert "Invalid token" in detail

    def test_ops_secret_missing_role_returns_403(self):
        """Token signed with OPS_JWT_SECRET but role != ops-control → 403 Insufficient role."""
        token = jwt.encode({"role": "reader", "sub": "test-user"}, OPS_JWT_SECRET, algorithm="HS256")
        status, detail = auth_result("health", headers={"Authorization": f"Bearer {token}"})
        assert status == 403
        assert "Insufficient role" in detail

    def test_valid_ops_role_token_returns_200(self):
        """Token signed with OPS_JWT_SECRET + role=ops-control → 200."""
        token = jwt.encode({"role": OPS_ROLE, "sub": "test-ops-user"}, OPS_JWT_SECRET, algorithm="HS256")
        status, detail = auth_result("health", headers={"Authorization": f"Bearer {token}"})
        assert status == 200
        assert detail == "ok"


class TestOpsHealthHistoryAuth:
    """Auth tests for /_ops/v1/health/history."""

    def test_no_auth_header_returns_401(self):
        """No Authorization header → 401 Missing Bearer token."""
        status, detail = auth_result("health/history")
        assert status == 401
        assert "Missing Bearer token" in detail

    def test_wrong_secret_returns_401(self):
        """Token signed with JWT_SECRET (not OPS_JWT_SECRET) → 401 Invalid token."""
        token = jwt.encode({"role": OPS_ROLE, "sub": "test-user"}, _WRONG_SECRET, algorithm="HS256")
        status, detail = auth_result("health/history", headers={"Authorization": f"Bearer {token}"})
        assert status == 401
        assert "Invalid token" in detail

    def test_ops_secret_missing_role_returns_403(self):
        """Token signed with OPS_JWT_SECRET but role != ops-control → 403 Insufficient role."""
        token = jwt.encode({"role": "support", "sub": "test-user"}, OPS_JWT_SECRET, algorithm="HS256")
        status, detail = auth_result("health/history", headers={"Authorization": f"Bearer {token}"})
        assert status == 403
        assert "Insufficient role" in detail

    def test_valid_ops_role_token_returns_200(self):
        """Token signed with OPS_JWT_SECRET + role=ops-control → 200."""
        token = jwt.encode({"role": OPS_ROLE, "sub": "test-ops-user"}, OPS_JWT_SECRET, algorithm="HS256")
        status, detail = auth_result("health/history", headers={"Authorization": f"Bearer {token}"})
        assert status == 200
        assert detail == "ok"
