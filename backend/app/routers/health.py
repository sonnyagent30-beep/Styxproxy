"""Health check router."""
from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.database import get_session
from app.schemas import HealthResponse

router = APIRouter(tags=["health"])

@router.get("/health", response_model=HealthResponse)
async def health_check(session: AsyncSession = Depends(get_session)):
    """Health check endpoint."""
    database_status = "connected"
    try:
        await session.execute(text("SELECT 1"))
    except Exception:
        database_status = "disconnected"

    return HealthResponse(
        status="healthy",
        version="1.0.0",
        database=database_status,
        timestamp=datetime.utcnow(),
    )
