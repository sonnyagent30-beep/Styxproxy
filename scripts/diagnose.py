import asyncio
import os
import sys

from dotenv import dotenv_values
env = dotenv_values("/opt/styxproxy/.env")
for k, v in env.items():
    if k and v:
        os.environ[k] = v

os.chdir("/opt/styxproxy/backend")
sys.path.insert(0, "/opt/styxproxy/backend")

from app.database import async_session
from sqlalchemy import text

async def diagnose():
    async with async_session() as session:
        # Check the test customer
        result = await session.execute(
            text("SELECT phone, email FROM customers WHERE phone = '+234-RENEW-TEST'")
        )
        row = result.fetchone()
        if row:
            print(f"Customer: phone={row[0]}, email={row[1]}")
        else:
            print("Customer not found")

        # Check all TEST-RN orders
        result = await session.execute(
            text("SELECT order_id, customer_phone, status, expires_at, emails_sent FROM orders WHERE order_id LIKE 'TEST-RN-%'")
        )
        rows = result.fetchall()
        print(f"\nTEST-RN orders: {len(rows)}")
        for r in rows:
            print(f"  order_id={r[0]}, phone={r[1]}, status={r[2]}, expires={r[3]}, emails_sent={r[4]}")

        # Check what the timer query would find
        from datetime import datetime, timedelta, timezone
        now = datetime.now(timezone.utc)
        warning_cutoff = now + timedelta(days=3)
        result = await session.execute(
            text("""
                SELECT order_id, customer_phone, status, expires_at
                FROM orders
                WHERE status IN ('active', 'fulfilled')
                  AND expires_at IS NOT NULL
                  AND expires_at <= :cutoff
                  AND expires_at >= :now
                ORDER BY expires_at
            """),
            {"cutoff": warning_cutoff, "now": now}
        )
        rows = result.fetchall()
        print(f"\nOrders in warning window (live statuses): {len(rows)}")
        for r in rows:
            print(f"  order_id={r[0]}, phone={r[1]}, status={r[2]}, expires={r[3]}")

asyncio.run(diagnose())
