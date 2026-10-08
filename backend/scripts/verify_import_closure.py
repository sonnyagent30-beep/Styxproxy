#!/usr/bin/env python3
"""Statically verify that a module's full first-party import closure is installable
from requirements.txt alone.

This is the offline stand-in for `python -c "import app.scripts.fulfillment_worker"`
in a venv built purely from requirements.txt (the acceptance check for t_dbdedd9a).
It cannot run when the package installer is unavailable, but it checks the same
property that matters: every third-party module reachable from the target -- through
first-party modules, including deferred/function-local imports -- is provided by a
distribution declared in requirements.txt.

Deliberately includes function-local and TYPE_CHECKING imports: those are the ones
that hide a missing dependency until a code path runs at runtime (the weasyprint
case), whereas a module-scope import fails loudly at startup.

Usage:
    python scripts/verify_import_closure.py app.scripts.fulfillment_worker
Exit code 1 if the closure references anything requirements.txt does not provide.
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from import_closure_audit import (  # noqa: E402
    FIRST_PARTY,
    IMPORT_NAME_OVERRIDES,
    TRANSITIVE_VIA,
    declared_distributions,
    imported_modules,
    imported_modules_by_scope,
    stdlib_names,
)


def module_to_path(backend: Path, dotted: str) -> Path | None:
    """Resolve `app.services.email` to app/services/email.py, or a package __init__."""
    parts = dotted.split(".")
    candidate = backend.joinpath(*parts).with_suffix(".py")
    if candidate.is_file():
        return candidate
    pkg_init = backend.joinpath(*parts, "__init__.py")
    if pkg_init.is_file():
        return pkg_init
    return None


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__)
        return 2
    target = argv[1]
    backend = Path(__file__).resolve().parent.parent

    declared = declared_distributions(backend)
    stdlib = stdlib_names()
    provided: dict[str, str] = {}
    for dist in declared:
        provided[IMPORT_NAME_OVERRIDES.get(dist.lower(), dist)] = dist
        provided[dist.replace("-", "_")] = dist
        provided[dist] = dist
    for name, via in TRANSITIVE_VIA.items():
        provided.setdefault(name, f"transitive via {via}")

    seen: set[str] = set()
    unresolved: dict[str, list[str]] = {}
    advisory: dict[str, list[str]] = {}
    queue = [target]
    visited_files: set[Path] = set()

    while queue:
        dotted = queue.pop()
        if dotted in seen:
            continue
        seen.add(dotted)
        path = module_to_path(backend, dotted)
        if path is None or path in visited_files:
            continue
        visited_files.add(path)
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        pkg = dotted.rsplit(".", 1)[0] if "." in dotted else dotted
        scope_imports, deferred_imports, _annotation_only = imported_modules_by_scope(tree)

        # Both scopes are followed (a deferred import still runs at request time), but
        # only a module-scope miss breaks `import <module>` -- so only that fails.
        blocking = {n.split(".")[0] for n in scope_imports}

        for name in sorted(imported_modules(tree)):
            head = name.split(".")[0]
            if head in stdlib or head in provided:
                continue
            if head not in FIRST_PARTY:
                bucket = unresolved if head in blocking else advisory
                bucket.setdefault(head, []).append(f"{path.relative_to(backend)}")
                continue
            # first-party: follow it into its own module. `from app.x import y`
            # yields both "app.x" and "app.x.y"; try the longest path that exists.
            parts = name.split(".")
            for i in range(len(parts), 0, -1):
                candidate = ".".join(parts[:i])
                if module_to_path(backend, candidate):
                    queue.append(candidate)
                    break

        # relative imports (level > 0) resolve against the importing package
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.level:
                anchor = pkg.split(".")
                base = ".".join(anchor[: len(anchor) - node.level + 1])
                for alias in node.names:
                    if alias.name != "*":
                        queue.append(f"{base}.{alias.name}")

    print(f"closure of {target}: {len(visited_files)} first-party module(s) reachable")
    for path in sorted(visited_files):
        print(f"  - {path.relative_to(backend)}")

    if advisory:
        print()
        for name, sites in sorted(advisory.items()):
            print(
                f"ADVISORY: '{name}' (deferred import in {', '.join(sorted(set(sites)))}) is not "
                "declared; it does not break module import but will raise at request time"
            )

    if unresolved:
        print()
        for name, sites in sorted(unresolved.items()):
            print(f"UNRESOLVED: '{name}' required at module scope by {', '.join(sorted(set(sites)))}")
        print(f"\n{len(unresolved)} unresolved module-scope import(s)")
        return 1

    print("\nOK: every module-scope third-party import in the closure is declared in requirements.txt")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
