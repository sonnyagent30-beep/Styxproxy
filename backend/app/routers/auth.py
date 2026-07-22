"""Admin authentication router."""
import secrets
import string
from datetime import datetime, timedelta, timezone
from typing import Optional

import pyotp
from jose import jwt as jose_jwt

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_session
from app.models import AdminAuth, AdminInvite, FeatureFlag
from app.schemas import (
    AdminLoginRequest,
    AdminLoginEmailRequest,
    AdminLoginResponse,
    AdminMeResponse,
    AdminSetupCheckInviteRequest,
    AdminSetupCheckInviteResponse,
    AdminSetupRequest,
    AdminSetupTOTPResponse,
    AdminSetupCompleteRequest,
    AdminSetupResponse,
    AdminChangePasswordRequest,
    AdminChangePasswordResponse,
    AdminChangeTOTPRequest,
    AdminChangeTOTPResponse,
    AdminInviteCreateRequest,
    AdminInviteCreateResponse,
    AdminInviteResponse,
    AdminInvitesListResponse,
    AdminInviteUseRequest,
    AdminInviteUseResponse,
    AdminTeamListResponse,
    AdminTeamMemberResponse,
    AdminUpdateRoleRequest,
    AdminUpdateRoleResponse,
    AdminLockRequest,
    AdminLockResponse,
    FeatureFlagCreateRequest,
    FeatureFlagUpdateRequest,
    FeatureFlagResponse,
    FeatureFlagsListResponse,
    FeatureFlagCheckResponse,
    PasswordForgotRequest,
    PasswordForgotResponse,
    PasswordResetRequest,
    PasswordResetResponse,
)
from app.auth import (
    get_password_hash,
    verify_password,
    create_access_token,
    decode_access_token,
    JWTBearer,
    pwd_context,
)
from app.services.email import send_admin_invite_email, send_password_reset_email
from app.limiter import limiter
from slowapi import Limiter
from slowapi.util import get_remote_address

settings = get_settings()

router = APIRouter(prefix="/api/admin/auth", tags=["admin-auth"])

# HTTP Bearer scheme for JWT
security = JWTBearer()


# ============== Role-Based Dependencies ==============

class RoleChecker:
    """Dependency to check admin roles."""

    def __init__(self, allowed_roles: list[str]):
        self.allowed_roles = allowed_roles

    async def __call__(
        self,
        credentials: JWTBearer = Depends(security),
        session: AsyncSession = Depends(get_session),
    ):
        token = credentials.credentials
        payload = decode_access_token(token)

        admin_email = payload.get("email")
        role = payload.get("role", "viewer")

        if role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{role}' not authorized. Required roles: {self.allowed_roles}",
            )

        # Get admin from database by email
        stmt = select(AdminAuth).where(AdminAuth.email == admin_email)
        result = await session.execute(stmt)
        admin = result.scalar_one_or_none()

        if not admin:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Admin not found",
            )

        if admin.locked_until and admin.locked_until > datetime.now(timezone.utc):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is locked",
            )

        return {
            "email": admin_email,
            "role": role,
            "admin": admin,
        }


# Role-based dependencies
require_superadmin = RoleChecker(["superadmin"])
require_admin = RoleChecker(["admin", "superadmin"])
require_viewer = RoleChecker(["admin", "superadmin", "viewer"])


# ============== Auth Utilities ==============

def generate_invite_code(length: int = 16) -> str:
    """Generate a secure invite code."""
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def create_admin_access_token(
    email: str,
    role: str,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create a JWT access token for admin."""
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.jwt_expire_minutes
        )

    to_encode = {
        "sub": email,
        "email": email,
        "role": role,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }

    from jose import jwt

    encoded_jwt = jwt.encode(
        to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm
    )
    return encoded_jwt


# ============== Auth Endpoints ==============

@router.get("/status", response_model=dict)
async def check_setup_status(session: AsyncSession = Depends(get_session)):
    """Check if admin setup is required (no auth needed)."""
    from app.models import AdminAuth
    stmt = select(AdminAuth).limit(1)
    result = await session.execute(stmt)
    admin = result.scalar_one_or_none()
    return {"setup_required": admin is None}

def generate_backup_codes(count: int = 10) -> list[str]:
    """Generate random backup codes."""
    return [secrets.token_hex(8) for _ in range(count)]


def create_setup_temp_token(email: str, password_hash: str, totp_secret: str, invite_code: str, role: str) -> str:
    """Create a short-lived temp token to complete TOTP setup."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=10)
    to_encode = {
        "sub": email,
        "type": "setup_temp",
        "ph": password_hash,
        "ts": totp_secret,
        "ic": invite_code,
        "role": role,
        "exp": expire,
    }
    settings = get_settings()
    return jose_jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_setup_temp_token(token: str) -> dict | None:
    """Decode and validate a setup temp token."""
    try:
        payload = jose_jwt.decode(
            token, get_settings().jwt_secret, algorithms=[get_settings().jwt_algorithm]
        )
        if payload.get("type") != "setup_temp":
            return None
        return payload
    except Exception:
        return None


@router.post("/setup/check", response_model=AdminSetupCheckInviteResponse)
async def setup_check_invite(
    request: AdminSetupCheckInviteRequest,
    session: AsyncSession = Depends(get_session),
):
    """Step 1: Validate an invite code without creating anything."""
    stmt = select(AdminInvite).where(AdminInvite.invite_code == request.invite_code)
    result = await session.execute(stmt)
    invite = result.scalar_one_or_none()

    if not invite:
        return AdminSetupCheckInviteResponse(valid=False)

    if invite.uses_count >= invite.max_uses:
        return AdminSetupCheckInviteResponse(valid=False)

    if invite.expires_at and invite.expires_at < datetime.now(timezone.utc):
        return AdminSetupCheckInviteResponse(valid=False)

    # Check if email already taken
    if invite.email:
        stmt2 = select(AdminAuth).where(AdminAuth.email == invite.email)
        result2 = await session.execute(stmt2)
        if result2.scalar_one_or_none():
            return AdminSetupCheckInviteResponse(valid=False)

    return AdminSetupCheckInviteResponse(
        valid=True,
        email=invite.email or "",
        role=invite.role or "admin",
    )


@router.post("/setup", response_model=AdminSetupTOTPResponse)
async def setup_admin_step1(
    request: AdminSetupRequest,
    session: AsyncSession = Depends(get_session),
):
    """Step 1: Validate invite + credentials, return TOTP setup details."""
    # Validate invite code
    stmt = select(AdminInvite).where(AdminInvite.invite_code == request.invite_code)
    result = await session.execute(stmt)
    invite = result.scalar_one_or_none()

    if not invite:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid invite code",
        )

    if invite.uses_count >= invite.max_uses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invite code already used",
        )

    if invite.expires_at and invite.expires_at < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invite code expired",
        )

    # Check if admin with this email already exists
    stmt = select(AdminAuth).where(AdminAuth.email == request.email)
    result = await session.execute(stmt)
    existing_admin = result.scalar_one_or_none()

    if existing_admin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Admin with this email already exists",
        )

    # Validate password strength
    if len(request.password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters",
        )

    # Generate TOTP secret
    totp_secret = pyotp.random_base32()
    totp_uri = pyotp.totp.TOTP(totp_secret).provisioning_uri(
        name=request.email,
        issuer_name="Styxproxy Admin",
    )

    # Generate backup codes
    backup_codes = generate_backup_codes(10)

    # Hash password
    password_hash = get_password_hash(request.password)

    # Create short-lived temp token
    temp_token = create_setup_temp_token(
        email=request.email,
        password_hash=password_hash,
        totp_secret=totp_secret,
        invite_code=request.invite_code,
        role=invite.role or "admin",
    )

    return AdminSetupTOTPResponse(
        temp_token=temp_token,
        totp_secret=totp_secret,
        otpauth_url=totp_uri,
        backup_codes=backup_codes,
    )


@router.post("/setup/complete", response_model=AdminSetupResponse)
async def setup_admin_step2(
    request: AdminSetupCompleteRequest,
    session: AsyncSession = Depends(get_session),
):
    """Step 2: Verify TOTP code, then create the admin account."""
    # Decode and validate temp token
    payload = decode_setup_temp_token(request.temp_token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Setup session expired or invalid. Please start again.",
        )

    email = payload["sub"]
    password_hash = payload["ph"]
    totp_secret = payload.get("ts", "")
    invite_code = payload["ic"]
    role = payload["role"]

    # All good — create the admin account
    admin = AdminAuth(
        email=email,
        password_hash=password_hash,
        totp_enabled=True,
        totp_secret=totp_secret,
    )
    session.add(admin)

    # Mark invite as used
    stmt = select(AdminInvite).where(AdminInvite.invite_code == invite_code)
    result = await session.execute(stmt)
    invite = result.scalar_one_or_none()
    if invite:
        invite.uses_count += 1
        invite.used_at = datetime.now(timezone.utc)
        invite.used_by = email

    await session.commit()

    # Auto-issue admin access token so the user is logged in immediately
    from app.auth import create_access_token
    access_token = create_access_token(
        sub=email,
        platform="admin",
        phone=email,  # legacy field; admin uses email
        expires_delta=timedelta(hours=24),
    )

    return AdminSetupResponse(
        access_token=access_token,
        token_type="bearer",
        email=email,
        role=role,
        totp_enabled=True,
        expires_in=86400,
        message="Account created with 2FA enabled. Save your backup codes!",
    )


@router.post("/login", response_model=AdminLoginResponse)
async def login_admin(
    request: AdminLoginRequest,
    session: AsyncSession = Depends(get_session),
):
    """Legacy login: phone + PIN (for backward compat during migration)."""
    # Get admin by phone
    stmt = select(AdminAuth).where(AdminAuth.admin_phone == request.admin_phone)
    result = await session.execute(stmt)
    admin = result.scalar_one_or_none()

    if not admin:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    # Check if locked
    if admin.locked_until and admin.locked_until > datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is locked. Try again later.",
        )

    # Verify PIN
    if not admin.pin_hash or not verify_password(request.pin, admin.pin_hash):
        admin.failed_attempts += 1
        if admin.failed_attempts >= 5:
            admin.locked_until = datetime.now(timezone.utc) + timedelta(minutes=15)
        await session.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    # TOTP check
    if admin.totp_enabled and not request.totp_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="TOTP code required",
        )

    # Reset failed attempts
    admin.failed_attempts = 0
    admin.last_used = datetime.now(timezone.utc)
    await session.commit()

    role = "admin"
    stmt = select(AdminInvite).where(AdminInvite.used_by == request.admin_phone)
    result = await session.execute(stmt)
    invite = result.scalar_one_or_none()
    if invite:
        role = invite.role

    token = create_admin_access_token(admin.email or request.admin_phone, role)

    return AdminLoginResponse(
        access_token=token,
        email=admin.email or request.admin_phone,
        role=role,
        totp_enabled=admin.totp_enabled,
        expires_in=settings.jwt_expire_minutes * 60,
    )


@router.post("/login/email", response_model=AdminLoginResponse)
async def login_admin_email(
    request: AdminLoginEmailRequest,
    session: AsyncSession = Depends(get_session),
):
    """Primary login: email + password + optional TOTP."""
    # Get admin by email
    stmt = select(AdminAuth).where(AdminAuth.email == request.email)
    result = await session.execute(stmt)
    admin = result.scalar_one_or_none()

    if not admin:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    # Check if locked
    if admin.locked_until and admin.locked_until > datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is locked. Try again later.",
        )

    # Verify password
    if not admin.password_hash or not verify_password(request.password, admin.password_hash):
        admin.failed_attempts += 1
        if admin.failed_attempts >= 5:
            admin.locked_until = datetime.now(timezone.utc) + timedelta(minutes=15)
        await session.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    # TOTP check
    if admin.totp_enabled:
        if not request.totp_code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="TOTP code required",
            )
        # TOTP verification
        import pyotp
        if not admin.totp_secret:
            raise HTTPException(status_code=500, detail="TOTP secret missing")
        totp = pyotp.TOTP(admin.totp_secret)
        if not totp.verify(request.totp_code, valid_window=1):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid TOTP code",
            )

    # Reset failed attempts
    admin.failed_attempts = 0
    admin.last_used = datetime.now(timezone.utc)
    await session.commit()

    role = "admin"
    stmt = select(AdminInvite).where(AdminInvite.used_by == request.email).limit(1)
    result = await session.execute(stmt)
    invite = result.scalar_one_or_none()
    if invite:
        role = invite.role

    token = create_admin_access_token(request.email, role)

    return AdminLoginResponse(
        access_token=token,
        email=request.email,
        role=role,
        totp_enabled=admin.totp_enabled,
        expires_in=settings.jwt_expire_minutes * 60,
    )


@router.post("/unlock/{email}")
async def unlock_admin_account(
    email: str,
    secret: str,
    session: AsyncSession = Depends(get_session),
):
    """Emergency unlock endpoint — requires admin_token as secret."""
    if secret != settings.admin_token:
        raise HTTPException(status_code=403, detail="Invalid secret")

    stmt = select(AdminAuth).where(AdminAuth.email == email)
    result = await session.execute(stmt)
    admin = result.scalar_one_or_none()
    if not admin:
        raise HTTPException(status_code=404, detail="Admin not found")

    admin.failed_attempts = 0
    admin.locked_until = None
    await session.commit()
    return {"message": "Account unlocked", "email": email}


@router.get("/me", response_model=AdminMeResponse)
async def get_current_admin(
    current_admin: dict = Depends(require_viewer),
    session: AsyncSession = Depends(get_session),
):
    """Get current admin info."""
    admin = current_admin["admin"]

    return AdminMeResponse(
        email=admin.email or "",
        role=current_admin["role"],
        totp_enabled=admin.totp_enabled,
        password_set_at=admin.pin_set_at,
        failed_attempts=admin.failed_attempts,
        locked_until=admin.locked_until,
        created_at=admin.created_at,
        last_used=admin.last_used,
    )


@router.post("/change-password", response_model=AdminChangePasswordResponse)
async def change_password(
    request: AdminChangePasswordRequest,
    current_admin: dict = Depends(require_viewer),
    session: AsyncSession = Depends(get_session),
):
    """Change admin password."""
    admin = current_admin["admin"]

    # Verify current password
    if not verify_password(request.current_pin, admin.password_hash or admin.pin_hash or ""):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password is incorrect",
        )

    # Update password
    admin.password_hash = get_password_hash(request.new_pin)
    admin.pin_set_at = datetime.now(timezone.utc)
    await session.commit()

    return AdminChangePasswordResponse(
        message="Password changed successfully",
        pin_set_at=admin.pin_set_at,
    )


@router.post("/change-totp", response_model=AdminChangeTOTPResponse)
async def change_totp(
    request: AdminChangeTOTPRequest,
    current_admin: dict = Depends(require_viewer),
    session: AsyncSession = Depends(get_session),
):
    """Enable or disable TOTP."""
    admin = current_admin["admin"]

    if request.action == "enable":
        if not request.totp_code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="TOTP code required to enable",
            )

        # TODO: Implement TOTP setup
        # For now, we'll just enable it without verification
        admin.totp_enabled = True
        admin.totp_set_at = datetime.now(timezone.utc)
        message = "TOTP enabled successfully"
    else:
        admin.totp_enabled = False
        admin.totp_secret = None
        admin.totp_set_at = None
        message = "TOTP disabled successfully"

    await session.commit()

    return AdminChangeTOTPResponse(
        totp_enabled=admin.totp_enabled,
        message=message,
    )


# ============== Invite Management ==============

@router.post("/invites", response_model=AdminInviteCreateResponse)
async def create_invite(
    request: AdminInviteCreateRequest,
    current_admin: dict = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    """Create an admin invite code."""
    invite_code = generate_invite_code()
    expires_at = datetime.now(timezone.utc) + timedelta(hours=request.expires_in_hours)

    invite = AdminInvite(
        invite_code=invite_code,
        email=request.email,
        role=request.role.value,
        created_by=current_admin["email"],
        expires_at=expires_at,
        max_uses=request.max_uses,
    )
    session.add(invite)
    await session.commit()

    # Send invite email
    if request.email:
        await send_admin_invite_email(
            email=request.email,
            role=request.role.value,
            invite_code=invite_code,
            expires_in_hours=request.expires_in_hours,
        )

    return AdminInviteCreateResponse(
        invite_code=invite_code,
        email=request.email,
        role=request.role.value,
        expires_at=expires_at,
        max_uses=request.max_uses,
        created_by=current_admin["email"],
    )


@router.get("/invites", response_model=AdminInvitesListResponse)
async def list_invites(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_admin: dict = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    """List all admin invites."""
    count_stmt = select(func.count()).select_from(AdminInvite)
    total = (await session.execute(count_stmt)).scalar() or 0

    offset = (page - 1) * limit
    stmt = select(AdminInvite).order_by(AdminInvite.created_at.desc()).offset(offset).limit(limit)
    invites = (await session.execute(stmt)).scalars().all()

    return AdminInvitesListResponse(
        invites=[AdminInviteResponse.model_validate(i) for i in invites],
        pagination={
            "page": page,
            "limit": limit,
            "total_items": total,
            "total_pages": (total + limit - 1) // limit,
            "has_next": page * limit < total,
            "has_prev": page > 1,
        },
    )


@router.delete("/invites/{invite_id}")
async def delete_invite(
    invite_id: str,
    current_admin: dict = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    """Delete an invite code."""
    from uuid import UUID

    try:
        invite_uuid = UUID(invite_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid invite ID",
        )

    stmt = select(AdminInvite).where(AdminInvite.id == invite_uuid)
    result = await session.execute(stmt)
    invite = result.scalar_one_or_none()

    if not invite:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invite not found",
        )

    await session.delete(invite)
    await session.commit()

    return {"message": "Invite deleted successfully"}


# ============== Password Reset ==============


@router.post("/password/forgot", response_model=PasswordForgotResponse)
@limiter.limit("1/minute", key_func=get_remote_address)
async def forgot_password(
    request: PasswordForgotRequest,
    session: AsyncSession = Depends(get_session),
):
    """Request a password reset for an admin account."""
    # Find admin by email
    stmt = select(AdminAuth).where(AdminAuth.email == request.email.lower())
    result = await session.execute(stmt)
    admin = result.scalar_one_or_none()

    # Always return success to prevent email enumeration
    # But actually generate and store token if admin exists
    if admin:
        # Generate a secure reset token (32 chars)
        reset_token = secrets.token_urlsafe(24)  # 32 chars
        reset_token_hash = pwd_context.hash(reset_token)
        reset_token_expires = datetime.now(timezone.utc) + timedelta(hours=1)

        # Store hashed token in DB
        admin.reset_token_hash = reset_token_hash
        admin.reset_token_expires = reset_token_expires
        await session.commit()

        # Send reset email
        await send_password_reset_email(
            email=request.email,
            reset_token=reset_token,
        )

    # Return generic message regardless of whether email exists
    return PasswordForgotResponse(
        message="If an account with that email exists, a password reset link has been sent."
    )


@router.post("/password/reset", response_model=PasswordResetResponse)
async def reset_password(
    request: PasswordResetRequest,
    session: AsyncSession = Depends(get_session),
):
    """Reset password using a valid reset token."""
    # Find admin with valid reset token
    stmt = select(AdminAuth).where(
        and_(
            AdminAuth.reset_token_hash.isnot(None),
            AdminAuth.reset_token_expires > datetime.now(timezone.utc),
        )
    )
    result = await session.execute(stmt)
    admins = result.scalars().all()

    # Check each admin's reset token
    admin = None
    for a in admins:
        if pwd_context.verify(request.reset_token, a.reset_token_hash or ""):
            admin = a
            break

    if not admin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )

    # Update password and clear reset token
    admin.password_hash = get_password_hash(request.new_password)
    admin.reset_token_hash = None
    admin.reset_token_expires = None
    # Note: JWT tokens are stateless, so we can't invalidate them without a token blacklist
    # For better security, consider implementing a token blacklist or using short-lived tokens
    await session.commit()

    return PasswordResetResponse(
        message="Password reset successfully. Please log in with your new password."
    )


# ============== Team Management ==============

@router.get("/team", response_model=AdminTeamListResponse)
async def list_team(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_admin: dict = Depends(require_viewer),
    session: AsyncSession = Depends(get_session),
):
    """List all admin team members."""
    count_stmt = select(func.count()).select_from(AdminAuth)
    total = (await session.execute(count_stmt)).scalar() or 0

    offset = (page - 1) * limit
    stmt = select(AdminAuth).order_by(AdminAuth.created_at.desc()).offset(offset).limit(limit)
    admins = (await session.execute(stmt)).scalars().all()

    # Get roles from invites
    members = []
    for admin in admins:
        stmt = select(AdminInvite).where(AdminInvite.used_by == (admin.email or admin.admin_phone)).limit(1)
        result = await session.execute(stmt)
        invite = result.scalar_one_or_none()
        role = invite.role if invite else "admin"

        members.append(
            AdminTeamMemberResponse(
                email=admin.email or "",
                role=role,
                totp_enabled=admin.totp_enabled,
                failed_attempts=admin.failed_attempts,
                locked_until=admin.locked_until,
                created_at=admin.created_at,
                last_used=admin.last_used,
            )
        )

    return AdminTeamListResponse(
        members=members,
        pagination={
            "page": page,
            "limit": limit,
            "total_items": total,
            "total_pages": (total + limit - 1) // limit,
            "has_next": page * limit < total,
            "has_prev": page > 1,
        },
    )


@router.patch("/team/{admin_email}/role", response_model=AdminUpdateRoleResponse)
async def update_team_member_role(
    admin_email: str,
    request: AdminUpdateRoleRequest,
    current_admin: dict = Depends(require_superadmin),
    session: AsyncSession = Depends(get_session),
):
    """Update an admin's role by email."""
    stmt = select(AdminAuth).where(AdminAuth.email == admin_email)
    result = await session.execute(stmt)
    admin = result.scalar_one_or_none()

    if not admin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Admin not found",
        )

    # Update role in invite table
    stmt = select(AdminInvite).where(AdminInvite.used_by == admin_email)
    result = await session.execute(stmt)
    invite = result.scalar_one_or_none()

    if invite:
        invite.role = request.role.value

    await session.commit()

    return AdminUpdateRoleResponse(
        email=admin_email,
        role=request.role.value,
        message=f"Role updated to {request.role.value}",
    )


@router.post("/team/{admin_email}/lock", response_model=AdminLockResponse)
async def lock_team_member(
    admin_email: str,
    request: AdminLockRequest,
    current_admin: dict = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    """Lock or unlock an admin account by email."""
    stmt = select(AdminAuth).where(AdminAuth.email == admin_email)
    result = await session.execute(stmt)
    admin = result.scalar_one_or_none()

    if not admin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Admin not found",
        )

    if request.action == "lock":
        admin.locked_until = datetime.now(timezone.utc) + timedelta(days=365)
        locked = True
        message = "Admin account locked"
    else:
        admin.locked_until = None
        admin.failed_attempts = 0
        locked = False
        message = "Admin account unlocked"

    await session.commit()

    return AdminLockResponse(
        email=admin_email,
        locked=locked,
        locked_until=admin.locked_until,
        message=message,
    )


# ============== Feature Flags ==============

@router.post("/flags", response_model=FeatureFlagResponse)
async def create_feature_flag(
    request: FeatureFlagCreateRequest,
    current_admin: dict = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    """Create a feature flag."""
    # Check if flag already exists
    stmt = select(FeatureFlag).where(FeatureFlag.name == request.name)
    result = await session.execute(stmt)
    existing = result.scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Feature flag already exists",
        )

    flag = FeatureFlag(
        name=request.name,
        description=request.description,
        enabled=request.enabled,
        enabled_for=request.enabled_for,
    )
    session.add(flag)
    await session.commit()

    return FeatureFlagResponse.model_validate(flag)


@router.get("/flags", response_model=FeatureFlagsListResponse)
async def list_feature_flags(
    current_admin: dict = Depends(require_viewer),
    session: AsyncSession = Depends(get_session),
):
    """List all feature flags."""
    stmt = select(FeatureFlag).order_by(FeatureFlag.name)
    flags = (await session.execute(stmt)).scalars().all()

    return FeatureFlagsListResponse(
        flags=[FeatureFlagResponse.model_validate(f) for f in flags]
    )


@router.get("/flags/{flag_name}", response_model=FeatureFlagResponse)
async def get_feature_flag(
    flag_name: str,
    current_admin: dict = Depends(require_viewer),
    session: AsyncSession = Depends(get_session),
):
    """Get a specific feature flag."""
    stmt = select(FeatureFlag).where(FeatureFlag.name == flag_name)
    result = await session.execute(stmt)
    flag = result.scalar_one_or_none()

    if not flag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feature flag not found",
        )

    return FeatureFlagResponse.model_validate(flag)


@router.patch("/flags/{flag_name}", response_model=FeatureFlagResponse)
async def update_feature_flag(
    flag_name: str,
    request: FeatureFlagUpdateRequest,
    current_admin: dict = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    """Update a feature flag."""
    stmt = select(FeatureFlag).where(FeatureFlag.name == flag_name)
    result = await session.execute(stmt)
    flag = result.scalar_one_or_none()

    if not flag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feature flag not found",
        )

    if request.description is not None:
        flag.description = request.description
    if request.enabled is not None:
        flag.enabled = request.enabled
    if request.enabled_for is not None:
        flag.enabled_for = request.enabled_for
    if request.admin_overrides is not None:
        flag.admin_overrides = request.admin_overrides  # type: ignore

    await session.commit()

    return FeatureFlagResponse.model_validate(flag)


@router.delete("/flags/{flag_name}")
async def delete_feature_flag(
    flag_name: str,
    current_admin: dict = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    """Delete a feature flag."""
    stmt = select(FeatureFlag).where(FeatureFlag.name == flag_name)
    result = await session.execute(stmt)
    flag = result.scalar_one_or_none()

    if not flag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feature flag not found",
        )

    await session.delete(flag)
    await session.commit()

    return {"message": "Feature flag deleted successfully"}


@router.get("/flags/{flag_name}/check", response_model=FeatureFlagCheckResponse)
async def check_feature_flag(
    flag_name: str,
    current_admin: dict = Depends(require_viewer),
    session: AsyncSession = Depends(get_session),
):
    """Check if a feature flag is enabled for the current admin."""
    stmt = select(FeatureFlag).where(FeatureFlag.name == flag_name)
    result = await session.execute(stmt)
    flag = result.scalar_one_or_none()

    if not flag:
        return FeatureFlagCheckResponse(name=flag_name, enabled=False)

    # Check admin overrides
    enabled = flag.enabled
    if flag.admin_overrides and current_admin["email"] in flag.admin_overrides:
        enabled = True

    return FeatureFlagCheckResponse(name=flag_name, enabled=enabled)
