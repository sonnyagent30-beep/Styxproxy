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


# ============== Orders Schemas ==============

class BuncheCredentialBrief(BaseModel):
    """Brief credential information for order response."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    bun_username: str
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
