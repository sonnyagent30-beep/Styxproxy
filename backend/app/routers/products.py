"""Products router."""
from typing import List
from fastapi import APIRouter, status
from app.schemas import ProductsResponse, ProductResponse


router = APIRouter(prefix="/api/products", tags=["products"])

PRODUCTS = [
    {"plan_code": "ISP-NG-1", "plan_type": "ISP", "country": "NG", "price_ngn": 5000, "quantity": 1, "duration_days": 30, "features": ["High speed", "Nigeria IPs", "Unlimited bandwidth"]},
    {"plan_code": "ISP-NG-2", "plan_type": "ISP", "country": "NG", "price_ngn": 9500, "quantity": 2, "duration_days": 30, "features": ["High speed", "Nigeria IPs", "Unlimited bandwidth"]},
    {"plan_code": "DC-NG-1", "plan_type": "DC", "country": "NG", "price_ngn": 8000, "quantity": 1, "duration_days": 30, "features": ["Dedicated IP", "Nigeria IPs", "Static IP"]},
    {"plan_code": "RESIDENTIAL-UK-1", "plan_type": "RESIDENTIAL", "country": "UK", "price_ngn": 12000, "quantity": 1, "duration_days": 30, "features": ["Residential IPs", "UK IPs", "High anonymity"]},
    {"plan_code": "RESIDENTIAL-US-1", "plan_type": "RESIDENTIAL", "country": "US", "price_ngn": 10000, "quantity": 1, "duration_days": 30, "features": ["Residential IPs", "US IPs", "High anonymity"]},
    {"plan_code": "MOBILE-DE-1", "plan_type": "MOBILE", "country": "DE", "price_ngn": 15000, "quantity": 1, "duration_days": 30, "features": ["Mobile IPs", "Germany IPs", "4G/5G"]},
    {"plan_code": "MOBILE-JP-1", "plan_type": "MOBILE", "country": "JP", "price_ngn": 18000, "quantity": 1, "duration_days": 30, "features": ["Mobile IPs", "Japan IPs", "4G/5G"]},
]

@router.get("", response_model=ProductsResponse)
async def list_products():
    """List all available products."""
    return ProductsResponse(products=[ProductResponse(**p) for p in PRODUCTS])
