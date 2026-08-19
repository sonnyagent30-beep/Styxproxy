"""
Decodo proxy provider integration (formerly Smartproxy).

API docs: https://decodo.com/api-docs
Sign up: https://decodo.com
Pricing: $2/GB at scale, $3.75/GB small, city/ZIP targeting.

Used by:
  - S2.8: Secondary provider for Nigeria city-level targeting (Lagos, Abuja)
  - provider.py routes Nigeria → Decodo; all other countries → DataImpulse
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)


# ─── Dataclasses (mirrors provider.py ProviderProxy) ─────────────────────────

@dataclass
class DecodoProxy:
    """A Decodo proxy order result."""

    order_id: str
    ip: str
    port: int
    username: str
    password: str
    protocol: str  # "http" | "socks5"
    expires_at: datetime
    country: str
    city: Optional[str] = None  # e.g. "Lagos", "Abuja"
    isp: str = ""
    asn: str = ""
    data_remaining_gb: float = 0.0


# ─── HTTP Client ───────────────────────────────────────────────────────────────

def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(timeout=30.0)


# ─── Settings helpers ───────────────────────────────────────────────────────────

def _base_url() -> str:
    return "https://proxy.decodo.com"


def _api_key() -> str:
    settings = get_settings()
    return settings.decodo_api_key or ""


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {_api_key()}",
        "Content-Type": "application/json",
    }


# ─── Health & Balance ──────────────────────────────────────────────────────────

async def check_health() -> bool:
    """Return True if Decodo API is reachable."""
    url = f"{_base_url()}/v1/account/balance"
    try:
        async with _client() as client:
            resp = await client.get(url, headers=_headers())
            return resp.status_code == 200
    except Exception:
        return False


async def check_balance() -> float:
    """Return current Decodo account balance in USD."""
    url = f"{_base_url()}/v1/account/balance"
    try:
        async with _client() as client:
            resp = await client.get(url, headers=_headers())
            if resp.status_code == 200:
                data = resp.json()
                # Decodo returns balance in USD directly
                return float(data.get("balance", data.get("balance_usd", 0)))
    except Exception:
        pass
    return 0.0


# ─── Order creation ───────────────────────────────────────────────────────────

async def create_order(
    country: str,
    city: Optional[str] = None,
    proxy_type: str = "residential",  # residential | mobile | datacenter
    quantity: int = 1,
    plan_code: Optional[str] = None,
) -> DecodoProxy:
    """
    Create a paid Decodo order.

    Decodo supports city-level targeting — pass city="Lagos" or city="Abuja"
    for Nigeria city targeting (S2.8 primary use case).

    proxy_type maps to Decodo product types:
      - "residential" → Residential proxy pool
      - "mobile"      → Mobile 4G proxies
      - "datacenter"  → Datacenter proxies
    """
    url = f"{_base_url()}/v1/order/create"

    payload: dict[str, Any] = {
        "country": country,
        "quantity": quantity,
        "type": proxy_type,
        "port": 1080,
        "login_type": "username_password",
        "format": "json",
    }

    # City-level targeting — Decodo's key differentiator for Nigeria
    if city:
        payload["city"] = city

    if plan_code:
        payload["plan"] = plan_code

    async with _client() as client:
        resp = await client.post(url, json=payload, headers=_headers(), timeout=30.0)
        if resp.status_code not in (200, 201):
            raise RuntimeError(f"Decodo order failed: {resp.status_code} {resp.text}")
        data = resp.json()

    return DecodoProxy(
        order_id=str(data.get("order_id", data.get("id", "unknown"))),
        ip=data.get("proxy_ip", data.get("ip", "")),
        port=int(data.get("proxy_port", data.get("port", 1080))),
        username=data.get("username", ""),
        password=data.get("password", ""),
        protocol=data.get("protocol", "socks5"),
        expires_at=(
            datetime.fromisoformat(data["expires_at"].replace("Z", "+00:00"))
            if data.get("expires_at")
            else datetime.now(timezone.utc) + timedelta(days=30)
        ),
        country=data.get("country", country),
        city=city or data.get("city"),
        isp=data.get("isp", ""),
        asn=data.get("asn", ""),
        data_remaining_gb=float(data.get("data_remaining_gb", 0.0)),
    )


async def rotate_ip(order_id: str) -> DecodoProxy:
    """
    Request a new IP for an existing Decodo order (admin-triggered rotation).

    Decodo API: POST /v1/order/{order_id}/rotate
    """
    url = f"{_base_url()}/v1/order/{order_id}/rotate"

    async with _client() as client:
        resp = await client.post(url, headers=_headers(), timeout=15.0)
        if resp.status_code not in (200, 201):
            raise RuntimeError(f"Decodo IP rotation failed: {resp.status_code} {resp.text}")
        data = resp.json()

    return DecodoProxy(
        order_id=order_id,
        ip=data.get("proxy_ip", data.get("ip", "")),
        port=int(data.get("proxy_port", data.get("port", 1080))),
        username=data.get("username", ""),
        password=data.get("password", ""),
        protocol=data.get("protocol", "socks5"),
        expires_at=(
            datetime.fromisoformat(data["expires_at"].replace("Z", "+00:00"))
            if data.get("expires_at")
            else datetime.now(timezone.utc) + timedelta(days=30)
        ),
        country=data.get("country", ""),
        city=data.get("city"),
        isp=data.get("isp", ""),
        asn=data.get("asn", ""),
        data_remaining_gb=float(data.get("data_remaining_gb", 0.0)),
    )
