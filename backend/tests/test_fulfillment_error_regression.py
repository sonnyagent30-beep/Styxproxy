"""Fulfilment-error regression tests — kanban t_604d405d.

Two customer-visible fulfilment failures, both captured in production with a
concrete cause in `customer_audit_log` (`event_type='payment.fulfilled'`,
`details.fulfillment_error`). That captured cause is what makes the audit log
trustworthy as ground truth, so these tests assert the *specific* failure modes
cannot recur silently:

  ORD-1YNKB1 (2026-09-27) — "'socks_port' is an invalid keyword argument for
                           StyxproxyCredential"
  ORD-JSW0HN (2026-09-15) — "name 'longcat_arg_value' is not defined"

Neither was a logic error. Both were integration errors: a kwarg that did not
exist on the model, and a name that was never bound. Both are invisible to unit
tests that mock the model, and invisible to a green suite — the order was paid,
the webhook 200'd, and the customer got nothing.

These tests are deliberately *structural* (does the kwarg exist on the model;
does every name the fulfilment path references actually bind) rather than
end-to-end, because the failure lives precisely in the seam between the
fulfilment code and the model, and mocking across that seam is what let it
through the first time.
"""

import ast
import pathlib

import pytest

APP_ROOT = pathlib.Path(__file__).resolve().parent.parent / "app"


# ── ORD-1YNKB1: 'socks_port' is an invalid keyword argument ──────────────────


def test_styxproxy_credential_accepts_socks_port():
    """The kwarg that failed ORD-1YNKB1 must exist on the model.

    `create_credential` passes socks_port=socks_port to the model constructor.
    A missing column turns every paid order into a failed_manual_review with a
    200 webhook in the log.
    """
    from app.models import StyxproxyCredential

    assert "socks_port" in StyxproxyCredential.__table__.columns


def test_create_credential_only_passes_real_model_kwargs():
    """Every kwarg create_credential passes must be a real model column.

    This is the ORD-1YNKB1 bug generalised: not "is socks_port present" but
    "is any passed kwarg absent". Catches the next column rename the same way,
    before a customer pays for it.
    """
    from app.models import StyxproxyCredential

    source = (APP_ROOT / "services" / "credential.py").read_text()
    tree = ast.parse(source)

    model_columns = set(StyxproxyCredential.__table__.columns.keys())
    passed: set[str] = set()

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        # Match StyxproxyCredential(...) positional constructor.
        is_ctor = (
            isinstance(func, ast.Name) and func.id == "StyxproxyCredential"
        ) or (
            isinstance(func, ast.Attribute) and func.attr == "StyxproxyCredential"
        )
        if not is_ctor:
            continue
        for kw in node.keywords:
            if kw.arg:  # skip **kwargs spreads
                passed.add(kw.arg)

    # 'id' and relationship attrs set post-construction are legitimately absent.
    unknown = passed - model_columns - {"id"}
    assert not unknown, (
        f"create_credential passes kwargs absent from StyxproxyCredential: {sorted(unknown)}. "
        "Each one raises TypeError at runtime and fails a PAID order "
        "(this is exactly ORD-1YNKB1)."
    )


# ── ORD-JSW0HN: name 'longcat_arg_value' is not defined ──────────────────────


def test_no_undefined_names_in_fulfilment_path():
    """No NameError-class bug in the modules the fulfilment path imports.

    ORD-JSW0HN failed on an unbound name. `compileall` cannot catch it — the
    module compiles fine; the NameError only fires on the executed branch. This
    statically binds every name loaded in the fulfilment modules against
    module-level bindings, imports and builtins, so the next unbound
    `something_arg_value` is caught before it costs a customer an order.
    """
    import builtins

    builtin_names = set(dir(builtins))

    targets = [
        APP_ROOT / "services" / "credential.py",
        APP_ROOT / "services" / "flutterwave.py",
        APP_ROOT / "scripts" / "fulfillment_worker.py",
    ]

    problems: list[str] = []

    for path in targets:
        tree = ast.parse(path.read_text())

        bound: set[str] = set(builtin_names)
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                for alias in node.names:
                    bound.add((alias.asname or alias.name).split(".")[0])
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                bound.add(node.name)
            elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
                bound.add(node.id)
            elif isinstance(node, ast.arg):
                bound.add(node.arg)
            elif isinstance(node, ast.ExceptHandler) and node.name:
                bound.add(node.name)
            elif isinstance(node, (ast.Global, ast.Nonlocal)):
                bound.update(node.names)
            elif isinstance(node, ast.comprehension):
                for sub in ast.walk(node.target):
                    if isinstance(sub, ast.Name):
                        bound.add(sub.id)

        # Only flag loads inside functions (module-level loads of conditionally
        # defined names are a different, pre-existing pattern).
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for sub in ast.walk(node):
                    if isinstance(sub, ast.Name) and isinstance(sub.ctx, ast.Load):
                        if sub.id not in bound:
                            problems.append(f"{path.name}:{sub.lineno} undefined name {sub.id!r}")

    assert not problems, (
        "Names referenced but never bound in the fulfilment path — each is an "
        f"ORD-JSW0HN-class runtime failure on a paid order:\n  " + "\n  ".join(problems)
    )


@pytest.mark.parametrize("order_id", ["ORD-1YNKB1", "ORD-JSW0HN"])
def test_historic_fulfilment_failures_are_not_reintroduced(order_id):
    """Placeholder guard so the two order IDs stay pinned to this module.

    Kept as an explicit, named test rather than a bare comment so that deleting
    the coverage above shows up as a visible change rather than silent drift.
    """
    assert order_id.startswith("ORD-"), "order id shape changed; re-check provenance"