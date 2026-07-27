"""Logo path resolution for both local + Docker environments.

The assets live in backend/app/assets/. The Docker image sets WORKDIR=/app
and copies app/ → /app/app/, so the path inside the container is
/app/app/assets/. Locally (CI, tests), the project lives at any path.

This module resolves the logo path once, at import time, relative to
this file. Falls back to a hardcoded path for backward compat if the
file isn't where we expect.
"""
from pathlib import Path

_THIS_DIR = Path(__file__).resolve().parent
_ASSETS_DIR = _THIS_DIR.parent / "assets"

_LOGO_DARK_PATH = _ASSETS_DIR / "styxproxy_logo_dark.png"
_LOGO_LIGHT_PATH = _ASSETS_DIR / "styxproxy_logo_light.png"


def get_logo_path(theme: str = "dark") -> Path:
    """Return absolute path to logo PNG for given theme."""
    if theme == "light":
        return _LOGO_LIGHT_PATH
    return _LOGO_DARK_PATH