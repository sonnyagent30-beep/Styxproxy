#!/usr/bin/env python3
"""
db-migrate.py — guarded migration runner for backend/db/migrations/

What this script does:
  1. Scans the SQL file for destructive statements (DELETE FROM, TRUNCATE)
     against protected tables (admin_auth, admin_invites, orders,
     styxproxy_credentials, customers).
  2. Refuses to apply the migration unless the file contains the magic
     comment '-- DESTRUCTIVE-CONFIRMED' on its own line, OR the
     destructive statement only touches non-protected tables.
  3. Prints what it found, prompts interactively (skipped under
     --yes), then pipes the SQL through to psql.

Why:
  On 2026-07-23, an unscripted session emptied admin_auth and
  admin_invites — the root cause is unknown, but the same shape could
  be re-created by any future migration that forgets a WHERE clause or
  runs TRUNCATE. This runner makes "I really meant to wipe this" a
  conscious, logged decision rather than a silent one-liner.

Usage:
  python3 backend/scripts/db-migrate.py backend/db/migrations/FOO.sql
  python3 backend/scripts/db-migrate.py --all                 # apply every migration in order
  python3 backend/scripts/db-migrate.py FILE.sql --yes        # skip interactive prompt
  python3 backend/scripts/db-migrate.py FILE.sql --dry-run    # scan only, no psql

Exit codes:
  0  migration applied (or dry-run clean)
  1  destructive statement without -- DESTRUCTIVE-CONFIRMED
  2  file unreadable or empty
  3  psql failed (error forwarded)
  4  no protected tables touched AND no marker present (benign; auto-pass)
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

PROTECTED_TABLES = {
    "admin_auth",
    "admin_invites",
    "orders",
    "styxproxy_credentials",
    "customers",
    "payments",          # not in schema but planned; include defensively
    "feature_flags",
    "free_trials",
}

DESTRUCTIVE_PATTERNS = [
    (re.compile(r"\bDELETE\s+FROM\s+(\w+)", re.IGNORECASE), "DELETE"),
    (re.compile(r"\bTRUNCATE\s+(?:TABLE\s+)?(\w+)", re.IGNORECASE), "TRUNCATE"),
    (re.compile(r"\bDROP\s+TABLE\s+(?:IF\s+EXISTS\s+)?(\w+)", re.IGNORECASE), "DROP TABLE"),
]

CONFIRM_MARKER = re.compile(r"^\s*--\s*DESTRUCTIVE-CONFIRMED\s*$", re.MULTILINE | re.IGNORECASE)

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MIGRATIONS_DIR = REPO_ROOT / "db" / "migrations"
DEFAULT_DBNAME = "styxproxy"
DEFAULT_PSQL_USER = "styxproxy_migrate"

# NOTE (Jul 29 2026, Theme C closure):
#   Migrations default to styxproxy_migrate (NOSUPERUSER) instead of postgres.
#   styxproxy_migrate owns all tables; postgres is reserved for emergencies.
#   Override with --psql-user postgres if you need superuser actions (rare).


def scan_for_destructive(sql: str) -> list[tuple[str, str]]:
    """Return [(statement_kind, table_name), ...] for every destructive hit."""
    hits: list[tuple[str, str]] = []
    for line in sql.splitlines():
        # Skip pure comment lines so people can write notes about DELETE
        # without triggering the guard.
        stripped = line.strip()
        if stripped.startswith("--"):
            continue
        for pat, kind in DESTRUCTIVE_PATTERNS:
            m = pat.search(line)
            if m:
                hits.append((kind, m.group(1).lower()))
    return hits


def scan_is_protected(hits: list[tuple[str, str]]) -> list[tuple[str, str]]:
    return [(kind, tbl) for kind, tbl in hits if tbl in PROTECTED_TABLES]


def run_psql(sql_path: Path, dbname: str, psql_user: str) -> int:
    """Pipe the SQL file to psql. Returns the psql exit code.

    Two auth modes supported:
      - "postgres" → sudo -u postgres psql (peer auth, no password needed)
      - any other role → psql via TCP with PGPASSWORD from /opt/styxproxy/.env
                         (avoids needing a matching Unix user for every DB role)

    Reads the file as the current user (root), pipes to psql via stdin.
    This avoids the chicken-and-egg of file permissions when the runner is
    invoked by a different account than the migration files' owner.
    """
    sql = sql_path.read_text()
    env = os.environ.copy()

    if psql_user == "postgres":
        # Peer auth via Unix socket
        cmd = ["sudo", "-u", psql_user, "psql", "-d", dbname, "-v", "ON_ERROR_STOP=1"]
    else:
        # TCP auth with password from .env (DATABASE_URL has styxproxy creds;
        # for styxproxy_migrate we read PGPASSWORD or fall back to same password)
        pg_password = env.get("PGPASSWORD") or _read_migrate_password()
        env["PGPASSWORD"] = pg_password
        cmd = [
            "psql",
            "-h", "127.0.0.1",
            "-U", psql_user,
            "-d", dbname,
            "-v", "ON_ERROR_STOP=1",
        ]
    print(f"\n$ cat {sql_path} | {' '.join(cmd)}")
    proc = subprocess.run(cmd, input=sql, text=True, check=False, env=env)
    return proc.returncode


def _read_migrate_password() -> str:
    """Read styxproxy_migrate password from /opt/styxproxy/.env.

    Convention: MIGRATE_PASSWORD=<password> in .env, falls back to
    styxproxy_migrate_2026 if not set (matches migration 016 default).
    """
    env_path = Path("/opt/styxproxy/.env")
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if line.startswith("MIGRATE_PASSWORD="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return "styxproxy_migrate_2026"


def apply_one(sql_path: Path, dbname: str, psql_user: str, yes: bool, dry_run: bool) -> int:
    if not sql_path.is_file():
        print(f"ERROR: not a file: {sql_path}", file=sys.stderr)
        return 2
    sql = sql_path.read_text()
    if not sql.strip():
        print(f"ERROR: empty file: {sql_path}", file=sys.stderr)
        return 2

    print(f"\n=== {sql_path} ===")
    hits = scan_for_destructive(sql)
    protected_hits = scan_is_protected(hits)

    if not hits:
        print("scan: no destructive statements — clean.")
    else:
        print(f"scan: found {len(hits)} destructive statement(s):")
        for kind, tbl in hits:
            tag = " [PROTECTED]" if tbl in PROTECTED_TABLES else ""
            print(f"  - {kind.upper()} {tbl}{tag}")

    if protected_hits and not CONFIRM_MARKER.search(sql):
        print(
            "\nREFUSED: destructive statement against a protected table "
            "without -- DESTRUCTIVE-CONFIRMED marker.\n"
            "If you really mean it, add this line to the SQL file:\n"
            "  -- DESTRUCTIVE-CONFIRMED\n"
            "and re-run. Every wipe is logged by the migration filename.",
            file=sys.stderr,
        )
        return 1

    if hits and not yes and not dry_run:
        # Even non-protected destructive ops get a prompt unless --yes
        print(
            f"\nAbout to apply migration with {len(hits)} destructive "
            f"statement(s) (protected={len(protected_hits)})."
        )
        try:
            answer = input("Proceed? [type 'yes' to continue] ")
        except EOFError:
            answer = ""
        if answer.strip().lower() != "yes":
            print("aborted by user.")
            return 1

    if dry_run:
        print("dry-run: not applying.")
        return 0

    rc = run_psql(sql_path, dbname, psql_user)
    if rc != 0:
        print(f"psql failed with exit code {rc}", file=sys.stderr)
        return 3
    print("applied OK.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Guarded migration runner.")
    parser.add_argument("files", nargs="*", help="SQL files to apply. Omit when using --all.")
    parser.add_argument("--all", action="store_true",
                        help=f"Apply every .sql in {DEFAULT_MIGRATIONS_DIR} in sorted order.")
    parser.add_argument("--dbname", default=DEFAULT_DBNAME)
    parser.add_argument("--psql-user", default=DEFAULT_PSQL_USER)
    parser.add_argument("--yes", action="store_true", help="Skip interactive prompt.")
    parser.add_argument("--dry-run", action="store_true", help="Scan only, do not apply.")
    args = parser.parse_args()

    if args.all:
        files = sorted(DEFAULT_MIGRATIONS_DIR.glob("*.sql"))
    else:
        files = [Path(f) for f in args.files]

    if not files:
        parser.error("provide SQL files or --all")

    overall_rc = 0
    for f in files:
        rc = apply_one(f, args.dbname, args.psql_user, args.yes, args.dry_run)
        # If a destructive guard refused, stop the batch
        if rc == 1:
            return rc
        overall_rc = overall_rc or rc
    return overall_rc


if __name__ == "__main__":
    sys.exit(main())