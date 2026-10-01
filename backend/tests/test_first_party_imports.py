"""Every first-party `from app... import name` must resolve (t_5d7bbe76).

The backend could not import `app.main` at all for a stretch of this tree. The
cause was mundane: app/routers/admin.py and app/routers/auth.py imported six
refund models and two IP-allowlist models from `app.schemas`, where they are not
defined -- they live in `app.routers.schemas`. `from X import name` raises
ImportError at import time, and app/routers/__init__.py imports admin, so one
wrong module path stopped the entire application from starting.

The failure was expensive because it was invisible. Two cards reported a green
test count with "10 pre-existing collection errors" written off as baseline; those
10 errors *were* this bug, and in one case the module that never executed was the
one carrying that card's own acceptance criterion. A suite that cannot import half
of itself cannot report on itself.

Why a static check and not just the runtime import gate
------------------------------------------------------
scripts/import_closure_audit.py (from t_dbdedd9a) already runs on main and is
green -- and it stays green on a branch that cannot import app.main, because it
only checks third-party imports against requirements.txt. It has no opinion about
whether a name exists in the module it is imported from. That gap is what let this
class through.

Importing app.main is still the stronger check, and the CI gate in
ci/import-gate-and-charon-contract adds it. This test earns its place by covering
what that gate structurally cannot see:

  * app/routers/customers.py and app/scripts/send_renewal_reminders.py are not
    reachable from app.main, so no entry-point import can ever notice they are
    broken -- but the cron job has a systemd/cron unit and the router has an
    OpenAPI operation.
  * app/routers/auth.py:1455 imports AdminRefreshToken *inside* a function body.
    The module imports fine; the route 500s on first call. A startup gate is
    blind to this by construction.

These are pure stdlib and need no installed dependencies, so they keep working in
the incomplete environments they exist to catch.
"""

from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
SCRIPTS = BACKEND / "scripts"
APP = BACKEND / "app"
CHECKER = SCRIPTS / "check_first_party_imports.py"

# Imports that are unresolved on main today, each with the reason it is tolerated
# here. Every entry is a real defect being tracked, not a false positive to be
# silenced: the checker reports all of them, and this list only keeps the suite
# red-free while the fixes land. Removing an entry here without fixing the import
# turns this test red again.
#
# TODO(t_5d7bbe76): each of these is a follow-up card. When one is fixed, delete
# its entry and the checker will keep enforcing the rest.
KNOWN_UNRESOLVED = {
    # app/routers/auth.py:1455 -- function-local, so app.main still imports, but
    # POST /api/admin/auth/refresh raises ImportError -> 500 on every call. The
    # model does not exist in app/models.py at all.
    ("app/routers/auth.py", "AdminRefreshToken"),
    # app/routers/customers.py:14 -- module scope. Not reachable from app.main
    # (routers/__init__.py does not import it), so nothing loads this module and
    # nothing notices. ConsentEvent is not defined in app/models.py.
    ("app/routers/customers.py", "ConsentEvent"),
}


def _run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(CHECKER), *args],
        capture_output=True,
        text=True,
        cwd=BACKEND,
    )


def test_every_first_party_import_resolves() -> None:
    """No unresolvable first-party import outside the known-debt allowlist."""
    result = _run()
    reported = set()
    for line in result.stdout.splitlines():
        line = line.strip()
        if not line.startswith("app/") or "cannot import name" not in line:
            continue
        # "app/routers/admin.py:47: cannot import name 'RefundX' from 'app.schemas'"
        file_part, _, rest = line.partition(":")
        name = rest.split("'")[1]
        reported.add((file_part, name))
    unexpected = reported - KNOWN_UNRESOLVED

    # The checker must actually be running, not silently finding nothing because it
    # was pointed at the wrong tree. Assert we parse findings at all on a tree we
    # know is dirty -- see test_checker_catches_the_original_defect.
    assert reported, (
        "checker reported no findings on a tree known to contain unresolved imports; "
        "it is probably resolving against the wrong package root"
    )
    assert not unexpected, (
        "unresolvable first-party import(s) -- `from app.x import name` raises "
        "ImportError at import time and takes down every module that transitively "
        "imports it:\n"
        + "\n".join(f"  {file}: {name}" for file, name in sorted(unexpected))
        + "\n\nIf the model is defined in app/routers/schemas.py, import it from "
        "there rather than from app.schemas."
    )
    # A dependency that silently stops resolving must not read as a pass.
    assert result.returncode in (0, 1), f"checker crashed (exit {result.returncode})\n{result.stderr}"


def test_checker_catches_the_original_defect() -> None:
    """Negative control: the checker must go red on the bug it was written for.

    A guard that cannot fail is not a guard. This reconstructs the exact import
    that broke app.main -- RefundApprovalResponse imported from app.schemas where
    it is not defined -- in a temp copy of the tree, and asserts the checker names
    it. If someone loosens the checker until it goes quiet, this goes red.
    """
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "app" / "routers").mkdir(parents=True)
        (root / "app" / "__init__.py").write_text("")
        (root / "app" / "routers" / "__init__.py").write_text("")
        # The model genuinely lives in routers/schemas.py, not schemas.py.
        (root / "app" / "routers" / "schemas.py").write_text(
            "from pydantic import BaseModel\n\n\nclass RefundApprovalResponse(BaseModel):\n    pass\n"
        )
        (root / "app" / "schemas.py").write_text("from pydantic import BaseModel\n")
        # The defect: imported from the module that does not define it.
        (root / "app" / "routers" / "admin.py").write_text("from app.schemas import RefundApprovalResponse\n")

        result = subprocess.run(
            [sys.executable, str(CHECKER), str(root / "app")],
            capture_output=True,
            text=True,
            cwd=BACKEND,
        )

    assert result.returncode == 1, f"checker did not fail on a known-bad import:\n{result.stdout}"
    assert "RefundApprovalResponse" in result.stdout
    assert "app.schemas" in result.stdout


def test_checker_accepts_a_correct_import() -> None:
    """Negative control, other direction: the fix must not be flagged.

    The same model imported from the module that actually defines it must pass,
    otherwise the checker is not discriminating and its silence means nothing.
    """
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "app" / "routers").mkdir(parents=True)
        (root / "app" / "__init__.py").write_text("")
        (root / "app" / "routers" / "__init__.py").write_text("")
        (root / "app" / "routers" / "schemas.py").write_text(
            "from pydantic import BaseModel\n\n\nclass RefundApprovalResponse(BaseModel):\n    pass\n"
        )
        (root / "app" / "schemas.py").write_text("from pydantic import BaseModel\n")
        (root / "app" / "routers" / "admin.py").write_text("from app.routers.schemas import RefundApprovalResponse\n")

        result = subprocess.run(
            [sys.executable, str(CHECKER), str(root / "app")],
            capture_output=True,
            text=True,
            cwd=BACKEND,
        )

    assert result.returncode == 0, f"checker rejected a valid import:\n{result.stdout}"


def test_checker_tolerates_guarded_optional_imports() -> None:
    """A try/except ImportError around a first-party import is a valid pattern.

    Optional-dependency shims are legitimate. If the checker flagged them, people
    would learn to ignore it, and a tool nobody trusts catches nothing.
    """
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "app").mkdir(parents=True)
        (root / "app" / "__init__.py").write_text("")
        (root / "app" / "maybe.py").write_text("VALUE = 1\n")
        (root / "app" / "consumer.py").write_text(
            "try:\n    from app.maybe import DOES_NOT_EXIST\nexcept ImportError:\n    pass\n"
        )

        result = subprocess.run(
            [sys.executable, str(CHECKER), str(root / "app")],
            capture_output=True,
            text=True,
            cwd=BACKEND,
        )

    assert result.returncode == 0, f"checker flagged a guarded optional import:\n{result.stdout}"


def test_checker_ignores_third_party_and_stdlib() -> None:
    """The checker must only judge first-party imports.

    requirements.txt coverage is a different tool's job
    (scripts/import_closure_audit.py). Claiming third-party names here would
    duplicate that check and produce findings nobody can action.
    """
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "app").mkdir(parents=True)
        (root / "app" / "__init__.py").write_text("")
        (root / "app" / "consumer.py").write_text(
            "import os\nimport json\nfrom fastapi import FastAPI\nimport a_package_not_in_reqs\n"
        )

        result = subprocess.run(
            [sys.executable, str(CHECKER), str(root / "app")],
            capture_output=True,
            text=True,
            cwd=BACKEND,
        )

    assert result.returncode == 0, f"checker judged non-first-party imports:\n{result.stdout}"


def test_main_entrypoint_imports() -> None:
    """app.main must import in a configured test environment.

    The static checks above are complements to this, not a substitute: only a real
    import proves the entry point loads. Runs in a subprocess so a failure is a
    clean assertion rather than a collection error that aborts the whole run --
    a collection error is exactly how this bug hid in the first place.
    """
    result = subprocess.run(
        [sys.executable, "-c", "import app.main; print('OK', len(app.main.app.routes))"],
        capture_output=True,
        text=True,
        cwd=BACKEND,
        env={**dict(__import__("os").environ), "PYTHONPATH": str(BACKEND)},
    )
    assert result.returncode == 0, (
        "import app.main failed -- the application cannot start:\n" f"{result.stdout}\n{result.stderr}"
    )
