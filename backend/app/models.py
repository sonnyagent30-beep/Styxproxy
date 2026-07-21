"""SQLAlchemy async ORM models for all 10 tables."""
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import INET, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all models."""
    pass


# ============== Table Models ==============


class Customer(Base):
    """Customer table - Primary identity table."""
    __tablename__ = "customers"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    phone: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    recovery_method: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    pin_hash: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    blocked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    blocked_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    free_trials_used_today: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    free_trial_offer_sent_today: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    free_trial_offer_sent_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    free_trial_declined_today: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    total_orders: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    lifetime_value_ngn: Mapped[float] = mapped_column(
        Numeric(12, 2), default=0, nullable=False
    )
    last_active_subscription: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_message_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_order_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    replacement_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    consent_given: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    consent_version: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    consent_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    support_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    platform_accounts: Mapped[list["PlatformAccount"]] = relationship(
        "PlatformAccount", back_populates="customer"
    )


class PlatformAccount(Base):
    """Platform accounts table - Platform-specific accounts."""
    __tablename__ = "platform_accounts"
    __table_args__ = (
        UniqueConstraint("platform", "platform_user_id", name="uq_platform_user"),
        Index("idx_platform_device", "device_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    customer_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id"), nullable=True
    )
    platform: Mapped[str] = mapped_column(String(50), nullable=False)
    platform_user_id: Mapped[str] = mapped_column(String(100), nullable=False)
    extra_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # Anonymous device session: ties anonymous website orders to a specific browser
    # via a UUID stored in localStorage on the client. No PII — just a UUID.
    device_id: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True, unique=False
    )

    # Relationships
    customer: Mapped[Optional[Customer]] = relationship(
        "Customer", back_populates="platform_accounts"
    )
    orders: Mapped[list["Order"]] = relationship("Order", back_populates="platform_account")


class MergeRequest(Base):
    """Merge requests table - OTP-based account merging."""
    __tablename__ = "merge_requests"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    source_account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("platform_accounts.id"), nullable=False
    )
    target_account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("platform_accounts.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(20), default="pending", nullable=False
    )
    requested_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id"), nullable=True
    )
    approved_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class Order(Base):
    """Orders table - Every proxy order."""
    __tablename__ = "orders"
    __table_args__ = (
        Index("idx_orders_customer", "customer_phone"),
        Index("idx_orders_status", "status"),
        Index("idx_orders_expires", "expires_at"),
        Index("idx_orders_created", "created_at"),
    )

    order_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    platform_account_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("platform_accounts.id"), nullable=True
    )
    customer_phone: Mapped[Optional[str]] = mapped_column(
        String(20), ForeignKey("customers.phone"), nullable=True
    )
    plan_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    plan_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    country: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    quantity: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    amount_paid_ngn: Mapped[Optional[float]] = mapped_column(
        Numeric(12, 2), nullable=True
    )
    payment_reference: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True
    )
    tx_ref: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, index=True
    )
    provider: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    provider_order_id: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True
    )
    bunche_credential_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("bunche_credentials.id"), nullable=True
    )
    status: Mapped[str] = mapped_column(
        String(50), default="pending", nullable=False
    )
    ip_tested: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    ip_test_result: Mapped[Optional[str]] = mapped_column(
        String(10), nullable=True
    )
    data_total_gb: Mapped[Optional[float]] = mapped_column(
        Numeric(10, 2), nullable=True
    )
    data_remaining_gb: Mapped[Optional[float]] = mapped_column(
        Numeric(10, 2), nullable=True
    )
    data_expires: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    ban_reported: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    screenshot_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ban_verified: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    replacement_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    refund_requested: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    refund_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    fulfilled_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    cost_usd: Mapped[Optional[float]] = mapped_column(
        Numeric(10, 4), nullable=True
    )

    # Relationships
    platform_account: Mapped[Optional[PlatformAccount]] = relationship(
        "PlatformAccount", back_populates="orders"
    )
    bunche_credential: Mapped[Optional["BuncheCredential"]] = relationship(
        "BuncheCredential",
        foreign_keys="[Order.bunche_credential_id]",
    )


class BuncheCredential(Base):
    """Bunche credentials table - Bunche usernames to provider IPs."""
    __tablename__ = "bunche_credentials"
    __table_args__ = (
        Index("idx_bunche_cred_username", "bun_username"),
        Index("idx_bunche_cred_customer", "customer_phone"),
        Index("idx_bunche_cred_status", "status"),
        Index("idx_bunche_cred_pool", "pool_type"),
        Index("idx_bunche_cred_expires", "expires_at"),
        Index("idx_bunche_cred_protocol", "protocol"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    bun_username: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False
    )
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    customer_phone: Mapped[Optional[str]] = mapped_column(
        String(20), ForeignKey("customers.phone"), nullable=True
    )
    order_id: Mapped[Optional[str]] = mapped_column(
        String(20), ForeignKey("orders.order_id"), nullable=True
    )
    pool_type: Mapped[str] = mapped_column(
        String(20), default="paid", nullable=False
    )
    protocol: Mapped[str] = mapped_column(
        String(10), default="socks5", nullable=False
    )
    provider_name: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    provider_order_id: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True
    )
    provider_username: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True
    )
    provider_password: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True
    )
    upstream_proxy_ip: Mapped[Optional[str]] = mapped_column(INET, nullable=True)
    upstream_proxy_port: Mapped[int] = mapped_column(Integer, default=1080, nullable=False)
    dante_port: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), default="active", nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    revoked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    revoke_reason: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True
    )
    last_used_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    gb_used: Mapped[float] = mapped_column(
        Numeric(10, 2), default=0, nullable=False
    )
    rotation_count: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )

    # Relationships
    order: Mapped[Optional[Order]] = relationship(
        "Order",
        foreign_keys="[BuncheCredential.order_id]",
    )
    # NOTE: BuncheCredential has no back-reference to FreeTrial
    # FreeTrial → BuncheCredential via FreeTrial.bunche_credential_id FK


class FreeTrial(Base):
    """Free trials table - Free trial tracking."""
    __tablename__ = "free_trials"
    __table_args__ = (
        Index("idx_free_trials_phone_date", "phone", "trial_date"),
        Index("idx_free_trials_status", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    phone: Mapped[Optional[str]] = mapped_column(
        String(20), ForeignKey("customers.phone"), nullable=True
    )
    trial_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    survey_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    reward_usd: Mapped[Optional[float]] = mapped_column(
        Numeric(10, 4), nullable=True
    )
    bunche_credential_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("bunche_credentials.id"), nullable=True
    )
    status: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    disclaimer_accepted: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    bunche_credential: Mapped[Optional[BuncheCredential]] = relationship(
        "BuncheCredential",
        foreign_keys="[FreeTrial.bunche_credential_id]",
    )


class PendingTrialSurvey(Base):
    """Pending trial surveys table - Trial feedback."""
    __tablename__ = "pending_trial_surveys"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    free_trial_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("free_trials.id"), nullable=True
    )
    customer_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id"), nullable=True
    )
    survey_token: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False
    )
    questions: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    responses: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), default="pending", nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class CustomerAuditLog(Base):
    """Customer audit log table - Immutable audit trail."""
    __tablename__ = "customer_audit_log"
    __table_args__ = (
        Index("idx_audit_timestamp", "timestamp"),
        Index("idx_audit_customer", "customer_hash"),
        Index("idx_audit_event", "event_type"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    request_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    customer_hash: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    event_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    order_id: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    workflow: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    status: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    details: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)


class ProcessedWebhook(Base):
    """Processed webhooks table - Idempotency storage."""
    __tablename__ = "processed_webhooks"
    __table_args__ = (
        Index("idx_processed_webhooks_id", "webhook_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    webhook_id: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False
    )
    provider: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    event_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    processed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    response_sent: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    extra_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)


class AdminAuth(Base):
    """Admin auth table - Admin authentication."""
    __tablename__ = "admin_auth"
    __table_args__ = (
        Index("idx_admin_auth_locked", "locked_until"),
    )

    admin_phone: Mapped[str] = mapped_column(String(20), primary_key=True)
    pin_hash: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    pin_set_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    totp_secret: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    totp_enabled: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    totp_set_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    failed_attempts: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    locked_until: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    last_used: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class AdminInvite(Base):
    """Admin invites table - Invite codes for new admin registration."""
    __tablename__ = "admin_invites"
    __table_args__ = (
        Index("idx_admin_invites_code", "invite_code", unique=True),
        Index("idx_admin_invites_email", "email"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    invite_code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    role: Mapped[str] = mapped_column(
        String(20), default="admin", nullable=False
    )  # admin, superadmin, viewer
    created_by: Mapped[Optional[str]] = mapped_column(
        String(20), ForeignKey("admin_auth.admin_phone"), nullable=True
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    used_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    used_by: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    max_uses: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    uses_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Plan(Base):
    """Plans table - Proxy plans with pricing for each country/type combo."""
    __tablename__ = "plans"
    __table_args__ = (
        Index("idx_plans_code", "plan_code", unique=True),
        Index("idx_plans_type_country", "plan_type", "country"),
        Index("idx_plans_active", "is_active"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    plan_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    plan_type: Mapped[str] = mapped_column(String(20), nullable=False)  # ISP, DC, RESIDENTIAL, MOBILE
    country: Mapped[str] = mapped_column(String(10), nullable=False)
    price_ngn: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    duration_days: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    features: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class TriggerEvent(Base):
    """Trigger events table — anonymous behavioral trigger firings."""
    __tablename__ = "trigger_events"
    __table_args__ = (
        Index("idx_trigger_events_trigger_fired", "trigger_id", "fired_at"),
        Index("idx_trigger_events_session", "session_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(64), nullable=False)
    trigger_id: Mapped[str] = mapped_column(String(50), nullable=False)
    fired_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    outcome: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # opened_chat | dismissed | ignored | converted
    charon_msg: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class TriggerWeight(Base):
    """Trigger weights table — aggregate learning weights per trigger."""
    __tablename__ = "trigger_weights"

    trigger_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    weight: Mapped[float] = mapped_column(Numeric(5, 3), default=1.0, nullable=False)
    total_fires: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_opens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_dismissed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_converted: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    positive_rate: Mapped[float] = mapped_column(Numeric(5, 4), default=0, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class FeatureFlag(Base):
    """Feature flags table - Toggle features globally or per-admin."""
    __tablename__ = "feature_flags"
    __table_args__ = (
        Index("idx_feature_flags_name", "name", unique=True),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    enabled_for: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    # JSON array of admin phones that have this feature enabled (null = all)
    admin_overrides: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)


class ContactSubmission(Base):
    """Contact form submissions table."""
    __tablename__ = "contact_submissions"
    __table_args__ = (
        Index("idx_contact_submissions_created", "created_at"),
        Index("idx_contact_submissions_email", "email"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    tx_ref: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    admin_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class CharonEscalation(Base):
    """Charon AI sales agent escalation table."""
    __tablename__ = "charon_escalations"
    __table_args__ = (
        Index("idx_charon_escalations_conversation", "conversation_id"),
        Index("idx_charon_escalations_created", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    conversation_id: Mapped[str] = mapped_column(String(100), nullable=False)
    customer_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    customer_phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    customer_message: Mapped[str] = mapped_column(Text, nullable=False)
    history_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    admin_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class Post(Base):
    """Blog posts table - CMS for blog articles with approval workflow."""
    __tablename__ = "posts"
    __table_args__ = (
        Index("idx_posts_slug", "slug", unique=True),
        Index("idx_posts_status", "status"),
        Index("idx_posts_published", "published_at"),
        Index("idx_posts_scheduled", "scheduled_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    excerpt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    cover_image_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    author: Mapped[str] = mapped_column(String(100), nullable=False)
    # Status: draft, pending, approved, rejected, published, archived
    status: Mapped[str] = mapped_column(
        String(20), default="draft", nullable=False
    )
    # Approval workflow
    submitted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    reviewed_by: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # Scheduling
    scheduled_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    published_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # SEO
    meta_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tags: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    # Counters
    view_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
