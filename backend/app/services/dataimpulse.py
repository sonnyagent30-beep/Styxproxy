"""
DataImpulse proxy provider integration.

API docs: https://dataimpulse.com/api-docs
Purchase page: https://dataimpulse.com — $5 trial gives 5 GB residential.

Used by:
  - S1.2: Full provider abstraction (provider.py delegates to this)
  - S2.3: trial_delivery.py calls create_dataimpulse_trial_order()
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
class DataImpulseProxy:
    """A DataImpulse proxy order result."""

    order_id: str
    ip: str
    port: int
    username: str
    password: str
    protocol: str  # "http" | "socks5"
    expires_at: datetime
    country: str
    isp: str
    data_remaining_gb: float


# ─── HTTP Client ───────────────────────────────────────────────────────────────

def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(timeout=30.0)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _base_url() -> str:
    return "https://proxy.dataimpulse.com"


def _api_key() -> str:
    settings = get_settings()
    return settings.dataimpulse_api_key or ""


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {_api_key()}",
        "Content-Type": "application/json",
    }


# ─── Health & Balance ────────────────────────────────────────────────────────

async def check_health() -> bool:
    """Return True if DataImpulse API is reachable."""
    url = f"{_base_url()}/v1/account/balance"
    try:
        async with _client() as client:
            resp = await client.get(url, headers=_headers())
            return resp.status_code == 200
    except Exception:
        return False


async def check_balance() -> float:
    """Return current DataImpulse account balance in USD."""
    url = f"{_base_url()}/v1/account/balance"
    try:
        async with _client() as client:
            resp = await client.get(url, headers=_headers())
            if resp.status_code == 200:
                data = resp.json()
                return float(data.get("balance", data.get("balance_usd", 0)))
    except Exception:
        pass
    return 0.0


# ─── Trial order ──────────────────────────────────────────────────────────────

async def create_dataimpulse_trial_order(
    device_id: str,
    country: str = "Nigeria",
) -> dict[str, Any]:
    """
    Create a DataImpulse trial order ($5 trial plan).

    DataImpulse's trial gives 5 GB of residential proxies for 30 days.
    We use this for the TheoremReach → trial pipeline (S2.3).

    Returns a dict with keys:
      order_id, proxy_ip, proxy_port, username, password,
      protocol, expires_at, country, isp, data_remaining_gb

    Raises RuntimeError on failure.
    """
    url = f"{_base_url()}/v1/order/create"

    payload = {
        "country": country,
        "quantity": 1,
        "plan": "trial",  # DataImpulse trial plan identifier
        "port": 1080,  # default SOCKS5 port
        "login_type": "username_password",
        "format": "json",
        "reference_id": device_id,  # tracks which device this is for
    }

    async with _client() as client:
        resp = await client.post(url, json=payload, headers=_headers(), timeout=30.0)
        if resp.status_code not in (200, 201):
            raise RuntimeError(
                f"DataImpulse trial order failed: {resp.status_code} {resp.text}"
            )
        data = resp.json()

    # Normalize response to our dict shape
    return {
        "order_id": str(data.get("order_id", data.get("id", "unknown"))),
        "proxy_ip": data.get("proxy_ip", data.get("ip", "")),
        "proxy_port": int(data.get("proxy_port", data.get("port", 1080))),
        "username": data.get("username", ""),
        "password": data.get("password", ""),
        "protocol": data.get("protocol", "socks5"),
        "expires_at": (
            datetime.fromisoformat(data["expires_at"].replace("Z", "+00:00"))
            if data.get("expires_at")
            else datetime.now(timezone.utc) + timedelta(days=30)
        ),
        "country": data.get("country", country),
        "isp": data.get("isp", ""),
        "data_remaining_gb": float(data.get("data_remaining_gb", 5.0)),
    )


# ─── Paid order (S1.2) ───────────────────────────────────────────────────────

async def create_paid_order(
    country: str,
    proxy_type: str = "residential",  # residential | mobile | datacenter
    quantity: int = 1,
    plan_code: Optional[str] = None,
) -> DataImpulseProxy:
    """
    Create a paid DataImpulse order (used by provider.py in S1.2).

    proxy_type maps to DataImpulse product types:
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

    if plan_code:
        payload["plan"] = plan_code

    async with _client() as client:
        resp = await client.post(url, json=payload, headers=_headers(), timeout=30.0)
        if resp.status_code not in (200, 201):
            raise RuntimeError(
                f"DataImpulse paid order failed: {resp.status_code} {resp.text}"
            )
        data = resp.json()

    return DataImpulseProxy(
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
        isp=data.get("isp", ""),
        data_remaining_gb=float(data.get("data_remaining_gb", 0.0)),
    )
