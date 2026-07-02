"""SQLAlchemy async ORM models for all 10 tables."""
import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import INET, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

class Base(DeclarativeBase): pass

class Customer(Base):
    __tablename__ = "customers"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    phone: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    recovery_method: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    pin_hash: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    blocked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    blocked_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    free_trials_used_today: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    free_trial_offer_sent_today: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    free_trial_offer_sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    free_trial_declined_today: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    total_orders: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    lifetime_value_ngn: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    last_active_subscription: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_message_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_order_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    replacement_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    consent_given: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    consent_version: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    consent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    support_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    platform_accounts: Mapped[list["PlatformAccount"]] = relationship("PlatformAccount", back_populates="customer")

class PlatformAccount(Base):
    __tablename__ = "platform_accounts"
    __table_args__ = (UniqueConstraint("platform", "platform_user_id", name="uq_platform_user"),)
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=True)
    platform: Mapped[str] = mapped_column(String(50), nullable=False)
    platform_user_id: Mapped[str] = mapped_column(String(100), nullable=False)
    metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    customer: Mapped[Optional[Customer]] = relationship("Customer", back_populates="platform_accounts")
    orders: Mapped[list["Order"]] = relationship("Order", back_populates="platform_account")

class MergeRequest(Base):
    __tablename__ = "merge_requests"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_account_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("platform_accounts.id"), nullable=False)
    target_account_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("platform_accounts.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    requested_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=True)
    approved_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

class Order(Base):
    __tablename__ = "orders"
    __table_args__ = (
        Index("idx_orders_customer", "customer_phone"),
        Index("idx_orders_status", "status"),
        Index("idx_orders_expires", "expires_at"),
        Index("idx_orders_created", "created_at"),
    )
    order_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    platform_account_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("platform_accounts.id"), nullable=True)
    customer_phone: Mapped[Optional[str]] = mapped_column(String(20), ForeignKey("customers.phone"), nullable=True)
    plan_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    plan_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    country: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    quantity: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    amount_paid_ngn: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)
    payment_reference: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    provider: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    provider_order_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    bunche_credential_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("bunche_credentials.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)
    ip_tested: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    ip_test_result: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    data_total_gb: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    data_remaining_gb: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    data_expires: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    ban_reported: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    screenshot_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ban_verified: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    replacement_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    refund_requested: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    refund_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    fulfilled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    cost_usd: Mapped[Optional[float]] = mapped_column(Numeric(10, 4), nullable=True)
    platform_account: Mapped[Optional[PlatformAccount]] = relationship("PlatformAccount", back_populates="orders")
    bunche_credential: Mapped[Optional["BuncheCredential"]] = relationship("BuncheCredential", back_populates="order")

class BuncheCredential(Base):
    __tablename__ = "bunche_credentials"
    __table_args__ = (
        Index("idx_bunche_cred_username", "bun_username"),
        Index("idx_bunche_cred_customer", "customer_phone"),
        Index("idx_bunche_cred_status", "status"),
        Index("idx_bunche_cred_pool", "pool_type"),
        Index("idx_bunche_cred_expires", "expires_at"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    bun_username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    customer_phone: Mapped[Optional[str]] = mapped_column(String(20), ForeignKey("customers.phone"), nullable=True)
    order_id: Mapped[Optional[str]] = mapped_column(String(20), ForeignKey("orders.order_id"), nullable=True)
    pool_type: Mapped[str] = mapped_column(String(20), default="paid", nullable=False)
    provider_name: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    provider_order_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    provider_username: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    provider_password: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    upstream_proxy_ip: Mapped[Optional[str]] = mapped_column(INET, nullable=True)
    upstream_proxy_port: Mapped[int] = mapped_column(Integer, default=1080, nullable=False)
    dante_port: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    revoke_reason: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    gb_used: Mapped[float] = mapped_column(Numeric(10, 2), default=0, nullable=False)
    order: Mapped[Optional[Order]] = relationship("Order", back_populates="bunche_credential")
    free_trial: Mapped[Optional["FreeTrial"]] = relationship("FreeTrial", back_populates="bunche_credential")

class FreeTrial(Base):
    __tablename__ = "free_trials"
    __table_args__ = (
        Index("idx_free_trials_phone_date", "phone", "trial_date"),
        Index("idx_free_trials_status", "status"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    phone: Mapped[Optional[str]] = mapped_column(String(20), ForeignKey("customers.phone"), nullable=True)
    trial_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    survey_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    reward_usd: Mapped[Optional[float]] = mapped_column(Numeric(10, 4), nullable=True)
    bunche_credential_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("bunche_credentials.id"), nullable=True)
    status: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    disclaimer_accepted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    bunche_credential: Mapped[Optional[BuncheCredential]] = relationship("BuncheCredential", back_populates="free_trial")

class PendingTrialSurvey(Base):
    __tablename__ = "pending_trial_surveys"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    free_trial_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("free_trials.id"), nullable=True)
    customer_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=True)
    survey_token: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    questions: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    responses: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

class CustomerAuditLog(Base):
    __tablename__ = "customer_audit_log"
    __table_args__ = (
        Index("idx_audit_timestamp", "timestamp"),
        Index("idx_audit_customer", "customer_hash"),
        Index("idx_audit_event", "event_type"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    request_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    customer_hash: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    event_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    order_id: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    workflow: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    status: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    details: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

class ProcessedWebhook(Base):
    __tablename__ = "processed_webhooks"
    __table_args__ = (Index("idx_processed_webhooks_id", "webhook_id"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    webhook_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    provider: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    event_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    processed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    response_sent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

class AdminAuth(Base):
    __tablename__ = "admin_auth"
    __table_args__ = (Index("idx_admin_auth_locked", "locked_until"),)
    admin_phone: Mapped[str] = mapped_column(String(20), primary_key=True)
    pin_hash: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    pin_set_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    totp_secret: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    totp_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    totp_set_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    failed_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    locked_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_used: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
