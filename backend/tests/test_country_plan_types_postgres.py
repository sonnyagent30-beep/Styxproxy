"""Prove `country_plan_types` really exists in a database built from this repo.

The unit guards in `test_country_plan_types_schema.py` assert against
SQLAlchemy metadata and the migration source. This file closes the gap by
running `Base.metadata.create_all` against a real PostgreSQL 16 and then
exercising the SQL that the catalog endpoints actually run.

The bug being pinned is the ABSENCE of a table. A mocked session cannot detect
an absent table by construction, so this test uses a real one.

Skipped rather than failed when Postgres is unreachable: the suite must keep
working in a broken environment, which is when a schema guard is most needed.
Run with:

    CPT_TEST_DATABASE_URL=postgresql+asyncpg://user:pw@host/db \
        python3 -m pytest tests/test_country_plan_types_postgres.py
"""
from __future__ import annotations

import os

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.models import Base
from app.services.catalog import (
    ENABLED_COUNTRY_PLAN_TYPES_SQL,
    load_enabled_country_plan_types,
)

_DB_URL = os.environ.get("CPT_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(
    not _DB_URL, reason="set CPT_TEST_DATABASE_URL to run the Postgres round-trip"
)
# Narrowed for the type checker: the skip above means this is a str when used.
DB_URL: str = _DB_URL or ""


@pytest.fixture
async def session():
    """A real session against a table that `create_all` just provisioned.

    This IS the fresh-deploy scenario: an empty database plus the repository's
    own provisioning path, with no hand-written SQL and no production dump.
    """
    engine = create_async_engine(DB_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Start from empty so a leftover row cannot make a query pass by luck.
        await conn.execute(text("DELETE FROM country_plan_types"))
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as s:
        yield s
    await engine.dispose()


async def test_create_all_provisions_the_table(session):
    """Without an ORM model this raises UndefinedTable — the 500 on
    /api/catalog and /api/countries."""
    result = await session.execute(text("SELECT count(*) FROM country_plan_types"))
    assert result.scalar_one() == 0


async def test_the_real_catalog_query_runs_and_honours_enabled(session):
    """The exact SQL both public endpoints depend on, against a real table."""
    await session.execute(text(
        "INSERT INTO country_plan_types (country_code, plan_type, enabled) VALUES"
        " ('NG','DC',true), ('GH','MOBILE',true), ('US','ISP',false)"
    ))
    await session.commit()

    rows = await load_enabled_country_plan_types(session)
    assert {(r["country_code"], r["plan_type"]) for r in rows} == {
        ("NG", "DC"),
        ("GH", "MOBILE"),
    }, "enabled=false rows must not be sellable"

    # The admin upsert's ON CONFLICT DO NOTHING needs this constraint.
    country_codes = {r["country_code"] for r in rows}
    assert "US" not in country_codes


async def test_is_special_is_readable_by_default(session):
    """`is_special` was listed in docs/STAGING-WORKFLOW-PLAN.md as a missing
    column. It exists on prod and in the model; reading it must not fail."""
    await session.execute(text(
        "INSERT INTO country_plan_types (country_code, plan_type, enabled, is_special)"
        " VALUES ('GB','RESIDENTIAL',true,true)"
    ))
    await session.commit()
    rows = await session.execute(ENABLED_COUNTRY_PLAN_TYPES_SQL)
    assert rows.mappings().one()["is_special"] is True


async def test_duplicate_country_plan_type_is_rejected(session):
    """`cpt_unique` must be a real constraint, not just a name."""
    await session.execute(text(
        "INSERT INTO country_plan_types (country_code, plan_type) VALUES ('NG','DC')"
    ))
    await session.commit()
    with pytest.raises(IntegrityError):
        await session.execute(text(
            "INSERT INTO country_plan_types (country_code, plan_type) VALUES ('NG','DC')"
        ))


async def test_admin_upsert_shape_is_accepted(session):
    """Replay the admin router's bootstrap INSERT verbatim. It relies on a
    unique constraint existing for the bare ON CONFLICT clause to bind to."""
    await session.execute(text(
        "INSERT INTO country_plan_types (country_code, plan_type, enabled) "
        "SELECT CAST('NG' AS varchar), pt, false FROM (VALUES ('DC'),('ISP'),"
        "('RESIDENTIAL'),('MOBILE')) AS v(pt) "
        "WHERE NOT EXISTS (SELECT 1 FROM country_plan_types cpt "
        "WHERE cpt.country_code = CAST('NG' AS varchar) AND cpt.plan_type = pt)"
    ))
    await session.commit()
    result = await session.execute(
        text("SELECT plan_type FROM country_plan_types ORDER BY plan_type")
    )
    assert [r[0] for r in result] == ["DC", "ISP", "MOBILE", "RESIDENTIAL"]

    # And it must be safe to run twice.
    await session.execute(text(
        "INSERT INTO country_plan_types (country_code, plan_type, enabled) "
        "SELECT CAST('NG' AS varchar), pt, false FROM (VALUES ('DC'),('ISP'),"
        "('RESIDENTIAL'),('MOBILE')) AS v(pt) "
        "WHERE NOT EXISTS (SELECT 1 FROM country_plan_types cpt "
        "WHERE cpt.country_code = CAST('NG' AS varchar) AND cpt.plan_type = pt)"
    ))
    await session.commit()
    result = await session.execute(
        text("SELECT plan_type FROM country_plan_types ORDER BY plan_type")
    )
    assert len(result.fetchall()) == 4, "the bootstrap INSERT created duplicates"


async def test_production_index_names_are_present(session):
    """The names must match prod so a fresh DB is not a second, divergent one."""
    result = await session.execute(text(
        "SELECT indexname FROM pg_indexes WHERE tablename='country_plan_types'"
    ))
    names = {r[0] for r in result}
    assert {"cpt_unique", "idx_cpt_enabled", "idx_cpt_plan_type"} <= names, (
        f"missing production index names: {names}"
    )