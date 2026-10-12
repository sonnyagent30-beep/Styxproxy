"""Shared logic for delivering a credential to a customer.

Extracted from ``app/scripts/fulfillment_worker.py`` because credential
delivery is not the worker's alone: ``app/services/flutterwave.py`` has an
inline fallback that mints and delivers a credential in the same request when
the RQ enqueue fails. That path had the same defect as the worker's — it read
``event_data["customer"]["email"]``, the Flutterwave shape only — and it was
never fixed, because the fix landed in the worker and nobody noticed the second
caller.

Two rules live here, both learned the hard way:

1. **The order row is the only authoritative source of the customer's address.**
   ``orders.customer_email`` holds what the customer actually typed. A gateway
   payload's ``customer.email`` is whatever was sent to the gateway, which for
   an anonymous checkout is a synthesized placeholder that no human can read.

2. **A delivery to a placeholder is not a delivery.** Resend accepts
   ``guest-anond…@example.com``, returns HTTP 200, and the send is logged as
   successful. It reaches nobody. Counting that as delivery is how "we have
   never observed a customer receiving a proxy" stayed true for 238 orders
   without anyone raising an alarm.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# RFC 2606 reserved domains used for anonymous-checkout placeholders. A send
# addressed here is accepted by the provider and reported as "sent", but it can
# never reach a human — so a delivery to one of these is a silent credential
# loss, not a delivery.
PLACEHOLDER_EMAIL_DOMAINS = ("example.com", "example.org", "example.net")


def is_placeholder_email(email: str | None) -> bool:
    """True if the address is missing or a non-routable checkout placeholder."""
    if not email:
        return True
    domain = email.rsplit("@", 1)[-1].strip().lower()
    return domain in PLACEHOLDER_EMAIL_DOMAINS


def resolve_customer_email(order, data_payload: dict) -> tuple[str | None, str]:
    """Resolve the customer's real email for credential delivery.

    Returns ``(email, source)``; ``email`` is None when no deliverable address
    exists, and ``source`` says where the answer came from — one of
    ``order.customer_email``, ``gateway_payload``, or ``none``. Callers log
    ``source`` so a send can be attributed, and so "resolved from the order row"
    vs "only the gateway payload had one" is visible in production.

    ``order`` may be any object exposing ``customer_email`` (an ORM row, or a
    stub). ``data_payload`` is the full gateway webhook body as received, so
    each provider nests differently:

    * Flutterwave — ``data.customer.email``
    * Paystack   — ``data.email`` / ``data.customer_email`` (no ``customer`` key)
    * NOWPayments — no customer email at all
    """
    row_email = (getattr(order, "customer_email", None) or "").strip()
    if row_email and not is_placeholder_email(row_email):
        return row_email, "order.customer_email"

    data = (data_payload or {}).get("data") or {}
    if not isinstance(data, dict):
        data = {}

    gateway_email = ""
    customer_obj = data.get("customer")
    if isinstance(customer_obj, dict):
        gateway_email = customer_obj.get("email") or ""
    if not gateway_email:
        gateway_email = data.get("customer_email") or data.get("email") or ""

    if not isinstance(gateway_email, str):
        gateway_email = ""

    gateway_email = gateway_email.strip()
    if gateway_email and not is_placeholder_email(gateway_email):
        return gateway_email, "gateway_payload"

    # A placeholder or missing address: the customer paid without giving us a
    # real email, so there is nobody to deliver to.
    return None, "none"