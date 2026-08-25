"""Secrets Vault — manage runtime env secrets from the admin dashboard.

Option A of the secrets-management plan: a superadmin-only web UI that
reads/writes the backend's own `.env` file on the VPS.

Design rules:
- Secrets are NEVER returned in plaintext after initial write. Reads return
  masked values (first 4 + last 4 chars) plus metadata.
- Writes are atomic: temp file + os.replace, preserving unrelated lines.
- Every read/write/restart is audit-logged.
- Restarting the API applies changes (systemd); endpoint shells out to
  `systemctl restart styxproxy-api` via a sudoers-scoped helper script.
"""

import asyncio
import logging
import os
import re
import tempfile
from pathlib import Path

from fastapi import APIRouter, Body, Depends, HTTPException, status

from app.config import get_settings
from app.services.audit import log_audit_event
from app.services.permissions import require_permission

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/api/admin/secrets", tags=["admin-secrets"])

ENV_PATH = Path(os.environ.get("STYXPROXY_ENV_FILE", "/opt/styxproxy/backend/.env"))

# Keys that must never be edited or exposed through the vault even by accident.
FORBIDDEN_PATTERNS = re.compile(r"^(DATABASE_URL|ADMIN_TOKEN|JWT_SECRET|SECRET_KEY|OPS_JWT_SECRET)$", re.IGNORECASE)

# Known keys grouped for the UI. Anything else on file shows under "Other".
KNOWN_GROUPS: dict[str, list[str]] = {
    "Payments": [
        "FLUTTERWAVE_SECRET_KEY",
        "FLUTTERWAVE_PUBLIC_KEY",
        "FLUTTERWAVE_WEBHOOK_SECRET",
        "PAYSTACK_SECRET_KEY",
        "NOWPAYMENTS_API_KEY",
        "NOWPAYMENTS_IPN_SECRET",
        "NOWPAYMENTS_BASE_URL",
    ],
    "Providers": [
        "PROXY_SELLER_API_KEY",
        "DATAIMPULSE_API_KEY",
    ],
    "Messaging": [
        "WHATSAPP_ACCESS_TOKEN",
        "WHATSAPP_PHONE_NUMBER_ID",
        "TELEGRAM_BOT_TOKEN",
    ],
    "Email": ["SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASSWORD", "FROM_EMAIL"],
    "Integrations": ["MINIMAX_API_KEY", "THEOREM_REACH_WEBHOOK_SECRET"],
}


def _mask(value: str) -> str:
    if len(value) <= 8:
        return "•" * len(value)
    return f"{value[:4]}••••••••{value[-4:]}"


def _parse_env(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        val = val.strip().strip('"').strip("'")
        # FROM_EMAIL=Styxproxy <noreply@...> has no quotes; keep raw remainder
        if not val and line.count("=") > 1:
            val = line.split("=", 1)[1].strip()
        out[key.strip()] = val
    return out


def _read_env_file() -> dict[str, str]:
    if not ENV_PATH.exists():
        return {}
    return _parse_env(ENV_PATH.read_text())


def _write_env_file(updates: dict[str, str | None]) -> int:
    """Set/unset keys in .env atomically. None = remove key. Returns changed count."""
    lines = ENV_PATH.read_text().splitlines() if ENV_PATH.exists() else []
    changed = 0
    seen: set[str] = set()
    new_lines: list[str] = []

    for line in lines:
        stripped = line.strip()
        key = stripped.split("=", 1)[0].strip() if ("=" in stripped and not stripped.startswith("#")) else None
        if key and key in updates:
            new_val = updates[key]
            seen.add(key)
            if new_val is None:
                changed += 1
                continue  # drop the line entirely
            quote = '"' if (" " in new_val or "<" in new_val) and not new_val.startswith('"') else ""
            new_lines.append(f"{key}={quote}{new_val}{quote}" if quote else f"{key}={new_val}")
            changed += 1
        else:
            new_lines.append(line)

    # Append keys that weren't already present
    for key, val in updates.items():
        if key not in seen and val is not None:
            quote = '"' if (" " in val or "<" in val) and not val.startswith('"') else ""
            new_lines.append(f"{key}={quote}{val}{quote}" if quote else f"{key}={val}")
            changed += 1

    fd, tmp = tempfile.mkstemp(dir=str(ENV_PATH.parent), prefix=".env.tmp")
    with os.fdopen(fd, "w") as f:
        f.write("\n".join(new_lines).rstrip("\n") + "\n")
    os.replace(tmp, ENV_PATH)
    try:
        os.chmod(ENV_PATH, 0o600)
    except OSError:
        pass
    return changed


def _validate_key(key: str) -> None:
    if not re.match(r"^[A-Z][A-Z0-9_]{2,64}$", key):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid key name: {key}")
    if FORBIDDEN_PATTERNS.match(key):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"{key} is protected and cannot be modified via the vault",
        )


@router.get("", dependencies=[Depends(require_permission("admin.system.secrets.read"))])
async def list_secrets():
    """List all env keys with masked values + known-group organization."""
    env = _read_env_file()

    groups: dict[str, list[dict]] = {}
    assigned: set[str] = set()
    for group_name, keys in KNOWN_GROUPS.items():
        rows = []
        for k in keys:
            if k in env:
                rows.append({"key": k, "masked": _mask(env[k]), "set": bool(env[k])})
                assigned.add(k)
        if rows:
            groups[group_name] = rows

    other = sorted(
        ({"key": k, "masked": _mask(v), "set": bool(v)} for k, v in env.items() if k not in assigned),
        key=lambda r: r["key"],
    )

    return {
        "groups": groups,
        "other": other,
        "env_path": str(ENV_PATH),
    }


@router.put("", dependencies=[Depends(require_permission("admin.system.secrets.write", totp_required=True))])
async def update_secret(
    payload: dict = Body(...),
    current_admin: dict = Depends(require_permission("admin.system.secrets.write", totp_required=True)),
):
    """Set one secret. Body: {key, value}."""
    key = (payload.get("key") or "").strip().upper() if isinstance(payload, dict) else ""
    value = payload.get("value") if isinstance(payload, dict) else None
    _validate_key(key)
    if value is None or value == "":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="value is required")

    changed = _write_env_file({key: str(value)})
    await log_audit_event(
        db_session=None,
        event_type="secrets_vault_write",
        details={"key": key, "changed": changed, "by": current_admin.get("email", "unknown")},
    )
    return {"status": "ok", "key": key, "restart_required": True}


@router.delete("/{key}", dependencies=[Depends(require_permission("admin.system.secrets.write", totp_required=True))])
async def delete_secret(key: str):
    """Unset a secret (removes it from .env)."""
    key = key.strip().upper()
    _validate_key(key)
    changed = _write_env_file({key: None})
    await log_audit_event(db_session=None, event_type="secrets_vault_delete", details={"key": key})
    if changed == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{key} not found in .env")
    return {"status": "ok", "key": key, "restart_required": True}


RESTART_SCRIPT = "/usr/local/bin/styxproxy-restart-api"


@router.post("/restart", dependencies=[Depends(require_permission("admin.system.secrets.restart", totp_required=True))])
async def restart_api():
    """Restart styxproxy-api so newly saved secrets take effect.

    Requires a passwordless-sudoers entry for the service user:
      styxproxy ALL=(root) NOPASSWD: /usr/local/bin/styxproxy-restart-api
    where that script runs `systemctl restart styxproxy-api`.
    """
    if not Path(RESTART_SCRIPT).exists():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Restart helper not installed. On the VPS run: "
                "printf '#!/bin/bash\\nsystemctl restart styxproxy-api\\n' > /usr/local/bin/styxproxy-restart-api "
                "&& chmod +x /usr/local/bin/styxproxy-restart-api"
            ),
        )
    proc = await asyncio.create_subprocess_exec(
        "sudo",
        "-n",
        RESTART_SCRIPT,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
    ok = proc.returncode == 0
    await log_audit_event(
        db_session=None,
        event_type="secrets_vault_restart",
        details={"success": ok, "stderr": stderr.decode()[:200] if not ok else ""},
    )
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Restart failed: {stderr.decode()[:200]}",
        )
    return {"status": "restarting"}
