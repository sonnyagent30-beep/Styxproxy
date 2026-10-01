"""End-to-end: does GET /api/catalog work on a database built from this repo?

This is the acceptance test for t_c072f1e0. Before the fix, a fresh database had
no `country_plan_types` table, so `GET /api/catalog` and `GET /api/countries`
raised UndefinedTable and returned 500.

The app is imported against a real empty database, its own lifespan
(`Base.metadata.create_all`) provisions the schema exactly as a real deploy
does, and both endpoints are then called over HTTP.

No mocking anywhere: the failure mode being pinned is the ABSENCE of a table,
which a mocked session cannot detect by construction.
"""
from __future__ import annotations

import os
import pathlib
import socket
import subprocess
import sys
import time

import httpx
import pytest

DB_NAME = os.environ.get("CPT_E2E_DB", "cpt_e2e")
ADMIN_BASE = f"postgresql://styxproxy:styxproxy@localhost:5432/{DB_NAME}"
ASYNC_URL = f"postgresql+asyncpg://styxproxy:styxproxy@localhost:5432/{DB_NAME}"

pytestmark = pytest.mark.skipif(
    not os.environ.get("CPT_E2E_DATABASE_URL"),
    reason="set CPT_E2E_DATABASE_URL to run the fresh-database endpoint test",
)


def _psql(sql: str) -> None:
    subprocess.run(
        ["sudo", "-u", "postgres", "psql", "-X", "-c", sql],
        check=True, capture_output=True,
    )


@pytest.fixture(scope="module")
def live_app():
    """A uvicorn process on an EMPTY database, provisioned only by the app itself.

    The database is dropped and recreated empty first, so nothing but the
    repository can be responsible for the schema that appears.
    """
    _psql(f'DROP DATABASE IF EXISTS "{DB_NAME}";')
    _psql(f'CREATE DATABASE "{DB_NAME}" OWNER styxproxy;')

    env = dict(os.environ)
    env.update({
        "DATABASE_URL": ASYNC_URL,
        "JWT_SECRET": "test-jwt-secret-not-real-32chars-long",
        "ADMIN_TOKEN": "test-admin-token-not-real",
        "REDIS_URL": "redis://localhost:6379/0",
        "TESTING": "1",
        "FLUTTERWAVE_SECRET_KEY": "test-flw-key",
        "FLUTTERWAVE_WEBHOOK_SECRET": "test-webhook-secret",
        "WHATSAPP_ACCESS_TOKEN": "test-wa-token",
        "WHATSAPP_PHONE_NUMBER_ID": "test-phone-id",
        "MINIMAX_API_KEY": "test-minimax-key",
        "OPS_JWT_SECRET": "test-ops-jwt-secret-not-real-32chars",
        "THEOREM_REACH_WEBHOOK_SECRET": "test-theorem-webhook",
    })

    with socket.socket() as s:  # pick a free port
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]

    base = f"http://127.0.0.1:{port}"
    log = pathlib.Path(__file__).with_name(".fresh_deploy_uvicorn.log")
    with log.open("w") as logf:
        proc = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "app.main:app", "--port", str(port),
             "--host", "127.0.0.1", "--log-level", "warning"],
            env=env, stdout=logf, stderr=subprocess.STDOUT, text=True,
        )
        deadline = time.time() + 90
        while time.time() < deadline:
            if proc.poll() is not None:
                raise RuntimeError(f"uvicorn died:\n{log.read_text()}")
            try:
                if httpx.get(f"{base}/api/v1/health", timeout=2).status_code == 200:
                    break
            except httpx.HTTPError:
                time.sleep(0.5)
        else:
            proc.kill()
            raise RuntimeError(f"app did not become healthy:\n{log.read_text()}")
        yield base
    proc.terminate()
    proc.wait(timeout=20)


def test_country_plan_types_exists_on_a_fresh_database(live_app):
    """The table the app created for itself, with the production schema.

    Depends on `live_app` deliberately: this test reads the database that
    fixture provisions, so it must not run before the app has started.
    """
    out = subprocess.run(
        ["sudo", "-u", "postgres", "psql", "-X", "-d", DB_NAME, "-A", "-t",
         "-c", "SELECT column_name FROM information_schema.columns "
               "WHERE table_name='country_plan_types' ORDER BY ordinal_position"],
        check=True, capture_output=True, text=True).stdout.split()
    assert out == [
        "id", "country_code", "plan_type", "enabled", "price_per_ip", "price_per_gb",
        "provider_id", "sort_order", "notes", "created_at", "updated_at", "is_special",
    ], f"fresh database has the wrong country_plan_types schema: {out}"


def test_catalog_endpoint_does_not_500(live_app):
    """Acceptance: before the fix this raised UndefinedTable and returned 500."""
    r = httpx.get(f"{live_app}/api/catalog", timeout=30)
    assert r.status_code == 200, f"/api/catalog returned {r.status_code}: {r.text[:300]}"
    assert isinstance(r.json(), (list, dict))


def test_countries_endpoint_does_not_500(live_app):
    """Acceptance: the same absent table broke this endpoint too.

    An empty list is a legitimate 200 here (no country is enabled on a fresh
    database) — the point is that it is 200, not 500.
    """
    r = httpx.get(f"{live_app}/api/countries", timeout=30)
    assert r.status_code == 200, f"/api/countries returned {r.status_code}: {r.text[:300]}"
    assert "countries" in r.json()


def test_endpoints_agree_and_reflect_the_table(live_app):
    """Enable a row and prove it becomes sellable end to end.

    This is the control that the endpoints are genuinely reading the table
    rather than merely surviving its absence.
    """
    subprocess.run(
        ["sudo", "-u", "postgres", "psql", "-X", "-d", DB_NAME, "-c",
         "INSERT INTO country_plan_types (country_code, plan_type, enabled) "
         "VALUES ('NG','DC',true) ON CONFLICT DO NOTHING"],
        check=True, capture_output=True)

    r = httpx.get(f"{live_app}/api/countries", timeout=30)
    assert r.status_code == 200
    codes = [c.get("code") for c in r.json()["countries"]]
    assert "NG" in codes, f"enabled NG missing from /api/countries: {codes}"

    r = httpx.get(f"{live_app}/api/catalog", timeout=30)
    assert r.status_code == 200
    assert "NG" in r.text, "enabled NG missing from /api/catalog"


def test_disabling_a_country_removes_it(live_app):
    """The admin control actually works — the defect this table's owner found."""
    subprocess.run(
        ["sudo", "-u", "postgres", "psql", "-X", "-d", DB_NAME, "-c",
         "UPDATE country_plan_types SET enabled=false WHERE country_code='NG'"],
        check=True, capture_output=True)
    r = httpx.get(f"{live_app}/api/countries", timeout=30)
    codes = [c.get("code") for c in r.json()["countries"]]
    assert "NG" not in codes, f"disabled NG still sellable: {codes}"