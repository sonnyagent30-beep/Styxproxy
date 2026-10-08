"""Regression tests for backend dependency completeness (t_dbdedd9a).

`rq` was imported at module scope by the fulfillment worker but absent from
backend/requirements.txt, so a clean `pip install -r requirements.txt` produced an
environment where the worker could not be imported. It went unnoticed because no test
imported the worker module.

These tests assert the property structurally -- every third-party import reachable from
the worker is provided by a declared distribution -- so the next missing pin fails here
instead of on a deploy. They are pure stdlib and need no installed dependencies, which
is the point: they must keep working even when the environment is incomplete.
"""
from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
SCRIPTS = BACKEND / "scripts"

# Modules that must remain importable from requirements.txt alone. Each is a runtime
# entry point, not a convenience script.
RUNTIME_ENTRYPOINTS = [
    "app.scripts.fulfillment_worker",  # styxproxy-fulfillment-worker.service
    "app.main",
]


def _run(script: str, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPTS / script), *args],
        capture_output=True,
        text=True,
        cwd=BACKEND,
    )


def test_worker_import_closure_is_fully_declared():
    """Every third-party import reachable from the worker is pinned in requirements.txt.

    This is the offline equivalent of
    `python -c "import app.scripts.fulfillment_worker"` in a venv built from
    requirements.txt: same property, but checkable without an install.
    """
    result = _run("verify_import_closure.py", "app.scripts.fulfillment_worker")
    assert result.returncode == 0, (
        "fulfillment worker's import closure references undeclared dependencies:\n"
        f"{result.stdout}\n{result.stderr}"
    )


def test_rq_is_declared_in_requirements():
    """rq is a module-scope import of the fulfillment worker; it must be pinned."""
    text = (BACKEND / "requirements.txt").read_text(encoding="utf-8")
    assert "rq==" in text, "rq is not pinned in backend/requirements.txt"


def test_rq_is_declared_in_pyproject_dependencies():
    """rq is runtime, not a dev-only tool, so it belongs in project dependencies."""
    text = (BACKEND / "pyproject.toml").read_text(encoding="utf-8")
    deps = text.split("[project.optional-dependencies]", 1)[0]
    assert "rq==" in deps, "rq is missing from [project] dependencies in pyproject.toml"


def test_no_undeclared_imports_outside_known_exceptions():
    """Repo-wide audit: no third-party import lacks a declared distribution.

    This was previously carrying an exception for weasyprint, which was imported
    lazily by the server-side receipt-PDF route and was never installed on
    production. That route has since been removed (see t_4acded30) -- receipts
    are generated client-side with the already-declared jspdf -- so there is no
    longer any undeclared import to except, and the exemption is gone. If a new
    one appears this test must fail.
    """
    result = _run("import_closure_audit.py", ".")
    undeclared = [
        line
        for line in result.stdout.splitlines()
        if "undeclared third-party import" in line
    ]
    assert not undeclared, "undeclared third-party imports found:\n" + "\n".join(undeclared)


def test_no_weasyprint_import_remains():
    """WeasyPrint must not creep back in.

    It needs native pango/cairo/gdk-pixbuf libraries that the production host
    does not have, so an import of it -- lazy or otherwise -- is a route that can
    only 500 in production. Receipts are rendered in the browser with jspdf.

    Parsed with ast rather than grepped, so prose mentions of the word in a
    docstring (including in this file and in the audit scripts) do not trip it;
    only a real import statement counts.
    """
    offenders: list[str] = []
    unparseable: list[str] = []
    for sub in ("app", "scripts", "tests"):
        for path in sorted((BACKEND / sub).rglob("*.py")):
            if ".venv" in path.parts or "__pycache__" in path.parts:
                continue
            rel = path.relative_to(BACKEND)
            try:
                tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            except SyntaxError:
                # Pre-existing broken files are not this test's business, but
                # they do blind the scan, so surface them rather than hide them.
                unparseable.append(str(rel))
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    names = [a.name for a in node.names]
                elif isinstance(node, ast.ImportFrom):
                    names = [node.module or ""]
                else:
                    continue
                if any(n.split(".")[0].lower() == "weasyprint" for n in names):
                    offenders.append(f"{rel}:{node.lineno}")
    assert not offenders, "weasyprint is imported in backend source: " + ", ".join(offenders)
    if unparseable:
        print(f"note: {len(unparseable)} file(s) skipped as unparseable: {unparseable}")


def test_orders_router_has_no_pdf_route():
    """The retired server-side receipt-PDF route must not be reinstated.

    It could only ever 500 in production (WeasyPrint absent). The frontend
    generates the PDF client-side with jspdf via src/lib/pdf-receipt.ts.
    """
    router = BACKEND / "app" / "routers" / "orders.py"
    tree = ast.parse(router.read_text(encoding="utf-8"), filename=str(router))
    # NOTE: must match AsyncFunctionDef too -- the original get_receipt_pdf was
    # `async def`, and matching FunctionDef alone silently misses every async
    # route (caught by the negative control, not by inspection).
    pdf_routes = [
        f"line {node.lineno}"
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and any(
            isinstance(d, ast.Constant) and isinstance(d.value, str) and d.value.endswith("/pdf")
            for dec in node.decorator_list
            for d in getattr(dec, "args", [])
        )
    ]
    assert not pdf_routes, f"server-side /pdf route is back: {', '.join(pdf_routes)}"


def test_requirements_file_parses_as_valid_pins():
    """Every non-comment line in requirements.txt is a pinned distribution spec."""
    bad: list[str] = []
    for raw in (BACKEND / "requirements.txt").read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        if not any(op in line for op in ("==", ">=", "<=", "~=", ">", "<")):
            bad.append(raw)
    assert not bad, f"unpinned or malformed requirement lines: {bad}"


def test_runtime_entrypoint_closures_are_declared():
    """Each runtime entry point's transitive first-party closure is installable."""
    for module in RUNTIME_ENTRYPOINTS:
        result = _run("verify_import_closure.py", module)
        assert result.returncode == 0, f"{module} closure incomplete:\n{result.stdout}"
