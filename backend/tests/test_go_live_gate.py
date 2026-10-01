"""Tests for the go-live payment gate (t_48808afc).

Production is in TEST mode for both gateways, and that test mode is the only
thing keeping five silent payment defects from becoming real customer loss. The
gate exists so that installing `sk_live_`/`FLWSECK_PROD` becomes a mechanical
check rather than a memory.

Two properties are asserted here:

1. **Fail-closed.** An UNDETERMINED check must never yield GO. This is the one
   that matters most -- a gate that reports "safe" because it could not read
   the environment is worse than no gate, because it manufactures confidence.

2. **Negative controls.** Every structural check is proved to FAIL when the
   exact defect is reintroduced into a scratch tree. A guard that passes on both
   the broken and the fixed tree proves nothing (see the retired receipt-PDF
   route guard, t_4acded30, which passed on a tree that still had the bug).

Stdlib only -- the gate must keep working in a broken environment, which is
precisely when it is needed.
"""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
GATE = BACKEND / "scripts" / "go_live_gate.py"


def _load():
    spec = importlib.util.spec_from_file_location("go_live_gate", GATE)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


gate = _load()


def _run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(GATE), *args],
                          capture_output=True, text=True, cwd=BACKEND)


# ── The gate itself ────────────────────────────────────────────────────────────

def test_gate_reports_no_go_against_committed_code():
    """origin/main must be NO-GO: the five defects are open in committed code.

    This is the guard that stops a live-key swap from being waved through on the
    strength of an in-progress fix that was never committed.
    """
    r = _run("--json")
    assert r.returncode == 1, f"expected NO-GO (exit 1), got {r.returncode}"
    payload = json.loads(r.stdout)
    assert payload["verdict"] == "NO-GO"
    failed = {c["item"] for c in payload["checks"] if c["status"] != "pass"}
    assert failed, "gate reported NO-GO with no failing/undetermined item"


def test_undetermined_checks_count_as_failure():
    """No --env => items 0 and 5 are UNKNOWN => still NO-GO, never GO."""
    r = _run("--json")
    payload = json.loads(r.stdout)
    by_item = {c["item"]: c for c in payload["checks"]}
    assert by_item["0"]["status"] == "unknown"
    assert by_item["5"]["status"] == "unknown"
    assert payload["verdict"] == "NO-GO"


def test_json_output_is_machine_parseable():
    r = _run("--json")
    payload = json.loads(r.stdout)
    assert set(payload) == {"verdict", "checks"}
    assert {"item", "title", "status", "detail"} == set(payload["checks"][0])


# ── Item 5: Flutterwave webhook secret ─────────────────────────────────────────

def test_flutterwave_secret_shape_is_enforced(tmp_path: Path):
    """The 12-char value on production must FAIL; a 32-hex hash must PASS."""
    good = tmp_path / "good.env"
    good.write_text("FLUTTERWAVE_WEBHOOK_SECRET=" + "a" * 32 + "\n")
    assert gate.check_flutterwave_webhook_secret(str(good)).ok is True

    bad = tmp_path / "bad.env"
    bad.write_text("FLUTTERWAVE_WEBHOOK_SECRET=Danifab@6158\n")
    c = gate.check_flutterwave_webhook_secret(str(bad))
    assert c.ok is False
    assert "32 hex" in c.detail


def test_flutterwave_secret_empty_is_failure_not_unknown():
    empty = "FLUTTERWAVE_WEBHOOK_SECRET=\n"
    p = Path("/tmp/_gate_empty.env")
    p.write_text(empty)
    try:
        assert gate.check_flutterwave_webhook_secret(str(p)).ok is False
    finally:
        p.unlink(missing_ok=True)


# ── Item 0: live-key detection ─────────────────────────────────────────────────

def test_live_key_detection():
    live = "/tmp/_gate_live.env"
    Path(live).write_text("PAYSTACK_SECRET_KEY=sk_live_abcdef123456\n")
    try:
        c = gate.check_no_live_keys(live)
        assert c.ok is False
        assert "PAYSTACK_SECRET_KEY" in c.detail
    finally:
        Path(live).unlink(missing_ok=True)

    test_mode = "/tmp/_gate_test.env"
    Path(test_mode).write_text("PAYSTACK_SECRET_KEY=sk_test_abcdef123456\n"
                               "FLUTTERWAVE_SECRET_KEY=FLWSECK_TEST-abcdef\n")
    try:
        assert gate.check_no_live_keys(test_mode).ok is True
    finally:
        Path(test_mode).unlink(missing_ok=True)


# ── Negative controls on the AST/regex checks ──────────────────────────────────
#
# Each control copies the real tree into a scratch dir, reintroduces the exact
# defect, points the gate at the scratch tree, and asserts the check FAILS.
# Without these, a check that silently stopped matching would still pass.

SCRATCH_FILES = {
    "app/services/paystack.py": None,
    "app/routers/payments.py": None,
    "app/routers/admin.py": None,
    "app/models.py": None,
}


def _make_scratch(tmp_path: Path) -> Path:
    """Copy the live files the checks read into a scratch backend tree."""
    root = tmp_path / "backend"
    for rel in SCRATCH_FILES:
        dst = root / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        src = BACKEND / rel
        dst.write_text(src.read_text(encoding="utf-8", errors="replace")
                       if src.exists() else "")
    (root / "scripts").mkdir(parents=True, exist_ok=True)
    return root


def test_negative_control_admin_refund_with_no_gateway_call(tmp_path: Path, monkeypatch):
    """Reintroduce the item-3 defect: a refund that never asks the gateway."""
    root = _make_scratch(tmp_path)
    admin = root / "app/routers/admin.py"
    admin.write_text(
        "async def _process_refund(session, order, admin_email, reason, http_request):\n"
        '    """status flip + revoke + email, no gateway call."""\n'
        '    order.status = "refunded"\n'
        "    return {\"refund_amount\": 0}\n"
    )
    monkeypatch.setattr(gate, "APP", root / "app")
    c = gate.check_admin_refund_calls_gateway()
    assert c.ok is False
    assert "NO gateway call" in c.detail


def test_negative_control_paystack_refund_absent(tmp_path: Path, monkeypatch):
    """Reintroduce item 4: no refund function in the Paystack service."""
    root = _make_scratch(tmp_path)
    (root / "app/services/paystack.py").write_text(
        "async def create_paystack_transaction(amount_ngn, customer_email, **kw):\n"
        "    return {}\n"
    )
    (root / "app/routers").mkdir(parents=True, exist_ok=True)
    (root / "app/routers/payments.py").write_text("# no callers\n")
    monkeypatch.setattr(gate, "APP", root / "app")
    c = gate.check_paystack_refund_support()
    assert c.ok is False


def test_negative_control_capture_column_absent(tmp_path: Path, monkeypatch):
    """Reintroduce item 2: an Order model with only the invoice amount."""
    root = _make_scratch(tmp_path)
    (root / "app/models.py").write_text(
        "class Order(Base):\n"
        "    amount_paid_ngn: Mapped[Optional[float]] = mapped_column(Numeric(12, 2))\n"
        "    status: Mapped[str] = mapped_column(String(20))\n"
    )
    monkeypatch.setattr(gate, "APP", root / "app")
    c = gate.check_capture_column()
    assert c.ok is False
    assert "no capture" in c.detail


def test_negative_control_reference_not_persisted(tmp_path: Path, monkeypatch):
    """Reintroduce item 1: service mints its own ref, order row never stores it."""
    root = _make_scratch(tmp_path)
    (root / "app/services/paystack.py").write_text(
        "async def create_paystack_transaction(amount_ngn, customer_email, **kw):\n"
        "    return {}\n"
    )
    (root / "app/routers/payments.py").write_text(
        "tx_ref = 'TXF-abc'\norder.payment_reference = tx_ref\n"
    )
    monkeypatch.setattr(gate, "APP", root / "app")
    c = gate.check_reference_persistence()
    assert c.ok is False


def test_capture_column_check_passes_when_column_present(tmp_path: Path, monkeypatch):
    """Positive control -- the capture check must be capable of passing."""
    root = _make_scratch(tmp_path)
    (root / "app/models.py").write_text(
        "class Order(Base):\n"
        "    captured_at: Mapped[Optional[str]] = mapped_column(String(40))\n"
    )
    monkeypatch.setattr(gate, "APP", root / "app")
    assert gate.check_capture_column().ok is True
