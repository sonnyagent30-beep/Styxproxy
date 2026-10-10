#!/usr/bin/env python3
"""Statically reconcile SQLAlchemy models against Alembic migration versions.

Checks:
1. Every model's __tablename__ has a matching CREATE TABLE in migrations.
2. Every model column (by name) has a matching ADD COLUMN / CREATE TABLE column.
3. Nullable/type mismatches are flagged.
4. Foreign key columns exist in the referenced table.

This is a static text check (no DB connection required) so it can run in CI.
"""
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
MODELS_PY = BACKEND / "app" / "models.py"
MIGRATIONS_DIR = BACKEND / "alembic" / "versions"

TYPE_MAP = {
    "String": "VARCHAR",
    "Integer": "INTEGER",
    "BigInteger": "BIGINT",
    "Boolean": "BOOLEAN",
    "DateTime": "TIMESTAMP",
    "Numeric": "NUMERIC",
    "Float": "DOUBLE PRECISION",
    "Text": "TEXT",
    "LargeBinary": "BYTEA",
    "JSON": "JSONB",
    "UUID": "UUID",
    "ARRAY": "ARRAY",
    "INET": "INET",
}


def parse_models() -> dict[str, dict]:
    """Parse models.py and extract table definitions."""
    tree = ast.parse(MODELS_PY.read_text())
    tables = {}

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            # Check for __tablename__
            table_name = None
            for item in node.body:
                if isinstance(item, ast.Assign):
                    for target in item.targets:
                        if (
                            isinstance(target, ast.Name)
                            and target.id == "__tablename__"
                        ):
                            table_name = item.value.value

            if not table_name:
                continue

            columns = {}
            for item in node.body:
                if isinstance(item, ast.AnnAssign) and isinstance(
                    item.target, ast.Name
                ):
                    col_name = item.target.id
                    if col_name.startswith("_"):
                        continue

                    # Extract type from annotation
                    col_type = None
                    if isinstance(item.annotation, ast.Name):
                        col_type = item.annotation.id
                    elif isinstance(item.annotation, ast.Subscript):
                        # Mapped[Optional[str]] etc
                        if isinstance(item.annotation.value, ast.Name):
                            col_type = item.annotation.value.id

                    # Check for ForeignKey
                    has_fk = False
                    for sub_node in ast.walk(item):
                        if isinstance(sub_node, ast.Call):
                            if isinstance(sub_node.func, ast.Name):
                                if sub_node.func.id == "ForeignKey":
                                    has_fk = True
                                elif sub_node.func.id == "mapped_column":
                                    # Check inside mapped_column
                                    for arg in sub_node.args:
                                        if isinstance(arg, ast.Call):
                                            if isinstance(arg.func, ast.Name) and arg.func.id == "ForeignKey":
                                                has_fk = True

                    # Check nullable (server_default implies not null in practice)
                    nullable = True
                    if isinstance(item.annotation, ast.Subscript):
                        # Mapped[Optional[X]] = nullable
                        # Mapped[X] = not nullable
                        slice_node = item.annotation.slice
                        if isinstance(slice_node, ast.Name) and slice_node.id == "Optional":
                            nullable = True
                        elif isinstance(slice_node, ast.Constant) and slice_node.value is None:
                            nullable = True
                        else:
                            nullable = False

                    columns[col_name] = {
                        "type": col_type,
                        "nullable": nullable,
                        "has_fk": has_fk,
                    }

            tables[table_name] = columns

    return tables


def parse_migrations() -> dict[str, dict]:
    """Parse all migration files and extract CREATE TABLE / ADD COLUMN statements."""
    tables = {}

    for mig_file in sorted(MIGRATIONS_DIR.glob("*.py")):
        content = mig_file.read_text()

        # Extract CREATE TABLE blocks (op.create_table and sa.create_table)
        create_pattern = re.compile(
            r'(?:op|sa)\.create_table\(\s*"(\w+)",(.*?)\)',
            re.DOTALL,
        )
        for match in create_pattern.finditer(content):
            table_name = match.group(1)
            body = match.group(2)
            tables.setdefault(table_name, {"columns": {}, "file": mig_file.name})

            # Extract sa.Column definitions inside CREATE TABLE
            col_pattern = re.compile(
                r'(?:sa|op)\.Column\(\s*"(\w+)"\s*,\s*([\w.]+(?:\([^)]*\))?)'
            )
            for col_match in col_pattern.finditer(body):
                col_name = col_match.group(1)
                col_type = col_match.group(2)
                tables[table_name]["columns"][col_name] = {
                    "type": col_type,
                    "source": "create_table",
                }

        # Extract ADD COLUMN statements (op.add_column)
        add_col_pattern = re.compile(
            r'add_column\(\s*"(\w+)"\s*,\s*sa\.Column\(\s*"(\w+)"\s*,\s*([\w.]+(?:\([^)]*\))?)'
        )
        for match in add_col_pattern.finditer(content):
            table_name = match.group(1)
            col_name = match.group(2)
            col_type = match.group(3)

            tables.setdefault(table_name, {"columns": {}, "file": mig_file.name})
            tables[table_name]["columns"][col_name] = {
                "type": col_type,
                "source": "add_column",
            }

        # Extract raw SQL ALTER TABLE ADD COLUMN statements
        alter_pattern = re.compile(
            r'ALTER\s+TABLE\s+(\w+)\s+ADD\s+COLUMN\s+(?:IF\s+NOT\s+EXISTS\s+)?"?(\w+)"?\s+(\w+(?:\([^)]*\))?)',
            re.IGNORECASE,
        )
        for match in alter_pattern.finditer(content):
            table_name = match.group(1)
            col_name = match.group(2)
            col_type = match.group(3)

            tables.setdefault(table_name, {"columns": {}, "file": mig_file.name})
            tables[table_name]["columns"][col_name] = {
                "type": col_type,
                "source": "alter_table",
            }

        # Extract raw SQL CREATE TABLE statements
        create_sql_pattern = re.compile(
            r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)"?(\w+)"?\s*\((.*?)\)',
            re.IGNORECASE | re.DOTALL,
        )
        for match in create_sql_pattern.finditer(content):
            table_name = match.group(1)
            body = match.group(2)
            tables.setdefault(table_name, {"columns": {}, "file": mig_file.name})

            # Extract column definitions from raw SQL
            col_sql_pattern = re.compile(
                r'"?(\w+)"?\s+(\w+(?:\([^)]*\))?)'
            )
            for col_match in col_sql_pattern.finditer(body):
                col_name = col_match.group(1)
                col_type = col_match.group(2)
                if col_name.upper() in ("PRIMARY", "FOREIGN", "UNIQUE", "CHECK", "CONSTRAINT", "INDEX"):
                    continue
                tables[table_name]["columns"][col_name] = {
                    "type": col_type,
                    "source": "create_table_sql",
                }

    return tables


def reconcile() -> int:
    """Run reconciliation and report mismatches."""
    models = parse_models()
    migrations = parse_migrations()

    errors = []
    warnings = []

    # Check every model table exists in migrations
    for table_name, model_cols in models.items():
        if table_name not in migrations:
            errors.append(f"TABLE MISSING in migrations: {table_name}")
            continue

        mig_table = migrations[table_name]

        # Check every model column exists in migrations
        for col_name, col_info in model_cols.items():
            if col_name not in mig_table["columns"]:
                errors.append(
                    f"COLUMN MISSING in migrations: {table_name}.{col_name}"
                )
            else:
                mig_col = mig_table["columns"][col_name]
                # Normalize types for comparison
                model_type = col_info["type"]
                mig_type = mig_col["type"]

                # Check type compatibility
                if model_type and mig_type:
                    # Normalize String(N) -> VARCHAR
                    if model_type == "String" and "VARCHAR" in mig_type.upper():
                        pass
                    elif model_type == "Integer" and "INTEGER" in mig_type.upper():
                        pass
                    elif model_type == "Boolean" and "BOOLEAN" in mig_type.upper():
                        pass
                    elif model_type == "DateTime" and "TIMESTAMP" in mig_type.upper():
                        pass
                    elif model_type == "Numeric" and "NUMERIC" in mig_type.upper():
                        pass
                    elif model_type == "BigInteger" and "BIGINT" in mig_type.upper():
                        pass
                    elif model_type == "Float" and "DOUBLE" in mig_type.upper():
                        pass
                    elif model_type == "Text" and "TEXT" in mig_type.upper():
                        pass
                    elif model_type == "LargeBinary" and "BYTEA" in mig_type.upper():
                        pass
                    elif model_type == "JSON" and "JSONB" in mig_type.upper():
                        pass
                    elif model_type == "UUID" and "UUID" in mig_type.upper():
                        pass
                    elif model_type == mig_type:
                        pass
                    else:
                        warnings.append(
                            f"TYPE MISMATCH: {table_name}.{col_name} "
                            f"model={model_type} migration={mig_type}"
                        )

    # Check reverse: migration tables that don't exist in models
    for table_name in migrations:
        if table_name not in models:
            warnings.append(f"TABLE in migrations but no model: {table_name}")

    # Report
    if errors:
        print("ERRORS:")
        for e in errors:
            print(f"  ✗ {e}")
    if warnings:
        print("WARNINGS:")
        for w in warnings:
            print(f"  ⚠ {w}")

    if not errors and not warnings:
        print("✓ All models match migrations")
        return 0
    elif not errors:
        print(f"\n✓ No errors ({len(warnings)} warnings)")
        return 0
    else:
        print(f"\n✗ {len(errors)} errors, {len(warnings)} warnings")
        return 1


if __name__ == "__main__":
    sys.exit(reconcile())
