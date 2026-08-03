"""Proxy session statistics — powers the globe live counter."""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import Credential

router = APIRouter(prefix="/api/proxy", tags=["proxy"])


@router.get("/active-countries")
async def active_countries(session: AsyncSession = Depends(get_session)) -> dict:
    """Return active proxy sessions grouped by country code.

    GlobeViz polls this every 30s to update city markers and session counts.
    Returns zero counts for cities with no active sessions (globe still renders).
    """
    # Active = credential not expired, status is active
    rows = (
        await session.execute(
            select(
                Credential.country_code,
                func.count(Credential.id).label("session_count"),
            )
            .where(Credential.status == "active")
            .where(Credential.expires_at > datetime.now(timezone.utc))
            .group_by(Credential.country_code)
        )
    ).fetchall()

    country_sessions = {r.country_code: r.session_count for r in rows}

    # Fixed list of cities the globe renders — merge in live counts
    CITIES = [
        {"lat": 51.5074, "lng": -0.1278,  "name": "London",       "country": "GB", "region": "Europe"},
        {"lat": 40.7128, "lng": -74.006,  "name": "New York",    "country": "US", "region": "North America"},
        {"lat": 52.52,   "lng": 13.405,   "name": "Berlin",      "country": "DE", "region": "Europe"},
        {"lat": 48.8566, "lng": 2.3522,   "name": "Paris",       "country": "FR", "region": "Europe"},
        {"lat": 45.5017, "lng": -73.5673, "name": "Toronto",     "country": "CA", "region": "North America"},
        {"lat": 35.6762, "lng": 139.6503, "name": "Tokyo",       "country": "JP", "region": "Asia Pacific"},
        {"lat": -33.8688,"lng": 151.2093, "name": "Sydney",      "country": "AU", "region": "Oceania"},
        {"lat": -23.5505,"lng": -46.6333, "name": "São Paulo",   "country": "BR", "region": "South America"},
        {"lat": 1.3521,  "lng": 103.8198, "name": "Singapore",   "country": "SG", "region": "Asia Pacific"},
        {"lat": 37.7749, "lng": -122.4194,"name": "San Jose",    "country": "US", "region": "North America"},
        {"lat": 28.6139, "lng": 77.209,   "name": "New Delhi",   "country": "IN", "region": "Asia Pacific"},
        {"lat": 55.7558, "lng": 37.6173,  "name": "Moscow",      "country": "RU", "region": "Europe"},
    ]

    cities = []
    for c in CITIES:
        count = country_sessions.get(c["country"], 0)
        cities.append({**c, "sessions": int(count)})

    total = sum(int(country_sessions.get(c, 0)) for c in set(r.country_code for r in rows))

    return {
        "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
        "total_active_sessions": total,
        "cities": cities,
    }
