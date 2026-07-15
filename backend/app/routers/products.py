"""Products router - uses Plans table for pricing."""
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_session
from app.models import Plan
from app.schemas import ProductsResponse, ProductResponse


router = APIRouter(prefix="/api/products", tags=["products"])


@router.get("", response_model=ProductsResponse)
async def list_products(
    plan_type: Optional[str] = Query(None),
    country: Optional[str] = Query(None),
    session: AsyncSession = Depends(get_session),
):
    """List all available products (active plans only)."""
    conditions = [Plan.is_active == True]
    if plan_type:
        conditions.append(Plan.plan_type == plan_type.upper())
    if country:
        conditions.append(Plan.country == country.upper())
    
    stmt = select(Plan).where(*conditions).order_by(Plan.sort_order, Plan.plan_code)
    plans = (await session.execute(stmt)).scalars().all()
    
    products = [
        ProductResponse(
            plan_code=p.plan_code,
            plan_type=p.plan_type,
            country=p.country,
            price_ngn=float(p.price_ngn),
            quantity=p.quantity,
            duration_days=p.duration_days,
            features=p.features.get("features", []) if p.features else [],
        )
        for p in plans
    ]
    return ProductsResponse(products=products)
