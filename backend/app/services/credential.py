"""Credential service for Bunche Dante credentials."""
import random, string
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models import BuncheCredential, Order
from app.auth import get_password_hash

PROXY_POOL = {
    "NG": [{"ip": "185.199.228.45", "port": 1080}, {"ip": "185.199.229.12", "port": 1080}, {"ip": "185.199.230.88", "port": 1080}],
    "UK": [{"ip": "178.62.34.56", "port": 1080}, {"ip": "178.62.35.78", "port": 1080}],
    "US": [{"ip": "104.248.12.34", "port": 1080}, {"ip": "104.248.13.56", "port": 1080}],
    "DEFAULT": [{"ip": "192.168.1.1", "port": 1080}, {"ip": "192.168.1.2", "port": 1080}],
}
def generate_bun_username(phone: str, order_id: str) -> str:
    suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=6))
    phone_suffix = phone[-4:] if phone else "0000"
    return f"bun_{phone_suffix}{suffix}"
def generate_temp_password() -> str:
    return "".join(random.choices(string.ascii_letters + string.digits, k=16))
def get_available_proxy(country: str) -> dict:
    return random.choice(PROXY_POOL.get(country, PROXY_POOL["DEFAULT"]))
async def create_credential(db_session: AsyncSession, customer_phone: str, order_id: str,
    pool_type: str = "paid", duration_days: int = 30, country: str = "NG") -> BuncheCredential:
    bun_username = generate_bun_username(customer_phone, order_id)
    password = generate_temp_password()
    password_hash = get_password_hash(password)
    proxy = get_available_proxy(country)
    expires_at = datetime.utcnow() + timedelta(days=duration_days)
    credential = BuncheCredential(bun_username=bun_username, password_hash=password_hash, customer_phone=customer_phone,
        order_id=order_id, pool_type=pool_type, upstream_proxy_ip=proxy["ip"], upstream_proxy_port=proxy["port"],
        dante_port=random.randint(9000, 9999), status="active", expires_at=expires_at)
    db_session.add(credential)
    await db_session.commit()
    await db_session.refresh(credential)
    return credential
async def get_credential_by_order(db_session: AsyncSession, order_id: str) -> Optional[BuncheCredential]:
    result = await db_session.execute(select(BuncheCredential).where(BuncheCredential.order_id == order_id))
    return result.scalar_one_or_none()
async def get_active_credentials_by_phone(db_session: AsyncSession, phone: str) -> list:
    result = await db_session.execute(select(BuncheCredential).where(
        BuncheCredential.customer_phone == phone, BuncheCredential.status == "active"))
    return list(result.scalars().all())
async def revoke_credential(db_session: AsyncSession, credential_id: int, reason: str = "manual") -> Optional[BuncheCredential]:
    result = await db_session.execute(select(BuncheCredential).where(BuncheCredential.id == credential_id))
    credential = result.scalar_one_or_none()
    if credential:
        credential.status = "revoked"
        credential.revoked_at = datetime.utcnow()
        credential.revoke_reason = reason
        await db_session.commit()
    return credential
async def replace_credential(db_session: AsyncSession, old_credential_id: int, reason: str = "ban_reported") -> Optional[BuncheCredential]:
    result = await db_session.execute(select(BuncheCredential).where(BuncheCredential.id == old_credential_id))
    old_credential = result.scalar_one_or_none()
    if not old_credential: return None
    result = await db_session.execute(select(Order).where(Order.order_id == old_credential.order_id))
    order = result.scalar_one_or_none()
    if not order: return None
    await revoke_credential(db_session, old_credential_id, reason)
    new_credential = await create_credential(db_session, customer_phone=old_credential.customer_phone or "",
        order_id=old_credential.order_id, pool_type=old_credential.pool_type, duration_days=30, country=order.country or "NG")
    order.bunche_credential_id = new_credential.id
    order.replacement_count += 1
    order.status = "active"
    await db_session.commit()
    return new_credential
async def get_credential_by_id(db_session: AsyncSession, credential_id: int) -> Optional[BuncheCredential]:
    result = await db_session.execute(select(BuncheCredential).where(BuncheCredential.id == credential_id))
    return result.scalar_one_or_none()
