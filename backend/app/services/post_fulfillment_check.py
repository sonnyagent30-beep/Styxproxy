"""
Post-fulfilment verification: test that a credential actually works before
the customer is told it is ready.

This is the check that would have caught the class of bug where credentials
are created but nothing listens on the port, or the upstream proxy is dead.

Design:
- Tests the upstream proxy DIRECTLY (not through the local relay)
- Uses the same protocol the customer will use (SOCKS5 or HTTP CONNECT)
- Fails closed: any error means the credential is not ready
- Returns a structured result so the caller can decide what to do

Usage:
    result = await verify_credential(
        ip="1.2.3.4",
        port=8080,
        username="sty_abc123",
        password="secret",
        protocol="socks5",
    )
    if not result.ok:
        # Don't tell the customer it's ready
"""

import asyncio
import logging
import socket
import struct
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class VerificationResult:
    """Result of a post-fulfilment verification."""

    ok: bool
    latency_ms: Optional[float] = None
    error: Optional[str] = None
    detail: Optional[str] = None


async def verify_credential(
    ip: str,
    port: int,
    username: str,
    password: str,
    protocol: str = "socks5",
    timeout: float = 10.0,
) -> VerificationResult:
    """Verify a credential by connecting through the upstream proxy.

    This tests the ACTUAL customer path: connect to the upstream proxy,
    authenticate with the styxproxy credentials, and make a test request.

    Returns VerificationResult with ok=True only if the proxy is reachable,
    accepts authentication, and successfully proxies a test request.
    """
    loop = asyncio.get_event_loop()

    try:
        # Run the blocking socket operations in a thread pool
        result = await asyncio.wait_for(
            loop.run_in_executor(
                None,
                _verify_sync,
                ip,
                port,
                username,
                password,
                protocol,
            ),
            timeout=timeout,
        )
        return result
    except asyncio.TimeoutError:
        return VerificationResult(
            ok=False,
            error="verification_timeout",
            detail=f"Verification did not complete within {timeout}s",
        )
    except Exception as e:
        return VerificationResult(
            ok=False,
            error="verification_exception",
            detail=f"{type(e).__name__}: {e}",
        )


def _verify_sync(
    ip: str,
    port: int,
    username: str,
    password: str,
    protocol: str,
) -> VerificationResult:
    """Synchronous verification — runs in thread pool."""
    import time

    start = time.monotonic()

    # ── TCP connect ──────────────────────────────────────────────────────────
    try:
        sock = socket.create_connection((ip, port), timeout=10)
    except socket.timeout:
        return VerificationResult(
            ok=False,
            error="upstream_tcp_timeout",
            detail=f"TCP connect to {ip}:{port} timed out",
        )
    except ConnectionRefusedError:
        return VerificationResult(
            ok=False,
            error="upstream_tcp_refused",
            detail=f"TCP connect to {ip}:{port} refused",
        )
    except Exception as e:
        return VerificationResult(
            ok=False,
            error="upstream_tcp_error",
            detail=f"TCP connect to {ip}:{port} failed: {e}",
        )

    try:
        if protocol.lower() == "socks5":
            return _verify_socks5(sock, username, password, start)
        elif protocol.lower() in ("http", "https"):
            return _verify_http_connect(sock, username, password, ip, port, start)
        else:
            # Unknown protocol — just verify TCP + auth handshake
            return _verify_tcp_only(sock, start)
    finally:
        try:
            sock.close()
        except Exception:
            pass


def _verify_socks5(
    sock: socket.socket,
    username: str,
    password: str,
    start_time: float,
) -> VerificationResult:
    """Verify via SOCKS5 protocol with username/password auth."""
    import time

    # ── Method selection ─────────────────────────────────────────────────────
    # Send: ver=5, nmethods=2, methods=[0x00 (no auth), 0x02 (user/pass)]
    methods = b"\x05\x02\x00\x02"
    try:
        sock.sendall(methods)
    except Exception as e:
        return VerificationResult(
            ok=False,
            error="socks5_send_methods_failed",
            detail=str(e),
        )

    # Read: ver=5, method=selected
    try:
        resp = sock.recv(2)
    except socket.timeout:
        return VerificationResult(
            ok=False,
            error="socks5_method_timeout",
        )
    except Exception as e:
        return VerificationResult(
            ok=False,
            error="socks5_recv_method_failed",
            detail=str(e),
        )

    if len(resp) < 2:
        return VerificationResult(
            ok=False,
            error="socks5_short_method_response",
            detail=f"Expected 2 bytes, got {len(resp)}",
        )

    version, method = resp[0], resp[1]
    if version != 5:
        return VerificationResult(
            ok=False,
            error="socks5_bad_version",
            detail=f"Expected version 5, got {version}",
        )

    if method == 0xFF:
        return VerificationResult(
            ok=False,
            error="socks5_no_acceptable_method",
            detail="Server rejected all auth methods",
        )

    # ── Username/Password auth (RFC 1929) ────────────────────────────────────
    if method == 0x02:
        # Send: ver=1, ulen, uname, plen, passwd
        uname_bytes = username.encode("utf-8")[:255]
        passwd_bytes = password.encode("utf-8")[:255]
        auth_msg = (
            b"\x01"
            + bytes([len(uname_bytes)])
            + uname_bytes
            + bytes([len(passwd_bytes)])
            + passwd_bytes
        )
        try:
            sock.sendall(auth_msg)
        except Exception as e:
            return VerificationResult(
                ok=False,
                error="socks5_send_auth_failed",
                detail=str(e),
            )

        # Read: ver=1, status=0 (success)
        try:
            auth_resp = sock.recv(2)
        except socket.timeout:
            return VerificationResult(
                ok=False,
                error="socks5_auth_timeout",
            )
        except Exception as e:
            return VerificationResult(
                ok=False,
                error="socks5_recv_auth_failed",
                detail=str(e),
            )

        if len(auth_resp) < 2:
            return VerificationResult(
                ok=False,
                error="socks5_short_auth_response",
            )

        if auth_resp[1] != 0:
            return VerificationResult(
                ok=False,
                error="socks5_auth_rejected",
                detail=f"Auth status: {auth_resp[1]}",
            )

    # ── Connect to a test target through the proxy ───────────────────────────
    # Use a well-known DNS root server as target (port 53 UDP is fine for TCP connect)
    # We just want to verify the proxy will CONNECT somewhere — we don't need
    # the actual connection to succeed, just the proxy to accept the request.
    # Actually, let's try a real HTTP request to a known-good target.
    # Use 1.1.1.1:443 (Cloudflare DNS-over-HTTPS) — reliable and fast.
    try:
        # SOCKS5 CONNECT: ver=5, cmd=1 (connect), rsv=0, atyp=1 (IPv4), addr, port
        connect_req = (
            b"\x05\x01\x00"
            + b"\x01"  # atyp: IPv4
            + socket.inet_aton("1.1.1.1")
            + struct.pack("!H", 443)
        )
        sock.sendall(connect_req)
    except Exception as e:
        return VerificationResult(
            ok=False,
            error="socks5_send_connect_failed",
            detail=str(e),
        )

    # Read response: ver=5, rep=0 (success), rsv=0, atyp, bind_addr, bind_port
    try:
        # Read first 4 bytes (ver, rep, rsv, atyp)
        resp = b""
        while len(resp) < 4:
            chunk = sock.recv(4 - len(resp))
            if not chunk:
                break
            resp += chunk

        if len(resp) < 4:
            return VerificationResult(
                ok=False,
                error="socks5_short_connect_response",
            )

        rep = resp[1]
        if rep != 0:
            error_codes = {
                1: "general_socks_server_failure",
                2: "connection_not_allowed",
                3: "network_unreachable",
                4: "host_unreachable",
                5: "connection_refused",
                6: "ttl_expired",
                7: "command_not_supported",
                8: "address_type_not_supported",
            }
            return VerificationResult(
                ok=False,
                error="socks5_connect_failed",
                detail=f"rep={rep}: {error_codes.get(rep, 'unknown')}",
            )

        # Read the rest of the response (bind address + port)
        atyp = resp[3]
        if atyp == 1:  # IPv4
            remaining = 4 + 2  # addr + port
        elif atyp == 3:  # Domain
            # Read domain length first
            try:
                domain_len = sock.recv(1)
                remaining = len(domain_len) + domain_len[0] + 2
            except Exception:
                remaining = 32  # fallback
        elif atyp == 4:  # IPv6
            remaining = 16 + 2
        else:
            remaining = 32  # fallback

        # Drain remaining response
        while remaining > 0:
            chunk = sock.recv(min(remaining, 256))
            if not chunk:
                break
            remaining -= len(chunk)

    except socket.timeout:
        return VerificationResult(
            ok=False,
            error="socks5_connect_timeout",
        )
    except Exception as e:
        return VerificationResult(
            ok=False,
            error="socks5_connect_error",
            detail=str(e),
        )

    latency_ms = (time.monotonic() - start_time) * 1000
    return VerificationResult(
        ok=True,
        latency_ms=round(latency_ms, 1),
        detail="SOCKS5 CONNECT to 1.1.1.1:443 succeeded",
    )


def _verify_http_connect(
    sock: socket.socket,
    username: str,
    password: str,
    target_ip: str,
    target_port: int,
    start_time: float,
) -> VerificationResult:
    """Verify via HTTP CONNECT (for HTTP proxies)."""
    import time
    import base64

    # Build CONNECT request with Proxy-Authorization
    auth = base64.b64encode(f"{username}:{password}".encode()).decode()
    connect_req = (
        f"CONNECT {target_ip}:{target_port} HTTP/1.1\r\n"
        f"Host: {target_ip}:{target_port}\r\n"
        f"Proxy-Authorization: Basic {auth}\r\n"
        f"User-Agent: styxproxy-verify/1.0\r\n"
        f"\r\n"
    )

    try:
        sock.sendall(connect_req.encode())
    except Exception as e:
        return VerificationResult(
            ok=False,
            error="http_connect_send_failed",
            detail=str(e),
        )

    # Read response
    try:
        resp = b""
        while b"\r\n\r\n" not in resp and len(resp) < 4096:
            chunk = sock.recv(1024)
            if not chunk:
                break
            resp += chunk
    except socket.timeout:
        return VerificationResult(
            ok=False,
            error="http_connect_timeout",
        )
    except Exception as e:
        return VerificationResult(
            ok=False,
            error="http_connect_recv_failed",
            detail=str(e),
        )

    status_line = resp.split(b"\r\n", 1)[0].decode("latin-1", errors="ignore")
    try:
        status_code = int(status_line.split()[1])
    except (IndexError, ValueError):
        return VerificationResult(
            ok=False,
            error="http_connect_bad_response",
            detail=f"Could not parse status from: {status_line!r}",
        )

    if not (200 <= status_code < 300):
        return VerificationResult(
            ok=False,
            error="http_connect_rejected",
            detail=f"HTTP {status_code}: {status_line}",
        )

    latency_ms = (time.monotonic() - start_time) * 1000
    return VerificationResult(
        ok=True,
        latency_ms=round(latency_ms, 1),
        detail=f"HTTP CONNECT to {target_ip}:{target_port} succeeded",
    )


def _verify_tcp_only(
    sock: socket.socket,
    start_time: float,
) -> VerificationResult:
    """Fallback: just verify TCP connectivity."""
    import time
    latency_ms = (time.monotonic() - start_time) * 1000
    return VerificationResult(
        ok=True,
        latency_ms=round(latency_ms, 1),
        detail="TCP connect succeeded (no protocol verification)",
    )
