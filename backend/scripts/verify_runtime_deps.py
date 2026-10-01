#!/usr/bin/env python3
"""Verify that pyproject [project] dependencies are all pinned in requirements.txt.

Motivation (t_8649483f): `alembic==1.13.2` was declared in pyproject.toml but was
NOT in requirements.txt. Every runtime install path -- the production venv
(`/opt/styxproxy/backend/venv`) and the CI `backend-test` job -- builds from
requirements.txt, so alembic was simply absent from the environment and the
deploy workflow's `alembic upgrade heads` could never do anything.
`import_closure_audit.py` could not catch this because it walks Python imports,
and alembic is used as a CLI tool: no module under app/ or tests/ ever does
`import alembic`, so its absence is invisible to an import-driven audit.

This closes the class rather than the single package: any dependency declared in
pyproject.toml but missing from requirements.txt is a declared-yet-not-installed
package that only surfaces when someone tries to run it.

Offline and venv-free, so it can gate every PR before an install is attempted.

Usage:
    python backend/scripts/verify_runtime_deps.py
Exit code 1 if any pyproject dependency is missing from requirements.txt.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path


def normalise(requirement: str) -> str:
    """Reduce a requirement string to a comparable distribution name."""
    name = requirement.split("[", 1)[0]  # drop extras
    for sep in ("==", ">=", "<=", "~=", ">", "<", "!", ";"):
        name = name.split(sep, 1)[0]
    return name.strip().lower().replace("_", "-").replace(".", "-")


def requirement_names(path: Path) -> set[str]:
    names: set[str] = set()
    if not path.exists():
        return names
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].strip()
        if line:
            names.add(normalise(line))
    return names


def pyproject_runtime_deps(path: Path) -> list[str]:
    """Dependencies from the [project] table only, not optional/dev extras.

    Dev and optional extras are deliberately excluded: they are not installed on
    the production path, so their absence from requirements.txt is correct.
    """
    text = path.read_text(encoding="utf-8")
    # Anchor on a top-level `dependencies = [` (the [project] table). The
    # [project.optional-dependencies] entries are nested and indented, so they
    # do not match.
    match = re.search(r"^dependencies\s*=\s*\[", text, re.M)
    if not match:
        raise SystemExit("ERROR: could not find [project] dependencies in pyproject.toml")

    # Bracket-match to the closing "]". A non-greedy regex is wrong here: the
    # first "]" inside the block belongs to an extras marker such as
    # uvicorn[standard], which truncates the list after its first entry.
    start = match.end() - 1
    depth = 0
    block = None
    for i in range(start, len(text)):
        if text[i] == "[":
            depth += 1
        elif text[i] == "]":
            depth -= 1
            if depth == 0:
                block = text[start + 1 : i]
                break
    if block is None:
        raise SystemExit("ERROR: unterminated dependencies list in pyproject.toml")

    return re.findall(r'"([^"]+)"', block)


def main(root: Path | None = None) -> int:
    root = root or Path(__file__).resolve().parent.parent
    req_names = requirement_names(root / "requirements.txt")
    declared = pyproject_runtime_deps(root / "pyproject.toml")

    missing = [d for d in declared if normalise(d) not in req_names]

    if missing:
        print("ERROR: declared in pyproject.toml [project] but MISSING from requirements.txt:")
        print("       (the production venv and the CI test job install from")
        print("        requirements.txt, so these are declared-but-never-installed)")
        for dep in missing:
            print(f"  - {dep}")
        print("\nAdd each to requirements.txt, then re-run this script.")
        return 1

    print(
        f"OK: all {len(declared)} pyproject [project] dependencies are pinned "
        f"in requirements.txt ({len(req_names)} declared distributions)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())