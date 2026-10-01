"""Regression tests for the daily renewal-reminder cron job (t_499e2432).

Two defects, both of which made the cron job a no-op while reporting success:

1. `app/scripts/send_renewal_reminders.py` imported `get_session_context` from
   `app.database`, which only defines `get_session` (an async-generator
   dependency) and the `async_session` factory. The script therefore died at
   ImportError and never ran at all.

2. `app/services/renewal.py` resolved the recipient with
   `getattr(customer, "email", None)`. The `Customer` model has NO email
   column -- the address lives on `Order.customer_email`. So even after fixing
   the import, every reminder resolved to no address, logged "customer has no
   email", and returned False. The job would have run daily and sent nothing.

Defect 2 is the reason this file tests behaviour rather than importability: a
green `import app.scripts.send_renewal_reminders` is exactly the check that
passed while the job was silently useless.

The email send is stubbed; the query, the customer lookup and the tracking
columns all run for real against the test database.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from sqlalchemy import delete, select

from app.database import async_session
from app.models import Customer, Order
from app.services.email import EmailResult

# NOT example.com/org/net -- those are in PLACEHOLDER_EMAIL_DOMAINS and the
# production guard correctly refuses to deliver to them.
TEST_EMAIL = "renewal-cron-test@styxproxy.invalid"
TEST_PHONE = "+2348009900001"

ORDER_IN_WINDOW = "TEST-RENEW-IN"
ORDER_OUT_OF_WINDOW = "TEST-RENEW-OUT"
ORDER_NO_EMAIL = "TEST-RENEW-NOEMAIL"


@pytest_asyncio.fixture
async def renewal_run(monkeypatch):
    """Seed orders, run the real cron script's main(), and capture the sends."""
    sent: list[dict] = []

    async def _fake_send(**kwargs):
        sent.append(kwargs)
        return EmailResult(success=True, message_id=f"stub-{len(sent)}")

    # Patch where it is used, not where it is defined.
    monkeypatch.setattr(
        "app.services.renewal.send_renewal_reminder_email", _fake_send
    )

    now = datetime.now(timezone.utc)
    async with async_session() as s:
        await s.execute(
            delete(Order).where(
                Order.order_id.in_(
                    [ORDER_IN_WINDOW, ORDER_OUT_OF_WINDOW, ORDER_NO_EMAIL]
                )
            )
        )
        await s.execute(delete(Customer).where(Customer.phone == TEST_PHONE))

        s.add(Customer(phone=TEST_PHONE, name="Renewal Cron Test"))

        # Expires in 2 days -> inside the 3-day warning window.
        s.add(
            Order(
                order_id=ORDER_IN_WINDOW,
                customer_phone=TEST_PHONE,
                plan_code="DC-NG-5GB",
                country="NG",
                status="active",
                customer_email=TEST_EMAIL,
                expires_at=now + timedelta(days=2),
            )
        )
        # Expires in 30 days -> outside the window. A query that matched
        # everything would also pass the positive case, so this is the control.
        s.add(
            Order(
                order_id=ORDER_OUT_OF_WINDOW,
                customer_phone=TEST_PHONE,
                plan_code="DC-NG-5GB",
                country="NG",
                status="active",
                customer_email=TEST_EMAIL,
                expires_at=now + timedelta(days=30),
            )
        )
        # In-window but with no deliverable address -> must be skipped, not
        # counted as a send.
        s.add(
            Order(
                order_id=ORDER_NO_EMAIL,
                customer_phone=TEST_PHONE,
                plan_code="DC-NG-5GB",
                country="NG",
                status="active",
                customer_email=None,
                expires_at=now + timedelta(days=2),
            )
        )
        await s.commit()

    from app.scripts.send_renewal_reminders import main as script_main

    yield sent, script_main

    async with async_session() as s:
        await s.execute(
            delete(Order).where(
                Order.order_id.in_(
                    [ORDER_IN_WINDOW, ORDER_OUT_OF_WINDOW, ORDER_NO_EMAIL]
                )
            )
        )
        await s.execute(delete(Customer).where(Customer.phone == TEST_PHONE))
        await s.commit()


async def _fetch(*order_ids: str) -> dict[str, Order]:
    async with async_session() as s:
        rows = (
            (
                await s.execute(
                    select(Order).where(Order.order_id.in_(list(order_ids)))
                )
            )
            .scalars()
            .all()
        )
        return {o.order_id: o for o in rows}


@pytest.mark.asyncio
async def test_script_module_imports(renewal_run):
    """Defect 1: the module must import at all.

    It was unreachable from app.main, which is why a green `import app.main`
    never caught this.
    """
    import app.scripts.send_renewal_reminders as mod

    assert hasattr(mod, "main")


@pytest.mark.asyncio
async def test_cron_sends_reminder_for_expiring_order(renewal_run):
    """Defect 2: an in-window order with an address must actually be sent to.

    The address lives on Order.customer_email, NOT on Customer -- the model has
    no email column, which is why this silently returned None before.
    """
    sent, script_main = renewal_run

    await script_main()

    assert len(sent) == 1, f"expected exactly one send, got {len(sent)}"
    assert sent[0]["order_id"] == ORDER_IN_WINDOW
    assert sent[0]["customer_email"] == TEST_EMAIL

    rows = await _fetch(ORDER_IN_WINDOW)
    assert rows[ORDER_IN_WINDOW].emails_sent == 1
    assert rows[ORDER_IN_WINDOW].reminder_sent_at is not None


@pytest.mark.asyncio
async def test_cron_ignores_order_outside_window(renewal_run):
    """Negative control: the 3-day window filter must actually filter."""
    sent, script_main = renewal_run

    await script_main()

    assert all(s["order_id"] != ORDER_OUT_OF_WINDOW for s in sent)
    rows = await _fetch(ORDER_OUT_OF_WINDOW)
    assert rows[ORDER_OUT_OF_WINDOW].emails_sent == 0
    assert rows[ORDER_OUT_OF_WINDOW].reminder_sent_at is None


@pytest.mark.asyncio
async def test_cron_skips_order_without_deliverable_email(renewal_run):
    """No address -> no send, and no crash."""
    sent, script_main = renewal_run

    await script_main()

    assert all(s["order_id"] != ORDER_NO_EMAIL for s in sent)
    rows = await _fetch(ORDER_NO_EMAIL)
    assert rows[ORDER_NO_EMAIL].emails_sent == 0


@pytest.mark.asyncio
async def test_cron_is_idempotent_within_a_day(renewal_run):
    """A cron that runs daily must not re-send on every run."""
    sent, script_main = renewal_run

    await script_main()
    await script_main()

    assert len(sent) == 1, f"re-sent within the same day: {len(sent)} sends"