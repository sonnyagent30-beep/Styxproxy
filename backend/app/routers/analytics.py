"""Customer journey analytics endpoint — funnel, NPS, retention.

Theme C: operational analytics dashboard.
- Funnel: page_view → plan_viewed → cart_added → checkout_started → payment_completed
- Trial survey analytics: response rates and NPS
- Real-time from analytics_events + pending_trial_surveys tables

Owner: Operations / Sonny
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import text

from app.database import async_session as get_session

router = APIRouter(prefix="/api/admin", tags=["admin"])

# ── Schemas ───────────────────────────────────────────────────────────────

class FunnelStep(BaseModel):
    step: str
    count: int
    unique_sessions: int


class FunnelResponse(BaseModel):
    period_start: str
    period_end: str
    total_sessions: int
    steps: list[FunnelStep]
    drop_off_pct: dict[str, float]


class TrialSurvey(BaseModel):
    surveys_sent: int
    surveys_completed: int
    response_rate_pct: float
    avg_nps_score: float
    promoters_pct: float
    passives_pct: float
    detractors_pct: float


class AnalyticsResponse(BaseModel):
    funnel: FunnelResponse
    trial_survey: TrialSurvey
    generated_at: str


# ── Funnel ──────────────────────────────────────────────────────────────

async def _funnel(days: int = 30) -> FunnelResponse:
    """Build conversion funnel from analytics_events."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    steps_order = [
        "page_view", "plan_viewed", "cart_added",
        "checkout_started", "payment_completed",
    ]

    async with get_session() as session:
        # Total unique sessions
        total_row = await session.execute(
            text("SELECT COUNT(DISTINCT session_id) FROM analytics_events WHERE created_at >= :cutoff"),
            {"cutoff": cutoff}
        )
        total_sessions = total_row.scalar() or 0

        # Per-step counts
        steps_out = []
        drop_offs = {}
        prev_unique = total_sessions

        for step in steps_order:
            row = await session.execute(
                text("""
                    SELECT COUNT(*) as cnt, COUNT(DISTINCT session_id) as uniq
                    FROM analytics_events
                    WHERE created_at >= :cutoff AND event_name = :step
                """),
                {"cutoff": cutoff, "step": step}
            )
            result = row.fetchone()
            cnt = result[0] or 0
            uniq = result[1] or 0
            steps_out.append(FunnelStep(step=step, count=cnt, unique_sessions=uniq))
            if prev_unique > 0:
                drop_offs[step] = round(((prev_unique - uniq) / prev_unique) * 100, 1)
            else:
                drop_offs[step] = 0.0
            prev_unique = uniq

        return FunnelResponse(
            period_start=cutoff.isoformat().replace("+00:00", "Z"),
            period_end=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            total_sessions=total_sessions,
            steps=steps_out,
            drop_off_pct=drop_offs,
        )


# ── Trial Survey ────────────────────────────────────────────────────────

async def _trial_survey() -> TrialSurvey:
    """NPS and response rates from pending_trial_surveys."""
    async with get_session() as session:
        sent_row = await session.execute(text("SELECT COUNT(*) FROM pending_trial_surveys"))
        sent = sent_row.scalar() or 0

        completed_row = await session.execute(
            text("SELECT COUNT(*) FROM pending_trial_surveys WHERE responses IS NOT NULL")
        )
        completed = completed_row.scalar() or 0

        response_rate = round((completed / max(1, sent)) * 100, 1)

        # Try to extract NPS scores from response field
        nps_rows = await session.execute(
            text("SELECT responses FROM pending_trial_surveys WHERE responses IS NOT NULL LIMIT 200")
        )
        nps_scores = []
        for row in nps_rows.fetchall():
            resp = row[0]
            if resp is None:
                continue
            if isinstance(resp, (int, float)):
                s = int(resp)
            elif isinstance(resp, str):
                try:
                    s = int(float(resp))
                except Exception:
                    continue
            elif isinstance(resp, dict):
                s = resp.get("nps_score") or resp.get("score")
                if s is None:
                    continue
                s = int(s)
            else:
                continue
            if 0 <= s <= 10:
                nps_scores.append(s)

        if nps_scores:
            avg_nps = round(sum(nps_scores) / len(nps_scores), 1)
            promoters = round(len([s for s in nps_scores if s >= 9]) / len(nps_scores) * 100, 1)
            passives_r = round(len([s for s in nps_scores if 7 <= s <= 8]) / len(nps_scores) * 100, 1)
            detractors = round(len([s for s in nps_scores if s <= 6]) / len(nps_scores) * 100, 1)
        else:
            avg_nps = 0.0
            promoters = passives_r = detractors = 0.0

        return TrialSurvey(
            surveys_sent=sent,
            surveys_completed=completed,
            response_rate_pct=response_rate,
            avg_nps_score=avg_nps,
            promoters_pct=promoters,
            passives_pct=passives_r,
            detractors_pct=detractors,
        )


# ── Endpoints ─────────────────────────────────────────────────────────────

@router.get("/analytics/funnel", response_model=FunnelResponse)
async def get_analytics_funnel(days: int = 30):
    """Conversion funnel (last N days)."""
    return await _funnel(days=days)


@router.get("/analytics/events")
async def get_analytics_events(
    page: int = 1,
    limit: int = 30,
    event_name: Optional[str] = None,
):
    """Paginated raw analytics events."""
    offset = (page - 1) * limit
    async with get_session() as session:
        # Build query
        where_clause = ""
        params = {"limit": limit, "offset": offset}
        if event_name:
            where_clause = "WHERE event_name = :event_name"
            params["event_name"] = event_name

        # Count
        count_row = await session.execute(
            text(f"SELECT COUNT(*) FROM analytics_events {where_clause}"),
            params,
        )
        total = count_row.scalar() or 0

        # Fetch rows
        rows = await session.execute(
            text(f"""
                SELECT id, event_name, session_id, customer_phone, country,
                       plan_code, channel, meta, created_at
                FROM analytics_events
                {where_clause}
                ORDER BY created_at DESC
                LIMIT :limit OFFSET :offset
            """),
            params,
        )

        events = []
        for row in rows.fetchall():
            events.append({
                "id": row[0],
                "event_name": row[1],
                "session_id": row[2],
                "customer_phone": row[3],
                "country": row[4],
                "plan_code": row[5],
                "channel": row[6] or "web",
                "meta": row[7] or {},
                "created_at": row[8].isoformat() if row[8] else None,
            })

        return {"events": events, "total": total, "page": page, "limit": limit}


@router.get("/analytics", response_model=AnalyticsResponse)
async def get_analytics():
    """Full analytics — funnel + trial survey."""
    funnel = await _funnel(days=30)
    trial = await _trial_survey()
    return AnalyticsResponse(
        funnel=funnel,
        trial_survey=trial,
        generated_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    )
