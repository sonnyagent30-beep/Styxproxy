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
- get_product_catalog: plan list from country_plan_types
- get_customer_context: customer profile + orders + spend (RLS-gated)
- suggest_articles: RAG over knowledge base
- create_order: Telegram/WhatsApp order creation
- initiate_payment: Flutterwave invoice creation
- get_setup_guide: proxy configuration instructions
- get_troubleshooting: common proxy issues and fixes
"""

from __future__ import annotations

import hashlib
import inspect
import logging
import os
import uuid
from dataclasses import dataclass
from typing import Any, Awaitable, Callable

logger = logging.getLogger(__name__)


async def _set_rls_context(session, customer_phone: str | None = None):
    """Set RLS session variables for customer isolation."""
    from sqlalchemy import text
    if customer_phone:
        await session.execute(
            text("SELECT set_config('app.current_customer_phone', :val, true)"),
            {"val": customer_phone}
        )
    else:
        await session.execute(
            text("SELECT set_config('app.current_customer_phone', '', true)")
        )


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
        return [{"name": t.name, "description": t.description, "parameters": t.schema} for t in self.tools.values()]


registry = _Registry()

# ─── Site URL (configured via env) ─────────────────────────────────────────

PUBLIC_URL = os.environ.get("PUBLIC_URL", "https://styxproxy.com")


# ─── Read tools (Charon is allowed to use these) ───────────────────────────


async def _lookup_order_tx_ref(tx_ref: str, customer_phone: str | None = None) -> ToolResult:
    """Look up an order by Flutterwave transaction reference."""
    try:
        from sqlalchemy import select
        from app.database import async_session
        from app.models import Order, StyxproxyCredential

        async with async_session() as session:
            await _set_rls_context(session, customer_phone)
            stmt = select(Order).where(Order.tx_ref == tx_ref)
            result = await session.execute(stmt)
            order = result.scalar_one_or_none()

            if not order:
                return ToolResult(
                    ok=False,
                    error=f"No order found for transaction reference '{tx_ref}'.",
                )

            creds = None
            if order.styxproxy_credential_id and order.status in ("fulfilled", "active", "fulfilling"):
                cred_stmt = select(StyxproxyCredential).where(StyxproxyCredential.id == order.styxproxy_credential_id)
                cred_result = await session.execute(cred_stmt)
                cred = cred_result.scalar_one_or_none()
                if cred:
                    creds = {
                        "username": cred.styxproxy_username,
                        "proxy_address": str(cred.upstream_proxy_ip) if cred.upstream_proxy_ip else None,
                        "port": cred.upstream_proxy_port,
                        "protocol": cred.protocol,
                        "status": cred.status,
                        "expires_at": cred.expires_at.isoformat() if cred.expires_at else None,
                    }

            status_message = ""
            if order.status == "pending":
                status_message = "Payment is pending."
            elif order.status == "paid":
                status_message = "Payment confirmed but proxy not yet generated."
            elif order.status in ("fulfilled", "active", "fulfilling"):
                status_message = "Proxy is ready."

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


async def _lookup_payment_status(tx_ref: str, customer_phone: str | None = None) -> ToolResult:
    """Look up payment status for a transaction reference via Flutterwave."""
    try:
        from app.services.flutterwave import verify_flutterwave_payment
        data = await verify_flutterwave_payment(tx_ref)
        status = data.get("status", "unknown")
        return ToolResult(ok=True, data={"tx_ref": tx_ref, "status": status, "amount": data.get("amount", 0), "currency": data.get("currency", "NGN"), "message": f"Payment status: {status}"})
    except Exception as exc:
        logger.exception("lookup_payment_status failed for tx_ref=%s", tx_ref)
        return ToolResult(ok=False, error=f"Payment status lookup failed: {exc}")


async def _generate_order_link(tx_ref: str, customer_phone: str | None = None) -> ToolResult:
    """Generate a direct link to the customer's order page."""
    url = f"{PUBLIC_URL}/receipt/{tx_ref}"
    return ToolResult(ok=True, data={"url": url, "display_text": "View your order", "message": f"Here is your order link: {url}"})


async def _generate_receipt_link(tx_ref: str, customer_phone: str | None = None) -> ToolResult:
    """Generate a receipt PDF download link."""
    try:
        from sqlalchemy import select
        from app.database import async_session
        from app.models import Order

        async with async_session() as session:
            await _set_rls_context(session, customer_phone)
            stmt = select(Order).where(Order.tx_ref == tx_ref)
            result = await session.execute(stmt)
            order = result.scalar_one_or_none()

        if not order:
            return ToolResult(ok=False, error=f"Order '{tx_ref}' not found")
        if order.status not in ("paid", "fulfilling", "fulfilled", "active"):
            return ToolResult(ok=False, error="Order not confirmed yet")

        url = f"{PUBLIC_URL}/preview?tx_ref={tx_ref}"
        return ToolResult(ok=True, data={"url": url, "display_text": "Download receipt", "message": f"Your receipt: {url}"})
    except Exception as exc:
        return ToolResult(ok=False, error=f"Receipt generation failed: {exc}")


async def _get_product_catalog() -> ToolResult:
    """Return the current product catalog from country_plan_types."""
    try:
        from sqlalchemy import select, text
        from app.database import async_session

        async with async_session() as session:
            stmt = text("""
                SELECT country_code, plan_type, price_per_ip, price_per_gb, is_special
                FROM country_plan_types
                WHERE enabled = true
                ORDER BY country_code, plan_type
            """)
            result = await session.execute(stmt)
            rows = result.fetchall()
            catalog = []
            for row in rows:
                plan_type = (row.plan_type or "RESIDENTIAL").upper()
                code = f"{plan_type[:4]}-{row.country_code}"
                catalog.append({
                    "code": code,
                    "type": (row.plan_type or "").lower(),
                    "country": row.country_code,
                    "price_per_ip": float(row.price_per_ip) if row.price_per_ip else None,
                    "price_per_gb": float(row.price_per_gb) if row.price_per_gb else None,
                    "is_special": row.is_special or False,
                })
            return ToolResult(ok=True, data={"plans": catalog})
    except Exception as exc:
        logger.exception("get_product_catalog failed")
        return ToolResult(ok=False, error=f"Failed to load catalog: {exc}")


async def _get_customer_context_tool(customer_phone: str | None = None) -> ToolResult:
    """Return customer profile, recent orders, and spend summary.
    
    RLS-gated: only returns data for the customer_phone set in session.
    Use this to personalize replies — know if they're new, returning, or VIP.
    """
    try:
        from sqlalchemy import select, func
        from app.database import async_session
        from app.models import Customer, Order, StyxproxyCredential

        if not customer_phone:
            return ToolResult(ok=False, error="No customer_phone provided")

        async with async_session() as session:
            await _set_rls_context(session, customer_phone)

            # Customer profile
            stmt_c = select(Customer).where(Customer.phone == customer_phone)
            result_c = await session.execute(stmt_c)
            customer = result_c.scalar_one_or_none()

            if not customer:
                return ToolResult(ok=True, data={
                    "is_new_customer": True,
                    "customer_phone": customer_phone,
                    "message": "New customer — no purchase history yet",
                })

            # Recent orders (last 5)
            stmt_o = (
                select(Order)
                .where(Order.customer_phone == customer_phone)
                .order_by(Order.created_at.desc())
                .limit(5)
            )
            result_o = await session.execute(stmt_o)
            orders = result_o.scalars().all()

            # Spend summary
            stmt_s = select(func.count(Order.order_id), func.coalesce(func.sum(Order.amount_paid_ngn), 0)).where(
                Order.customer_phone == customer_phone,
                Order.status.in_(["paid", "fulfilling", "fulfilled", "active"]),
            )
            result_s = await session.execute(stmt_s)
            order_count, total_spend = result_s.one()

            # Active credentials
            stmt_cr = (
                select(StyxproxyCredential)
                .join(Order, Order.styxproxy_credential_id == StyxproxyCredential.id)
                .where(
                    Order.customer_phone == customer_phone,
                    Order.status.in_(["fulfilled", "active"]),
                    StyxproxyCredential.status == "active",
                )
                .order_by(StyxproxyCredential.expires_at.asc())
                .limit(3)
            )
            result_cr = await session.execute(stmt_cr)
            active_creds = result_cr.scalars().all()

            # Determine customer tier
            tier = "new"
            if order_count >= 10 or total_spend >= 500000:
                tier = "vip"
            elif order_count >= 3 or total_spend >= 100000:
                tier = "returning"

            return ToolResult(ok=True, data={
                "is_new_customer": False,
                "customer_phone": customer_phone,
                "customer_name": customer.name,
                "tier": tier,
                "total_orders": order_count,
                "total_spend_ngn": float(total_spend),
                "recent_orders": [
                    {
                        "order_id": o.order_id,
                        "plan_type": o.plan_type,
                        "plan_code": o.plan_code,
                        "status": o.status,
                        "amount": float(o.amount_paid_ngn) if o.amount_paid_ngn else None,
                        "created_at": o.created_at.isoformat() if o.created_at else None,
                    }
                    for o in orders
                ],
                "active_credentials": [
                    {
                        "proxy_address": str(c.upstream_proxy_ip) if c.upstream_proxy_ip else None,
                        "port": c.upstream_proxy_port,
                        "protocol": c.protocol,
                        "expires_at": c.expires_at.isoformat() if c.expires_at else None,
                    }
                    for c in active_creds
                ],
                "last_order_at": customer.last_order_at.isoformat() if customer.last_order_at else None,
                "message": f"{tier.capitalize()} customer — {order_count} orders, ₦{float(total_spend):,.0f} total spend",
            })
    except Exception as exc:
        logger.exception("get_customer_context failed")
        return ToolResult(ok=False, error=f"Customer context lookup failed: {exc}")


async def _suggest_articles(topic: str) -> ToolResult:
    """Suggest articles from the knowledge base."""
    from .knowledge import search
    chunks = search(topic, top_k=3)
    return ToolResult(ok=True, data={"chunks": [{"heading": c.heading, "preview": c.content[:240]} for c in chunks]})


async def _get_setup_guide(plan_type: str | None = None, protocol: str | None = None) -> ToolResult:
    """Return proxy setup instructions for the customer's plan type.
    
    Covers: HTTP/HTTPS, SOCKS5, authentication, browser config, common tools.
    """
    guides = {
        "residential": {
            "description": "Residential proxies use real home IPs. Best for social media, ad verification, sneaker sites.",
            "setup": [
                "Use format: proxy.styxproxy.com:PORT",
                "Auth with your Styxproxy username/password",
                "Protocol: HTTP, HTTPS, or SOCKS5",
                "IP rotates per request or every 5-30 min (depends on plan)",
            ],
            "tools": ["Browser (Firefox/Chrome with proxy extension)", "Selenium/Puppeteer", "Python requests", "Sneaker bots"],
            "tips": [
                "Use sticky sessions if you need the same IP for >30 min",
                "Whitelist your IP on the dashboard for static access",
                "Best for: Instagram, TikTok, Twitter, ad verification",
            ],
        },
        "mobile": {
            "description": "Mobile 4G proxies use real carrier IPs. Highest trust score for social platforms.",
            "setup": [
                "Use format: proxy.styxproxy.com:PORT",
                "Auth with your Styxproxy username/password",
                "Protocol: HTTP, HTTPS, or SOCKS5",
                "IP rotates every 5-30 min",
            ],
            "tools": ["Mobile emulators", "App automation", "Social media management"],
            "tips": [
                "Mobile IPs are the hardest to detect by platforms",
                "Use for account creation on strict platforms",
                "Not ideal for high-throughput scraping (more expensive)",
            ],
        },
        "isp": {
            "description": "ISP proxies are datacenter IPs registered to real ISPs. Fast + residential-like reputation.",
            "setup": [
                "Use format: proxy.styxproxy.com:PORT",
                "Auth with your Styxproxy username/password",
                "Protocol: HTTP, HTTPS, or SOCKS5",
                "Static IP — stays the same for your subscription period",
            ],
            "tools": ["Web scraping", "Automation", "Account management", "Sneaker sites"],
            "tips": [
                "Static IP means you keep the same address for 30 days",
                "Good balance of speed and trust",
                "Best for: long sessions that need same IP",
            ],
        },
        "datacenter": {
            "description": "Datacenter proxies are bare-metal server IPs. Fastest, cheapest, easiest to detect.",
            "setup": [
                "Use format: proxy.styxproxy.com:PORT",
                "Auth with your Styxproxy username/password",
                "Protocol: HTTP, HTTPS, or SOCKS5",
                "Static IP or rotating pool",
            ],
            "tools": ["Large-scale scraping", "SEO monitoring", "Price aggregation", "Server testing"],
            "tips": [
                "Cheapest option per IP — best for volume",
                "Easiest to detect by streaming services and strict platforms",
                "Best for: data extraction, bulk operations, non-stealth tasks",
            ],
        },
    }

    if plan_type and plan_type.lower() in guides:
        guide = guides[plan_type.lower()]
        return ToolResult(ok=True, data=guide)
    elif plan_type and plan_type.lower() in ("dc", "data_center", "datacentre"):
        return ToolResult(ok=True, data=guides["datacenter"])
    else:
        # Return all guides
        return ToolResult(ok=True, data={
            "available_types": list(guides.keys()),
            "message": "Ask for a specific plan type (residential, mobile, isp, datacenter) to get detailed setup instructions",
            "guides": guides,
        })


async def _get_troubleshooting(issue: str | None = None, plan_type: str | None = None) -> ToolResult:
    """Return troubleshooting steps for common proxy issues.
    
    Covers: auth failures, IP banned, slow speeds, connection refused,
    proxy not working, credential expired.
    """
    issues = {
        "auth_failed": {
            "symptoms": ["401 Unauthorized", "407 Proxy Authentication Required", "login prompt keeps appearing"],
            "steps": [
                "Verify your username/password — case sensitive",
                "Check that your order is still active (not expired)",
                "Try resetting credentials from the Manage page",
                "Make sure you're not sending credentials in plaintext to an HTTPS proxy without proper config",
            ],
        },
        "ip_banned": {
            "symptoms": ["403 Forbidden", "Access denied", "Site blocks your proxy IP"],
            "steps": [
                "Report the banned IP from the Manage page — we rotate it free",
                "The proxy IP may have been flagged by the target site",
                "Try a different country or plan type",
                "Use residential or mobile IPs instead of datacenter for strict sites",
            ],
        },
        "slow_speed": {
            "symptoms": ["Requests timing out", "Very slow page loads", "Connection slow"],
            "steps": [
                "Check your own internet connection first",
                "Try a closer geographic region (lower latency)",
                "Datacenter and ISP are fastest; mobile is slowest",
                "Reduce concurrent connections — too many at once slows each down",
            ],
        },
        "connection_refused": {
            "symptoms": ["Connection refused", "ECONNREFUSED", "Cannot connect to proxy"],
            "steps": [
                "Verify the proxy address and port — check your credentials page",
                "Make sure your order is active (not expired or pending)",
                "Try a different protocol (HTTP vs SOCKS5)",
                "Check if your firewall is blocking outbound proxy connections",
            ],
        },
        "not_working": {
            "symptoms": ["Proxy does nothing", "Still seeing my real IP", "Not routing through proxy"],
            "steps": [
                "Verify proxy is actually configured in your browser/tool",
                "Test with https://ipinfo.io to confirm proxy is active",
                "Clear browser cache and retry",
                "Make sure you're authenticating with the right credentials",
            ],
        },
        "expired": {
            "symptoms": ["Credentials stopped working", "Subscription ended", "Order expired"],
            "steps": [
                "Check expiry date on your credentials page",
                "Renew from the Manage page using your tx_ref",
                "Renewal keeps the same IP if still available",
                "Set a reminder — we send email alerts 3 days before expiry",
            ],
        },
    }

    if issue and issue.lower() in issues:
        return ToolResult(ok=True, data=issues[issue.lower()])
    else:
        # Return issue categories
        return ToolResult(ok=True, data={
            "known_issues": list(issues.keys()),
            "message": "Ask about a specific issue: auth_failed, ip_banned, slow_speed, connection_refused, not_working, expired",
            "issues": issues,
        })


# ─── Customer Self-Service Tools (added 2026-08-29) ──────────────────────────


async def _list_customer_orders_tool(customer_phone: str | None = None) -> ToolResult:
    """Return all orders for a customer (RLS-gated).
    
    No tx_ref needed — lists everything the customer has bought.
    Use when customer asks "show me my orders", "what did I buy", "my orders".
    """
    try:
        from sqlalchemy import select
        from app.database import async_session
        from app.models import Order, StyxproxyCredential

        if not customer_phone:
            return ToolResult(ok=False, error="No customer_phone provided")

        async with async_session() as session:
            await _set_rls_context(session, customer_phone)
            stmt = (
                select(Order)
                .where(Order.customer_phone == customer_phone)
                .order_by(Order.created_at.desc())
                .limit(20)
            )
            result = await session.execute(stmt)
            orders = result.scalars().all()

            if not orders:
                return ToolResult(ok=True, data={
                    "orders": [],
                    "message": "No orders found. Want to browse our plans?",
                })

            order_list = []
            for o in orders:
                cred_info = None
                if o.styxproxy_credential_id and o.status in ("fulfilled", "active", "fulfilling"):
                    cred_stmt = select(StyxproxyCredential).where(
                        StyxproxyCredential.id == o.styxproxy_credential_id
                    )
                    cred_result = await session.execute(cred_stmt)
                    cred = cred_result.scalar_one_or_none()
                    if cred:
                        cred_info = {
                            "proxy_address": str(cred.upstream_proxy_ip) if cred.upstream_proxy_ip else None,
                            "port": cred.upstream_proxy_port,
                            "protocol": cred.protocol,
                            "status": cred.status,
                            "expires_at": cred.expires_at.isoformat() if cred.expires_at else None,
                        }
                order_list.append({
                    "order_id": o.order_id,
                    "tx_ref": o.tx_ref,
                    "plan_type": o.plan_type,
                    "plan_code": o.plan_code,
                    "country": o.country,
                    "quantity": o.quantity,
                    "amount_paid_ngn": float(o.amount_paid_ngn) if o.amount_paid_ngn else None,
                    "status": o.status,
                    "created_at": o.created_at.isoformat() if o.created_at else None,
                    "expires_at": o.expires_at.isoformat() if o.expires_at else None,
                    "data_remaining_gb": float(o.data_remaining_gb) if o.data_remaining_gb else None,
                    "data_total_gb": float(o.data_total_gb) if o.data_total_gb else None,
                    "credential": cred_info,
                })

            return ToolResult(ok=True, data={
                "orders": order_list,
                "total": len(order_list),
                "message": f"Found {len(order_list)} order(s)",
            })
    except Exception as exc:
        logger.exception("list_customer_orders failed")
        return ToolResult(ok=False, error=f"Failed to list orders: {exc}")


async def _check_data_remaining_tool(customer_phone: str | None = None) -> ToolResult:
    """Check remaining data for residential/mobile proxies.
    
    Returns active orders with data_remaining_gb and data_total_gb.
    Use when customer asks "how much data do I have left", "data usage".
    """
    try:
        from sqlalchemy import select
        from app.database import async_session
        from app.models import Order, StyxproxyCredential

        if not customer_phone:
            return ToolResult(ok=False, error="No customer_phone provided")

        async with async_session() as session:
            await _set_rls_context(session, customer_phone)
            stmt = (
                select(Order, StyxproxyCredential)
                .join(StyxproxyCredential, StyxproxyCredential.id == Order.styxproxy_credential_id, isouter=True)
                .where(
                    Order.customer_phone == customer_phone,
                    Order.status.in_(["fulfilled", "active", "fulfilling"]),
                    Order.plan_type.in_(["residential", "mobile"]),
                )
                .order_by(StyxproxyCredential.expires_at.asc())
                .limit(10)
            )
            result = await session.execute(stmt)
            rows = result.all()

            if not rows:
                return ToolResult(ok=True, data={
                    "active_data_plans": [],
                    "message": "No active data plans found. Data plans are residential or mobile proxies.",
                })

            plans = []
            total_remaining = 0
            total_allocated = 0
            for order, cred in rows:
                remaining = float(order.data_remaining_gb) if order.data_remaining_gb else 0
                allocated = float(order.data_total_gb) if order.data_total_gb else 0
                total_remaining += remaining
                total_allocated += allocated
                plans.append({
                    "order_id": order.order_id,
                    "plan_type": order.plan_type,
                    "plan_code": order.plan_code,
                    "country": order.country,
                    "data_total_gb": allocated,
                    "data_remaining_gb": remaining,
                    "data_used_gb": allocated - remaining,
                    "usage_pct": round((allocated - remaining) / allocated * 100, 1) if allocated > 0 else 0,
                    "proxy_address": str(cred.upstream_proxy_ip) if cred and cred.upstream_proxy_ip else None,
                    "expires_at": cred.expires_at.isoformat() if cred and cred.expires_at else None,
                })

            return ToolResult(ok=True, data={
                "active_data_plans": plans,
                "total_remaining_gb": total_remaining,
                "total_allocated_gb": total_allocated,
                "message": f"{len(plans)} active data plan(s) — {total_remaining:.1f}GB remaining of {total_allocated:.1f}GB total",
            })
    except Exception as exc:
        logger.exception("check_data_remaining failed")
        return ToolResult(ok=False, error=f"Data check failed: {exc}")


async def _get_referral_info_tool(customer_phone: str | None = None) -> ToolResult:
    """Return customer's referral code, earnings, and terms.
    
    Use when customer asks "referral", "refer a friend", "my referral code".
    """
    try:
        from sqlalchemy import select, func
        from app.database import async_session
        from app.models import Customer, ReferralCredit

        if not customer_phone:
            return ToolResult(ok=False, error="No customer_phone provided")

        async with async_session() as session:
            await _set_rls_context(session, customer_phone)
            stmt_c = select(Customer).where(Customer.phone == customer_phone)
            result_c = await session.execute(stmt_c)
            customer = result_c.scalar_one_or_none()

            if not customer:
                return ToolResult(ok=True, data={
                    "has_referrer": False,
                    "referral_code": None,
                    "message": "No customer profile found. Make your first order to unlock referrals.",
                })

            # Count successful referrals
            stmt_r = select(func.count(ReferralCredit.id)).where(
                ReferralCredit.referrer_customer_id == customer.id,
                ReferralCredit.applied_at.isnot(None),
            )
            result_r = await session.execute(stmt_r)
            successful_referrals = result_r.scalar() or 0

            # Pending referrals (signed up but not paid)
            stmt_p = select(func.count(ReferralCredit.id)).where(
                ReferralCredit.referrer_customer_id == customer.id,
                ReferralCredit.applied_at.is_(None),
            )
            result_p = await session.execute(stmt_p)
            pending_referrals = result_p.scalar() or 0

            total_earnings = successful_referrals * 500

            return ToolResult(ok=True, data={
                "referral_code": customer.referral_code,
                "successful_referrals": successful_referrals,
                "pending_referrals": pending_referrals,
                "total_earnings_ngn": total_earnings,
                "terms": {
                    "reward_per_referral": "₦500",
                    "condition": "Friend must complete their first payment",
                    "payout": "Applied automatically to your account",
                },
                "message": f"Your referral code: {customer.referral_code} — {successful_referrals} successful referrals (₦{total_earnings} earned)",
            })
    except Exception as exc:
        logger.exception("get_referral_info failed")
        return ToolResult(ok=False, error=f"Referral info lookup failed: {exc}")


async def _detect_renewal_tool(customer_phone: str | None = None) -> ToolResult:
    """Detect proxies expiring within 7 days.
    
    Returns credentials that need renewal soon.
    Use for proactive "your proxy expires soon" messages.
    """
    try:
        from datetime import datetime, timezone, timedelta
        from sqlalchemy import select
        from app.database import async_session
        from app.models import Order, StyxproxyCredential

        if not customer_phone:
            return ToolResult(ok=False, error="No customer_phone provided")

        async with async_session() as session:
            await _set_rls_context(session, customer_phone)
            threshold = datetime.now(timezone.utc) + timedelta(days=7)
            stmt = (
                select(Order, StyxproxyCredential)
                .join(StyxproxyCredential, StyxproxyCredential.id == Order.styxproxy_credential_id)
                .where(
                    Order.customer_phone == customer_phone,
                    Order.status.in_(["fulfilled", "active"]),
                    StyxproxyCredential.status == "active",
                    StyxproxyCredential.expires_at <= threshold,
                )
                .order_by(StyxproxyCredential.expires_at.asc())
                .limit(5)
            )
            result = await session.execute(stmt)
            rows = result.all()

            if not rows:
                return ToolResult(ok=True, data={
                    "expiring_soon": [],
                    "message": "No proxies expiring in the next 7 days. You're all set!",
                })

            expiring = []
            for order, cred in rows:
                expires_at = cred.expires_at if cred.expires_at else None
                days_left = None
                if expires_at:
                    delta = expires_at - datetime.now(timezone.utc)
                    days_left = max(0, delta.days)
                expiring.append({
                    "order_id": order.order_id,
                    "plan_type": order.plan_type,
                    "plan_code": order.plan_code,
                    "country": order.country,
                    "proxy_address": str(cred.upstream_proxy_ip) if cred.upstream_proxy_ip else None,
                    "expires_at": expires_at.isoformat() if expires_at else None,
                    "days_left": days_left,
                    "tx_ref": order.tx_ref,
                })

            return ToolResult(ok=True, data={
                "expiring_soon": expiring,
                "message": f"{len(expiring)} proxy(ies) expiring within 7 days. Renew now to keep your IP!",
            })
    except Exception as exc:
        logger.exception("detect_renewal failed")
        return ToolResult(ok=False, error=f"Renewal detection failed: {exc}")


async def _compare_plans_tool(plan_type_a: str | None = None, plan_type_b: str | None = None) -> ToolResult:
    """Compare two plan types side-by-side.
    
    Use when customer asks "what's the difference between X and Y",
    "which is better", "compare residential and ISP".
    """
    comparisons = {
        ("residential", "mobile"): {
            "shared": "Both are residential IPs (real subscribers). Best for social media, account creation, ad verification.",
            "differences": [
                {"feature": "IP source", "residential": "Home broadband ISPs", "mobile": "Mobile carrier networks (4G/LTE)"},
                {"feature": "Trust score", "residential": "High", "mobile": "Highest (gold standard)"},
                {"feature": "Speed", "residential": "Fast", "mobile": "Moderate (carrier NAT)"},
                {"feature": "Price per GB", "residential": "₦1,000/GB", "mobile": "₦1,500/GB"},
                {"feature": "Detection risk", "residential": "Low", "mobile": "Lowest"},
                {"feature": "Best for", "residential": "Social media management, scraping, ad verification", "mobile": "Strict platforms, account creation, sneaker bots"},
            ],
            "recommendation": "Choose **Mobile** for strict platforms (Instagram, TikTok). Choose **Residential** for better value and high-volume work.",
        },
        ("residential", "isp"): {
            "shared": "Both look like residential/office connections. Good for scraping, automation, account management.",
            "differences": [
                {"feature": "IP source", "residential": "Real home subscribers", "isp": "Datacenter hardware, ISP-registered"},
                {"feature": "IP type", "residential": "Rotating pool (changes)", "isp": "Static (same IP for 30 days)"},
                {"feature": "Speed", "residential": "Fast", "isp": "Very fast"},
                {"feature": "Pricing", "residential": "Per GB (pay for traffic)", "isp": "Per IP/month (unlimited traffic)"},
                {"feature": "Best for", "residential": "Social media, ad verification, per-request rotation", "isp": "Long sessions, automation, scraping"},
            ],
            "recommendation": "Choose **ISP** for static IP / unlimited traffic / long sessions. Choose **Residential** for rotating IPs and social media.",
        },
        ("residential", "datacenter"): {
            "shared": "Both proxy your traffic through an IP that isn't yours.",
            "differences": [
                {"feature": "IP source", "residential": "Real home subscribers", "datacenter": "Bare-metal servers"},
                {"feature": "Detection", "residential": "Hard to detect", "datacenter": "Easily detected"},
                {"feature": "Speed", "residential": "Fast", "datacenter": "Fastest"},
                {"feature": "Pricing", "residential": "Per GB", "datacenter": "Per IP/month"},
                {"feature": "Price range", "residential": "₦1,000/GB", "datacenter": "₦2,000-2,500/IP/month"},
                {"feature": "Best for", "residential": "Social media, streaming, strict platforms", "datacenter": "Scraping, SEO, bulk ops where stealth doesn't matter"},
            ],
            "recommendation": "Choose **Datacenter** for large-scale scraping where cost matters. Choose **Residential** for anything where detection is a risk.",
        },
        ("isp", "datacenter"): {
            "shared": "Both are datacenter-class, static IP, unlimited traffic.",
            "differences": [
                {"feature": "IP registration", "isp": "Registered to real ISPs", "datacenter": "Datacenter ranges"},
                {"feature": "Trust score", "isp": "Medium-high (looks residential)", "datacenter": "Low (obvious datacenter)"},
                {"feature": "Price per IP", "isp": "₦5,000-6,500/month", "datacenter": "₦2,000-2,500/month"},
                {"feature": "Best for", "isp": "Sneaker sites, scraping with some stealth", "datacenter": "Pure volume, non-stealth"},
            ],
            "recommendation": "Choose **Datacenter** for cheapest per-IP. Choose **ISP** when you need slightly better reputation.",
        },
        ("mobile", "isp"): {
            "shared": "Both are premium options. Higher trust than datacenter.",
            "differences": [
                {"feature": "IP source", "mobile": "Mobile carriers", "isp": "ISP-registered datacenter"},
                {"feature": "IP type", "mobile": "Rotating pool", "isp": "Static"},
                {"feature": "Pricing", "mobile": "Per GB (₦1,500/GB)", "isp": "Per IP/month (₦5,000-6,500)"},
                {"feature": "Best for", "mobile": "Account creation, strict social platforms", "isp": "Long sessions, automation"},
            ],
            "recommendation": "Choose **Mobile** for highest trust and account creation. Choose **ISP** for static IP and unlimited traffic.",
        },
    }

    # Normalize input
    def normalize(pt: str | None) -> str:
        pt = (pt or "").lower().strip()
        mapping = {"dc": "datacenter", "data_center": "datacenter", "datacentre": "datacenter", "data centre": "datacenter"}
        return mapping.get(pt, pt)

    # If no specific comparison, return all comparisons
    if not plan_type_a and not plan_type_b:
        return ToolResult(ok=True, data={
            "message": "Ask me to compare two plans — e.g., 'compare residential and ISP' or 'what's the difference between mobile and datacenter'",
            "available_types": ["residential", "mobile", "isp", "datacenter"],
        })

    a, b = normalize(plan_type_a), normalize(plan_type_b)
    key = tuple(sorted([a, b]))
    comp = comparisons.get(key)

    if not comp:
        return ToolResult(ok=True, data={
            "message": f"I don't have a comparison for {plan_type_a} vs {plan_type_b}. Try: residential vs mobile, residential vs ISP, residential vs datacenter, ISP vs datacenter, mobile vs ISP.",
            "available_types": ["residential", "mobile", "isp", "datacenter"],
        })

    return ToolResult(ok=True, data={
        "plan_a": a,
        "plan_b": b,
        **comp,
    })


async def _escalate_bulk_inquiry_tool(customer_phone: str | None = None, quantity: int | None = None, plan_type: str | None = None, use_case: str | None = None) -> ToolResult:
    """Escalate bulk/enterprise pricing to admin.
    
    When customer needs >20 IPs or >100GB, pricing is custom.
    Escalates with full context so admin can follow up.
    """
    try:
        from app.services.charon.escalation_persist import persist_escalation_sync
        from app.database import async_session
        from app.models import Customer
        from sqlalchemy import select

        # Get customer info
        customer_name = "Unknown"
        if customer_phone:
            async with async_session() as session:
                stmt = select(Customer).where(Customer.phone == customer_phone)
                result = await session.execute(stmt)
                cust = result.scalar_one_or_none()
                if cust:
                    customer_name = cust.name

        summary = f"Bulk inquiry from {customer_name} ({customer_phone or 'unknown'}): {quantity or '?'} x {plan_type or 'proxy'} for {use_case or 'unspecified use case'}"
        persist_escalation_sync(
            conversation_id=f"bulk_{customer_phone or 'unknown'}",
            customer_email=None,
            customer_phone=customer_phone,
            customer_message=f"Bulk/enterprise pricing request: {quantity or '?'}x {plan_type or 'proxy'} — {use_case or 'unspecified'}",
            history_summary=summary,
            scenario_id="bulk_inquiry",
            reason="bulk_pricing",
        )

        return ToolResult(ok=True, data={
            "escalated": True,
            "message": summary,
            "customer_message": "I've sent your bulk pricing request to the team. They'll reach out with custom pricing within 24 hours. In the meantime, here are our standard plans — bulk discounts start at 20+ IPs or 100+ GB.",
        })
    except Exception as exc:
        logger.exception("escalate_bulk_inquiry failed")
        return ToolResult(ok=False, error=f"Escalation failed: {exc}")


# ─── Payment Recovery Tool (added 2026-08-29) ─────────────────────────────────


async def _retry_payment_tool(order_id: str, customer_email: str | None = None, customer_phone: str | None = None) -> ToolResult:
    """Check a failed/pending order and create a new checkout link.
    
    Use when customer says "my payment failed", "I want to pay again",
    "generate new payment link".
    """
    try:
        from app.database import async_session
        from app.models import Order
        from sqlalchemy import select

        async with async_session() as session:
            stmt = select(Order).where(Order.order_id == order_id)
            result = await session.execute(stmt)
            order = result.scalar_one_or_none()

            if not order:
                return ToolResult(ok=False, error=f"Order {order_id} not found")

            if order.status not in ("pending", "failed"):
                return ToolResult(ok=False, error=f"Order status is '{order.status}' — cannot retry payment")

            amount = float(order.amount_paid_ngn or 0)
            if amount <= 0:
                return ToolResult(ok=False, error="Invalid order amount")

            # Generate new checkout
            cust_email = customer_email or f"customer-{order_id[:8]}@styxproxy.local"
            cust_phone = customer_phone or order.customer_phone or ""

            from app.services.flutterwave import create_flutterwave_invoice
            invoice = await create_flutterwave_invoice(
                amount=amount, customer_email=cust_email,
                customer_phone=cust_phone, description=f"Styxproxy {order.plan_type} proxy (retry)",
            )
            checkout_url = invoice.get("checkout_url", "")

            return ToolResult(ok=True, data={
                "order_id": order_id,
                "checkout_url": checkout_url,
                "amount_ngn": amount,
                "message": f"Here's a new payment link for order {order_id}: {checkout_url}",
            })
    except Exception as exc:
        logger.exception("retry_payment failed")
        return ToolResult(ok=False, error=f"Payment retry failed: {exc}")


# ─── Integration Docs Tool (added 2026-08-29) ─────────────────────────────────


async def _get_integration_docs(integration_type: str | None = None) -> ToolResult:
    """Return developer integration docs for proxy setup.
    
    Covers: Python, Node.js, Selenium, Puppeteer, cURL, browser config.
    Use when customer asks "how do I integrate", "API docs", "code example".
    """
    docs = {
        "python": {
            "description": "Python requests with proxy",
            "code": "import requests\n\nproxies = {\n    'http': 'http://USERNAME:PASSWORD@proxy.styxproxy.com:PORT',\n    'https': 'http://USERNAME:PASSWORD@proxy.styxproxy.com:PORT'\n}\n\nresponse = requests.get('https://ipinfo.io', proxies=proxies)\nprint(response.json())",
            "tips": ["Use `requests.Session()` to persist auth across calls", "Rotate by changing credentials or using different orders"],
        },
        "node": {
            "description": "Node.js with axios + proxy",
            "code": "const axios = require('axios');\n\nconst response = await axios.get('https://ipinfo.io', {\n  proxy: {\n    protocol: 'http',\n    host: 'proxy.styxproxy.com',\n    port: PORT,\n    auth: {\n      username: 'USERNAME',\n      password: 'PASSWORD'\n    }\n  }\n});\nconsole.log(response.data);",
            "tips": ["For SOCKS5, use `socks-proxy-agent` package", "Set `axios.defaults.proxy` for global proxy"],
        },
        "selenium": {
            "description": "Selenium + Chrome with proxy auth",
            "code": "from selenium import webdriver\nfrom selenium.webdriver.chrome.options import Options\n\noptions = Options()\noptions.add_argument('--proxy-server=http://proxy.styxproxy.com:PORT')\n\ndriver = webdriver.Chrome(options=options)\ndriver.get('https://ipinfo.io')\n# Handle proxy auth popup with AutoAlert or proxy-auth extension",
            "tips": ["Proxy auth popups need extension or AutoAlert", "Use Chrome Proxy Auth Extension for headless mode"],
        },
        "puppeteer": {
            "description": "Puppeteer with proxy",
            "code": "const browser = await puppeteer.launch({\n  args: ['--proxy-server=http://proxy.styxproxy.com:PORT']\n});\nconst page = await browser.newPage();\nawait page.authenticate({\n  username: 'USERNAME',\n  password: 'PASSWORD'\n});\nawait page.goto('https://ipinfo.io');",
            "tips": ["Use `page.authenticate()` for proxy auth", "Stealth plugin recommended for bot detection"],
        },
        "curl": {
            "description": "cURL with proxy",
            "code": "curl -x http://USERNAME:PASSWORD@proxy.styxproxy.com:PORT https://ipinfo.io",
            "tips": ["Add `--proxy-insecure` if testing with self-signed certs", "Use `-v` to debug proxy connection issues"],
        },
        "browser": {
            "description": "Browser manual proxy config",
            "setup": [
                "Proxy host: proxy.styxproxy.com",
                "Port: YOUR_PORT (check credentials page)",
                "Username: YOUR_USERNAME",
                "Password: YOUR_PASSWORD",
                "Protocol: HTTP, HTTPS, or SOCKS5",
            ],
            "browsers": {
                "Firefox": "Settings → Network → Manual proxy → Enter credentials",
                "Chrome": "Use SwitchyOmega or FoxyProxy extension",
                "Safari": "Settings → Advanced → Proxies → Web Proxy (HTTP)",
            },
        },
        "socks5": {
            "description": "SOCKS5 proxy configuration",
            "setup": [
                "Host: proxy.styxproxy.com",
                "Port: YOUR_PORT",
                "Auth: Username + Password",
                "Protocol: SOCKS5",
            ],
            "tips": ["SOCKS5 supports TCP and UDP", "Works with most tools that support SOCKS (curl, python-socks, etc.)"],
        },
    }

    if not integration_type:
        return ToolResult(ok=True, data={
            "available_integrations": list(docs.keys()),
            "message": "Ask for a specific integration: python, node, selenium, puppeteer, curl, browser, socks5",
        })

    key = integration_type.lower().strip()
    if key in ("nodejs", "node.js", "javascript", "js"):
        key = "node"
    elif key in ("py", "requests"):
        key = "python"
    elif key in ("chrome", "firefox", "safari", "manual"):
        key = "browser"
    elif key in ("socks", "socks5-proxy"):
        key = "socks5"

    if key in docs:
        return ToolResult(ok=True, data=docs[key])
    else:
        return ToolResult(ok=True, data={
            "message": f"No docs for '{integration_type}'. Available: {', '.join(docs.keys())}",
            "available_integrations": list(docs.keys()),
        })


# ─── Telegram Sales Tools (added 2026-08-29) ─────────────────────────────────


async def _create_order_tool(
    channel_user_id: str,
    plan_code: str,
    country: str = "NG",
    customer_email: str | None = None,
    quantity: int = 1,
    quantity_gb: int | None = None,
    gateway: str = "flutterwave",
    channel: str = "web",
    customer_name: str | None = None,
) -> ToolResult:
    """Create an order for a customer with real identity per channel."""
    try:
        from sqlalchemy import select
        from app.database import async_session
        from app.models import Customer, Order, PlatformAccount
        from app.routers.orders import resolve_plan, generate_order_id
        from app.services.referral import generate_referral_code

        # Derive real customer identity based on channel
        if channel == "telegram":
            identity = channel_user_id
            platform = "telegram"
        elif channel == "whatsapp":
            identity = channel_user_id
            platform = "whatsapp"
        else:
            identity = f"anon_{channel_user_id}"
            platform = "web"

        async with async_session() as session:
            stmt = select(Customer).where(Customer.phone == identity)
            result = await session.execute(stmt)
            customer = result.scalar_one_or_none()

            if not customer:
                name = customer_name or customer_email.split("@")[0][:100] if customer_email else f"Customer-{channel_user_id[:8]}"
                customer = Customer(
                    phone=identity, name=name, blocked=False,
                    free_trials_used_today=0, referral_code=generate_referral_code(),
                )
                if customer_email:
                    customer.email = customer_email
                session.add(customer)
                await session.flush()

            plan = await resolve_plan(session, plan_code, country=country)
            if not plan:
                return ToolResult(ok=False, error=f"Invalid plan '{plan_code}' for country {country}")

            pt = plan.plan_type.lower()
            if pt in ("residential", "mobile"):
                gb = quantity_gb or plan.quantity or 1
                if plan.price_per_gb is None:
                    return ToolResult(ok=False, error="Plan has no price_per_gb configured")
                total_amount = float(plan.price_per_gb) * gb
                effective_quantity = gb
            else:
                if plan.price_ngn is None:
                    return ToolResult(ok=False, error="Plan has no price_ngn configured")
                total_amount = float(plan.price_ngn) * quantity
                effective_quantity = quantity

            stmt_pa = select(PlatformAccount).where(
                PlatformAccount.platform == platform,
                PlatformAccount.platform_user_id == channel_user_id
            )
            result_pa = await session.execute(stmt_pa)
            platform_account = result_pa.scalar_one_or_none()

            if not platform_account:
                platform_account = PlatformAccount(
                    platform=platform,
                    platform_user_id=channel_user_id,
                    customer_id=customer.id
                )
                session.add(platform_account)
                await session.flush()
            elif platform_account.customer_id is None:
                platform_account.customer_id = customer.id

            order_id = generate_order_id()
            order = Order(
                order_id=order_id, platform_account_id=platform_account.id,
                customer_phone=customer.phone, plan_type=pt, plan_code=plan_code,
                country=plan.country, quantity=effective_quantity,
                amount_paid_ngn=total_amount, status="pending",
            )
            session.add(order)
            await session.commit()
            await session.refresh(order)

            await _set_rls_context(session, customer.phone)

            return ToolResult(ok=True, data={
                "order_id": order.order_id, "plan_code": plan_code,
                "plan_type": pt, "country": country,
                "quantity": effective_quantity, "amount_ngn": total_amount,
                "plan_name": plan.name or plan_code,
            })
    except Exception as exc:
        logger.exception("create_order tool failed")
        return ToolResult(ok=False, error=f"Order creation failed: {exc}")


async def _initiate_payment_tool(
    order_id: str, customer_email: str | None = None,
    customer_phone: str | None = None, gateway: str = "flutterwave",
) -> ToolResult:
    """Initiate payment for an existing pending order."""
    try:
        from app.database import async_session
        from app.models import Order

        async with async_session() as session:
            from sqlalchemy import select
            stmt = select(Order).where(Order.order_id == order_id)
            result = await session.execute(stmt)
            order = result.scalar_one_or_none()

            if not order:
                return ToolResult(ok=False, error=f"Order {order_id} not found")
            if order.status != "pending":
                return ToolResult(ok=False, error=f"Order status is '{order.status}'")
            amount = float(order.amount_paid_ngn or 0)
            if amount <= 0:
                return ToolResult(ok=False, error="Invalid order amount")

            tx_ref = f"TXF-{uuid.uuid4().hex[:12].upper()}"
            order.payment_reference = tx_ref
            cust_email = customer_email or f"customer-{order_id[:8]}@styxproxy.local"
            cust_phone = customer_phone or order.customer_phone or ""
            await session.commit()

            if gateway == "flutterwave":
                from app.services.flutterwave import create_flutterwave_invoice
                invoice = await create_flutterwave_invoice(
                    amount=amount, customer_email=cust_email,
                    customer_phone=cust_phone, description=f"Styxproxy {order.plan_type} proxy",
                )
                checkout_url = invoice.get("checkout_url", "")
                fw_tx_ref = invoice.get("tx_ref", "")
                if fw_tx_ref and order.payment_reference != fw_tx_ref:
                    order.payment_reference = fw_tx_ref
                    await session.commit()
            else:
                return ToolResult(ok=False, error=f"Unsupported gateway: {gateway}")

            return ToolResult(ok=True, data={
                "tx_ref": order.payment_reference, "order_id": order_id,
                "checkout_url": checkout_url, "amount_ngn": amount, "gateway": gateway,
            })
    except Exception as exc:
        logger.exception("initiate_payment tool failed")
        return ToolResult(ok=False, error=f"Payment initiation failed: {exc}")


# ─── Register all tools ──────────────────────────────────────────────────────

registry.register(ToolSpec(
    name="lookup_order",
    description="Look up an order by its Flutterwave transaction reference (tx_ref).",
    schema={"type": "object", "properties": {"tx_ref": {"type": "string", "description": "The customer's Flutterwave transaction reference"}}, "required": ["tx_ref"]},
    handler=_lookup_order_tx_ref,
))

registry.register(ToolSpec(
    name="lookup_payment_status",
    description="Look up payment status for a transaction reference via Flutterwave.",
    schema={"type": "object", "properties": {"tx_ref": {"type": "string", "description": "The customer's Flutterwave transaction reference"}}, "required": ["tx_ref"]},
    handler=_lookup_payment_status,
))

registry.register(ToolSpec(
    name="generate_order_link",
    description="Generate a direct link to the customer's order page.",
    schema={"type": "object", "properties": {"tx_ref": {"type": "string", "description": "The customer's Flutterwave transaction reference"}}, "required": ["tx_ref"]},
    handler=_generate_order_link,
))

registry.register(ToolSpec(
    name="generate_receipt_link",
    description="Generate a download link for the customer's official receipt PDF.",
    schema={"type": "object", "properties": {"tx_ref": {"type": "string", "description": "The customer's Flutterwave transaction reference"}}, "required": ["tx_ref"]},
    handler=_generate_receipt_link,
))

registry.register(ToolSpec(
    name="get_product_catalog",
    description="Return the full product catalog with plans and prices.",
    schema={"type": "object", "properties": {}},
    handler=_get_product_catalog,
))

registry.register(ToolSpec(
    name="get_customer_context",
    description="Return customer profile, recent orders, and spend summary. Use this to personalize replies — know if they're new, returning, or VIP. Requires customer_phone param.",
    schema={"type": "object", "properties": {"customer_phone": {"type": "string", "description": "The customer's phone/identity from channel context"}}, "required": ["customer_phone"]},
    handler=_get_customer_context_tool,
))

registry.register(ToolSpec(
    name="suggest_articles",
    description="Suggest relevant knowledge-base chunks for a topic.",
    schema={"type": "object", "properties": {"topic": {"type": "string", "description": "Topic keyword or phrase"}}, "required": ["topic"]},
    handler=_suggest_articles,
))

registry.register(ToolSpec(
    name="create_order",
    description="Create a new order for a Telegram or WhatsApp customer. Returns order_id, amount_ngn, plan details. Call initiate_payment next.",
    schema={
        "type": "object",
        "properties": {
            "channel_user_id": {"type": "string", "description": "Telegram chat_id or WhatsApp phone hash"},
            "plan_code": {"type": "string", "description": "Plan code (e.g., 'isp-uk-1')"},
            "country": {"type": "string", "default": "NG"},
            "customer_email": {"type": "string"},
            "quantity": {"type": "integer", "default": 1},
            "quantity_gb": {"type": "integer"},
            "gateway": {"type": "string", "default": "flutterwave"},
        },
        "required": ["channel_user_id", "plan_code"],
    },
    handler=_create_order_tool,
))

registry.register(ToolSpec(
    name="initiate_payment",
    description="Initiate payment for an existing pending order. Creates a Flutterwave invoice and returns a checkout URL.",
    schema={
        "type": "object",
        "properties": {
            "order_id": {"type": "string", "description": "The order_id returned by create_order"},
            "customer_email": {"type": "string"},
            "customer_phone": {"type": "string"},
            "gateway": {"type": "string", "default": "flutterwave"},
        },
        "required": ["order_id"],
    },
    handler=_initiate_payment_tool,
))

registry.register(ToolSpec(
    name="get_setup_guide",
    description="Return proxy setup instructions. Use when customer asks 'how do I set up', 'proxy not working', 'configure browser'. Pass plan_type (residential, mobile, isp, datacenter) and optional protocol.",
    schema={"type": "object", "properties": {"plan_type": {"type": "string", "description": "residential, mobile, isp, or datacenter"}, "protocol": {"type": "string", "description": "http, https, or socks5"}}, "required": []},
    handler=_get_setup_guide,
))

registry.register(ToolSpec(
    name="get_troubleshooting",
    description="Return troubleshooting steps for common proxy issues. Use when customer reports: auth failures, IP banned, slow speed, connection refused, proxy not working, or expired credentials. Pass issue keyword.",
    schema={"type": "object", "properties": {"issue": {"type": "string", "description": "auth_failed, ip_banned, slow_speed, connection_refused, not_working, expired"}, "plan_type": {"type": "string", "description": "residential, mobile, isp, datacenter"}}, "required": []},
    handler=_get_troubleshooting,
))

registry.register(ToolSpec(
    name="list_customer_orders",
    description="Return ALL orders for the customer (RLS-gated). No tx_ref needed. Use when customer asks 'show me my orders', 'what did I buy', 'my orders', 'order history'.",
    schema={"type": "object", "properties": {"customer_phone": {"type": "string", "description": "Customer phone/identity from channel context"}}, "required": ["customer_phone"]},
    handler=_list_customer_orders_tool,
))

registry.register(ToolSpec(
    name="check_data_remaining",
    description="Check remaining data for residential/mobile proxies. Returns data_remaining_gb, data_total_gb, usage percentage. Use when customer asks 'how much data do I have left', 'data usage', 'bandwidth remaining'.",
    schema={"type": "object", "properties": {"customer_phone": {"type": "string", "description": "Customer phone/identity from channel context"}}, "required": ["customer_phone"]},
    handler=_check_data_remaining_tool,
))

registry.register(ToolSpec(
    name="get_referral_info",
    description="Return customer's referral code, earnings, and terms. Use when customer asks 'referral', 'refer a friend', 'my referral code', 'how to earn'.",
    schema={"type": "object", "properties": {"customer_phone": {"type": "string", "description": "Customer phone/identity from channel context"}}, "required": ["customer_phone"]},
    handler=_get_referral_info_tool,
))

registry.register(ToolSpec(
    name="detect_renewal",
    description="Detect proxies expiring within 7 days. Returns credentials that need renewal soon. Use for proactive renewal reminders when customer asks 'when does my proxy expire'.",
    schema={"type": "object", "properties": {"customer_phone": {"type": "string", "description": "Customer phone/identity from channel context"}}, "required": ["customer_phone"]},
    handler=_detect_renewal_tool,
))

registry.register(ToolSpec(
    name="compare_plans",
    description="Compare two plan types side-by-side. Use when customer asks 'what's the difference between X and Y', 'which is better', 'compare residential and ISP'. Pass two plan types.",
    schema={"type": "object", "properties": {"plan_type_a": {"type": "string", "description": "residential, mobile, isp, or datacenter"}, "plan_type_b": {"type": "string", "description": "residential, mobile, isp, or datacenter"}}, "required": []},
    handler=_compare_plans_tool,
))

registry.register(ToolSpec(
    name="escalate_bulk_inquiry",
    description="Escalate bulk/enterprise pricing to admin. Use when customer needs >20 IPs or >100GB, or asks about custom/wholesale pricing. Pass quantity, plan_type, use_case.",
    schema={"type": "object", "properties": {"customer_phone": {"type": "string"}, "quantity": {"type": "integer"}, "plan_type": {"type": "string"}, "use_case": {"type": "string"}}, "required": []},
    handler=_escalate_bulk_inquiry_tool,
))

registry.register(ToolSpec(
    name="retry_payment",
    description="Check a failed/pending order and create a new checkout link. Use when customer says 'my payment failed', 'I want to pay again', 'generate new payment link'.",
    schema={"type": "object", "properties": {"order_id": {"type": "string", "description": "The order_id to retry payment for"}, "customer_email": {"type": "string"}, "customer_phone": {"type": "string"}}, "required": ["order_id"]},
    handler=_retry_payment_tool,
))

registry.register(ToolSpec(
    name="get_integration_docs",
    description="Return developer integration docs for proxy setup. Covers: Python, Node.js, Selenium, Puppeteer, cURL, browser config, SOCKS5. Use when customer asks 'how do I integrate', 'code example', 'API docs'.",
    schema={"type": "object", "properties": {"integration_type": {"type": "string", "description": "python, node, selenium, puppeteer, curl, browser, socks5"}}, "required": []},
    handler=_get_integration_docs,
))


# ─── Forbidden tools (not registered — guard rails) ──────────────────────────

# - refund_order
# - replace_proxy
# - cancel_order
# - reissue_credentials
# - block_customer
# - issue_free_trial
# - change_pricing
