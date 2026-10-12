#!/usr/bin/env python3
"""Test the data usage refresh flow end-to-end."""
import asyncio
import sys
from datetime import datetime, timezone
sys.path.insert(0, "/opt/styxproxy/backend")

from sqlalchemy import text
from app.database import async_session as AsyncSessionLocal

async def main():
    async with AsyncSessionLocal() as db:
        # Insert test order
        await db.execute(text("""
            INSERT INTO orders (order_id, customer_phone, plan_type, plan_code, country, quantity, amount_paid_ngn, status, data_total_gb, data_remaining_gb, expires_at)
            VALUES (:order_id, :phone, :plan_type, :plan_code, :country, :quantity, :amount, :status, :data_total, :data_remaining, :expires)
            ON CONFLICT (order_id) DO UPDATE SET data_remaining_gb = EXCLUDED.data_remaining_gb
        """), {
            "order_id": "TEST-DATA-REFRESH",
            "phone": "+2340000000000",
            "plan_type": "residential",
            "plan_code": "RESIDENTIAL-NG",
            "country": "NG",
            "quantity": 10,
            "amount": 10000,
            "status": "active",
            "data_total": 10.0,
            "data_remaining": 10.0,
            "expires": datetime(2026, 11, 1, tzinfo=timezone.utc)
        })

        # Insert credential
        await db.execute(text("""
            INSERT INTO styxproxy_credentials (styxproxy_username, customer_phone, order_id, pool_type, protocol, provider_name, provider_order_id, upstream_proxy_ip, upstream_proxy_port, status, expires_at)
            VALUES (:username, :phone, :order_id, :pool_type, :protocol, :provider_name, :provider_order_id, :ip, :port, :status, :expires)
            ON CONFLICT (styxproxy_username) DO UPDATE SET provider_order_id = EXCLUDED.provider_order_id
        """), {
            "username": "test_data_refresh_user",
            "phone": "+2340000000000",
            "order_id": "TEST-DATA-REFRESH",
            "pool_type": "residential",
            "protocol": "socks5",
            "provider_name": "simulator",
            "provider_order_id": "SIM-RESIDENTIAL-ceffeb1e7820fd01",
            "ip": "80.249.119.66",
            "port": 30847,
            "status": "active",
            "expires": datetime(2026, 11, 1, tzinfo=timezone.utc)
        })

        # Link credential to order
        result = await db.execute(text("SELECT id FROM styxproxy_credentials WHERE styxproxy_username = :username"), {"username": "test_data_refresh_user"})
        cred_id = result.scalar()
        await db.execute(text("UPDATE orders SET styxproxy_credential_id = :cred_id WHERE order_id = :order_id"), {"cred_id": cred_id, "order_id": "TEST-DATA-REFRESH"})

        await db.commit()
        print(f"Test order inserted with credential {cred_id}")

        # Check initial value
        result = await db.execute(text("SELECT order_id, data_remaining_gb, data_total_gb FROM orders WHERE order_id = :order_id"), {"order_id": "TEST-DATA-REFRESH"})
        row = result.fetchone()
        print(f"Before refresh: data_remaining_gb={row[1]}, data_total_gb={row[2]}")

asyncio.run(main())
