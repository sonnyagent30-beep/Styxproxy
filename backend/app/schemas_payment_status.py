"""Payment status schemas — customer-facing polling endpoint."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class OrderPaymentStatus(BaseModel):
    """Single response shape for the polling endpoint.

    Frontend polls this every 3-5 seconds after the customer hits Flutterwave.
    When payment_status transitions to "successful" AND order_status becomes
    "active", the response includes the SOCKS5 credentials and a redirect URL.
    """

    # Order identity
    order_id: str
    plan_type: str  # residential | datacenter
    plan_code: str
    country: str
    rotation_mode: str  # rotating | static
    quantity_gb: int
    duration_days: int
    amount_paid_ngn: float
    currency: str = "NGN"

    # Status fields
    order_status: str  # pending | paid | active | cancelled | failed | expired
    payment_status: str  # pending | successful | failed | abandoned
    payment_reference: Optional[str] = None  # Flutterwave tx_ref

    # Timestamps
    created_at: datetime
    paid_at: Optional[datetime] = None
    fulfilled_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None

    # What the frontend should do next
    next_action: str = Field(
        ...,
        description=(
            "poll | redirect_to_payment | show_success | show_failure | "
            "redirect_to_proxy_details | show_retry"
        ),
    )
    next_action_url: Optional[str] = None  # URL the customer should be sent to
    user_message: str  # Human-readable status for the customer

    # If active (payment successful + credential provisioned), populate these
    credential: Optional["PaymentStatusCredential"] = None


class PaymentStatusCredential(BaseModel):
    """Credential info — only populated when order is ACTIVE (paid + fulfilled)."""

    credential_id: int
    styxproxy_username: str
    styxproxy_password: str  # plaintext — shown once
    proxy_host: str = "proxy.styxproxy.com"
    proxy_port_socks5: int = 1080
    proxy_port_http: int = 8080
    protocol: str = "socks5"
    assigned_static_ip: Optional[str] = None
    curl_socks5_example: str
    curl_http_example: str
    python_socks5_example: str

    # Next page after success — frontend routes here
    manage_url: str  # e.g. /manage or /dashboard/proxies/{id}


# Rebuild parent model to allow forward reference
OrderPaymentStatus.model_rebuild()