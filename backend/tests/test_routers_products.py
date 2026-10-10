"""Tests for products router."""
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.mark.asyncio
async def test_list_products_returns_all():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/products")
    assert response.status_code == 200
    data = response.json()
    assert "products" in data
    products = data["products"]
    assert len(products) == 7
    plan_codes = [p["plan_code"] for p in products]
    assert "ISP-NG-1" in plan_codes
    assert "MOBILE-JP-1" in plan_codes


@pytest.mark.asyncio
async def test_products_have_required_fields():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/products")
    products = response.json()["products"]
    for p in products:
        assert "plan_code" in p
        assert "plan_type" in p
        assert "country" in p
        assert "price_ngn" in p
        assert "quantity" in p
        assert "duration_days" in p
        assert "features" in p


@pytest.mark.asyncio
async def test_products_prices_are_correct():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/products")
    products = response.json()["products"]
    prices = {p["plan_code"]: p["price_ngn"] for p in products}
    assert prices["ISP-NG-1"] == 5000
    assert prices["ISP-NG-2"] == 9500
    assert prices["DC-NG-1"] == 8000
    assert prices["MOBILE-DE-1"] == 15000
