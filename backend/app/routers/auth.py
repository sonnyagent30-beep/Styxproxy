"""Admin authentication router."""
import secrets
import string
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_session
from app.models import AdminAuth, AdminInvite, FeatureFlag
from app.schemas import (
    AdminLoginRequest,
    AdminLoginResponse,
    AdminMeResponse,
    AdminSetupRequest,
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
    FeatureFlagCreateRequest,
    FeatureFlagUpdateRequest,
    FeatureFlagResponse,
    FeatureFlagsListResponse,
    FeatureFlagCheckResponse,
    AdminTeamMemberResponse,
    AdminTeamListResponse,
    AdminUpdateRoleRequest,
    AdminUpdateRoleResponse,
    AdminLockRequest,
    AdminLockResponse,
    AdminRole,
)
from app.auth import (
    get_password_hash,
    verify_password,
    create_access_token,
    decode_access_token,
    JWTBearer,
    pwd_context,
)

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

        admin_phone = payload.get("admin_phone")
        role = payload.get("role", "viewer")

        if role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{role}' not authorized. Required roles: {self.allowed_roles}",
            )

        # Get admin from database
        stmt = select(AdminAuth).where(AdminAuth.admin_phone == admin_phone)
        result = await session.execute(stmt)
        admin = result.scalar_one_or_none()

        if not admin:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Admin not found",
            )

        if admin.locked_until and admin.locked_until > datetime.utcnow():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is locked",
            )

        return {
            "admin_phone": admin_phone,
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
    admin_phone: str,
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
        "sub": admin_phone,
        "admin_phone": admin_phone,
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

@router.post("/setup", response_model=AdminSetupResponse)
async def setup_admin(
    request: AdminSetupRequest,
    session: AsyncSession = Depends(get_session),
):
    """Set up admin credentials using an invite code."""
    # Validate invite code
    stmt = select(AdminInvite).where(AdminInvite.invite_code == request.invite_code)
    result = await session.execute(stmt)
    invite = result.scalar_one_or_none()

    if not invite:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid invite code",
        )

    if invite.used_at and invite.uses_count >= invite.max_uses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invite code already used",
        )

    if invite.expires_at and invite.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invite code expired",
        )

    # Check if admin already exists
    stmt = select(AdminAuth).where(AdminAuth.admin_phone == request.admin_phone)
    result = await session.execute(stmt)
    existing_admin = result.scalar_one_or_none()

    if existing_admin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Admin with this phone already exists",
        )

    # Create admin
    pin_hash = get_password_hash(request.pin)
    admin = AdminAuth(
        admin_phone=request.admin_phone,
        pin_hash=pin_hash,
        pin_set_at=datetime.utcnow(),
    )
    session.add(admin)

    # Mark invite as used
    invite.uses_count += 1
    invite.used_at = datetime.utcnow()
    invite.used_by = request.admin_phone

    await session.commit()

    return AdminSetupResponse(
        admin_phone=request.admin_phone,
        role=invite.role,
        totp_enabled=False,
        message="Admin account created successfully",
    )


@router.post("/login", response_model=AdminLoginResponse)
async def login_admin(
    request: AdminLoginRequest,
    session: AsyncSession = Depends(get_session),
):
    """Log in as admin."""
    # Get admin
    stmt = select(AdminAuth).where(AdminAuth.admin_phone == request.admin_phone)
    result = await session.execute(stmt)
    admin = result.scalar_one_or_none()

    if not admin:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    # Check if locked
    if admin.locked_until and admin.locked_until > datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is locked. Try again later.",
        )

    # Verify PIN
    if not admin.pin_hash or not verify_password(request.pin, admin.pin_hash):
        admin.failed_attempts += 1

        # Lock after 5 failed attempts
        if admin.failed_attempts >= 5:
            admin.locked_until = datetime.utcnow() + timedelta(minutes=15)

        await session.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    # Verify TOTP if enabled
    if admin.totp_enabled:
        if not request.totp_code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="TOTP code required",
            )

        # TODO: Implement TOTP verification using pyotp
        # For now, we'll skip this check if TOTP is enabled
        # import pyotp
        # totp = pyotp.TOTP(admin.totp_secret)
        # if not totp.verify(request.totp_code):
        #     raise HTTPException(
        #         status_code=status.HTTP_401_UNAUTHORIZED,
        #         detail="Invalid TOTP code",
        #     )

    # Reset failed attempts on successful login
    admin.failed_attempts = 0
    admin.last_used = datetime.utcnow()
    await session.commit()

    # Create token
    # Get role from invite if admin was just created
    role = "admin"
    stmt = select(AdminInvite).where(AdminInvite.used_by == request.admin_phone)
    result = await session.execute(stmt)
    invite = result.scalar_one_or_none()
    if invite:
        role = invite.role

    token = create_admin_access_token(request.admin_phone, role)

    return AdminLoginResponse(
        access_token=token,
        admin_phone=request.admin_phone,
        role=role,
        totp_enabled=admin.totp_enabled,
        expires_in=settings.jwt_expire_minutes * 60,
    )


@router.get("/me", response_model=AdminMeResponse)
async def get_current_admin(
    current_admin: dict = Depends(require_viewer),
    session: AsyncSession = Depends(get_session),
):
    """Get current admin info."""
    admin = current_admin["admin"]

    return AdminMeResponse(
        admin_phone=admin.admin_phone,
        role=current_admin["role"],
        totp_enabled=admin.totp_enabled,
        pin_set_at=admin.pin_set_at,
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
    """Change admin PIN."""
    admin = current_admin["admin"]

    # Verify current PIN
    if not verify_password(request.current_pin, admin.pin_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current PIN is incorrect",
        )

    # Update PIN
    admin.pin_hash = get_password_hash(request.new_pin)
    admin.pin_set_at = datetime.utcnow()
    await session.commit()

    return AdminChangePasswordResponse(
        message="PIN changed successfully",
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
        admin.totp_set_at = datetime.utcnow()
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
    expires_at = datetime.utcnow() + timedelta(hours=request.expires_in_hours)

    invite = AdminInvite(
        invite_code=invite_code,
        email=request.email,
        role=request.role.value,
        created_by=current_admin["admin_phone"],
        expires_at=expires_at,
        max_uses=request.max_uses,
    )
    session.add(invite)
    await session.commit()

    return AdminInviteCreateResponse(
        invite_code=invite_code,
        email=request.email,
        role=request.role.value,
        expires_at=expires_at,
        max_uses=request.max_uses,
        created_by=current_admin["admin_phone"],
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
        stmt = select(AdminInvite).where(AdminInvite.used_by == admin.admin_phone)
        result = await session.execute(stmt)
        invite = result.scalar_one_or_none()
        role = invite.role if invite else "admin"

        members.append(
            AdminTeamMemberResponse(
                admin_phone=admin.admin_phone,
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


@router.patch("/team/{admin_phone}/role", response_model=AdminUpdateRoleResponse)
async def update_team_member_role(
    admin_phone: str,
    request: AdminUpdateRoleRequest,
    current_admin: dict = Depends(require_superadmin),
    session: AsyncSession = Depends(get_session),
):
    """Update an admin's role."""
    stmt = select(AdminAuth).where(AdminAuth.admin_phone == admin_phone)
    result = await session.execute(stmt)
    admin = result.scalar_one_or_none()

    if not admin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Admin not found",
        )

    # Update role in invite table
    stmt = select(AdminInvite).where(AdminInvite.used_by == admin_phone)
    result = await session.execute(stmt)
    invite = result.scalar_one_or_none()

    if invite:
        invite.role = request.role.value

    await session.commit()

    return AdminUpdateRoleResponse(
        admin_phone=admin_phone,
        role=request.role.value,
        message=f"Role updated to {request.role.value}",
    )


@router.post("/team/{admin_phone}/lock", response_model=AdminLockResponse)
async def lock_team_member(
    admin_phone: str,
    request: AdminLockRequest,
    current_admin: dict = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    """Lock or unlock an admin account."""
    stmt = select(AdminAuth).where(AdminAuth.admin_phone == admin_phone)
    result = await session.execute(stmt)
    admin = result.scalar_one_or_none()

    if not admin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Admin not found",
    )

    if request.action == "lock":
        admin.locked_until = datetime.utcnow() + timedelta(days=365)  # Lock for 1 year
        locked = True
        message = "Admin account locked"
    else:
        admin.locked_until = None
        admin.failed_attempts = 0
        locked = False
        message = "Admin account unlocked"

    await session.commit()

    return AdminLockResponse(
        admin_phone=admin_phone,
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
    if flag.admin_overrides and current_admin["admin_phone"] in flag.admin_overrides:
        enabled = True

    return FeatureFlagCheckResponse(name=flag_name, enabled=enabled)
