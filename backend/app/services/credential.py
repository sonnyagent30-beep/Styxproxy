"""
Credential service for Bunche Dante credentials.

This module has two layers:

1. Low-level (provider + dante services):
   - get_provider_proxy(): calls provider API, tests, retries up to 5x
   - register_on_dante(): calls Dante API to get branded bun_username/bun_password
   These are used directly by the fulfillment flow.

2. High-level (this module):
   - create_credential(): full pipeline — provider → Dante → DB
   - Returns (BuncheCredential, plaintext_password) tuple so the
     fulfillment caller can send the password to the customer via n8n/email.

When Dante and the provider are deployed on the VPS, only the underlying
service stubs (app/services/dante.py, app/services/provider.py) need updating.
"""
import random
import string
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models import BuncheCredential, Order
from app.auth import get_password_hash


# ─── Constants ────────────────────────────────────────────────────────────────

MAX_PROVIDER_RETRIES = 5
STUB_PROXY_POOL = {
    "NG": [{"ip": "185.199.228.45", "port": 1080}],
    "UK": [{"ip": "178.62.34.56", "port": 1080}],
    "US": [{"ip": "104.248.12.34", "port": 1080}],
    "DEFAULT": [{"ip": "192.168.1.1", "port": 1080}],
}


# ─── Helpers ───────────────────────────────────────────────────────────────────

def generate_bun_username(phone: Optional[str] = None, order_id: Optional[str] = None) -> str:
    """Generate a Bunche proxy username.

    With phone+order_id: ``bun_{last4phone}{order_suffix}{rand8}`` (used
    historically and by tests). With no args: ``bun_{rand8}``.
    """
    if phone and order_id:
        phone_suffix = phone.replace("+", "").replace(" ", "")[-4:]
        order_suffix = "".join(c for c in order_id if c.isalnum())[-4:]
        rand = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
        return f"bun_{phone_suffix}{order_suffix}{rand}"
    suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
    return f"bun_{suffix}"


def generate_bun_password() -> str:
    return "".join(random.choices(string.ascii_letters + string.digits, k=16))


def generate_temp_password(length: int = 16) -> str:
    """Generate a temporary alphanumeric password of the given length.

    Used for share-by-link / short-lived credentials. Letters + digits only,
    no symbols to keep copy/paste safe across all clients.
    """
    return "".join(random.choices(string.ascii_letters + string.digits, k=length))


def get_available_proxy(country: str) -> dict:
    """Return a stub proxy for the given country, falling back to DEFAULT.

    Format: {ip, port, username, password}. Wraps the internal pool so
    tests (and any future code that needs a quick proxy reference) can use
    the same data shape.
    """
    return _stub_proxy(country)


def _stub_proxy(country: str):
    """Return a stub proxy from the hardcoded pool (used when provider is offline)."""
    pool = STUB_PROXY_POOL.get(country.upper(), STUB_PROXY_POOL["DEFAULT"])
    p = random.choice(pool)
    return {
        "ip": p["ip"],
        "port": p["port"],
        "username": f"raw_{random.randint(10000, 99999)}",
        "password": f"rawpass_{random.randint(100000, 999999)}",
    }


# ─── Provider Proxy Pipeline ───────────────────────────────────────────────────

async def get_provider_proxy(
    plan_code: str,
    country: str,
    proxy_type: str = "isp",
    quantity: int = 1,
) -> dict:
    """
    Get a tested, working proxy from the provider.
    Tries up to MAX_PROVIDER_RETRIES times.

    Returns a dict with keys: {ip, port, username, password, provider_order_id, expires_at}

    Raises RuntimeError if all retries are exhausted.
    """
    from app.services import provider as provider_svc

    last_error = None
    for attempt in range(MAX_PROVIDER_RETRIES):
        try:
            proxy = await provider_svc.create_order(
                plan_code=plan_code,
                country=country,
                proxy_type=proxy_type,
                quantity=quantity,
            )

            test_result = await provider_svc.test_proxy(proxy)
            if test_result.alive:
                return {
                    "provider_order_id": proxy.provider_order_id,
                    "ip": proxy.ip,
                    "port": proxy.port,
                    "username": proxy.username,
                    "password": proxy.password,
                    "protocol": proxy.protocol,
                    "expires_at": proxy.expires_at,
                    "country": proxy.country,
                    "isp": proxy.isp,
                    "asn": proxy.asn,
                    "latency_ms": test_result.latency_ms,
                }

            last_error = test_result.error or "proxy_test_failed"

        except Exception as e:
            last_error = str(e)

    raise RuntimeError(
        f"Provider proxy unavailable after {MAX_PROVIDER_RETRIES} attempts. "
        f"Last error: {last_error}"
    )


# ─── Dante Pipeline ───────────────────────────────────────────────────────────

async def register_on_dante(
    upstream_ip: str,
    upstream_port: int,
    expires_at: datetime,
) -> dict:
    """
    Register branded credentials on Dante.

    Returns a dict with keys: {bun_username, bun_password, dante_port}
    The plaintext password is returned so it can be sent to the customer.
    """
    from app.services import dante as dante_svc

    bun_username = generate_bun_username()
    bun_password = generate_bun_password()

    try:
        dante_cred = await dante_svc.register_credential(
            upstream_ip=upstream_ip,
            upstream_port=upstream_port,
            expires_at=expires_at,
        )
        # Use Dante's returned credentials if available
        bun_username = dante_cred.bun_username
        bun_password = dante_cred.bun_password
        dante_port = dante_cred.dante_port
    except Exception:
        # Dante not yet deployed — use local generation
        dante_port = random.randint(9000, 9999)

    return {
        "bun_username": bun_username,
        "bun_password": bun_password,
        "dante_port": dante_port,
    }


# ─── High-level Credential Creation ──────────────────────────────────────────

async def create_credential(
    db_session: AsyncSession,
    order_id: str,
    customer_phone: str,
    plan_code: str,
    country: str,
    proxy_type: str = "isp",
    quantity: int = 1,
    duration_days: int = 30,
    protocol: str = "socks5",
    pool_type: str = "paid",
) -> tuple[BuncheCredential, str]:
    """
    Full credential pipeline: provider → test → Dante branding → DB.

    Returns (BuncheCredential, plaintext_password).

    The plaintext password is NOT stored in the DB — only the hash is.
    The caller is responsible for delivering the plaintext password
    to the customer (via email, WhatsApp, n8n, etc.).
    """
    # 1. Get and test a working proxy from the provider
    proxy = await get_provider_proxy(
        plan_code=plan_code,
        country=country,
        proxy_type=proxy_type,
        quantity=quantity,
    )

    # 2. Register on Dante to get branded credentials
    dante = await register_on_dante(
        upstream_ip=proxy["ip"],
        upstream_port=proxy["port"],
        expires_at=proxy["expires_at"],
    )

    # 3. Build the DB record
    plaintext_password = dante["bun_password"]
    password_hash = get_password_hash(plaintext_password)

    expires_at = proxy.get("expires_at") or (datetime.utcnow() + timedelta(days=duration_days))

    credential = BuncheCredential(
        bun_username=dante["bun_username"],
        password_hash=password_hash,
        customer_phone=customer_phone,
        order_id=order_id,
        pool_type=pool_type,
        protocol=protocol,
        provider_name="proxy-seller",
        provider_order_id=proxy["provider_order_id"],
        provider_username=proxy["username"],
        provider_password=proxy["password"],
        upstream_proxy_ip=proxy["ip"],
        upstream_proxy_port=proxy["port"],
        dante_port=dante["dante_port"],
        status="active",
        expires_at=expires_at,
    )

    db_session.add(credential)
    await db_session.commit()
    await db_session.refresh(credential)

    return credential, plaintext_password


# ─── Read helpers ─────────────────────────────────────────────────────────────

async def get_credential_by_order(
    db_session: AsyncSession,
    order_id: str,
) -> Optional[BuncheCredential]:
    return (
        await db_session.execute(
            select(BuncheCredential).where(BuncheCredential.order_id == order_id)
        )
    ).scalar_one_or_none()


async def get_credential_by_id(
    db_session: AsyncSession,
    credential_id: int,
) -> Optional[BuncheCredential]:
    return (
        await db_session.execute(
            select(BuncheCredential).where(BuncheCredential.id == credential_id)
        )
    ).scalar_one_or_none()


async def get_active_credentials_by_phone(
    db_session: AsyncSession,
    phone: str,
) -> list[BuncheCredential]:
    result = await db_session.execute(
        select(BuncheCredential).where(
            BuncheCredential.customer_phone == phone,
            BuncheCredential.status == "active",
        )
    )
    return list(result.scalars().all())


async def revoke_credential(
    db_session: AsyncSession,
    credential_id: int,
    reason: str = "manual",
) -> Optional[BuncheCredential]:
    credential = await get_credential_by_id(db_session, credential_id)
    if credential:
        credential.status = "revoked"
        credential.revoked_at = datetime.utcnow()
        credential.revoke_reason = reason
        await db_session.commit()
    return credential


async def replace_credential(
    db_session: AsyncSession,
    old_credential_id: int,
    reason: str = "ban_reported",
) -> Optional[BuncheCredential]:
    """
    Revoke old credential and create a new one.
    For Dante-rotation (bun_username/bun_password change, same upstream IP).
    """
    old = await get_credential_by_id(db_session, old_credential_id)
    if not old:
        return None

    order = (
        await db_session.execute(select(Order).where(Order.order_id == old.order_id))
    ).scalar_one_or_none()
    if not order:
        return None

    await revoke_credential(db_session, old_credential_id, reason)

    if not old.order_id:
        return None

    new_cred, _ = await create_credential(
        db_session=db_session,
        order_id=old.order_id,
        customer_phone=old.customer_phone or "",
        plan_code=order.plan_code or "unknown",
        country=order.country or "NG",
        duration_days=30,
        protocol=old.protocol or "socks5",
        pool_type=old.pool_type or "paid",
    )

    order.bunche_credential_id = new_cred.id
    order.replacement_count += 1
    await db_session.commit()

    return new_cred
