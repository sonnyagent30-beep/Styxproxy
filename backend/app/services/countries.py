"""Shared country loader — single source of truth for valid ISO country codes.

Both the API validator (app/schemas.py) and the fulfilment validator
(app/services/credential.py) read from this module. There is no fallback:
if the DB read fails, the loader raises RuntimeError so the caller fails
loudly rather than silently validating against a stale static set.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

_valid_countries_cache: Optional[set[str]] = None


async def load_valid_countries() -> set[str]:
    """Load valid ISO country codes from the `countries` table.

    Raises RuntimeError if the DB read fails or returns empty — fail closed.
    Caches the result for the process lifetime.
    """
    global _valid_countries_cache
    if _valid_countries_cache is not None:
        return _valid_countries_cache

    from sqlalchemy import text

    from app.database import engine

    try:
        async with engine.connect() as conn:
            rows = (await conn.execute(text("SELECT code FROM countries"))).fetchall()
        codes = {str(r[0]).strip().upper() for r in rows if r[0]}
        if not codes:
            raise RuntimeError("countries table is empty")
        _valid_countries_cache = codes
        logger.info("Loaded %d valid country codes from the countries table", len(codes))
        return codes
    except Exception as e:
        logger.error("Could not load valid countries from the DB: %s", e)
        raise RuntimeError(
            f"Could not load valid countries from the DB: {e}. "
            "Refusing to validate against a stale fallback set."
        ) from e


def get_valid_countries() -> set[str]:
    """Return the cached set, or raise if not yet loaded."""
    if _valid_countries_cache is None:
        raise RuntimeError(
            "Valid countries have not been loaded yet. "
            "Call await load_valid_countries() first."
        )
    return _valid_countries_cache


def set_valid_countries(codes: Optional[set[str]]) -> None:
    """Set the cached valid countries (for tests)."""
    global _valid_countries_cache
    _valid_countries_cache = codes
