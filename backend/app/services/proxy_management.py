"""
Customer proxy management service.

Handles SOCKS5 password rotation, country targeting, sticky sessions,
bandwidth metering queries, and admin operations (suspend, reset, etc).

Design notes:
- Customer-facing endpoints use AsyncSession (SQLAlchemy) — works with the
  existing app/models.py definitions.
- Admin endpoints can also call the relay daemon's metadata via direct psql
  when needed (e.g. bytes_used in styxproxy_relay_entries).
"""

import secrets
import string
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Order, StyxproxyCredential

# ─── Constants ────────────────────────────────────────────────────────────────

# Customer-facing SOCKS5 endpoint (front door for customers)
PROXY_PUBLIC_HOST = "proxy.styxproxy.com"
PROXY_PORT_SOCKS5 = 1080
PROXY_PORT_HTTP = 8080

# Password rotation policy
ROTATIONS_PER_DAY_LIMIT = 3

# Default upstream gateway templates (per pool_type + country)
# Used by provision_credential_relay() to create styxproxy_relay_entries
UPSTREAM_GATEWAYS = {
    "residential": {
        # Rayobyte residential gateway (HTTP CONNECT + Basic auth)
        "host": "la.residential.rayobyte.com",
        "port": 8000,
        "upstream_protocol": "http",  # HTTP CONNECT to upstream
        "upstream_type": "rayobyte_resi",
    },
    "mobile": {
        # Rayobyte mobile gateway — pending Hakan confirmation of exact host
        # Use residential as fallback until mobile gateway discovered
        "host": "la.residential.rayobyte.com",
        "port": 8000,
        "upstream_protocol": "http",
        "upstream_type": "rayobyte_mobile",
    },
    "datacenter": {
        # Static datacenter IPs come from Rayobyte ISP endpoint or Contabo
        # Per-region: US = Interserver, UK = Contabo
        "host": "",  # set per-credential via upstream_proxy_ip
        "port": 1080,
        "upstream_protocol": "socks5",
        "upstream_type": "rayobyte_dc",
    },
    "isp": {
        # Static ISP IPs (US or UK depending on country)
        "host": "",  # set per-credential
        "port": 1080,
        "upstream_protocol": "socks5",
        "upstream_type": "rayobyte_isp",
    },
    "trial": {
        # Trial uses Contabo dante (free trial path)
        "host": "trial.styxproxy.com",
        "port": 8001,
        "upstream_protocol": "socks5",
        "upstream_type": "trial_dante",
    },
}


# ─── Password generation ──────────────────────────────────────────────────────


def generate_proxy_password(length: int = 16) -> str:
    """Generate a random SOCKS5 password (letters+digits, no symbols for copy/paste)."""
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def generate_proxy_username(phone: str) -> str:
    """Generate SOCKS5 username based on phone number (deterministic + unique suffix)."""
    phone_clean = phone.replace("+", "").replace(" ", "").replace("-", "")
    suffix = secrets.token_hex(3)  # 6 hex chars
    return f"sty_{phone_clean[-6:]}_{suffix}"


# ─── Customer endpoints ───────────────────────────────────────────────────────


async def list_customer_credentials(session: AsyncSession, customer_phone: str) -> list[StyxproxyCredential]:
    """Get all credentials belonging to a customer phone."""
    stmt = (
        select(StyxproxyCredential)
        .where(StyxproxyCredential.customer_phone == customer_phone)
        .order_by(StyxproxyCredential.created_at.desc())
    )
    result = await session.execute(stmt)
    return result.scalars().all()


async def get_credential_for_customer(
    session: AsyncSession, credential_id: int, customer_phone: str
) -> Optional[StyxproxyCredential]:
    """Fetch a single credential, scoped to the customer (404 if not theirs)."""
    stmt = select(StyxproxyCredential).where(
        StyxproxyCredential.id == credential_id,
        StyxproxyCredential.customer_phone == customer_phone,
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_credential_usage(session: AsyncSession, credential_id: int, customer_phone: str) -> dict:
    """Get bandwidth usage + recent activity for a customer's credential."""
    cred = await get_credential_for_customer(session, credential_id, customer_phone)
    if not cred:
        return {}

    # Get the most recent active order for this credential
    order_stmt = (
        select(Order).where(Order.styxproxy_credential_id == credential_id).order_by(Order.created_at.desc()).limit(1)
    )
    order = (await session.execute(order_stmt)).scalar_one_or_none()

    gb_total = float(order.data_total_gb) if order and order.data_total_gb else 0.0
    gb_used = float(cred.gb_used) if cred.gb_used else 0.0
    gb_remaining = max(0.0, gb_total - gb_used)
    usage_pct = (gb_used / gb_total * 100) if gb_total > 0 else 0.0

    days_remaining = 0
    if cred.expires_at:
        delta = cred.expires_at - datetime.now(timezone.utc)
        days_remaining = max(0, delta.days)

    return {
        "credential_id": credential_id,
        "gb_total": gb_total,
        "gb_used": gb_used,
        "gb_remaining": gb_remaining,
        "usage_pct": round(usage_pct, 1),
        "bandwidth_alert_pct": cred.bandwidth_alert_pct,
        "bytes_used": cred.gb_used,  # approximate; relay tracks exact bytes
        "last_used_at": cred.last_used_at,
        "last_ip_address": str(cred.last_ip_address) if cred.last_ip_address else None,
        "last_ip_country": cred.last_ip_country,
        "days_remaining": days_remaining,
        "expires_at": cred.expires_at,
        "status": cred.status,
    }


async def rotate_credential_password(
    session: AsyncSession, credential_id: int, customer_phone: str, rotated_by: str = "customer"
) -> dict:
    """
    Rotate the SOCKS5 password for a credential.
    Rate-limited to 3/day per credential. The relay picks up the new password
    on its next cache refresh (max 30s).
    """
    cred = await get_credential_for_customer(session, credential_id, customer_phone)
    if not cred:
        raise ValueError("credential_not_found")
    if cred.status != "active":
        raise ValueError(f"credential_not_active:{cred.status}")

    # Rate limit check (3/day)
    today = datetime.now(timezone.utc).date()
    if cred.password_rotations_reset_at != today:
        # Reset counter (different day)
        cred.password_rotations_today = 0
        cred.password_rotations_reset_at = today
    if cred.password_rotations_today >= ROTATIONS_PER_DAY_LIMIT:
        next_allowed = datetime.combine(today + timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc)
        raise ValueError(f"rate_limit_exceeded:{next_allowed.isoformat()}")

    new_password = generate_proxy_password()
    cred.styxproxy_password = new_password.encode("utf-8")
    cred.password_rotated_at = datetime.now(timezone.utc)
    cred.password_rotations_today += 1

    # Audit log entry (insert separately via raw SQL since we don't have a model for it)
    from sqlalchemy import text

    await session.execute(
        text("""
            INSERT INTO credential_password_rotations
              (credential_id, rotated_by, rotated_at, ip_address, user_agent)
            VALUES
              (:cid, :by, now(), NULL, NULL)
        """),
        {"cid": credential_id, "by": rotated_by},
    )

    await session.commit()

    next_reset = datetime.combine(today + timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc)
    return {
        "new_password": new_password,
        "rotated_at": cred.password_rotated_at,
        "rotations_remaining_today": ROTATIONS_PER_DAY_LIMIT - cred.password_rotations_today,
        "next_rotation_allowed_at": next_reset,
    }


# Daily change limits per credential
LOCATION_CHANGES_PER_DAY = 5
ROTATION_MODE_CHANGES_PER_DAY = 3


async def update_credential_settings(
    session: AsyncSession,
    credential_id: int,
    customer_phone: str,
    country_target: Optional[str] = None,
    sticky_session_minutes: Optional[int] = None,
    bandwidth_alert_pct: Optional[int] = None,
    rotation_mode: Optional[str] = None,
) -> StyxproxyCredential:
    """Update mutable settings (location, sticky session, rotation mode, alert threshold).

    Rate-limited per day:
      - location_change_count: 5/day
      - rotation_mode_change_count: 3/day

    When location or rotation_mode changes, the upstream password is rebuilt
    (Rayobyte session-id + country code) and styxproxy_relay_entries.upstream_pass
    is updated so the relay picks up the change within its 30s cache refresh.
    """
    from sqlalchemy import text

    cred = await get_credential_for_customer(session, credential_id, customer_phone)
    if not cred:
        raise ValueError("credential_not_found")

    today = datetime.now(timezone.utc).date()

    # ─── Location change ───────────────────────────────────────────────────
    if country_target is not None and country_target.upper() != (cred.country_target or ""):
        if cred.location_changes_reset_at != today:
            cred.location_change_count = 0
            cred.location_changes_reset_at = today
        if cred.location_change_count >= LOCATION_CHANGES_PER_DAY:
            raise ValueError(f"location_rate_limit_exceeded:{LOCATION_CHANGES_PER_DAY}")
        cred.country_target = country_target.upper()
        cred.location_change_count += 1

    # ─── Sticky session minutes ────────────────────────────────────────────
    if sticky_session_minutes is not None:
        cred.sticky_session_minutes = max(0, min(60, sticky_session_minutes))
        if cred.sticky_session_minutes > 0 and (
            not cred.session_expires_at or cred.session_expires_at < datetime.now(timezone.utc)
        ):
            cred.session_id = secrets.token_hex(8)
            cred.session_expires_at = datetime.now(timezone.utc) + timedelta(minutes=cred.sticky_session_minutes)
        elif sticky_session_minutes == 0:
            cred.session_id = None
            cred.session_expires_at = None

    # ─── Bandwidth alert threshold ─────────────────────────────────────────
    if bandwidth_alert_pct is not None:
        cred.bandwidth_alert_pct = max(50, min(99, bandwidth_alert_pct))

    # ─── Rotation mode change (rotating ↔ static) ──────────────────────────
    rotation_changed = False
    if rotation_mode is not None and rotation_mode != cred.rotation_mode:
        if rotation_mode not in ("rotating", "static"):
            raise ValueError(f"invalid_rotation_mode:{rotation_mode}")
        if cred.rotation_mode_changes_reset_at != today:
            cred.rotation_mode_change_count = 0
            cred.rotation_mode_changes_reset_at = today
        if cred.rotation_mode_change_count >= ROTATION_MODE_CHANGES_PER_DAY:
            raise ValueError(f"rotation_mode_rate_limit_exceeded:{ROTATION_MODE_CHANGES_PER_DAY}")

        cred.rotation_mode = rotation_mode
        cred.rotation_mode_change_count += 1
        rotation_changed = True

        if rotation_mode == "static":
            # Mint a fresh session for Rayobyte sticky IP
            new_sid = secrets.token_hex(4)
            cred.assigned_static_session_id = new_sid
            cred.session_id = new_sid
            cred.sticky_session_minutes = max(cred.sticky_session_minutes or 0, 60)
            cred.session_expires_at = datetime.now(timezone.utc) + timedelta(hours=cred.sticky_session_minutes)
            cred.last_static_assigned_at = datetime.now(timezone.utc)
        else:
            cred.assigned_static_session_id = None
            cred.session_id = None
            cred.sticky_session_minutes = 0
            cred.session_expires_at = None

    # ─── Rebuild upstream password if location or rotation changed ─────────
    if (country_target is not None and country_target.upper() != (cred.country_target or "")) or rotation_changed:
        from app.services.catalog import build_upstream_password

        upstream_user = cred.provider_username or "styx_t1"
        new_upstream_pass = build_upstream_password(
            cred.pool_type,
            cred.rotation_mode,
            cred.country_target or "US",
            cred.assigned_static_session_id,
            upstream_user,
        )
        cred.provider_password = new_upstream_pass
        # Update relay entry too
        await session.execute(
            text("""
                UPDATE styxproxy_relay_entries
                SET upstream_pass = :new_pass
                WHERE credential_id = :cred_id AND status = 'active'
            """),
            {"new_pass": new_upstream_pass, "cred_id": credential_id},
        )

    await session.commit()
    return cred


# ─── Admin endpoints ──────────────────────────────────────────────────────────


async def list_all_credentials_admin(
    session: AsyncSession,
    status_filter: Optional[str] = None,
    pool_type_filter: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
) -> tuple[list, int]:
    """List all credentials with optional filters (admin only)."""
    stmt = select(StyxproxyCredential)
    if status_filter:
        stmt = stmt.where(StyxproxyCredential.status == status_filter)
    if pool_type_filter:
        stmt = stmt.where(StyxproxyCredential.pool_type == pool_type_filter)

    # Count
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await session.execute(count_stmt)).scalar() or 0

    # Page
    stmt = stmt.order_by(StyxproxyCredential.created_at.desc())
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    result = await session.execute(stmt)
    creds = result.scalars().all()
    return list(creds), total


async def suspend_credential(
    session: AsyncSession, credential_id: int, reason: str, actor: str = "admin"
) -> StyxproxyCredential:
    """Suspend a credential (relay stops serving within 30s on next refresh)."""
    cred = (
        await session.execute(select(StyxproxyCredential).where(StyxproxyCredential.id == credential_id))
    ).scalar_one_or_none()
    if not cred:
        raise ValueError("credential_not_found")
    if cred.status == "suspended":
        return cred  # idempotent

    cred.status = "suspended"
    cred.revoked_at = datetime.now(timezone.utc)
    cred.revoke_reason = reason
    await session.commit()
    return cred


async def unsuspend_credential(session: AsyncSession, credential_id: int) -> StyxproxyCredential:
    """Re-activate a suspended credential."""
    cred = (
        await session.execute(select(StyxproxyCredential).where(StyxproxyCredential.id == credential_id))
    ).scalar_one_or_none()
    if not cred:
        raise ValueError("credential_not_found")
    if cred.status != "suspended":
        return cred  # idempotent

    cred.status = "active"
    cred.revoked_at = None
    cred.revoke_reason = None
    await session.commit()
    return cred


async def reset_credential_usage(session: AsyncSession, credential_id: int, actor: str = "admin") -> dict:
    """Zero out the bandwidth counter on a credential (admin escape hatch)."""
    cred = (
        await session.execute(select(StyxproxyCredential).where(StyxproxyCredential.id == credential_id))
    ).scalar_one_or_none()
    if not cred:
        raise ValueError("credential_not_found")

    before = float(cred.gb_used) if cred.gb_used else 0.0
    cred.gb_used = 0
    await session.commit()

    return {
        "credential_id": credential_id,
        "gb_used_before": before,
        "gb_used_after": 0.0,
        "reset_at": datetime.now(timezone.utc),
        "reset_by": actor,
    }


async def force_password_rotation_admin(session: AsyncSession, credential_id: int, actor: str = "admin") -> dict:
    """Admin-initiated password rotation (bypasses the 3/day customer limit)."""
    cred = (
        await session.execute(select(StyxproxyCredential).where(StyxproxyCredential.id == credential_id))
    ).scalar_one_or_none()
    if not cred:
        raise ValueError("credential_not_found")

    new_password = generate_proxy_password()
    cred.styxproxy_password = new_password.encode("utf-8")
    cred.password_rotated_at = datetime.now(timezone.utc)
    # NOTE: do NOT increment password_rotations_today — admin rotation is unlimited

    from sqlalchemy import text

    await session.execute(
        text("""
            INSERT INTO credential_password_rotations
              (credential_id, rotated_by, rotated_at)
            VALUES (:cid, :by, now())
        """),
        {"cid": credential_id, "by": actor},
    )
    await session.commit()
    return {"new_password": new_password, "rotated_at": cred.password_rotated_at}


# ─── Connection string helpers (for customer-facing responses) ────────────────


def build_curl_socks5_example(username: str, password: str) -> str:
    return f"curl --socks5-hostname {username}:{password}@{PROXY_PUBLIC_HOST}:{PROXY_PORT_SOCKS5} https://api.ipify.org"


def build_curl_http_example(username: str, password: str) -> str:
    return f"curl --proxy http://{username}:{password}@{PROXY_PUBLIC_HOST}:{PROXY_PORT_HTTP} https://api.ipify.org"


def build_python_socks5_example(username: str, password: str) -> str:
    return (
        "import requests\n"
        f"proxies = {{\n"
        f"  'http':  'socks5h://{username}:{password}@{PROXY_PUBLIC_HOST}:{PROXY_PORT_SOCKS5}',\n"
        f"  'https': 'socks5h://{username}:{password}@{PROXY_PUBLIC_HOST}:{PROXY_PORT_SOCKS5}',\n"
        f"}}\n"
        "print(requests.get('https://api.ipify.org', proxies=proxies).text)"
    )
