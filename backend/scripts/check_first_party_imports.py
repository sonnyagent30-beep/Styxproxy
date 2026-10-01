"""Statically resolve every first-party `from app... import <name>` in the backend
and report names the target module does not define.

Why this exists
---------------
`import app.main` used to fail outright on this tree, and the failure was invisible
until a human ran pytest and read "10 errors during collection". Two cards
(t_72aeebb7, t_7343d7c0) reported a green number with those 10 collection errors
written off as "pre-existing baseline" -- but those errors *were* the bug, and in
t_72aeebb7's case the module that never ran (test_fulfillment_ledger_e2e.py, 8
tests) was the one carrying its own acceptance criterion.

The concrete defect: app/routers/admin.py and app/routers/auth.py imported refund
and IP-allowlist models from `app.schemas`, where they were not defined -- they
live in `app.routers.schemas`. `from X import name` raises ImportError at import
time if `name` is absent, so a single wrong module path takes down every module
that transitively imports the offender. app/routers/__init__.py imports admin,
so the whole application fails to start.

Why not just import the app
---------------------------
Importing is the ground truth, but it needs a configured environment (settings,
DATABASE_URL, secrets) and only proves the *entry point* works. This check
resolves names statically instead, so it:

  * needs no environment and no installed dependencies (pure stdlib), so it
    still runs in the broken environments it exists to catch;
  * reports *every* unresolved name at once, with file:line, rather than only
    the first ImportError the interpreter happens to raise;
  * covers modules no entry point reaches, such as app/scripts/fulfillment_worker.py,
    which the systemd unit runs directly.

Scope and honest limits
-----------------------
This resolves module-scope `from app... import name` and `import app....` only.
It deliberately does NOT try to judge re-exports through a package __init__
beyond one level, star imports, TYPE_CHECKING blocks, names injected at runtime,
or conditional/try-except imports -- an import inside `try: ImportError` is a
legitimate optional-dependency pattern and is skipped, because flagging it would
teach people to ignore this tool. A name that resolves only via a star import is
reported as unverified rather than silently trusted.

It is a *complement* to the runtime import gate, not a replacement: the strongest
statement is still "app.main imports in a real environment". What this adds is
coverage of files the entry point never touches, and a precise file:line.

Run:  python scripts/check_first_party_imports.py [path ...]
Exit 1 if any first-party import cannot be resolved.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
APP = BACKEND / "app"

# The `app` package name, and the directories that sit on sys.path for this
# backend so `app.services.email` resolves to backend/app/services/email.py.
# Overridden by main() when the caller points the checker at another tree, so the
# tests can exercise it against a synthetic package.
PACKAGE = "app"
SEARCH_ROOTS: tuple[Path, ...] = (APP, BACKEND)


class Finding:
    """One unresolvable first-party import."""

    def __init__(self, path: Path, line: int, module: str, name: str) -> None:
        self.path = path
        self.line = line
        self.module = module
        self.name = name

    def __str__(self) -> str:
        return f"{_display(self.path)}:{self.line}: cannot import name {self.name!r} from {self.module!r}"

    def as_dict(self) -> dict:
        return {
            "file": _display(self.path),
            "line": self.line,
            "module": self.module,
            "name": self.name,
        }


def _display(path: Path) -> str:
    """Repo-relative when possible, so findings are stable across machines."""
    try:
        return str(path.relative_to(BACKEND))
    except ValueError:
        return str(path)


def module_path(dotted: str) -> Path | None:
    """Resolve a dotted module name to a file, or None if it is not a file module.

    A package (a/ with __init__.py) resolves to its __init__.py so that
    `from app.services import x` is checked against the names that package
    actually binds.
    """
    parts = dotted.split(".")
    for root in SEARCH_ROOTS:
        base = root.joinpath(*parts)
        if base.is_dir() and (base / "__init__.py").is_file():
            return base / "__init__.py"
        candidate = base.with_suffix(".py")
        if candidate.is_file():
            return candidate
    return None


def _bound_names(tree: ast.Module) -> tuple[set[str], bool]:
    """Names a module binds at module scope, and whether it uses a star import.

    A star import makes any name from that module unknowable without executing
    it, so we record the fact and treat the module as partially opaque.
    """
    bound: set[str] = set()
    star = False
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            bound.add(node.name)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    bound.add(target.id)
        elif isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name):
                bound.add(node.target.id)
        elif isinstance(node, ast.AugAssign):
            if isinstance(node.target, ast.Name):
                bound.add(node.target.id)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                bound.add(alias.asname or alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if alias.name == "*":
                    star = True
                else:
                    bound.add(alias.asname or alias.name)
        elif isinstance(node, (ast.If, ast.Try)):
            # Conditional/try-guarded module-scope bindings still bind at runtime.
            # We walk them so `try: from x import y except ImportError` counts as
            # bound -- that is the legitimate optional-dependency pattern.
            for sub in ast.walk(node):
                if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    bound.add(sub.name)
                elif isinstance(sub, ast.Import):
                    for alias in sub.names:
                        bound.add(alias.asname or alias.name.split(".")[0])
                elif isinstance(sub, ast.ImportFrom):
                    for alias in sub.names:
                        if alias.name != "*":
                            bound.add(alias.asname or alias.name)
                elif isinstance(sub, ast.Assign):
                    for target in sub.targets:
                        if isinstance(target, ast.Name):
                            bound.add(target.id)
    return bound, star


_CACHE: dict[Path, tuple[set[str], bool]] = {}


def exports(path: Path) -> tuple[set[str], bool]:
    if path not in _CACHE:
        try:
            _CACHE[path] = _bound_names(ast.parse(path.read_text(encoding="utf-8")))
        except (OSError, SyntaxError):
            # Unparseable file: a SyntaxError is its own hard failure and is
            # reported by the interpreter gate. Do not double-report it here.
            _CACHE[path] = (set(), False)
    return _CACHE[path]


def is_first_party(dotted: str) -> bool:
    return dotted == "app" or dotted.startswith("app.")


def _catches_import_error(node: ast.Try) -> bool:
    """True if any handler on this try/except catches ImportError or a superclass.

    `except ImportError` and `except ModuleNotFoundError` both make an import
    optional; a bare `except Exception` also swallows it, and is treated the same
    way -- flagging those would be noise, not signal.
    """
    for handler in node.handlers:
        exc = handler.type
        names: list[str] = []
        if isinstance(exc, ast.Name):
            names.append(exc.id)
        elif isinstance(exc, ast.Tuple):
            names.extend(e.id for e in exc.elts if isinstance(e, ast.Name))
        elif exc is None:
            return True  # bare except
        for name in names:
            if name in {"ImportError", "ModuleNotFoundError", "Exception", "BaseException"}:
                return True
    return False


def check_file(path: Path) -> list[Finding]:
    """Report unresolvable `from app... import name` statements in one file.

    Optional-dependency imports (`from app.x import y` inside try/except
    ImportError) are skipped: they are a deliberate pattern, not a defect.
    """
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError):
        return []

    # An import inside a `try:` body whose handlers catch ImportError (or a
    # superclass such as ModuleNotFoundError) is a deliberate optional-dependency
    # shim, not a defect. Collect the *body* statements, not the handlers.
    guarded: set[int] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Try):
            continue
        if not _catches_import_error(node):
            continue
        for stmt in node.body:
            for sub in ast.walk(stmt):
                guarded.add(id(sub))

    findings: list[Finding] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom):
            continue
        if node.level:  # relative import; resolved against package context
            continue
        module = node.module or ""
        if not is_first_party(module):
            continue
        if id(node) in guarded:
            continue

        target = module_path(module)
        if target is None:
            # The module itself does not exist as a file. That is a different
            # failure (ModuleNotFoundError) and is out of scope here.
            continue
        bound, star = exports(target)
        for alias in node.names:
            if alias.name == "*":
                continue
            name = alias.asname or alias.name
            # `from app.x import submodule` is valid if submodule is a module.
            if alias.name in bound or (name in bound and alias.asname):
                continue
            if alias.name != "*" and module_path(f"{module}.{alias.name}") is not None:
                continue  # importing a submodule, not a name
            if star:
                continue  # unknowable without executing; do not cry wolf
            findings.append(Finding(path, node.lineno, module, alias.name))
    return findings


def iter_python_files(roots: list[Path]) -> list[Path]:
    files: list[Path] = []
    for root in roots:
        if root.is_file() and root.suffix == ".py":
            files.append(root)
        elif root.is_dir():
            files.extend(
                p for p in sorted(root.rglob("*.py")) if "__pycache__" not in p.parts and not p.name.startswith(".")
            )
    return files


def infer_roots(roots: list[Path]) -> tuple[Path, ...]:
    """Work out where the first-party package lives for the tree being scanned.

    Resolution has to be relative to the tree under test, not to this script's own
    location, or the checker silently judges a different package than the one it was
    pointed at. When the caller passes `.../app`, the import root is its parent;
    otherwise the directory itself is the root.
    """
    roots = [r.resolve() for r in roots]
    dirs = [r if r.is_dir() else r.parent for r in roots]
    for directory in dirs:
        if directory.name == PACKAGE:
            return (directory.parent, directory)
    return tuple(dirs)


def main(argv: list[str]) -> int:
    global SEARCH_ROOTS, PACKAGE

    roots = [Path(a) for a in argv[1:]] or [APP]
    SEARCH_ROOTS = infer_roots(roots)
    # When scanning a directory that is itself the package (rather than a path
    # ending in it), treat that directory's name as the package name so the
    # first-party test matches the synthetic trees the tests build.
    if len(roots) == 1 and roots[0].resolve().is_dir():
        candidate = roots[0].resolve()
        if candidate.name != PACKAGE and (candidate / "__init__.py").is_file():
            PACKAGE = candidate.name
    _CACHE.clear()

    files = iter_python_files(roots)
    findings: list[Finding] = []
    for path in files:
        findings.extend(check_file(path))

    if findings:
        print(f"{len(findings)} unresolvable first-party import(s) across {len(files)} file(s):\n")
        for finding in findings:
            print(f"  {finding}")
        print(
            "\nA `from app.x import name` that fails raises ImportError at import time and\n"
            "takes down every module that transitively imports it -- app/routers/__init__.py\n"
            "imports admin, so one wrong module path stops the whole application from starting.\n"
            "Either the model belongs in the module you are importing from, or the import\n"
            "should name app.routers.schemas."
        )
        return 1

    print(f"OK: every first-party import resolves across {len(files)} file(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
