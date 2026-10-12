"""
Styxproxy SOCKS5 Auth Proxy
============================

Lightweight SOCKS5 proxy that authenticates users against the control API's
users.json, then connects to Dante on localhost:1080 (which has no auth),
then dante routes to the user's assigned upstream proxy IP:port.

This gives us:
  - Per-user auth (no PAM complexity)
  - Per-user upstream proxy selection (each customer gets routed to their IP)
  - The control API manages a simple JSON user database

Layout:
  Customer → :1081 (this proxy) → :1080 (dante, no auth) → upstream proxy
"""

import asyncio
import json
import logging
import os
import socket
import struct
from typing import Optional

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=LOG_LEVEL, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
log = logging.getLogger("socks-auth-proxy")

USERS_FILE = os.getenv("USERS_FILE", "/etc/dante/users.json")
DANTE_HOST = os.getenv("DANTE_HOST", "127.0.0.1")
DANTE_PORT = int(os.getenv("DANTE_PORT", "1080"))
LISTEN_HOST = os.getenv("LISTEN_HOST", "0.0.0.0")
LISTEN_PORT = int(os.getenv("LISTEN_PORT", "1081"))


# ─── SOCKS5 protocol constants ────────────────────────────────────────────────

SOCKS_VERSION = 0x05
NO_AUTH_METHOD = 0x00
USER_PASS_METHOD = 0x02
NO_ACCEPTABLE_METHOD = 0xFF

CMD_CONNECT = 0x01
ADDR_IPV4 = 0x01
ADDR_DOMAIN = 0x03
ADDR_IPV6 = 0x04

RESP_SUCCESS = 0x00
RESP_GENERAL_FAILURE = 0x01
RESP_NOT_ALLOWED = 0x02
RESP_NETWORK_UNREACHABLE = 0x03
RESP_HOST_UNREACHABLE = 0x04
RESP_REFUSED = 0x05
RESP_TTL_EXPIRED = 0x06
RESP_CMD_NOT_SUPPORTED = 0x07
RESP_ADDR_NOT_SUPPORTED = 0x08

USERNAME_PASSWD_VERSION = 0x01
AUTH_SUCCESS = 0x00


# ─── User store ──────────────────────────────────────────────────────────────


def _load_users() -> dict:
    """Reload users from JSON. {username: {password, upstream_ip, upstream_port}}."""
    if not os.path.exists(USERS_FILE):
        return {}
    try:
        with open(USERS_FILE, "r") as f:
            return json.load(f)
    except Exception as e:
        log.error(f"Failed to read {USERS_FILE}: {e}")
        return {}


def _verify_user(username: str, password: str) -> Optional[dict]:
    users = _load_users()
    user = users.get(username)
    if not user:
        return None
    if user.get("password") != password:
        return None
    return user


# ─── SOCKS5 protocol helpers ──────────────────────────────────────────────────


async def _read_exact(reader: asyncio.StreamReader, n: int) -> bytes:
    data = await reader.readexactly(n)
    return data


async def _send_response(writer: asyncio.StreamWriter, reply: int, bind_addr: tuple = ("0.0.0.0", 0)):
    """Send SOCKS5 connect response with bind address."""
    host, port = bind_addr
    try:
        # Try IPv4 first
        ip_bytes = socket.inet_aton(host) if isinstance(host, str) else socket.inet_aton(host.decode())
        writer.write(bytes([SOCKS_VERSION, reply, 0x00, ADDR_IPV4]))
        writer.write(ip_bytes)
        writer.write(struct.pack(">H", int(port)))
    except Exception:
        # Fallback to 0.0.0.0:0
        writer.write(bytes([SOCKS_VERSION, reply, 0x00, ADDR_IPV4]))
        writer.write(socket.inet_aton("0.0.0.0"))
        writer.write(struct.pack(">H", 0))
    await writer.drain()


async def _authenticate(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> Optional[dict]:
    """SOCKS5 handshake with username/password auth. Returns user dict or None."""
    # Client greeting: [VER, NMETHODS, METHODS]
    header = await _read_exact(reader, 2)
    ver, nmethods = header[0], header[1]
    if ver != SOCKS_VERSION:
        log.debug(f"Bad SOCKS version: {ver}")
        return None

    methods = []
    if nmethods > 0:
        methods = list(await _read_exact(reader, nmethods))

    if USER_PASS_METHOD not in methods:
        writer.write(bytes([SOCKS_VERSION, NO_ACCEPTABLE_METHOD]))
        await writer.drain()
        return None

    writer.write(bytes([SOCKS_VERSION, USER_PASS_METHOD]))
    await writer.drain()

    # Username/password: [VER, ULEN, UNAME, PLEN, PASSWD]
    auth_header = await _read_exact(reader, 2)
    auth_ver, ulen = auth_header[0], auth_header[1]
    if auth_ver != USERNAME_PASSWD_VERSION:
        return None

    uname = (await _read_exact(reader, ulen)).decode("utf-8", errors="replace")
    plen_byte = await _read_exact(reader, 1)
    plen = plen_byte[0]
    pwd = (await _read_exact(reader, plen)).decode("utf-8", errors="replace")

    user = _verify_user(uname, pwd)
    if not user:
        writer.write(bytes([USERNAME_PASSWD_VERSION, 0x01]))  # auth failed
        await writer.drain()
        log.warning(f"Auth failed for {uname}")
        return None

    writer.write(bytes([USERNAME_PASSWD_VERSION, AUTH_SUCCESS]))
    await writer.drain()
    log.info(f"Auth OK: {uname} → upstream {user['upstream_ip']}:{user['upstream_port']}")
    return user


async def _parse_request(reader: asyncio.StreamReader) -> Optional[tuple]:
    """Parse SOCKS5 connect request. Returns (cmd, addr, port) or None."""
    header = await _read_exact(reader, 4)
    ver, cmd, _rsv, atype = header
    if ver != SOCKS_VERSION:
        return None
    if cmd != CMD_CONNECT:
        return None

    if atype == ADDR_IPV4:
        addr_bytes = await _read_exact(reader, 4)
        addr = socket.inet_ntoa(addr_bytes)
    elif atype == ADDR_DOMAIN:
        dlen = (await _read_exact(reader, 1))[0]
        addr = (await _read_exact(reader, dlen)).decode("utf-8", errors="replace")
    elif atype == ADDR_IPV6:
        addr_bytes = await _read_exact(reader, 16)
        addr = socket.inet_ntop(socket.AF_INET6, addr_bytes)
    else:
        return None

    port_bytes = await _read_exact(reader, 2)
    port = struct.unpack(">H", port_bytes)[0]
    return (cmd, addr, port)


async def _connect_to_dante(user: dict) -> tuple[asyncio.StreamReader, asyncio.StreamWriter]:
    """Connect to upstream dante (no auth)."""
    upstream_ip = user["upstream_ip"]
    upstream_port = user["upstream_port"]

    log.debug(f"Connecting to dante {DANTE_HOST}:{DANTE_PORT} then to upstream {upstream_ip}:{upstream_port}")

    reader, writer = await asyncio.open_connection(DANTE_HOST, DANTE_PORT)
    # Send SOCKS5 greeting with no auth
    writer.write(bytes([SOCKS_VERSION, 1, NO_AUTH_METHOD]))
    await writer.drain()

    # Read server method selection
    resp = await _read_exact(reader, 2)
    if resp[0] != SOCKS_VERSION or resp[1] != NO_AUTH_METHOD:
        log.error(f"Bad dante greeting: {resp.hex()}")
        writer.close()
        raise ValueError(f"dante rejected no-auth: {resp.hex()}")

    # Send connect request to upstream IP
    writer.write(bytes([SOCKS_VERSION, CMD_CONNECT, 0x00, ADDR_IPV4]))
    writer.write(socket.inet_aton(upstream_ip))
    writer.write(struct.pack(">H", upstream_port))
    await writer.drain()

    # Read dante response
    resp = await _read_exact(reader, 10)
    reply = resp[1]
    if reply != RESP_SUCCESS:
        log.error(f"Dante refused upstream: reply={reply:#x}")
        writer.close()
        raise ConnectionError(f"dante refused upstream: reply={reply:#x}")

    return reader, writer


async def _handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    client_peer = writer.get_extra_info("peername")
    try:
        # 1. SOCKS5 auth handshake
        user = await _authenticate(reader, writer)
        if not user:
            return

        # 2. SOCKS5 connect request - we IGNORE the destination and use the user's assigned upstream
        req = await _parse_request(reader)
        if not req:
            await _send_response(writer, RESP_CMD_NOT_SUPPORTED)
            return
        # We don't actually care where the customer wants to go - they want through their assigned proxy
        # We tell them success and tunnel to dante

        # 3. Tell client success
        # `sockname` returns a tuple (host, port) — never None for a connected socket
        bind_addr = writer.get_extra_info("sockname") or ("0.0.0.0", 0)
        await _send_response(writer, RESP_SUCCESS, bind_addr=bind_addr)

        # 4. Connect to dante with the user's assigned upstream
        dante_reader, dante_writer = await _connect_to_dante(user)

        # 5. Bidirectional copy
        async def pipe(r: asyncio.StreamReader, w: asyncio.StreamWriter):
            try:
                while True:
                    data = await r.read(4096)
                    if not data:
                        break
                    w.write(data)
                    await w.drain()
            except Exception:
                pass
            finally:
                if not w.is_closing():
                    w.close()

        await asyncio.gather(
            pipe(reader, dante_writer),
            pipe(dante_reader, writer),
            return_exceptions=True,
        )

    except Exception as e:
        log.warning(f"client {client_peer}: {type(e).__name__}: {e}", exc_info=True)
    finally:
        try:
            writer.close()
        except Exception:
            pass


async def main():
    log.info(f"SOCKS5 auth proxy starting on {LISTEN_HOST}:{LISTEN_PORT}")
    log.info(f"Forwarding to dante at {DANTE_HOST}:{DANTE_PORT}")
    log.info(f"Users file: {USERS_FILE}")

    server = await asyncio.start_server(_handle_client, LISTEN_HOST, LISTEN_PORT, reuse_address=True)
    log.info(f"Listening on {LISTEN_HOST}:{LISTEN_PORT}")
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())
