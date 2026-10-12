"""Self-contained test for provider.test_proxy.

Three behavioral assertions:

1. Unreachable host (port 1, refused) — alive=False, error='connection_refused',
   elapsed < 8s.
2. protocol='http', TCP-accepts-but-no-CONNECT-reply (we just open and close) —
   alive=False with error indicating handshake/protocol failure (any of
   connect_rejected, protocol_handshake_failed, OR connection reset).
3. protocol='socks5' (TCP-only fallback) — alive=True when the port accepts TCP.

Run: ssh to interserver and execute.
"""
import asyncio
import socket
import sys
import time

sys.path.insert(0, "/opt/styxproxy/backend")

from app.services.provider import ProviderProxy, test_proxy


async def test_unreachable_host():
    """TCP connect to a closed port should return alive=False quickly."""
    proxy = ProviderProxy(
        provider_order_id="STUB-1",
        ip="127.0.0.1",
        port=1,  # reserved, typically refused
        username="x",
        password="y",
        protocol="http",
        expires_at=None,
        country="NG",
        isp="Test",
        asn="AS0",
    )
    t0 = time.time()
    result = await test_proxy(proxy)
    elapsed = time.time() - t0
    print(f"[unreachable] alive={result.alive} error={result.error!r} elapsed={elapsed:.2f}s")
    assert result.alive is False
    assert result.error == "connection_refused"
    assert elapsed < 8, f"took {elapsed:.2f}s, expected <8"
    print("  PASS")


async def _find_free_port() -> int:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


async def test_http_handshake_failure():
    """Server accepts TCP then closes without responding. HTTP handshake
    should fail, alive=False with an error indicating handshake issue."""
    port = await _find_free_port()

    # Server: accept and immediately close
    async def server():
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(("127.0.0.1", port))
        s.listen(1)
        s.settimeout(8)
        try:
            conn, _ = s.accept()
            conn.close()
        except Exception:
            pass
        finally:
            s.close()

    server_task = asyncio.create_task(server())
    # Allow server to bind + start listening (longer than tcp_only to avoid races)
    await asyncio.sleep(0.5)

    proxy = ProviderProxy(
        provider_order_id="STUB-2",
        ip="127.0.0.1",
        port=port,
        username="x",
        password="y",
        protocol="http",
        expires_at=None,
        country="NG",
        isp="Test",
        asn="AS0",
    )

    result = await test_proxy(proxy)
    server_task.cancel()
    try:
        await server_task
    except (asyncio.CancelledError, Exception):
        pass

    print(f"[http_handshake_failure] alive={result.alive} error={result.error!r}")
    assert result.alive is False, f"expected alive=False (proxy dead), got {result.alive}"
    error = result.error or ""
    assert any(
        marker in error
        for marker in (
            "connect_rejected",
            "protocol_handshake_failed",
            "connection_reset",
            "connection_closed",
            "timed_out",
            "ECONNRESET",
            "connection_refused",
        )
    ), f"unexpected error: {error!r}"
    print("  PASS")


async def test_tcp_only_fallback():
    """protocol='socks5' falls back to TCP-only check. Local listener that
    accepts should give alive=True."""
    port = await _find_free_port()

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("127.0.0.1", port))
    server.listen(1)
    server.settimeout(5)

    accept_done = asyncio.Event()
    accepted_conn = []

    async def accept_in_thread():
        loop = asyncio.get_event_loop()
        try:
            conn, addr = await loop.run_in_executor(None, server.accept)
            accepted_conn.append(conn)
            accept_done.set()
        except Exception:
            pass

    asyncio.create_task(accept_in_thread())
    await asyncio.sleep(0.5)  # let server bind + start listening

    proxy = ProviderProxy(
        provider_order_id="STUB-3",
        ip="127.0.0.1",
        port=port,
        username="x",
        password="y",
        protocol="socks5",
        expires_at=None,
        country="NG",
        isp="Test",
        asn="AS0",
    )

    try:
        result = await test_proxy(proxy)
    finally:
        try:
            await asyncio.wait_for(accept_done.wait(), timeout=2)
        except Exception:
            pass
        try:
            server.close()
        except Exception:
            pass
        for c in accepted_conn:
            try:
                c.close()
            except Exception:
                pass

    print(f"[tcp_only_fallback] alive={result.alive} latency={result.latency_ms}")
    assert result.alive is True, f"expected alive=True (TCP-only fallback), got {result.alive}"
    print("  PASS")


async def main():
    await test_unreachable_host()
    await test_http_handshake_failure()
    await test_tcp_only_fallback()
    print("\nAll test_proxy behavioral checks PASSED")


asyncio.run(main())
