"""
Styxproxy SOCKS5 + HTTP Relay (Postgres-backed)
================================================

PAID customer relay on Interserver.
- Reads styxproxy_credentials (joined with styxproxy_relay_entries) from Postgres.
- Customer connects on :1080 (SOCKS5) or :8080 (HTTP CONNECT) with username/password.
- Relay authenticates customer against Postgres, then connects to the upstream proxy
  specified in their credential/relay_entry (Rayobyte, Proxy-Seller, etc.).
- Supports upstream protocols: SOCKS5 (username/password) and HTTP CONNECT (Basic auth).
- Free trial relay uses /opt/styxproxy-dante/socks-auth-proxy (different deploy).

Customer → :1080/:8080 (this relay) → upstream provider → internet
"""

import asyncio
import base64
import logging
import os
import socket
import struct
import sys
from pathlib import Path
from typing import Optional

import asyncpg

# Add backend to path so we can import app config
sys.path.insert(0, "/opt/styxproxy/backend")

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=LOG_LEVEL, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
log = logging.getLogger("styxproxy-relay")

LISTEN_HOST = os.getenv("LISTEN_HOST", "0.0.0.0")
LISTEN_PORT_SOCKS = int(os.getenv("LISTEN_PORT_SOCKS", "1080"))
LISTEN_PORT_HTTP = int(os.getenv("LISTEN_PORT_HTTP", "8080"))

DATABASE_URL = os.getenv("DATABASE_URL", "")
if not DATABASE_URL:
    env_file = Path("/opt/styxproxy/.env")
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line.startswith("DATABASE_URL="):
                url = line.split("=", 1)[1].strip()
                if url.startswith("postgresql+asyncpg://"):
                    url = url.replace("postgresql+asyncpg://", "postgresql://", 1)
                DATABASE_URL = url
                break

if not DATABASE_URL:
    log.error("DATABASE_URL not set")
    sys.exit(1)


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


# ─── Database ────────────────────────────────────────────────────────────────


class RelayAuth:
    """Postgres-backed auth table with TTL cache."""

    def __init__(self, dsn: str, ttl_seconds: int = 30):
        self.dsn = dsn
        self.ttl = ttl_seconds
        self._cache: dict = {}  # username -> password
        self._user_to_upstream: dict = {}  # username -> {host, port, user, pass, protocol}
        self._expires_at: float = 0
        self._lock = asyncio.Lock()

    async def refresh(self):
        """Refresh cache from Postgres."""
        async with self._lock:
            conn = await asyncpg.connect(self.dsn)
            try:
                rows = await conn.fetch(
                    """
                    SELECT
                        c.styxproxy_username,
                        c.styxproxy_password,
                        c.protocol,
                        c.upstream_proxy_ip,
                        c.upstream_proxy_port,
                        c.provider_username,
                        c.provider_password,
                        c.expires_at,
                        c.status,
                        r.upstream_type,
                        r.upstream_host,
                        r.upstream_port,
                        r.upstream_user,
                        r.upstream_pass,
                        r.upstream_protocol,
                        r.status AS relay_status,
                        r.region
                    FROM styxproxy_credentials c
                    LEFT JOIN styxproxy_relay_entries r ON c.id = r.credential_id
                    WHERE c.status = 'active'
                    """
                )

                new_passwords = {}
                new_upstreams = {}
                now = asyncio.get_event_loop().time()

                for row in rows:
                    username = row["styxproxy_username"]
                    password = row["styxproxy_password"]
                    if isinstance(password, bytes):
                        password = password.decode("utf-8", errors="replace")

                    # Skip expired
                    expires = row["expires_at"]
                    if expires is not None:
                        try:
                            exp_ts = expires.timestamp()
                            if exp_ts < now:
                                continue
                        except Exception:
                            pass

                    # Skip if relay entry explicitly inactive
                    relay_status = row["relay_status"]
                    if relay_status and relay_status != "active":
                        continue

                    new_passwords[username] = password

                    upstream = {
                        "host": row["upstream_host"] or row["upstream_proxy_ip"] or "",
                        "port": row["upstream_port"] or row["upstream_proxy_port"] or 0,
                        "user": row["upstream_user"] or row["provider_username"] or "",
                        "pass": row["upstream_pass"] or row["provider_password"] or "",
                        "protocol": row["upstream_protocol"] or row["protocol"] or "socks5",
                    }
                    new_upstreams[username] = upstream

                self._cache = new_passwords
                self._user_to_upstream = new_upstreams
                self._expires_at = now + self.ttl
                log.info(f"Auth cache refreshed: {len(new_passwords)} users")
            finally:
                await conn.close()

    async def verify(self, username: str, password: str) -> Optional[dict]:
        """Verify credentials. Returns user dict (with upstream) if valid."""
        now = asyncio.get_event_loop().time()
        if now > self._expires_at:
            await self.refresh()

        expected = self._cache.get(username)
        if not expected or expected != password:
            return None

        upstream = self._user_to_upstream.get(username)
        if not upstream or not upstream["host"]:
            log.warning(f"User {username} has no upstream configured")
            return None

        return {"username": username, "upstream": upstream}


# ─── SOCKS5 protocol helpers ─────────────────────────────────────────────────


async def _read_exact(reader: asyncio.StreamReader, n: int) -> bytes:
    return await reader.readexactly(n)


async def _send_response(writer: asyncio.StreamWriter, reply: int, bind_addr: tuple = ("0.0.0.0", 0)):
    host, port = bind_addr
    try:
        ip_bytes = socket.inet_aton(host) if isinstance(host, str) else socket.inet_aton(host.decode())
        writer.write(bytes([SOCKS_VERSION, reply, 0x00, ADDR_IPV4]))
        writer.write(ip_bytes)
        writer.write(struct.pack(">H", int(port)))
    except Exception:
        writer.write(bytes([SOCKS_VERSION, reply, 0x00, ADDR_IPV4]))
        writer.write(socket.inet_aton("0.0.0.0"))
        writer.write(struct.pack(">H", 0))
    await writer.drain()


async def _authenticate(reader: asyncio.StreamReader, writer: asyncio.StreamWriter, auth: RelayAuth) -> Optional[dict]:
    header = await _read_exact(reader, 2)
    ver, nmethods = header[0], header[1]
    if ver != SOCKS_VERSION:
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

    auth_header = await _read_exact(reader, 2)
    auth_ver, ulen = auth_header[0], auth_header[1]
    if auth_ver != USERNAME_PASSWD_VERSION:
        return None

    uname = (await _read_exact(reader, ulen)).decode("utf-8", errors="replace")
    plen_byte = await _read_exact(reader, 1)
    plen = plen_byte[0]
    pwd = (await _read_exact(reader, plen)).decode("utf-8", errors="replace")

    user = await auth.verify(uname, pwd)
    if not user:
        writer.write(bytes([USERNAME_PASSWD_VERSION, 0x01]))
        await writer.drain()
        log.warning(f"Auth failed for {uname}")
        return None

    writer.write(bytes([USERNAME_PASSWD_VERSION, AUTH_SUCCESS]))
    await writer.drain()
    log.info(f"Auth OK: {uname} -> upstream {user['upstream']['host']}:{user['upstream']['port']}")
    return user


async def _parse_request(reader: asyncio.StreamReader) -> Optional[tuple]:
    header = await _read_exact(reader, 4)
    ver, cmd, _rsv, atype = header
    if ver != SOCKS_VERSION or cmd != CMD_CONNECT:
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


async def _connect_to_upstream(upstream: dict) -> tuple:
    """Connect to upstream proxy and authenticate (if SOCKS5). HTTP auth done in handler."""
    host = upstream["host"]
    port = upstream["port"]
    protocol = upstream["protocol"]
    user = upstream["user"]
    password = upstream["pass"]

    log.debug(f"Connecting to upstream {host}:{port} via {protocol}")

    if protocol == "socks5":
        reader, writer = await asyncio.open_connection(host, port)
        writer.write(bytes([SOCKS_VERSION, 1, USER_PASS_METHOD]))
        await writer.drain()
        resp = await _read_exact(reader, 2)
        if resp[0] != SOCKS_VERSION or resp[1] != USER_PASS_METHOD:
            writer.close()
            raise ValueError(f"upstream rejected auth: {resp.hex()}")

        user_bytes = user.encode("utf-8")
        pass_bytes = password.encode("utf-8")
        writer.write(bytes([USERNAME_PASSWD_VERSION, len(user_bytes)]))
        writer.write(user_bytes)
        writer.write(bytes([len(pass_bytes)]))
        writer.write(pass_bytes)
        await writer.drain()

        auth_resp = await _read_exact(reader, 2)
        if auth_resp[1] != AUTH_SUCCESS:
            writer.close()
            raise ConnectionError(f"upstream auth failed: {auth_resp.hex()}")

        return reader, writer
    elif protocol in ("http", "https"):
        reader, writer = await asyncio.open_connection(host, port)
        return reader, writer
    else:
        raise ValueError(f"unsupported protocol: {protocol}")


async def _send_http_connect_to_upstream(upstream: dict, target_host: str, target_port: int, reader, writer):
    """Send HTTP CONNECT with Basic auth to upstream proxy."""
    creds = base64.b64encode(f"{upstream['user']}:{upstream['pass']}".encode()).decode()
    connect_req = (
        f"CONNECT {target_host}:{target_port} HTTP/1.1\r\n"
        f"Host: {target_host}:{target_port}\r\n"
        f"Proxy-Authorization: Basic {creds}\r\n"
        f"\r\n"
    )
    writer.write(connect_req.encode())
    await writer.drain()
    resp_line = await reader.readline()
    log.debug(f"upstream CONNECT response: {resp_line!r}")
    # Read headers until empty line
    while True:
        hdr = await reader.readline()
        if not hdr or hdr == b"\r\n":
            break
    if b" 200 " not in resp_line:
        raise ConnectionError(f"upstream CONNECT failed: {resp_line!r}")


async def _handle_socks5_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter, auth: RelayAuth):
    client_peer = writer.get_extra_info("peername")
    try:
        user = await _authenticate(reader, writer, auth)
        if not user:
            return

        req = await _parse_request(reader)
        if not req:
            await _send_response(writer, RESP_CMD_NOT_SUPPORTED)
            return

        bind_addr = writer.get_extra_info("sockname") or ("0.0.0.0", 0)
        await _send_response(writer, RESP_SUCCESS, bind_addr=bind_addr)

        upstream = user["upstream"]
        upstream_reader, upstream_writer = await _connect_to_upstream(upstream)

        cmd, addr, port = req

        if upstream["protocol"] == "socks5":
            # Send CONNECT to upstream SOCKS5
            try:
                ip_bytes = socket.inet_aton(addr)
                upstream_writer.write(bytes([SOCKS_VERSION, CMD_CONNECT, 0x00, ADDR_IPV4]))
                upstream_writer.write(ip_bytes)
                upstream_writer.write(struct.pack(">H", port))
            except Exception:
                dlen = len(addr)
                upstream_writer.write(bytes([SOCKS_VERSION, CMD_CONNECT, 0x00, ADDR_DOMAIN]))
                upstream_writer.write(bytes([dlen]))
                upstream_writer.write(addr.encode("utf-8"))
                upstream_writer.write(struct.pack(">H", port))
            await upstream_writer.drain()

            resp = await _read_exact(upstream_reader, 10)
            if resp[1] != RESP_SUCCESS:
                log.warning(f"upstream refused: {resp[1]:#x}")
                upstream_writer.close()
                return

        elif upstream["protocol"] in ("http", "https"):
            try:
                await _send_http_connect_to_upstream(upstream, addr, port, upstream_reader, upstream_writer)
            except Exception as e:
                log.warning(f"upstream HTTP CONNECT failed: {e}")
                upstream_writer.close()
                return

        async def pipe(r, w):
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
            pipe(reader, upstream_writer),
            pipe(upstream_reader, writer),
            return_exceptions=True,
        )
    except Exception as e:
        log.warning(f"client {client_peer}: {type(e).__name__}: {e}")
    finally:
        try:
            writer.close()
        except Exception:
            pass


async def _handle_http_connect_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter, auth: RelayAuth):
    """HTTP CONNECT proxy handler."""
    client_peer = writer.get_extra_info("peername")
    try:
        # Read request line
        line = await reader.readline()
        if not line:
            return
        line = line.decode("utf-8", errors="replace").strip()

        parts = line.split(" ")
        if len(parts) < 2 or parts[0] != "CONNECT":
            writer.write(b"HTTP/1.1 400 Bad Request\r\n\r\n")
            await writer.drain()
            return

        target = parts[1]
        # Parse auth from headers
        username = None
        password = None
        while True:
            header_line = await reader.readline()
            if not header_line:
                return
            header_line = header_line.decode("utf-8", errors="replace").strip()
            if not header_line:
                break
            if header_line.lower().startswith("proxy-authorization:"):
                auth_str = header_line.split(":", 1)[1].strip()
                if auth_str.lower().startswith("basic "):
                    try:
                        decoded = base64.b64decode(auth_str[6:]).decode("utf-8")
                        username, password = decoded.split(":", 1)
                    except Exception:
                        pass

        if not username or not password:
            writer.write(b"HTTP/1.1 407 Proxy Authentication Required\r\n")
            writer.write(b'Proxy-Authenticate: Basic realm="styxproxy"\r\n\r\n')
            await writer.drain()
            return

        user = await auth.verify(username, password)
        if not user:
            writer.write(b"HTTP/1.1 407 Proxy Authentication Required\r\n\r\n")
            await writer.drain()
            return

        upstream = user["upstream"]
        upstream_reader, upstream_writer = await _connect_to_upstream(upstream)

        target_host, _, target_port = target.rpartition(":")
        try:
            target_port = int(target_port)
        except ValueError:
            return

        if upstream["protocol"] == "socks5":
            # SOCKS5 handshake already done in _connect_to_upstream; just send CONNECT
            try:
                ip_bytes = socket.inet_aton(target_host)
                upstream_writer.write(bytes([SOCKS_VERSION, CMD_CONNECT, 0x00, ADDR_IPV4]))
                upstream_writer.write(ip_bytes)
                upstream_writer.write(struct.pack(">H", target_port))
            except Exception:
                dlen = len(target_host)
                upstream_writer.write(bytes([SOCKS_VERSION, CMD_CONNECT, 0x00, ADDR_DOMAIN]))
                upstream_writer.write(bytes([dlen]))
                upstream_writer.write(target_host.encode("utf-8"))
                upstream_writer.write(struct.pack(">H", target_port))
            await upstream_writer.drain()
            resp = await _read_exact(upstream_reader, 10)
            if resp[1] != RESP_SUCCESS:
                return

        elif upstream["protocol"] in ("http", "https"):
            try:
                await _send_http_connect_to_upstream(
                    upstream, target_host, target_port, upstream_reader, upstream_writer
                )
            except Exception as e:
                log.warning(f"upstream HTTP CONNECT failed: {e}")
                writer.write(b"HTTP/1.1 502 Bad Gateway\r\n\r\n")
                await writer.drain()
                upstream_writer.close()
                return

        # Tell client CONNECT established
        writer.write(b"HTTP/1.1 200 Connection Established\r\n\r\n")
        await writer.drain()

        async def pipe(r, w):
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
            pipe(reader, upstream_writer),
            pipe(upstream_reader, writer),
            return_exceptions=True,
        )
    except Exception as e:
        log.warning(f"client {client_peer}: {type(e).__name__}: {e}")
    finally:
        try:
            writer.close()
        except Exception:
            pass


# ─── Main ─────────────────────────────────────────────────────────────────────


async def main():
    log.info(f"Starting Styxproxy relay on {LISTEN_HOST}")
    log.info(f"  SOCKS5: {LISTEN_PORT_SOCKS}")
    log.info(f"  HTTP:   {LISTEN_PORT_HTTP}")
    log.info(f"  Database: {DATABASE_URL.split('@')[-1]}")

    auth = RelayAuth(DATABASE_URL)
    await auth.refresh()

    socks_server = await asyncio.start_server(
        lambda r, w: _handle_socks5_client(r, w, auth),
        host=LISTEN_HOST,
        port=LISTEN_PORT_SOCKS,
    )
    log.info(f"SOCKS5 listening on {LISTEN_HOST}:{LISTEN_PORT_SOCKS}")

    http_server = await asyncio.start_server(
        lambda r, w: _handle_http_connect_client(r, w, auth),
        host=LISTEN_HOST,
        port=LISTEN_PORT_HTTP,
    )
    log.info(f"HTTP CONNECT listening on {LISTEN_HOST}:{LISTEN_PORT_HTTP}")

    async def refresh_loop():
        while True:
            await asyncio.sleep(30)
            try:
                await auth.refresh()
            except Exception as e:
                log.warning(f"Cache refresh failed: {e}")

    refresh_task = asyncio.create_task(refresh_loop())

    try:
        await asyncio.gather(
            socks_server.serve_forever(),
            http_server.serve_forever(),
            return_exceptions=True,
        )
    finally:
        refresh_task.cancel()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass