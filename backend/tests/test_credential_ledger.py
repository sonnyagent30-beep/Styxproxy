"""Ledger tests: credential delivery must be observable in the database.

These assert against ``credential_notifications`` — a real Postgres table, via
a real SQLAlchemy session — rather than against a mock or a log line.

Why not ``orders.emails_sent``
------------------------------
``emails_sent`` is written in exactly one place: ``app/services/renewal.py``,
inside ``check_and_send_renewal_reminder``, for renewal reminders.
``send_order_active_email`` never touches it. So ``emails_sent = 0`` means "no
renewal reminder fired", which is expected for most orders — it is not a
credential-delivery signal, and an assertion against it passes or fails for an
unrelated reason. Assert on the ledger instead.

Why a real database
-------------------
The ledger table has a NOT NULL foreign key to ``styxproxy_credentials`` and a
NOT NULL ``target``. A mocked session proves neither: an INSERT that satisfies
a mock can still violate the database. These tests run against the real
constraints, using the schema in ``tests/ledger_schema.sql``, which mirrors the
live production table (captured from 162.35.184.69 on 2026-10-01).

The worker under test is ``app/scripts/fulfillment_worker.py`` — the copy
systemd actually executes via ``ExecStart``. The near-identical
``backend/scripts/`` copy is dead code and is guarded against by
``test_deployed_file_is_the_one_under_test`` in
``test_fulfillment_email_delivery.py``.
"""
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.models import CredentialNotification, Order, StyxproxyCredential  # noqa: E402
from app.services import credential_ledger as ledger_mod  # noqa: E402
from app.services.credential_ledger import (  # noqa: E402
    NO_ADDRESS_TARGET,
    STATUS_FAILED,
    STATUS_NO_ADDRESS,
    STATUS_SENT,
    record_credential_send,
    record_email_result,
)
from app.services.email import EmailResult  # noqa: E402

EXPIRES = datetime(2030, 1, 1, tzinfo=timezone.utc)

# A dedicated database so these tests never touch a developer's real data.
LEDGER_TEST_DB = os.environ.get(
    "LEDGER_TEST_DATABASE_URL",
    "postgresql+asyncpg://styxproxy:styxproxy@127.0.0.1:5432/styxproxy_test",
)

SCHEMA_SQL = BACKEND_DIR / "tests" / "ledger_schema.sql"


async def _apply_schema(async_eng) -> None:
    """Create the ledger + parent tables from the mirrored schema.

    The parent table ``styxproxy_credentials`` is created from the ORM
    metadata rather than hand-written, so it cannot drift from the model (an
    earlier hand-written version was missing a dozen columns and every insert
    failed on the first one). The ledger table itself comes from
    ``ledger_schema.sql``, which mirrors production exactly — that fidelity is
    the point of the test, so it is not generated from the model.

    ``styxproxy_credentials`` and ``orders`` declare foreign keys to a chain of
    other tables, so the whole ORM metadata set is created together via
    ``Base.metadata.create_all`` — creating tables one at a time in dependency
    order is brittle, and a missing referenced relation makes the DDL fail and
    every test skip.
    """
    from sqlalchemy import text

    from app.models import Base

    async with async_eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_eng.begin() as conn:
        for raw in SCHEMA_SQL.read_text().split(";"):
            stmt = raw.strip()
            if not stmt or stmt.startswith("--"):
                continue
            # Strip comment lines so only SQL reaches the server.
            body = "\n".join(
                line for line in stmt.splitlines() if not line.strip().startswith("--")
            ).strip()
            if body:
                await conn.execute(text(body))


@pytest_asyncio.fixture
async def ledger_engine():
    """A real Postgres engine with the ledger schema applied.

    Skips (rather than fails) when no test database is reachable, so a
    developer without Postgres is not blocked — but wherever a database IS
    available, the DB-backed assertions below actually run rather than skip
    silently. CI must assert these ran, not merely that they exist.

    Function-scoped deliberately: pytest-asyncio gives each test a fresh event
    loop, and an asyncpg pool created in one loop cannot be used from the next
    ("another operation is in progress"). A module-scoped engine makes every
    test after the first error out — the same trap `tests/conftest.py`
    documents for the app engine.
    """
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


@pytest_asyncio.fixture
async def db(ledger_engine):
    """A session on the real ledger table, truncated per test."""
    from sqlalchemy import text

    factory = async_sessionmaker(ledger_engine, expire_on_commit=False)
    async with factory() as session:
        # orders <-> styxproxy_credentials have a circular FK pair (see the
        # same fixture in test_fulfillment_ledger_e2e.py), so both links are
        # broken before either table is emptied.
        await session.execute(text("DELETE FROM credential_notifications"))
        await session.execute(text("UPDATE orders SET styxproxy_credential_id = NULL"))
        await session.execute(text("UPDATE styxproxy_credentials SET order_id = NULL"))
        await session.execute(text("DELETE FROM styxproxy_credentials"))
        await session.execute(text("DELETE FROM orders"))
        await session.commit()
        yield session


async def _make_credential(session, username="sty_ledger1", order_id="STX-LEDGER1"):
    """Create a credential row with a real parent order.

    ``styxproxy_credentials.order_id`` is a real FK to ``orders.order_id``, so
    the parent row must exist — which is itself worth proving, since the ledger
    sits two FK hops from the order and an unattributable send is exactly the
    defect class this work closes.
    """
    from sqlalchemy import text

    existing = await session.execute(
        text("SELECT 1 FROM orders WHERE order_id = :oid"), {"oid": order_id}
    )
    if existing.first() is None:
        session.add(
            Order(
                order_id=order_id,
                status="fulfilled",
                plan_code="NG-RES-1IP",
                country="NG",
                quantity=1,
            )
        )
        await session.commit()

    cred = StyxproxyCredential(
        styxproxy_username=username,
        order_id=order_id,
        status="active",
        pool_type="paid",
        protocol="socks5",
        upstream_proxy_ip="1.2.3.4",
        upstream_proxy_port=1080,
    )
    session.add(cred)
    await session.commit()
    await session.refresh(cred)
    return cred


async def _rows_for(session, order_id):
    result = await session.execute(
        select(CredentialNotification).where(CredentialNotification.order_id == order_id)
    )
    return result.scalars().all()


# ─── Happy path (AC#2) ───────────────────────────────────────────────────────


class TestSuccessfulSendIsLedgered:
    async def test_success_writes_row_with_real_address_as_target(self, db):
        """AC#2: a successful send produces a row carrying the real address."""
        cred = await _make_credential(db)

        result = EmailResult(success=True, message_id="msg_abc123", status=None, error=None)
        row_id = await record_email_result(
            db,
            result,
            credential_id=cred.id,
            order_id="STX-LEDGER1",
            target="buyer@gmail.com",
        )

        assert row_id is not None, "ledger write must report a row id"
        rows = await _rows_for(db, "STX-LEDGER1")
        assert len(rows) == 1, f"expected exactly one ledger row, got {rows}"
        row = rows[0]

        assert row.status == STATUS_SENT
        assert row.target == "buyer@gmail.com", "target must be the real address"
        assert row.notification_type == "email"
        assert row.channel == "email"
        assert row.enabled is True
        assert row.message_id == "msg_abc123"
        assert row.error is None
        assert row.credential_id == cred.id

    async def test_row_survives_a_later_rollback_of_the_order(self, db):
        """A send that happened must not be un-recorded by a later failure."""
        cred = await _make_credential(db, username="sty_rollback", order_id="STX-ROLLBACK")

        await record_credential_send(
            db,
            credential_id=cred.id,
            order_id="STX-ROLLBACK",
            target="buyer@gmail.com",
            status=STATUS_SENT,
        )
        # Simulate the worker's generic handler rolling the order back.
        await db.rollback()

        rows = await _rows_for(db, "STX-ROLLBACK")
        assert len(rows) == 1, "a completed send must persist across a rollback"


# ─── Failure path (AC#3) ─────────────────────────────────────────────────────


class TestFailedSendIsLedgered:
    async def test_provider_rejection_records_error_from_the_db(self, db):
        """AC#3: EmailResult.error must be visible without reading logs."""
        cred = await _make_credential(db, username="sty_failed", order_id="STX-FAILED")

        result = EmailResult(
            success=False,
            message_id=None,
            status="api_error",
            error="422: Unprocessable entity — invalid from address",
        )
        await record_email_result(
            db, result, credential_id=cred.id, order_id="STX-FAILED", target="buyer@gmail.com"
        )

        rows = await _rows_for(db, "STX-FAILED")
        assert len(rows) == 1
        row = rows[0]
        assert row.status == STATUS_FAILED
        assert row.target == "buyer@gmail.com"
        # The DoD: the error text is in the database.
        assert "422" in row.error
        assert "invalid from address" in row.error
        assert row.message_id is None

    async def test_missing_api_key_is_recorded_as_failed(self, db):
        """skipped_no_key is a credential loss, not a success."""
        cred = await _make_credential(db, username="sty_nokey", order_id="STX-NOKEY")

        result = EmailResult(success=False, status="skipped_no_key", error="RESEND_API_KEY not configured")
        await record_email_result(
            db, result, credential_id=cred.id, order_id="STX-NOKEY", target="buyer@gmail.com"
        )

        row = (await _rows_for(db, "STX-NOKEY"))[0]
        assert row.status == STATUS_FAILED
        assert "RESEND_API_KEY" in row.error

    async def test_raised_exception_is_recorded(self, db):
        """A raised exception is a different failure and was recorded nowhere."""
        cred = await _make_credential(db, username="sty_exc", order_id="STX-EXC")

        await record_credential_send(
            db,
            credential_id=cred.id,
            order_id="STX-EXC",
            target="buyer@gmail.com",
            status=STATUS_FAILED,
            error="TimeoutError: read timed out",
        )

        row = (await _rows_for(db, "STX-EXC"))[0]
        assert row.status == STATUS_FAILED
        assert "read timed out" in row.error


# ─── Absent-address path (AC#1, AC#5) ───────────────────────────────────────


class TestAbsentAddressIsLedgered:
    async def test_no_address_writes_no_address_row_with_sentinel_target(self, db):
        """AC#1/AC#5: the silent skip becomes a durable, queryable record."""
        cred = await _make_credential(db, username="sty_noaddr", order_id="STX-NOADDR")

        await record_credential_send(
            db,
            credential_id=cred.id,
            order_id="STX-NOADDR",
            target=None,
            status=STATUS_NO_ADDRESS,
            error="no deliverable email: order row customer_email=None",
        )

        rows = await _rows_for(db, "STX-NOADDR")
        assert len(rows) == 1, "the absent-address case must not be a silent skip"
        row = rows[0]
        assert row.status == STATUS_NO_ADDRESS
        # NOT NULL target is satisfied by an explicit sentinel, not a fake address.
        assert row.target == NO_ADDRESS_TARGET
        assert "@" not in row.target, "sentinel must not look like a deliverable address"
        assert "no deliverable email" in row.error

    async def test_placeholder_address_is_not_recorded_as_a_send(self, db):
        """A guest-anond…@example.com target must not count as a delivery."""
        cred = await _make_credential(db, username="sty_placeholder", order_id="STX-PLACEHOLDER")

        # Simulate the worker passing a placeholder through: the ledger must
        # refuse to record it as sent.
        await record_credential_send(
            db,
            credential_id=cred.id,
            order_id="STX-PLACEHOLDER",
            target="guest-anondabc123@example.com",
            status=STATUS_SENT,  # caller wrongly believes it was sent
        )

        row = (await _rows_for(db, "STX-PLACEHOLDER"))[0]
        # The ledger downgrades a placeholder "sent" to no_address.
        assert row.status == STATUS_NO_ADDRESS
        assert row.target == NO_ADDRESS_TARGET

    async def test_empty_target_downgrades_to_no_address(self, db):
        cred = await _make_credential(db, username="sty_empty", order_id="STX-EMPTY")
        await record_credential_send(
            db, credential_id=cred.id, order_id="STX-EMPTY", target="   ", status=STATUS_SENT
        )
        row = (await _rows_for(db, "STX-EMPTY"))[0]
        assert row.status == STATUS_NO_ADDRESS


# ─── Robustness ──────────────────────────────────────────────────────────────


class TestLedgerSchemaReadiness:
    """The worker never runs app.main's lifespan patches, so it self-verifies."""

    async def test_ensure_ledger_columns_is_a_noop_when_already_applied(self, db):
        from app.services.credential_ledger import ensure_ledger_columns

        assert await ensure_ledger_columns(db) is True
        # Idempotent: a second run must not raise.
        assert await ensure_ledger_columns(db) is True

        cred = await _make_credential(db, username="sty_ensure", order_id="STX-ENSURE")
        row_id = await record_credential_send(
            db,
            credential_id=cred.id,
            order_id="STX-ENSURE",
            target="buyer@gmail.com",
            status=STATUS_SENT,
        )
        assert row_id is not None

    async def test_failure_is_reported_not_raised(self, db):
        """A permissions problem must not stop the worker starting."""
        from app.services.credential_ledger import ensure_ledger_columns

        with patch.object(db, "commit", side_effect=RuntimeError("permission denied")):
            assert await ensure_ledger_columns(db) is False


class TestLedgerNeverBreaksFulfillment:
    async def test_missing_credential_id_returns_none_without_raising(self, db):
        """No credential_id would violate the NOT NULL FK — log, don't crash."""
        result = await record_credential_send(
            db, credential_id=0, order_id="STX-NOCRED", target="b@x.com", status=STATUS_SENT
        )
        assert result is None
        assert await _rows_for(db, "STX-NOCRED") == []

    async def test_db_failure_is_swallowed_and_returns_none(self, db):
        """A ledger outage must not fail a fulfilled order."""
        with patch.object(db, "commit", side_effect=RuntimeError("db down")):
            result = await record_credential_send(
                db, credential_id=1, order_id="STX-DBDOWN", target="b@x.com", status=STATUS_SENT
            )
        assert result is None, "must report failure, not raise into the worker"

    async def test_fk_violation_is_caught(self, db):
        """A credential_id that does not exist must not propagate."""
        result = await record_credential_send(
            db, credential_id=999999, order_id="STX-FK", target="b@x.com", status=STATUS_SENT
        )
        assert result is None
        assert await _rows_for(db, "STX-FK") == []

    async def test_long_target_is_truncated_to_fit_varchar_255(self, db):
        cred = await _make_credential(db, username="sty_long", order_id="STX-LONG")
        long_addr = "a" * 300 + "@example.com"
        await record_credential_send(
            db, credential_id=cred.id, order_id="STX-LONG", target=long_addr, status=STATUS_SENT
        )
        row = (await _rows_for(db, "STX-LONG"))[0]
        assert len(row.target) <= 255


# ─── The worker actually calls the ledger (AC#3 wiring) ──────────────────────


class TestWorkerWiresTheLedger:
    """The ledger is only useful if the live worker writes to it."""

    WORKER = BACKEND_DIR / "app" / "scripts" / "fulfillment_worker.py"

    def test_worker_source_contains_ledger_calls(self):
        src = self.WORKER.read_text()
        assert "record_email_result" in src, "worker must record the EmailResult"
        assert "record_credential_send" in src, "worker must record failure/no-address"
        assert "from app.services.credential_ledger import" in src

    def test_worker_verifies_ledger_columns_at_startup(self):
        """The worker is an RQ process — it never runs app.main's lifespan."""
        src = self.WORKER.read_text()
        assert "ensure_ledger_columns" in src
        bootstrap = src.split('if __name__ == "__main__":')[-1]
        assert "ensure_ledger_columns(session)" in bootstrap, (
            "the column check must run before the worker takes its first job"
        )

    def test_no_email_result_is_discarded(self):
        """The original bug: EmailResult returned and never inspected."""
        src = self.WORKER.read_text()
        # A bare `await send_order_active_email(...)` whose result is dropped.
        assert "email_result = await send_order_active_email(" in src
        assert "if email_result.success:" in src

    def test_deployed_file_is_the_one_under_test(self):
        import app.scripts.fulfillment_worker as mod

        parts = Path(mod.__file__).resolve().parts
        assert "app" in parts and "scripts" in parts, (
            f"imported {mod.__file__} — not the app/scripts copy systemd runs"
        )
