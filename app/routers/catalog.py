"""
Catalog + order creation router.

GET    /api/catalog          - list plan_type templates with country + rotation options
POST   /api/orders           - create order + provision credential (customer picks location + rotation_mode)
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_account
from app.database import get_session
from app.schemas_catalog import OrderCreateRequest, OrderCreateResponse, ProductTemplatesResponse
from app.services.catalog import (
    create_order_with_credential,
    list_catalog,
    list_enabled_country_codes,
)

router = APIRouter(prefix="/api", tags=["catalog"])


@router.get("/catalog", response_model=ProductTemplatesResponse)
async def get_catalog(session: AsyncSession = Depends(get_session)):
    """List all plan_type templates with available countries + rotation modes.

    Customer uses this to see what they can buy before hitting /api/orders.
    """
    return await list_catalog(session)


@router.post("/orders", response_model=OrderCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_order(
    body: OrderCreateRequest,
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_account),
):
    """Buy a proxy — pick plan_type + country + rotation_mode.

    Customer picks location (country) and rotation mode (rotating pool vs static IP)
    at purchase. They can later change both via PATCH /api/proxies/{id}.

    Returns the order + SOCKS5 connection details + curl/python examples.
    The plaintext password is shown ONCE here — store it now.
    """
    customer = current_user.get("customer")
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No customer profile found. Register via /api/platform/register first.",
        )

    try:
        result = await create_order_with_credential(
            session,
            customer_phone=customer.phone,
            plan_type=body.plan_type,
            country=body.country,
            rotation_mode=body.rotation_mode,
            payment_reference=body.payment_reference,
            quantity_gb=body.quantity_gb,
            duration_days=body.duration_days,
        )
    except ValueError as e:
        msg = str(e)
        if msg.startswith("country_not_supported"):
            _, plan_type, country = msg.split(":")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Country {country} is not available for {plan_type}. See /api/catalog for options.",
            )
        if msg.startswith("rotation_mode_not_supported"):
            _, plan_type, mode = msg.split(":")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Rotation mode '{mode}' is not available for {plan_type}.",
            )
        if msg.startswith("no_active_plan"):
            _, plan_type, country = msg.split(":")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No active plan for {plan_type} in {country}.",
            )
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=msg)

    return OrderCreateResponse(**result)


# ─── Public Countries Endpoint ────────────────────────────────────────────────

class CountryInfo(BaseModel):
    """Minimal country info for GlobeMap + public country list."""
    code: str
    name: str
    flag_emoji: str
    region: Optional[str] = None


class CountriesResponse(BaseModel):
    countries: list[CountryInfo]


@router.get("/countries", response_model=CountriesResponse)
async def get_countries(session: AsyncSession = Depends(get_session)):
    """Return every country that is currently enabled for sale.

    Source of truth is `country_plan_types` — the table the admin dashboard
    writes when it enables or disables a (country, plan_type). This used to read
    `plans`, a table the dashboard stopped writing, so it returned
    `{"countries":[]}` in production while `/api/catalog` returned a full
    catalog. Because Hero.tsx treats an empty list as "no data" rather than an
    error, that silently left the homepage globe rendering the hardcoded
    PRODUCT_COUNTRIES table: disabling a country in the dashboard did nothing.

    A country enabled for sale is always returned, even if its `countries`
    reference row is missing — a sellable country must never be invisible just
    because display metadata is absent.
    """
    from app.models import Country

    country_codes = await list_enabled_country_codes(session)

    country_infos: list[CountryInfo] = []
    if country_codes:
        result = await session.execute(
            select(Country).where(Country.code.in_(country_codes))
        )
        by_code = {c.code: c for c in result.scalars().all()}
        for code in country_codes:
            row = by_code.get(code)
            country_infos.append(
                CountryInfo(
                    code=code,
                    name=row.name if row else code,
                    flag_emoji=row.flag_emoji if row else "",
                    region=row.region if row else None,
                )
            )

    return CountriesResponse(countries=country_infos)
