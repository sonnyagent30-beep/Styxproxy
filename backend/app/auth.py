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

    encoded_jwt = jwt.encode(
        to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm
    )
    return encoded_jwt


def decode_access_token(token: str) -> dict:
    """Decode and validate a JWT access token."""
    try:
        payload = jwt.decode(
            token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
        return payload
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


def verify_admin_token(authorization: str) -> bool:
    """Verify the admin token from Authorization header."""
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing",
        )

    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format",
        )

    token = parts[1]
    if token != settings.admin_token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid admin token",
        )

    return True


async def get_current_account(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Get current authenticated account from JWT token."""
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
    from sqlalchemy import select

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

    # Get customer
    if platform_account.customer_id:
        stmt = select(Customer).where(Customer.id == platform_account.customer_id)
        result = await session.execute(stmt)
        customer = result.scalar_one_or_none()
    else:
        customer = None

    return {
        "platform_account": platform_account,
        "customer": customer,
    }


async def admin_only(
    authorization: HTTPAuthorizationCredentials = Depends(HTTPBearer()),
) -> bool:
    """Dependency for admin-only endpoints."""
    verify_admin_token(authorization.credentials)
    return True
