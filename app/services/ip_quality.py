"""IPQualityScore integration — proxy IP screening.

Screens every proxy IP returned by the provider before it reaches the customer.
Free tier: 5,000 lookups/month, 250/day — plenty for Styxproxy volume.

Usage:
    from app.services.ip_quality import screen_ip

    result = await screen_ip("185.199.228.45")
    if not result.is_clean:
        raise IPQualityError(f"IP {ip} failed screening: {result.fail_reason}")
"""

import logging
import os
from dataclasses import dataclass
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

# ─── Settings lazy-load ───────────────────────────────────────────────────────

_settings: Optional["Settings"] = None

def _s():
    global _settings
    if _settings is None:
        from app.config import get_settings
        _settings = get_settings()
    return _settings


def _api_key() -> str:
    val = os.environ.get("IPQUALITYSCORE_API_KEY", "")
    if not val:
        val = _s().ipqualityscore_api_key or ""
    return val


# ─── Dataclasses ─────────────────────────────────────────────────────────────

@dataclass
class IPQResult:
    """Result of IPQS screening on a single proxy IP."""

    ip: str
    fraud_score: int  # 0-100; higher = worse
    is_proxy: bool
    is_vpn: bool
    is_tor: bool
    is_datacenter: bool
    recent_abuse: bool
    abuse_velocity: str  # "low", "medium", "high", "none"
    country_code: str
    city: str
    isp: str
    asn: str
    is_clean: bool  # True if IP passes Styxproxy quality gates
    fail_reason: Optional[str]  # Human-readable failure reason

    @classmethod
    def from_api_response(cls, ip: str, data: dict) -> "IPQResult":
        """Parse IPQS API response into IPQResult."""
        fraud_score = int(data.get("fraud_score", 0))
        is_proxy = bool(data.get("proxy", False))
        is_vpn = bool(data.get("vpn", False))
        is_tor = bool(data.get("tor", False))
        is_datacenter = bool(data.get("datacenter", False))
        recent_abuse = bool(data.get("recent_abuse", False))
        abuse_velocity = data.get("abuse_velocity", "none")
        country_code = data.get("country_code", "")
        city = data.get("city", "")
        isp = data.get(" ISP ", data.get("ISP", ""))
        asn = data.get("ASN", "")

        # ── Styxproxy quality gates ─────────────────────────────────────────
        #
        # Residential plans: reject datacenter IPs, open proxies, VPN exit nodes,
        #                    and IPs with fraud_score >= 75 or recent abuse.
        # ISP plans:         allow datacenter IPs (that's what ISP means here),
        #                    but still reject open proxies and high-fraud IPs.
        #
        # Tor is a soft reject (most Tor IPs are in datacenters anyway).
        #
        fail_reason: Optional[str] = None

        if fraud_score >= 85:
            fail_reason = f"fraud_score={fraud_score} (>= 85)"
        elif recent_abuse and fraud_score >= 50:
            fail_reason = f"recent_abuse=True with fraud_score={fraud_score}"
        elif is_proxy and not is_vpn:
            fail_reason = "open_proxy detected"
        elif is_vpn and fraud_score >= 75:
            fail_reason = f"vpn=True with fraud_score={fraud_score}"
        # Tor: warn but don't block (low volume, abuse rarely comes from Tor)
        elif is_tor:
            logger.warning(f"IP {ip}: Tor exit node (fraud_score={fraud_score})")
            fail_reason = None  # soft warn only

        is_clean = fail_reason is None

        return cls(
            ip=ip,
            fraud_score=fraud_score,
            is_proxy=is_proxy,
            is_vpn=is_vpn,
            is_tor=is_tor,
            is_datacenter=is_datacenter,
            recent_abuse=recent_abuse,
            abuse_velocity=abuse_velocity,
            country_code=country_code,
            city=city,
            isp=isp,
            asn=asn,
            is_clean=is_clean,
            fail_reason=fail_reason,
        )

    @classmethod
    def stub(cls, ip: str) -> "IPQResult":
        """Return a pass for environments without an IPQS key (e.g. tests)."""
        return cls(
            ip=ip,
            fraud_score=0,
            is_proxy=False,
            is_vpn=False,
            is_tor=False,
            is_datacenter=False,
            recent_abuse=False,
            abuse_velocity="none",
            country_code="",
            city="",
            isp="",
            asn="",
            is_clean=True,
            fail_reason=None,
        )


# ─── Screen a single IP ───────────────────────────────────────────────────────

SCORE_URL = "https://ipqualityscore.com/api/json/ip/{key}/{ip}"


async def screen_ip(ip: str) -> IPQResult:
    """Query IPQS for a single IP. Returns IPQResult.

    Raises:
        IPQualityError: on network/HTTP errors (caller should retry).
    """
    key = _api_key()

    # No key configured — pass all IPs (fail open for dev environments)
    if not key:
        logger.debug(f"IPQUALITYSCORE_API_KEY not set; skipping screening for {ip}")
        return IPQResult.stub(ip)

    # strictness=0 (light check), lighter_penalties=true (avoid false positives on free tier)
    params = {"strictness": "0", "allow_public_access": "true", "lighter_penalties": "true"}
    url = SCORE_URL.format(key=key, ip=ip)

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

            # Handle IPQS-level errors (success=false in response body)
            if not data.get("success", True):
                msg = data.get("message", "")
                if "unauthorized" in msg.lower() or "invalid" in msg.lower():
                    # Bad credentials — fail open, don't retry
                    logger.error(f"IPQS key invalid/unauthorized: {msg}. Check IPQUALITYSCORE_API_KEY.")
                    return IPQResult.stub(ip)
                elif "insufficient credits" in msg.lower():
                    logger.warning("IPQS out of credits. Screening skipped.")
                    return IPQResult.stub(ip)
                elif "rate limit" in msg.lower():
                    raise IPQualityError(f"IPQS rate limit hit (429); retry later for {ip}")
                else:
                    raise IPQualityError(f"IPQS error: {msg}")

    except httpx.TimeoutException:
        raise IPQualityError(f"IPQS timeout screening {ip}")
    except httpx.HTTPStatusError as e:
        raise IPQualityError(f"IPQS HTTP error {e.response.status_code} screening {ip}")
    except Exception as e:
        raise IPQualityError(f"IPQS unexpected error {type(e).__name__}: {e} screening {ip}")

    return IPQResult.from_api_response(ip, data)


class IPQualityError(Exception):
    """Raised when IPQS is unreachable or returns an unexpected error.

    Callers should RETRY (provider API is slow, or IPQS is down).
    Do NOT treat this as a hard rejection — retry the same IP or get a new one.
    """
    pass
