"""JWT authentication utilities and admin token verification."""
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import jwt as jose_jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_session

settings = get_settings()

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class JWTBearer(HTTPBearer):
    """JWT Bearer authentication scheme."""

    async def __call__(
        self, credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))
    ) -> HTTPAuthorizationCredentials:
        """Call the authentication scheme."""
        if credentials is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authorization header missing",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return credentials


# HTTP Bearer scheme for JWT
security = JWTBearer()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hashed password."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password using bcrypt."""
    return pwd_context.hash(password)


def create_access_token(
    sub: str,
    platform: str,
    phone: str,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create a JWT access token."""
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.jwt_expire_minutes
        )

    to_encode = {
        "sub": sub,
        "platform": platform,
        "phone": phone,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }

    encoded_jose_jwt = jose_jwt.encode(
        to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm
    )
    return encoded_jose_jwt


def decode_access_token(token: str) -> dict:
    """Decode and validate a JWT access token."""
    try:
        payload = jose_jwt.decode(
            token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
        return payload
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


def verify_admin_token(authorization: Optional[str]) -> bool:
    """Verify the admin token from Authorization header."""
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing",
        )

    parts = authorization.split() if isinstance(authorization, str) else None
    if parts is not None and len(parts) > 1 and parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format",
        )

    token = parts[1] if parts and len(parts) == 2 else (authorization.credentials if hasattr(authorization, 'credentials') else authorization)
    if isinstance(token, str) and token.startswith('Bearer '):
        token = token[7:]
    if token != settings.admin_token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid admin token",
        )

    return True


async def get_current_account(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Get current authenticated account from JWT token OR device_id header.

    Web flow: device_id is sent in X-Device-Id header on every API call.
    Backend auto-creates an anonymous PlatformAccount on first call.
    JWT cookie is set by /api/session/init and reused.
    """
    from app.models import PlatformAccount, Customer

    token = credentials.credentials
    payload = decode_access_token(token)

    platform_account_id: str = payload.get("sub")
    if platform_account_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    # Get platform account
    stmt = select(PlatformAccount).where(
        PlatformAccount.id == UUID(platform_account_id)
    )
    result = await session.execute(stmt)
    platform_account = result.scalar_one_or_none()

    if platform_account is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Platform account not found",
        )

    # Get customer (may be None for anonymous web sessions)
    customer = None
    if platform_account.customer_id:
        stmt = select(Customer).where(Customer.id == platform_account.customer_id)
        result = await session.execute(stmt)
        customer = result.scalar_one_or_none()

    return {
        "platform_account": platform_account,
        "customer": customer,
        "device_id": platform_account.device_id,
    }


async def admin_only(
    authorization: HTTPAuthorizationCredentials = Depends(HTTPBearer()),
) -> bool:
    """Dependency for admin-only endpoints."""
    verify_admin_token(authorization.credentials)
    return True


async def admin_only_with_email(
    authorization: HTTPAuthorizationCredentials = Depends(HTTPBearer()),
) -> str:
    """Like admin_only, but returns the admin's email from the JWT payload."""
    token = authorization.credentials
    payload = decode_access_token(token)
    return payload.get("email") or payload.get("sub") or "unknown"
