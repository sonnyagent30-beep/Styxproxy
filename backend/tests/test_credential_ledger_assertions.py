"""QA assertions: a fulfilled order leaves exactly one channel-delivery record.

Reuses the developer's e2e driver (``tests/test_fulfillment_ledger_e2e.py``) so
there is one harness over this path rather than three, and asserts through the
shared helpers in ``tests/ledger_assertions.py`` so `t_8271a59b` and
`t_e25e50ce` can adopt the same assertion logic.

Scope of this module
--------------------
The three cases the card names -- success, failure, absent-address -- plus the
behavioural proof that ``orders.emails_sent`` is not a delivery signal. The
underlying writer is already covered by ``test_credential_ledger.py``; what is
new here is asserting *through the worker*, because the wiring is the part that
rots: when the ledger calls were stripped from ``fulfillment_worker.py`` to
check, every behavioural test elsewhere still passed and only a source-grep
failed.

These assert the system emitted a credential and recorded it. They do NOT assert
a human received anything -- ``EmailResult.success`` means the provider accepted
the message. Inbox arrival is `t_e25e50ce`'s job and needs a real external
address.
"""
import pytest

from app.services.credential_ledger import STATUS_FAILED, STATUS_NO_ADDRESS, STATUS_SENT
from app.services.email import EmailResult

# The developer's driver, reused rather than rewritten.
from tests.test_fulfillment_ledger_e2e import _run_worker
from tests.ledger_assertions import (
    assert_emails_sent_is_not_the_signal,
    assert_no_address_recorded,
    assert_no_channel_delivered,
    assert_one_channel_delivered,
    credential_factory,
    emails_sent_value,
    ledger_rows,
    seed_order,
)

# Re-exported so pytest collects them: it only auto-discovers fixtures declared
# in conftest.py or the test module itself, never through an import.
from tests.ledger_assertions import db, ledger_engine  # noqa: F401

pytestmark = pytest.mark.asyncio

BUYER = "buyer@gmail.com"
ORDER = "STX-QA0001"


def _run_worker_unique(monkeypatch, db, order_id, payload, email_result=None, **kw):
    """`_run_worker`, but minting a username-unique credential.

    `_run_worker` patches `create_credential` with its own factory, which
    hardcodes username `sty_e2e0001`. `styxproxy_username` is unique, so the
    second order in a test raises UniqueViolation and the failure surfaces as a
    PendingRollbackError on the *next* commit -- an error that says nothing about
    the assertion it appears under.

    Re-patching after `_run_worker` is deliberate: `_run_worker` patches
    `cred_mod.create_credential` (the source module) itself, so overriding it
    afterwards wins. Patching before would be silently overwritten, and the test
    would pass or fail for the wrong reason.

    `email_result` defaults to None here so callers may pass it positionally
    (as `_run_worker` allows) *or* via keyword; forwarding both would raise
    "got multiple values for argument".
    """
    import app.services.credential as cred_mod

    coro = _run_worker(monkeypatch, db, order_id, payload, email_result, **kw)
    monkeypatch.setattr(cred_mod, "create_credential", credential_factory(db))
    return coro


async def _seed_and_run(db, monkeypatch, *, order_id, email, result, payload=None):
    """Seed one order, run the real fulfill_order_job, return the ledger rows."""
    await seed_order(db, order_id, email)
    payload = payload if payload is not None else {"email": email, "amount": 5000}
    await _run_worker_unique(monkeypatch, db, order_id, payload, result, n8n_ok=True)
    return await ledger_rows(db, order_id)


# ─── AC#1: success — exactly one channel emitted it, and the ledger says which ───


class TestSuccessfulDelivery:
    async def test_exactly_one_channel_delivered_and_the_ledger_names_it(
        self, db, monkeypatch
    ):
        """The assertion that matters: one channel emitted, ledger records which.

        Asserts *exactly* one `sent` row rather than "at least one", because the
        double-emission case (email plus a second path both sending) is the
        failure a "> 0" assertion waves through.
        """
        rows = await _seed_and_run(
            db,
            monkeypatch,
            order_id=ORDER,
            email=BUYER,
            result=EmailResult(
                success=True, status="sent", message_id="msg_qa_001", error=None
            ),
        )

        row = assert_one_channel_delivered(
            rows, expected_target=BUYER, expected_message_id="msg_qa_001"
        )
        # The ledger is what a human or a query reads later, so the order id has
        # to be on the row: `credential_id` alone is not enough, since
        # styxproxy_credentials.order_id is nullable and a multi-quantity order
        # mints several credentials.
        assert row.order_id == ORDER

    async def test_delivery_does_not_move_the_renewal_counter(self, db, monkeypatch):
        """`orders.emails_sent` stays 0 even when a credential was delivered.

        The behavioural form of the trap. `emails_sent` is a renewal-reminder
        counter written only at `app/services/renewal.py:119`; the credential
        path never touches it. So it reads 0 here -- on an order that demonstrably
        DID deliver -- which is exactly why it cannot be cited as delivery
        evidence either way.
        """
        await _seed_and_run(
            db,
            monkeypatch,
            order_id=ORDER,
            email=BUYER,
            result=EmailResult(
                success=True, status="sent", message_id="msg_qa_002", error=None
            ),
        )

        rows = await ledger_rows(db, ORDER)
        assert_one_channel_delivered(rows, expected_target=BUYER)
        await assert_emails_sent_is_not_the_signal(db, ORDER, expected_emails_sent=0)

    async def test_channel_field_distinguishes_the_emitting_channel(self, db, monkeypatch):
        """The ledger says *which* channel, not merely that something was sent."""
        rows = await _seed_and_run(
            db,
            monkeypatch,
            order_id=ORDER,
            email=BUYER,
            result=EmailResult(success=True, status="sent", message_id="msg_qa_003"),
        )
        row = assert_one_channel_delivered(rows, expected_target=BUYER)
        assert row.channel == "email", (
            f"expected the ledger to record channel='email', got {row.channel!r}. "
            f"The n8n webhook is also a delivery channel, so the row has to "
            f"identify which one actually emitted the credential."
        )


# ─── AC#2: failure — recorded with EmailResult.error, provable from the DB ───


class TestFailedDelivery:
    async def test_provider_rejection_is_queryable_and_carries_the_error(
        self, db, monkeypatch
    ):
        """A rejection is a row in the DB carrying EmailResult.error verbatim."""
        rows = await _seed_and_run(
            db,
            monkeypatch,
            order_id=ORDER,
            email=BUYER,
            result=EmailResult(
                success=False,
                status="rejected",
                message_id=None,
                error="Resend API returned 422: domain is not verified",
            ),
        )

        row = assert_no_channel_delivered(
            rows,
            expected_status=STATUS_FAILED,
            error_contains="domain is not verified",
        )
        assert row.is_deliverable_target, (
            "a rejection against a real address must keep that address on the "
            f"row, so the failure is attributable; got {row.target!r}"
        )
        assert row.order_id == ORDER

    async def test_rejection_is_not_recorded_as_a_delivery(self, db, monkeypatch):
        """The dangerous direction: a rejection must never read as a send.

        The old code logged "fallback email sent" whenever the call returned
        without raising, so a Resend rejection was indistinguishable from a
        delivery. This asserts the ledger cannot express that confusion.
        """
        rows = await _seed_and_run(
            db,
            monkeypatch,
            order_id=ORDER,
            email=BUYER,
            result=EmailResult(
                success=False, status="rejected", error="provider refused"
            ),
        )

        assert not [r for r in rows if r.status == STATUS_SENT], (
            f"a rejected send produced a `sent` row: {[r.id for r in rows]}"
        )
        assert [r.status for r in rows] == [STATUS_FAILED]

    async def test_raised_exception_is_recorded_as_failed(self, db, monkeypatch):
        """A raising send is recorded too -- otherwise the attempt vanishes."""
        from unittest.mock import AsyncMock

        email_double = AsyncMock(side_effect=RuntimeError("smtp connection reset"))
        await seed_order(db, ORDER, BUYER)
        await _run_worker_unique(
            monkeypatch,
            db,
            ORDER,
            {"email": BUYER, "amount": 5000},
            None,
            n8n_ok=True,
            email_double=email_double,
        )

        rows = await ledger_rows(db, ORDER)
        row = assert_no_channel_delivered(rows, expected_status=STATUS_FAILED)
        assert "smtp connection reset" in row.error, (
            f"the exception text must be preserved verbatim, got {row.error!r}"
        )

    async def test_failure_does_not_move_the_renewal_counter(self, db, monkeypatch):
        """`emails_sent` is 0 on failure too -- it carries no failure signal.

        Recorded here because it is the second half of the trap: the counter
        cannot distinguish a delivered credential from a rejected one, so it can
        support no conclusion about either.
        """
        await _seed_and_run(
            db,
            monkeypatch,
            order_id=ORDER,
            email=BUYER,
            result=EmailResult(success=False, status="rejected", error="nope"),
        )
        await assert_emails_sent_is_not_the_signal(db, ORDER, expected_emails_sent=0)


# ─── AC#3: absent address — loud, recorded, never a silent skip ───


class TestAbsentAddress:
    async def test_no_address_records_a_row_with_the_sentinel_target(
        self, db, monkeypatch
    ):
        """No resolvable address still leaves exactly one ledger row."""
        await seed_order(db, ORDER, None)
        await _run_worker_unique(
            monkeypatch,
            db,
            ORDER,
            {"amount": 5000},  # gateway payload carries no address either
            None,
            n8n_ok=True,
        )

        rows = await ledger_rows(db, ORDER)
        row = assert_no_address_recorded(rows)
        assert row.status == STATUS_NO_ADDRESS
        assert row.order_id == ORDER

    async def test_absent_address_is_not_silently_skipped(self, db, monkeypatch):
        """The row must exist at all -- zero rows is the original bug.

        Stated separately from the sentinel check because "no row" and "row with
        a fabricated address" are different defects, and a helper that only
        checked the sentinel would pass vacuously on an empty result.
        """
        await seed_order(db, ORDER, None)
        await _run_worker_unique(
            monkeypatch, db, ORDER, {"amount": 5000}, None, n8n_ok=True
        )

        rows = await ledger_rows(db, ORDER)
        assert len(rows) == 1, (
            f"a fulfilled order with no deliverable email must leave a ledger "
            f"row; found {len(rows)}. A silent skip is the exact failure this "
            f"card exists to prevent."
        )

    async def test_absent_address_does_not_move_the_renewal_counter(
        self, db, monkeypatch
    ):
        """Third state, identical counter value -- the trap, closed for good."""
        await seed_order(db, ORDER, None)
        await _run_worker_unique(
            monkeypatch, db, ORDER, {"amount": 5000}, None, n8n_ok=True
        )
        await assert_emails_sent_is_not_the_signal(db, ORDER, expected_emails_sent=0)


# ─── the counter is identical across all three outcomes ───


class TestEmailsSentCannotDistinguishOutcomes:
    async def test_all_three_outcomes_leave_the_same_counter_value(
        self, db, monkeypatch
    ):
        """delivered, rejected and unreachable all read `emails_sent = 0`.

        This is the sharpest statement of why the counter is useless as
        evidence: it is not merely insensitive to delivery, it cannot tell three
        materially different outcomes apart. One order per outcome, all asserted
        against the ledger.
        """
        outcomes = []

        cases = [
            ("STX-QASENT", BUYER, EmailResult(success=True, status="sent", message_id="m1")),
            ("STX-QAFAIL", BUYER, EmailResult(success=False, status="rejected", error="x")),
            ("STX-QAADDR", None, None),
        ]

        for order_id, email, result in cases:
            await seed_order(db, order_id, email)
            await _run_worker_unique(
                monkeypatch,
                db,
                order_id,
                {"email": email, "amount": 5000} if email else {"amount": 5000},
                result,
                n8n_ok=True,
            )
            outcomes.append(
                (
                    order_id,
                    await emails_sent_value(db, order_id),
                    [r.status for r in await ledger_rows(db, order_id)],
                )
            )

        # The ledger distinguishes all three.
        statuses = {order_id: st for order_id, _, st in outcomes}
        assert statuses["STX-QASENT"] == [STATUS_SENT]
        assert statuses["STX-QAFAIL"] == [STATUS_FAILED]
        assert statuses["STX-QAADDR"] == [STATUS_NO_ADDRESS]

        # The counter does not distinguish any of them.
        assert [v for _, v, _ in outcomes] == [0, 0, 0], (
            f"expected emails_sent=0 for all three outcomes, got {outcomes}. "
            f"A counter that reads the same for delivered, rejected and "
            f"unreachable carries no information about delivery -- which is why "
            f"these tests assert on credential_notifications instead."
        )

    async def test_ledger_statuses_are_mutually_exclusive(self, db, monkeypatch):
        """Each outcome produces exactly one status, and they never overlap."""
        seen = set()
        for order_id, email, result in [
            ("STX-QAX1", BUYER, EmailResult(success=True, status="sent", message_id="m")),
            ("STX-QAX2", BUYER, EmailResult(success=False, status="rejected", error="e")),
            ("STX-QAX3", None, None),
        ]:
            await seed_order(db, order_id, email)
            await _run_worker_unique(
                monkeypatch,
                db,
                order_id,
                {"email": email, "amount": 5000} if email else {"amount": 5000},
                result,
                n8n_ok=True,
            )
            rows = await ledger_rows(db, order_id)
            assert len(rows) == 1, f"{order_id}: expected one row, got {len(rows)}"
            seen.add(rows[0].status)

        assert seen == {STATUS_SENT, STATUS_FAILED, STATUS_NO_ADDRESS}, (
            f"expected the three outcomes to produce three distinct statuses, "
            f"got {seen}"
        )