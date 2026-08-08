"""
Customer proxy management router.

Endpoints (all require authenticated customer via get_current_account):
  GET    /api/proxies                    - list customer's proxies
  GET    /api/proxies/{id}               - full connection details (with password)
  GET    /api/proxies/{id}/usage         - bandwidth + last activity
  POST   /api/proxies/{id}/rotate-password - rotate SOCKS5 password (3/day limit)
  PATCH  /api/proxies/{id}               - update country/sticky/alert settings
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_account
from app.database import get_session
from app.schemas_proxy import (
    ProxiesListResponse,
    ProxyFullDetails,
    ProxySummary,
    ProxyUsageResponse,
    RotatePasswordResponse,
    UpdateProxySettingsRequest,
    UpdateProxySettingsResponse,
)
from app.services.proxy_management import (
    PROXY_PORT_HTTP,
    PROXY_PORT_SOCKS5,
    PROXY_PUBLIC_HOST,
    build_curl_http_example,
    build_curl_socks5_example,
    build_python_socks5_example,
    get_credential_for_customer,
    get_credential_usage,
    list_customer_credentials,
    rotate_credential_password,
    update_credential_settings,
)

router = APIRouter(prefix="/api/proxies", tags=["proxies"])


def _to_summary(cred, order_gb_total: float = 0.0) -> ProxySummary:
    """Convert StyxproxyCredential row to ProxySummary (no password)."""
    days_remaining = 0
    if cred.expires_at:
        delta = cred.expires_at - datetime.now(timezone.utc)
        days_remaining = max(0, delta.days)

    # Daily-change counters — reset if date changed
    today = datetime.now(timezone.utc).date()
    loc_count = cred.location_change_count or 0
    rot_count = cred.rotation_mode_change_count or 0
    if cred.location_changes_reset_at != today:
        loc_count = 0
    if cred.rotation_mode_changes_reset_at != today:
        rot_count = 0

    return ProxySummary(
        id=cred.id,
        styxproxy_username=cred.styxproxy_username,
        protocol=cred.protocol or "socks5",
        pool_type=cred.pool_type,
        rotation_mode=cred.rotation_mode or "rotating",
        country_target=cred.country_target,
        status=cred.status,
        expires_at=cred.expires_at,
        last_used_at=cred.last_used_at,
        last_ip_address=str(cred.last_ip_address) if cred.last_ip_address else None,
        last_ip_country=cred.last_ip_country,
        assigned_static_ip=str(cred.assigned_static_ip) if cred.assigned_static_ip else None,
        assigned_static_session_id=cred.assigned_static_session_id,
        bandwidth_alert_pct=cred.bandwidth_alert_pct or 80,
        created_at=cred.created_at,
        sticky_session_minutes=cred.sticky_session_minutes or 0,
        session_expires_at=cred.session_expires_at,
        gb_total=order_gb_total,
        gb_used=float(cred.gb_used) if cred.gb_used else 0.0,
        days_remaining=days_remaining,
        location_changes_remaining_today=max(0, 5 - loc_count),
        rotation_mode_changes_remaining_today=max(0, 3 - rot_count),
    )


@router.get("", response_model=ProxiesListResponse)
async def list_my_proxies(
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_account),
):
    """List all proxies owned by the authenticated customer."""
    customer = current_user.get("customer")
    if not customer:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No customer profile found")

    creds = await list_customer_credentials(session, customer.phone)
    # Lazy-load orders to get gb_total per credential
    from sqlalchemy import select

    from app.models import Order

    order_map = {}
    if creds:
        ids = [c.id for c in creds]
        stmt = select(Order).where(Order.styxproxy_credential_id.in_(ids)).order_by(Order.created_at.desc())
        orders = (await session.execute(stmt)).scalars().all()
        for o in orders:
            if o.styxproxy_credential_id not in order_map:
                order_map[o.styxproxy_credential_id] = float(o.data_total_gb) if o.data_total_gb else 0.0

    return ProxiesListResponse(proxies=[_to_summary(c, order_map.get(c.id, 0.0)) for c in creds])


@router.get("/{proxy_id}", response_model=ProxyFullDetails)
async def get_proxy_details(
    proxy_id: int = Path(..., ge=1),
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_account),
):
    """Get full SOCKS5 connection details (includes password).

    Returns the plaintext password — caller MUST use HTTPS. The relay picks up
    password changes within 30s.
    """
    customer = current_user.get("customer")
    if not customer:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No customer profile found")

    cred = await get_credential_for_customer(session, proxy_id, customer.phone)
    if not cred:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proxy not found")

    # Decode password from bytea
    password = ""
    if cred.styxproxy_password:
        password = (
            cred.styxproxy_password.decode("utf-8", errors="replace")
            if isinstance(cred.styxproxy_password, bytes)
            else str(cred.styxproxy_password)
        )  # noqa: E501

    return ProxyFullDetails(
        id=cred.id,
        styxproxy_username=cred.styxproxy_username,
        styxproxy_password=password,
        proxy_host=PROXY_PUBLIC_HOST,
        proxy_port_socks5=PROXY_PORT_SOCKS5,
        proxy_port_http=PROXY_PORT_HTTP,
        protocol=cred.protocol or "socks5",
        pool_type=cred.pool_type,
        country_target=cred.country_target,
        status=cred.status,
        expires_at=cred.expires_at,
        rotation_endpoint=f"/api/proxies/{cred.id}/rotate-password",
        usage_endpoint=f"/api/proxies/{cred.id}/usage",
        curl_socks5_example=build_curl_socks5_example(cred.styxproxy_username, password),
        curl_http_example=build_curl_http_example(cred.styxproxy_username, password),
        python_socks5_example=build_python_socks5_example(cred.styxproxy_username, password),
    )


@router.get("/{proxy_id}/usage", response_model=ProxyUsageResponse)
async def get_proxy_usage(
    proxy_id: int = Path(..., ge=1),
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_account),
):
    """Get bandwidth usage + recent activity for a proxy."""
    customer = current_user.get("customer")
    if not customer:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No customer profile found")

    usage = await get_credential_usage(session, proxy_id, customer.phone)
    if not usage:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proxy not found")
    return ProxyUsageResponse(**usage)


@router.post("/{proxy_id}/rotate-password", response_model=RotatePasswordResponse)
async def rotate_my_password(
    proxy_id: int = Path(..., ge=1),
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_account),
):
    """Rotate the SOCKS5 password (3 per day max, resets at UTC midnight).

    Returns the new plaintext password — store it now, this is the only time
    it will be shown. The relay picks up the change within 30s.
    """
    customer = current_user.get("customer")
    if not customer:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No customer profile found")

    try:
        result = await rotate_credential_password(session, proxy_id, customer.phone, rotated_by="customer")
    except ValueError as e:
        msg = str(e)
        if msg.startswith("credential_not_found"):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proxy not found")
        if msg.startswith("credential_not_active:"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Proxy is {msg.split(':')[1]} — cannot rotate password",
            )
        if msg.startswith("rate_limit_exceeded:"):
            next_iso = msg.split(":", 1)[1]
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Password rotation limit reached (3/day). Try again after {next_iso}.",
                headers={"Retry-After": "86400"},
            )
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=msg)

    return RotatePasswordResponse(**result)


@router.patch("/{proxy_id}", response_model=UpdateProxySettingsResponse)
async def update_my_proxy_settings(
    body: UpdateProxySettingsRequest,
    proxy_id: int = Path(..., ge=1),
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_account),
):
    """Update proxy settings (country target, sticky session, alert threshold).

    - country_target: ISO alpha-2 (US, GB, NG, etc.). Resets session.
    - sticky_session_minutes: 0 = rotate per request, max 60. New session ID generated.
    - bandwidth_alert_pct: 50-99, alert when usage exceeds this %.
    """
    customer = current_user.get("customer")
    if not customer:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No customer profile found")

    try:
        cred = await update_credential_settings(
            session,
            proxy_id,
            customer.phone,
            country_target=body.country_target,
            sticky_session_minutes=body.sticky_session_minutes,
            bandwidth_alert_pct=body.bandwidth_alert_pct,
            rotation_mode=body.rotation_mode,
        )
    except ValueError as e:
        msg = str(e)
        if msg == "credential_not_found":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proxy not found")
        if msg.startswith("location_rate_limit_exceeded"):
            limit = msg.split(":")[1]
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Location change limit reached ({limit}/day). Resets at UTC midnight.",
            )
        if msg.startswith("rotation_mode_rate_limit_exceeded"):
            limit = msg.split(":")[1]
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rotation mode change limit reached ({limit}/day). Resets at UTC midnight.",
            )
        if msg.startswith("invalid_rotation_mode"):
            mode = msg.split(":")[1]
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid rotation_mode '{mode}'. Use 'rotating' or 'static'.",
            )
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=msg)

    changes = []
    if body.country_target is not None:
        changes.append(f"country_target={body.country_target.upper()}")
    if body.sticky_session_minutes is not None:
        changes.append(f"sticky_session_minutes={body.sticky_session_minutes}")
    if body.bandwidth_alert_pct is not None:
        changes.append(f"bandwidth_alert_pct={body.bandwidth_alert_pct}")
    if body.rotation_mode is not None:
        changes.append(f"rotation_mode={body.rotation_mode}")

    # Compute remaining-today counters
    today_d = datetime.now(timezone.utc).date()
    loc_count = cred.location_change_count or 0
    rot_count = cred.rotation_mode_change_count or 0
    if cred.location_changes_reset_at != today_d:
        loc_count = 0
    if cred.rotation_mode_changes_reset_at != today_d:
        rot_count = 0

    return UpdateProxySettingsResponse(
        credential_id=cred.id,
        country_target=cred.country_target,
        rotation_mode=cred.rotation_mode or "rotating",
        sticky_session_minutes=cred.sticky_session_minutes,
        bandwidth_alert_pct=cred.bandwidth_alert_pct,
        location_changes_remaining_today=max(0, 5 - loc_count),
        rotation_mode_changes_remaining_today=max(0, 3 - rot_count),
        message=f"Updated: {', '.join(changes) or 'no changes'}. Relay picks up within 30s.",
    )
