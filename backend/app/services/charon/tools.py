"""Charon's tool registry.

Each tool is a Python function. Charon can call it through the
function-calling loop in `tool_loop()`.

Tool authorization is enforced at registration time. Charon cannot
add tools it has not been granted. Adding refund/replacement tools
to this file grants Charon the ability to perform those actions —
do this only when the underlying API call has its own auth
constraints (admin role, signed JWT, etc.).

The HTTP backend (legacy orders endpoint) is not yet known to Charon.
Once that route is migrated to a stable address, register the
real implementations. Until then, tool calls return a clear
"not yet wired" message so Charon can answer "I don't know yet"
honestly while being able to teach the team how to integrate.
"""
from __future__ import annotations

import asyncio
import inspect
import logging
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



# ─── Read tools (Charon is allowed to use these) ──────────────────


async def _lookup_order_tx_ref(tx_ref: str) -> ToolResult:
    """Look up an order by transaction reference. Returns redacted
    credentials if the order is active. Currently a placeholder until
    the legacy HTTP route is wired into this agent runtime."""
    return ToolResult(
        ok=False,
        error=(
            "Order lookup is not yet wired into Charon's runtime — the legacy "
            "FastAPI route is at /api/orders/{tx_ref} but I do not have auth "
            "context for it yet. Until then, please ask the customer to use "
            "/manage to look up their order directly."
        ),
    )


async def _lookup_payment_status(tx_ref: str) -> ToolResult:
    """Look up payment status by transaction reference. Placeholder."""
    return ToolResult(
        ok=False,
        error=(
            "Payment status lookup from Charon is not yet wired. Payment "
            "processing is on /webhooks/flutterwave; the team handles "
            "status questions via support@styxproxy.com today."
        ),
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


# Register read-tools
registry.register(ToolSpec(
    name="lookup_order",
    description="Look up an order by its transaction reference (tx_ref). Returns the order's status, plan, country, payment status, and redacted credentials if the order is active.",
    schema={
        "type": "object",
        "properties": {
            "tx_ref": {"type": "string", "description": "The customer's transaction reference"}
        },
        "required": ["tx_ref"],
    },
    handler=_lookup_order_tx_ref,
))


registry.register(ToolSpec(
    name="lookup_payment_status",
    description="Look up payment status for a transaction reference. Returns 'pending', 'paid', 'failed', or 'refunded'.",
    schema={
        "type": "object",
        "properties": {
            "tx_ref": {"type": "string", "description": "The customer's transaction reference"}
        },
        "required": ["tx_ref"],
    },
    handler=_lookup_payment_status,
))


registry.register(ToolSpec(
    name="get_product_catalog",
    description="Return the full product catalog with plans and prices. Use this when the customer wants plan details.",
    schema={"type": "object", "properties": {}},
    handler=_get_product_catalog,
))


registry.register(ToolSpec(
    name="suggest_articles",
    description="Suggest relevant knowledge-base chunks for a topic. Use before falling back to LLM-only answers when context is thin.",
    schema={
        "type": "object",
        "properties": {
            "topic": {"type": "string", "description": "Topic keyword or phrase"}
        },
        "required": ["topic"],
    },
    handler=_suggest_articles,
))


# ─── Forbidden tools (not registered — these are the actions Charon cannot perform) ───

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
