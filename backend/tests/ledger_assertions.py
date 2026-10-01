"""Shared credential-delivery ledger assertions.

One harness for every QA card that needs to prove a credential was delivered:
`t_484fcfca` (this surface), `t_8271a59b` (delivery-outcome harness) and
`t_e25e50ce` (real external address). Import from here rather than writing a
third set of assertions, so a change to the ledger's shape breaks all of them
together instead of silently passing one of them.

    from tests.ledger_assertions import (
        ledger_rows, assert_one_channel_delivered, assert_no_channel_delivered,
    )

Asserting on ``credential_notifications``, NOT on ``orders.emails_sent``
-----------------------------------------------------------------------
``orders.emails_sent`` is a renewal-reminder counter. It is written in exactly
one place -- ``app/services/renewal.py:119``, inside
``check_and_send_renewal_reminder`` -- and ``send_order_active_email`` never
touches it. So ``emails_sent = 0`` means "no renewal reminder fired", which is
the expected state for any order outside the reminder window. An assertion
against it passes or fails for a reason unrelated to credential delivery.

This was not a theoretical trap: ``emails_sent = 0`` was cited as standing
evidence that delivery was broken for several hours before Operations retracted
it. Worse, it is *bidirectionally* useless -- because the counter is never
incremented by the delivery path, ``emails_sent`` stays 0 even when a
credential demonstrably reached the customer, so it cannot prove delivery
either.

``assert_emails_sent_is_not_the_signal`` pins this behaviourally, so the
distinction cannot silently rot back into the codebase as a comment only.

What these helpers do and do not prove
--------------------------------------
They prove the system **emitted** a credential over one channel and **recorded**
that it did. They do not prove a human received anything: ``EmailResult.success``
means the provider accepted the message, not that it was delivered to an inbox.
Real inbox-arrival proof is ``t_e25e50ce``'s job and needs a real external
address. Do not report a ledger row as end-to-end customer receipt.
"""

from __future__ import annotations

import itertools
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Sequence

import pytest
import pytest_asyncio
from sqlalchemy import select

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.models import CredentialNotification, Order  # noqa: E402
from app.services.credential_ledger import (  # noqa: E402
    CHANNEL_EMAIL,
    NO_ADDRESS_TARGET,
    STATUS_FAILED,
    STATUS_NO_ADDRESS,
    STATUS_SENT,
)

# Monotonic counters for unique customer phone numbers and credential usernames.
# Module-level so every test module importing these helpers shares one sequence
# and cannot collide.
_CUSTOMER_SEQ = itertools.count(1)
_CREDENTIAL_SEQ = itertools.count(1)


# ─── shared database fixtures ───────────────────────────────────────────────
# Defined here, not in a consuming test module, so every QA card that asserts
# on the ledger gets the same real-Postgres fixtures. `test_credential_ledger.py`
# and `test_fulfillment_ledger_e2e.py` define their own equivalent copies; those
# are left alone rather than rewritten, because touching the developer's module
# would put QA's fixture churn into a branch QA does not own. These are the
# canonical ones for new work.


@pytest_asyncio.fixture
async def ledger_engine():
    """A real Postgres engine with the ledger schema applied.

    Real database, not a mock: the ledger table has a NOT NULL foreign key to
    `styxproxy_credentials` and a NOT NULL `target`, and an INSERT that
    satisfies a mock can still violate the database. Skips rather than fails
    when no test database is reachable, so a contributor without Postgres is not
    blocked by these tests.
    """
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    from tests.test_credential_ledger import LEDGER_TEST_DB, _apply_schema

    try:
        eng = create_async_engine(LEDGER_TEST_DB, future=True)
        async with eng.begin() as conn:
            await conn.execute(text("SELECT 1"))
        await _apply_schema(eng)
    except Exception as exc:
        pytest.skip(f"no test database at {LEDGER_TEST_DB}: {exc}")
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def db(ledger_engine):
    """A clean session against the ledger schema.

    Truncates between tests rather than rolling back, because the worker under
    test commits on its own session (`record_credential_send` commits
    immediately so a later order rollback cannot un-record a real delivery).
    A rollback-based fixture would not see those committed rows at all.
    """
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import async_sessionmaker

    factory = async_sessionmaker(ledger_engine, expire_on_commit=False)
    async with factory() as session:
        await session.execute(text("DELETE FROM credential_notifications"))
        # orders <-> styxproxy_credentials have a circular FK pair, so neither
        # can be emptied until both links are broken.
        await session.execute(text("UPDATE orders SET styxproxy_credential_id = NULL"))
        await session.execute(text("UPDATE styxproxy_credentials SET order_id = NULL"))
        await session.execute(text("DELETE FROM styxproxy_credentials"))
        await session.execute(text("DELETE FROM orders"))
        await session.execute(text("DELETE FROM customers"))
        await session.commit()
        yield session


@dataclass(frozen=True)
class LedgerRow:
    """One credential-delivery outcome, read straight out of the DB."""

    id: int
    credential_id: int
    order_id: Optional[str]
    notification_type: str
    channel: str
    target: str
    status: Optional[str]
    error: Optional[str]
    message_id: Optional[str]

    @property
    def is_deliverable_target(self) -> bool:
        """True if `target` is a real address rather than the no-address sentinel."""
        return "@" in self.target and self.target != NO_ADDRESS_TARGET

    @classmethod
    def from_model(cls, row: CredentialNotification) -> "LedgerRow":
        return cls(
            id=row.id,
            credential_id=row.credential_id,
            order_id=row.order_id,
            notification_type=row.notification_type,
            channel=row.channel,
            target=row.target,
            status=row.status,
            error=row.error,
            message_id=row.message_id,
        )


async def ledger_rows(db, order_id: str) -> list[LedgerRow]:
    """Every send record for `order_id`.

    Uses the service's own query builder so callers and tests cannot drift
    apart on what "the ledger for this order" means.
    """
    from app.services.credential_ledger import ledger_query_for_order

    result = await db.execute(ledger_query_for_order(order_id))
    return [LedgerRow.from_model(r) for r in result.scalars().all()]


async def emails_sent_value(db, order_id: str) -> int:
    """Read `orders.emails_sent` so a test can demonstrate it is not the signal."""
    result = await db.execute(select(Order.emails_sent).where(Order.order_id == order_id))
    value = result.scalar_one_or_none()
    return 0 if value is None else int(value)


async def seed_order(db, order_id: str, customer_email: Optional[str] = None) -> None:
    """Seed a real order row and its customer parent.

    Needed because `orders.customer_phone` is an FK to `customers.phone`, and
    `customers.phone` carries a unique constraint -- so any test seeding two
    orders must give each its own customer.

    Unlike the developer's `_seed_order` in `test_fulfillment_ledger_e2e.py`,
    which hardcodes one phone (`+234****0000`) and therefore collides on the
    second order in a single test. Deriving the phone from a module-level
    counter rather than from `order_id` avoids the two failure modes the
    credential factory documents: IDs with no digits, and an ID repeated across
    a test.

    Pass `customer_email=None` to model the unreachable-customer case.
    """
    from app.models import Customer

    phone = f"+2348{next(_CUSTOMER_SEQ):09d}"

    existing = await db.execute(select(Customer).where(Customer.phone == phone))
    if existing.scalar_one_or_none() is None:
        # `customers.name` is NOT NULL -- there is no `display_name` column.
        db.add(Customer(phone=phone, name=f"QA Buyer {order_id}"))
        await db.commit()

    db.add(
        Order(
            order_id=order_id,
            status="paid",
            plan_code="NG-RES-1IP",
            country="NG",
            quantity=1,
            customer_email=customer_email,
            customer_phone=phone,
            amount_paid_ngn=5000,
        )
    )
    await db.commit()


def credential_factory(db):
    """A `create_credential` double that mints a REAL row in the REAL table.

    Mints a real credential rather than a mock because the ledger's
    `credential_id` is a NOT NULL foreign key to this table -- a mocked session
    would not catch an insert that violates it.

    Unlike the developer's `_fake_credential_factory`, which hardcodes the
    username `sty_e2e0001` and so collides on the second credential in a test
    (`styxproxy_username` is unique). This uses a monotonic counter rather than
    deriving the name from `order_id`, because derivation is wrong in two ways:
    order IDs are not required to be unique per seeded credential, and IDs with
    no digits at all (`STX-QAADDR`) all collapse to the same name -- which is the
    exact collision this exists to prevent.

    Note the developer's driver `_run_worker` wires its *own* factory and offers
    no override hook, so tests using that driver still get the hardcoded one.
    These helpers are for new tests that drive the worker directly; migrating
    the developer's module onto them is left to whoever owns that branch, to keep
    QA's changes out of a branch QA does not own.
    """
    from app.models import StyxproxyCredential

    async def _create(db_session=None, order_id=None, **kwargs):
        username = f"sty_qa_{next(_CREDENTIAL_SEQ):06d}"
        cred = StyxproxyCredential(
            styxproxy_username=username,
            order_id=order_id,
            status="active",
            pool_type="paid",
            protocol="socks5",
            upstream_proxy_ip="1.2.3.4",
            upstream_proxy_port=1080,
            expires_at=datetime(2030, 1, 1, tzinfo=timezone.utc),
        )
        db_session.add(cred)
        await db_session.commit()
        await db_session.refresh(cred)
        return cred, "plaintextpassword123"

    return _create


def assert_one_channel_delivered(
    rows: Sequence[LedgerRow],
    *,
    expected_target: Optional[str] = None,
    expected_message_id: Optional[str] = None,
) -> LedgerRow:
    """Exactly one channel emitted the credential, and the ledger names which.

    This is the assertion that matters for a fulfilled order with a deliverable
    email: the credential was emitted over exactly one channel, and
    `credential_notifications` is the record of which.

    Raises AssertionError naming the actual rows if the count is not exactly one,
    or if the single row does not match the expectation -- a wrong count and a
    wrong target are different bugs and the message keeps them apart.
    """
    sent = [r for r in rows if r.status == STATUS_SENT]

    assert len(sent) == 1, (
        f"expected exactly ONE channel to have emitted the credential, "
        f"found {len(sent)} `sent` rows out of {len(rows)} total. "
        f"Zero means the credential went nowhere; more than one means a "
        f"duplicate emission. rows={_fmt(rows)}"
    )

    row = sent[0]
    assert row.notification_type == "email", (
        f"expected notification_type='email', got {row.notification_type!r}"
    )
    assert row.channel == CHANNEL_EMAIL, (
        f"expected channel={CHANNEL_EMAIL!r}, got {row.channel!r}"
    )
    assert row.error is None, f"a `sent` row must not carry an error, got {row.error!r}"
    if expected_target is not None:
        assert row.target == expected_target, (
            f"expected the ledger to name the real address {expected_target!r}, "
            f"got {row.target!r}"
        )
    if expected_message_id is not None:
        assert row.message_id == expected_message_id, (
            f"expected message_id={expected_message_id!r}, got {row.message_id!r}"
        )
    return row


def assert_no_channel_delivered(
    rows: Sequence[LedgerRow],
    *,
    expected_status: str = STATUS_FAILED,
    error_contains: Optional[str] = None,
) -> LedgerRow:
    """No channel emitted the credential, and the ledger says why.

    This is AC#2's negative path: a provider rejection must be provable from the
    database, not from a log line. Asserts there is no `sent` row (the actual
    risk -- a rejection recorded as a delivery) and that a row exists carrying
    the failure, with ``EmailResult.error`` preserved.
    """
    assert not [r for r in rows if r.status == STATUS_SENT], (
        f"no channel was supposed to deliver, but a `sent` row exists -- a "
        f"rejection or missing address was recorded as a delivery. "
        f"rows={_fmt(rows)}"
    )
    assert len(rows) == 1, (
        f"expected exactly one ledger row recording the failure, found "
        f"{len(rows)}. A failed send must leave a record, not a gap. "
        f"rows={_fmt(rows)}"
    )

    row = rows[0]
    assert row.status == expected_status, (
        f"expected status={expected_status!r}, got {row.status!r}. rows={_fmt(rows)}"
    )
    assert row.error, (
        f"a {expected_status!r} row must carry a non-empty error explaining why "
        f"nothing was delivered; got {row.error!r}. An empty error makes the "
        f"failure unqueryable."
    )
    if error_contains is not None:
        assert error_contains.lower() in row.error.lower(), (
            f"expected the recorded error to mention {error_contains!r}, "
            f"got {row.error!r}"
        )
    return row


def assert_no_address_recorded(rows: Sequence[LedgerRow]) -> LedgerRow:
    """An order with no resolvable address is recorded loudly, not skipped.

    AC#3. Two distinct properties, kept as separate assertions because they fail
    for different reasons: the row must exist (no silent skip), and its target
    must be the sentinel rather than a fabricated address (a fabricated one
    would be counted as a delivery by any ``target LIKE '%@%'`` query).
    """
    assert len(rows) == 1, (
        f"an order with no deliverable address must still leave exactly one "
        f"ledger row -- a silent skip leaves none, which is the original bug. "
        f"Found {len(rows)}. rows={_fmt(rows)}"
    )

    row = rows[0]
    assert row.status == STATUS_NO_ADDRESS, (
        f"expected status={STATUS_NO_ADDRESS!r}, got {row.status!r}. rows={_fmt(rows)}"
    )
    assert row.target == NO_ADDRESS_TARGET, (
        f"expected the explicit sentinel target {NO_ADDRESS_TARGET!r}, got "
        f"{row.target!r}. `target` is NOT NULL, so a fabricated address would "
        f"read as a real delivery."
    )
    assert not row.is_deliverable_target, (
        f"the no-address sentinel must not look like a deliverable address "
        f"(a `LIKE '%@%'` query would count it as a send): {row.target!r}"
    )
    assert row.error, (
        "a no_address row must explain what could not be resolved, including "
        f"the order-row value that was present or absent; got {row.error!r}"
    )
    return row


async def assert_emails_sent_is_not_the_signal(
    db, order_id: str, *, expected_emails_sent: int = 0
) -> int:
    """Pin, behaviourally, that `orders.emails_sent` did not move.

    Called after a delivery that demonstrably emitted a credential. Proves the
    renewal counter is untouched by the credential path, so nobody can cite it
    as evidence again. This is the assertion that keeps the trap closed: the
    source-grep in `test_credential_ledger` says where the counter is written,
    and this says what it therefore does and does not mean.
    """
    value = await emails_sent_value(db, order_id)
    assert value == expected_emails_sent, (
        f"expected orders.emails_sent to stay {expected_emails_sent} after a "
        f"credential send, got {value}. If the credential path has started "
        f"incrementing this counter, it is being conflated with the "
        f"renewal-reminder counter -- assert on credential_notifications instead."
    )
    return value


def _fmt(rows: Sequence[LedgerRow]) -> str:
    if not rows:
        return "[]"
    return (
        "["
        + ", ".join(
            f"id={r.id} status={r.status!r} channel={r.channel!r} "
            f"type={r.notification_type!r} target={r.target!r} error={r.error!r}"
            for r in rows
        )
        + "]"
    )


__all__ = [
    "CHANNEL_EMAIL",
    "LedgerRow",
    "NO_ADDRESS_TARGET",
    "STATUS_FAILED",
    "STATUS_NO_ADDRESS",
    "STATUS_SENT",
    "assert_emails_sent_is_not_the_signal",
    "assert_no_address_recorded",
    "assert_no_channel_delivered",
    "assert_one_channel_delivered",
    "credential_factory",
    "emails_sent_value",
    "ledger_rows",
    "seed_order",
]