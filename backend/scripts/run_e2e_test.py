"""Create a test customer with email, then run the e2e renewal reminder test."""
import asyncio
import os
import sys
from datetime import datetime, timedelta, timezone

from dotenv import dotenv_values

env = dotenv_values("/opt/styxproxy/.env")
for k, v in env.items():
    if k and v:
        os.environ[k] = v

os.chdir("/opt/styxproxy/backend")
sys.path.insert(0, "/opt/styxproxy/backend")

from sqlalchemy import text

from app.database import async_session
from app.services.renewal import RENEWAL_WARNING_DAYS, send_daily_renewal_reminders


async def setup_and_test():
    async with async_session() as session:
        # Step 1: Create a test customer with an email
        test_email = "renewal-test@styxproxy.local"
        test_phone = "+234-RENEW-TEST"

        # Check if test customer already exists
        result = await session.execute(
            text("SELECT phone FROM customers WHERE phone = :phone OR email = :email"),
            {"phone": test_phone, "email": test_email}
        )
        existing = result.fetchone()
        if existing:
            print(f"Test customer already exists (phone={existing[0]}), reusing...")
            test_phone = existing[0]
        else:
            await session.execute(
                text("""
                    INSERT INTO customers (id, phone, email, name, blocked, free_trials_used_today, referral_code)
                    VALUES (gen_random_uuid(), :phone, :email, 'Renewal Test Customer', false, 0, 'RENEWTEST1')
                """),
                {"phone": test_phone, "email": test_email}
            )
            await session.commit()
            print(f"Created test customer: phone={test_phone}, email={test_email}")

        # Step 2: Create a test order — status=fulfilled, expires in 2 days
        test_order_id = f"TEST-RENEW-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        expires_at = datetime.now(timezone.utc) + timedelta(days=2)

        # Clean up any previous test orders
        await session.execute(
            text("DELETE FROM styxproxy_credentials WHERE order_id LIKE 'TEST-RENEW-%'")
        )
        await session.execute(
            text("DELETE FROM orders WHERE order_id LIKE 'TEST-RENEW-%'")
        )
        await session.commit()

        # Create the test order with status='fulfilled' (what the webhook sets)
        await session.execute(
            text("""
                INSERT INTO orders (order_id, customer_phone, plan_code, status, expires_at,
                                    emails_sent, reminder_sent_at, amount_paid_ngn, quantity,
                                    plan_type, country)
                VALUES (:oid, :phone, 'RESIDENTIAL-NG', 'fulfilled', :expires,
                        0, NULL, 5000, 1, 'residential', 'NG')
            """),
            {"oid": test_order_id, "phone": test_phone, "expires": expires_at}
        )
        await session.commit()
        print(f"Created test order {test_order_id}, status=fulfilled, expires_at={expires_at}")

        # Step 3: Verify the order is in the DB correctly
        result = await session.execute(
            text("SELECT status, expires_at FROM orders WHERE order_id = :oid"),
            {"oid": test_order_id}
        )
        row = result.fetchone()
        print(f"DB check: status={row[0]}, expires_at={row[1]}")

        # Step 4: Run the daily reminder timer
        print(f"\nRunning send_daily_renewal_reminders (window={RENEWAL_WARNING_DAYS} days)...")
        summary = await send_daily_renewal_reminders(session)
        print(f"\nRESULT: sent={summary['sent']}, skipped={summary['skipped']}, errors={summary['errors']}")

        if summary["sent"] >= 1:
            print(f"\nPASS: Timer sent {summary['sent']} reminder(s) — fulfilled orders now qualify!")
        else:
            print(f"\nFAIL: Timer sent {summary['sent']} reminders — fix did not work!")
            sys.exit(1)

        # Step 5: Verify the order's tracking fields were updated
        result = await session.execute(
            text("SELECT emails_sent, reminder_sent_at FROM orders WHERE order_id = :oid"),
            {"oid": test_order_id}
        )
        row = result.fetchone()
        print(f"After: emails_sent={row[0]}, reminder_sent_at={row[1]}")

        # Step 6: Clean up test data
        await session.execute(
            text("DELETE FROM orders WHERE order_id = :oid"),
            {"oid": test_order_id}
        )
        await session.execute(
            text("DELETE FROM customers WHERE phone = :phone"),
            {"phone": test_phone}
        )
        await session.commit()
        print("\nCleaned up test order and customer")


asyncio.run(setup_and_test())
