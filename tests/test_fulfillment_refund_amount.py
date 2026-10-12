"""The auto-refund amount on the fulfillment worker's provider-exhausted path.

`fulfillment_worker.py` read the refund amount as `data_payload.get("amount", 0)`
— a TOP-LEVEL key. No gateway puts the amount there: Flutterwave sends it at
`data.amount` and Paystack at `data.amount` (in kobo). The read therefore always
yielded 0, so the auto-refund was issued for NGN 0 and the order was then marked
`refunded`.

That is the worst possible shape for a money path: the customer had paid and
received nothing, the platform recorded that a refund had been issued, and no
money moved. Nothing in the order row or the audit log contradicted it.

This module tests the extraction as a pure function so the defect is pinned
without standing up the worker, its Redis connection and its RQ loop.

NOTE on `amount_paid_ngn`: it records the INVOICE amount and is populated on
every row including cancelled/expired/refunded ones. It is the right source for
"what were we billed" — but it is NOT evidence that money was captured, and no
test here should be read as claiming otherwise. There is no capture-status
column.
"""
import re
from pathlib import Path

import pytest

WORKER = Path(__file__).resolve().parents[1] / "app" / "scripts" / "fulfillment_worker.py"


def strip_comments(source: str) -> str:
    """Drop `#` comments so prose quoting the old code cannot fail an assertion.

    The fix's comment block deliberately quotes `data_payload.get("amount", 0)`
    to explain why it was removed. Matching raw text would then flag the
    explanation as the defect, so assertions run against code only.
    """
    out = []
    for line in source.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("#"):
            continue
        # Drop a trailing comment only when it is not inside a string.
        if "#" in line:
            before, _, after = line.partition("#")
            if before.count('"') % 2 == 0 and before.count("'") % 2 == 0:
                line = before
        out.append(line)
    return "\n".join(out)


@pytest.fixture(scope="module")
def source() -> str:
    return WORKER.read_text()


@pytest.fixture(scope="module")
def code() -> str:
    return strip_comments(WORKER.read_text())


def test_refund_amount_is_not_read_from_a_top_level_payload_key(code):
    """The original defect, asserted as the absence of the mistake.

    Asserting on the absence of the exact anti-pattern is the only way to pin
    this without executing the worker: the read looked reasonable and returned
    a plausible 0.
    """
    assert not re.search(r'data_payload\.get\(\s*"amount"', code), (
        "refund amount read from a top-level payload key again — no gateway "
        "sends the amount there, so this silently yields 0"
    )


def test_refund_amount_comes_from_the_order_row(code):
    """The order row is authoritative for what we billed."""
    assert re.search(r"amount\s*=\s*float\(\s*order\.amount_paid_ngn", code), (
        "refund amount must be sourced from order.amount_paid_ngn"
    )


def test_a_zero_amount_never_marks_an_order_refunded(code):
    """A NGN 0 refund must not be recorded as a refund.

    This is the harmful half. Fixing the amount source alone would still let a
    row with no recorded amount produce "refunded" with nothing issued, so the
    guard is asserted separately.
    """
    assert re.search(r"await _flutterwave_refund\(", code), "auto-refund call not found"

    guarded = re.search(
        r"if not amount:.*?else:\s*(?:.*?\n)*?\s*await _flutterwave_refund\(",
        code,
        re.S,
    )
    assert guarded, "the refund call is not behind an `if not amount` guard"

    guard_start = code.index("if not amount:")
    refund_idx = code.index("await _flutterwave_refund(")
    status_idx = code.index('order.status = "refunded"')
    assert guard_start < refund_idx < status_idx, (
        'setting status="refunded" must come after the amount guard and after '
        "the refund call, so a skipped refund cannot be recorded as issued"
    )


def test_refund_skip_is_recorded_on_the_order_for_humans(code):
    """A skipped refund must leave a reason a human can act on."""
    guard = code[code.index("if not amount:"):]
    guard = guard[: guard.index("else:")]
    assert "refund_reason" in guard, (
        "a blocked auto-refund must record why, or the order is left with no "
        "explanation of why the customer was not refunded"
    )
    # The status set BEFORE the guard (line ~197) stays failed_unfulfilled; the
    # guard must not assign a status of its own.
    assert 'order.status = "' not in guard, (
        "the guard must not change order.status — the order should remain "
        "failed_unfulfilled and be routed to a human"
    )
