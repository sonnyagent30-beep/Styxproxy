"""
Product catalog service.

Provides plan_type templates so the customer picks:
  - plan_type (residential, mobile, datacenter, isp)
  - country (location)
  - rotation_mode (rotating pool vs static IP)
  - quantity_gb + duration_days (or defaults)

Then creates a styxproxy_credentials row with the chosen config and provisions
the relay entry.
"""

import secrets
import string
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Order, Plan, StyxproxyCredential

# ─── Plan catalog (what we actually sell) ─────────────────────────────────────

# Countries supported per plan_type (post-trial, Rayobyte proven to work)
# Countries supported per plan_type (user directive Jul 30):
#   residential: any Rayobyte country proven to work in 8-country trial
#   datacenter:  US + UK ONLY (other DCs not yet provisioned)
#   mobile:      COMING SOON (not yet available — Rayobyte mobile gateway pending Hakan)
#   isp:         COMING SOON (not yet available — ISP IPs pending Hakan provisioning)
SUPPORTED_COUNTRIES = {
    # Customer sees GB; catalog translates to UK for DB lookup
    "residential": ["US", "GB", "DE", "CA", "AU", "FR", "BR", "IN"],
    "datacenter":  ["US", "UK"],
}

# When looking up plans in DB, translate customer-facing code → DB code
COUNTRY_TRANSLATION = {
    "GB": "UK",  # residential plans stored under legacy "UK"
    # US, DE, CA, AU, FR, BR, IN — same in DB and customer-facing
}

# Rotation modes supported per plan_type
# residential: rotating OR static (customer picks)
# datacenter:  static only (DC IPs are inherently static)
SUPPORTED_ROTATION_MODES = {
    "residential": ["rotating", "static"],
    "datacenter":  ["static"],
}


def get_plan_template_for(plan_type: str) -> dict:
    """Return what we offer for a plan_type (country options, rotation options, default price)."""
    plan_type = plan_type.lower()
    return {
        "plan_type": plan_type,
        "rotation_mode_options": SUPPORTED_ROTATION_MODES.get(plan_type, ["rotating"]),
        "available_countries": SUPPORTED_COUNTRIES.get(plan_type, []),
        "supports_country_change": plan_type in ("residential", "datacenter"),  # DC = US/UK, customer can switch
    }


# ─── Credential provisioning ──────────────────────────────────────────────────


def generate_styxproxy_username(phone: Optional[str] = None) -> str:
    """Generate SOCKS5 username (random, no phone dependency for purchase)."""
    suffix = secrets.token_hex(4)  # 8 hex chars
    return f"sty_{suffix}"


def generate_styxproxy_password(length: int = 16) -> str:
    """Random alphanumeric password."""
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


# ─── Upstream config ─────────────────────────────────────────────────────────

UPSTREAM_GATEWAYS = {
    "residential": {
        "host": "la.residential.rayobyte.com",
        "port": 8000,
        "upstream_protocol": "http",  # HTTP CONNECT + Basic auth
        "upstream_type": "rayobyte_resi",
    },
    "mobile": {
        # Until Hakan confirms actual mobile gateway, fall back to residential
        "host": "la.residential.rayobyte.com",
        "port": 8000,
        "upstream_protocol": "http",
        "upstream_type": "rayobyte_mobile",
    },
    "datacenter": {
        "host": "",  # set per-credential (static IP)
        "port": 1080,
        "upstream_protocol": "socks5",
        "upstream_type": "rayobyte_dc",
    },
    "isp": {
        "host": "",
        "port": 1080,
        "upstream_protocol": "socks5",
        "upstream_type": "rayobyte_isp",
    },
}


def build_upstream_password(
    plan_type: str,
    rotation_mode: str,
    country: str,
    session_id: Optional[str] = None,
    upstream_user: str = "",
) -> str:
    """Build the upstream (Rayobyte) password from our credential's settings.

    Rayobyte password format:
      Rotating pool: <user>-country-<CC>
      Static IP:     <user>-session-<RANDOM>-country-<CC>

    Example for residential US rotating: styx_t1-country-US
    Example for residential US static:   styx_t1-session-a1b2c3d4-country-US
    """
    if rotation_mode == "static":
        sid = session_id or secrets.token_hex(4)  # 8 hex chars
        return f"{upstream_user}-session-{sid}-country-{country}"
    else:
        return f"{upstream_user}-country-{country}"


# ─── Catalog API ──────────────────────────────────────────────────────────────


async def list_catalog(session: AsyncSession) -> dict:
    """List all plan_type templates with their options."""
    templates = []
    all_countries = set()
    all_rotation_modes = set()

    # Pull all active plans
    plans_result = await session.execute(
        select(Plan).where(Plan.is_active is True).order_by(Plan.sort_order, Plan.plan_code)
    )
    plans = plans_result.scalars().all()

    # Group by plan_type
    plans_by_type: dict = {}
    for p in plans:
        plans_by_type.setdefault(p.plan_type, []).append(p)

    for plan_type, plan_list in plans_by_type.items():
        template = get_plan_template_for(plan_type)
        all_countries.update(template["available_countries"])
        all_rotation_modes.update(template["rotation_mode_options"])

        variants = []
        # Build variants for each (country, rotation_mode) combination
        for country in template["available_countries"]:
            for rotation_mode in template["rotation_mode_options"]:
                # Find the cheapest plan that matches
                matching = [p for p in plan_list if p.country.upper() == country.upper()]
                if not matching:
                    continue
                base_plan = matching[0]
                base_price = float(base_plan.price_ngn)
                if rotation_mode == "static":
                    base_price = base_price * float(base_plan.static_price_multiplier)

                variant_features = list(base_plan.features.get("features", [])) if base_plan.features else []
                if rotation_mode == "static":
                    variant_features.append("Pinned IP — same address for the lifetime of the session")
                else:
                    variant_features.append("Rotating pool — new IP per request")

                variants.append({
                    "plan_code": base_plan.plan_code,
                    "plan_type": plan_type,
                    "country": country.upper(),
                    "rotation_mode": rotation_mode,
                    "price_ngn": round(base_price, 2),
                    "quantity": base_plan.quantity,
                    "duration_days": base_plan.duration_days,
                    "features": variant_features,
                    "in_stock": True,
                })

        if not variants:
            continue

        # Default price = cheapest rotating variant
        cheapest_rotating = min(
            (v for v in variants if v["rotation_mode"] == "rotating"),
            key=lambda v: v["price_ngn"],
            default=None,
        )
        default_price = cheapest_rotating["price_ngn"] if cheapest_rotating else variants[0]["price_ngn"]
        default_quantity = cheapest_rotating["quantity"] if cheapest_rotating else variants[0]["quantity"]
        default_duration = cheapest_rotating["duration_days"] if cheapest_rotating else variants[0]["duration_days"]
        default_plan = plan_list[0]

        description_map = {
            "residential": "Real home Wi-Fi connections from a rotating pool of consumer devices. Pick from US, GB, DE, CA, AU, FR, BR, IN. Switch countries anytime via /manage. Best for scraping, sneaker bots, ad verification.",  # noqa: E501
            "datacenter":  "Fast, low-cost static IPs in cloud data centers (US or UK). Same IP every request. Best for high-volume non-sensitive workloads. Switch between US and UK via /manage.",  # noqa: E501
            # mobile and isp are coming soon — UI hides them, this just prevents crashes
            "mobile":      "3G/4G mobile carrier IPs. Coming soon — not yet available for purchase.",
            "isp":         "Real residential IPs hosted at ISPs but sold as static. Coming soon — not yet available for purchase.",  # noqa: E501
        }

        templates.append({
            "plan_type": plan_type,
            "rotation_mode_options": template["rotation_mode_options"],
            "available_countries": template["available_countries"],
            "base_quantity_gb": default_quantity,
            "base_price_ngn": default_price,
            "duration_days": default_duration,
            "static_price_multiplier": float(default_plan.static_price_multiplier),
            "supports_country_change": template["supports_country_change"],
            "description": description_map.get(plan_type, ""),
            "variants": variants,
        })

    return {
        "templates": templates,
        "countries_supported": sorted(all_countries),
        "rotation_modes_supported": sorted(all_rotation_modes),
    }


# ─── Order + credential creation ─────────────────────────────────────────────


async def create_order_with_credential(
    session: AsyncSession,
    customer_phone: str,
    plan_type: str,
    country: str,
    rotation_mode: str,
    payment_reference: Optional[str] = None,
    quantity_gb: Optional[int] = None,
    duration_days: Optional[int] = None,
    customer_user: str = "styx_t1",  # Rayobyte sub-user to draw from (single shared for trial)
) -> dict:
    """Create an order + matching StyxproxyCredential row.

    Returns the order + credential connection details so customer can connect immediately.
    """
    plan_type = plan_type.lower()
    rotation_mode = rotation_mode.lower()
    country = country.upper()

    # Validate plan_type + country + rotation_mode
    template = get_plan_template_for(plan_type)
    if country not in template["available_countries"]:
        raise ValueError(f"country_not_supported:{plan_type}:{country}")
    if rotation_mode not in template["rotation_mode_options"]:
        raise ValueError(f"rotation_mode_not_supported:{plan_type}:{rotation_mode}")

    # Translate customer-facing country code to DB code if needed (GB → UK for residential)
    db_country = COUNTRY_TRANSLATION.get(country, country)

    # Find a matching plan (use the first one with matching plan_type + country)
    plan_result = await session.execute(
        select(Plan).where(
            Plan.plan_type == plan_type,
            Plan.country == db_country,
            Plan.is_active is True,
        ).order_by(Plan.price_ngn)
    )
    plan = plan_result.scalars().first()
    if not plan:
        raise ValueError(f"no_active_plan:{plan_type}:{country}")

    # Compute price (apply static multiplier if needed)
    base_price = float(plan.price_ngn)
    if rotation_mode == "static":
        base_price = base_price * float(plan.static_price_multiplier)

    # Defaults
    final_quantity = quantity_gb or plan.quantity
    final_duration = duration_days or plan.duration_days
    expires_at = datetime.now(timezone.utc) + timedelta(days=final_duration)

    # Build Rayobyte upstream password (relay needs this for upstream auth)
    upstream_template = UPSTREAM_GATEWAYS.get(plan_type, {})
    upstream_host = upstream_template.get("host", "")
    upstream_port = upstream_template.get("port", 8000)
    upstream_protocol = upstream_template.get("upstream_protocol", "http")
    upstream_type = upstream_template.get("upstream_type", "rayobyte_resi")

    if rotation_mode == "static":
        # Generate session_id for Rayobyte sticky session
        session_id = secrets.token_hex(4)  # 8 hex chars
        upstream_pass = build_upstream_password(plan_type, "static", country, session_id, customer_user)
        # For static mode, set our own sticky_session_minutes so the relay knows
        our_session_id = session_id
        our_session_minutes = 60  # max
        our_session_expires = datetime.now(timezone.utc) + timedelta(hours=our_session_minutes)
    else:
        session_id = None
        upstream_pass = build_upstream_password(plan_type, "rotating", country, None, customer_user)
        our_session_id = None
        our_session_minutes = 0
        our_session_expires = None

    # Customer-facing SOCKS5 credentials (different from upstream — what they connect with)
    our_username = generate_styxproxy_username(customer_phone)
    our_password = generate_styxproxy_password()

    # Create order
    import uuid as uuid_module
    order_id = f"ord_{uuid_module.uuid4().hex[:12]}"
    order = Order(
        order_id=order_id,
        customer_phone=customer_phone,
        plan_type=plan_type,
        plan_code=plan.plan_code,
        country=country,
        quantity=final_quantity,
        amount_paid_ngn=base_price,
        payment_reference=payment_reference,
        rotation_mode=rotation_mode,
        status="active",  # skip payment flow for now (dev mode)
        data_total_gb=final_quantity,
        data_remaining_gb=final_quantity,
        expires_at=expires_at,
        data_expires=expires_at,
    )
    session.add(order)
    await session.flush()  # get order_id

    # Create styxproxy_credential
    credential = StyxproxyCredential(
        styxproxy_username=our_username,
        styxproxy_password=our_password.encode("utf-8"),
        customer_phone=customer_phone,
        order_id=order_id,
        pool_type=plan_type,
        protocol="socks5",  # always SOCKS5 for customer-facing
        provider_name="rayobyte",
        provider_username=customer_user,
        provider_password=upstream_pass,
        upstream_proxy_ip=upstream_host,
        upstream_proxy_port=upstream_port,
        status="active",
        expires_at=expires_at,
        # New fields
        rotation_mode=rotation_mode,
        country_target=country,
        sticky_session_minutes=our_session_minutes,
        session_id=our_session_id,
        session_expires_at=our_session_expires,
        assigned_static_session_id=session_id,
        # Daily-change reset timestamps (UTC midnight)
        password_rotations_reset_at=datetime.now(timezone.utc).date(),
        location_changes_reset_at=datetime.now(timezone.utc).date(),
        rotation_mode_changes_reset_at=datetime.now(timezone.utc).date(),
    )
    session.add(credential)
    await session.flush()

    # Link order → credential
    order.styxproxy_credential_id = credential.id

    # Create relay entry (so the relay picks it up within 30s)
    from sqlalchemy import text
    await session.execute(
        text("""
            INSERT INTO styxproxy_relay_entries
              (customer_id, credential_id, upstream_type, upstream_host, upstream_port,
               upstream_user, upstream_pass, upstream_protocol, exit_ip_strategy,
               exit_ip_pool_code, region, monthly_bandwidth_gb, status)
            VALUES
              ((SELECT id FROM customers WHERE phone = :phone LIMIT 1),
               :cred_id, :upstream_type, :host, :port,
               :upstream_user, :upstream_pass, :protocol, :strategy,
               :country, :country, :gb, 'active')
        """),
        {
            "phone": customer_phone,
            "cred_id": credential.id,
            "upstream_type": upstream_type,
            "host": upstream_host,
            "port": upstream_port,
            "upstream_user": customer_user,
            "upstream_pass": upstream_pass,
            "protocol": upstream_protocol,
            "strategy": "pool" if rotation_mode == "rotating" else "single",
            "country": country,
            "gb": final_quantity,
        },
    )

    await session.commit()

    # Build response with connection examples
    from app.services.proxy_management import (
        PROXY_PORT_HTTP,
        PROXY_PORT_SOCKS5,
        PROXY_PUBLIC_HOST,
        build_curl_http_example,
        build_curl_socks5_example,
        build_python_socks5_example,
    )

    return {
        "order_id": order_id,
        "plan_type": plan_type,
        "country": country,
        "rotation_mode": rotation_mode,
        "quantity_gb": final_quantity,
        "duration_days": final_duration,
        "amount_paid_ngn": round(base_price, 2),
        "status": "active",
        "styxproxy_username": our_username,
        "styxproxy_password": our_password,
        "proxy_host": PROXY_PUBLIC_HOST,
        "proxy_port_socks5": PROXY_PORT_SOCKS5,
        "proxy_port_http": PROXY_PORT_HTTP,
        "protocol": "socks5",
        "expires_at": expires_at.isoformat() if expires_at else None,
        "curl_socks5_example": build_curl_socks5_example(our_username, our_password),
        "curl_http_example": build_curl_http_example(our_username, our_password),
        "python_socks5_example": build_python_socks5_example(our_username, our_password),
        "assigned_static_ip": None,  # populated on first use (relay reports back)
        "credential_id": credential.id,
    }