"""Styxproxy SOCKS5 + HTTP Relay (Postgres-backed, with bandwidth metering)"""
import asyncio
import base64
import logging
import os
import socket
import struct
import sys
from collections import defaultdict
from pathlib import Path
from typing import Optional
import asyncpg
from cryptography.fernet import Fernet, InvalidToken
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=LOG_LEVEL, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
log = logging.getLogger("styxproxy-relay")


def _load_env_file(path: str = "/opt/styxproxy/.env") -> dict:
    """Read KEY=VALUE pairs from the shared env file.

    Parsed by hand because the file contains unquoted values with spaces and
    commas that the shell cannot `source`. Never log the contents.
    """
    values = {}
    p = Path(path)
    if not p.exists():
        return values
    for line in p.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        values[key.strip()] = val.strip().strip('"').strip("'")
    return values


_ENV_CACHE = _load_env_file()


def _cred_encryption_key() -> Optional[str]:
    """Fernet key for decrypting styxproxy_password, or None if unavailable."""
    key = os.getenv("CRED_ENCRYPTION_KEY") or _ENV_CACHE.get("CRED_ENCRYPTION_KEY")
    return key or None


# Fernet tokens are urlsafe-base64 of a 0x80 version byte, so they always start
# with these four characters. This is how we tell an encrypted password from a
# legacy raw-plaintext one without attempting a decrypt first.
FERNET_PREFIX = b"gAAAA"


def _build_fernet() -> Optional[Fernet]:
    """Build a Fernet instance from CRED_ENCRYPTION_KEY, or None if unusable.

    Returning None is safe: encrypted credentials are then rejected loudly at
    auth rather than being compared against their own ciphertext.
    """
    key = _cred_encryption_key()
    if not key:
        log.error(
            "CRED_ENCRYPTION_KEY not set for the relay — encrypted credentials "
            "cannot be authenticated. Check the unit's Environment/EnvironmentFile.",
        )
        return None
    try:
        return Fernet(key.encode("ascii"))
    except (ValueError, TypeError) as e:
        log.error("CRED_ENCRYPTION_KEY is malformed (not a Fernet key): %s", e)
        return None


def decrypt_stored_password(raw: Optional[bytes], fernet: Optional[Fernet]) -> Optional[str]:
    """Return the customer-facing plaintext for a stored styxproxy_password.

    The column holds either Fernet ciphertext (written via
    StyxproxyCredential.set_password) or raw UTF-8 plaintext (written by
    catalog.py / proxy_management.py before they were corrected, and by every
    row that predates the encrypted column). Comparing the customer's typed
    password against the raw column value therefore rejects every modern
    credential — the ciphertext is ~120 bytes and can never equal a 16-char
    password.

    Shapes are distinguished by the Fernet prefix, NOT by "decrypt failed":
    a value carrying the prefix IS ciphertext, so a decrypt failure means the
    key is wrong or the value is tampered, and we return None rather than
    silently comparing against the blob. Falling back to plaintext there would
    reproduce the exact bug this function prevents.

    Returns None when the value is absent or undecryptable — the caller must
    then refuse to authenticate rather than guess.
    """
    if not raw:
        return None
    if isinstance(raw, str):
        raw = raw.encode("utf-8")

    if raw.startswith(FERNET_PREFIX):
        if fernet is None:
            log.error(
                "Cannot decrypt %d-byte credential: CRED_ENCRYPTION_KEY not "
                "configured for the relay. Refusing to authenticate.",
                len(raw),
            )
            return None
        try:
            return fernet.decrypt(raw).decode("utf-8")
        except (InvalidToken, ValueError, UnicodeDecodeError) as e:
            log.error("Failed to decrypt credential (wrong key or tampered?): %s", e)
            return None

    # No Fernet prefix -> legacy raw plaintext row. Keep it working so existing
    # customers are not logged out by this fix.
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        log.error(
            "Credential is neither Fernet ciphertext nor valid UTF-8 — refusing "
            "to authenticate. Length=%d.",
            len(raw),
        )
        return None


# ── Bandwidth Tracker ─────────────────────────────────────────────────────────────

class BandwidthTracker:
    """Per-user byte counter. Flushes to styxproxy_relay_entries.bytes_used every 30s."""

    FLUSH_INTERVAL = 30

    def __init__(self, dsn: str):
        self.dsn = dsn
        self._stats: dict = {}
        self._lock = asyncio.Lock()
        self._task = None

    async def start(self):
        self._task = asyncio.create_task(self._loop())
        log.info("BandwidthTracker started (flush every %ds)", self.FLUSH_INTERVAL)

    async def stop(self):
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        await self._flush()

    def record(self, username: str, n: int):
        if username and n > 0:
            loop = asyncio.get_event_loop()
            loop.call_soon_threadsafe(self._add, username, n)

    def _add(self, username: str, n: int):
        self._stats[username] = self._stats.get(username, 0) + n

    async def _loop(self):
        while True:
            await asyncio.sleep(self.FLUSH_INTERVAL)
            try:
                await self._flush()
            except Exception as e:
                log.warning("BW flush error: %s", e)

    async def _flush(self):
        async with self._lock:
            if not self._stats:
                return
            snapshot = dict(self._stats)
            self._stats.clear()
        conn = await asyncpg.connect(self.dsn, ssl=False)
        try:
            for username, byte_count in snapshot.items():
                await conn.execute(
                    """
                    UPDATE styxproxy_relay_entries r
                    SET bytes_used = r.bytes_used + $1,
                        last_used_at = NOW()
                    FROM styxproxy_credentials c
                    WHERE c.styxproxy_username = $2
                      AND c.id = r.credential_id
                      AND c.status = 'active'
                    """,
                    byte_count, username,
                )
            log.info("BW flushed: %s",
                ", ".join("%s: %dB" % (u, n) for u, n in snapshot.items()))
        finally:
            await conn.close()

    async def flush_session(self, username: str):
        """Flush stats for one user immediately on session end."""
        async with self._lock:
            count = self._stats.pop(username, 0)
        if count > 0:
            conn = await asyncpg.connect(self.dsn, ssl=False)
            try:
                await conn.execute(
                    """
                    UPDATE styxproxy_relay_entries r
                    SET bytes_used = r.bytes_used + $1, last_used_at = NOW()
                    FROM styxproxy_credentials c
                    WHERE c.styxproxy_username = $2 AND c.id = r.credential_id
                    """,
                    count, username,
                )
                log.info("BW session [%s]: %d bytes", username, count)
            finally:
                await conn.close()


# ── Auth ─────────────────────────────────────────────────────────────────────────

class RelayAuth:
    def __init__(self, dsn: str, ttl_seconds: int = 30):
        self.dsn = dsn
        self.ttl = ttl_seconds
        self._cache: dict = {}
        self._user_to_upstream: dict = {}
        self._expires_at: float = 0
        self._lock = asyncio.Lock()

    async def refresh(self):
        conn = await asyncpg.connect(self.dsn, ssl=False)
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
                    r.region,
                    r.id AS relay_entry_id,
                    c.id AS credential_id
                FROM styxproxy_credentials c
                LEFT JOIN styxproxy_relay_entries r ON c.id = r.credential_id
                WHERE c.status = 'active'
                """
            )
            new_passwords = {}
            new_upstreams = {}
            now = asyncio.get_event_loop().time()
            fernet = _build_fernet()
            undecryptable = 0
            for row in rows:
                username = row["styxproxy_username"]
                cred_status = row.get("status") or "active"
                if cred_status != "active":
                    continue
                # DECRYPT before caching. Caching the raw column value compares
                # the customer's 16-char password against ~120 bytes of Fernet
                # ciphertext and rejects every encrypted credential.
                pw = decrypt_stored_password(row["styxproxy_password"], fernet)
                if pw:
                    new_passwords[username] = pw.encode("utf-8")
                elif row["styxproxy_password"]:
                    # Present but unusable — count it so a key misconfiguration
                    # is visible in the log instead of silently rejecting users.
                    undecryptable += 1
                    log.warning(
                        "Credential %s has an undecryptable password — it will be "
                        "rejected at auth.", username,
                    )
                relay_status = row.get("relay_status")
                if relay_status and relay_status != "active":
                    continue
                # Prefer relay_entries, fall back to credentials columns
                upstream_host = (
                    row.get("upstream_host") or row.get("upstream_proxy_ip") or ""
                )
                upstream_port = (
                    row.get("upstream_port") or row.get("upstream_proxy_port") or 0
                )
                upstream_user = (
                    row.get("upstream_user") or row.get("provider_username") or ""
                )
                upstream_pass = (
                    row.get("upstream_pass") or row.get("provider_password") or ""
                )
                upstream_protocol = (
                    row.get("upstream_protocol") or row.get("protocol") or "socks5"
                )
                if upstream_host:
                    new_upstreams[username] = {
                        "host": upstream_host,
                        "port": upstream_port,
                        "user": upstream_user,
                        "pass": upstream_pass,
                        "protocol": upstream_protocol,
                        "credential_id": row.get("credential_id"),
                        "relay_entry_id": row.get("relay_entry_id"),
                    }
            async with self._lock:
                self._cache = new_passwords
                self._user_to_upstream = new_upstreams
                self._expires_at = now + self.ttl
            log.debug("Auth cache refreshed: %d users", len(new_passwords))
            if undecryptable:
                # Surfaced at WARNING on every refresh: a key problem must be
                # visible in the log, not inferred from customers being rejected.
                log.warning(
                    "Auth cache: %d credential(s) had a password that could not be "
                    "decrypted and will be REJECTED. Check CRED_ENCRYPTION_KEY.",
                    undecryptable,
                )
        finally:
            await conn.close()

    async def verify(self, username: str, password: str) -> Optional[dict]:
        now = asyncio.get_event_loop().time()
        if now > self._expires_at:
            await self.refresh()
        async with self._lock:
            cached_pw = self._cache.get(username)
            upstream = self._user_to_upstream.get(username)
        if cached_pw is None or upstream is None:
            return None
        if cached_pw != password.encode():
            return None
        return {"username": username, "upstream": upstream}


# ── Low-level helpers ───────────────────────────────────────────────────────────

SOCKS_VERSION = 0x05
NO_AUTH_METHOD = 0x00
USER_PASS_METHOD = 0x02
NO_ACCEPTABLE_METHOD = 0xFF
CMD_CONNECT = 0x01
ADDR_IPV4 = 0x01
ADDR_DOMAIN = 0x03
ADDR_IPV6 = 0x04
RESP_SUCCESS = 0x00
USERNAME_PASSWD_VERSION = 0x01
AUTH_SUCCESS = 0x00


async def _read_exact(reader, n):
    return await reader.readexactly(n)


async def _send_response(writer, reply, bind_addr=("0.0.0.0", 0)):
    try:
        ip_bytes = socket.inet_aton(bind_addr[0])
        writer.write(bytes([SOCKS_VERSION, reply, 0x00, ADDR_IPV4]))
        writer.write(ip_bytes)
        writer.write(struct.pack(">H", int(bind_addr[1])))
    except Exception:
        writer.write(bytes([SOCKS_VERSION, reply, 0x00, ADDR_IPV4]))
        writer.write(socket.inet_aton("0.0.0.0"))
        writer.write(struct.pack(">H", 0))
    await writer.drain()


async def _authenticate(reader, writer, auth):
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
    plen = (await _read_exact(reader, 1))[0]
    pwd = (await _read_exact(reader, plen)).decode("utf-8", errors="replace")
    user = await auth.verify(uname, pwd)
    if not user:
        writer.write(bytes([USERNAME_PASSWD_VERSION, 0x01]))
        await writer.drain()
        log.warning("Auth failed for %s", uname)
        return None
    writer.write(bytes([USERNAME_PASSWD_VERSION, AUTH_SUCCESS]))
    await writer.drain()
    log.info("Auth OK: %s -> upstream %s:%s",
             uname, user["upstream"]["host"], user["upstream"]["port"])
    return user


async def _parse_request(reader):
    header = await _read_exact(reader, 4)
    ver, cmd, _rsv, atype = header[0], header[1], header[2], header[3]
    if ver != SOCKS_VERSION or cmd != CMD_CONNECT:
        return None
    if atype == ADDR_IPV4:
        addr = socket.inet_ntoa(await _read_exact(reader, 4))
    elif atype == ADDR_DOMAIN:
        addr = (await _read_exact(reader, (await _read_exact(reader, 1))[0])).decode("utf-8", errors="replace")
    elif atype == ADDR_IPV6:
        addr = socket.inet_ntop(socket.AF_INET6, await _read_exact(reader, 16))
    else:
        return None
    port = struct.unpack(">H", await _read_exact(reader, 2))[0]
    return (cmd, addr, port)


async def _connect_to_upstream(upstream):
    host, port = upstream["host"], upstream["port"]
    protocol = upstream["protocol"]
    user, password = upstream["user"], upstream["pass"]
    log.debug("Connecting to upstream %s:%s via %s", host, port, protocol)
    if protocol == "socks5":
        reader, writer = await asyncio.open_connection(host, port)
        writer.write(bytes([SOCKS_VERSION, 1, USER_PASS_METHOD]))
        await writer.drain()
        resp = await _read_exact(reader, 2)
        if resp[0] != SOCKS_VERSION or resp[1] != USER_PASS_METHOD:
            writer.close()
            raise ValueError("upstream rejected auth: %s" % resp.hex())
        ub, pb = user.encode("utf-8"), password.encode("utf-8")
        writer.write(bytes([USERNAME_PASSWD_VERSION, len(ub)]))
        writer.write(ub)
        writer.write(bytes([len(pb)]))
        writer.write(pb)
        await writer.drain()
        auth_resp = await _read_exact(reader, 2)
        if auth_resp[1] != AUTH_SUCCESS:
            writer.close()
            raise ConnectionError("upstream auth failed: %s" % auth_resp.hex())
        return reader, writer
    else:  # http / https
        reader, writer = await asyncio.open_connection(host, port)
        return reader, writer


async def _pipe_counting(r, w, username=None, tracker=None, direction=""):
    """Pipe with byte counting."""
    bytes_count = 0
    try:
        while True:
            data = await r.read(4096)
            if not data:
                break
            bytes_count += len(data)
            w.write(data)
            await w.drain()
    except Exception:
        pass
    finally:
        if not w.is_closing():
            w.close()
        if tracker and username and bytes_count > 0:
            tracker.record(username, bytes_count)
            log.debug("BW %s [%s]: %d bytes", direction, username, bytes_count)


# ── SOCKS5 handler ─────────────────────────────────────────────────────────────

async def _handle_socks5_client(reader, writer, auth, tracker):
    client_peer = writer.get_extra_info("peername")
    try:
        user = await _authenticate(reader, writer, auth)
        if not user:
            return
        username = user["username"]
        req = await _parse_request(reader)
        if not req:
            await _send_response(writer, 0x07)
            return
        bind_addr = writer.get_extra_info("sockname") or ("0.0.0.0", 0)
        await _send_response(writer, RESP_SUCCESS, bind_addr=bind_addr)
        upstream = user["upstream"]
        upstream_reader, upstream_writer = await _connect_to_upstream(upstream)
        cmd, addr, port = req
        if upstream["protocol"] == "socks5":
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
                log.warning("upstream refused CONNECT: 0x%x", resp[1])
                upstream_writer.close()
                return
        else:  # http/https
            creds = base64.b64encode(("%s:%s" % (upstream["user"], upstream["pass"])).encode()).decode()
            req_str = "CONNECT %s:%d HTTP/1.1\r\nHost: %s:%d\r\nProxy-Authorization: Basic %s\r\n\r\n" % (
                addr, port, addr, port, creds)
            upstream_writer.write(req_str.encode())
            await upstream_writer.drain()
            resp_line = await upstream_reader.readline()
            if b" 200 " not in resp_line:
                log.warning("upstream HTTP CONNECT failed: %r", resp_line)
                upstream_writer.close()
                return
            while True:
                hdr = await upstream_reader.readline()
                if not hdr or hdr == b"\r\n":
                    break
        await asyncio.gather(
            _pipe_counting(reader, upstream_writer, username, tracker, "DOWN"),
            _pipe_counting(upstream_reader, writer, username, tracker, "UP"),
            return_exceptions=True,
        )
        if username:
            await tracker.flush_session(username)
    except Exception as e:
        log.warning("client %s: %s: %s", client_peer, type(e).__name__, e)
    finally:
        try:
            writer.close()
        except Exception:
            pass


# ── HTTP CONNECT handler ────────────────────────────────────────────────────────

async def _handle_http_connect_client(reader, writer, auth, tracker):
    client_peer = writer.get_extra_info("peername")
    try:
        line = await reader.readline()
        if not line:
            return
        line_str = line.decode("utf-8", errors="replace").strip()
        parts = line_str.split(" ")
        if len(parts) < 2 or parts[0] != "CONNECT":
            writer.write(b"HTTP/1.1 400 Bad Request\r\n\r\n")
            await writer.drain()
            return
        target = parts[1]
        username = None
        password = None
        while True:
            hdr = await reader.readline()
            if not hdr:
                return
            hdr_str = hdr.decode("utf-8", errors="replace").strip()
            if not hdr_str:
                break
            if hdr_str.lower().startswith("proxy-authorization:"):
                auth_str = hdr_str.split(":", 1)[1].strip()
                if auth_str.lower().startswith("basic "):
                    try:
                        decoded = base64.b64decode(auth_str[6:]).decode("utf-8")
                        username, password = decoded.split(":", 1)
                    except Exception:
                        pass
        if not username or not password:
            writer.write(b"HTTP/1.1 407 Proxy Auth Required\r\nProxy-Authenticate: Basic realm=\"styxproxy\"\r\n\r\n")
            await writer.drain()
            return
        user = await auth.verify(username, password)
        if not user:
            writer.write(b"HTTP/1.1 407 Proxy Auth Required\r\nProxy-Authenticate: Basic realm=\"styxproxy\"\r\n\r\n")
            await writer.drain()
            return
        upstream_reader, upstream_writer = await _connect_to_upstream(user["upstream"])
        target_host, _, target_port_str = target.rpartition(":")
        try:
            target_port = int(target_port_str)
        except ValueError:
            return
        if user["upstream"]["protocol"] == "socks5":
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
        else:  # http/https upstream
            creds = base64.b64encode(("%s:%s" % (user["upstream"]["user"], user["upstream"]["pass"])).encode()).decode()
            req_str = "CONNECT %s:%d HTTP/1.1\r\nHost: %s:%d\r\nProxy-Authorization: Basic %s\r\n\r\n" % (
                target_host, target_port, target_host, target_port, creds)
            upstream_writer.write(req_str.encode())
            await upstream_writer.drain()
            resp_line = await upstream_reader.readline()
            if b" 200 " not in resp_line:
                log.warning("upstream HTTP CONNECT failed: %r", resp_line)
                upstream_writer.close()
                writer.write(b"HTTP/1.1 502 Bad Gateway\r\n\r\n")
                await writer.drain()
                return
            while True:
                hdr = await upstream_reader.readline()
                if not hdr or hdr == b"\r\n":
                    break
        writer.write(b"HTTP/1.1 200 Connection Established\r\n\r\n")
        await writer.drain()
        await asyncio.gather(
            _pipe_counting(reader, upstream_writer, username, tracker, "DOWN"),
            _pipe_counting(upstream_reader, writer, username, tracker, "UP"),
            return_exceptions=True,
        )
        if username:
            await tracker.flush_session(username)
    except Exception as e:
        log.warning("client %s: %s: %s", client_peer, type(e).__name__, e)
    finally:
        try:
            writer.close()
        except Exception:
            pass


# ── Main ───────────────────────────────────────────────────────────────────────

LISTEN_HOST = os.getenv("LISTEN_HOST", "0.0.0.0")
LISTEN_PORT_SOCKS = int(os.getenv("LISTEN_PORT_SOCKS", "11080"))
LISTEN_PORT_HTTP = int(os.getenv("LISTEN_PORT_HTTP", "18080"))

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


async def main():
    log.info("Starting Styxproxy relay on %s", LISTEN_HOST)
    log.info("  SOCKS5: %s:%s", LISTEN_HOST, LISTEN_PORT_SOCKS)
    log.info("  HTTP:   %s:%s", LISTEN_HOST, LISTEN_PORT_HTTP)
    log.info("  Database: %s", DATABASE_URL.split("@")[-1])

    auth = RelayAuth(DATABASE_URL)
    await auth.refresh()

    tracker = BandwidthTracker(DATABASE_URL)
    await tracker.start()

    socks_server = await asyncio.start_server(
        lambda r, w: _handle_socks5_client(r, w, auth, tracker),
        host=LISTEN_HOST, port=LISTEN_PORT_SOCKS,
    )
    log.info("SOCKS5 listening on %s:%s", LISTEN_HOST, LISTEN_PORT_SOCKS)

    http_server = await asyncio.start_server(
        lambda r, w: _handle_http_connect_client(r, w, auth, tracker),
        host=LISTEN_HOST, port=LISTEN_PORT_HTTP,
    )
    log.info("HTTP CONNECT listening on %s:%s", LISTEN_HOST, LISTEN_PORT_HTTP)

    async def refresh_loop():
        while True:
            await asyncio.sleep(30)
            try:
                await auth.refresh()
            except Exception as e:
                log.warning("Auth cache refresh failed: %s", e)

    refresh_task = asyncio.create_task(refresh_loop())

    try:
        await asyncio.gather(
            socks_server.serve_forever(),
            http_server.serve_forever(),
            refresh_task,
            return_exceptions=True,
        )
    finally:
        refresh_task.cancel()
        try:
            await refresh_task
        except asyncio.CancelledError:
            pass
        await tracker.stop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("Relay shutting down")
