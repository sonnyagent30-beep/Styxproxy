"""IPQualityScore integration — proxy IP screening.

Screens every proxy IP returned by the provider before it reaches the customer.
Free tier: 5,000 lookups/month, 250/day — plenty for Styxproxy volume.

Usage:
    from app.services.ip_quality import screen_ip

    result = await screen_ip("185.199.228.45")
    if not result.is_clean:
        raise IPQualityError(f"IP {ip} failed screening: {result.fail_reason}")
"""

import ipaddress
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
    plan_type: str = "unknown"  # which rule set produced is_clean

    @classmethod
    def from_api_response(cls, ip: str, data: dict, plan_type: str = "unknown") -> "IPQResult":
        """Parse IPQS API response into IPQResult.

        `plan_type` selects the rule set. The gate is plan-aware because the
        four product lines are not interchangeable: a datacenter IP is a defect
        on a residential plan and the *entire point* of a datacenter plan.
        Applying one flat rule set to all four rejected 100% of DC and ISP
        proxies — see `_evaluate`.
        """
        fraud_score = int(data.get("fraud_score", 0))
        is_proxy = bool(data.get("proxy", False))
        is_vpn = bool(data.get("vpn", False))
        is_tor = bool(data.get("tor", False))
        # IPQS v3 does NOT return a `datacenter` boolean — it returns a
        # `connection_type` STRING. Reading `data.get("datacenter")` therefore
        # yielded None on every live lookup, so is_datacenter was ALWAYS False
        # and the per-plan datacenter rule never fired. That is the rule the
        # plan-aware gate was built around, so `allow_datacenter` was inert.
        #
        # The consequence is concrete: a residential plan would accept a
        # datacenter address — the exact defect the rule exists to catch — and a
        # DC/ISP plan would have been rejected for `vpn=True` instead of being
        # allowed as a datacenter product, which is what blocked DC/ISP.
        #
        # Read the string, and keep the legacy boolean as a fallback in case a
        # future API version restores it.
        _connection_type = str(data.get("connection_type") or "").strip().lower()
        is_datacenter = bool(data.get("datacenter", False)) or (
            "data center" in _connection_type or "datacenter" in _connection_type
        )
        recent_abuse = bool(data.get("recent_abuse", False))
        abuse_velocity = data.get("abuse_velocity", "none")
        country_code = data.get("country_code", "")
        city = data.get("city", "")
        isp = data.get(" ISP ", data.get("ISP", ""))
        asn = data.get("ASN", "")

        fail_reason = _evaluate(
            ip=ip,
            plan_type=plan_type,
            fraud_score=fraud_score,
            is_proxy=is_proxy,
            is_vpn=is_vpn,
            is_tor=is_tor,
            is_datacenter=is_datacenter,
            recent_abuse=recent_abuse,
        )

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
            plan_type=plan_type,
            fail_reason=fail_reason,
        )

    @classmethod
    def stub(cls, ip: str, plan_type: str = "unknown") -> "IPQResult":
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
            plan_type=plan_type,
            fail_reason=None,
        )


# ─── Plan-aware quality gates ─────────────────────────────────────────────────

#: Rule sets per product line. Values are (fraud_score_ceiling, allow_datacenter).
#:
#: `datacenter` and `isp` are *supposed* to be datacenter IPs — that is what the
#: customer is buying. A flat rule set that rejects `is_proxy`/`is_vpn` rejects
#: 100% of them, which is what happened: the gate was implemented without the
#: plan-awareness its own docstring described, so DC and ISP could never fulfil.
#:
#: `residential` and `mobile` must NOT be datacenter addresses; a residential
#: proxy that resolves to a hosting provider is a mis-sold product.
#:
#: The ceiling is a hard reject on reputation alone. It sits above the IPQS
#: "suspicious" band (75-84) on purpose: that band is routinely occupied by
#: legitimate shared hosting, and rejecting it would fail closed on good stock.
#: `recent_abuse` still rejects at >= 50 for every plan — that is the signal
#: that actually predicts abuse, and it is what the docstring called out.
_PLAN_RULES: dict[str, dict] = {
    "residential": {"ceiling": 85, "allow_datacenter": False},
    "mobile":      {"ceiling": 85, "allow_datacenter": False},
    "datacenter":  {"ceiling": 90, "allow_datacenter": True},
    "isp":         {"ceiling": 90, "allow_datacenter": True},
}
_DEFAULT_RULES = {"ceiling": 85, "allow_datacenter": False}

#: `recent_abuse` is a hard reject at or above this score, for every plan.
_RECENT_ABUSE_SCORE = 50


def _normalise_plan_type(plan_type: Optional[str]) -> str:
    """Map a plan type / plan code onto a rule-set key.

    Callers pass what they have — `plan_type` ('residential'), a plan code
    ('DC-US-3IP'), or nothing. Unknown values fall to the strict residential
    rule set so a new product line cannot silently inherit the permissive one.
    """
    raw = (plan_type or "").strip().lower()
    if not raw:
        return "unknown"
    for key in _PLAN_RULES:
        if raw == key or raw.startswith(key):
            return key
    # plan codes: DC-*, ISP-*, RESIDENTIAL-*, MOBILE-*
    if raw.startswith("dc"):
        return "datacenter"
    if raw.startswith("isp"):
        return "isp"
    if raw.startswith("res"):
        return "residential"
    if raw.startswith("mob"):
        return "mobile"
    return "unknown"


def _evaluate(
    *,
    ip: str,
    plan_type: Optional[str],
    fraud_score: int,
    is_proxy: bool,
    is_vpn: bool,
    is_tor: bool,
    is_datacenter: bool,
    recent_abuse: bool,
) -> Optional[str]:
    """Return a human-readable failure reason, or None if the IP is acceptable.

    Pure function so the rule set can be exercised without the IPQS API.
    """
    key = _normalise_plan_type(plan_type)
    rules = _PLAN_RULES.get(key, _DEFAULT_RULES)

    if fraud_score >= rules["ceiling"]:
        return f"fraud_score={fraud_score} (>= {rules['ceiling']} for {key})"

    if recent_abuse and fraud_score >= _RECENT_ABUSE_SCORE:
        return f"recent_abuse=True with fraud_score={fraud_score}"

    if is_datacenter and not rules["allow_datacenter"]:
        return f"datacenter IP on a {key} plan"

    # An open proxy on a non-datacenter plan is a defect regardless of VPN flag:
    # `is_proxy and not is_vpn` was the old test, but a VPN-flagged open proxy
    # slipped through it. Datacenter/ISP stock is legitimately proxy-flagged.
    if is_proxy and not rules["allow_datacenter"] and not is_vpn:
        return "open_proxy detected"

    if is_vpn and not rules["allow_datacenter"] and fraud_score >= 75:
        return f"vpn=True with fraud_score={fraud_score} on a {key} plan"

    if is_tor:
        # Soft warn only — low volume, abuse rarely originates from Tor.
        logger.warning("IP %s: Tor exit node (fraud_score=%d)", ip, fraud_score)

    return None


# ─── Screen a single IP ───────────────────────────────────────────────────────

SCORE_URL = "https://ipqualityscore.com/api/json/ip/{key}/{ip}"


async def screen_ip(ip: str, plan_type: Optional[str] = None) -> IPQResult:
    """Query IPQS for a single IP. Returns IPQResult.

    `plan_type` selects the rule set (residential / mobile / datacenter / isp).
    Omitting it applies the strict residential rules, so a caller that forgets
    cannot accidentally accept a datacenter IP on a residential plan.

    Raises:
        IPQualityError: on network/HTTP errors (caller should retry).
    """
    # ── Local format check BEFORE anything else ─────────────────────────────
    # A malformed value must NEVER reach the fail-open branch. Fail-open exists
    # for conditions outside our control (network, 5xx, rate limit, third-party
    # outage); a local data defect is OUR bug and is never a reason to accept
    # input. This exact case shipped: the simulator generated `192.0.2.58.144`
    # (five octets), IPQS answered "Invalid IPv4 address", that response fell
    # into fail-open, and every DC/ISP credential was accepted as
    # "screened clean" while carrying an address that routes nowhere.
    try:
        ipaddress.IPv4Address(ip)
    except (ipaddress.AddressValueError, ValueError, TypeError) as e:
        raise IPQualityError(
            f"refusing to screen {ip!r}: not a valid IPv4 address ({e}). "
            f"This is a local data defect, not a screening outage — failing CLOSED."
        ) from e

    key = _api_key()

    # No key configured — pass all IPs (fail open for dev environments)
    if not key:
        logger.debug(f"IPQUALITYSCORE_API_KEY not set; skipping screening for {ip}")
        return IPQResult.stub(ip, plan_type=plan_type or "unknown")

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

    return IPQResult.from_api_response(ip, data, plan_type=plan_type or "unknown")


class IPQualityError(Exception):
    """Raised when IPQS is unreachable or returns an unexpected error.

    Callers should RETRY (provider API is slow, or IPQS is down).
    Do NOT treat this as a hard rejection — retry the same IP or get a new one.
    """
    pass
