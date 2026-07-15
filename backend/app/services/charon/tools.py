"""Charon's tool registry.

Each tool is a Python function. Charon can call it through the
function-calling loop in `agent.py`.

Tool authorization is enforced at registration time. Charon cannot
add tools it has not been granted. Adding refund/replacement tools
to this file grants Charon the ability to perform those actions —
do this only when the underlying API call has its own auth
constraints (admin role, signed JWT, etc.).

Live tools:
- lookup_order: DB query by tx_ref, returns status + redacted credentials
- lookup_payment_status: Flutterwave API verification
- generate_order_link: builds styxproxy.com/receipt/{tx_ref}
- generate_receipt_link: builds receipt PDF download URL
- get_product_catalog: hardcoded plan list
- suggest_articles: RAG over knowledge base
"""
from __future__ import annotations

import asyncio
import inspect
import logging
import os
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Union

logger = logging.getLogger(__name__)


@dataclass
class ToolResult:
    ok: bool
    data: Any = None
    error: str | None = None

    def to_dict(self) -> dict:
        return {"ok": self.ok, "data": self.data, "error": self.error}


AsyncHandler = Callable[..., Awaitable[ToolResult]]


@dataclass
class ToolSpec:
    name: str
    description: str
    schema: dict  # JSON schema for parameters
    handler: Callable[..., Any]  # sync or async; we normalise inside .call()


class _Registry:
    def __init__(self) -> None:
        self.tools: dict[str, ToolSpec] = {}

    def register(self, tool: ToolSpec) -> None:
        if tool.name in self.tools:
            raise ValueError(f"tool {tool.name!r} already registered")
        self.tools[tool.name] = tool

    def get(self, name: str) -> ToolSpec | None:
        return self.tools.get(name)

    async def call(self, name: str, **params) -> ToolResult:
        spec = self.get(name)
        if not spec:
            return ToolResult(ok=False, error=f"unknown tool {name!r}")
        try:
            rv = spec.handler(**params)
            if inspect.isawaitable(rv):
                rv = await rv
        except TypeError as exc:
            return ToolResult(ok=False, error=f"bad call: {exc}")
        except Exception as exc:
            logger.exception("tool %s raised", name)
            return ToolResult(ok=False, error=f"exception: {exc}")
        if isinstance(rv, ToolResult):
            return rv
        return ToolResult(ok=True, data=rv)

    def list_specs(self) -> list[dict]:
        return [
            {"name": t.name, "description": t.description, "parameters": t.schema}
            for t in self.tools.values()
        ]


registry = _Registry()

# ─── Site URL (configured via env) ─────────────────────────────────────────

PUBLIC_URL = os.environ.get("PUBLIC_URL", "https://styxproxy.com")


# ─── Read tools (Charon is allowed to use these) ───────────────────────────


async def _lookup_order_tx_ref(tx_ref: str) -> ToolResult:
    """Look up an order by Flutterwave transaction reference.
    Returns order status, plan details, and redacted credentials if active.
    Does NOT require auth — Charon runs inside the service boundary."""
    try:
        from sqlalchemy import select
        from app.database import async_session
        from app.models import Order, BuncheCredential

        async with async_session() as session:
            stmt = select(Order).where(Order.tx_ref == tx_ref)
            result = await session.execute(stmt)
            order = result.scalar_one_or_none()

            if not order:
                return ToolResult(
                    ok=False,
                    error=(
                        f"No order found for transaction reference '{tx_ref}'. "
                        "Please ask the customer to double-check the reference — "
                        "it should be in their Flutterwave confirmation message."
                    ),
                )

            # Get credentials if fulfilled
            creds = None
            if (
                order.bunche_credential_id
                and order.status in ("fulfilled", "active", "fulfilling")
            ):
                cred_stmt = select(BuncheCredential).where(
                    BuncheCredential.id == order.bunche_credential_id
                )
                cred_result = await session.execute(cred_stmt)
                cred = cred_result.scalar_one_or_none()
                if cred:
                    pwd = cred.provider_password or ""
                    redacted_password = f"***{pwd[-4:]}" if len(pwd) >= 4 else "****"
                    creds = {
                        "username": cred.bun_username,
                        "password_preview": redacted_password,
                        "proxy_address": str(cred.upstream_proxy_ip) if cred.upstream_proxy_ip else None,
                        "port": cred.upstream_proxy_port,
                        "protocol": cred.protocol,
                        "status": cred.status,
                        "expires_at": cred.expires_at.isoformat() if cred.expires_at else None,
                    }

            status_message = ""
            if order.status == "pending":
                status_message = (
                    "Payment is pending — the customer may still be completing checkout on Flutterwave. "
                    "Ask them to confirm the payment was made."
                )
            elif order.status == "paid":
                status_message = (
                    "Payment confirmed but proxy not yet generated. "
                    "The customer should wait a moment. If they already refreshed, "
                    "escalate to the support team."
                )
            elif order.status in ("fulfilled", "active", "fulfilling"):
                status_message = "Proxy is ready. Share the credentials with the customer."

            return ToolResult(
                ok=True,
                data={
                    "tx_ref": order.tx_ref,
                    "order_id": order.order_id,
                    "status": order.status,
                    "plan_type": order.plan_type,
                    "plan_code": order.plan_code,
                    "country": order.country,
                    "quantity": order.quantity,
                    "amount_paid_ngn": float(order.amount_paid_ngn) if order.amount_paid_ngn else None,
                    "created_at": order.created_at.isoformat() if order.created_at else None,
                    "expires_at": order.expires_at.isoformat() if order.expires_at else None,
                    "credential": creds,
                    "status_message": status_message,
                },
            )
    except Exception as exc:
        logger.exception("lookup_order failed for tx_ref=%s", tx_ref)
        return ToolResult(ok=False, error=f"Order lookup failed: {exc}")


async def _lookup_payment_status(tx_ref: str) -> ToolResult:
    """Look up payment status for a transaction reference via Flutterwave."""
    try:
        from app.services.flutterwave import verify_flutterwave_payment

        data = await verify_flutterwave_payment(tx_ref)
        status = data.get("status", "unknown")
        amount = data.get("amount", 0)
        currency = data.get("currency", "NGN")

        message = ""
        if status == "successful":
            message = "Payment was successful."
        elif status == "pending":
            message = "Payment is still pending — the customer may still be on Flutterwave."
        elif status == "failed":
            message = "Payment failed. The customer may need to try again."
        elif status == "refunded":
            message = "Payment was refunded."
        else:
            message = f"Payment status is: {status}."

        return ToolResult(
            ok=True,
            data={
                "tx_ref": tx_ref,
                "status": status,
                "amount": amount,
                "currency": currency,
                "message": message,
            },
        )
    except Exception as exc:
        logger.exception("lookup_payment_status failed for tx_ref=%s", tx_ref)
        return ToolResult(
            ok=False,
            error=f"Payment status lookup failed: {exc}. "
                   "Please ask the customer for their Flutterwave confirmation "
                   "reference and try again.",
        )


async def _generate_order_link(tx_ref: str) -> ToolResult:
    """Generate a direct link to the customer's order/receipt page.
    Use when the customer needs to check their order status or retrieve credentials."""
    url = f"{PUBLIC_URL}/receipt/{tx_ref}"
    return ToolResult(
        ok=True,
        data={
            "url": url,
            "display_text": "View your order",
            "message": (
                f"Here is your order link — bookmark it to check your status anytime: "
                f"{url}"
            ),
        },
    )


async def _generate_receipt_link(tx_ref: str) -> ToolResult:
    """Generate a receipt PDF download link, but only if the order is confirmed paid.
    Verifies the order exists and has a paid status before sharing the receipt URL."""
    try:
        from sqlalchemy import select
        from app.database import async_session
        from app.models import Order

        async with async_session() as session:
            stmt = select(Order).where(Order.tx_ref == tx_ref)
            result = await session.execute(stmt)
            order = result.scalar_one_or_none()

        if not order:
            return ToolResult(
                ok=False,
                error=(
                    f"I couldn't find an order with reference '{tx_ref}'. "
                    "Please double-check your transaction reference and try again."
                ),
            )

        if order.status not in ("paid", "fulfilling", "fulfilled", "active"):
            return ToolResult(
                ok=False,
                error=(
                    "Your order hasn't been confirmed yet. Once your payment is confirmed "
                    "by Flutterwave, I'll send you your receipt right away. "
                    "This usually takes a few minutes after payment."
                ),
            )

        url = f"{PUBLIC_URL}/preview?tx_ref={tx_ref}"
        return ToolResult(
            ok=True,
            data={
                "url": url,
                "display_text": "Download your receipt",
                "message": f"Your official receipt is ready. You can download it here: {url}",
            },
        )
    except Exception as exc:
        logger.exception("generate_receipt_link failed for tx_ref=%s", tx_ref)
        return ToolResult(
            ok=False,
            error=f"Receipt generation failed: {exc}. Please try again or contact support.",
        )


async def _get_product_catalog() -> ToolResult:
    """Return the current product catalog with plan codes, names, and prices."""
    return ToolResult(
        ok=True,
        data={
            "plans": [
                {"code": "ISP-1", "type": "isp", "label": "ISP", "starting_price_ngn": 6500, "starting_price_period": "month"},
                {"code": "RESIDENTIAL-5GB", "type": "residential", "label": "Residential 5GB", "price_ngn": 5000, "period": "data_plan"},
                {"code": "RESIDENTIAL-10GB", "type": "residential", "label": "Residential 10GB", "price_ngn": 9000, "period": "data_plan"},
                {"code": "RESIDENTIAL-50GB", "type": "residential", "label": "Residential 50GB", "price_ngn": 38000, "period": "data_plan"},
                {"code": "MOBILE-5GB", "type": "mobile", "label": "Mobile 4G 5GB", "price_ngn": 20000, "period": "data_plan"},
                {"code": "MOBILE-10GB", "type": "mobile", "label": "Mobile 4G 10GB", "price_ngn": 35000, "period": "data_plan"},
                {"code": "DC-10", "type": "datacenter", "label": "Datacenter 10 IPs", "price_ngn": 3000, "period": "month"},
                {"code": "DC-50", "type": "datacenter", "label": "Datacenter 50 IPs", "price_ngn": 12000, "period": "month"},
                {"code": "DC-100", "type": "datacenter", "label": "Datacenter 100 IPs", "price_ngn": 20000, "period": "month"},
            ],
        },
    )


async def _suggest_articles(topic: str) -> ToolResult:
    """Suggest articles from the knowledge base for a topic."""
    from .knowledge import search
    chunks = search(topic, top_k=3)
    return ToolResult(
        ok=True,
        data={"chunks": [{"heading": c.heading, "preview": c.content[:240]} for c in chunks]},
    )


# ─── Register read-tools ─────────────────────────────────────────────────────

registry.register(ToolSpec(
    name="lookup_order",
    description=(
        "Look up an order by its Flutterwave transaction reference (tx_ref). "
        "Returns the order's status, plan, country, payment status, and redacted credentials "
        "if the proxy is already active. Use this when a customer provides a transaction reference "
        "to check on their order or retrieve their proxy credentials."
    ),
    schema={
        "type": "object",
        "properties": {
            "tx_ref": {"type": "string", "description": "The customer's Flutterwave transaction reference"},
        },
        "required": ["tx_ref"],
    },
    handler=_lookup_order_tx_ref,
))


registry.register(ToolSpec(
    name="lookup_payment_status",
    description=(
        "Look up payment status for a transaction reference via Flutterwave. "
        "Returns 'pending', 'successful', 'failed', or 'refunded'."
    ),
    schema={
        "type": "object",
        "properties": {
            "tx_ref": {"type": "string", "description": "The customer's Flutterwave transaction reference"},
        },
        "required": ["tx_ref"],
    },
    handler=_lookup_payment_status,
))


registry.register(ToolSpec(
    name="generate_order_link",
    description=(
        "Generate a direct link to the customer's order page where they can view their "
        "order status and credentials. Use when a customer needs to retrieve their proxy "
        "or check their order status — especially if they were disconnected during checkout."
    ),
    schema={
        "type": "object",
        "properties": {
            "tx_ref": {"type": "string", "description": "The customer's Flutterwave transaction reference"},
        },
        "required": ["tx_ref"],
    },
    handler=_generate_order_link,
))


registry.register(ToolSpec(
    name="generate_receipt_link",
    description=(
        "Generate a download link for the customer's official receipt PDF. "
        "Use after fulfilling an order to send the customer their receipt."
    ),
    schema={
        "type": "object",
        "properties": {
            "tx_ref": {"type": "string", "description": "The customer's Flutterwave transaction reference"},
        },
        "required": ["tx_ref"],
    },
    handler=_generate_receipt_link,
))


registry.register(ToolSpec(
    name="get_product_catalog",
    description="Return the full product catalog with plans and prices. Use when the customer wants plan details.",
    schema={"type": "object", "properties": {}},
    handler=_get_product_catalog,
))


registry.register(ToolSpec(
    name="suggest_articles",
    description="Suggest relevant knowledge-base chunks for a topic. Use before falling back to LLM-only answers when context is thin.",
    schema={
        "type": "object",
        "properties": {
            "topic": {"type": "string", "description": "Topic keyword or phrase"},
        },
        "required": ["topic"],
    },
    handler=_suggest_articles,
))


# ─── Forbidden tools (not registered — guard rails) ───────────────────────────

# The following operations exist in the system but Charon is NOT
# authorized to invoke them. They are listed here as a guard rail —
# if you ever see Charon call one of these, escalate to admin.
# - refund_order
# - replace_proxy
# - cancel_order
# - reissue_credentials
# - block_customer
# - issue_free_trial
# - change_pricing
