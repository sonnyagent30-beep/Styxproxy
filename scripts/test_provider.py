#!/usr/bin/env python3
"""
CLI runner for provider_test.py — Sprint 3.

Usage:
  # Test a single proxy IP
  python3 test_provider.py --ip 185.199.228.45 --port 1080

  # Test with HTTP protocol (default)
  python3 test_provider.py --ip 185.199.228.45 --port 1080 --http

  # Test SOCKS5 protocol
  python3 test_provider.py --ip 185.199.228.45 --port 1080 --socks5

  # Tier definitions only
  python3 test_provider.py --tiers

Env vars (optional):
  ABUSEIPDB_API_KEY        — AbuseIPDB free tier (1000/day)
  IPQUALITYSCORE_API_KEY   — IPQualityScore free tier
"""

import argparse
import asyncio

# Allow running from repo root or scripts/ dir
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))) or ".")

from app.services.provider import ProviderProxy
from app.services.provider_test import benchmark_tiers, test_proxy_full


async def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark a proxy: Speed + Strength + Quality")
    parser.add_argument("--ip", help="Proxy IP address")
    parser.add_argument("--port", type=int, help="Proxy port")
    parser.add_argument("--http", action="store_true", default=True, help="Protocol is HTTP (default)")
    parser.add_argument("--socks5", action="store_true", default=False, help="Protocol is SOCKS5")
    parser.add_argument("--tiers", action="store_true", help="Print tier definitions and exit")
    args = parser.parse_args()

    if args.tiers:
        print("=== Benchmark Tier Definitions ===\n")
        tiers = benchmark_tiers()
        for tier, info in tiers.items():
            print(f"Tier {tier}: {info['description']}")
            print(f"  Speed:    {info['speed']}")
            print(f"  Strength: {info['strength']}")
            print(f"  Quality:  {info['quality']}")
            print()
        return

    if not args.ip or not args.port:
        parser.error("--ip and --port are required (or use --tiers)")

    protocol = "socks5" if args.socks5 else "http"

    proxy = ProviderProxy(
        provider_order_id=f"cli-test-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
        ip=args.ip,
        port=args.port,
        username="",
        password="",
        protocol=protocol,
        expires_at=datetime.now(timezone.utc),
        country="",
        isp="",
        asn="",
    )

    print(f"Testing {args.ip}:{args.port} (protocol={protocol})...\n")

    result = await test_proxy_full(proxy)

    print("=== Benchmark Results ===\n")
    spd = f"{result.speed_ms:.0f}ms" if result.speed_ms else "N/A"
    print(f"  Speed grade:    {result.speed_grade}  ({spd})")
    print(f"  Strength grade: {result.strength_grade}  (AbuseIPDB: {result.abuse_reports} reports)")
    qs = f"  (IPQS fraud_score={result.fraud_score:.0f})" if result.fraud_score else ""
    print(f"  Quality grade:  {result.quality_grade}{qs}")
    print(f"  Verdict:        {result.final_verdict}")
    print(f"  Notes:          {result.notes}")
    print()

    sys.exit(0 if result.final_verdict == "PASS" else 1)


if __name__ == "__main__":
    asyncio.run(main())
