"""Pydantic v2 request/response models."""
import re
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Optional
from uuid import UUID

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
    model_validator,
)


# ============== Enums ==============

class PlatformEnum(str, Enum):
    """Platform types."""
    WHATSAPP = "whatsapp"
    TELEGRAM = "telegram"


class PlanTypeEnum(str, Enum):
    """Plan types."""
    ISP = "ISP"
    DC = "DC"
    RESIDENTIAL = "RESIDENTIAL"
    MOBILE = "MOBILE"


class OrderStatusEnum(str, Enum):
    """Order status values."""
    PENDING = "pending"
    PAID = "paid"
    FULFILLED = "fulfilled"
    ACTIVE = "active"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"
    PENDING_VERIFICATION = "pending_verification"


class CredentialStatusEnum(str, Enum):
    """Credential status values."""
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"
    SUSPENDED = "suspended"


class PoolTypeEnum(str, Enum):
    """Pool type values."""
    PAID = "paid"
    FREE_TRIAL = "free_trial"
    REFUNDED_RECYCLED = "refunded_recycled"


class ProtocolEnum(str, Enum):
    """Proxy protocol types."""
    HTTP = "http"
    HTTPS = "https"
    SOCKS5 = "socks5"


class MergeStatusEnum(str, Enum):
    """Merge request status values."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    COMPLETED = "completed"


class TrialStatusEnum(str, Enum):
    """Trial status values."""
    ACTIVE = "active"
    EXPIRED = "expired"
    DEAD = "dead"


# ============== Validators ==============

VALID_COUNTRIES = {"NG", "UK", "US", "DE", "JP", "AU", "BR", "SG", "KR"}


def validate_phone(phone: str) -> str:
    """Validate phone number format."""
    cleaned = re.sub(r"[\s\-]", "", phone)
    if not re.match(r"^\+?234[0-9]{10}$|^234[0-9]{10}$|^[0-9]{10,15}$", cleaned):
        raise ValueError("Invalid phone number format")
    return cleaned


def validate_country(country: str) -> str:
    """Validate country code."""
    if country.upper() not in VALID_COUNTRIES:
        raise ValueError(f"Country must be one of: {', '.join(sorted(VALID_COUNTRIES))}")
    return country.upper()


# ============== Base Schemas ==============

class PaginationParams(BaseModel):
    """Pagination parameters."""
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=20, ge=1, le=100)


class PaginatedResponse(BaseModel):
    """Paginated response wrapper."""
    data: list[Any]
    pagination: dict[str, Any]


# ============== Health Check ==============

class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    version: str = "1.0.0"
    database: str
    timestamp: datetime


# ============== Platform Schemas ==============

class PlatformRegisterRequest(BaseModel):
    """Request to register a platform account."""
    platform: PlatformEnum
    platform_user_id: str = Field(..., min_length=1, max_length=100)
    metadata: Optional[dict[str, Any]] = None


class PlatformAccountResponse(BaseModel):
    """Platform account response."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    customer_id: Optional[UUID]
    platform: str
    platform_user_id: str
    is_primary: bool
    created_at: datetime


class PlatformRegisterResponse(PlatformAccountResponse):
    """Response after registering platform account."""
    pass


class CustomerBrief(BaseModel):
    """Brief customer information."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    phone: str
    name: str


class PlatformMeResponse(BaseModel):
    """Response for /api/platform/me endpoint."""
    customer: Optional[CustomerBrief]
    accounts: list[PlatformAccountResponse]


class MergeRequestRequest(BaseModel):
    """Request to merge accounts."""
    source_account_id: UUID
    target_account_id: UUID


class MergeRequestResponse(BaseModel):
    """Merge request response."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    status: str
    source_account_id: UUID
    target_account_id: UUID
    created_at: datetime


# ============== Products Schemas ==============

class ProductResponse(BaseModel):
    """Product response."""
    plan_code: str
    plan_type: str
    country: str
    price_ngn: float
    quantity: int
    duration_days: int
    features: list[str]


class ProductsResponse(BaseModel):
    """Products list response."""
    products: list[ProductResponse]


# ============== Plans Schemas ==============

class PlanCreateRequest(BaseModel):
    """Request to create a plan."""
    plan_code: str = Field(..., min_length=1, max_length=50)
    plan_type: str = Field(..., min_length=1, max_length=20)
    country: str = Field(..., min_length=2, max_length=10)
    price_ngn: float = Field(..., ge=0)
    quantity: int = Field(default=1, ge=1)
    duration_days: int = Field(default=30, ge=1)
    features: Optional[dict[str, Any]] = None
    is_active: bool = True
    sort_order: int = 0

    @field_validator("plan_type")
    @classmethod
    def validate_plan_type(cls, v: str) -> str:
        valid_types = {"ISP", "DC", "RESIDENTIAL", "MOBILE"}
        if v.upper() not in valid_types:
            raise ValueError(f"Plan type must be one of: {', '.join(valid_types)}")
        return v.upper()

    @field_validator("country")
    @classmethod
    def validate_country_code(cls, v: str) -> str:
        return validate_country(v)


class PlanUpdateRequest(BaseModel):
    """Request to update a plan."""
    price_ngn: Optional[float] = Field(None, ge=0)
    quantity: Optional[int] = Field(None, ge=1)
    duration_days: Optional[int] = Field(None, ge=1)
    features: Optional[dict[str, Any]] = None
    is_active: Optional[bool] = None
    sort_order: Optional[int] = None


class PlanResponse(BaseModel):
    """Plan response."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    plan_code: str
    plan_type: str
    country: str
    price_ngn: float
    quantity: int
    duration_days: int
    features: Optional[dict[str, Any]]
    is_active: bool
    sort_order: int
    created_at: datetime
    updated_at: datetime


class PlansResponse(BaseModel):
    """Plans list response."""
    plans: list[PlanResponse]
    pagination: dict[str, Any]


# ============== Orders Schemas ==============

class BuncheCredentialBrief(BaseModel):
    """Brief credential information for order response."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    bun_username: str
    protocol: str
    upstream_proxy_ip: Optional[str]
    upstream_proxy_port: int
    status: str


class OrderCreateRequest(BaseModel):
    """Request to create an order."""
    plan_code: str = Field(..., min_length=1, max_length=50)
    country: str = Field(..., min_length=2, max_length=10)
    quantity: int = Field(default=1, ge=1)
    payment_reference: Optional[str] = Field(None, max_length=100)
    idempotency_key: Optional[str] = Field(None, max_length=100)

    @field_validator("country")
    @classmethod
    def validate_country_code(cls, v: str) -> str:
        return validate_country(v)


class OrderResponse(BaseModel):
    """Order response."""
    model_config = ConfigDict(from_attributes=True)

    order_id: str
    status: str
    plan_type: Optional[str]
    country: Optional[str]
    amount_paid_ngn: Optional[float]
    bunche_credential: Optional[BuncheCredentialBrief]
    created_at: datetime
    expires_at: Optional[datetime]
    customer_name: Optional[str] = None  # Only populated if customer set a name (WhatsApp/Telegram)
    is_renewable: Optional[bool] = False
    rotation_count: Optional[int] = 0
    max_rotations: Optional[int] = 3


class OrderCancelRequest(BaseModel):
    """Request to cancel an order."""
    reason: str = Field(..., max_length=500)


class OrderCancelResponse(BaseModel):
    """Response after cancelling an order."""
    order_id: str
    status: str
    refund_processed: bool
    refund_amount_ngn: Optional[float]


class OrderReportDeadRequest(BaseModel):
    """Request to report a dead IP."""
    screenshot_url: str = Field(..., max_length=500)
    issue_description: str = Field(..., max_length=500)


class OrderReportDeadResponse(BaseModel):
    """Response after reporting dead IP."""
    order_id: str
    ban_reported: bool
    status: str
    replacement_estimate_hours: int


class PrecheckRequest(BaseModel):
    """Request to precheck order availability."""
    plan_code: str = Field(..., min_length=1, max_length=50)
    country: str = Field(..., min_length=2, max_length=10)
    quantity: int = Field(default=1, ge=1)

    @field_validator("country")
    @classmethod
    def validate_country_code(cls, v: str) -> str:
        return validate_country(v)


class PrecheckResponse(BaseModel):
    """Response from precheck endpoint."""
    available: bool
    reason: Optional[str] = None
    price_ngn: Optional[float] = None
    estimated_delivery_seconds: int = 30


class ReceiptOrderResponse(BaseModel):
    """Receipt response - order with credential data for public receipt page."""
    model_config = ConfigDict(from_attributes=True)

    order_id: str
    tx_ref: Optional[str] = None
    status: str
    plan_type: Optional[str] = None
    plan_code: Optional[str] = None
    country: Optional[str] = None
    quantity: Optional[int] = None
    amount_paid_ngn: Optional[float] = None
    customer_name: Optional[str] = None
    created_at: datetime
    expires_at: Optional[datetime] = None
    bunche_credential: Optional[BuncheCredentialBrief] = None


# ============== Payments Schemas ==============

class PaymentInitiateRequest(BaseModel):
    """Request to initiate payment."""
    plan_code: str = Field(..., min_length=1, max_length=50)
    quantity: int = Field(default=1, ge=1)
    customer_phone: str = Field(..., min_length=10, max_length=20)
    callback_url: Optional[str] = Field(None, max_length=200)

    @field_validator("customer_phone")
    @classmethod
    def validate_phone_number(cls, v: str) -> str:
        return validate_phone(v)


class PaymentInitiateResponse(BaseModel):
    """Payment initiation response."""
    payment_id: str
    checkout_url: str
    amount_ngn: float
    expires_at: datetime


class PaymentStatusResponse(BaseModel):
    """Payment status response."""
    tx_ref: str
    status: str
    amount: float
    currency: str


# ============== Credentials Schemas ==============

class CredentialResponse(BaseModel):
    """Credential response."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    bun_username: str
    protocol: str
    upstream_proxy_ip: Optional[str]
    upstream_proxy_port: int
    dante_port: Optional[int]
    status: str
    expires_at: Optional[datetime]


class CredentialsListResponse(BaseModel):
    """List of credentials response."""
    credentials: list[CredentialResponse]


# ============== Trials Schemas ==============

class TrialClaimRequest(BaseModel):
    """Request to claim free trial."""
    disclaimer_accepted: bool


class TrialCredentialResponse(BaseModel):
    """Trial credential response."""
    bun_username: str
    protocol: str
    upstream_proxy_ip: str
    upstream_proxy_port: int
    expires_at: datetime


class TrialClaimResponse(BaseModel):
    """Response after claiming trial."""
    trial_id: int
    status: str
    bunche_credential: TrialCredentialResponse


class TrialSurveyRequest(BaseModel):
    """Request to submit trial survey."""
    rating: int = Field(..., ge=1, le=5)
    feedback: str = Field(..., max_length=1000)
    would_recommend: bool


class TrialSurveyResponse(BaseModel):
    """Response after submitting survey."""
    survey_id: str
    status: str
    reward_usd: Optional[float]


# ============== Admin Schemas ==============

class AdminStatsResponse(BaseModel):
    """Admin statistics response."""
    total_customers: int
    active_orders: int
    total_revenue_ngn: float
    free_trials_today: int
    active_credentials: int


class AdminCustomerResponse(BaseModel):
    """Admin customer response."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    phone: str
    name: str
    blocked: bool
    total_orders: int
    lifetime_value_ngn: float
    created_at: datetime


class AdminCustomersResponse(BaseModel):
    """Admin customers list response."""
    customers: list[AdminCustomerResponse]
    pagination: dict[str, Any]


class AdminBlockRequest(BaseModel):
    """Request to block customer."""
    reason: str = Field(..., max_length=500)


class AdminOrderResponse(BaseModel):
    """Admin order response."""
    model_config = ConfigDict(from_attributes=True)

    order_id: str
    customer_phone: Optional[str]
    plan_type: Optional[str]
    plan_code: Optional[str]
    country: Optional[str]
    amount_paid_ngn: Optional[float]
    status: str
    created_at: datetime
    expires_at: Optional[datetime]


class AdminOrdersResponse(BaseModel):
    """Admin orders list response."""
    orders: list[AdminOrderResponse]
    pagination: dict[str, Any]


class AdminOrderUpdateRequest(BaseModel):
    """Request to update order."""
    status: Optional[str] = None
    notes: Optional[str] = None
    ban_verified: Optional[str] = None


class AdminRefundRequest(BaseModel):
    """Request to refund order."""
    reason: str = Field(..., max_length=500)
    full_refund: bool = True


class AdminCredentialResponse(BaseModel):
    """Admin credential response."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    bun_username: str
    customer_phone: Optional[str]
    order_id: Optional[str]
    pool_type: str
    protocol: str
    upstream_proxy_ip: Optional[str]
    status: str
    expires_at: Optional[datetime]


class AdminCredentialsResponse(BaseModel):
    """Admin credentials list response."""
    credentials: list[AdminCredentialResponse]
    pagination: dict[str, Any]


class AdminAuditLogResponse(BaseModel):
    """Admin audit log response."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    timestamp: datetime
    customer_hash: Optional[str]
    event_type: Optional[str]
    order_id: Optional[str]
    workflow: Optional[str]
    status: Optional[str]
    details: Optional[dict[str, Any]]


class AdminAuditLogsResponse(BaseModel):
    """Admin audit logs list response."""
    logs: list[AdminAuditLogResponse]
    pagination: dict[str, Any]


class AdminWebhookLogResponse(BaseModel):
    """Admin webhook log response."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    webhook_id: str
    provider: Optional[str]
    event_type: Optional[str]
    processed_at: datetime
    response_sent: bool


class AdminWebhookLogsResponse(BaseModel):
    """Admin webhook logs list response."""
    webhooks: list[AdminWebhookLogResponse]
    pagination: dict[str, Any]


# ============== Contact Submission Schemas ==============
class ContactSubmissionResponse(BaseModel):
    """Contact submission response."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    email: str
    message: str
    phone: Optional[str]
    tx_ref: Optional[str]
    status: str
    admin_notes: Optional[str]
    created_at: datetime


class ContactSubmissionsResponse(BaseModel):
    """Contact submissions list response."""
    data: list[ContactSubmissionResponse]
    total: int


class ContactSubmissionReplyRequest(BaseModel):
    """Request to reply to a contact submission."""
    admin_notes: str = Field(..., min_length=1)


# ============== Charon Escalation Schemas ==============
class CharonEscalationResponse(BaseModel):
    """Charon escalation response."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    conversation_id: str
    customer_email: Optional[str]
    customer_phone: Optional[str]
    customer_message: str
    history_summary: Optional[str]
    status: str
    admin_notes: Optional[str]
    resolved_at: Optional[datetime]
    created_at: datetime


class EscalationsResponse(BaseModel):
    """Escalations list response."""
    data: list[CharonEscalationResponse]
    total: int


class EscalationRespondRequest(BaseModel):
    """Request to respond to an escalation."""
    admin_notes: str = Field(..., min_length=1)


class LearnedFileResponse(BaseModel):
    """Learned file response."""
    name: str
    path: str
    size: int
    modified_at: datetime


class LearnedFilesResponse(BaseModel):
    """List of learned files."""
    files: list[LearnedFileResponse]


class LearnContentResponse(BaseModel):
    """Content of a learned file."""
    name: str
    path: str
    content: str


class DeleteLearnedFileRequest(BaseModel):
    """Request to delete a learned file."""
    filename: str = Field(..., description="Filename to delete")


class DeleteLearnedFileResponse(BaseModel):
    """Response after deleting a learned file."""
    ok: bool
    message: str


# ============== Error Schemas ==============

class ErrorDetail(BaseModel):
    """Error detail."""
    field: str
    message: str


class ErrorResponse(BaseModel):
    """Error response."""
    error: dict[str, Any]


# ============== Webhook Schemas ==============

class FlutterwaveWebhookPayload(BaseModel):
    """Flutterwave webhook payload."""
    event: str
    data: dict[str, Any]


# ============== Admin Auth Schemas ==============

class AdminRole(str, Enum):
    """Admin role values."""
    ADMIN = "admin"
    SUPERADMIN = "superadmin"
    VIEWER = "viewer"


class AdminSetupCheckInviteRequest(BaseModel):
    """Step 1: Validate invite code only."""
    invite_code: str = Field(..., min_length=8, max_length=64)


class AdminSetupCheckInviteResponse(BaseModel):
    """Step 1 response: invite is valid."""
    valid: bool
    email: Optional[str] = None
    role: Optional[str] = None


class AdminSetupRequest(BaseModel):
    """Step 2: submit credentials — returns TOTP secret for user to scan."""
    invite_code: str = Field(..., min_length=8, max_length=64)
    email: str = Field(..., pattern=r"^[^@]+@[^@]+\.[^@]+$")
    password: str = Field(..., min_length=8, max_length=128)


class AdminSetupTOTPResponse(BaseModel):
    """Response after step 1: credentials accepted, TOTP setup required."""
    temp_token: str  # short-lived token to complete step 2
    totp_secret: str  # base32 secret (user can manually enter)
    otpauth_url: str  # otpauth:// URL for QR code
    backup_codes: list[str]  # 10 one-time backup codes
    message: str = "Scan the QR code with your authenticator app, then complete setup."


class AdminSetupCompleteRequest(BaseModel):
    """Step 2: complete setup after verifying TOTP code."""
    temp_token: str
    totp_code: str = Field(..., min_length=6, max_length=6)


class AdminSetupResponse(BaseModel):
    """Final response after setup is complete."""
    email: str
    role: str
    totp_enabled: bool
    message: str


class AdminLoginRequest(BaseModel):
    """Legacy: Phone + PIN login (for migration only)."""
    admin_phone: str = Field(..., min_length=10, max_length=20)
    pin: str = Field(..., min_length=4, max_length=6)
    totp_code: Optional[str] = Field(None, min_length=6, max_length=6)


class AdminLoginEmailRequest(BaseModel):
    """Email + password login (primary auth method)."""
    email: str = Field(..., pattern=r"^[^@]+@[^@]+\.[^@]+$")
    password: str = Field(..., min_length=1)
    totp_code: Optional[str] = Field(None, min_length=6, max_length=6)


class AdminLoginResponse(BaseModel):
    """Response after admin login."""
    access_token: str
    token_type: str = "bearer"
    email: str
    role: str
    totp_enabled: bool
    expires_in: int


class AdminMeResponse(BaseModel):
    """Response for /api/admin/auth/me endpoint."""
    email: str
    role: str
    totp_enabled: bool
    password_set_at: Optional[datetime]
    failed_attempts: int
    locked_until: Optional[datetime]
    created_at: datetime
    last_used: Optional[datetime]


class AdminChangePasswordRequest(BaseModel):
    """Request to change admin password."""
    current_pin: str = Field(..., min_length=8, max_length=128)  # renamed for compat
    new_pin: str = Field(..., min_length=8, max_length=128)


class AdminChangePasswordResponse(BaseModel):
    """Response after changing admin PIN."""
    message: str
    pin_set_at: datetime


class AdminChangeTOTPRequest(BaseModel):
    """Request to enable/disable TOTP."""
    action: str = Field(..., pattern="^(enable|disable)$")
    totp_code: Optional[str] = Field(None, min_length=6, max_length=6)


class AdminChangeTOTPResponse(BaseModel):
    """Response after changing TOTP status."""
    totp_enabled: bool
    message: str


class AdminInviteCreateRequest(BaseModel):
    """Request to create an admin invite."""
    email: Optional[str] = Field(None, max_length=255)
    role: AdminRole = AdminRole.ADMIN
    expires_in_hours: int = Field(default=24, ge=1, le=168)
    max_uses: int = Field(default=1, ge=1, le=100)


class AdminInviteCreateResponse(BaseModel):
    """Response after creating an admin invite."""
    invite_code: str
    email: Optional[str]
    role: str
    expires_at: Optional[datetime]
    max_uses: int
    created_by: str


class AdminInviteResponse(BaseModel):
    """Response for an admin invite."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    invite_code: str
    email: Optional[str]
    role: str
    expires_at: Optional[datetime]
    used_at: Optional[datetime]
    max_uses: int
    uses_count: int
    created_at: datetime


class AdminInvitesListResponse(BaseModel):
    """List of admin invites response."""
    invites: list[AdminInviteResponse]
    pagination: dict[str, Any]


class AdminInviteUseRequest(BaseModel):
    """Legacy: Use an invite code with phone (deprecated — use /setup instead)."""
    invite_code: str = Field(..., min_length=8, max_length=64)
    admin_phone: str = Field(..., min_length=10, max_length=20)
    pin: str = Field(..., min_length=4, max_length=6)


class AdminInviteUseResponse(BaseModel):
    """Response after using an invite code."""
    email: str
    role: str
    message: str


# ============== Feature Flag Schemas ==============

class FeatureFlagCreateRequest(BaseModel):
    """Request to create a feature flag."""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    enabled: bool = False
    enabled_for: Optional[str] = None


class FeatureFlagUpdateRequest(BaseModel):
    """Request to update a feature flag."""
    description: Optional[str] = None
    enabled: Optional[bool] = None
    enabled_for: Optional[str] = None
    admin_overrides: Optional[list[str]] = None


class FeatureFlagResponse(BaseModel):
    """Response for a feature flag."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: Optional[str]
    enabled: bool
    enabled_for: Optional[str]
    admin_overrides: Optional[list[str]]
    created_at: datetime
    updated_at: datetime


class FeatureFlagsListResponse(BaseModel):
    """List of feature flags response."""
    flags: list[FeatureFlagResponse]


class FeatureFlagCheckResponse(BaseModel):
    """Response for checking a feature flag."""
    name: str
    enabled: bool


# ============== Team Management Schemas ==============

class AdminTeamMemberResponse(BaseModel):
    """Response for an admin team member."""
    email: str
    role: str
    totp_enabled: bool
    failed_attempts: int
    locked_until: Optional[datetime]
    created_at: datetime
    last_used: Optional[datetime]


class AdminTeamListResponse(BaseModel):
    """List of admin team members response."""
    members: list[AdminTeamMemberResponse]
    pagination: dict[str, Any]


class AdminUpdateRoleRequest(BaseModel):
    """Request to update an admin's role."""
    role: AdminRole


class AdminUpdateRoleResponse(BaseModel):
    """Response after updating an admin's role."""
    email: str
    role: str
    message: str


class AdminLockRequest(BaseModel):
    """Request to lock/unlock an admin account."""
    action: str = Field(..., pattern="^(lock|unlock)$")


class AdminLockResponse(BaseModel):
    """Response after locking/unlocking an admin account."""
    email: str
    locked: bool
    locked_until: Optional[datetime]
    message: str


# ============== Blog/Post Schemas ==============

class PostStatusEnum(str, Enum):
    """Post status values."""
    DRAFT = "draft"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class PostCreateRequest(BaseModel):
    """Request to create a blog post."""
    title: str = Field(..., min_length=1, max_length=255)
    content: str = Field(..., min_length=1)
    excerpt: Optional[str] = Field(None, max_length=500)
    cover_image_url: Optional[str] = Field(None, max_length=500)
    meta_description: Optional[str] = Field(None, max_length=160)
    tags: Optional[list[str]] = None
    scheduled_at: Optional[datetime] = None
    featured: bool = False
    category_ids: Optional[list[UUID]] = None


class PostUpdateRequest(BaseModel):
    """Request to update a blog post."""
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    content: Optional[str] = None
    excerpt: Optional[str] = Field(None, max_length=500)
    cover_image_url: Optional[str] = Field(None, max_length=500)
    meta_description: Optional[str] = Field(None, max_length=160)
    tags: Optional[list[str]] = None
    scheduled_at: Optional[datetime] = None
    featured: Optional[bool] = None
    category_ids: Optional[list[UUID]] = None


class PostResponse(BaseModel):
    """Response for a blog post."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    slug: str
    content: str
    excerpt: Optional[str]
    cover_image_url: Optional[str]
    author: str
    status: str
    submitted_at: Optional[datetime]
    reviewed_by: Optional[str]
    reviewed_at: Optional[datetime]
    rejection_reason: Optional[str]
    scheduled_at: Optional[datetime]
    published_at: Optional[datetime]
    meta_description: Optional[str]
    tags: Optional[list[str]]
    featured: bool
    view_count: int
    created_at: datetime
    updated_at: datetime
    categories: Optional[list[dict]] = []


class PostBriefResponse(BaseModel):
    """Brief response for a blog post (list view)."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    slug: str
    excerpt: Optional[str]
    cover_image_url: Optional[str]
    author: str
    status: str
    published_at: Optional[datetime]
    view_count: int
    created_at: datetime


class PostListResponse(BaseModel):
    """List of blog posts response."""
    posts: list[PostBriefResponse]
    pagination: dict[str, Any]


class PostSubmitRequest(BaseModel):
    """Request to submit a post for review."""
    pass


class PostSubmitResponse(BaseModel):
    """Response after submitting a post for review."""
    post_id: UUID
    status: str
    submitted_at: datetime


class PostApproveRequest(BaseModel):
    """Request to approve a post."""
    pass


class PostRejectRequest(BaseModel):
    """Request to reject a post."""
    reason: str = Field(..., min_length=1, max_length=500)


class PostReviewResponse(BaseModel):
    """Response after reviewing a post."""
    post_id: UUID
    status: str
    reviewed_by: str
    reviewed_at: datetime


class PostPublishRequest(BaseModel):
    """Request to publish a post."""
    publish_now: bool = True


class PostPublishResponse(BaseModel):
    """Response after publishing a post."""
    post_id: UUID
    status: str
    published_at: datetime


class PostScheduleRequest(BaseModel):
    """Request to schedule a post."""
    scheduled_at: datetime


class PostScheduleResponse(BaseModel):
    """Response after scheduling a post."""
    post_id: UUID
    status: str
    scheduled_at: datetime


# ============== Category Schemas ==============

class CategoryCreateRequest(BaseModel):
    """Request to create a category."""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    color: Optional[str] = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$")


class CategoryUpdateRequest(BaseModel):
    """Request to update a category."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    color: Optional[str] = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$")


class CategoryResponse(BaseModel):
    """Response for a category."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    slug: str
    description: Optional[str]
    color: Optional[str]
    created_at: datetime
    updated_at: datetime
    post_count: Optional[int] = 0


class CategoryListResponse(BaseModel):
    """List of categories response."""
    categories: list[CategoryResponse]
    pagination: dict[str, Any]


# ============== Channel Feature Flags ==============

class ChannelConfig(BaseModel):
    """Channel configuration for Telegram/WhatsApp."""
    enabled: bool = False
    url: str = ""


class ChannelFeatureFlagsResponse(BaseModel):
    """Response for channel feature flags."""
    telegram: ChannelConfig
    whatsapp: ChannelConfig


class ChannelFeatureFlagsUpdate(BaseModel):
    """Request to update channel feature flags."""
    telegram: ChannelConfig
    whatsapp: ChannelConfig
