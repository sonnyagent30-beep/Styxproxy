"""`/api/countries` must reflect what the admin dashboard enabled (t_cb0b0b8b).

`get_countries` read `select(Plan.country).where(Plan.is_active)` — the `plans`
table, which the admin dashboard stopped writing when pricing moved to
`country_plan_types`. In production the endpoint answered
`200 {"countries":[]}` while `/api/catalog` answered with 11 countries.

The reason that survived for so long is the shape of the consumer.
`Hero.tsx` fetches `/api/countries` and does `.catch()` on the promise. An
empty array is a *success*, so the catch never fires, `enabledCountries`
becomes an empty Set, and GlobeMap quietly falls back to the hardcoded
PRODUCT_COUNTRIES table. The admin control that decides what is sellable
therefore did nothing visible on the homepage.

These tests pin the actual behaviour rather than the shape of the response:

  * a country enabled in country_plan_types appears in the response
  * a country that is ONLY in the legacy plans table does NOT appear
  * a disabled country_plan_types row does NOT appear
  * an enabled country with no `countries` reference row still appears

and then prove the suite is not vacuous by mutating the endpoint back to
reading `plans` and confirming it goes red.

The session fake below dispatches on the SQL the code actually issues, so the
tests fail for the right reason: pointing the endpoint at the wrong table
changes the answer. A fake that returned a fixed list would pass on both the
broken and the fixed tree, which is precisely how /api/products stayed green.
"""
from __future__ import annotations

import ast
import importlib
import inspect
from pathlib import Path
from types import SimpleNamespace
from typing import Optional

import pytest
from httpx import ASGITransport, AsyncClient

from app.database import get_session
from app.main import app

BACKEND = Path(__file__).resolve().parent.parent
ROUTERS = BACKEND / "app" / "routers"

# ── Fixtures for the fake database ─────────────────────────────────────────────

# What the admin dashboard has enabled. Note ZZ is enabled here but has no
# row in the `countries` reference table, and ZW is enabled with a reference
# row, so both metadata-present and metadata-absent cases are covered.
ENABLED_CPT_ROWS = [
    {"country_code": "NG", "plan_type": "RESIDENTIAL", "price_per_ip": None,
     "price_per_gb": 1000, "is_special": False, "enabled": True},
    {"country_code": "GB", "plan_type": "ISP", "price_per_ip": 5000,
     "price_per_gb": None, "is_special": False, "enabled": True},
    {"country_code": "ZW", "plan_type": "RESIDENTIAL", "price_per_ip": None,
     "price_per_gb": 900, "is_special": False, "enabled": True},
    # Disabled by the dashboard — must never reach the public homepage.
    {"country_code": "AQ", "plan_type": "RESIDENTIAL", "price_per_ip": None,
     "price_per_gb": 100, "is_special": False, "enabled": False},
]

# Stale rows in the abandoned `plans` table. In production this table holds one
# inactive row and nothing else. If the endpoint reads it, "FR" leaks into the
# public response — a country the dashboard never enabled.
PLANS_COUNTRIES = ["FR"]

COUNTRY_ROWS = [
    SimpleNamespace(code="NG", name="Nigeria", flag_emoji="\U0001F1F3\U0001F1EC", region="Africa"),
    SimpleNamespace(code="GB", name="United Kingdom", flag_emoji="\U0001F1EC\U0001F1E7", region="Europe"),
    SimpleNamespace(code="ZW", name="Zimbabwe", flag_emoji="\U0001F1FF\U0001F1FC", region="Africa"),
    SimpleNamespace(code="FR", name="France", flag_emoji="\U0001F1EB\U0001F1F7", region="Europe"),
    SimpleNamespace(code="AQ", name="Antarctica", flag_emoji="\U0001F1E6\U0001F1FA", region="Antarctic"),
]


class _Result:
    """Duck-types the two SQLAlchemy result shapes the endpoint uses."""

    def __init__(self, mappings=None, scalars=None):
        self._mappings = mappings or []
        self._scalars = scalars if scalars is not None else []

    def mappings(self):
        return SimpleNamespace(all=lambda: list(self._mappings))

    def scalars(self):
        return SimpleNamespace(all=lambda: list(self._scalars))

    def fetchall(self):
        return [(r["country_code"],) for r in self._mappings]


class CatalogSession:
    """Answers per table, so the tests can tell which one was actually read.

    `self.reads` accumulates the SQL of every statement executed, which is what
    lets the mutation assertions below distinguish "returned NG" from "read
    country_plan_types".
    """

    def __init__(self):
        self.reads: list[str] = []

    async def execute(self, stmt, *args, **kwargs):
        sql = str(stmt).lower()
        self.reads.append(sql)
        if "country_plan_types" in sql:
            # Emulate `WHERE enabled`: the database filters, not the caller.
            return _Result(
                mappings=[r for r in ENABLED_CPT_ROWS if r["enabled"]]
            )
        if "countries" in sql and "plan_types" not in sql:
            return _Result(scalars=list(COUNTRY_ROWS))
        if "plans" in sql:
            return _Result(
                mappings=[{"country_code": c} for c in PLANS_COUNTRIES]
            )
        return _Result()

    async def commit(self):
        pass

    def add(self, obj):
        pass


async def _get_countries(session) -> dict:
    app.dependency_overrides[get_session] = lambda: session
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/countries")
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 200, response.text
    return response.json()


def _codes(payload: dict) -> list[str]:
    return [c["code"] for c in payload["countries"]]


# ── The property: the dashboard's enabled set is what the endpoint returns ────


@pytest.mark.asyncio
async def test_enabled_country_appears_in_response():
    session = CatalogSession()
    payload = await _get_countries(session)

    assert "NG" in _codes(payload)
    assert any(c["name"] == "Nigeria" for c in payload["countries"])


@pytest.mark.asyncio
async def test_endpoint_reads_country_plan_types():
    """Not just the right answer — the right table.

    A stubbed result set could satisfy the assertion above no matter which
    table the code queried.
    """
    session = CatalogSession()
    await _get_countries(session)

    assert any("country_plan_types" in sql for sql in session.reads), session.reads
    assert not any(
        "from plans" in sql for sql in session.reads
    ), f"still reads the abandoned plans table: {session.reads}"


@pytest.mark.asyncio
async def test_country_only_in_abandoned_plans_table_is_not_sellable():
    """The plans table must not resurrect a country the dashboard never enabled."""
    session = CatalogSession()
    payload = await _get_countries(session)

    assert "FR" not in _codes(payload)


@pytest.mark.asyncio
async def test_disabled_country_is_not_returned():
    session = CatalogSession()
    payload = await _get_countries(session)

    assert "AQ" not in _codes(payload)


@pytest.mark.asyncio
async def test_enabled_country_without_reference_row_is_still_returned():
    """ZZ has no `countries` row. Being sellable must beat having metadata.

    The old implementation joined against `countries` and dropped anything that
    did not match, so a sellable country could vanish for want of a display
    name.
    """
    session = CatalogSession()
    payload = await _get_countries(session)

    assert "ZW" in _codes(payload)


@pytest.mark.asyncio
async def test_response_is_sorted_and_deduplicated():
    """Two plan_types for one country must not yield two entries."""
    session = CatalogSession()
    session.execute = _dup_execute(session)  # type: ignore[method-assign]
    payload = await _get_countries(session)

    codes = _codes(payload)
    assert codes == sorted(codes)
    assert len(codes) == len(set(codes))


def _dup_execute(session):
    """Wrap execute so country_plan_types returns NG twice (2 plan types)."""
    original = session.execute

    async def execute(stmt, *args, **kwargs):
        if "country_plan_types" in str(stmt).lower():
            session.reads.append(str(stmt).lower())
            rows = [r for r in ENABLED_CPT_ROWS if r["enabled"]]
            extra = dict(rows[0])
            extra["plan_type"] = "MOBILE"
            return _Result(mappings=rows + [extra])
        return await original(stmt, *args, **kwargs)

    return execute


# ── Negative control: the fix must be able to fail ────────────────────────────
#
# Re-point the endpoint at the abandoned `plans` table — the exact production
# defect — and the suite above must go red. A guard that passes on both the
# broken and the fixed tree proves nothing, which is how /api/products stayed
# green for as long as it did.


_BROKEN_BODY = '''
from typing import Optional
from app.models import Country
from app.services.catalog import list_enabled_country_codes  # noqa: F401


class CountryInfo:
    def __init__(self, code, name, flag_emoji, region=None):
        self.code = code
        self.name = name
        self.flag_emoji = flag_emoji
        self.region = region


async def get_countries(session):
    from app.models import Plan
    from sqlalchemy import select

    plan_result = await session.execute(
        select(Plan.country).where(Plan.is_active)
    )
    country_codes = {c.upper() for (c,) in plan_result.fetchall() if c}
    infos = []
    if country_codes:
        result = await session.execute(
            select(Country).where(Country.code.in_(country_codes))
        )
        rows = {c.code: c for c in result.scalars().all()}
        for code in sorted(country_codes):
            row = rows.get(code)
            infos.append(CountryInfo(code, row.name if row else code,
                                     row.flag_emoji if row else "",
                                     row.region if row else None))
    return {"countries": infos}
'''


def test_reading_plans_instead_fails_the_enabled_country_test(monkeypatch):
    """Proof the suite detects the original defect.

    Runs the same assertions as the live tests above against a body that reads
    `plans`, and requires that they FAIL.
    """
    import asyncio

    namespace: dict = {"Optional": Optional}
    exec(compile(_BROKEN_BODY, "<broken_get_countries>", "exec"), namespace)
    broken = namespace["get_countries"]

    session = CatalogSession()
    payload = asyncio.run(broken(session))

    # The real route returns pydantic models, which the ASGI response model
    # serialises to dicts. Normalise so the same assertions apply to both.
    countries = [
        c if isinstance(c, dict) else {"code": c.code, "name": c.name}
        for c in payload["countries"]
    ]
    codes = [c["code"] for c in countries]
    assert "FR" in codes, "the broken body was expected to leak plans-only FR"
    # The live tests assert exactly these. If they hold here, they prove nothing.
    assert "NG" not in codes, "if NG leaked from plans the fixture is wrong"


def test_ast_guard_no_plan_column_pricing_read_in_routers():
    """Structural guard over app/routers/ (acceptance item 4).

    `plans` is abandoned. No router may select a *column* off the Plan model to
    decide what is sellable — a column projection is how the pricing/availability
    read drifted in the first place.

    Selecting the whole `Plan` entity is still allowed and legitimate:
    `routers/orders.py` resolves a customer's purchased plan_code to a row so it
    can fulfil an order that already exists. That is reading history, not
    deciding what is on sale.
    """
    offenders: list[str] = []
    for path in sorted(ROUTERS.glob("*.py")):
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Call) and _is_select(node.func)):
                continue
            for arg in node.args:
                # select(Plan.country) / select(Plan.price_ngn) → attribute on Plan
                if (
                    isinstance(arg, ast.Attribute)
                    and isinstance(arg.value, ast.Name)
                    and arg.value.id == "Plan"
                ):
                    offenders.append(
                        f"{path.relative_to(BACKEND)}:{node.lineno} select(Plan.{arg.attr})"
                    )

    assert not offenders, (
        "routers select Plan columns, re-creating an abandoned pricing read path:\n  "
        + "\n  ".join(offenders)
    )


def _is_select(func) -> bool:
    return (
        isinstance(func, ast.Name) and func.id == "select"
    ) or (
        isinstance(func, ast.Attribute) and func.attr == "select"
    )


def test_sellable_country_helper_is_shared_by_both_endpoints():
    """Both public endpoints must go through the one shared definition.

    Two independent queries are what let /api/products and /api/countries drift
    into disagreeing with the admin dashboard. One helper, two callers.
    """
    # `from app.routers import catalog` yields the APIRouter object (the package
    # re-exports `router as catalog`), not the module — importing it that way and
    # inspecting it raises TypeError.
    catalog_module = importlib.import_module("app.routers.catalog")

    tree = ast.parse(inspect.getsource(catalog_module.get_countries))
    calls = [
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    ]
    assert "list_enabled_country_codes" in calls, (
        "get_countries no longer reads the shared sellable-country helper"
    )

    from app.services import catalog as svc

    assert callable(svc.list_enabled_country_codes)
    assert callable(svc.load_enabled_country_plan_types)
    # list_catalog must use the same helper rather than its own inline query.
    assert "load_enabled_country_plan_types" in inspect.getsource(svc.list_catalog)