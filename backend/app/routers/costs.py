"""Cost monitoring endpoint — LLM spend, Resend emails.

Theme C: unified cost dashboard for ops visibility.
- LLM: Charon tokens used, estimated M2 spend vs daily budget
- Email: Resend delivery stats (today + total, bounce rate)

Owner: Operations / Sonny
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.services.permissions import require_permission

router = APIRouter(prefix="/api/admin", tags=["admin"])

# ── Schemas ────────────────────────────────────────────────────────────

class LLM_cost(BaseModel):
    tokens_used_total: int
    daily_spend_usd: float
    budget_usd: float
    budget_remaining_usd: float
    budget_pct_used: float
    daily_reset_utc: str


class ResendCost(BaseModel):
    emails_today: int
    emails_total: int
    bounces_today: int
    bounce_rate_pct: float


class CostsResponse(BaseModel):
    llm: LLM_cost
    email: ResendCost
    generated_at: str


# ── Helpers ────────────────────────────────────────────────────────────

def _llm_cost() -> LLM_cost:
    try:
        from app.services.charon.stats import CharonMetrics
        stats = CharonMetrics.get()
        budget = float(os.environ.get("CHARON_DAILY_BUDGET_USD", "0"))
        daily = stats.daily_spend_usd
        remaining = max(0.0, budget - daily)
        pct = round((daily / budget) * 100, 1) if budget > 0 else 0.0
        now = datetime.now(timezone.utc)
        reset_str = f"{24 - now.hour:02d}:00 UTC"
        return LLM_cost(
            tokens_used_total=stats.tokens_used_total,
            daily_spend_usd=round(daily, 4),
            budget_usd=budget,
            budget_remaining_usd=round(remaining, 4),
            budget_pct_used=pct,
            daily_reset_utc=reset_str,
        )
    except Exception:
        return LLM_cost(
            tokens_used_total=0,
            daily_spend_usd=0.0,
            budget_usd=0.0,
            budget_remaining_usd=0.0,
            budget_pct_used=0.0,
            daily_reset_utc="00:00 UTC",
        )


def _resend_cost() -> ResendCost:
    log_path = Path(
        os.environ.get(
            "EMAIL_DELIVERY_LOG_PATH",
            "/opt/styxproxy/backend/data/email_delivery.log.jsonl",
        )
    )
    today = datetime.now(timezone.utc).date().isoformat()
    emails_today = 0
    emails_total = 0
    bounces_today = 0

    if log_path.exists():
        try:
            lines = log_path.read_text(encoding="utf-8").splitlines()
            emails_total = len(lines)
            for line in lines[-1000:]:
                try:
                    entry = json.loads(line)
                    if entry.get("ts", "")[:10] == today:
                        emails_today += 1
                    if entry.get("status") in ("bounced", "bounce"):
                        bounces_today += 1
                except Exception:
                    pass
        except Exception:
            pass

    bounce_rate = (
        round((bounces_today / max(1, emails_today)) * 100, 2)
        if emails_today > 0
        else 0.0
    )
    return ResendCost(
        emails_today=emails_today,
        emails_total=emails_total,
        bounces_today=bounces_today,
        bounce_rate_pct=bounce_rate,
    )


# ── Endpoint ────────────────────────────────────────────────────────────

@router.get("/costs", response_model=CostsResponse)
async def get_costs(
    current_admin: dict = Depends(require_permission("admin.monitor.metrics.read")),
) -> CostsResponse:
    """
    Unified cost monitoring dashboard (superadmin only).

    Returns LLM spend and email delivery stats.
    """
    llm = _llm_cost()
    email = _resend_cost()
    return CostsResponse(
        llm=llm,
        email=email,
        generated_at=datetime.now(timezone.utc).isoformat() + "Z",
    )
