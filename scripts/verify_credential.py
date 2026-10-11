#!/usr/bin/env python3
"""
Post-fulfillment verification for Styxproxy credentials.

Tests that a credential actually works by connecting through the upstream proxy.
This is the check that would have caught the class of bug where credentials
are created but nothing listens on the port, or the upstream proxy is dead.

Usage:
    # Verify a specific credential by ID
    python3 verify_credential.py --credential-id 42
    
    # Verify a credential by upstream IP/port
    python3 verify_credential.py --ip 1.2.3.4 --port 8080 --username sty_abc --password secret
    
    # Verify all active credentials (for ops health check)
    python3 verify_credential.py --all
    
    # Output as JSON
    python3 verify_credential.py --credential-id 42 --json

Exit codes:
    0 = all verifications passed
    1 = at least one verification failed
    2 = error (invalid args, DB connection failed, etc.)
"""

import argparse
import asyncio
import json
import logging
import sys
import os
from pathlib import Path
from typing import Optional

# Add backend to path
BACKEND_PATH = "/opt/styxproxy/backend"
sys.path.insert(0, BACKEND_PATH)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("verify_credential")


async def verify_by_id(credential_id: int, json_output: bool = False) -> bool:
    """Verify a credential by its database ID."""
    import asyncpg
    from app.config import get_settings
    from app.services.post_fulfillment_check import verify_credential

    settings = get_settings()
    dsn = (settings.database_url or "").replace("postgresql+asyncpg://", "postgresql://")

    try:
        conn = await asyncpg.connect(dsn)
    except Exception as e:
        logger.error(f"DB connection failed: {e}")
        return False

    try:
        row = await conn.fetchrow(
            """
            SELECT id, styxproxy_username, styxproxy_password, upstream_proxy_ip,
                   upstream_proxy_port, protocol, status
            FROM styxproxy_credentials
            WHERE id = $1
            """,
            credential_id,
        )
    finally:
        await conn.close()

    if not row:
        logger.error(f"Credential {credential_id} not found")
        return False

    # Decrypt password
    from app.services.crypto import decrypt_credential_compat
    password = decrypt_credential_compat(row["styxproxy_password"])
    if not password:
        logger.error(f"Could not decrypt password for credential {credential_id}")
        return False

    result = await verify_credential(
        ip=row["upstream_proxy_ip"],
        port=row["upstream_proxy_port"],
        username=row["styxproxy_username"],
        password=password,
        protocol=row["protocol"] or "socks5",
    )

    if json_output:
        output = {
            "credential_id": credential_id,
            "username": row["styxproxy_username"],
            "upstream": f"{row['upstream_proxy_ip']}:{row['upstream_proxy_port']}",
            "protocol": row["protocol"],
            "ok": result.ok,
            "latency_ms": result.latency_ms,
            "error": result.error,
            "detail": result.detail,
        }
        print(json.dumps(output, indent=2))
    else:
        status = "PASS" if result.ok else "FAIL"
        print(f"[{status}] Credential {credential_id} ({row['styxproxy_username']})")
        print(f"  Upstream: {row['upstream_proxy_ip']}:{row['upstream_proxy_port']}")
        print(f"  Protocol: {row['protocol']}")
        if result.ok:
            print(f"  Latency: {result.latency_ms}ms")
            print(f"  Detail: {result.detail}")
        else:
            print(f"  Error: {result.error}")
            print(f"  Detail: {result.detail}")

    return result.ok


async def verify_by_params(
    ip: str,
    port: int,
    username: str,
    password: str,
    protocol: str = "socks5",
    json_output: bool = False,
) -> bool:
    """Verify a credential by explicit parameters."""
    from app.services.post_fulfillment_check import verify_credential

    result = await verify_credential(
        ip=ip,
        port=port,
        username=username,
        password=password,
        protocol=protocol,
    )

    if json_output:
        output = {
            "ip": ip,
            "port": port,
            "username": username,
            "protocol": protocol,
            "ok": result.ok,
            "latency_ms": result.latency_ms,
            "error": result.error,
            "detail": result.detail,
        }
        print(json.dumps(output, indent=2))
    else:
        status = "PASS" if result.ok else "FAIL"
        print(f"[{status}] {username}@{ip}:{port} ({protocol})")
        if result.ok:
            print(f"  Latency: {result.latency_ms}ms")
            print(f"  Detail: {result.detail}")
        else:
            print(f"  Error: {result.error}")
            print(f"  Detail: {result.detail}")

    return result.ok


async def verify_all(json_output: bool = False) -> bool:
    """Verify all active credentials."""
    import asyncpg
    from app.config import get_settings
    from app.services.post_fulfillment_check import verify_credential
    from app.services.crypto import decrypt_credential_compat

    settings = get_settings()
    dsn = (settings.database_url or "").replace("postgresql+asyncpg://", "postgresql://")

    try:
        conn = await asyncpg.connect(dsn)
    except Exception as e:
        logger.error(f"DB connection failed: {e}")
        return False

    try:
        rows = await conn.fetch(
            """
            SELECT id, styxproxy_username, styxproxy_password, upstream_proxy_ip,
                   upstream_proxy_port, protocol, status
            FROM styxproxy_credentials
            WHERE status = 'active'
            ORDER BY id
            """
        )
    finally:
        await conn.close()

    if not rows:
        logger.info("No active credentials to verify")
        return True

    logger.info(f"Verifying {len(rows)} active credentials...")

    passed = 0
    failed = 0
    results = []

    for row in rows:
        password = decrypt_credential_compat(row["styxproxy_password"])
        if not password:
            logger.error(f"Could not decrypt password for credential {row['id']}")
            failed += 1
            results.append({
                "id": row["id"],
                "ok": False,
                "error": "decrypt_failed",
            })
            continue

        result = await verify_credential(
            ip=row["upstream_proxy_ip"],
            port=row["upstream_proxy_port"],
            username=row["styxproxy_username"],
            password=password,
            protocol=row["protocol"] or "socks5",
        )

        status = "PASS" if result.ok else "FAIL"
        print(f"[{status}] Credential {row['id']} ({row['styxproxy_username']}) — {row['upstream_proxy_ip']}:{row['upstream_proxy_port']}")

        if result.ok:
            passed += 1
        else:
            failed += 1
            print(f"  Error: {result.error}: {result.detail}")

        results.append({
            "id": row["id"],
            "username": row["styxproxy_username"],
            "ok": result.ok,
            "latency_ms": result.latency_ms,
            "error": result.error,
            "detail": result.detail,
        })

    print(f"\nSummary: {passed} passed, {failed} failed, {len(rows)} total")

    if json_output:
        print(json.dumps({"passed": passed, "failed": failed, "total": len(rows), "results": results}, indent=2))

    return failed == 0


def main():
    parser = argparse.ArgumentParser(description="Verify Styxproxy credentials")
    parser.add_argument("--credential-id", type=int, help="Verify a specific credential by ID")
    parser.add_argument("--ip", help="Upstream proxy IP")
    parser.add_argument("--port", type=int, help="Upstream proxy port")
    parser.add_argument("--username", help="Proxy username")
    parser.add_argument("--password", help="Proxy password")
    parser.add_argument("--protocol", default="socks5", choices=["socks5", "http", "https"], help="Proxy protocol")
    parser.add_argument("--all", action="store_true", help="Verify all active credentials")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--quiet", action="store_true", help="Suppress info logs")

    args = parser.parse_args()

    if args.quiet:
        logging.getLogger().setLevel(logging.WARNING)

    # Validate args
    if args.all:
        success = asyncio.run(verify_all(args.json))
    elif args.credential_id:
        success = asyncio.run(verify_by_id(args.credential_id, args.json))
    elif args.ip and args.port and args.username and args.password:
        success = asyncio.run(verify_by_params(
            args.ip, args.port, args.username, args.password, args.protocol, args.json
        ))
    else:
        parser.print_help()
        sys.exit(2)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
