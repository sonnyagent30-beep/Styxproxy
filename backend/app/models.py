"""SQLAlchemy async ORM models for all 10 tables."""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    ARRAY,
    JSON,
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
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
    # ─── Referral system (Sprint 2 / BIZ STYXv2-004 §4.3) ────────────────────
    # 20-char random unique string shown to the customer as their referral code.
    # Null only for rows created before this migration was applied.
    referral_code: Mapped[Optional[str]] = mapped_column(String(20), unique=True, nullable=True, index=True)
    # UUID of the customer who referred this one (null = organic, no referrer).
    referred_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id"), nullable=True, index=True
    )

    # Relationships
    platform_accounts: Mapped[list["PlatformAccount"]] = relationship("PlatformAccount", back_populates="customer")
    # Customers this customer has referred — REMOVED 2026-08-19
    # The referred_customers / referrer self-referential relationships crashed
    # SQLAlchemy mapper init ("both of the same direction ONETOMANY").
    # The referred_by FK column is preserved; queries join via it manually.


class ReferralCredit(Base):
    """Referral credits table — ₦500 credit applied to referrer when referee makes first payment.

    One row per successful referral. `applied_at` is set to the moment the credit
    was applied (first confirmed Flutterwave payment of the referee). If the
    referee never makes a payment `applied_at` stays null — the credit is pending.
    """

    __tablename__ = "referral_credits"
    __table_args__ = (
        Index("idx_referral_credits_referrer", "referrer_customer_id"),
        Index("idx_referral_credits_referee", "referee_customer_id"),
        Index("idx_referral_credits_applied", "applied_at"),
        # Each referee can only earn once (first payment triggers the credit)
        UniqueConstraint("referee_customer_id", name="uq_one_credit_per_referee"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # The customer whose account receives the ₦500 credit
    referrer_customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False
    )
    # The customer who was referred (earns the credit once they pay)
    referee_customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False
    )
    # Credit amount in nano-naira (500 NGN = 500_000_000 nGN)
    credit_amount_nGN: Mapped[int] = mapped_column(BigInteger, nullable=False, default=500_000_000)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    # Null = pending (referee hasn't paid yet); set when credit is applied
    applied_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    # tx_ref of the referee's first payment that triggered this credit
    referee_payment_tx_ref: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)

    # Relationships
    referrer: Mapped["Customer"] = relationship(
        "Customer", foreign_keys="[ReferralCredit.referrer_customer_id]"
    )
    referee: Mapped["Customer"] = relationship(
        "Customer", foreign_keys="[ReferralCredit.referee_customer_id]"
    )


class PlatformAccount(Base):
    """Platform accounts table - Platform-specific accounts."""

    __tablename__ = "platform_accounts"
    __table_args__ = (
        UniqueConstraint("platform", "platform_user_id", name="uq_platform_user"),
        Index("idx_platform_device", "device_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id"), nullable=True
    )
    platform: Mapped[str] = mapped_column(String(50), nullable=False)
    platform_user_id: Mapped[str] = mapped_column(String(100), nullable=False)
    extra_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # Anonymous device session: ties anonymous website orders to a specific browser
    # via a UUID stored in localStorage on the client. No PII — just a UUID.
    device_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, unique=False)

    # Relationships
    customer: Mapped[Optional[Customer]] = relationship("Customer", back_populates="platform_accounts")
    orders: Mapped[list["Order"]] = relationship("Order", back_populates="platform_account")
    trial_sessions: Mapped[list["TrialSession"]] = relationship("TrialSession", back_populates="platform_account")


class MergeRequest(Base):
    """Merge requests table - OTP-based account merging."""

    __tablename__ = "merge_requests"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("platform_accounts.id"), nullable=False
    )
    target_account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("platform_accounts.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    requested_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id"), nullable=True
    )
    approved_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


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
    customer_phone: Mapped[Optional[str]] = mapped_column(String(20), ForeignKey("customers.phone"), nullable=True)
    plan_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    plan_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    country: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    quantity: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    amount_paid_ngn: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)
    payment_reference: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    tx_ref: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    provider: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    provider_order_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    styxproxy_credential_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("styxproxy_credentials.id"), nullable=True
    )
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
    rotation_mode: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # rotating | static
    # Sprint 13 — city picker (residential/mobile orders)
    city_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("cities.id", ondelete="SET NULL"), nullable=True)
    city_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    # Referral: tx_ref of the referee's payment that earned the referrer a credit (Sprint 2)
    referral_tx_ref: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    # S2.5 — Renewal reminder tracking
    # Number of renewal reminder emails sent for this order.
    emails_sent: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # Timestamp of the last renewal reminder email sent (null = never sent).
    reminder_sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    platform_account: Mapped[Optional[PlatformAccount]] = relationship("PlatformAccount", back_populates="orders")
    styxproxy_credential: Mapped[Optional["StyxproxyCredential"]] = relationship(
        "StyxproxyCredential",
        foreign_keys="[Order.styxproxy_credential_id]",
    )


class StyxproxyCredential(Base):
    """Styxproxy credentials table — Styxproxy usernames to provider IPs."""

    __tablename__ = "styxproxy_credentials"
    __table_args__ = (
        Index("idx_styxproxy_cred_username", "styxproxy_username"),
        Index("idx_styxproxy_cred_customer", "customer_phone"),
        Index("idx_styxproxy_cred_status", "status"),
        Index("idx_styxproxy_cred_pool", "pool_type"),
        Index("idx_styxproxy_cred_expires", "expires_at"),
        Index("idx_styxproxy_cred_protocol", "protocol"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    styxproxy_username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    # Proxy auth credential — stored as encrypted bytes (Fernet ciphertext).
    # The plaintext is needed for the receipt / email delivery / rotation, but
    # should not be visible to anyone with raw DB read access.
    #
    # Use get_password() / set_password() rather than touching this attribute
    # directly — they handle encryption transparently. Read the raw column for
    # debugging only.
    styxproxy_password: Mapped[Optional[bytes]] = mapped_column(LargeBinary, nullable=True)

    def get_password(self) -> Optional[str]:
        """Decrypt and return the plaintext proxy password.

        Returns None if the password is not set, encryption is not configured,
        or decryption fails (wrong key / tampered ciphertext).
        """
        # Imported lazily to avoid a circular import at module load time.
        from app.services.crypto import decrypt_credential

        return decrypt_credential(self.styxproxy_password)

    def set_password(self, plaintext: str) -> None:
        """Encrypt and store the proxy password.

        No-op (logs a warning) if encryption is not configured — refusing
        to write plaintext is the whole point of this column.
        """
        from app.services.crypto import encrypt_credential

        ciphertext = encrypt_credential(plaintext)
        if ciphertext is None:
            import logging

            logging.getLogger(__name__).error(
                "Refusing to set styxproxy_password — CRED_ENCRYPTION_KEY not configured. "
                "Set the key in your secrets manager (Doppler/Vault/SSM)."
            )
            return
        self.styxproxy_password = ciphertext

    customer_phone: Mapped[Optional[str]] = mapped_column(String(20), ForeignKey("customers.phone"), nullable=True)
    order_id: Mapped[Optional[str]] = mapped_column(String(20), ForeignKey("orders.order_id"), nullable=True)
    pool_type: Mapped[str] = mapped_column(String(20), default="paid", nullable=False)
    protocol: Mapped[str] = mapped_column(String(10), default="socks5", nullable=False)
    provider_name: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    provider_order_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    provider_username: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    provider_password: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    upstream_proxy_ip: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )  # TEXT (was INET pre-migration 018)
    upstream_proxy_port: Mapped[int] = mapped_column(Integer, default=1080, nullable=False)
    dante_port: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    revoke_reason: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    gb_used: Mapped[float] = mapped_column(Numeric(10, 2), default=0, nullable=False)
    rotation_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # ─── Customer proxy management (added Jul 30) ─────────────────────────
    # Password rotation tracking (rate-limited 3/day per customer)
    password_rotated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    password_rotations_today: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    password_rotations_reset_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Targeting + sticky session
    country_target: Mapped[Optional[str]] = mapped_column(String(2), nullable=True)
    sticky_session_minutes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    session_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    session_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Bandwidth alerting (alert customer when usage exceeds N% of plan)
    bandwidth_alert_pct: Mapped[int] = mapped_column(Integer, default=80, nullable=False)

    # Last seen (for activity feeds)
    last_ip_country: Mapped[Optional[str]] = mapped_column(String(2), nullable=True)
    last_ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)  # IPv6 max 45 chars

    # ─── Rotation mode + static IP pinning (added Jul 30) ────────────────
    # rotating = pool, IP changes per request (Rayobyte -country-XX password)
    # static   = pinned IP via Rayobyte -session-XXXX-country-XX password
    rotation_mode: Mapped[str] = mapped_column(String(20), default="rotating", nullable=False)
    assigned_static_ip: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    assigned_static_session_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    last_static_assigned_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Daily rate-limit counters (reset at UTC midnight)
    location_change_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rotation_mode_change_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    location_changes_reset_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    rotation_mode_changes_reset_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    order: Mapped[Optional[Order]] = relationship(
        "Order",
        foreign_keys="[StyxproxyCredential.order_id]",
    )
    # NOTE: StyxproxyCredential has no back-reference to FreeTrial
    # FreeTrial → StyxproxyCredential via FreeTrial.styxproxy_credential_id FK


class FreeTrial(Base):
    """Free trials table - Free trial tracking."""

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
    styxproxy_credential_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("styxproxy_credentials.id"), nullable=True
    )
    status: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    disclaimer_accepted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    styxproxy_credential: Mapped[Optional[StyxproxyCredential]] = relationship(
        "StyxproxyCredential",
        foreign_keys="[FreeTrial.styxproxy_credential_id]",
    )


# Sprint 2 — S2.3 / S2.4: Trial session tracking for TheoremReach → trial pipeline.
# Each row represents a single trial grant: one TheoremReach survey completion
# = 2 hours of trial credit, capped at 24 hours per device_id.
#
# trial_started_at / trial_expires_at are the canonical source of truth for
# "how long does this trial last?" — this drives both the n8n reminder cron
# (fires 24 hours before trial_expires_at) and the S2.4 conversion tracking.
#
# device_id here matches platform_accounts.device_id — used by the n8n workflow
# to look up the platform_account that initiated the survey flow.
class TrialSession(Base):
    """Trial sessions table — tracks trial grants from TheoremReach surveys."""

    __tablename__ = "trial_sessions"
    __table_args__ = (
        Index("idx_trial_sessions_device_id", "device_id"),
        Index("idx_trial_sessions_status", "status"),
        Index("idx_trial_sessions_expires", "trial_expires_at"),
        Index("idx_trial_sessions_started", "trial_started_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Which platform_account this trial belongs to (used to look up customer).
    # Nullable: anonymous users who haven't linked a phone number yet.
    platform_account_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("platform_accounts.id"), nullable=True
    )

    # TheoremReach device identifier — unique per-browser, set as localStorage UUID.
    device_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)

    # The survey that triggered this trial grant.
    survey_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, unique=True)

    # Trial window
    trial_started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    trial_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Cumulative hours granted from all surveys for this device.
    # 1 survey = 2 hours. Accumulated up to MAX_TOTAL_TRIAL_HOURS.
    total_hours_granted: Mapped[float] = mapped_column(Numeric(6, 2), default=0.0, nullable=False)

    # Credentials granted as part of this trial session.
    styxproxy_credential_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("styxproxy_credentials.id"), nullable=True
    )

    # 3proxy port allocated for this trial session.
    threeproxy_port: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Delivery status
    status: Mapped[str] = mapped_column(
        String(20),
        default="pending",  # pending | active | expiring_soon | expired | converted
        nullable=False,
    )

    # Trial-to-paid conversion
    converted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Audit
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    platform_account: Mapped[Optional["PlatformAccount"]] = relationship(
        "PlatformAccount", back_populates="trial_sessions"
    )
    styxproxy_credential: Mapped[Optional["StyxproxyCredential"]] = relationship(
        "StyxproxyCredential",
        foreign_keys="[TrialSession.styxproxy_credential_id]",
    )


class PendingTrialSurvey(Base):
    """Pending trial surveys table - Trial feedback."""

    __tablename__ = "pending_trial_surveys"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    free_trial_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("free_trials.id"), nullable=True)
    customer_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id"), nullable=True
    )
    survey_token: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    questions: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    responses: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class CustomerAuditLog(Base):
    """Customer audit log table - Immutable audit trail."""

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
    """Processed webhooks table - Idempotency storage."""

    __tablename__ = "processed_webhooks"
    __table_args__ = (Index("idx_processed_webhooks_id", "webhook_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    webhook_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    provider: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    event_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    processed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    response_sent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    extra_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)


class IdempotencyResponse(Base):
    """Idempotency responses table — caches POST handler responses by key_hash.

    Created via raw SQL on startup (see idempotency.py). This ORM model
    is used only for type-safe query construction; it does NOT manage
    table creation or schema.
    """

    __tablename__ = "idempotency_responses"

    key_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    status_code: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    response_body: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    response_headers: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AdminAuth(Base):
    """Admin auth table - Admin authentication."""

    __tablename__ = "admin_auth"
    __table_args__ = (
        Index("idx_admin_auth_locked", "locked_until"),
        Index("idx_admin_auth_email", "email", unique=True),
    )

    # UUID primary key
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # Legacy: phone kept for backward compat during migration
    admin_phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    # Primary identity (unique, used for login)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    # Password auth (replaces pin_hash)
    password_hash: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # Legacy: kept for migration path
    pin_hash: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    pin_set_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    totp_secret: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    totp_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    totp_set_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    failed_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    locked_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_used: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    # Role column - source of truth for admin role
    role: Mapped[str] = mapped_column(
        String(20), default="admin", nullable=False, index=True
    )  # admin, superadmin, viewer
    # Password reset tokens
    reset_token_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    reset_token_expires: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class AdminInvite(Base):
    """Admin invites table - Invite codes for new admin registration."""

    __tablename__ = "admin_invites"
    __table_args__ = (
        Index("idx_admin_invites_code", "invite_code", unique=True),
        Index("idx_admin_invites_email", "email"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    invite_code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    role: Mapped[str] = mapped_column(String(20), default="admin", nullable=False)  # admin, superadmin, viewer
    created_by: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )  # email of admin who issued the invite (Jul 24: widened from 20)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    used_by: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )  # email of admin who consumed the invite (Jul 23: widened from 20)
    max_uses: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    uses_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    feature_overrides: Mapped[Optional[list]] = mapped_column(
        JSON, nullable=True
    )  # Jul 24: list of feature-flag names granted by the superadmin at invite time


class AdminAuditLog(Base):
    """Admin audit log table - Immutable audit trail for admin actions.

    Matches existing schema in production Postgres (integer PK + admin_phone).
    """

    __tablename__ = "admin_audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    admin_phone: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


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
    # per-GB price for residential/mobile (Jul 30 2026 — Sprint 13)
    # For DC/ISP plans, NULL; the price_ngn column is the per-IP price.
    price_per_gb: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    duration_days: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    features: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # ─── Rotation + location flexibility (added Jul 30) ──────────────────
    # rotation_mode = 'rotating' (pool) | 'static' (pinned IP) | 'both' (customer picks)
    # supports_country_change = false for ISP/Datacenter (location is fixed per IP)
    # static_price_multiplier = static mode costs this × base price
    rotation_mode: Mapped[str] = mapped_column(String(20), default="both", nullable=False)
    supports_country_change: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    static_price_multiplier: Mapped[float] = mapped_column(Numeric(4, 2), default=2.50, nullable=False)
    # ─── Sprint 13: pricing model + city picker ─────────────────────────
    # min_gb: minimum GB customer can purchase (residential/mobile)
    # max_gb: maximum GB customer can purchase
    # gb_tiers: suggested GB tiers shown in the FE dropdown (e.g. [5,10,20,50])
    # supports_city: TRUE for residential/mobile (customer picks country+city)
    min_gb: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    max_gb: Mapped[int] = mapped_column(Integer, default=50, nullable=False)
    gb_tiers: Mapped[Optional[list]] = mapped_column(ARRAY(Integer), nullable=True)
    supports_city: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class City(Base):
    """Cities table — provider-supported cities per country (Sprint 13).

    Populated from Rayobyte's residential gateway for residential/mobile plans.
    Customers can pick a city for exact targeting or skip (="random") to get
    a pool IP from the country.
    """

    __tablename__ = "cities"
    __table_args__ = (
        Index("idx_cities_country", "country_code"),
        Index("idx_cities_active", "is_active"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    country_code: Mapped[str] = mapped_column(String(2), nullable=False)
    city_name: Mapped[str] = mapped_column(String(100), nullable=False)
    state_code: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    isp_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    latitude: Mapped[Optional[float]] = mapped_column(Numeric(9, 6), nullable=True)
    longitude: Mapped[Optional[float]] = mapped_column(Numeric(9, 6), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    source: Mapped[Optional[str]] = mapped_column(String(20), default="rayobyte", nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class PlanCity(Base):
    """Plan <-> City mapping (admin can restrict cities per plan)."""

    __tablename__ = "plan_cities"
    plan_id: Mapped[int] = mapped_column(Integer, ForeignKey("plans.id", ondelete="CASCADE"), primary_key=True)
    city_id: Mapped[int] = mapped_column(Integer, ForeignKey("cities.id", ondelete="CASCADE"), primary_key=True)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


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
    fired_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    outcome: Mapped[str] = mapped_column(String(20), nullable=False)  # opened_chat | dismissed | ignored | converted
    charon_msg: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


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
    __table_args__ = (Index("idx_feature_flags_name", "name", unique=True),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
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

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    tx_ref: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    admin_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
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

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[str] = mapped_column(String(100), nullable=False)
    customer_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    customer_phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    customer_message: Mapped[str] = mapped_column(Text, nullable=False)
    history_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    admin_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class CharonContext(Base):
    """Charon AI sales agent — per-conversation rolling summary.

    Theme C — give Charon persistent memory across page reloads. Today
    Charon reconstructs context from the escalations table and the
    knowledge base only. With this table, Charon can:
      - Remember the customer's last intent (e.g. "asked about 3GB plan")
      - Resume a conversation if the customer returns within 24h
      - Surface "what we talked about last time" to the agent

    Retention: 24h, enforced by cleanup_charon_context cron (Theme C).
    After 24h customers get a fresh conversation rather than stale context.

    Uniqueness: one row per conversation_id (UPSERT on the next turn).
    """

    __tablename__ = "charon_context"
    __table_args__ = (
        Index("idx_charon_context_conversation", "conversation_id"),
        Index("idx_charon_context_expires", "expires_at"),
        Index("idx_charon_context_customer_email", "customer_email"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    session_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    customer_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    customer_phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    summary_json: Mapped[str] = mapped_column(Text, nullable=False)
    message_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_intent: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    last_topics: Mapped[Optional[list[str]]] = mapped_column(ARRAY(String(100)), nullable=True)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Country(Base):
    """ISO 3166-1 country reference table.

    Theme C — replace the hardcoded `available_countries` dict in
    `app/services/provider.py` with a queryable DB table. Lets the
    admin panel flip is_supported / plan_type_eligible without a
    deploy, and lets Charon answer country questions from live data
    instead of a frozen list.

    Seeded with all 195 ISO 3166-1 entries (see scripts/seed_countries.py).
    The 9 currently-enabled countries in provider.py are seeded with
    is_supported=TRUE; the rest are FALSE by default.
    """

    __tablename__ = "countries"
    __table_args__ = (
        Index("idx_countries_supported", "is_supported"),
        Index("idx_countries_eligible", "plan_type_eligible"),
        Index("idx_countries_region", "region"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(2), nullable=False, unique=True)
    code3: Mapped[str] = mapped_column(String(3), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    flag_emoji: Mapped[str] = mapped_column(String(8), nullable=False)
    region: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    subregion: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    plan_type_eligible: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_supported: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    proxy_pool: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
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

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    excerpt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    cover_image_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    author: Mapped[str] = mapped_column(String(100), nullable=False)
    # Status: draft, pending, approved, rejected, published, archived
    status: Mapped[str] = mapped_column(String(20), default="draft", nullable=False)
    # Approval workflow
    submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_by: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # Scheduling
    scheduled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    # SEO
    meta_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tags: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    # Featured flag
    featured: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # Counters
    view_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class Category(Base):
    """Blog categories for organizing posts."""

    __tablename__ = "categories"
    __table_args__ = (Index("idx_categories_slug", "slug", unique=True),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    color: Mapped[Optional[str]] = mapped_column(String(7), nullable=True)  # Hex color
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class PostCategory(Base):
    """Junction table for posts <-> categories many-to-many relationship."""

    __tablename__ = "post_categories"

    post_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("posts.id", ondelete="CASCADE"), primary_key=True
    )
    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("categories.id", ondelete="CASCADE"), primary_key=True
    )


class SupportThread(Base):
    """Support threads table - tracks customer support conversations."""

    __tablename__ = "support_threads"
    __table_args__ = (
        Index("idx_support_threads_customer_email", "customer_email"),
        Index("idx_support_threads_status", "status"),
        Index("idx_support_threads_last_message", "last_message_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_email: Mapped[str] = mapped_column(String(255), nullable=False)
    customer_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="open", nullable=False)  # open, replied, closed
    order_id: Mapped[Optional[str]] = mapped_column(String(20), ForeignKey("orders.order_id"), nullable=True)
    resend_last_message_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    last_message_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class SupportMessage(Base):
    """Support messages table - individual messages in support threads."""

    __tablename__ = "support_messages"
    __table_args__ = (
        Index("idx_support_messages_thread", "thread_id"),
        Index("idx_support_messages_created", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    thread_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("support_threads.id", ondelete="CASCADE"), nullable=False
    )
    direction: Mapped[str] = mapped_column(String(20), nullable=False)  # inbound, outbound
    from_email: Mapped[str] = mapped_column(String(255), nullable=False)
    to_email: Mapped[str] = mapped_column(String(255), nullable=False)
    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    body_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    body_html: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    resend_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    in_reply_to: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    references: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class HealthSnapshot(Base):
    """Health history table — Time-series of system health probes.

    Theme A M5: a cron job polls health every minute and writes a snapshot.
    GET /api/admin/health/history reads these for time-series display in
    the admin dashboard. Used for incident triage (was it always down or
    did it just drop?), uptime monitoring (SLO calculations), and
    trend spotting (gradually increasing DB latency, etc.).

    Retention: 7 days (caller should add a cron to prune older rows).
    Index on created_at DESC so time-range queries are fast.
    """

    __tablename__ = "health_snapshots"
    __table_args__ = (Index("idx_health_snapshots_created", "created_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # Component status flags
    db_connected: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    redis_connected: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    m2_connected: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    litellm_connected: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    ollama_connected: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # Aggregated
    overall_status: Mapped[str] = mapped_column(String(20), nullable=False, default="unknown")
    charon_available: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # Performance
    total_latency_ms: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    # Errors
    error_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # Source
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="cron")
    # Timestamp
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class AdminPermission(Base):
    """Permission code catalog (Theme C).

    The permission system lives in 4 tables:
      - admin_permissions: the catalog of all valid permission codes
      - admin_role_permissions: role → default grants (superadmin/admin/viewer)
      - admin_user_permissions: per-admin overrides (grant or revoke)
      - permission_change_requests: workflow for non-superadmin requests

    Migration 016 created them. The seed (scripts/seed_permissions.py)
    populates ~50 permission codes + role defaults matching the existing
    hardcoded RoleChecker in app/routers/auth.py.

    Note: today's auth code still uses the 3-role RoleChecker. The
    permission tables are SETUP for the future granular permission
    system; the existing flow is unchanged.
    """

    __tablename__ = "admin_permissions"
    __table_args__ = (Index("idx_admin_permissions_category", "category"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    is_sensitive: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class AdminRolePermission(Base):
    """Role → permission defaults (Theme C)."""

    __tablename__ = "admin_role_permissions"
    __table_args__ = (Index("idx_admin_role_permissions_role", "role"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    permission_code: Mapped[str] = mapped_column(String(64), nullable=False)
    granted: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class AdminUserPermission(Base):
    """Per-admin permission overrides (Theme C)."""

    __tablename__ = "admin_user_permissions"
    __table_args__ = (Index("idx_admin_user_permissions_email", "admin_email"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    admin_email: Mapped[str] = mapped_column(String(255), nullable=False)
    permission_code: Mapped[str] = mapped_column(String(64), nullable=False)
    granted: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    granted_by: Mapped[str] = mapped_column(String(255), nullable=False)
    granted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class PermissionChangeRequest(Base):
    """Permission request workflow (Theme C).

    Admins who lack a permission can file a request here. Superadmins
    approve/reject from the admin panel. A 7-day auto-expire keeps the
    queue short if reviewers are unavailable.
    """

    __tablename__ = "permission_change_requests"
    __table_args__ = (
        Index("idx_pcr_status", "status"),
        Index("idx_pcr_target_email", "target_email"),
        Index("idx_pcr_target_role", "target_role"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    requested_by: Mapped[str] = mapped_column(String(255), nullable=False)
    target_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    target_role: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    permission_code: Mapped[str] = mapped_column(String(64), nullable=False)
    desired_state: Mapped[bool] = mapped_column(Boolean, nullable=False)
    justification: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    reviewed_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewer_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class RlsPolicy(Base):
    """Single source of truth for which tables have RLS enabled (Theme C).

    RLS was rolled back in commit 0ba7241 (security review found the
    policies too restrictive). This table tracks future RLS decisions:
    - policy_enabled: TRUE if RLS is currently active on this table
    - applied_at: when RLS was last enabled (NULL if never)
    - rolled_back_at: when RLS was last disabled (NULL if never rolled back)
    - last_audit: when admins last reviewed the policy

    INSERT-only updates: never DELETE. Old entries remain as audit trail.
    """

    __tablename__ = "rls_policy"
    __table_args__ = (Index("idx_rls_policy_enabled", "policy_enabled"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    table_name: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    policy_name: Mapped[str] = mapped_column(String(100), nullable=False)
    policy_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    applied_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    rolled_back_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_audit: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # Sprint 15 — added via migration 022
    using_clause: Mapped[Optional[str]] = mapped_column(Text, nullable=True, server_default="true")
    with_check: Mapped[Optional[str]] = mapped_column(Text, nullable=True, server_default="true")
    role_name: Mapped[Optional[str]] = mapped_column(String(32), nullable=True, server_default="styxproxy_app")
    policy_status: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, server_default="not_started")
    created_by: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class AdminTotpSession(Base):
    """TOTP session tokens for "remember this device" feature (Theme C).

    When an admin successfully TOTP-authenticates, the API issues a
    session_token (in the Set-Cookie header). Subsequent requests with
    that cookie skip TOTP for `expires_at` days.

    The token is hashed (Argon2 via pwd_context) before storage. The
    raw token never touches the DB. Revoke by setting revoked_at.

    TTL: a daily cron will clean up expired rows (cleanup_admin_totp_sessions).
    """

    __tablename__ = "admin_totp_sessions"
    __table_args__ = (
        Index("idx_admin_totp_sessions_email", "admin_email"),
        Index("idx_admin_totp_sessions_expires", "expires_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    admin_email: Mapped[str] = mapped_column(String(255), nullable=False)
    session_token_hash: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    granted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    device_fingerprint: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(INET, nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class CharonBlogChunk(Base):
    """Chunked blog content for Charon's RAG knowledge base (Theme C).

    Blog posts are large (5000+ words). Charon's knowledge search
    retrieves top_k=4 chunks per query. Splitting posts into ~500-word
    chunks with their headings gives Charon the surrounding context
    without overwhelming the LLM context window.

    Embedding field is BYTEA so we can store serialized vectors
    (numpy or whatever the embedding model returns). The initial
    backfill script (scripts/seed_blog_chunks.py) populates published
    posts only — drafts/drafts are skipped.
    """

    __tablename__ = "charon_blog_chunks"
    __table_args__ = (Index("idx_charon_blog_chunks_post", "post_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    post_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    heading: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    word_count: Mapped[int] = mapped_column(Integer, nullable=False)
    embedding: Mapped[Optional[bytes]] = mapped_column(LargeBinary, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class DanteUser(Base):
    """Dante SOCKS proxy user accounts (Theme C).

    Each customer who buys a Styxproxy plan gets a Dante user account
    on the Contabo fleet. The table tracks credentials, port range,
    expiry, and bandwidth usage. The dante_auth service (port 1081)
    looks up users here to authenticate.

    bytes_used is updated by dante-auth on each connection (writes
    sampled to avoid hot-row contention). Bytes reset is handled by
    the plan renewal cron (Theme C future work).
    """

    __tablename__ = "dante_users"
    __table_args__ = (
        Index("idx_dante_users_customer", "customer_id"),
        Index("idx_dante_users_active", "is_active"),
        Index("idx_dante_users_expires", "expires_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    customer_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    username: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    port_range_low: Mapped[int] = mapped_column(Integer, default=10000, nullable=False)
    port_range_high: Mapped[int] = mapped_column(Integer, default=60000, nullable=False)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    bytes_used: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class PlanSettings(Base):
    """Plan settings table - Global and country-specific pricing rules."""

    __tablename__ = "plan_settings"
    __table_args__ = (
        Index("idx_plan_settings_type_country", "plan_type", "country"),
        Index("idx_plan_settings_active", "is_active"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    plan_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    country: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    setting_key: Mapped[str] = mapped_column(String(50), nullable=False)
    setting_value: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    valid_from: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    valid_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class CharonAbAssignment(Base):
    """A/B test assignment for Charon conversations."""

    __tablename__ = "charon_ab_assignments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    variant: Mapped[str] = mapped_column(String(1), nullable=False)
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class CharonAbOutcome(Base):
    """A/B test outcome per conversation session."""

    __tablename__ = "charon_ab_outcomes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(64), nullable=False)
    variant: Mapped[str] = mapped_column(String(1), nullable=False)
    conversation_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    outcome: Mapped[str] = mapped_column(String(20), nullable=False)
    concluded_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class EmailUnsubscribe(Base):
    """Email unsubscribe tracking — public, no auth required."""

    __tablename__ = "email_unsubscribes"

    email: Mapped[str] = mapped_column(String(255), primary_key=True)
    unsubscribed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    source: Mapped[str] = mapped_column(String(50), default="list_unsubscribe")
