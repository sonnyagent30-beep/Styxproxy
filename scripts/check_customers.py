import asyncio
import os
import sys

os.chdir("/opt/styxproxy/backend")
sys.path.insert(0, "/opt/styxproxy/backend")

from app.database import async_session
from sqlalchemy import text

async def check():
    async with async_session() as session:
        result = await session.execute(text("SELECT phone, email, name FROM customers LIMIT 10"))
        rows = result.fetchall()
        print(f"Total customers found: {len(rows)}")
        for r in rows:
            print(f"  phone={r[0]}, email={r[1]}, name={r[2]}")

        result2 = await session.execute(text("SELECT COUNT(*) FROM customers WHERE email IS NOT NULL AND email != ''"))
        count = result2.scalar()
        print(f"Customers with email: {count}")

asyncio.run(check())
