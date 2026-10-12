"""
Provider proxy testing service — Sprint 3.

Provides structured benchmarking of proxy quality across three dimensions:
Speed, Strength (AbuseIPDB reputation), and Quality (IPQualityScore fraud score).

Run from: backend/scripts/test_provider.py CLI runner,
or via: POST /api/admin/providers/test (wired in admin.py)
"""

import asyncio
import os
from dataclasses import dataclass
from typing import Optional

import httpx

from app.services.provider import ProviderProxy, TestResult, test_proxy

# ─── Settings helpers ────────────────────────────────────────────────────────────


def _get_setting(name: str) -> Optional[str]:
    """Return an env var value, or None if not set."""
    return os.environ.get(name) or None


ABUSEIPDB_KEY: Optional[str] = _get_setting("ABUSEIPDB_API_KEY")
IPQS_KEY: Optional[str] = _get_setting("IPQUALITYSCORE_API_KEY")

# ─── Dataclasses ────────────────────────────────────────────────────────────────


@dataclass
class ProxyTestResult:
    """Result of a full three-dimension proxy benchmark."""

    proxy: ProviderProxy
    speed_grade: str = "?"
    strength_grade: str = "?"
    quality_grade: str = "?"
    final_verdict: str = "?"
    speed_ms: Optional[float] = None
    abuse_reports: int = 0
    fraud_score: Optional[float] = None
    abuse_confidence: Optional[float] = None
    notes: str = ""

    def to_dict(self) -> dict:
        return {
            "proxy_ip": self.proxy.ip,
            "proxy_port": self.proxy.port,
            "country": self.proxy.country,
            "speed_grade": self.speed_grade,
            "strength_grade": self.strength_grade,
            "quality_grade": self.quality_grade,
            "final_verdict": self.final_verdict,
            "speed_ms": self.speed_ms,
            "abuse_reports": self.abuse_reports,
            "fraud_score": self.fraud_score,
            "abuse_confidence": self.abuse_confidence,
            "notes": self.notes,
        }


# ─── Speed test ────────────────────────────────────────────────────────────────


async def _speed_test(proxy: ProviderProxy) -> tuple[TestResult, str]:
    """Run the existing TCP+HTTP CONNECT test and return grade."""
    result: TestResult = await test_proxy(proxy)
    if not result.alive:
        return result, "D"
    ms = result.latency_ms or 0
    if ms < 100:
        grade = "A"
    elif ms < 300:
        grade = "B"
    elif ms < 1000:
        grade = "C"
    else:
        grade = "D"
    return result, grade


# ─── Strength test (AbuseIPDB) ────────────────────────────────────────────────


async def _strength_test(proxy: ProviderProxy) -> tuple[int, float, str]:
    """
    Check AbuseIPDB for abuse reports on the proxy IP.

    Returns (reports_count, abuse_confidence_score, grade).

    Grade: A=0 reports, B=1-5, C=6-20, D=21+
    Free tier: 1000 lookups/day. No API key = skip with grade "?".

    API: GET https://api.abuseipdb.com/api/v2/check
    Params: ip-address, maxAgeInDays=30, key
    """
    if not ABUSEIPDB_KEY:
        return 0, 0.0, "?"

    url = "https://api.abuseipdb.com/api/v2/check"
    params = {"ip-address": proxy.ip, "maxAgeInDays": 30}
    headers = {"Key": ABUSEIPDB_KEY, "Accept": "application/json"}

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, params=params, headers=headers)
        if resp.status_code != 200:
            return 0, 0.0, "?"

        data = resp.json().get("data", {})
        reports = data.get("totalReports", 0)
        confidence = data.get("abuseConfidenceScore", 0)

        if reports == 0:
            grade = "A"
        elif reports <= 5:
            grade = "B"
        elif reports <= 20:
            grade = "C"
        else:
            grade = "D"

        return reports, float(confidence), grade

    except Exception:
        return 0, 0.0, "?"


# ─── Quality test (IPQualityScore) ─────────────────────────────────────────────


async def _quality_test(proxy: ProviderProxy) -> tuple[float, str]:
    """
    Check IPQualityScore for fraud indicators on the proxy IP.

    Returns (fraud_score, grade).

    Grade: A=<30, B=<60, C=<80, D=≥80
    No API key = skip with grade "?".

    API: GET https://ipqualityscore.com/api/json/ip/{ip}?key={key}
    """
    if not IPQS_KEY:
        return 0.0, "?"

    url = f"https://ipqualityscore.com/api/json/ip/{proxy.ip}"
    params = {"key": IPQS_KEY}

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, params=params)
        if resp.status_code != 200:
            return 0.0, "?"

        data = resp.json()
        fraud_score = float(data.get("fraud_score", 0))

        if fraud_score < 30:
            grade = "A"
        elif fraud_score < 60:
            grade = "B"
        elif fraud_score < 80:
            grade = "C"
        else:
            grade = "D"

        return fraud_score, grade

    except Exception:
        return 0.0, "?"


# ─── Full benchmark ─────────────────────────────────────────────────────────────


async def test_proxy_full(proxy: ProviderProxy) -> ProxyTestResult:
    """
    Run Speed + Strength + Quality tests concurrently.

    Returns a ProxyTestResult with all grades and a final PASS/FAIL verdict.

    PASS criteria: speed ≥ C AND strength ≥ C AND quality ≥ C
    """
    # Run all three in parallel
    speed_task = asyncio.create_task(_speed_test(proxy))
    strength_task = asyncio.create_task(_strength_test(proxy))
    quality_task = asyncio.create_task(_quality_test(proxy))

    speed_result, speed_grade = await speed_task
    abuse_reports, abuse_confidence, strength_grade = await strength_task
    fraud_score, quality_grade = await quality_task

    # Assemble notes
    notes_parts = []
    if not speed_result.alive:
        notes_parts.append(f"Speed dead: {speed_result.error}")
    elif speed_result.latency_ms:
        notes_parts.append(f"Latency {speed_result.latency_ms:.0f}ms")

    if ABUSEIPDB_KEY and strength_grade != "?":
        notes_parts.append(f"AbuseIPDB: {abuse_reports} reports ({abuse_confidence:.0f}% confidence)")
    elif not ABUSEIPDB_KEY:
        notes_parts.append("AbuseIPDB: no API key configured")

    if IPQS_KEY and quality_grade != "?":
        notes_parts.append(f"IPQS fraud_score={fraud_score:.0f}")
    elif not IPQS_KEY:
        notes_parts.append("IPQualityScore: no API key configured")

    # Final verdict
    grades = [speed_grade, strength_grade, quality_grade]
    grade_vals = {"A": 4, "B": 3, "C": 2, "D": 1, "?": 0}

    # PASS if all non-"?" grades ≥ C AND at least one grade is real (not all "?")
    real_grades = [g for g in grades if g != "?"]
    if real_grades and all(grade_vals.get(g, 0) >= 2 for g in real_grades):
        final_verdict = "PASS"
    else:
        final_verdict = "FAIL"

    return ProxyTestResult(
        proxy=proxy,
        speed_grade=speed_grade,
        strength_grade=strength_grade,
        quality_grade=quality_grade,
        final_verdict=final_verdict,
        speed_ms=speed_result.latency_ms,
        abuse_reports=abuse_reports,
        fraud_score=fraud_score if fraud_score else None,
        abuse_confidence=abuse_confidence if abuse_confidence else None,
        notes=" | ".join(notes_parts) if notes_parts else "No issues found",
    )


# ─── Benchmark tier definitions ────────────────────────────────────────────────


def benchmark_tiers() -> dict:
    """Return human-readable benchmark tier definitions."""
    return {
        "A": {
            "description": "Excellent — ready for production",
            "speed": "< 100ms latency",
            "strength": "0 AbuseIPDB reports",
            "quality": "IPQS fraud_score < 30",
        },
        "B": {
            "description": "Good — suitable for most use cases",
            "speed": "100–299ms latency",
            "strength": "1–5 AbuseIPDB reports",
            "quality": "IPQS fraud_score 30–59",
        },
        "C": {
            "description": "Acceptable — use with caution",
            "speed": "300–999ms latency",
            "strength": "6–20 AbuseIPDB reports",
            "quality": "IPQS fraud_score 60–79",
        },
        "D": {
            "description": "Poor — do not use",
            "speed": "> 1000ms or dead",
            "strength": "21+ AbuseIPDB reports",
            "quality": "IPQS fraud_score ≥ 80",
        },
        "?": {
            "description": "Skipped — API key not configured",
            "speed": "N/A",
            "strength": "N/A",
            "quality": "N/A",
        },
    }
