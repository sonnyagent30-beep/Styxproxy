"""
Dante Control API - Styxproxy (Contabo / Interserver)
=====================================================

Manages SOCKS5 users for the local Dante server + the SOCKS5 auth wrapper.
Auth backend: a simple JSON file (`/etc/dante/users.json`) shared with the
socks-auth-proxy container.

Format:
{
  "<username>": {
    "password":     "<plaintext, since SOCKS5 protocol has no public-key auth>",
    "upstream_ip":  "1.2.3.4",
    "upstream_port": 8080,
    "customer_id":  "...",   # optional
    "order_id":     "..."    # optional
  }
}

The SOCKS5 auth wrapper (socks-auth-proxy) reads this file directly on every
connection. We also expose API endpoints for the Styxproxy backend to call.

API endpoints:
    POST   /api/credentials          register new user
    POST   /api/credentials/rotate   rotate password (+ optionally upstream)
    DELETE /api/credentials/{u}      revoke user
    POST   /api/credentials/update-upstream  rotate upstream IP only
    GET    /api/users                list users (no passwords)
    POST   /api/auth/verify          verify user/password (used by admin dashboard)
    GET    /health                   liveness
    GET    /stats                    active user count
"""

import json
import logging
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=LOG_LEVEL, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
log = logging.getLogger("dante-control")

app = FastAPI(title="Dante Control API", version="1.0.0")

USERS_FILE = Path(os.getenv("USERS_FILE", "/etc/dante/users.json"))
VPS_LABEL = os.getenv("VPS_LABEL", "unknown")
PUBLIC_IP = os.getenv("PUBLIC_IP", "")
DANTE_PORT = int(os.getenv("DANTE_PORT", "1080"))


# ─── Models ───────────────────────────────────────────────────────────────────

class CredentialCreate(BaseModel):
    username: str
    password: str
    upstream_ip: str
    upstream_port: int
    customer_id: str | None = None
    order_id: str | None = None


class CredentialRotate(BaseModel):
    username: str
    new_password: str
    new_upstream_ip: str | None = None
    new_upstream_port: int | None = None


class UpstreamUpdate(BaseModel):
    username: str
    upstream_ip: str
    upstream_port: int


class AuthVerify(BaseModel):
    username: str
    password: str


# ─── User DB helpers ──────────────────────────────────────────────────────────


def _read_users() -> dict:
    """Read users.json. Returns {username: userdict}."""
    if not USERS_FILE.exists():
        return {}
    try:
        with USERS_FILE.open("r") as f:
            return json.load(f)
    except Exception as e:
        log.error(f"Failed to read {USERS_FILE}: {e}")
        return {}


def _write_users(users: dict) -> None:
    """Write users.json atomically (write tmp, then rename)."""
    USERS_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = USERS_FILE.with_suffix(".tmp")
    with tmp.open("w") as f:
        json.dump(users, f, indent=2)
    os.replace(tmp, USERS_FILE)
    try:
        os.chmod(USERS_FILE, 0o640)
    except Exception:
        pass


def _find_user(username: str) -> dict | None:
    return _read_users().get(username)


# ─── Routes ───────────────────────────────────────────────────────────────────


@app.get("/health")
async def health():
    users = _read_users()
    return {
        "status": "healthy",
        "service": "dante-control-api",
        "version": "1.0.0",
        "vps_label": VPS_LABEL,
        "public_ip": PUBLIC_IP,
        "users": len(users),
    }


@app.get("/stats")
async def stats():
    return {
        "vps_label": VPS_LABEL,
        "public_ip": PUBLIC_IP,
        "dante_port": DANTE_PORT,
        "total_users": len(_read_users()),
    }


@app.post("/api/credentials")
async def create_credential(cred: CredentialCreate):
    """Register a new SOCKS5 user. Writes to shared users.json."""
    users = _read_users()
    if cred.username in users:
        raise HTTPException(status.HTTP_409_CONFLICT, f"User {cred.username} already exists")

    users[cred.username] = {
        "password": cred.password,
        "upstream_ip": cred.upstream_ip,
        "upstream_port": cred.upstream_port,
        "customer_id": cred.customer_id,
        "order_id": cred.order_id,
    }
    _write_users(users)
    log.info(
        f"Created user {cred.username} → upstream={cred.upstream_ip}:{cred.upstream_port} "
        f"(cust={cred.customer_id}, order={cred.order_id})"
    )
    return {
        "username": cred.username,
        "upstream_ip": cred.upstream_ip,
        "upstream_port": cred.upstream_port,
        "dante_port": DANTE_PORT,
        "auth_proxy_port": 1081,
        "vps_label": VPS_LABEL,
        "public_ip": PUBLIC_IP,
    }


@app.post("/api/credentials/rotate")
async def rotate_credential(cred: CredentialRotate):
    """Update password (and optionally upstream) for an existing user."""
    users = _read_users()
    if cred.username not in users:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"User {cred.username} not found")

    users[cred.username]["password"] = cred.new_password
    if cred.new_upstream_ip is not None:
        users[cred.username]["upstream_ip"] = cred.new_upstream_ip
    if cred.new_upstream_port is not None:
        users[cred.username]["upstream_port"] = cred.new_upstream_port
    _write_users(users)
    log.info(f"Rotated password for {cred.username}")
    return {"username": cred.username, "rotated": True}


@app.delete("/api/credentials/{username}")
async def revoke_credential(username: str):
    """Remove a user."""
    users = _read_users()
    if username not in users:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"User {username} not found")
    del users[username]
    _write_users(users)
    log.info(f"Revoked user {username}")
    return {"username": username, "revoked": True}


@app.post("/api/credentials/update-upstream")
async def update_upstream(upd: UpstreamUpdate):
    """Update only the upstream proxy (rotate IP without changing password)."""
    users = _read_users()
    if upd.username not in users:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"User {upd.username} not found")
    users[upd.username]["upstream_ip"] = upd.upstream_ip
    users[upd.username]["upstream_port"] = upd.upstream_port
    _write_users(users)
    return {
        "username": upd.username,
        "upstream_ip": upd.upstream_ip,
        "upstream_port": upd.upstream_port,
    }


@app.post("/api/auth/verify")
async def verify_credential(cred: AuthVerify):
    """Verify a credential pair (admin/dashboard use)."""
    user = _find_user(cred.username)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "user not found")
    if user["password"] != cred.password:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid password")
    return {
        "username": cred.username,
        "valid": True,
        "upstream_ip": user.get("upstream_ip"),
        "upstream_port": user.get("upstream_port"),
    }


@app.get("/api/users")
async def list_users():
    """List all users (admin endpoint, no passwords)."""
    users = _read_users()
    return {
        "count": len(users),
        "vps_label": VPS_LABEL,
        "public_ip": PUBLIC_IP,
        "users": [
            {
                "username": k,
                "upstream_ip": v["upstream_ip"],
                "upstream_port": v["upstream_port"],
                "customer_id": v.get("customer_id"),
                "order_id": v.get("order_id"),
            }
            for k, v in users.items()
        ],
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9000)
