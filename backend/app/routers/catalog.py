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
from app.services.catalog import create_order_with_credential, list_catalog

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
    """Return all countries that have at least one active plan_type in PlanSettings."""
    from app.models import Country, PlanSettings
    from sqlalchemy import select

    pt_result = await session.execute(
        select(PlanSettings.plan_type, PlanSettings.country).where(PlanSettings.is_active)
    )
    rows = pt_result.fetchall()

    country_codes: set[str] = {code for _, code in rows if code}

    if country_codes:
        country_result = await session.execute(
            select(Country).where(Country.code.in_(country_codes))
        )
        countries_rows = country_result.scalars().all()
    else:
        countries_rows = []

    country_infos = []
    for c in countries_rows:
        country_infos.append(CountryInfo(
            code=c.code, name=c.name, flag_emoji=c.flag_emoji, region=c.region
        ))

    return CountriesResponse(countries=country_infos)
