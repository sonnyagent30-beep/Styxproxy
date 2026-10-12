"""`country_plan_types` must exist in a database built from this repository.

## The bug this pins

`country_plan_types` is the authoritative definition of what is sellable. It is
read by `app/services/catalog.py`, `app/routers/catalog.py`,
`app/routers/orders.py`, `app/routers/admin.py` and the Charon tools — yet it
had no ORM model in `models.py` and no migration in `alembic/versions/`.
Production had it because it was created out-of-band by hand.

So a fresh environment had no such table and `GET /api/catalog` /
`GET /api/countries` raised `UndefinedTable` (HTTP 500). The pre-existing tests
could not catch this because every one of them fakes the session, so the
table's absence was invisible to the suite.

## Why these tests do not fake anything

The whole failure mode IS the absence of a real table, so a test that mocks the
session cannot detect it by construction. These assert against the SQLAlchemy
`MetaData` (what `create_all` will actually emit) and against the migration
source, and the Postgres file next door proves it end to end.

Skipped rather than failed when Postgres is unreachable: the suite must still
run in a broken environment, which is when a schema guard is most needed.
"""
from __future__ import annotations

import pathlib
import re

import pytest
from sqlalchemy import UniqueConstraint
from sqlalchemy.dialects import postgresql

from app.models import Base, CountryPlanType

REPO_BACKEND = pathlib.Path(__file__).resolve().parents[1]


# ── The authoritative schema, copied from live production ───────────────────
# Captured from `\d+ country_plan_types` on Interserver 162.35.184.69. This is
# a transcription of reality, not a design: a fresh database that disagrees
# with production is exactly the bug in this card.
PROD_COLUMNS = {
    "id": ("integer", False),
    "country_code": ("character varying(2)", False),
    "plan_type": ("character varying(20)", False),
    "enabled": ("boolean", False),
    "price_per_ip": ("numeric(12,2)", True),
    "price_per_gb": ("numeric(12,2)", True),
    "provider_id": ("integer", True),
    "sort_order": ("integer", False),
    "notes": ("text", True),
    "created_at": ("timestamp with time zone", False),
    "updated_at": ("timestamp with time zone", False),
    "is_special": ("boolean", False),
}
PROD_NAMED_INDEXES = {"cpt_unique", "idx_cpt_enabled", "idx_cpt_plan_type"}


# ── 1. The model exists and is wired into create_all ────────────────────────


def test_country_plan_types_is_in_create_all_metadata():
    """`Base.metadata.create_all` is what provisions a fresh DB. No model = no table.

    This is the guard that actually pins the bug: delete the model and this
    fails, which is the pre-fix state.
    """
    assert "country_plan_types" in Base.metadata.tables, (
        "country_plan_types is not in Base.metadata, so create_all will not "
        "create it and every catalog endpoint raises UndefinedTable"
    )


def test_country_plan_type_model_declares_the_production_columns():
    """Every column prod has, no column prod lacks — a typo'd name here is a
    runtime UndefinedColumn on prod-shaped data."""
    table = CountryPlanType.__table__
    assert set(table.columns.keys()) == set(PROD_COLUMNS), (
        f"column set differs from production: "
        f"only-in-model={set(table.columns.keys()) - set(PROD_COLUMNS)}, "
        f"only-in-prod={set(PROD_COLUMNS) - set(table.columns.keys())}"
    )


@pytest.mark.parametrize("column", sorted(PROD_COLUMNS))
def test_column_type_and_nullability_match_production(column):
    """`varchar(2)` vs bare `varchar` matters: prod truncates at 2, a fresh DB
    would not, so the two databases would disagree about what a country code is.

    Case is normalised because the two sources case differently: SQLAlchemy
    renders DDL-canonical uppercase (`VARCHAR(2)`) while psql's `format_type`
    returns lowercase (`character varying(2)`). The typmod — the part that
    carries meaning — is compared exactly.
    """
    col = CountryPlanType.__table__.columns[column]
    rendered = col.type.compile(dialect=postgresql.dialect())
    expected_type, nullable = PROD_COLUMNS[column]

    def normalise(s: str) -> str:
        # The two sources spell the same types differently: SQLAlchemy renders
        # DDL-canonical uppercase (`VARCHAR(2)`, `NUMERIC(12, 2)`) with the SQL
        # keyword and a space after the comma, while psql's format_type returns
        # the catalog spelling (`character varying(2)`, `numeric(12,2)`) in
        # lowercase and without the space. None of that is semantic.
        s = s.lower().replace(" ", "")
        return s.replace("charactervarying", "varchar").replace(
            "timestampwithtimezone", "timestamptz"
        )

    assert normalise(rendered) == normalise(expected_type), (
        f"{column}: model declares {rendered!r}, production has {expected_type!r}"
    )
    assert col.nullable is nullable, (
        f"{column}: model nullable={col.nullable}, production nullable={nullable}"
    )


def test_cpt_unique_constraint_exists_by_name():
    """`cpt_unique` is load-bearing: `routers/admin.py` upserts with a bare
    `ON CONFLICT DO NOTHING`, which needs a unique constraint on
    (country_code, plan_type) to resolve to."""
    constraints = {
        c.name: tuple(col.name for col in c.columns)
        for c in CountryPlanType.__table__.constraints
        if isinstance(c, UniqueConstraint)
    }
    assert constraints.get("cpt_unique") == ("country_code", "plan_type"), (
        f"cpt_unique missing or wrong; found {constraints}"
    )


def test_production_index_names_are_declared_explicitly():
    """create_all would otherwise emit `ix_country_plan_types_*` and leave
    prod's `idx_cpt_*` as a second, divergent set of index names.

    `cpt_unique` is a UniqueConstraint rather than an Index in the model, but
    Postgres materialises a unique constraint AS an index — which is why it
    shows up in pg_indexes on prod and in the fresh database alike. Both are
    therefore collected here.
    """
    table = CountryPlanType.__table__
    names = {i.name for i in table.indexes}  # type: ignore[attr-defined]
    names |= {c.name for c in table.constraints}  # type: ignore[attr-defined]
    assert PROD_NAMED_INDEXES <= names, (
        f"missing production index names: {PROD_NAMED_INDEXES - names}"
    )


@pytest.mark.parametrize(
    "column,expected",
    [("enabled", "false"), ("sort_order", "0"), ("is_special", "false")],
)
def test_not_null_columns_carry_their_production_server_default(column, expected):
    """A Python-side `default=` alone is not a server default: a row inserted by
    raw SQL, a seed script, or another service would get NULL and violate NOT
    NULL. The bootstrap INSERTs in `routers/admin.py` are exactly that case."""
    col = CountryPlanType.__table__.columns[column]
    assert col.server_default is not None, (
        f"{column} has no server_default, so a non-ORM insert violates NOT NULL"
    )
    assert expected in str(col.server_default.arg), (
        f"{column} server_default is {col.server_default.arg!r}, expected {expected!r}"
    )


# ── 2. The migration exists, is idempotent, and does not fork a head ────────

MIGRATION = REPO_BACKEND / "alembic" / "versions" / "20261001_country_plan_types.py"


@pytest.fixture(scope="module")
def migration_source() -> str:
    assert MIGRATION.exists(), (
        f"{MIGRATION.name} is missing — a migration-based restore would have no "
        f"country_plan_types table"
    )
    return MIGRATION.read_text()


def test_migration_exists(migration_source):
    assert "CREATE TABLE IF NOT EXISTS country_plan_types" in migration_source


def test_migration_is_idempotent(migration_source):
    """Prod already has the table with 64 rows. `IF NOT EXISTS` is what keeps a
    re-run a no-op instead of an error."""
    assert "CREATE TABLE IF NOT EXISTS" in migration_source
    assert "CREATE UNIQUE INDEX IF NOT EXISTS" in migration_source
    assert "CREATE INDEX IF NOT EXISTS" in migration_source
    assert re.search(r"CREATE TABLE (?!IF NOT EXISTS)", migration_source) is None


def test_migration_does_not_drop_the_table_on_downgrade(migration_source):
    """A `DROP TABLE` rollback would destroy the rows that define what is
    sellable and turn a rollback into a full catalog outage.

    Comments are stripped first: this file's own prose explains why the drop is
    deliberately absent, and a bare substring search would match that
    explanation and report the safe code as unsafe.
    """
    downgrade = migration_source.split("def downgrade")[1]
    code = re.sub(r"#.*", "", downgrade)  # drop comments
    code = re.sub(r'""".*?"""', "", code, flags=re.S)  # and docstrings
    assert "DROP TABLE" not in code.upper(), (
        "downgrade() drops country_plan_types — that destroys live catalog data"
    )


def test_migration_appends_to_the_existing_head():
    """A second alembic head makes `alembic upgrade head` refuse to run at all.

    The parent is the current single head, `20261001_refund_gateway_evidence`.

    Heads are computed with alembic's OWN resolver rather than by hand. A
    hand-rolled scan that reads `down_revision` as a single string gets the
    tuple-valued merge revision (`20260819_merge_three_heads`) wrong and then
    reports six phantom heads — a guard that cries wolf on a healthy graph.
    """
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    script = ScriptDirectory.from_config(Config(str(REPO_BACKEND / "alembic.ini")))
    heads = list(script.get_heads())
    assert heads == ["20261001_country_plan_types"], (
        f"expected exactly one alembic head, got {heads}"
    )
    # And the new revision must hang off the previous single head.
    rev = script.get_revision("20261001_country_plan_types")
    assert rev.down_revision == "20261001_refund_gateway_evidence", (
        f"unexpected down_revision: {rev.down_revision!r}"
    )