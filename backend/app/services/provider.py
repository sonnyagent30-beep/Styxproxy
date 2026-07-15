"""
Provider service — proxy provider abstraction layer.

This module provides a clean interface for interacting with proxy providers.
For now, returns realistic stub data so the rest of the system can develop
against a known contract. When real providers are chosen, swap the
implementation here — the calling code throughout the app stays the same.
"""
import random
import socket
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Optional

import httpx


# ─── Lazy settings ───────────────────────────────────────────────────────────

_settings = None

def _s():
    global _settings
    if _settings is None:
        from app.config import get_settings
        _settings = get_settings()
    return _settings

def _PROXY_SELLER_API_KEY() -> str:
    return _s().proxy_seller_api_key or ""

def _PROXY_SELLER_BASE_URL() -> str:
    return _s().proxy_seller_base_url or "https://api.proxy-seller.com"


# ─── Dataclasses ─────────────────────────────────────────────────────────────

@dataclass
class ProviderProxy:
    """A raw proxy from the provider — before branding."""
    provider_order_id: str
    ip: str
    port: int
    username: str
    password: str
    protocol: str  # e.g. "http", "socks5"
    expires_at: datetime
    country: str
    isp: str
    asn: str


@dataclass
class AvailabilityResult:
    """Result of an availability / precheck call."""
    available: bool
    reason: Optional[str] = None
    price_ngn: Optional[float] = None
    estimated_delivery_seconds: int = 30


@dataclass
class TestResult:
    """Result of proxy health + speed test."""
    alive: bool
    latency_ms: Optional[float] = None
    error: Optional[str] = None


# ─── HTTP Client ───────────────────────────────────────────────────────────────

def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(timeout=10.0)


# ─── Health & Balance ─────────────────────────────────────────────────────────

async def check_health() -> bool:
    """Check if the provider API is reachable and responding."""
    url = f"{_PROXY_SELLER_BASE_URL()}/v1.0/health"
    try:
        async with _client() as client:
            resp = await client.get(
                url,
                headers={"X-API-KEY": _PROXY_SELLER_API_KEY()},
            )
            return resp.status_code == 200
    except Exception:
        return False


async def check_balance() -> float:
    """Return the current wallet/balance on the provider account, in USD."""
    url = f"{_PROXY_SELLER_BASE_URL()}/v1.0/balance"
    try:
        async with _client() as client:
            resp = await client.get(
                url,
                headers={"X-API-KEY": _PROXY_SELLER_API_KEY()},
            )
            if resp.status_code == 200:
                data = resp.json()
                return float(data.get("balance", data.get("balance_usd", 0)))
    except Exception:
        pass
    return 0.0


# ─── Availability / Precheck ───────────────────────────────────────────────────

async def check_availability(
    plan_code: str,
    country: str,
    proxy_type: str,
    quantity: int,
) -> AvailabilityResult:
    """Check whether a proxy order can be fulfilled right now."""
    # 1. Provider API must be up
    if not await check_health():
        return AvailabilityResult(
            available=False,
            reason="provider_down",
            estimated_delivery_seconds=0,
        )

    # 2. Wallet must have enough funds
    estimated_cost_usd = quantity * 3.0  # ~$3 per proxy placeholder
    balance = await check_balance()
    if balance < estimated_cost_usd:
        return AvailabilityResult(
            available=False,
            reason="insufficient_balance",
            estimated_delivery_seconds=0,
        )

    # 3. Stub: check stock by country
    available_countries = {
        "Nigeria": True, "United Kingdom": True, "United States": True,
        "Canada": True, "Germany": True, "France": True,
    }
    if not available_countries.get(country, False):
        return AvailabilityResult(
            available=False,
            reason="country_unavailable",
            estimated_delivery_seconds=0,
        )

    # Estimate price in NGN
    price_ngn = quantity * 6500  # placeholder per-proxy price
    return AvailabilityResult(
        available=True,
        price_ngn=price_ngn,
        estimated_delivery_seconds=30,
    )


# ─── Order Creation ────────────────────────────────────────────────────────────

async def create_order(
    plan_code: str,
    country: str,
    proxy_type: str,
    quantity: int,
) -> ProviderProxy:
    """Create a raw proxy order with the provider."""
    url = f"{_PROXY_SELLER_BASE_URL()}/v1.0/order/create"

    payload = {
        "country": country,
        "type": proxy_type,
        "quantity": quantity,
        "duration_days": 30,
        "format": "username_password",
    }

    async with _client() as client:
        resp = await client.post(
            url,
            json=payload,
            headers={
                "X-API-KEY": _PROXY_SELLER_API_KEY(),
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )
        if resp.status_code not in (200, 201):
            raise RuntimeError(f"Provider order failed: {resp.status_code} {resp.text}")

        data = resp.json()

    ip = data.get("ip") or data.get("data", {}).get("ip", "")
    port = int(data.get("port") or data.get("data", {}).get("port", 8080))

    # Stub response — used when provider is not yet wired
    if not ip:
        order_id = f"STUB-{random.randint(100000, 999999)}"
        ip = f"185.199.{random.randint(228, 232)}.{random.randint(1, 254)}"
        port = random.choice([8080, 3128, 1080])
        username = f"raw_{random.randint(10000, 99999)}"
        password = f"rawpass_{random.randint(100000, 999999)}"
        expires_at = datetime.now(timezone.utc) + timedelta(days=30)
        return ProviderProxy(
            provider_order_id=order_id,
            ip=ip, port=port,
            username=username, password=password,
            protocol="http",
            expires_at=expires_at,
            country=country,
            isp="Stub ISP",
            asn="AS00000",
        )

    return ProviderProxy(
        provider_order_id=str(data.get("order_id", data.get("id", "unknown"))),
        ip=ip,
        port=port,
        username=data.get("username", ""),
        password=data.get("password", ""),
        protocol=data.get("protocol", "http"),
        expires_at=datetime.fromisoformat(data["expires_at"].replace("Z", "+00:00"))
            if data.get("expires_at")
            else datetime.now(timezone.utc) + timedelta(days=30),
        country=country,
        isp=data.get("isp", ""),
        asn=data.get("asn", ""),
    )


# ─── Health + Speed Test ───────────────────────────────────────────────────────

async def test_proxy(proxy: ProviderProxy) -> TestResult:
    """Test whether a proxy is alive and fast enough."""
    start = datetime.now()
    try:
        sock = socket.create_connection(
            (proxy.ip, proxy.port),
            timeout=5,
        )
        sock.close()
        latency_ms = (datetime.now() - start).total_seconds() * 1000
        return TestResult(alive=True, latency_ms=round(latency_ms, 1))
    except socket.timeout:
        return TestResult(alive=False, error="connection_timeout")
    except ConnectionRefusedError:
        return TestResult(alive=False, error="connection_refused")
    except Exception as e:
        return TestResult(alive=False, error=str(e))


async def rotate_ip(provider_order_id: str) -> ProviderProxy:
    """Request a new IP from the provider for an existing order (admin-triggered)."""
    url = f"{_PROXY_SELLER_BASE_URL()}/v1.0/order/{provider_order_id}/rotate"

    async with _client() as client:
        resp = await client.post(
            url,
            headers={"X-API-KEY": _PROXY_SELLER_API_KEY()},
            timeout=15.0,
        )
        if resp.status_code not in (200, 201):
            raise RuntimeError(f"Provider rotate failed: {resp.status_code} {resp.text}")

        data = resp.json()

    ip = data.get("ip", "")
    if not ip:
        ip = f"185.199.{random.randint(228, 232)}.{random.randint(1, 254)}"

    return ProviderProxy(
        provider_order_id=provider_order_id,
        ip=ip,
        port=int(data.get("port", 8080)),
        username=data.get("username", ""),
        password=data.get("password", ""),
        protocol=data.get("protocol", "http"),
        expires_at=datetime.now(timezone.utc) + timedelta(days=30),
        country=data.get("country", ""),
        isp=data.get("isp", ""),
        asn=data.get("asn", ""),
    )
