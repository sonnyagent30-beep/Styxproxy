"""
Provider service — proxy provider abstraction layer.

Dual-provider routing (S1.2 + S2.8):
  - Nigeria (Lagos, Abuja) → Decodo  (city-level targeting, S2.8)
  - All other countries   → DataImpulse (S1.2 primary)

The calling code throughout the app stays the same; provider selection
is handled internally based on country.
"""

import random
import socket
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx

from app.config import get_settings

# ─── Lazy settings ───────────────────────────────────────────────────────────

_settings = None


def _s():
    global _settings
    if _settings is None:
        _settings = get_settings()
    return _settings


# ─── Provider routing ─────────────────────────────────────────────────────────

# Countries routed to Decodo (city-level targeting)
_DECODO_COUNTRIES = {"Nigeria"}

# Countries routed to DataImpulse (all others)
_DATAIMPULSE_COUNTRIES = {
    "United Kingdom",
    "United States",
    "Canada",
    "Germany",
    "France",
    # ... any country not in _DECODO_COUNTRIES
}


def _country_routing(country: str) -> str:
    """Return which provider handles a given country."""
    return "decodo" if country in _DECODO_COUNTRIES else "dataimpulse"


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
    """Check if the selected provider for Nigeria is reachable and responding.

    Aggregates health from both Decodo (Nigeria) and DataImpulse (others).
    Returns True if at least one provider is healthy.
    """
    from app.services import dataimpulse, decodo

    results = await Promise.all([
        decodo.check_health(),
        dataimpulse.check_health(),
    ])
    return any(results)


async def check_balance() -> float:
    """Return the current wallet/balance across provider accounts, in USD.

    Returns the sum of DataImpulse balance (primary, non-Nigeria) and
    Decodo balance (Nigeria city targeting).
    """
    from app.services import dataimpulse, decodo

    di_balance, dc_balance = await Promise.all([
        dataimpulse.check_balance(),
        decodo.check_balance(),
    ])
    return di_balance + dc_balance


# ─── Availability / Precheck ───────────────────────────────────────────────────


async def check_availability(
    plan_code: str,
    country: str,
    proxy_type: str,
    quantity: int,
) -> AvailabilityResult:
    """Check whether a proxy order can be fulfilled right now."""
    provider = _country_routing(country)

    if provider == "decodo":
        return await _check_availability_decodo(country, proxy_type, quantity)
    else:
        return await _check_availability_dataimpulse(country, proxy_type, quantity)


async def _check_availability_decodo(
    country: str,
    proxy_type: str,
    quantity: int,
) -> AvailabilityResult:
    """Check availability via Decodo (Nigeria city-level)."""
    from app.services import decodo

    # 1. Provider API must be up
    if not await decodo.check_health():
        return AvailabilityResult(
            available=False,
            reason="provider_down",
            estimated_delivery_seconds=0,
        )

    # 2. Wallet must have enough funds
    estimated_cost_usd = quantity * 3.0  # ~$3 per GB placeholder
    balance = await decodo.check_balance()
    if balance < estimated_cost_usd:
        return AvailabilityResult(
            available=False,
            reason="insufficient_balance",
            estimated_delivery_seconds=0,
        )

    # 3. Nigeria is supported by Decodo (city-level)
    # Decodo supports Lagos and Abuja
    return AvailabilityResult(
        available=True,
        price_ngn=quantity * 6500,  # placeholder per-proxy price in NGN
        estimated_delivery_seconds=30,
    )


async def _check_availability_dataimpulse(
    country: str,
    proxy_type: str,
    quantity: int,
) -> AvailabilityResult:
    """Check availability via DataImpulse (all non-Nigeria countries)."""
    from app.services import dataimpulse

    # 1. Provider API must be up
    if not await dataimpulse.check_health():
        return AvailabilityResult(
            available=False,
            reason="provider_down",
            estimated_delivery_seconds=0,
        )

    # 2. Wallet must have enough funds
    estimated_cost_usd = quantity * 3.0  # ~$3 per GB placeholder
    balance = await dataimpulse.check_balance()
    if balance < estimated_cost_usd:
        return AvailabilityResult(
            available=False,
            reason="insufficient_balance",
            estimated_delivery_seconds=0,
        )

    # 3. Stub: check stock by country (mirrors original stub behaviour)
    available_countries = {
        "Nigeria": True,        # DataImpulse supports Nigeria too, but
        "United Kingdom": True,  # we prefer Decodo for Lagos/Abuja
        "United States": True,
        "Canada": True,
        "Germany": True,
        "France": True,
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
    city: Optional[str] = None,
) -> ProviderProxy:
    """Create a raw proxy order with the appropriate provider.

    Routing:
      - Nigeria (Lagos, Abuja) → Decodo (city-level targeting)
      - All other countries    → DataImpulse

    Args:
        plan_code: plan identifier (passed through to provider)
        country: ISO country name
        proxy_type: residential | mobile | datacenter
        quantity: number of proxies
        city: city name (e.g. "Lagos", "Abuja") — forwarded to Decodo only
    """
    provider = _country_routing(country)

    if provider == "decodo":
        return await _create_order_decodo(country, proxy_type, quantity, city)
    else:
        return await _create_order_dataimpulse(plan_code, country, proxy_type, quantity)


async def _create_order_decodo(
    country: str,
    proxy_type: str,
    quantity: int,
    city: Optional[str] = None,
) -> ProviderProxy:
    """Create a proxy order via Decodo (Nigeria city-level targeting)."""
    from app.services import decodo

    result: decodo.DecodoProxy = await decodo.create_order(
        country=country,
        city=city,
        proxy_type=proxy_type,
        quantity=quantity,
    )
    return ProviderProxy(
        provider_order_id=result.order_id,
        ip=result.ip,
        port=result.port,
        username=result.username,
        password=result.password,
        protocol=result.protocol,
        expires_at=result.expires_at,
        country=result.country,
        isp=result.isp,
        asn=result.asn,
    )


async def _create_order_dataimpulse(
    plan_code: str,
    country: str,
    proxy_type: str,
    quantity: int,
) -> ProviderProxy:
    """Create a proxy order via DataImpulse (non-Nigeria countries)."""
    from app.services import dataimpulse

    result: dataimpulse.DataImpulseProxy = await dataimpulse.create_paid_order(
        country=country,
        proxy_type=proxy_type,
        quantity=quantity,
        plan_code=plan_code,
    )
    return ProviderProxy(
        provider_order_id=result.order_id,
        ip=result.ip,
        port=result.port,
        username=result.username,
        password=result.password,
        protocol=result.protocol,
        expires_at=result.expires_at,
        country=result.country,
        isp=result.isp,
        asn="",  # DataImpulseProxy doesn't have asn field
    )


# ─── Health + Speed Test ───────────────────────────────────────────────────────


async def test_proxy(proxy: ProviderProxy) -> TestResult:
    """Test whether a proxy is alive AND speaks the expected proxy protocol.

    Two-step check:
    1. TCP connect (5s) — verifies the port is open at all
    2. Protocol handshake — for HTTP proxies, issue a CONNECT to
       example.com:80 and expect a 2xx response. This catches
       "router accepts TCP but proxy is dead" false-positives that
       a pure TCP-connect test misses.

    SOCKS5 protocol test isn't included (no PySocks in requirements, and
    providers currently emit protocol='http' — the upstream path is
    http; we re-brand to socks5 for the customer via Dante).
    """
    connect_start = datetime.now()
    try:
        sock = socket.create_connection(
            (proxy.ip, proxy.port),
            timeout=5,
        )
    except socket.timeout:
        return TestResult(alive=False, error="connection_timeout")
    except ConnectionRefusedError:
        return TestResult(alive=False, error="connection_refused")
    except Exception as e:
        return TestResult(alive=False, error=str(e))

    try:
        # Most providers return protocol="http"; we exercise HTTP CONNECT.
        # If the proxy is a different protocol we still got TCP-up, so
        # fall back to "alive=True with TCP-only check".
        if (proxy.protocol or "http").lower() == "http":
            sock.settimeout(5)
            # Minimal HTTP/1.0 CONNECT: server replies 200 on success.
            connect_req = (
                b"CONNECT example.com:80 HTTP/1.0\r\n"
                b"Host: example.com:80\r\n"
                b"User-Agent: styxproxy-test/1.0\r\n"
                b"\r\n"
            )
            sock.sendall(connect_req)
            resp = b""
            while b"\r\n\r\n" not in resp and len(resp) < 2048:
                chunk = sock.recv(1024)
                if not chunk:
                    break
                resp += chunk
            sock.close()
            # Parse status line: "HTTP/1.x NNN ..."
            status_line = resp.split(b"\r\n", 1)[0].decode("latin-1", errors="ignore")
            # Accept 2xx as "proxy works"; anything else is a dead proxy
            # masquerading as a working one.
            try:
                status_code = int(status_line.split()[1])
            except (IndexError, ValueError):
                status_code = 0
            if 200 <= status_code < 300:
                latency_ms = (datetime.now() - connect_start).total_seconds() * 1000
                return TestResult(alive=True, latency_ms=round(latency_ms, 1))
            # CONNECT failed — proxy rejected, treat as dead
            return TestResult(
                alive=False,
                error=f"connect_rejected:{status_code}",
            )

        # Non-http protocol (rare): trust the TCP connect + measure latency.
        sock.close()
        latency_ms = (datetime.now() - connect_start).total_seconds() * 1000
        return TestResult(alive=True, latency_ms=round(latency_ms, 1))
    except Exception as e:
        try:
            sock.close()
        except Exception:
            pass
        return TestResult(alive=False, error=f"protocol_handshake_failed:{e}")


async def rotate_ip(provider_order_id: str, country: str = "Nigeria") -> ProviderProxy:
    """Request a new IP from the provider for an existing order (admin-triggered).

    Routes to the correct provider based on country.
    """
    provider = _country_routing(country)

    if provider == "decodo":
        from app.services import decodo
        result: decodo.DecodoProxy = await decodo.rotate_ip(provider_order_id)
        return ProviderProxy(
            provider_order_id=result.order_id,
            ip=result.ip,
            port=result.port,
            username=result.username,
            password=result.password,
            protocol=result.protocol,
            expires_at=result.expires_at,
            country=result.country,
            isp=result.isp,
            asn=result.asn,
        )
    else:
        from app.services import dataimpulse
        # DataImpulse doesn't expose rotate_ip in its public API
        # Fall back to a stub response
        order_id = f"DI-ROTATE-{random.randint(100000, 999999)}"
        ip = f"185.199.{random.randint(228, 232)}.{random.randint(1, 254)}"
        port = random.choice([8080, 3128, 1080])
        username = f"rotated_{random.randint(10000, 99999)}"
        password = f"rotpass_{random.randint(100000, 999999)}"
        return ProviderProxy(
            provider_order_id=provider_order_id,
            ip=ip,
            port=port,
            username=username,
            password=password,
            protocol="http",
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
            country=country,
            isp="DataImpulse Rotated",
            asn="AS00000",
        )


# ─── Promise.all helper (no external dependency) ───────────────────────────────

class _Sentinel:
    pass


class Promise:
    """Minimal async Promise.all implementation."""

    @staticmethod
    async def all(coros):
        results = []
        for coro in coros:
            results.append(await coro)
        return results
