"""Proxy session statistics — powers the globe live counter."""

from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import StyxproxyCredential

router = APIRouter(prefix="/api/proxy", tags=["proxy"])

# Fixed list of cities the globe renders — merge in live counts
CITY_META = [
    {"lat": 51.5074, "lng": -0.1278,  "name": "London",       "code": "GB", "region": "Europe"},
    {"lat": 40.7128, "lng": -74.006,  "name": "New York",    "code": "US", "region": "North America"},
    {"lat": 52.52,   "lng": 13.405,   "name": "Berlin",      "code": "DE", "region": "Europe"},
    {"lat": 48.8566, "lng": 2.3522,   "name": "Paris",       "code": "FR", "region": "Europe"},
    {"lat": 45.5017, "lng": -73.5673, "name": "Toronto",     "code": "CA", "region": "North America"},
    {"lat": 35.6762, "lng": 139.6503, "name": "Tokyo",       "code": "JP", "region": "Asia Pacific"},
    {"lat": -33.8688,"lng": 151.2093, "name": "Sydney",      "code": "AU", "region": "Oceania"},
    {"lat": -23.5505,"lng": -46.6333, "name": "São Paulo",   "code": "BR", "region": "South America"},
    {"lat": 1.3521,  "lng": 103.8198, "name": "Singapore",   "code": "SG", "region": "Asia Pacific"},
    {"lat": 37.7749, "lng": -122.4194,"name": "San Jose",    "code": "US", "region": "North America"},
    {"lat": 28.6139, "lng": 77.209,   "name": "New Delhi",   "code": "IN", "region": "Asia Pacific"},
    {"lat": 55.7558, "lng": 37.6173,  "name": "Moscow",      "code": "RU", "region": "Europe"},
]


@router.get("/active-countries")
async def active_countries(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
    """Return active proxy sessions grouped by last known IP country.

    GlobeScene polls this every 60 s to update city markers and session counts.
    last_ip_country is set by the Dante auth layer on each proxy connection.
    Returns zero counts when no sessions are active (pre-launch — globe shows demo arcs).
    """
    rows = (
        await session.execute(
            select(
                StyxproxyCredential.last_ip_country,
                func.count(StyxproxyCredential.id).label("session_count"),
            )
            .where(StyxproxyCredential.status == "active")
            .where(StyxproxyCredential.last_ip_country.isnot(None))
            .group_by(StyxproxyCredential.last_ip_country)
        )
    ).fetchall()

    # Map: country_code → session_count
    live_counts: dict[str, int] = {r.last_ip_country: r.session_count for r in rows}

    # Merge live counts into the fixed city list
    cities = []
    for c in CITY_META:
        cities.append({
            **c,
            "sessions": live_counts.get(c["code"], 0),
        })

    total = sum(live_counts.values())

    return {
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "total_active_sessions": total,
        "cities": cities,
    }
