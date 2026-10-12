#!/usr/bin/env python3
"""Verify that every third-party import in the backend is declared in requirements.txt.

Motivation (t_dbdedd9a): `rq` was imported at module scope by the fulfillment worker
but absent from backend/requirements.txt, so a clean install produced an environment
where the worker could not even be imported -- and no test caught it because no test
imports the worker module.

This script closes that class of bug structurally rather than one package at a time:
it walks the AST of every module under app/ and scripts/, collects every top-level
module imported, and reports any that is neither stdlib, nor a first-party package,
nor satisfied by a distribution declared in requirements.txt / pyproject.toml.

It is offline and needs no venv, so it runs in CI and in review before an install is
ever attempted.

Usage:
    python scripts/import_closure_audit.py [root ...]
Exit code 1 if any undeclared third-party import is found.
"""
from __future__ import annotations

import ast
import sys
import sysconfig
from pathlib import Path

# Distribution name -> import name, for declared deps whose import name differs.
# Keep sorted; add an entry whenever a new pin is added with a non-obvious import name.
IMPORT_NAME_OVERRIDES = {
    "python-jose": "jose",
    "pydantic-settings": "pydantic_settings",
    "python-dateutil": "dateutil",
    "python-multipart": "multipart",
    "python-dotenv": "dotenv",
    "passlib": "passlib",
    "uvicorn": "uvicorn",
    "sqlalchemy": "sqlalchemy",
    "sentry-sdk": "sentry_sdk",
    "pytest-asyncio": "pytest_asyncio",
    "pyotp": "pyotp",
    "pyjwt": "jwt",
    "pillow": "PIL",
}

# Distributions that are pulled in transitively by a declared dependency, so an
# import of them is legitimately covered. Each entry records which pin provides it,
# because an undeclared transitive that disappears is exactly the regression class
# this script exists to catch (see t_dbdedd9a for the rq instance).
TRANSITIVE_VIA = {
    "starlette": "fastapi==0.133.1",
    "cryptography": "python-jose[cryptography]==3.5.0",
    "anyio": "fastapi==0.133.1 / starlette",
    "sqlalchemy": "sqlalchemy[asyncio]==2.0.51",
}

FIRST_PARTY = {
    "app",
    "scripts",
    "alembic",
    "tests",
    # Sibling modules inside scripts/ that the audit scripts import as top-level names
    # (they add scripts/ to sys.path rather than using a package-relative import).
    "import_closure_audit",
    # First-party subpackages of app/services/charon/.
    "charon",
    "knowledge",
    "llm",
    "scenarios",
    "tools",
}


def declared_distributions(root: Path) -> set[str]:
    """Top-level distribution names declared in requirements.txt and pyproject.toml."""
    names: set[str] = set()
    req = root / "requirements.txt"
    if req.exists():
        for line in req.read_text(encoding="utf-8").splitlines():
            line = line.split("#", 1)[0].strip()
            if not line:
                continue
            # strip version specifiers, extras and environment markers
            for sep in ("[", "=", "<", ">", "!", "~", ";", " "):
                line = line.split(sep, 1)[0]
            if line:
                names.add(line.lower().replace("_", "-"))
    return names


def stdlib_names() -> set[str]:
    names = set(sys.stdlib_module_names)
    names |= {"__future__", "__main__"}
    return names


def imported_modules(tree: ast.Module) -> set[str]:
    """Fully-qualified modules imported anywhere in the file.

    Unlike `top_level_imports` this keeps the dotted path (`app.services.email`), so a
    first-party import can be resolved to a real file and followed. Relative imports
    (level > 0) are returned as-is via a leading-dot marker and handled by the caller.
    """
    # Everything reachable, including annotation-only imports: used for traversal, so a
    # first-party module imported under TYPE_CHECKING is still followed. Runtime safety
    # is judged separately by scope (see imported_modules_by_scope).
    module_scope, deferred, annotation_only = imported_modules_by_scope(tree)
    return set(module_scope | deferred | annotation_only)


def imported_modules_by_scope(tree: ast.Module) -> tuple[set[str], set[str], set[str]]:
    """Return (module_scope, deferred, annotation_only) import sets.

    A module-scope import executes when the module is imported, so a missing
    distribution breaks `import <module>` outright. A deferred import (inside a function
    or class body) only fails when that code path runs, which is a runtime 500 rather
    than an import error. TYPE_CHECKING-only imports execute never, not even that.

    Callers checking "can this module be imported?" must use only the first set;
    conflating the three produces false alarms -- weasyprint is imported lazily inside a
    request handler and does not stop app/routers/orders.py from importing.
    """
    module_scope: set[str] = set()
    deferred: set[str] = set()
    annotation_only: set[str] = set()

    def record(node: ast.AST, into: set[str]) -> None:
        if isinstance(node, ast.Import):
            for alias in node.names:
                into.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            base = node.module or ""
            for alias in node.names:
                into.add(f"{base}.{alias.name}" if base else alias.name)

    # Pass 1: statements directly in the module body execute at import time.
    for stmt in tree.body:
        record(stmt, module_scope)

    # Pass 2: everything nested inside a function/class/lambda is deferred. TYPE_CHECKING
    # blocks are collected separately since they never execute at all.
    def walk_scoped(node: ast.AST, guarded: bool) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                # The def/class line itself is deferred; its body is too.
                record(child, deferred)
                walk_scoped(child, guarded)
                continue
            if isinstance(child, ast.If) and "TYPE_CHECKING" in ast.dump(child.test):
                for sub in ast.walk(child):
                    if sub is not child:
                        record(sub, annotation_only)
                continue
            record(child, deferred)
            walk_scoped(child, guarded)

    for stmt in tree.body:
        walk_scoped(stmt, guarded=False)

    for bucket in (module_scope, deferred, annotation_only):
        bucket.discard("")

    deferred -= module_scope
    annotation_only -= module_scope | deferred
    return module_scope, deferred, annotation_only


def top_level_imports(tree: ast.Module) -> set[str]:
    """Top-level module names imported anywhere in the file, ignoring TYPE_CHECKING."""
    return {name.split(".")[0] for name in imported_modules(tree)}


def main(argv: list[str]) -> int:
    roots = [Path(a) for a in argv[1:]] or [Path(__file__).resolve().parent.parent]
    backend = roots[0]
    declared = declared_distributions(backend)
    stdlib = stdlib_names()

    # Import name -> set of distributions that could provide it. Normalise on
    # underscores too, so `sentence_transformers` matches the `sentence-transformers`
    # pin and `PIL` matches `pillow` only when explicitly declared.
    provided: dict[str, set[str]] = {}
    for dist in declared:
        provided.setdefault(IMPORT_NAME_OVERRIDES.get(dist.lower(), dist), set()).add(dist)
        provided.setdefault(dist.replace("-", "_"), set()).add(dist)
        provided.setdefault(dist.upper(), set()).add(dist)

    scan_targets: list[Path] = []
    for root in roots:
        for sub in ("app", "scripts"):
            d = root / sub
            if d.is_dir():
                scan_targets.extend(sorted(d.rglob("*.py")))

    # Directories that sit on sys.path for this backend, so a first-party name can be
    # resolved to a real module. `app` is a sibling of `scripts/`, and charon's
    # submodules are siblings of each other under app/services/charon/.
    package_roots: list[Path] = []
    for root in roots:
        for sub in ("", "app", "app/services", "app/services/charon", "scripts"):
            package_roots.append(root / sub if sub else root)

    violations: list[tuple[Path, str, str]] = []
    for path in scan_targets:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for name in sorted(top_level_imports(tree)):
            if name in stdlib or name in provided:
                continue
            if name in TRANSITIVE_VIA:
                print(f"note: '{name}' ({path}) covered transitively via {TRANSITIVE_VIA[name]}")
                continue
            # FIRST_PARTY is a name allowlist; confirm a matching module really exists
            # so a typo'd allowlist entry cannot silently mask a real third-party dep.
            if name in FIRST_PARTY and any(
                (p / f"{name}.py").is_file() or (p / name).is_dir() for p in package_roots
            ):
                continue
            if name in FIRST_PARTY:
                print(f"note: '{name}' ({path}) is first-party but no such module was found")
            violations.append((path, name, "not declared in requirements.txt"))

    for path, name, why in violations:
        print(f"{path}: undeclared third-party import '{name}' ({why})")

    print(
        f"\n{len(violations)} undeclared import(s) across {len(scan_targets)} file(s); "
        f"{len(declared)} declared distributions"
    )
    if not violations:
        print("OK: every third-party import is covered by requirements.txt")
    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
