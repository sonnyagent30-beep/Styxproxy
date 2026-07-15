"""
Dante service — branding gateway on the VPS.

Dante acts as the auth layer between the customer and the upstream provider proxy.
- Customer authenticates to Dante with their bun_username / bun_password
- Dante routes the authenticated request to the upstream proxy (hidden from customer)
- We can rotate the customer's bun credentials without changing the upstream IP

This module provides a clean interface for registering and managing Dante credentials.
For now, returns realistic stub data so the rest of the system can develop
against a known contract. When Dante is deployed on the VPS, swap the
implementation here — the calling code throughout the app stays the same.

Dante API URL and key are configured via environment variables.
"""
import asyncio
import random
import string
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Optional

import httpx

from app.config import get_settings

_settings = None  # lazy singleton

# ─── Constants ────────────────────────────────────────────────────────────────

_DANTE_API_URL() = get_settings().dante_api_url or "http://localhost:9000"
_DANTE_API_KEY() = get_settings().dante_api_key or ""
_DANTE_DEFAULT_PORT() = get_settings().dante_default_port or 1080

ALPHANUM = string.ascii_lowercase + string.digits


# ─── Dataclasses ─────────────────────────────────────────────────────────────

@dataclass
class DanteCredential:
    """A branded credential registered on Dante."""
    bun_username: str
    bun_password: str
    upstream_ip: str
    upstream_port: int
    dante_port: int
    expires_at: datetime
    active: bool = True


@dataclass
class DanteRotateResult:
    """Result of rotating Dante credentials."""
    new_bun_username: str
    new_bun_password: str
    upstream_ip: str
    upstream_port: int
    dante_port: int
    expires_at: datetime


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _random_username(prefix: str = "bun", length: int = 8) -> str:
    suffix = "".join(random.choices(ALPHANUM, k=length))
    return f"{prefix}_{suffix}"


def _random_password(length: int = 16) -> str:
    chars = string.ascii_letters + string.digits + "!@#$%"
    return "".join(random.choices(chars, k=length))


def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(timeout=15.0)


# ─── Dante API ────────────────────────────────────────────────────────────────

async def _dante_post(path: str, payload: dict) -> dict:
    """Make an authenticated request to the Dante API."""
    url = f"{_DANTE_API_URL()}{path}"
    try:
        async with _client() as client:
            resp = await client.post(
                url,
                json=payload,
                headers={
                    "Authorization": f"Bearer {_DANTE_API_KEY()}",
                    "Content-Type": "application/json",
                },
            )
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        raise RuntimeError(f"Dante API error at {path}: {e}")


async def _dante_get(path: str) -> dict:
    """Make an authenticated GET request to the Dante API."""
    url = f"{_DANTE_API_URL()}{path}"
    try:
        async with _client() as client:
            resp = await client.get(
                url,
                headers={"Authorization": f"Bearer {_DANTE_API_KEY()}"},
            )
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        raise RuntimeError(f"Dante API error at {path}: {e}")


# ─── Credential Management ───────────────────────────────────────────────────

async def register_credential(
    upstream_ip: str,
    upstream_port: int,
    expires_at: datetime,
    duration_days: int = 30,
) -> DanteCredential:
    """
    Register a new branded credential on Dante.

    - Generates bun_username + bun_password
    - Registers them on Dante, pointing to the upstream proxy
    - Dante listens on a port and routes authenticated requests to upstream_ip:port

    Returns DanteCredential with the branded details.
    """
    bun_username = _random_username()
    bun_password = _random_password()

    payload = {
        "username": bun_username,
        "password": bun_password,
        "upstream_host": upstream_ip,
        "upstream_port": upstream_port,
        "expires_at": expires_at.isoformat(),
        "port": _DANTE_DEFAULT_PORT(),
    }

    try:
        await _dante_post("/api/credentials", payload)
    except RuntimeError:
        # Dante not yet deployed — stub response
        pass

    # Assign a random dante_port for the stub (in production, Dante returns this)
    dante_port = _DANTE_DEFAULT_PORT()

    return DanteCredential(
        bun_username=bun_username,
        bun_password=bun_password,
        upstream_ip=upstream_ip,
        upstream_port=upstream_port,
        dante_port=dante_port,
        expires_at=expires_at,
        active=True,
    )


async def rotate_credential(
    current_bun_username: str,
    upstream_ip: str,
    upstream_port: int,
    expires_at: datetime,
) -> DanteRotateResult:
    """
    Rotate the Dante credentials for a customer.

    - Generates NEW bun_username + bun_password
    - Re-registers on Dante, same upstream proxy (IP unchanged)
    - Invalidates the old credentials immediately
    - Customer keeps same upstream proxy IP

    This is the Dante-only rotation — NOT the provider IP rotation.
    """
    new_bun_username = _random_username()
    new_bun_password = _random_password()

    payload = {
        "old_username": current_bun_username,
        "username": new_bun_username,
        "password": new_bun_password,
        "upstream_host": upstream_ip,
        "upstream_port": upstream_port,
        "expires_at": expires_at.isoformat(),
        "port": _DANTE_DEFAULT_PORT(),
    }

    try:
        await _dante_post("/api/credentials/rotate", payload)
    except RuntimeError:
        # Dante not yet deployed — stub response
        pass

    return DanteRotateResult(
        new_bun_username=new_bun_username,
        new_bun_password=new_bun_password,
        upstream_ip=upstream_ip,
        upstream_port=upstream_port,
        dante_port=_DANTE_DEFAULT_PORT(),
        expires_at=expires_at,
    )


async def revoke_credential(bun_username: str) -> bool:
    """
    Revoke a credential on Dante — immediately invalidates it.
    Returns True if successful, False otherwise.
    """
    try:
        await _dante_post("/api/credentials/revoke", {"username": bun_username})
        return True
    except RuntimeError:
        return False


async def update_upstream_ip(
    bun_username: str,
    new_upstream_ip: str,
    new_upstream_port: int,
) -> bool:
    """
    Update the upstream proxy IP for an existing Dante credential.
    Used when admin approves a provider IP rotation.

    Customer's bun_username + bun_password remain the same;
    Dante now routes to the new upstream IP.
    """
    payload = {
        "username": bun_username,
        "upstream_host": new_upstream_ip,
        "upstream_port": new_upstream_port,
    }
    try:
        await _dante_post("/api/credentials/update-upstream", payload)
        return True
    except RuntimeError:
        return False


async def health_check() -> bool:
    """Check if Dante is reachable."""
    try:
        await _dante_get("/health")
        return True
    except RuntimeError:
        return False
