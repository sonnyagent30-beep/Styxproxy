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

    weasyprint is a known, tracked exception (t_a193b8fd): it is imported lazily inside
    a request handler and is not installed in production at all, so pinning it here
    would assert a dependency the deploy target does not have. Everything else must
    be declared.
    """
    result = _run("import_closure_audit.py", ".")
    undeclared = [
        line
        for line in result.stdout.splitlines()
        if "undeclared third-party import" in line and "weasyprint" not in line
    ]
    assert not undeclared, "undeclared third-party imports found:\n" + "\n".join(undeclared)


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
