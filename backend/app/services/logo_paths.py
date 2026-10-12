"""Logo path resolution for both local + Docker environments."""

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
