"""Go-live preflight gate for Paystack/Flutterwave live key installation (t_48808afc).

Production currently runs both gateways in TEST mode (`pk_test_`/`sk_test_`,
`FLWPUBK_TEST`/`FLWSECK_TEST`). That test mode is the ONLY thing keeping a set of
silent defects from becoming real customer loss:

  1. Paystack `tx_ref` mismatch -- the order row stored `TXF-...` while Paystack
     charged `TXP-...`, so the charged reference was recorded NOWHERE.  (t_d37da1c4)
  2. No capture column -- `amount_paid_ngn` is an INVOICE amount, populated on
     cancelled/refunded/expired rows too. It is never evidence money arrived.
  3. Admin refund never calls the gateway -- `routers/admin.py::_process_refund()`
     flips status, revokes the credential and emails the customer. All 46
     `refunded` rows are administrative status flips, not refunds.
  4. No Paystack refund support at all -- `services/paystack.py` has no refund
     method; `POST /transaction/{id}/refund` is never called.
  5. Flutterwave webhook secret is not Flutterwave's 32-char hex Secret Hash, so
     real `charge.completed` events are discarded with 401.

This script is the gate. It is deliberately FAIL-CLOSED: it reports `GO` only
when every check passes, and it treats "cannot determine" as a failure. A check
that cannot prove safety must never be reported as safe.

Usage:
    python3 scripts/go_live_gate.py                 # human-readable report
    python3 scripts/go_live_gate.py --json          # machine-readable
    python3 scripts/go_live_gate.py --env /opt/styxproxy/.env   # check real keys

Exit codes:
    0 = GO   (every check passed -- live keys may be installed)
    1 = NO-GO (one or more checks failed -- live keys must NOT be installed)
    2 = the gate itself could not run (missing tree, unreadable env)
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import re
import subprocess
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
APP = BACKEND / "app"

# Live-key markers. A live secret starts `sk_live_`/`pk_live_`; Flutterwave live
# keys carry a PROD/TEST designation in the variable name and the `FLWSECK_`/`FLWPUBK_`
# prefix, so those are matched by variable name + key-mode inference instead.
PAYSTACK_LIVE = re.compile(r"^(sk|pk)_live_[A-Za-z0-9]+$")
FLW_VAR_LIVE = re.compile(r"FLWSECK_PROD|FLWPUBK_PROD|FLWSECK_TEST_PROD")

# The shape Flutterwave documents for its webhook Secret Hash.
FLW_SECRET_HASH_SHAPE = re.compile(r"^[0-9a-fA-F]{32}$")


class Check:
    """One gate item. `ok` is tri-state on purpose: None means UNDETERMINED."""

    __slots__ = ("item", "title", "ok", "detail")

    def __init__(self, item: str, title: str, ok: bool | None, detail: str) -> None:
        self.item = item
        self.title = title
        self.ok = ok
        self.detail = detail

    def as_dict(self) -> dict:
        return {
            "item": self.item,
            "title": self.title,
            "status": "pass" if self.ok is True else ("fail" if self.ok is False else "unknown"),
            "detail": self.detail,
        }


# When set, every code check reads from this git ref instead of the working tree.
# This matters: the shared working tree carries uncommitted WIP from concurrent
# workers, and a gate that validates a half-finished edit green-lights on code
# that was never reviewed, never tested, and is not what would deploy.
_GIT_REF: str | None = None
# git must run from the repo ROOT, not backend/: pathspecs and `git show` paths are
# resolved relative to cwd, and backend/ paths would double up as backend/backend/.
_REPO = BACKEND.parent
_CWD = _REPO


def _read(path: Path) -> str | None:
    try:
        if _GIT_REF is None:
            return path.read_text(encoding="utf-8", errors="replace")
        rel = path.relative_to(_REPO).as_posix()
        r = subprocess.run(["git", "show", f"{_GIT_REF}:{rel}"],
                           capture_output=True, text=True, cwd=_CWD)
        return r.stdout if r.returncode == 0 else None
    except (OSError, ValueError):
        return None


def _tree_ok(*parts: str) -> bool:
    if _GIT_REF is None:
        return all((BACKEND / p).exists() for p in parts)
    r = subprocess.run(["git", "ls-tree", "-r", "--name-only", _GIT_REF, "--"] +
                       [f"backend/{p}" for p in parts],
                       capture_output=True, text=True, cwd=_CWD)
    return r.returncode == 0 and len(r.stdout.split()) == len(parts)


# ── 1. Charged reference is persisted ──────────────────────────────────────────
def check_reference_persistence() -> Check:
    """The reference Paystack actually charged must be stored on the order row.

    Asserting prefix alignment is NOT enough: if the gateway mints its own
    reference we must still write the returned one back, or reconciliation is
    impossible after the fact.
    """
    title = "Gateway's real charged reference is persisted (t_d37da1c4)"
    payments = _read(APP / "routers" / "payments.py")
    paystack = _read(APP / "services" / "paystack.py")
    if payments is None or paystack is None:
        return Check("1", title, None, "payments.py / paystack.py unreadable")

    # The service must be able to ACCEPT a backend-owned reference...
    accepts_ref = bool(re.search(r"def create_paystack_transaction\([^)]*tx_ref", paystack, re.S))
    if not accepts_ref:
        return Check("1", title, False,
                     "create_paystack_transaction() takes no tx_ref -- the service still "
                     "mints its own reference, so the charged ref is not ours to store")
    # ...and the returned/reference value must be written back to the order row.
    if not re.search(r"(provider_order_id|gateway_reference|gateway_tx_ref|charged_reference)\s*=", payments):
        return Check("1", title, False,
                     "no column write-back of the gateway-returned reference "
                     "(looked for provider_order_id/gateway_reference/gateway_tx_ref/"
                     "charged_reference assignment in payments.py)")
    return Check("1", title, True,
                 "create_paystack_transaction accepts tx_ref and payments.py writes the "
                 "gateway reference back onto the order")


# ── 2. A real capture column exists ────────────────────────────────────────────
def check_capture_column() -> Check:
    """`amount_paid_ngn` is an invoice amount and must never stand in for capture."""
    title = "A real capture column exists (amount_paid_ngn is not capture evidence)"
    models = _read(APP / "models.py")
    if models is None:
        return Check("2", title, None, "models.py unreadable")
    m = re.search(r"class Order\b.*?(?=\nclass |\Z)", models, re.S)
    if not m:
        return Check("2", title, None, "no Order class found in models.py")
    body = m.group(0)
    found = [c for c in re.findall(r"^\s{4}(\w+)\s*:\s*Mapped", body, re.M)
             if re.search(r"captur|captured_at|paid_at|settled", c)]
    if not found:
        return Check("2", title, False,
                     "Order has no capture/paid_at column -- capture cannot be proven from "
                     "our DB, so reconciliation has nothing authoritative to read")
    return Check("2", title, True, f"capture column(s) present: {', '.join(found)}")


# ── 3 & 4. Refunds actually call the gateway ───────────────────────────────────
def _functions(path: Path) -> dict:
    """Map function name -> source segment, for async and sync defs alike."""
    src = _read(path)
    if src is None:
        return {}
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return {}
    out = {}
    lines = src.splitlines()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            start = node.lineno - 1
            end = getattr(node, "end_lineno", node.lineno)
            out[node.name] = "\n".join(lines[start:end])
    return out


def check_admin_refund_calls_gateway() -> Check:
    """Admin refund must call the gateway and store the gateway's refund id."""
    title = "Admin refund calls the gateway and stores its response id (item 3)"
    admin = APP / "routers" / "admin.py"
    fns = _functions(admin)
    body = fns.get("_process_refund")
    if body is None:
        return Check("3", title, None, "_process_refund() not found in routers/admin.py")
    low = body.lower()
    # Strip the `async def _process_refund(...)` signature line before matching.
    # Without this the check self-satisfies on its OWN name: the substring
    # "refund(" appears inside "_process_refund(", so a refund that calls no
    # gateway at all still looks like it does. (Caught by the negative control.)
    body_no_sig = "\n".join(body.splitlines()[1:]).lower()
    gateway_re = re.compile(
        r"\b(paystack|flutterwave)"          # a gateway module/name
        r"|\brefund_transaction\b"
        r"|\b\w*refund\w*\s*\(",              # any refund-ish call, excluding the def line
    )
    calls_gateway = bool(gateway_re.search(body_no_sig))
    if not calls_gateway:
        return Check("3", title, False,
                     "_process_refund() makes NO gateway call -- it flips status, revokes the "
                     "credential and emails the customer, so the customer is told the money "
                     "came back when the gateway was never asked")
    stores_id = bool(re.search(r"(refund_id|gateway_refund_id|provider_refund_id|response\.json)", body))
    if not stores_id:
        return Check("3", title, False,
                     "_process_refund() calls a gateway but stores no refund response id -- "
                     "the refund still cannot be reconciled afterwards")
    return Check("3", title, True, "admin refund calls the gateway and records its response id")


def check_paystack_refund_support() -> Check:
    """Paystack refund support must exist and be reachable."""
    title = "Paystack refund support exists and is called (item 4)"
    svc = APP / "services" / "paystack.py"
    src = _read(svc)
    if src is None:
        return Check("4", title, None, "services/paystack.py unreadable")
    if not re.search(r"def \w*refund\w*\s*\(", src, re.I):
        return Check("4", title, False,
                     "no refund function in services/paystack.py -- Paystack's "
                     "POST /transaction/{id}/refund is never called")
    # And it must actually be invoked somewhere in app/.
    callers = []
    for p in (APP / "routers").glob("*.py"):
        blob = _read(p) or ""
        for m in re.finditer(r"\b(\w*[Rr]efund\w*)\s*\(", blob):
            nm = m.group(1)
            if nm.lower().startswith("_") or nm.lower() in {"refund", "requestrefund"}:
                continue
            callers.append(f"{p.name}:{nm}")
    if not callers:
        return Check("4", title, False,
                     "a Paystack refund helper exists but nothing in app/routers calls it")
    return Check("4", title, True, f"Paystack refund path present and called from {', '.join(callers)}")


# ── 5. Flutterwave webhook secret ──────────────────────────────────────────────
def check_flutterwave_webhook_secret(env_path: str | None) -> Check:
    """The configured secret must be Flutterwave's 32-char hex Secret Hash.

    Finance saw 228 x `401 invalid Flutterwave signature` from Flutterwave's own
    AWS us-east-1 IPs vs 68 successes: in live mode that silently discards real
    charge.completed events, so orders never fulfill.
    """
    title = "Flutterwave webhook secret matches the dashboard Secret Hash (item 5)"
    if not env_path:
        return Check("5", title, None,
                     "no --env supplied: cannot verify the deployed secret "
                     "(run with --env /opt/styxproxy/.env)")
    p = Path(env_path)
    if not p.exists():
        return Check("5", title, None, f"env file not found: {p}")
    src = _read(p)
    if src is None:
        return Check("5", title, None, f"env file unreadable: {p}")
    m = re.search(r"^FLUTTERWAVE_WEBHOOK_SECRET=(.*)$", src, re.M)
    if not m:
        return Check("5", title, None, "FLUTTERWAVE_WEBHOOK_SECRET not present in env file")
    val = m.group(1).strip().strip('"').strip("'")
    if not val:
        return Check("5", title, False, "FLUTTERWAVE_WEBHOOK_SECRET is empty")
    if not FLW_SECRET_HASH_SHAPE.match(val):
        return Check("5", title, False,
                     f"secret shape is wrong (len={len(val)}, expected 32 hex chars) -- this "
                     "is not Flutterwave's Secret Hash, so every real webhook will 401")
    return Check("5", title, True, "secret matches Flutterwave's 32-char hex Secret Hash shape")


# ── Live-key exposure ──────────────────────────────────────────────────────────
def check_no_live_keys(env_path: str | None) -> Check:
    """Confirm we are still in test mode. This is the gate's own precondition."""
    title = "No live gateway key is installed (gate precondition)"
    if not env_path:
        return Check("0", title, None, "no --env supplied: cannot confirm key mode")
    src = _read(Path(env_path))
    if src is None:
        return Check("0", title, None, f"env file unreadable: {env_path}")
    live = []
    for line in src.splitlines():
        if not re.match(r"^\s*[A-Z0-9_]+=", line):
            continue
        k, _, v = line.partition("=")
        v = v.strip().strip('"').strip("'")
        if PAYSTACK_LIVE.match(v) or FLW_VAR_LIVE.search(k):
            live.append(k.strip())
    if live:
        return Check("0", title, False,
                     f"LIVE keys already installed: {', '.join(live)} -- the defects this "
                     "gate covers are no longer hypothetical")
    return Check("0", title, True, "all gateway keys are in test mode")


def run(env_path: str | None) -> list[Check]:
    return [
        check_no_live_keys(env_path),
        check_reference_persistence(),
        check_capture_column(),
        check_admin_refund_calls_gateway(),
        check_paystack_refund_support(),
        check_flutterwave_webhook_secret(env_path),
    ]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Styxproxy go-live payment gate")
    ap.add_argument("--env", default=os.environ.get("GO_LIVE_ENV"),
                    help="path to the deployed .env to inspect for key mode / webhook secret")
    ap.add_argument("--json", action="store_true", help="emit JSON")
    ap.add_argument("--git-ref", default="origin/main",
                    help="git ref holding the COMMITTED code to gate on (default: origin/main). "
                         "The working tree carries uncommitted WIP from concurrent workers; "
                         "gating on it would pass on a half-finished, unreviewed fix. "
                         "Use --git-ref '' to gate on the working tree instead.")
    args = ap.parse_args(argv)

    global _GIT_REF
    ref = (args.git_ref or "").strip()
    _GIT_REF = ref or None

    if not _tree_ok("app/routers/payments.py", "app/models.py"):
        print(f"go_live_gate: backend tree not found at ref {_GIT_REF!r}; run from backend/",
              file=sys.stderr)
        return 2

    checks = run(args.env)
    go = all(c.ok is True for c in checks)

    if args.json:
        print(json.dumps({"verdict": "GO" if go else "NO-GO", "checks": [c.as_dict() for c in checks]}, indent=2))
    else:
        print("=" * 74)
        print("Styxproxy go-live payment gate -- live Paystack/Flutterwave keys")
        print("=" * 74)
        for c in checks:
            mark = {True: "PASS", False: "FAIL", None: "UNKN"}[c.ok]
            print(f"[{mark}] {c.item}. {c.title}")
            for line in _wrap(c.detail, 68):
                print(f"        {line}")
        print("-" * 74)
        if go:
            print("VERDICT: GO -- all checks passed; live keys may be installed.")
        else:
            print("VERDICT: NO-GO -- do NOT install live keys.")
            und = [c.item for c in checks if c.ok is None]
            if und:
                print(f"         undetermined items {', '.join(und)} count as FAIL (fail-closed).")
        print("=" * 74)
    return 0 if go else 1


def _wrap(text: str, width: int) -> list[str]:
    words, lines, cur = text.split(), [], ""
    for w in words:
        if len(cur) + len(w) + 1 > width:
            lines.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    if cur:
        lines.append(cur)
    return lines


if __name__ == "__main__":
    sys.exit(main())
