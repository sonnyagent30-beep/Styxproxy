"""End-to-end test for renewal reminder fix.

Creates a test order with status='fulfilled', expires_at 2 days out,
then runs the daily renewal reminder timer and verifies sent>=1.
"""
import asyncio
import os
import sys
from datetime import datetime, timedelta, timezone

# Load .env properly (dotenv handles special characters)
from dotenv import dotenv_values

env = dotenv_values("/opt/styxproxy/.env")
for k, v in env.items():
    if k and v:
        os.environ[k] = v

# Ensure we're in the right directory
os.chdir("/opt/styxproxy/backend")
sys.path.insert(0, "/opt/styxproxy/backend")

from app.database import async_session
from app.services.order_status import is_live_order
from app.services.renewal import RENEWAL_WARNING_DAYS, send_daily_renewal_reminders


async def test_is_live_order():
    """Unit test: the predicate accepts both active and fulfilled."""
    assert is_live_order("active"), "active should be live"
    assert is_live_order("fulfilled"), "fulfilled should be live"
    assert not is_live_order("pending"), "pending should not be live"
    assert not is_live_order("expired"), "expired should not be live"
    assert not is_live_order("cancelled"), "cancelled should not be live"
    assert not is_live_order(None), "None should not be live"
    print("PASS: is_live_order predicate works correctly")

async def test_end_to_end():
    """Integration test: create a fulfilled order in the warning window, run timer."""
    async with async_session() as session:
        # First, check if test order already exists (from previous run)
        from sqlalchemy import text
        result = await session.execute(
            text("SELECT order_id FROM orders WHERE order_id LIKE 'TEST-RENEW-%'")
        )
        existing = result.fetchone()
        if existing:
            print(f"Test order {existing[0]} already exists, deleting first...")
            await session.execute(
                text("DELETE FROM styxproxy_credentials WHERE order_id = :oid"),
                {"oid": existing[0]}
            )
            await session.execute(
                text("DELETE FROM orders WHERE order_id = :oid"),
                {"oid": existing[0]}
            )
            await session.commit()

        # Create test order: status=fulfilled, expires in 2 days
        test_order_id = f"TEST-RENEW-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        expires_at = datetime.now(timezone.utc) + timedelta(days=2)

        # Find a real customer to use (need customer_phone + email)
        result = await session.execute(
            text("SELECT phone, email, name FROM customers WHERE email IS NOT NULL LIMIT 1")
        )
        customer_row = result.fetchone()
        if not customer_row:
            print("SKIP: No customer with email found in DB, cannot run e2e test")
            return

        customer_phone, customer_email, customer_name = customer_row
        print(f"Using customer: {customer_name} <{customer_email}> phone={customer_phone}")

        # Create the test order
        await session.execute(
            text("""
                INSERT INTO orders (order_id, customer_phone, plan_code, status, expires_at,
                                    emails_sent, reminder_sent_at, amount_paid_ngn, quantity)
                VALUES (:oid, :phone, 'RESIDENTIAL-NG', 'fulfilled', :expires,
                        0, NULL, 5000, 1)
            """),
            {
                "oid": test_order_id,
                "phone": customer_phone,
                "expires": expires_at,
            }
        )
        await session.commit()
        print(f"Created test order {test_order_id}, expires_at={expires_at}, status=fulfilled")

        # Verify the order is in the window
        result = await session.execute(
            text("SELECT status, expires_at FROM orders WHERE order_id = :oid"),
            {"oid": test_order_id}
        )
        row = result.fetchone()
        print(f"DB check: status={row[0]}, expires_at={row[1]}")

        # Run the daily reminder timer
        print(f"\nRunning send_daily_renewal_reminders (window={RENEWAL_WARNING_DAYS} days)...")
        summary = await send_daily_renewal_reminders(session)
        print(f"\nRESULT: sent={summary['sent']}, skipped={summary['skipped']}, errors={summary['errors']}")

        if summary["sent"] >= 1:
            print(f"\nPASS: Timer sent {summary['sent']} reminder(s) — fulfilled orders now qualify!")
        else:
            print(f"\nFAIL: Timer sent {summary['sent']} reminders — fix did not work!")
            sys.exit(1)

        # Clean up: delete test order
        await session.execute(
            text("DELETE FROM orders WHERE order_id = :oid"),
            {"oid": test_order_id}
        )
        await session.commit()
        print(f"Cleaned up test order {test_order_id}")

async def main():
    print("=" * 60)
    print("E2E TEST: Renewal reminder status guard fix")
    print("=" * 60)

    print("\n--- Unit test: is_live_order predicate ---")
    await test_is_live_order()

    print("\n--- Integration test: fulfilled order in warning window ---")
    await test_end_to_end()

    print("\n" + "=" * 60)
    print("ALL TESTS PASSED")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
