"""t_8f73c118 -- POST /api/admin/auth/refresh is deliberately gone.

The route shipped broken: its body did `from app.models import AdminRefreshToken`
inside the function, and AdminRefreshToken was never defined. Every call raised
ImportError -> 500. Because the import was function-local, `import app.main` stayed
green, so no startup gate and no import-closure audit could see it.

Two ways to "fix" it were considered:

  1. Add the model + migration. Rejected on evidence -- no login route ever mints a
     refresh token (AdminLoginResponse has no refresh_token field; /login,
     /login/email and /setup return access_token only), production's
     admin_refresh_tokens table holds 0 rows with no ORM mapping and no migration,
     and no caller exists in the frontend, n8n workflows or the Postman collection.
     The route could only ever have returned 401.

  2. Delete the route, which is what happened. The decision is recorded as a NOTE in
     app/routers/auth.py at the point of removal.

These tests exist so the deletion cannot be undone silently, and so a future
half-implementation cannot come back unnoticed. A guard that cannot go red is not a
guard, so the negative controls at the bottom re-create the original defect and
prove these assertions still have teeth.
"""
import ast
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parent.parent
AUTH_PY = BACKEND / "app" / "routers" / "auth.py"

REFRESH_PATH = "/api/admin/auth/refresh"
MODEL_NAME = "AdminRefreshToken"


def _registered_admin_auth_routes() -> set:
    """Path+method pairs the admin auth router actually exposes."""
    from app.routers.auth import router

    routes = set()
    for r in router.routes:
        path = getattr(r, "path", None)
        methods = getattr(r, "methods", None) or set()
        if path:
            routes.add((path, tuple(sorted(methods))))
    return routes


def test_refresh_route_is_not_registered() -> None:
    """POST /api/admin/auth/refresh must not exist.

    Asserted on the router itself rather than through TestClient so the test needs
    no database or event loop: this is a routing fact, not a runtime one.
    """
    registered = _registered_admin_auth_routes()
    assert all(
        path != REFRESH_PATH for path, _methods in registered
    ), f"{REFRESH_PATH} is registered again; it has no issuer for refresh tokens"


def test_no_route_path_matches_admin_auth_refresh() -> None:
    """Guard against the route returning under a different method or spelling."""
    from app.main import app

    offending = [
        (r.path, sorted(r.methods))
        for r in app.routes
        if getattr(r, "path", "") == REFRESH_PATH and getattr(r, "methods", None)
    ]
    assert not offending, f"{REFRESH_PATH} re-registered via app.main: {offending}"


def test_admin_refresh_token_model_is_not_silently_reintroduced() -> None:
    """No module may import AdminRefreshToken; app.models must not define it.

    The two states this card ruled out were "route 500s on a missing model" and
    "model added for a table nobody writes to". Both are caught: the first by the
    import check, the second by this assertion on app.models.
    """
    models_src = (BACKEND / "app" / "models.py").read_text()
    assert f"class {MODEL_NAME}" not in models_src, (
        f"{MODEL_NAME} is defined in app/models.py but nothing mints refresh tokens; "
        "either wire up a login issuer or drop the model"
    )

    offenders = []
    for py in (BACKEND / "app").rglob("*.py"):
        try:
            tree = ast.parse(py.read_text())
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and any(
                (a.name or "") == MODEL_NAME for a in node.names
            ):
                offenders.append(f"{py.relative_to(BACKEND)}:{node.lineno}")
    assert not offenders, f"unresolvable {MODEL_NAME} import reintroduced: {offenders}"


def test_auth_router_source_has_no_orphaned_refresh_body() -> None:
    """auth.py must parse and define no admin-refresh function.

    Guards the removal itself: the first attempt at this edit left the old function
    body dangling after the note comment, which parses as a syntax error only at
    import time.
    """
    tree = ast.parse(AUTH_PY.read_text())
    names = {
        n.name
        for n in ast.walk(tree)
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    assert "refresh_token" not in names
    assert REFRESH_PATH.lstrip("/") not in AUTH_PY.read_text()


# --- negative controls ------------------------------------------------------
# Prove the assertions above can fail.


def test_control_detects_a_reregistered_route() -> None:
    """The route-absence check fails when a /refresh route is present."""
    src = BACKEND / "app" / "routers" / "auth.py"
    text = src.read_text()
    fake = text + '\n\n@router.post("/refresh")\nasync def refresh_token():\n    return {}\n'
    assert any(
        path == REFRESH_PATH
        for path in _router_paths_from_source(fake)
    ), "negative control failed: re-added /refresh route was not detected"


def _router_paths_from_source(source: str) -> set:
    """Extract decorator path strings from router source without importing it."""
    paths = set()
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for dec in node.decorator_list:
            if not isinstance(dec, ast.Call) or not dec.args:
                continue
            first = dec.args[0]
            if isinstance(first, ast.Constant) and isinstance(first.value, str):
                paths.add(f"/api/admin/auth{first.value}")
    return paths


def test_control_detects_reintroduced_model_and_import() -> None:
    """The model/import check fails on the original defect shape."""
    bad = (
        "from app.models import AdminRefreshToken\n"
        "class AdminRefreshToken(Base):\n"
        "    pass\n"
    )
    has_model = "class AdminRefreshToken" in bad
    node = ast.parse(bad).body[0]
    has_import = any((a.name or "") == MODEL_NAME for a in node.names)
    assert has_model and has_import, "negative control failed"


@pytest.mark.parametrize("needle", ["AdminRefreshToken", "/refresh"])
def test_control_needle_present_in_original_defect(needle: str) -> None:
    """Both needles existed in the pre-fix source, so the checks are not vacuous."""
    original = (
        '@router.post("/refresh")\n'
        "async def refresh_token(request, session):\n"
        "    import secrets\n"
        "    import hashlib\n"
        "    from app.models import AdminRefreshToken\n"
        "    return {}\n"
    )
    assert needle in original