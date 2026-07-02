"""JWT authentication utilities and admin token verification."""
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import get_settings
from app.database import get_session
settings = get_settings()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = JWTBearer()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(sub: str, platform: str, phone: str, expires_delta: Optional[timedelta] = None) -> str:
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=settings.jwt_expire_minutes))
    to_encode = {"sub": sub, "platform": platform, "phone": phone, "exp": expire, "iat": datetime.now(timezone.utc)}
    return jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm)

def decode_access_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials", headers={"WWW-Authenticate": "Bearer"}) from e

def verify_admin_token(authorization: str) -> bool:
    if not authorization:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authorization header missing")
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authorization header format")
    if parts[1] != settings.admin_token:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid admin token")
    return True

async def get_current_account(credentials: HTTPAuthorizationCredentials = Depends(security), session: AsyncSession = Depends(get_session)) -> dict:
    from app.models import PlatformAccount, Customer
    from sqlalchemy import select
    payload = decode_access_token(credentials.credentials)
    platform_account_id = payload.get("sub")
    if not platform_account_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")
    result = await session.execute(select(PlatformAccount).where(PlatformAccount.id == UUID(platform_account_id)))
    platform_account = result.scalar_one_or_none()
    if not platform_account:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Platform account not found")
    customer = None
    if platform_account.customer_id:
        result = await session.execute(select(Customer).where(Customer.id == platform_account.customer_id))
        customer = result.scalar_one_or_none()
    return {"platform_account": platform_account, "customer": customer}

async def admin_only(authorization: str = Depends(HTTPBearer())) -> bool:
    verify_admin_token(authorization.credentials)
    return True

class JWTBearer(HTTPBearer):
    async def __call__(self, credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))) -> HTTPAuthorizationCredentials:
        if credentials is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authorization header missing", headers={"WWW-Authenticate": "Bearer"})
        return credentials
