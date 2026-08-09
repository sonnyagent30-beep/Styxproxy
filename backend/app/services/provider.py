"""
Provider service — proxy provider abstraction layer.

This module provides a clean interface for interacting with proxy providers.
For now, returns realistic stub data so the rest of the system can develop
against a known contract. When real providers are chosen, swap the
implementation here — the calling code throughout the app stays the same.
"""

from __future__ import annotations

import asyncio
import logging
import random
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx

# ── Lazy settings ─────────────────────────────────────────────────────────────

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


# ── Exceptions ────────────────────────────────────────────────────────────────

class IPQBlockedError(Exception):
    """Raised when a provider proxy IP fails IPQS quality screening.

    Caught in the call chain and treated as a soft provider error —
    the order pipeline retries with a new proxy (up to 5 retries total).
    """

    pass


# ── Dataclasses ───────────────────────────────────────────────────────────────

@dataclass
class ProviderProxy:
    """A raw proxy from the provider — before branding."""

    ip: str
    port: int
    username: str
    password: str
    country: str
    protocol: str
    provider_order_id: str
    expires_at: datetime | None = None


@dataclass
class AvailabilityResult:
    available: bool
    reason: str | None = None
    price_ngn: int | None = None
    estimated_delivery_seconds: int | None = None


@dataclass
class TestResult:
    alive: bool
    latency_ms: float | None = None
    error: str | None = None


# ── Circuit breaker per country ─────────────────────────────────────────────────
#
# Tracks consecutive failures per country. When threshold is hit, that country
# is "tripped" for a cooldown period — no orders attempted during cooldown.
# Success resets the counter.
#
# Why per-country: one country's provider cluster can be down while others work.
# We don't want to block all orders — only orders for the dead country.

CIRCUIT_TRIP_AFTER = 3          # consecutive failures before tripping
CIRCUIT_COOLDOWN_SECONDS = 600  # 10 minutes before retry
MAX_RETRIES_PER_ORDER = 5


class CountryCircuitBreaker:
    """Per-country circuit breaker for provider orders.

    States:
      - CLOSED: normal operation, orders go through
      - OPEN: circuit tripped, orders for this country fail fast
      - HALF_OPEN: cooldown expired, allow one test order through
    """

    __slots__ = ("_failures", "_tripped_at", "_state")

    def __init__(self) -> None:
        self._failures: dict[str, int] = {}
        self._tripped_at: dict[str, float] = {}
        self._state: dict[str, str] = {}  # country -> "closed" | "open" | "half_open"

    def state(self, country: str) -> str:
        """Return current state: closed | open | half_open."""
        state = self._state.get(country, "closed")
        if state == "open":
            # Check if cooldown expired
            if self._tripped_at.get(country, 0) + CIRCUIT_COOLDOWN_SECONDS < time.time():
                self._state[country] = "half_open"
                return "half_open"
        return self._state.get(country, "closed")

    def record_success(self, country: str) -> None:
        """Reset failure counter on success."""
        self._failures[country] = 0
        self._state[country] = "closed"

    def record_failure(self, country: str) -> None:
        """Increment failure counter; trip circuit if threshold reached."""
        self._failures[country] = self._failures.get(country, 0) + 1
        if self._failures[country] >= CIRCUIT_TRIP_AFTER:
            self._tripped_at[country] = time.time()
            self._state[country] = "open"
            logging.warning(
                f"Circuit breaker TRIPPED for country={country} "
                f"after {self._failures[country]} consecutive failures. "
                f"Cooldown: {CIRCUIT_COOLDOWN_SECONDS}s"
            )

    def is_available(self, country: str) -> bool:
        """Return True if orders can be attempted for this country."""
        return self.state(country) != "open"

    def stats(self) -> dict:
        """Return human-readable stats for admin dashboard."""
        return {
            country: {
                "failures": self._failures.get(country, 0),
                "state": self.state(country),
                "tripped_at": (
                    datetime.fromtimestamp(self._tripped_at[country], tz=timezone.utc).isoformat()
                    if country in self._tripped_at else None
                ),
            }
            for country in set(list(self._failures) + list(self._state))
        }


# Global circuit breaker instance (lives for the process lifetime)
_circuit_breaker: CountryCircuitBreaker | None = None


def get_circuit_breaker() -> CountryCircuitBreaker:
    global _circuit_breaker
    if _circuit_breaker is None:
        _circuit_breaker = CountryCircuitBreaker()
    return _circuit_breaker


# ── Provider health ────────────────────────────────────────────────────────────

async def check_health() -> bool:
    """Return True if the provider API is reachable."""
    try:
        url = f"{_PROXY_SELLER_BASE_URL()}/v1.0/health"
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(url)
            return resp.status_code == 200
    except Exception:
        return False


async def check_balance() -> float:
    """Return the current wallet/balance on the provider account, in USD."""
    try:
        url = f"{_PROXY_SELLER_BASE_URL()}/v1.0/wallet"
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                url,
                headers={"X-API-Key": _PROXY_SELLER_API_KEY()},
            )
            if resp.status_code == 200:
                data = resp.json()
                return float(data.get("balance_usd", 0))
            return 0.0
    except Exception:
        return 0.0


# ── Availability check (with circuit breaker) ───────────────────────────────────

STUB_COUNTRIES = {
    "Nigeria": True,
    "United Kingdom": True,
    "United States": True,
    "Canada": True,
    "Germany": True,
    "France": True,
}


async def check_availability(
    plan_code: str,
    country: str,
    proxy_type: str,
    quantity: int,
) -> AvailabilityResult:
    """Check whether a proxy order can be fulfilled right now."""

    # 0. Circuit breaker: fail fast if country is tripped
    cb = get_circuit_breaker()
    if not cb.is_available(country):
        return AvailabilityResult(
            available=False,
            reason="country_degraded",
            estimated_delivery_seconds=0,
        )

    # 1. Provider API must be up
    if not await check_health():
        cb.record_failure(country)
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

    # 3. Check country availability (stub — real impl would call provider API)
    available_countries = STUB_COUNTRIES
    if not available_countries.get(country, False):
        cb.record_failure(country)
        return AvailabilityResult(
            available=False,
            reason="country_unavailable",
            estimated_delivery_seconds=0,
        )

    cb.record_success(country)

    # Estimate price in NGN
    price_ngn = quantity * 6500  # placeholder per-proxy price
    return AvailabilityResult(
        available=True,
        price_ngn=price_ngn,
        estimated_delivery_seconds=30,
    )


# ─── Order Creation ─────────────────────────────────────────────────────────────


async def create_order(
    plan_code: str,
    country: str,
    proxy_type: str,
    quantity: int,
    _retry_count: int = 0,
) -> ProviderProxy:
    """Create a raw proxy order with the provider.

    On failure, records the failure in the circuit breaker and re-raises.
    The caller (order pipeline) handles retries up to MAX_RETRIES_PER_ORDER.
    """
    url = f"{_PROXY_SELLER_BASE_URL()}/v1.0/order/create"
    cb = get_circuit_breaker()

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                url,
                headers={"X-API-Key": _PROXY_SELLER_API_KEY()},
                json={
                    "country": country,
                    "type": proxy_type,
                    "quantity": quantity,
                    "duration_days": 30,
                    "format": "username_password",
                },
            )

            if resp.status_code not in (200, 201):
                cb.record_failure(country)
                raise RuntimeError(f"Provider order failed: {resp.status_code} {resp.text}")

            data = resp.json()

    except httpx.TimeoutException:
        cb.record_failure(country)
        raise RuntimeError(f"Provider order timed out for country={country}")

    except httpx.ConnectError as e:
        cb.record_failure(country)
        raise RuntimeError(f"Provider connection error: {e}")

    cb.record_success(country)

    ip = data.get("ip", f"10.{random.randint(1,254)}.{random.randint(1,254)}.{random.randint(1,254)}")
    port = data.get("port", 8000)
    order_id = str(data.get("order_id", data.get("id", "stub_order")))

    return ProviderProxy(
        ip=ip,
        port=port,
        username=data.get("username", f"user_{order_id}"),
        password=data.get("password", f"pass_{order_id}"),
        country=country,
        protocol="http",
        provider_order_id=order_id,
    )


# ─── Stubs (unchanged — used when no real provider) ──────────────────────────

async def _stub_proxy(country: str, quantity: int, order_id: str) -> list[ProviderProxy]:
    """Return stub proxies when provider is not wired."""
    proxies = []
    for i in range(quantity):
        ip = f"10.{random.randint(1,254)}.{random.randint(1,254)}.{i + 1}"
        proxies.append(
            ProviderProxy(
                ip=ip,
                port=8000,
                username=f"user_{order_id}_{i}",
                password=f"pass_{order_id}_{i}",
                country=country,
                protocol="http",
                provider_order_id=order_id,
            )
        )
    return proxies


# ─── IPQS screening (unchanged) ───────────────────────────────────────────────

async def _screen_with_ipqs(proxy: ProviderProxy) -> None:
    from app.services.ip_quality import screen_ip

    try:
        iq = await screen_ip(proxy.ip)
        if iq.fail_reason:
            raise IPQBlockedError(
                f"IP {proxy.ip} failed IPQS quality screening: {iq.fail_reason}"
            )
    except Exception as e:
        if "IPQBlockedError" in type(e).__name__:
            raise
        # Non-IPQ error — log and continue (don't block on screening failure)
        logging.warning(f"IPQS screening error for {proxy.ip}: {e}")


# ─── Proxy health test (unchanged) ─────────────────────────────────────────────

async def test_proxy(proxy: ProviderProxy) -> TestResult:
    """Check if a proxy is alive and responsive.

    Uses TCP connect timing — does not go through Dante (which routes via the
    proxy). This catches "router accepts TCP but proxy is dead" false-positives
    that the Dante test misses.
    """
    host = proxy.ip
    port = proxy.port

    # Most providers return protocol="http"; we exercise HTTP CONNECT.
    # For SOCKS proxies the test is different — extend when needed.
    start = time.monotonic()
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port),
            timeout=5.0,
        )
        latency_ms = (time.monotonic() - start) * 1000
        writer.close()
        await writer.wait_closed()

        # Try a simple HTTP CONNECT to confirm it's a proxy, not a black hole
        try:
            import socket

            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            sock.connect((host, port))
            sock.sendall(b"CONNECT google.com:443 HTTP/1.0\r\n\r\n")
            resp = sock.recv(64)
            sock.close()
            if b"200" not in resp and b"connected" not in resp.lower():
                return TestResult(alive=False, error="proxy_rejected_connect")
        except Exception:
            pass  # Fall through to TCP success

        return TestResult(alive=True, latency_ms=latency_ms)

    except asyncio.TimeoutError:
        return TestResult(alive=False, error="timeout")
    except ConnectionRefusedError:
        return TestResult(alive=False, error="connection_refused")
    except OSError as e:
        # "No route to host", "Network unreachable", etc.
        return TestResult(alive=False, error=f"network_error:{e.strerror or e.errno}")
    except Exception as e:
        return TestResult(alive=False, error=f"unknown:{e}")


async def rotate_ip(provider_order_id: str) -> ProviderProxy:
    """Request a new IP from the provider for an existing order (admin-triggered)."""
    url = f"{_PROXY_SELLER_BASE_URL()}/v1.0/order/{provider_order_id}/rotate"

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                url,
                headers={"X-API-Key": _PROXY_SELLER_API_KEY()},
            )
            if resp.status_code not in (200, 201):
                raise RuntimeError(f"Provider rotate failed: {resp.status_code} {resp.text}")
            data = resp.json()
    except Exception:
        # Stub — real provider rotation not wired
        return ProviderProxy(
            ip=f"10.{random.randint(1,254)}.{random.randint(1,254)}.1",
            port=8000,
            username=f"rotated_{provider_order_id}",
            password=f"rotated_{provider_order_id}",
            country="",
            protocol="http",
            provider_order_id=provider_order_id,
        )

    return ProviderProxy(
        ip=data.get("ip", "0.0.0.0"),
        port=data.get("port", 8000),
        username=data.get("username", ""),
        password=data.get("password", ""),
        country=data.get("country", ""),
        protocol=data.get("protocol", "http"),
        provider_order_id=provider_order_id,
    )
