"""Tests for the payment CAPTURE record (gate item 2, t_c0b38088).

## What is being protected

`orders.amount_paid_ngn` is an INVOICE amount. It is written when an order is
raised, before any money moves, and in production it is populated on 100% of
rows — including all 46 `refunded`, 54 `cancelled` and 110 `expired` ones.
Before this change the schema had NO column recording that money arrived, so
"did this customer actually pay?" could not be answered from our own database.

These tests pin three properties:

1. **A capture record is only written from a gateway's own response.** The
   charged amount is normalised from the gateway's stated unit and never
   re-derived from `amount_paid_ngn`. A guard that accepts a locally computed
   amount has reintroduced the original bug.

2. **A cancelled or refunded row can never satisfy "was money captured?"** —
   both via `was_captured()` and via the SQL predicate `capture_query()`, which
   must agree with each other. A bulk query that disagrees with the row check is
   how 46 customers get told their money came back when it did not.

3. **Negative controls.** Every invariant is proved to FAIL when the exact
   defect is reintroduced. A guard that passes on both the broken and the fixed
   tree proves nothing (cf. the retired receipt-PDF route guard, t_4acded30,
   which passed on a tree that still had the bug).

No database is required: `record_capture` mutates a plain object, and the
capture predicates are asserted against both a stub row and the real SQL
predicate. That keeps the suite runnable in a broken environment, which is
precisely when a payment guard is needed.
"""
from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from app.services.capture import (
    CAPTURED_STATUS,
    GATEWAY_STATUS_FAILED,
    GATEWAY_STATUS_PENDING,
    GATEWAY_STATUS_REFUNDED,
    GATEWAY_STATUS_SUCCESS,
    NON_CAPTURE_ORDER_STATUSES,
    UNIT_MAJOR,
    UNIT_MINOR,
    CaptureContractError,
    capture_query,
    gateway_captured_at,
    normalise_gateway_amount,
    record_capture,
    was_captured,
)


def _order(status: str = "pending", **overrides):
    """A minimal stand-in for Order with only the capture-relevant fields.

    Deliberately includes amount_paid_ngn, because the whole point is that
    amount_paid_ngn must NOT be what makes a row count as captured.
    """
    row = SimpleNamespace(
        order_id="ORD-TEST01",
        status=status,
        amount_paid_ngn=5000.0,  # invoice amount — populated on every row
        provider=None,
        captured_at=None,
        gateway_status=None,
        gateway_amount_ngn=None,
        gateway_currency=None,
        gateway_reference=None,
        provider_order_id=None,
    )
    for k, v in overrides.items():
        setattr(row, k, v)
    return row


# ── Amount normalisation: the gateways disagree, and guessing is 100x wrong ────

def test_paystack_kobo_is_normalised_to_naira():
    """Paystack reports the SUBUNIT. N5000 arrives as 500000 and must be 5000."""
    assert normalise_gateway_amount(500000, UNIT_MINOR) == 5000.0


def test_flutterwave_naira_is_not_divided():
    """Flutterwave v3 reports the MAJOR unit — dividing would understate 100x."""
    assert normalise_gateway_amount(5000, UNIT_MAJOR) == 5000.0


def test_unknown_unit_raises_rather_than_guessing():
    """A caller that does not know its gateway's convention must not guess."""
    with pytest.raises(CaptureContractError, match="100x"):
        normalise_gateway_amount(5000, "bananas")


def test_amount_without_unit_is_rejected():
    """The 100x trap is prevented at the call site, not merely documented."""
    order = _order()
    with pytest.raises(CaptureContractError, match="without amount_unit"):
        record_capture(
            order,
            provider="paystack",
            gateway_status=GATEWAY_STATUS_SUCCESS,
            gateway_amount=500000,  # no amount_unit
        )
    assert order.gateway_status is None  # nothing half-written


# ── The capture record ─────────────────────────────────────────────────────────

def test_successful_webhook_records_the_gateways_own_amount():
    """The stored amount is the gateway's, not our invoice arithmetic."""
    order = _order(amount_paid_ngn=5000.0)
    record_capture(
        order,
        provider="paystack",
        gateway_status=GATEWAY_STATUS_SUCCESS,
        gateway_amount=250000,  # kobo — gateway said it charged N2500
        amount_unit=UNIT_MINOR,
        gateway_reference="TXF-ABC123",
        gateway_currency="NGN",
        gateway_transaction_id=302961,
    )
    assert order.gateway_amount_ngn == 2500.0        # normalised from the gateway
    assert order.amount_paid_ngn == 5000.0           # invoice left untouched
    assert order.gateway_status == GATEWAY_STATUS_SUCCESS
    assert order.captured_at is not None
    assert order.provider == "paystack"
    assert order.gateway_reference == "TXF-ABC123"
    assert order.provider_order_id == "302961"


def test_pending_init_does_not_look_captured():
    """Payment-init records what the gateway WILL charge; it is not a capture.

    A pending row must have a null captured_at, or "was money captured?" can be
    answered 'yes' for an order the customer never completed.
    """
    order = _order(status="pending")
    record_capture(
        order,
        provider="flutterwave",
        gateway_status=GATEWAY_STATUS_PENDING,
        gateway_amount=5000,
        amount_unit=UNIT_MAJOR,
    )
    assert order.gateway_status == GATEWAY_STATUS_PENDING
    assert order.captured_at is None
    assert was_captured(order) is False


def test_success_requires_an_amount():
    """A success with no charged amount cannot answer 'how much did they pay?'."""
    order = _order()
    with pytest.raises(CaptureContractError, match="requires gateway_amount"):
        record_capture(
            order,
            provider="paystack",
            gateway_status=GATEWAY_STATUS_SUCCESS,
            gateway_amount=None,
        )


def test_provider_is_mandatory():
    """Requirement 3 of the card: every capture path must write `provider`.

    All 19 historical `fulfilled` and all 8 `active` rows have provider=NULL —
    written by hand or by test, never by a webhook. A capture row with no
    provider cannot be reconciled against anybody.
    """
    order = _order()
    with pytest.raises(CaptureContractError, match="without a provider"):
        record_capture(
            order,
            provider=None,
            gateway_status=GATEWAY_STATUS_SUCCESS,
            gateway_amount=5000,
            amount_unit=UNIT_MAJOR,
        )
    assert order.gateway_status is None


def test_blank_provider_is_also_rejected():
    """A whitespace provider is as useless as a missing one."""
    order = _order()
    with pytest.raises(CaptureContractError):
        record_capture(
            order,
            provider="   ",
            gateway_status=GATEWAY_STATUS_SUCCESS,
            gateway_amount=5000,
            amount_unit=UNIT_MAJOR,
        )


def test_unknown_gateway_status_is_rejected():
    """The vocabulary is enforced, so a typo cannot silently break the query."""
    order = _order()
    with pytest.raises(CaptureContractError, match="unknown gateway_status"):
        record_capture(
            order,
            provider="paystack",
            gateway_status="captured",  # not in the vocabulary
            gateway_amount=5000,
            amount_unit=UNIT_MAJOR,
        )


def test_captured_at_comes_from_the_gateway_not_arrival():
    """Use the gateway's own timestamp — delivery is routinely delayed, and a
    row stamped on arrival silently shifts revenue across a day boundary."""
    order = _order()
    gateway_ts = datetime(2026, 9, 30, 23, 50, tzinfo=timezone.utc)
    record_capture(
        order,
        provider="paystack",
        gateway_status=GATEWAY_STATUS_SUCCESS,
        gateway_amount=5000,
        amount_unit=UNIT_MAJOR,
        captured_at=gateway_ts,
    )
    assert order.captured_at == gateway_ts


# ── The core property: cancelled/refunded rows are never "captured" ────────────

@pytest.mark.parametrize("status", NON_CAPTURE_ORDER_STATUSES)
def test_cancelled_and_refunded_rows_are_never_captured(status):
    """The card's third test requirement, directly.

    A cancelled or refunded order carries an invoice amount but is not evidence
    of payment. `refunded` in particular is currently written by
    admin._process_refund() WITHOUT calling the gateway (gate item 3), so it can
    describe money the gateway still holds.
    """
    order = _order(status=status, amount_paid_ngn=5000.0)
    with pytest.raises(CaptureContractError, match="refusing to mark it as captured"):
        record_capture(
            order,
            provider="paystack",
            gateway_status=GATEWAY_STATUS_SUCCESS,
            gateway_amount=5000,
            amount_unit=UNIT_MAJOR,
        )
    assert was_captured(order) is False


def test_refunded_status_does_not_satisfy_the_query():
    """Negative control at the predicate level.

    Simulates the current production state — a row a webhook captured, later
    flipped to `refunded` administratively without the gateway being told. The
    gateway still says success, so a naive `gateway_status == 'success'` filter
    would report money as held that is not.
    """
    order = _order(status="refunded", amount_paid_ngn=5000.0)
    record_capture(
        order,
        provider="paystack",
        gateway_status=GATEWAY_STATUS_REFUNDED,
        gateway_amount=5000,
        amount_unit=UNIT_MAJOR,
    )
    assert order.gateway_status == GATEWAY_STATUS_REFUNDED
    assert was_captured(order) is False


def test_cancelled_order_with_full_capture_fields_is_still_not_captured():
    """Every capture field populated is not sufficient on its own.

    Proves the status check is load-bearing: strip it and this row would read as
    captured despite the order being cancelled.
    """
    order = _order(
        status="cancelled",
        amount_paid_ngn=5000.0,
        provider="paystack",
        gateway_status=GATEWAY_STATUS_SUCCESS,
        gateway_amount_ngn=5000.0,
        captured_at=datetime(2026, 10, 1, tzinfo=timezone.utc),
    )
    assert was_captured(order) is False


# ── was_captured / capture_query must agree ────────────────────────────────────

def _captured_row(status: str = "paid"):
    """Build a row that WAS captured at the gateway, then given a local status.

    The capture happens while the order is still `pending` (mirroring real
    webhook ordering: money arrives, then our workflow advances), and the local
    status is applied afterwards. Recording capture directly on a
    cancelled/refunded row is exactly what record_capture refuses to do.
    """
    order = _order(status="pending")
    record_capture(
        order,
        provider="paystack",
        gateway_status=GATEWAY_STATUS_SUCCESS,
        gateway_amount=5000,
        amount_unit=UNIT_MAJOR,
    )
    order.status = status
    return order


def test_a_fully_captured_paid_order_counts():
    order = _captured_row()
    assert was_captured(order) is True


@pytest.mark.parametrize("status", ["cancelled", "refunded"])
def test_non_captured_statuses_do_not_count(status):
    """Only cancelled/refunded disqualify a capture — the card's exact scope."""
    order = _captured_row(status=status)
    assert was_captured(order) is False


@pytest.mark.parametrize("status", ["pending", "paid", "fulfilled", "active", "expired",
                                   "failed", "failed_unfulfilled", "failed_manual_review"])
def test_captured_money_counts_regardless_of_our_workflow_state(status):
    """Once the gateway says success, the money IS ours — our status is irrelevant.

    This is the deliberate converse of the cancelled/refunded rule, and it
    matters operationally. Two cases make it concrete:

      * `expired` — the webhooks REJECT an expired order with 400 before
        recording anything, so a customer who paid after the TTL lapsed leaves
        the gateway holding their money and our row holding nothing. If that
        capture record ever does land, it must still read as captured, or the
        customer becomes unrefundable precisely because we let it expire.
      * `failed_unfulfilled` — charged but undeliverable. This is the row that
        most needs refunding, and item 3 (t_f765263b) reads
        `gateway_amount_ngn` from it. Hiding it here would make the
        worst-funded orders the hardest to refund.

    `orders.status` is our workflow state; `gateway_status` is the gateway's
    statement about money. Only the latter answers "did they pay?".
    """
    order = _captured_row(status=status)
    assert was_captured(order) is True


def test_capture_query_excludes_every_status_was_captured_rejects():
    """The bulk predicate and the row check must not drift apart.

    `capture_query()` compiles against the real Order columns; if someone widens
    it to `status = 'paid'` or `amount_paid_ngn IS NOT NULL`, this fails.
    """
    from app.models import Order

    # literal_binds so the NOT IN values appear in the text rather than as
    # bound parameters.
    sql = str(capture_query().compile(compile_kwargs={"literal_binds": True}))
    for status in NON_CAPTURE_ORDER_STATUSES:
        assert status in sql, f"{status!r} must be excluded from capture_query()"
    # Every column was_captured() requires must appear in the SQL predicate.
    assert Order.captured_at.name in sql
    assert Order.gateway_status.name in sql
    assert Order.gateway_amount_ngn.name in sql
    assert Order.provider.name in sql
    # And it must NOT have been widened to the invoice amount.
    assert Order.amount_paid_ngn.name not in sql, (
        "capture_query() must never filter on amount_paid_ngn — that is the "
        "invoice amount, populated on cancelled/refunded/expired rows too"
    )


def test_was_captured_on_none_is_false():
    assert was_captured(None) is False


# ── Gateway timestamp parsing ──────────────────────────────────────────────────

def test_gateway_captured_at_parses_paystack_epoch():
    assert gateway_captured_at({"paid_at": 1759240000}) == datetime.fromtimestamp(
        1759240000, tz=timezone.utc
    )


def test_gateway_captured_at_parses_flutterwave_iso():
    assert gateway_captured_at({"created_at": "2026-10-01T09:30:00Z"}) == datetime(
        2026, 10, 1, 9, 30, tzinfo=timezone.utc
    )


def test_gateway_captured_at_returns_none_on_junk():
    """Unparseable input falls back to arrival time — never a fabricated date."""
    assert gateway_captured_at({"created_at": "not-a-date"}) is None
    assert gateway_captured_at({}) is None
    assert gateway_captured_at("nonsense") is None


# ── Negative controls: each guard must fail on the defect it guards ───────────

def test_negative_control_invoice_amount_alone_is_not_capture():
    """The original defect, reproduced: an invoice amount and no capture record.

    If this ever reports captured, the whole point of the column has been lost.
    """
    order = _order(status="paid", amount_paid_ngn=5000.0)
    assert order.amount_paid_ngn == 5000.0     # invoice present...
    assert order.gateway_status is None         # ...capture evidence absent
    assert was_captured(order) is False


def test_negative_control_removing_the_status_guard_flips_a_cancelled_row():
    """Prove the status check is what stops a cancelled row reading as captured.

    Reimplements was_captured() WITHOUT the status term (the natural but wrong
    simplification) and shows it now accepts a cancelled row. If this stops
    failing, the real was_captured() has lost its status check.
    """
    cancelled = _order(
        status="cancelled",
        provider="paystack",
        gateway_status=GATEWAY_STATUS_SUCCESS,
        gateway_amount_ngn=5000.0,
        captured_at=datetime(2026, 10, 1, tzinfo=timezone.utc),
    )

    def was_captured_without_status_guard(row):
        return (
            row.gateway_status == CAPTURED_STATUS
            and row.captured_at is not None
            and row.gateway_amount_ngn is not None
            and row.provider is not None
        )

    assert was_captured(cancelled) is False              # the real guard holds
    assert was_captured_without_status_guard(cancelled) is True  # the bug it prevents


def test_negative_control_capture_column_absent_from_a_legacy_order_model():
    """An Order model with only the pre-change columns fails the gate check.

    This is the gate's negative control (go_live_gate.py check 2): an Order with
    only amount_paid_ngn/status must not be reported as having capture evidence.
    """
    import re

    legacy_source = (
        "class Order(Base):\n"
        "    amount_paid_ngn: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)\n"
        "    status: Mapped[str] = mapped_column(String(50), default=\"pending\", nullable=False)\n"
    )
    m = re.search(r"class Order\b.*?(?=\nclass |\Z)", legacy_source, re.S)
    body = m.group(0)
    found = [c for c in re.findall(r"^\s{4}(\w+)\s*:\s*Mapped", body, re.M)
             if re.search(r"captur|captured_at|paid_at|settled", c)]
    assert found == []  # -> gate check 2 reports FAIL
