"""Scan for NameError-by-construction: names a function reads but never binds in
any enclosing scope, and that are not defined at module level or as builtins —
i.e. code guaranteed to raise NameError the first time that line executes.

Built on CPython's `symtable`, so closures and nested scopes resolve correctly.
This catches what ruff F821 alone does not: F821 is per-scope, so a closure
variable defined in a sibling branch can mask a genuinely undefined name.

Run:  python scripts/ast_undeclared_name_scan.py [path ...]
Exit code 1 if any runtime NameError-by-construction is found.

Reported severities:
  NameError       - a value read that is bound nowhere (guaranteed runtime crash)
  annotation-only - undefined name used solely in an annotation (no runtime error
                    in a function body, but still an undefined reference)
"""
from __future__ import annotations

import ast
import builtins
import symtable
import sys
from pathlib import Path

BUILTINS = frozenset(dir(builtins)) | {
    "__file__",
    "__name__",
    "__doc__",
    "__package__",
    "__spec__",
    "__loader__",
    "__builtins__",
}

# symtable synthesises this pseudo-symbol for `from __future__ import annotations`;
# it is never a real runtime lookup.
IMPLICIT = frozenset({"__conditional_annotations__"})


def _annotation_only_names(tree: ast.Module) -> set[str]:
    """Names that appear only inside annotations (not evaluated in a function body)."""
    annotation_nodes: set[int] = set()
    for node in ast.walk(tree):
        subs: list[ast.AST] = []
        if isinstance(node, ast.arg) and node.annotation is not None:
            subs.append(node.annotation)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.returns is not None:
            subs.append(node.returns)
        elif isinstance(node, ast.AnnAssign):
            subs.append(node.annotation)
        for sub in subs:
            for inner in ast.walk(sub):
                annotation_nodes.add(id(inner))

    runtime_loads = {
        id(n) for n in ast.walk(tree) if isinstance(n, ast.Name) and id(n) not in annotation_nodes
    }
    only_annotations = {
        n.id
        for n in ast.walk(tree)
        if isinstance(n, ast.Name) and id(n) in annotation_nodes and id(n) not in runtime_loads
    }
    return only_annotations


def _first_use_line(source_lines: list[str], name: str) -> int:
    """Best-effort line of the offending read; symtable carries no line info."""
    for lineno, line in enumerate(source_lines, start=1):
        stripped = line.strip()
        if name not in stripped:
            continue
        if stripped.startswith(("def ", "async def ", "class ", "import ", "from ")):
            continue
        return lineno
    return 0


def scan_source(source: str, filename: str) -> list[tuple[int, str, str, str]]:
    """Return sorted (lineno, scope_path, severity, name) findings."""
    tree = ast.parse(source, filename=filename)
    ann_only = _annotation_only_names(tree)
    source_lines = source.splitlines()

    top = symtable.symtable(source, filename, "exec")
    module_names = {s.get_name() for s in top.get_symbols() if s.is_assigned() or s.is_imported()}

    findings: set[tuple[int, str, str, str]] = set()

    def walk(table: symtable.SymbolTable, path: str, enclosing: frozenset[str]) -> None:
        local: set[str] = set(enclosing)
        unresolved: list[str] = []
        for sym in table.get_symbols():
            name = sym.get_name()
            if sym.is_local():
                local.add(name)
            elif sym.is_free():
                # bound in an enclosing function scope -> inherit it
                local.add(name)
            elif sym.is_global() or sym.is_namespace():
                unresolved.append(name)

        for name in unresolved:
            if name in local or name in module_names or name in BUILTINS or name in IMPLICIT:
                continue
            severity = "annotation-only" if name in ann_only else "NameError"
            findings.add((_first_use_line(source_lines, name), path or "<module>", severity, name))

        for child in table.get_children():
            child_path = f"{path}.{child.get_name()}" if path else child.get_name()
            walk(child, child_path, frozenset(local))

    walk(top, "", frozenset())
    return sorted(findings)


def main(argv: list[str]) -> int:
    roots = argv[1:] or ["app/services/email.py"]
    paths: list[Path] = []
    for raw in roots:
        p = Path(raw)
        paths.extend(sorted(p.rglob("*.py")) if p.is_dir() else [p])

    hard = 0
    soft = 0
    for path in paths:
        source = path.read_text(encoding="utf-8")
        for lineno, scope, severity, name in scan_source(source, str(path)):
            if severity == "NameError":
                hard += 1
            else:
                soft += 1
            print(f"{path}:{lineno}: [{severity}] {scope} references undefined name '{name}'")

    print(f"\n{hard} runtime NameError-by-construction, {soft} annotation-only, across {len(paths)} file(s)")
    return 1 if hard else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
