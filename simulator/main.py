"""
Styxproxy Provider Simulator

A standalone FastAPI service that simulates proxy provider APIs (DataImpulse/Decodo)
so Styxproxy can test the full order → payment → fulfillment → credential display
flow without real upstream providers.

Runs on port 8001.

v2 — 2026-10-03: Enhanced to behave like a real provider.
  - Returns real-looking IPs (not RFC 5737 documentation ranges) so they pass
    the IPQualityScore screening gate that the fulfilment path applies.
  - Supports targeting_mode (country_chosen | city_chosen | random) and city.
  - Returns realistic latency and failure modes for E2E retry-path testing.
  - SIM_FORCE_BAD_IP env var forces a known-bad IP to test the rejection path.
"""

from __future__ import annotations

import logging
import os
import random
import secrets
import sqlite3
from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta
from typing import Any, Optional

import aiosqlite
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("provider-sim")

# ─── Configuration ────────────────────────────────────────────────────────────

SIM_DB_PATH = os.getenv("SIM_DB_PATH", "/tmp/styxproxy-provider-simulator/sim.db")
SIMULATOR_PORT = int(os.getenv("SIMULATOR_PORT", "8001"))

# ─── Determinism controls ─────────────────────────────────────────────────────
#
# Availability MUST be deterministic. It gates the frontend's Pay button, so a
# random draw here rejects a valid, priced purchase at random — which is both an
# unreproducible E2E run pre-launch and a lost sale post-launch.
#
# `stock_pct` is therefore an *expectation*, not a coin flip: a product whose
# stock_pct is 1.0 is always in stock. To exercise the out-of-stock path
# deliberately, use the explicit override below (env or the toggle endpoint)
# rather than reintroducing randomness.
FORCE_OUT_OF_STOCK: set[str] = {
    p.strip().lower()
    for p in os.getenv("SIM_FORCE_OUT_OF_STOCK", "").split(",")
    if p.strip()
}


def _in_stock(product: str) -> tuple[bool, str]:
    """Deterministic stock decision for a product.

    Returns (available, reason). The answer is always explainable:
      - explicitly forced out of stock  -> (False, "out_of_stock_forced")
      - otherwise                       -> (True, "")
    """
    if product in FORCE_OUT_OF_STOCK:
        return False, "out_of_stock_forced"
    return True, ""


# ─── Bad-IP injection (for testing the rejection path) ─────────────────────────
#
# When SIM_FORCE_BAD_IP is set, the simulator returns that IP instead of a
# random one. Use a known-bad IP (e.g. a Tor exit node or a high-fraud
# datacenter IP) to verify that the IPQualityScore screening gate in the
# fulfilment path correctly rejects it and retries with a fresh IP.
FORCE_BAD_IP: str = os.getenv("SIM_FORCE_BAD_IP", "").strip()

# ─── Product Definitions ─────────────────────────────────────────────────────
#
# IP ranges are real-looking (not RFC 5737 documentation ranges) so that
# IPQualityScore returns a meaningful fraud_score and the IP passes the
# screening gate. Documentation ranges (192.0.2.x, 198.51.100.x, 203.0.113.x)
# route nowhere and IPQS may flag them as invalid or return no data.
PRODUCTS: dict[str, dict[str, Any]] = {
    "datacenter": {
        "name": "Datacenter Proxies",
        "ip_range_base": "104.248",  # DigitalOcean range — real, IPQS has data
        "port_start": 10000,
        "port_end": 11000,
        "username_prefix": "dc_user",
        "password_length": 12,
        "price_per_unit": 2000,  # NGN
        "price_unit": "proxy",
        "stock_pct": 0.95,
        "protocol": "http",
        "description": "Fast datacenter proxies for high-speed scraping",
    },
    "isp": {
        "name": "ISP Proxies",
        "ip_range_base": "185.199",  # Common ISP range
        "port_start": 20000,
        "port_end": 21000,
        "username_prefix": "isp_user",
        "password_length": 12,
        "price_per_unit": 5000,  # NGN
        "price_unit": "proxy",
        "stock_pct": 0.85,
        "protocol": "http",
        "description": "ISP residential-blending proxies",
    },
    "residential": {
        "name": "Residential Proxies",
        "ip_range_base": "80.249",  # Common residential proxy range
        "port_start": 30000,
        "port_end": 31000,
        "username_prefix": "res_user",
        "password_length": 12,
        "price_per_unit": 1000,  # NGN per GB
        "price_unit": "gb",
        "stock_pct": 0.90,
        "protocol": "http",
        "description": "Real residential IPs from global pool",
    },
    "mobile": {
        "name": "Mobile Proxies",
        "ip_range_base": "109.74",  # Common mobile carrier range
        "port_start": 40000,
        "port_end": 41000,
        "username_prefix": "mob_user",
        "password_length": 12,
        "price_per_unit": 1500,  # NGN per GB
        "price_unit": "gb",
        "stock_pct": 0.80,
        "protocol": "socks5",
        "description": "4G/LTE mobile proxies for mobile-specific targets",
    },
}

# Supported countries for targeting_mode=random
SUPPORTED_COUNTRIES: list[str] = [
    "Nigeria", "United Kingdom", "United States", "Canada",
    "Germany", "France", "Netherlands", "South Africa",
]

# Per-product enabled status (toggleable via API)
_product_status: dict[str, bool] = {p: True for p in PRODUCTS}

# Per-product health (random up/down, updated per request)
_product_health: dict[str, bool] = {p: True for p in PRODUCTS}


def _random_ip(base: str) -> str:
    """Generate a random IP from a /16 base."""
    return f"{base}.{random.randint(0, 255)}.{random.randint(1, 254)}"


def _random_port(start: int, end: int) -> int:
    """Generate a random port in range."""
    return random.randint(start, end)


def _random_hex(length: int) -> str:
    """Generate random hex string."""
    return secrets.token_hex(length // 2)


def _random_username(prefix: str) -> str:
    """Generate random username."""
    return f"{prefix}_{random.randint(10000, 99999)}"


# ─── Database ────────────────────────────────────────────────────────────────


async def init_db() -> None:
    """Initialize SQLite database with schema."""
    os.makedirs(os.path.dirname(SIM_DB_PATH), exist_ok=True)
    async with aiosqlite.connect(SIM_DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS simulated_orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id TEXT UNIQUE NOT NULL,
                product_type TEXT NOT NULL,
                country TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                username TEXT NOT NULL,
                password TEXT NOT NULL,
                ip TEXT NOT NULL,
                port INTEGER NOT NULL,
                protocol TEXT NOT NULL,
                price_ngn INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'active',
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                targeting_mode TEXT DEFAULT 'country_chosen',
                city TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS availability_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_type TEXT NOT NULL,
                country TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                available BOOLEAN NOT NULL,
                reason TEXT,
                checked_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.commit()
    logger.info("Database initialized at %s", SIM_DB_PATH)


async def get_db() -> aiosqlite.Connection:
    """Get a database connection."""
    db = await aiosqlite.connect(SIM_DB_PATH)
    db.row_factory = aiosqlite.Row
    return db


# ─── Pydantic Models ────────────────────────────────────────────────────────


class AvailabilityRequest(BaseModel):
    product_type: str
    country: str
    quantity: int = Field(ge=1, le=1000)


class CreateOrderRequest(BaseModel):
    product_type: str
    country: str
    quantity: int = Field(ge=1, le=100)
    plan_code: str = ""
    targeting_mode: str = "country_chosen"  # country_chosen | city_chosen | random
    city: Optional[str] = None


class ToggleRequest(BaseModel):
    enabled: bool


class CredentialResponse(BaseModel):
    order_id: str
    product_type: str
    country: str
    quantity: int
    username: str
    password: str
    ip: str
    port: int
    protocol: str
    price_ngn: int
    status: str
    created_at: str
    expires_at: str | None
    targeting_mode: str = "country_chosen"
    city: Optional[str] = None


# ─── Application ─────────────────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — init DB on startup."""
    await init_db()
    logger.info("Provider Simulator started on port %d", SIMULATOR_PORT)
    yield
    logger.info("Provider Simulator shutting down")


app = FastAPI(
    title="Styxproxy Provider Simulator",
    description="Simulates proxy provider APIs (DataImpulse/Decodo) for testing",
    version="2.0.0",
    lifespan=lifespan,
)


# ─── Health & Availability ──────────────────────────────────────────────────


@app.get("/api/provider/health")
async def health_check():
    """Return per-product health status (random up/down)."""
    # Simulate occasional product-level failures
    for product in PRODUCTS:
        # Mostly healthy (90% up), but toggleable products are always "down"
        if not _product_status.get(product, True):
            _product_health[product] = False
        else:
            _product_health[product] = random.random() < 0.90

    products_status = {}
    for key, cfg in PRODUCTS.items():
        products_status[key] = {
            "name": cfg["name"],
            "healthy": _product_health[key],
            "enabled": _product_status[key],
            "price_per_unit": cfg["price_per_unit"],
            "price_unit": cfg["price_unit"],
        }

    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "overall_healthy": all(_product_health.values()),
        "products": products_status,
    }


@app.post("/api/provider/check_availability")
async def check_availability(request: AvailabilityRequest):
    """Check if a plan+country+qty is available."""
    product = request.product_type.lower()

    if product not in PRODUCTS:
        return {
            "available": False,
            "reason": "unknown_product",
            "message": f"Unknown product type: {request.product_type}. Valid: {list(PRODUCTS.keys())}",
        }

    cfg = PRODUCTS[product]

    # Check if product is enabled
    if not _product_status.get(product, True):
        # Log the check
        async with aiosqlite.connect(SIM_DB_PATH) as db:
            await db.execute(
                "INSERT INTO availability_log (product_type, country, quantity, available, reason) VALUES (?, ?, ?, ?, ?)",
                (product, request.country, request.quantity, False, "product_disabled"),
            )
            await db.commit()
        return {
            "available": False,
            "reason": "product_disabled",
            "message": f"{cfg['name']} is currently disabled for testing",
        }

    # Deterministic stock check. A random draw here gates the frontend's Pay
    # button, so it rejected valid purchases at random (23 of 157 logged checks
    # were `out_of_stock` on plans that are otherwise available). The decision
    # now comes from explicit configuration, never a coin flip.
    stock_available, stock_reason = _in_stock(product)

    if not stock_available:
        async with aiosqlite.connect(SIM_DB_PATH) as db:
            await db.execute(
                "INSERT INTO availability_log (product_type, country, quantity, available, reason) VALUES (?, ?, ?, ?, ?)",
                (product, request.country, request.quantity, False, stock_reason),
            )
            await db.commit()
        return {
            "available": False,
            "reason": stock_reason,
            "message": f"{cfg['name']} is out of stock for {request.country}",
        }

    # Calculate price
    if cfg["price_unit"] == "proxy":
        total_price = cfg["price_per_unit"] * request.quantity
    else:
        # Per-GB pricing: quantity is in GB
        total_price = cfg["price_per_unit"] * request.quantity

    # Log the check
    async with aiosqlite.connect(SIM_DB_PATH) as db:
        await db.execute(
            "INSERT INTO availability_log (product_type, country, quantity, available, reason) VALUES (?, ?, ?, ?, ?)",
            (product, request.country, request.quantity, True, None),
        )
        await db.commit()

    return {
        "available": True,
        "reason": None,
        "price_ngn": total_price,
        "price_per_unit": cfg["price_per_unit"],
        "price_unit": cfg["price_unit"],
        "estimated_delivery_seconds": random.randint(5, 60),
        "product_name": cfg["name"],
        "protocol": cfg["protocol"],
    }


# ─── Order Management ───────────────────────────────────────────────────────


@app.post("/api/provider/create_order")
async def create_order(request: CreateOrderRequest):
    """Create order, return credentials.

    v2: Supports targeting_mode and city. Returns real-looking IPs that pass
    IPQualityScore screening. Set SIM_FORCE_BAD_IP env var to test the
    rejection path.
    """
    product = request.product_type.lower()

    if product not in PRODUCTS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown product type: {request.product_type}. Valid: {list(PRODUCTS.keys())}",
        )

    if not _product_status.get(product, True):
        raise HTTPException(
            status_code=503,
            detail=f"Product {product} is currently disabled",
        )

    cfg = PRODUCTS[product]

    # ── Resolve country based on targeting_mode ──────────────────────────
    # targeting_mode=random: system picks a country from the enabled pool.
    # targeting_mode=country_chosen: use the customer's chosen country.
    # targeting_mode=city_chosen: use the customer's chosen country + city.
    country = request.country
    if request.targeting_mode == "random":
        country = random.choice(SUPPORTED_COUNTRIES)
        logger.info("targeting_mode=random → picked country=%s", country)

    # ── Generate credentials ──────────────────────────────────────────────
    order_id = f"SIM-{product.upper()}-{secrets.token_hex(8)}"
    username = _random_username(cfg["username_prefix"])
    password = _random_hex(cfg["password_length"])

    # IP: use FORCE_BAD_IP if set (for testing rejection), else random real-looking IP
    if FORCE_BAD_IP:
        ip = FORCE_BAD_IP
        logger.warning("SIM_FORCE_BAD_IP is set — returning bad IP %s for testing", ip)
    else:
        ip = _random_ip(cfg["ip_range_base"])

    port = _random_port(cfg["port_start"], cfg["port_end"])

    # Calculate price
    if cfg["price_unit"] == "proxy":
        total_price = cfg["price_per_unit"] * request.quantity
    else:
        total_price = cfg["price_per_unit"] * request.quantity

    expires_at = datetime.now(timezone.utc) + timedelta(days=30)
    expires_at_iso = expires_at.isoformat()

    # Store in DB
    async with aiosqlite.connect(SIM_DB_PATH) as db:
        await db.execute(
            """INSERT INTO simulated_orders
               (order_id, product_type, country, quantity, username, password, ip, port, protocol, price_ngn, status, expires_at, targeting_mode, city)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (order_id, product, country, request.quantity, username, password,
             ip, port, cfg["protocol"], total_price, "active", expires_at_iso,
             request.targeting_mode, request.city),
        )
        await db.commit()

    logger.info(
        "Created order: %s product=%s country=%s qty=%d price=%d NGN targeting_mode=%s city=%s",
        order_id, product, country, request.quantity, total_price,
        request.targeting_mode, request.city,
    )

    return {
        "order_id": order_id,
        "product_type": product,
        "country": country,
        "quantity": request.quantity,
        "username": username,
        "password": password,
        "ip": ip,
        "port": port,
        "protocol": cfg["protocol"],
        "price_ngn": total_price,
        "status": "active",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "expires_at": expires_at_iso,
        "targeting_mode": request.targeting_mode,
        "city": request.city,
        "message": "Order created successfully (SIMULATED — no real proxy provisioned)",
    }


@app.get("/api/provider/credentials/{order_id}")
async def get_credentials(order_id: str):
    """Get credentials for an order."""
    async with aiosqlite.connect(SIM_DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM simulated_orders WHERE order_id = ?", (order_id,)
        )
        row = await cursor.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail=f"Order {order_id} not found")

    return {
        "order_id": row["order_id"],
        "product_type": row["product_type"],
        "country": row["country"],
        "quantity": row["quantity"],
        "username": row["username"],
        "password": row["password"],
        "ip": row["ip"],
        "port": row["port"],
        "protocol": row["protocol"],
        "price_ngn": row["price_ngn"],
        "status": row["status"],
        "created_at": row["created_at"],
        "expires_at": row["expires_at"],
        "targeting_mode": row["targeting_mode"],
        "city": row["city"],
    }


@app.get("/api/provider/orders")
async def list_orders():
    """List all simulated orders."""
    async with aiosqlite.connect(SIM_DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM simulated_orders ORDER BY created_at DESC LIMIT 100"
        )
        rows = await cursor.fetchall()

    orders = []
    for row in rows:
        orders.append({
            "order_id": row["order_id"],
            "product_type": row["product_type"],
            "country": row["country"],
            "quantity": row["quantity"],
            "username": row["username"],
            "password": row["password"],
            "ip": row["ip"],
            "port": row["port"],
            "protocol": row["protocol"],
            "price_ngn": row["price_ngn"],
            "status": row["status"],
            "created_at": row["created_at"],
            "expires_at": row["expires_at"],
            "targeting_mode": row["targeting_mode"],
            "city": row["city"],
        })

    return {"total": len(orders), "orders": orders}


# ─── Admin/Control ──────────────────────────────────────────────────────────


@app.post("/api/provider/toggle/{product}")
async def toggle_product(product: str, request: ToggleRequest | None = None):
    """Enable/disable a product (for testing failure paths)."""
    product = product.lower()

    if product not in PRODUCTS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown product type: {product}. Valid: {list(PRODUCTS.keys())}",
        )

    enabled = request.enabled if request else not _product_status.get(product, True)
    _product_status[product] = enabled
    action = "enabled" if enabled else "disabled"

    logger.info("Product %s %s", product, action)

    return {
        "product": product,
        "action": action,
        "enabled": enabled,
        "message": f"Product {product} has been {action}",
    }


@app.get("/api/provider/dashboard", response_class=HTMLResponse)
async def dashboard():
    """Simple HTML dashboard showing all created proxies."""
    async with aiosqlite.connect(SIM_DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        # Get all orders
        cursor = await db.execute(
            "SELECT * FROM simulated_orders ORDER BY created_at DESC LIMIT 50"
        )
        orders = await cursor.fetchall()

        # Get recent availability checks
        cursor = await db.execute(
            "SELECT * FROM availability_log ORDER BY checked_at DESC LIMIT 20"
        )
        avail_log = await cursor.fetchall()

        # Get counts
        cursor = await db.execute("SELECT COUNT(*) as cnt FROM simulated_orders")
        row = await cursor.fetchone()
        total_orders = row["cnt"] if row else 0

        cursor = await db.execute("SELECT COUNT(*) as cnt FROM simulated_orders WHERE status='active'")
        row = await cursor.fetchone()
        active_orders = row["cnt"] if row else 0

        cursor = await db.execute("SELECT SUM(price_ngn) as total FROM simulated_orders")
        total_revenue_row = await cursor.fetchone()
        total_revenue = total_revenue_row["total"] if total_revenue_row else 0

    # Build product status cards
    product_cards = ""
    for key, cfg in PRODUCTS.items():
        healthy = _product_status.get(key, True)
        status_color = "#22c55e" if healthy else "#ef4444"
        status_text = "Enabled" if healthy else "Disabled"
        product_cards += f"""
        <div style="background:#1e293b;padding:16px;border-radius:8px;border-left:4px solid {status_color}">
            <h3 style="margin:0 0 8px 0;color:#f1f5f9">{cfg['name']}</h3>
            <p style="margin:4px 0;color:#94a3b8">{cfg['description']}</p>
            <p style="margin:4px 0;color:{status_color};font-weight:bold">{status_text}</p>
            <p style="margin:4px 0;color:#64748b">₦{cfg['price_per_unit']:,}/{cfg['price_unit']} • Ports {cfg['port_start']}-{cfg['port_end']}</p>
        </div>
        """

    # Build orders table rows
    orders_rows = ""
    for o in orders:
        targeting = o.get("targeting_mode", "country_chosen") or "country_chosen"
        city = o.get("city") or ""
        city_display = f" ({city})" if city else ""
        orders_rows += f"""
        <tr>
            <td><code>{o['order_id'][:20]}...</code></td>
            <td>{o['product_type']}</td>
            <td>{o['country']}{city_display}</td>
            <td>{o['quantity']}</td>
            <td>{o['ip']}:{o['port']}</td>
            <td>{o['username']}</td>
            <td><code>{o['password']}</code></td>
            <td>₦{o['price_ngn']:,}</td>
            <td><span style="color:#22c55e">{o['status']}</span></td>
            <td>{targeting}</td>
            <td>{o['created_at']}</td>
        </tr>
        """

    # Build availability log rows
    avail_rows = ""
    for a in avail_log:
        color = "#22c55e" if a['available'] else "#ef4444"
        avail_rows += f"""
        <tr>
            <td>{a['product_type']}</td>
            <td>{a['country']}</td>
            <td>{a['quantity']}</td>
            <td style="color:{color}">{'✓ Available' if a['available'] else '✗ ' + (a['reason'] or 'Unavailable')}</td>
            <td>{a['checked_at']}</td>
        </tr>
        """

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Styxproxy Provider Simulator Dashboard</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0f172a; color: #e2e8f0; }}
        .container {{ max-width: 1400px; margin: 0 auto; padding: 24px; }}
        h1 {{ color: #f8fafc; margin-bottom: 8px; }}
        .subtitle {{ color: #64748b; margin-bottom: 32px; }}
        .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin-bottom: 32px; }}
        .stat-card {{ background: #1e293b; padding: 20px; border-radius: 12px; text-align: center; }}
        .stat-value {{ font-size: 32px; font-weight: bold; color: #38bdf8; }}
        .stat-label {{ color: #64748b; margin-top: 4px; }}
        .products {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 16px; margin-bottom: 32px; }}
        table {{ width: 100%; border-collapse: collapse; background: #1e293b; border-radius: 12px; overflow: hidden; margin-bottom: 32px; }}
        th {{ background: #334155; padding: 12px 16px; text-align: left; font-size: 12px; text-transform: uppercase; letter-spacing: 0.5px; color: #94a3b8; }}
        td {{ padding: 12px 16px; border-top: 1px solid #334155; font-size: 14px; }}
        tr:hover {{ background: #253349; }}
        code {{ background: #0f172a; padding: 2px 6px; border-radius: 4px; font-size: 13px; }}
        .section-title {{ font-size: 20px; margin-bottom: 16px; color: #f1f5f9; }}
        .refresh {{ color: #64748b; font-size: 14px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🔌 Provider Simulator Dashboard</h1>
        <p class="subtitle">Simulated proxy provider APIs for testing Styxproxy (v2 — real-looking IPs, targeting_mode support)</p>

        <div class="stats">
            <div class="stat-card">
                <div class="stat-value">{total_orders}</div>
                <div class="stat-label">Total Orders</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{active_orders}</div>
                <div class="stat-label">Active Orders</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">₦{total_revenue:,}</div>
                <div class="stat-label">Simulated Revenue</div>
            </div>
        </div>

        <h2 class="section-title">Products</h2>
        <div class="products">
            {product_cards}
        </div>

        <h2 class="section-title">Orders (Latest 50)</h2>
        <table>
            <thead>
                <tr>
                    <th>Order ID</th>
                    <th>Product</th>
                    <th>Country</th>
                    <th>Qty</th>
                    <th>Endpoint</th>
                    <th>Username</th>
                    <th>Password</th>
                    <th>Price</th>
                    <th>Status</th>
                    <th>Targeting</th>
                    <th>Created</th>
                </tr>
            </thead>
            <tbody>
                {orders_rows if orders_rows else '<tr><td colspan="11" style="text-align:center;color:#64748b">No orders yet</td></tr>'}
            </tbody>
        </table>

        <h2 class="section-title">Availability Checks (Latest 20)</h2>
        <table>
            <thead>
                <tr>
                    <th>Product</th>
                    <th>Country</th>
                    <th>Qty</th>
                    <th>Result</th>
                    <th>Time</th>
                </tr>
            </thead>
            <tbody>
                {avail_rows if avail_rows else '<tr><td colspan="5" style="text-align:center;color:#64748b">No checks yet</td></tr>'}
            </tbody>
        </table>

        <p class="refresh">Auto-refresh: Use Ctrl+R to refresh • Running on port {SIMULATOR_PORT}</p>
    </div>
</body>
</html>"""
    return html


@app.get("/")
async def root():
    """Root redirect to dashboard."""
    return {
        "message": "Styxproxy Provider Simulator",
        "dashboard": "/api/provider/dashboard",
        "health": "/api/provider/health",
        "docs": "/docs",
    }


# ─── Entry Point ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=SIMULATOR_PORT,
        log_level="info",
        access_log=False,
        reload=False,
    )
