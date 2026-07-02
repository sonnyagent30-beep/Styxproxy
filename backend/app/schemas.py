"""Pydantic v2 request/response models."""
import re
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, field_validator


class PlatformEnum(str, Enum): WHATSAPP = "whatsapp"; TELEGRAM = "telegram"
class PlanTypeEnum(str, Enum): ISP = "ISP"; DC = "DC"; RESIDENTIAL = "RESIDENTIAL"; MOBILE = "MOBILE"
class OrderStatusEnum(str, Enum): PENDING = "pending"; PAID = "paid"; FULFILLED = "fulfilled"; ACTIVE = "active"; EXPIRED = "expired"; CANCELLED = "cancelled"; REFUNDED = "refunded"; PENDING_VERIFICATION = "pending_verification"
class CredentialStatusEnum(str, Enum): ACTIVE = "active"; EXPIRED = "expired"; REVOKED = "revoked"; SUSPENDED = "suspended"
class PoolTypeEnum(str, Enum): PAID = "paid"; FREE_TRIAL = "free_trial"; REFUNDED_RECYCLED = "refunded_recycled"
class MergeStatusEnum(str, Enum): PENDING = "pending"; APPROVED = "approved"; REJECTED = "rejected"; COMPLETED = "completed"
class TrialStatusEnum(str, Enum): ACTIVE = "active"; EXPIRED = "expired"; DEAD = "dead"

VALID_COUNTRIES = {"NG", "UK", "US", "DE", "JP", "AU", "BR", "SG", "KR"}

def validate_phone(phone: str) -> str:
    cleaned = re.sub(r"[\s\-]", "", phone)
    if not re.match(r"^\+?234[0-9]{10}$|^234[0-9]{10}$|^[0-9]{10,15}$", cleaned):
        raise ValueError("Invalid phone number format")
    return cleaned

def validate_country(country: str) -> str:
    if country.upper() not in VALID_COUNTRIES:
        raise ValueError(f"Country must be one of: {', '.join(sorted(VALID_COUNTRIES))}")
    return country.upper()

class PaginationParams(BaseModel): page: int = Field(default=1, ge=1); limit: int = Field(default=20, ge=1, le=100)
class PaginatedResponse(BaseModel): data: list[Any]; pagination: dict[str, Any]

class HealthResponse(BaseModel): status: str; version: str = "1.0.0"; database: str; timestamp: datetime

class PlatformRegisterRequest(BaseModel): platform: PlatformEnum; platform_user_id: str = Field(..., min_length=1, max_length=100); metadata: Optional[dict[str, Any]] = None
class PlatformAccountResponse(BaseModel): model_config = ConfigDict(from_attributes=True); id: UUID; customer_id: Optional[UUID]; platform: str; platform_user_id: str; is_primary: bool; created_at: datetime
class PlatformRegisterResponse(PlatformAccountResponse): pass
class CustomerBrief(BaseModel): model_config = ConfigDict(from_attributes=True); id: UUID; phone: str; name: str
class PlatformMeResponse(BaseModel): customer: Optional[CustomerBrief]; accounts: list[PlatformAccountResponse]
class MergeRequestRequest(BaseModel): source_account_id: UUID; target_account_id: UUID
class MergeRequestResponse(BaseModel): model_config = ConfigDict(from_attributes=True); id: UUID; status: str; source_account_id: UUID; target_account_id: UUID; created_at: datetime

class ProductResponse(BaseModel): plan_code: str; plan_type: str; country: str; price_ngn: float; quantity: int; duration_days: int; features: list[str]
class ProductsResponse(BaseModel): products: list[ProductResponse]

class BuncheCredentialBrief(BaseModel): model_config = ConfigDict(from_attributes=True); id: int; bun_username: str; upstream_proxy_ip: Optional[str]; upstream_proxy_port: int; status: str
class OrderCreateRequest(BaseModel): plan_code: str = Field(..., min_length=1, max_length=50); country: str = Field(..., min_length=2, max_length=10); quantity: int = Field(default=1, ge=1); payment_reference: Optional[str] = Field(None, max_length=100); idempotency_key: Optional[str] = Field(None, max_length=100)
    @field_validator("country") @classmethod def validate_country_code(cls, v: str) -> str: return validate_country(v)
class OrderResponse(BaseModel): model_config = ConfigDict(from_attributes=True); order_id: str; status: str; plan_type: Optional[str]; country: Optional[str]; amount_paid_ngn: Optional[float]; bunche_credential: Optional[BuncheCredentialBrief]; created_at: datetime; expires_at: Optional[datetime]
class OrderCancelRequest(BaseModel): reason: str = Field(..., max_length=500)
class OrderCancelResponse(BaseModel): order_id: str; status: str; refund_processed: bool; refund_amount_ngn: Optional[float]
class OrderReportDeadRequest(BaseModel): screenshot_url: str = Field(..., max_length=500); issue_description: str = Field(..., max_length=500)
class OrderReportDeadResponse(BaseModel): order_id: str; ban_reported: bool; status: str; replacement_estimate_hours: int

class PaymentInitiateRequest(BaseModel): plan_code: str = Field(..., min_length=1, max_length=50); quantity: int = Field(default=1, ge=1); customer_phone: str = Field(..., min_length=10, max_length=20); callback_url: Optional[str] = Field(None, max_length=200)
    @field_validator("customer_phone") @classmethod def validate_phone_number(cls, v: str) -> str: return validate_phone(v)
class PaymentInitiateResponse(BaseModel): payment_id: str; checkout_url: str; amount_ngn: float; expires_at: datetime
class PaymentStatusResponse(BaseModel): tx_ref: str; status: str; amount: float; currency: str

class CredentialResponse(BaseModel): model_config = ConfigDict(from_attributes=True); id: int; bun_username: str; upstream_proxy_ip: Optional[str]; upstream_proxy_port: int; dante_port: Optional[int]; status: str; expires_at: Optional[datetime]
class CredentialsListResponse(BaseModel): credentials: list[CredentialResponse]

class TrialClaimRequest(BaseModel): disclaimer_accepted: bool
class TrialCredentialResponse(BaseModel): bun_username: str; upstream_proxy_ip: str; upstream_proxy_port: int; expires_at: datetime
class TrialClaimResponse(BaseModel): trial_id: int; status: str; bunche_credential: TrialCredentialResponse
class TrialSurveyRequest(BaseModel): rating: int = Field(..., ge=1, le=5); feedback: str = Field(..., max_length=1000); would_recommend: bool
class TrialSurveyResponse(BaseModel): survey_id: str; status: str; reward_usd: Optional[float]

class AdminStatsResponse(BaseModel): total_customers: int; active_orders: int; total_revenue_ngn: float; free_trials_today: int; active_credentials: int
class AdminCustomerResponse(BaseModel): model_config = ConfigDict(from_attributes=True); id: UUID; phone: str; name: str; blocked: bool; total_orders: int; lifetime_value_ngn: float; created_at: datetime
class AdminCustomersResponse(BaseModel): customers: list[AdminCustomerResponse]; pagination: dict[str, Any]
class AdminBlockRequest(BaseModel): reason: str = Field(..., max_length=500)
class AdminOrderResponse(BaseModel): model_config = ConfigDict(from_attributes=True); order_id: str; customer_phone: Optional[str]; plan_type: Optional[str]; plan_code: Optional[str]; country: Optional[str]; amount_paid_ngn: Optional[float]; status: str; created_at: datetime; expires_at: Optional[datetime]
class AdminOrdersResponse(BaseModel): orders: list[AdminOrderResponse]; pagination: dict[str, Any]
class AdminOrderUpdateRequest(BaseModel): status: Optional[str] = None; notes: Optional[str] = None; ban_verified: Optional[str] = None
class AdminRefundRequest(BaseModel): reason: str = Field(..., max_length=500); full_refund: bool = True
class AdminCredentialResponse(BaseModel): model_config = ConfigDict(from_attributes=True); id: int; bun_username: str; customer_phone: Optional[str]; order_id: Optional[str]; pool_type: str; upstream_proxy_ip: Optional[str]; status: str; expires_at: Optional[datetime]
class AdminCredentialsResponse(BaseModel): credentials: list[AdminCredentialResponse]; pagination: dict[str, Any]
class AdminAuditLogResponse(BaseModel): model_config = ConfigDict(from_attributes=True); id: int; timestamp: datetime; customer_hash: Optional[str]; event_type: Optional[str]; order_id: Optional[str]; workflow: Optional[str]; status: Optional[str]; details: Optional[dict[str, Any]]
class AdminAuditLogsResponse(BaseModel): logs: list[AdminAuditLogResponse]; pagination: dict[str, Any]
class AdminWebhookLogResponse(BaseModel): model_config = ConfigDict(from_attributes=True); id: int; webhook_id: str; provider: Optional[str]; event_type: Optional[str]; processed_at: datetime; response_sent: bool
class AdminWebhookLogsResponse(BaseModel): webhooks: list[AdminWebhookLogResponse]; pagination: dict[str, Any]

class ErrorDetail(BaseModel): field: str; message: str
class ErrorResponse(BaseModel): error: dict[str, Any]
class FlutterwaveWebhookPayload(BaseModel): event: str; data: dict[str, Any]
