"""Customer proxy management schemas."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

# ─── Customer-facing endpoints ────────────────────────────────────────────────


class ProxySummary(BaseModel):
    """Summary view of a customer's proxy credential (used in list responses)."""

    id: int
    styxproxy_username: str
    protocol: str = "socks5"
    pool_type: str
    rotation_mode: str = "rotating"  # rotating | static
    country_target: Optional[str] = None
    status: str
    expires_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None
    last_ip_address: Optional[str] = None
    last_ip_country: Optional[str] = None
    assigned_static_ip: Optional[str] = None
    assigned_static_session_id: Optional[str] = None
    bandwidth_alert_pct: int = 80
    created_at: datetime
    sticky_session_minutes: int = 0
    session_expires_at: Optional[datetime] = None
    # Usage stats (joined from orders)
    gb_total: float = 0.0
    gb_used: float = 0.0
    days_remaining: int = 0
    # Daily limits
    location_changes_remaining_today: int = 5
    rotation_mode_changes_remaining_today: int = 3


class ProxyFullDetails(BaseModel):
    """Full proxy connection details (only returned on first fetch / explicit request)."""

    id: int
    styxproxy_username: str
    styxproxy_password: str  # only included in detail view (HTTPS only)
    proxy_host: str = "proxy.styxproxy.com"
    proxy_port_socks5: int = 1080
    proxy_port_http: int = 8080
    protocol: str = "socks5"
    pool_type: str
    country_target: Optional[str] = None
    status: str
    expires_at: Optional[datetime] = None
    rotation_endpoint: str  # full URL to rotate password
    usage_endpoint: str  # full URL to view usage
    # Connection examples (one-line curl commands customers can copy)
    curl_socks5_example: str
    curl_http_example: str
    python_socks5_example: str


class ProxiesListResponse(BaseModel):
    proxies: list[ProxySummary]


class RotatePasswordRequest(BaseModel):
    """Rotate password request — empty body, rate-limited 3/day per credential."""

    pass


class RotatePasswordResponse(BaseModel):
    new_password: str
    rotated_at: datetime
    rotations_remaining_today: int
    next_rotation_allowed_at: datetime


class ProxyUsageResponse(BaseModel):
    credential_id: int
    gb_total: float
    gb_used: float
    gb_remaining: float
    usage_pct: float
    bandwidth_alert_pct: int
    bytes_used: int
    last_used_at: Optional[datetime] = None
    last_ip_address: Optional[str] = None
    last_ip_country: Optional[str] = None
    days_remaining: int
    expires_at: Optional[datetime] = None
    status: str


class UpdateProxySettingsRequest(BaseModel):
    """Update mutable proxy settings (location, sticky session, rotation mode, alert threshold)."""

    country_target: Optional[str] = Field(None, min_length=2, max_length=2, description="ISO 3166-1 alpha-2 (US, GB, etc.)")  # noqa: E501
    sticky_session_minutes: Optional[int] = Field(None, ge=0, le=60, description="0 = rotate per request")
    bandwidth_alert_pct: Optional[int] = Field(None, ge=50, le=99)
    rotation_mode: Optional[str] = Field(None, description="rotating | static — switch between pool and pinned IP")


class UpdateProxySettingsResponse(BaseModel):
    credential_id: int
    country_target: Optional[str] = None
    rotation_mode: str = "rotating"
    sticky_session_minutes: int
    bandwidth_alert_pct: int
    location_changes_remaining_today: int = 5
    rotation_mode_changes_remaining_today: int = 3
    message: str


# ─── Admin endpoints ───────────────────────────────────────────────────────────


class AdminProxySummary(BaseModel):
    id: int
    styxproxy_username: str
    customer_phone: Optional[str] = None
    customer_name: Optional[str] = None
    pool_type: str
    country_target: Optional[str] = None
    status: str
    protocol: str
    upstream_host: Optional[str] = None
    upstream_type: Optional[str] = None
    created_at: datetime
    expires_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None
    last_ip_address: Optional[str] = None
    gb_used: float = 0.0
    gb_total: float = 0.0


class AdminProxiesListResponse(BaseModel):
    proxies: list[AdminProxySummary]
    total: int
    page: int
    page_size: int


class SuspendRequest(BaseModel):
    reason: str = Field(..., min_length=3, max_length=200)


class SuspendResponse(BaseModel):
    credential_id: int
    status: str
    reason: str
    suspended_at: datetime


class ResetUsageResponse(BaseModel):
    credential_id: int
    gb_used_before: float
    gb_used_after: float
    reset_at: datetime
    reset_by: str


class UpstreamHealthEntry(BaseModel):
    upstream_host: str
    upstream_port: int
    upstream_type: str
    is_reachable: bool
    latency_ms: Optional[int] = None
    last_check_at: datetime
    consecutive_failures: int
    bytes_sent: int
    bytes_failed: int


class UpstreamHealthResponse(BaseModel):
    gateways: list[UpstreamHealthEntry]
    checked_at: datetime