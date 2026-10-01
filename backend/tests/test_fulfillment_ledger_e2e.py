"""End-to-end: run the real ``fulfill_order_job`` and assert on the ledger.

The other ledger tests call ``record_credential_send`` directly. That proves
the writer works, but not that the *worker* calls it — and the wiring is the
part most likely to rot. When the ledger calls were stripped from
``fulfillment_worker.py`` to check these tests would notice, only a source-grep
test failed; every behavioural test still passed. That is the same
"looks tested, proves nothing" trap this sprint keeps hitting.

So this module drives the real ``fulfill_order_job`` against a real database
and asserts on the rows that come out the other end. Only the provider
boundaries are faked:

  * ``create_credential``            → mints a real row in the real table
  * ``trigger_credentials_delivered_webhook`` → returns a caller-chosen value,
                                        which delivery must ignore either way
  * ``send_order_active_email``      → returns a real ``EmailResult``

``send_order_active_email`` is faked rather than allowed to call Resend: these
tests assert what the system recorded, not that a message left the building.
Actual transport proof is QA's job (t_e25e50ce).

n8n is no longer forced to fail to reach the send. Since t_7343d7c0 delivery is
unconditional and the webhook is a best-effort notification, so the helper
returns whatever the test asks for and
``TestN8NResultCannotGateTheLedger`` asserts the ledger row appears either way.
That is the regression guard for the defect this whole sprint is about: a
channel that cannot deliver was suppressing the one that could.
"""
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.models import CredentialNotification, Order  # noqa: E402
from app.services.credential_ledger import (  # noqa: E402
    NO_ADDRESS_TARGET,
    STATUS_FAILED,
    STATUS_NO_ADDRESS,
    STATUS_SENT,
)
from app.services.email import EmailResult  # noqa: E402

from tests.test_credential_ledger import (  # noqa: E402
    LEDGER_TEST_DB,
    _apply_schema,
)

EXPIRES = datetime(2030, 1, 1, tzinfo=timezone.utc)


@pytest_asyncio.fixture
async def db(ledger_engine):
    from sqlalchemy import text

    # Bind to the fixture's *engine*, not to `db` — inside its own fixture body
    # `db` is the FixtureFunctionDefinition object, not a session.
    factory = async_sessionmaker(ledger_engine, expire_on_commit=False)
    async with factory() as session:
        # orders <-> styxproxy_credentials have a circular FK pair:
    #   orders.styxproxy_credential_id -> styxproxy_credentials.id
    #   styxproxy_credentials.order_id -> orders.order_id
        # Neither table can be emptied until both links are broken, so null
        # both sides first. customers is the parent of orders.
        await session.execute(text("DELETE FROM credential_notifications"))
        await session.execute(text("UPDATE orders SET styxproxy_credential_id = NULL"))
        await session.execute(text("UPDATE styxproxy_credentials SET order_id = NULL"))
        await session.execute(text("DELETE FROM styxproxy_credentials"))
        await session.execute(text("DELETE FROM orders"))
        await session.execute(text("DELETE FROM customers"))
        await session.commit()
        yield session


@pytest_asyncio.fixture
async def ledger_engine():
    from sqlalchemy import text

    try:
        eng = create_async_engine(LEDGER_TEST_DB, future=True)
        async with eng.begin() as conn:
            await conn.execute(text("SELECT 1"))
        await _apply_schema(eng)
    except Exception as exc:
        pytest.skip(f"no test database at {LEDGER_TEST_DB}: {exc}")
    yield eng
    await eng.dispose()


async def _seed_order(db, order_id="STX-E2E01", customer_email="buyer@gmail.com"):
    """Seed a real order row (and its customer parent).

    ``orders.customer_phone`` is an FK to ``customers.phone``, so the customer
    must exist first.
    """
    from app.models import Customer

    phone = "+2348000000000"
    # `customers.name` is NOT NULL — there is no `display_name` column.
    db.add(Customer(phone=phone, name="E2E Buyer"))
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


def _fake_credential_factory(db):
    """A create_credential double that mints a REAL row in the REAL table."""

    async def _create(db_session=None, order_id=None, **kwargs):
        from app.models import StyxproxyCredential

        cred = StyxproxyCredential(
            styxproxy_username="sty_e2e0001",
            order_id=order_id,
            status="active",
            pool_type="paid",
            protocol="socks5",
            upstream_proxy_ip="1.2.3.4",
            upstream_proxy_port=1080,
            expires_at=EXPIRES,
        )
        db_session.add(cred)
        await db_session.commit()
        await db_session.refresh(cred)
        return cred, "plaintextpassword123"

    return _create


def _run_worker(
    monkeypatch,
    db,
    order_id,
    payload,
    email_result,
    n8n_ok=False,
    email_double=None,
):
    """Invoke the real fulfill_order_job with the boundaries faked.

    ``email_double`` replaces the default ``send_order_active_email`` stand-in
    entirely, for the case where the send must *raise* rather than return an
    EmailResult. Patching it from outside the helper does not work:
    ``_run_worker`` monkeypatches the same attribute afterwards, so the outer
    patch is silently overwritten and the test passes for the wrong reason.
    """
    import app.scripts.fulfillment_worker as worker

    # The worker opens its own session via AsyncSessionLocal; point it at the
    # test database so the rows land where the assertions look.
    factory = async_sessionmaker(db.bind, expire_on_commit=False)

    class _Ctx:
        async def __aenter__(self):
            self._s = factory()
            return self._s

        async def __aexit__(self, *exc):
            await self._s.close()
            return False

    monkeypatch.setattr(worker, "AsyncSessionLocal", lambda: _Ctx())

    # Force the fallback path: n8n "fails", so email delivery is reached.
    monkeypatch.setattr(
        worker, "trigger_credentials_delivered_webhook", AsyncMock(return_value=n8n_ok)
    )

    # create_credential / resolve_plan / audit are imported *inside* the
    # function body, so they must be patched at their source modules.
    #
    # `import app.routers.orders as orders_mod` does NOT work here: the
    # package's __init__ rebinds the name `orders` to the APIRouter object
    # (`from app.routers.orders import router as orders`), so the attribute
    # resolves to a router, not the module. importlib returns the module.
    import importlib

    import app.services.audit as audit_mod
    import app.services.credential as cred_mod
    import app.services.email as email_mod

    orders_mod = importlib.import_module("app.routers.orders")

    monkeypatch.setattr(cred_mod, "create_credential", _fake_credential_factory(db))
    monkeypatch.setattr(
        orders_mod,
        "resolve_plan",
        AsyncMock(return_value=SimpleNamespace(plan_type="residential")),
    )
    monkeypatch.setattr(audit_mod, "log_audit_event", AsyncMock(return_value=None))
    monkeypatch.setattr(
        email_mod,
        "send_order_active_email",
        email_double or AsyncMock(return_value=email_result),
    )

    return worker.fulfill_order_job("TXF-E2E123", order_id, payload, job_id="e2e")


# ─── AC#2 / AC#5: happy path, end to end ────────────────────────────────────


class TestFulfillmentWorkerEndToEnd:
    async def test_successful_send_lands_in_the_ledger(self, db, monkeypatch):
        """A fulfilled order with a real address produces a `sent` row."""
        from sqlalchemy import text

        await _seed_order(db, "STX-E2E01", "buyer@gmail.com")

        result = await _run_worker(
            monkeypatch,
            db,
            "STX-E2E01",
            {"data": {"customer": {"email": "gateway@other.com"}}},
            EmailResult(success=True, message_id="msg_e2e_1"),
        )
        assert result["status"] == "fulfilled", result

        async with async_sessionmaker(db.bind, expire_on_commit=False)() as check:
            rows = (
                (
                    await check.execute(
                        select(CredentialNotification).where(
                            CredentialNotification.order_id == "STX-E2E01"
                        )
                    )
                )
                .scalars()
                .all()
            )
            assert len(rows) == 1, f"expected one ledger row, got {rows}"
            row = rows[0]
            assert row.status == STATUS_SENT
            # The ORDER ROW address, not the gateway payload's.
            assert row.target == "buyer@gmail.com"
            assert row.notification_type == "email"
            assert row.channel == "email"
            assert row.enabled is True
            assert row.message_id == "msg_e2e_1"
            assert row.error is None

            # Cross-check with raw SQL: the row is really in the table, not
            # just in the ORM identity map.
            raw = (
                await check.execute(
                    text(
                        "SELECT status, target, order_id FROM credential_notifications "
                        "WHERE order_id = 'STX-E2E01'"
                    )
                )
            ).first()
            assert raw == (STATUS_SENT, "buyer@gmail.com", "STX-E2E01")

    async def test_prefers_order_row_over_gateway_payload(self, db, monkeypatch):
        """AC#1: the order row is authoritative; the payload is fallback."""
        await _seed_order(db, "STX-E2E02", "typed@gmail.com")

        await _run_worker(
            monkeypatch,
            db,
            "STX-E2E02",
            {"data": {"customer": {"email": "gateway@other.com"}}},
            EmailResult(success=True, message_id="msg_e2e_2"),
        )

        async with async_sessionmaker(db.bind, expire_on_commit=False)() as check:
            row = (
                (
                    await check.execute(
                        select(CredentialNotification).where(
                            CredentialNotification.order_id == "STX-E2E02"
                        )
                    )
                )
                .scalars()
                .first()
            )
            assert row.target == "typed@gmail.com"


# ─── AC#3: failure path, end to end ─────────────────────────────────────────


class TestFailedSendEndToEnd:
    async def test_provider_rejection_is_queryable_from_the_db(self, db, monkeypatch):
        """A Resend rejection must be visible without reading a log."""
        await _seed_order(db, "STX-E2E03", "buyer@gmail.com")

        await _run_worker(
            monkeypatch,
            db,
            "STX-E2E03",
            {"data": {}},
            EmailResult(
                success=False,
                status="api_error",
                error="422: Unprocessable entity — invalid from address",
            ),
        )

        async with async_sessionmaker(db.bind, expire_on_commit=False)() as check:
            row = (
                (
                    await check.execute(
                        select(CredentialNotification).where(
                            CredentialNotification.order_id == "STX-E2E03"
                        )
                    )
                )
                .scalars()
                .first()
            )
            assert row is not None, "a rejected send must still be recorded"
            assert row.status == STATUS_FAILED
            assert row.target == "buyer@gmail.com"
            assert "422" in row.error
            assert "invalid from address" in row.error

    async def test_raised_exception_is_recorded(self, db, monkeypatch):
        """An exception in the send path is a distinct, recorded failure."""
        await _seed_order(db, "STX-E2E04", "buyer@gmail.com")

        async def _boom(**kwargs):
            raise TimeoutError("SMTP read timed out")

        await _run_worker(
            monkeypatch,
            db,
            "STX-E2E04",
            {"data": {}},
            EmailResult(success=True),
            email_double=_boom,
        )

        async with async_sessionmaker(db.bind, expire_on_commit=False)() as check:
            row = (
                (
                    await check.execute(
                        select(CredentialNotification).where(
                            CredentialNotification.order_id == "STX-E2E04"
                        )
                    )
                )
                .scalars()
                .first()
            )
            assert row is not None, "an exception must be recorded, not swallowed"
            assert row.status == STATUS_FAILED
            assert "timed out" in row.error.lower()


# ─── AC#1 / AC#5: absent address, end to end ────────────────────────────────


class TestAbsentAddressEndToEnd:
    async def test_no_address_records_a_row_rather_than_skipping_silently(
        self, db, monkeypatch, caplog
    ):
        """The silent skip is the defect. It must leave a durable record."""
        import logging

        await _seed_order(db, "STX-E2E05", customer_email=None)

        with caplog.at_level(logging.ERROR):
            await _run_worker(
                monkeypatch,
                db,
                "STX-E2E05",
                # A placeholder address: the gateway shape, unroutable.
                {"data": {"customer": {"email": "guest-anondabc@example.com"}}},
                EmailResult(success=True),
            )

        # A loud log line…
        assert any("NO DELIVERABLE EMAIL" in r.message for r in caplog.records), (
            "the absent-address case must log loudly"
        )

        # …and a queryable row.
        async with async_sessionmaker(db.bind, expire_on_commit=False)() as check:
            row = (
                (
                    await check.execute(
                        select(CredentialNotification).where(
                            CredentialNotification.order_id == "STX-E2E05"
                        )
                    )
                )
                .scalars()
                .first()
            )
            assert row is not None, "no row means the skip is still silent"
            assert row.status == STATUS_NO_ADDRESS
            assert row.target == NO_ADDRESS_TARGET

    async def test_gateway_fallback_used_when_order_row_is_empty(self, db, monkeypatch):
        """AC#1: with no order-row address, a real gateway address is used."""
        await _seed_order(db, "STX-E2E06", customer_email="")

        await _run_worker(
            monkeypatch,
            db,
            "STX-E2E06",
            {"data": {"email": "paystack@buyer.com"}},  # Paystack shape
            EmailResult(success=True, message_id="msg_ps"),
        )

        async with async_sessionmaker(db.bind, expire_on_commit=False)() as check:
            row = (
                (
                    await check.execute(
                        select(CredentialNotification).where(
                            CredentialNotification.order_id == "STX-E2E06"
                        )
                    )
                )
                .scalars()
                .first()
            )
            assert row is not None
            assert row.status == STATUS_SENT
            assert row.target == "paystack@buyer.com"


# ─── the ledger must not be gated on a channel that cannot deliver ────────────


class TestN8NResultCannotGateTheLedger:
    """Regression guard for the n8n-suppression defect (t_7343d7c0).

    The worker used to deliver by email only `if not n8n_success`. The live
    workflow has no send node and Charon answers 402 as HTTP 200, so n8n always
    reported success and the email branch never ran — 238 orders with no
    observable delivery. If anyone re-introduces the gate, the ledger goes
    empty again, and that is precisely what these two tests must catch.
    """

    async def _run_and_read(self, monkeypatch, db, order_id, n8n_ok):
        await _seed_order(db, order_id, "buyer@gmail.com")
        await _run_worker(
            monkeypatch,
            db,
            order_id,
            {"data": {}},
            EmailResult(success=True),
            n8n_ok=n8n_ok,
        )
        async with async_sessionmaker(db.bind, expire_on_commit=False)() as check:
            return (
                (
                    await check.execute(
                        select(CredentialNotification).where(
                            CredentialNotification.order_id == order_id
                        )
                    )
                )
                .scalars()
                .all()
            )

    async def test_ledger_row_is_written_when_n8n_reports_success(self, db, monkeypatch):
        rows = await self._run_and_read(monkeypatch, db, "STX-E2E07", n8n_ok=True)
        assert len(rows) == 1, (
            "n8n reporting success must not suppress the send and its ledger row"
        )
        assert rows[0].status == STATUS_SENT
        assert rows[0].target == "buyer@gmail.com"

    async def test_ledger_row_is_written_when_n8n_reports_failure(self, db, monkeypatch):
        rows = await self._run_and_read(monkeypatch, db, "STX-E2E08", n8n_ok=False)
        assert len(rows) == 1, "the ledger must not depend on n8n's answer"
        assert rows[0].status == STATUS_SENT
