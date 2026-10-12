"""Prove the capture record works against a REAL Postgres, not just a stub.

tests/test_capture_record.py exercises record_capture() and the predicates
against a plain Python object, which is fast and dependency-free. This file
closes the remaining gap: it runs the actual SQLAlchemy model against a real
PostgreSQL database carrying the real migration, so the round trip is proven —
the columns exist where the migration put them, the ORM can write and read
them, and `capture_query()` returns exactly the rows `was_captured()` accepts.

Skipped (not failed) when no database is reachable: the suite must keep
working in a broken environment, which is when a payment guard is most needed.
Run with:

    CAPTURE_TEST_DATABASE_URL=postgresql+asyncpg://user:pw@host/db python3 -m pytest tests/test_capture_record_postgres.py
"""
from __future__ import annotations

import os
from datetime import datetime, timezone

import pytest
from sqlalchemy import func, select, text

from app.services.capture import (
    GATEWAY_STATUS_REFUNDED,
    GATEWAY_STATUS_SUCCESS,
    UNIT_MAJOR,
    UNIT_MINOR,
    capture_query,
    record_capture,
    was_captured,
)

DB_URL = os.environ.get("CAPTURE_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(
    not DB_URL, reason="set CAPTURE_TEST_DATABASE_URL to run the Postgres round-trip"
)


@pytest.fixture
async def session():
    """A real session against a migrated `orders` table."""
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    engine = create_async_engine(DB_URL)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as conn:
        # Start from a known state; the migration is assumed already applied.
        # CASCADE because other tables hold FKs to orders.
        await conn.exec_driver_sql("TRUNCATE orders CASCADE")
    async with maker() as s:
        yield s
    await engine.dispose()


async def _make(session, order_id: str, status: str = "pending"):
    from app.models import Order

    order = Order(
        order_id=order_id,
        status=status,
        # The invoice amount is populated on every row, like production.
        amount_paid_ngn=5000.0,
        payment_reference=f"TXF-{order_id}",
    )
    session.add(order)
    await session.commit()
    return order


@pytest.mark.asyncio
async def test_orm_round_trips_the_capture_record(session):
    """The migration's columns are writable and readable through the model."""
    from app.models import Order

    order = await _make(session, "ORD-PG0001")
    record_capture(
        order,
        provider="paystack",
        gateway_status=GATEWAY_STATUS_SUCCESS,
        gateway_amount=250000,  # kobo
        amount_unit=UNIT_MINOR,
        gateway_reference="TXF-ORD-PG0001",
        gateway_currency="NGN",
        gateway_transaction_id=302961,
    )
    await session.commit()

    loaded = (await session.execute(
        select(Order).where(Order.order_id == "ORD-PG0001")
    )).scalar_one()

    assert loaded.gateway_status == GATEWAY_STATUS_SUCCESS
    assert float(loaded.gateway_amount_ngn) == 2500.0
    assert loaded.captured_at is not None
    assert loaded.provider == "paystack"
    assert loaded.gateway_currency == "NGN"
    assert loaded.gateway_reference == "TXF-ORD-PG0001"
    assert loaded.provider_order_id == "302961"
    # The invoice amount is untouched by the capture record.
    assert float(loaded.amount_paid_ngn) == 5000.0
    assert was_captured(loaded) is True


@pytest.mark.asyncio
async def test_cancelled_and_refunded_rows_are_excluded_by_the_real_query(session):
    """The card's core requirement, proven against a real database.

    Every row below carries a full invoice amount, and the cancelled/refunded
    ones are given every capture field it is possible to set. Neither may be
    returned as captured money.
    """
    from app.models import Order

    # A genuinely captured, paid order.
    paid = await _make(session, "ORD-PGPAID")
    record_capture(paid, provider="flutterwave", gateway_status=GATEWAY_STATUS_SUCCESS,
                   gateway_amount=5000, amount_unit=UNIT_MAJOR)
    paid.status = "paid"
    await session.commit()

    # A refunded row: capture fields set, but the gateway says refunded.
    refunded = await _make(session, "ORD-PGREF")
    record_capture(refunded, provider="flutterwave", gateway_status=GATEWAY_STATUS_REFUNDED,
                   gateway_amount=5000, amount_unit=UNIT_MAJOR)
    refunded.status = "refunded"
    await session.commit()

    # A cancelled row with capture fields forced on by hand — the shape a bug
    # would produce. capture_query() must still exclude it.
    #
    # Written as raw SQL because record_capture() correctly refuses to produce
    # this row; forcing it is the only way to prove the READ side defends
    # against it. session.expire_all() afterwards is essential: without it the
    # identity map still holds the pre-UPDATE `status` and was_captured() would
    # read stale state — a trap for anyone writing DB-level assertions here.
    await _make(session, "ORD-PGCAN")
    await session.execute(
        text(
            "UPDATE orders SET status='cancelled', provider='flutterwave', "
            "gateway_status='success', gateway_amount_ngn=5000, "
            "captured_at=now() WHERE order_id='ORD-PGCAN'"
        )
    )
    await session.commit()
    session.expire_all()

    rows = (await session.execute(select(Order).where(capture_query()))).scalars().all()
    ids = {r.order_id for r in rows}

    assert ids == {"ORD-PGPAID"}, f"only the genuinely captured order may match, got {ids}"
    assert "ORD-PGREF" not in ids
    assert "ORD-PGCAN" not in ids

    # And the bulk result agrees with the row-by-row check on every row.
    everything = (await session.execute(select(Order))).scalars().all()
    assert {r.order_id for r in everything if was_captured(r)} == ids


@pytest.mark.asyncio
async def test_pending_row_is_not_captured_in_the_database(session):
    """Payment-init writes pending evidence; it must not read as captured."""
    from app.models import Order

    order = await _make(session, "ORD-PGPEND")
    record_capture(order, provider="paystack", gateway_status="pending",
                   gateway_amount=500000, amount_unit=UNIT_MINOR)
    await session.commit()

    loaded = (await session.execute(
        select(Order).where(Order.order_id == "ORD-PGPEND")
    )).scalar_one()
    assert loaded.gateway_status == "pending"
    assert loaded.captured_at is None            # pending must never stamp a time
    assert was_captured(loaded) is False

    rows = (await session.execute(select(Order).where(capture_query()))).scalars().all()
    assert rows == []


@pytest.mark.asyncio
async def test_captured_revenue_sums_only_real_money(session):
    """Revenue must come from gateway amounts over gateway capture times.

    The old shape — sum(amount_paid_ngn) filtered by status — counts invoices
    that were never paid. Here a paid-but-uncaptured row and a cancelled row both
    carry invoice amounts, and neither may appear in the total.
    """
    from sqlalchemy import select

    from app.models import Order
    from app.services.capture import captured_revenue_stmt

    # Genuinely captured: N2,500 via Flutterwave (major unit).
    paid = await _make(session, "ORD-PGREV1")
    record_capture(paid, provider="flutterwave", gateway_status=GATEWAY_STATUS_SUCCESS,
                   gateway_amount=2500, amount_unit=UNIT_MAJOR)
    paid.status = "paid"
    await session.commit()

    # Invoice raised, never paid — must not count.
    pending = await _make(session, "ORD-PGREV2")
    record_capture(pending, provider="paystack", gateway_status="pending",
                   gateway_amount=500000, amount_unit=UNIT_MINOR)
    await session.commit()

    # Cancelled with an invoice amount — must not count.
    cancelled = await _make(session, "ORD-PGREV3", status="cancelled")
    await session.commit()

    total = float((await session.execute(captured_revenue_stmt())).scalar() or 0)
    assert total == 2500.0, f"only the N2,500 capture may count, got {total}"

    # The naive shape the dashboards use today — sum the invoice amount for
    # anything that looks paid-ish — counts all three rows: 5000 + 5000 + 5000.
    # It overstates real revenue by N12,500 while looking entirely plausible.
    # This is the number that must never be called revenue.
    naive = float((await session.execute(
        select(func.coalesce(func.sum(Order.amount_paid_ngn), 0)).where(
            Order.status.in_(["pending", "paid", "cancelled"])
        )
    )).scalar() or 0)
    assert naive == 15000.0
    assert naive != total
    session.expire_all()


@pytest.mark.asyncio
async def test_captured_at_survives_as_timestamptz(session):
    """The column is a real timestamptz — a naive timestamp would lose the zone.

    Revenue-per-period reporting depends on this; a column that silently drops
    the offset makes day boundaries ambiguous.
    """
    from app.models import Order

    order = await _make(session, "ORD-PGTS", status="paid")
    when = datetime(2026, 10, 1, 9, 30, tzinfo=timezone.utc)
    record_capture(order, provider="paystack", gateway_status=GATEWAY_STATUS_SUCCESS,
                   gateway_amount=5000, amount_unit=UNIT_MAJOR, captured_at=when)
    await session.commit()

    tzname = (await session.execute(text(
        "SELECT data_type FROM information_schema.columns "
        "WHERE table_name='orders' AND column_name='captured_at'"
    ))).scalar_one()
    assert tzname == "timestamp with time zone"

    loaded = (await session.execute(
        select(Order).where(Order.order_id == "ORD-PGTS")
    )).scalar_one()
    assert loaded.captured_at == when
    assert loaded.captured_at.tzinfo is not None
