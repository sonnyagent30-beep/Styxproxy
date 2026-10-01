"""Cost monitoring endpoint — LLM spend, Resend emails, Vercel bandwidth.

Theme C: unified cost dashboard for ops visibility.
- LLM: Charon tokens used + MiniMax M2 cost estimation + daily budget
- Email: Resend delivery stats (today + total, bounce/complaint rate)
- Vercel: bandwidth usage (this billing period)

Owner: Operations / Sonny
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api/admin", tags=["admin"])

# ── Pricing constants ────────────────────────────────────────────────────────
# Groq Qwen 3.5 27B: free tier (community/preview) or very low cost
# Actual pricing: $0.05-0.10/M input, $0.10-0.25/M output depending on model
# Using conservative estimates
GROQ_INPUT_COST_PER_M = 0.08
GROQ_OUTPUT_COST_PER_M = 0.20
INPUT_RATIO = 0.70
OUTPUT_RATIO = 0.30

# ── Schemas ─────────────────────────────────────────────────────────────────

class LLM_cost(BaseModel):
    tokens_used_total: int
    estimated_cost_usd: float
    budget_usd: float
    budget_remaining_usd: float
    budget_pct_used: float
    daily_reset_utc: str
    pricing_model: str


class ResendCost(BaseModel):
    emails_today: int
    emails_total: int
    bounces_today: int
    complaints_today: int
    bounce_rate_pct: float
    complaint_rate_pct: float


class VercelBandwidth(BaseModel):
    bandwidth_bytes: int
    bandwidth_gb: float
    used_formatted: str


class VercelCost(BaseModel):
    bandwidth: VercelBandwidth
    build_time_seconds: int
    function_invocations: int
    period_start: str
    period_end: str
    error: Optional[str] = None


class CostsResponse(BaseModel):
    llm: LLM_cost
    email: ResendCost
    vercel: VercelCost
    generated_at: str


# ── LLM cost ────────────────────────────────────────────────────────────────

def _llm_cost() -> LLM_cost:
    try:
        from app.services.charon.stats import CharonMetrics
        stats = CharonMetrics.get()
        tokens = stats.tokens_used_total
        input_tokens = int(tokens * INPUT_RATIO)
        output_tokens = int(tokens * OUTPUT_RATIO)
        cost = (
            (input_tokens / 1_000_000) * GROQ_INPUT_COST_PER_M
            + (output_tokens / 1_000_000) * GROQ_OUTPUT_COST_PER_M
        )
        budget = float(os.environ.get("CHARON_DAILY_BUDGET_USD", "0"))
        remaining = max(0.0, budget - cost)
        pct = round((cost / budget) * 100, 1) if budget > 0 else 0.0
        now = datetime.now(timezone.utc)
        reset_str = f"{24 - now.hour:02d}:{now.minute:02d} UTC"
        return LLM_cost(
            tokens_used_total=tokens,
            estimated_cost_usd=round(cost, 4),
            budget_usd=budget,
            budget_remaining_usd=round(remaining, 4),
            budget_pct_used=pct,
            daily_reset_utc=reset_str,
            pricing_model="Groq Qwen 3.5 27B ($0.08/M input, $0.20/M output)",
        )
    except Exception:
        return LLM_cost(
            tokens_used_total=0,
            estimated_cost_usd=0.0,
            budget_usd=0.0,
            budget_remaining_usd=0.0,
            budget_pct_used=0.0,
            daily_reset_utc="00:00 UTC",
            pricing_model="Groq Qwen 3.5 27B",
        )


# ── Resend cost ─────────────────────────────────────────────────────────────

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
    complaints_today = 0

    if log_path.exists():
        try:
            lines = log_path.read_text(encoding="utf-8").splitlines()
            emails_total = len(lines)
            for line in lines[-2000:]:
                try:
                    entry = json.loads(line)
                    ts = entry.get("ts", "")
                    if ts[:10] == today:
                        emails_today += 1
                    status_val = entry.get("status", "").lower()
                    if status_val in ("bounced", "bounce"):
                        bounces_today += 1
                    if status_val in ("complained", "complaint", "spam"):
                        complaints_today += 1
                except Exception:
                    pass
        except Exception:
            pass

    bounce_rate = round((bounces_today / max(1, emails_today)) * 100, 2)
    complaint_rate = round((complaints_today / max(1, emails_today)) * 100, 2)
    return ResendCost(
        emails_today=emails_today,
        emails_total=emails_total,
        bounces_today=bounces_today,
        complaints_today=complaints_today,
        bounce_rate_pct=bounce_rate,
        complaint_rate_pct=complaint_rate,
    )


# ── Vercel bandwidth ────────────────────────────────────────────────────────

def _vercel_cost() -> VercelCost:
    vercel_token = os.environ.get("VERCEL_API_TOKEN", "")
    project_id = os.environ.get(
        "VERCEL_PROJECT_ID", "prj_CowINCcRq9ZmIwo9MZsk3ASYSk4G"
    )

    now = datetime.now(timezone.utc)
    period_start_dt = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    period_end_dt = now

    if not vercel_token:
        return VercelCost(
            bandwidth=VercelBandwidth(bandwidth_bytes=0, bandwidth_gb=0.0, used_formatted="N/A — token not set"),
            build_time_seconds=0,
            function_invocations=0,
            period_start=period_start_dt.isoformat() + "Z",
            period_end=period_end_dt.isoformat() + "Z",
            error="VERCEL_API_TOKEN not set",
        )

    # vcp_ tokens are deployment-only — cannot read usage
    if vercel_token.startswith("vcp_"):
        return VercelCost(
            bandwidth=VercelBandwidth(bandwidth_bytes=0, bandwidth_gb=0.0,
        used_formatted="N/A — deploy token (no usage access)"),
            build_time_seconds=0,
            function_invocations=0,
            period_start=period_start_dt.isoformat() + "Z",
            period_end=period_end_dt.isoformat() + "Z",
            error="vcp_ token — Vercel deploy tokens cannot read usage. Swap to a full account token for stats.",
        )

    try:
        import httpx
        with httpx.Client(timeout=10.0) as client:
            r = client.get(
                f"https://api.vercel.com/v6/projects/{project_id}/usage",
                headers={"Authorization": f"Bearer {vercel_token}"},
                params={
                    "start": period_start_dt.strftime("%Y-%m-%d"),
                    "end": period_end_dt.strftime("%Y-%m-%d"),
                },
            )
        if r.status_code == 200:
            data = r.json()
            bw_bytes = data.get("bandwidth", 0) or 0
            bw_gb = round(bw_bytes / (1024**3), 3)
            if bw_gb < 0.001:
                bw_formatted = f"{round(bw_bytes / 1024, 1)} KB"
            elif bw_gb < 1:
                bw_formatted = f"{round(bw_gb * 1024, 1)} MB"
            else:
                bw_formatted = f"{bw_gb} GB"
            return VercelCost(
                bandwidth=VercelBandwidth(bandwidth_bytes=bw_bytes, bandwidth_gb=bw_gb, used_formatted=bw_formatted),
                build_time_seconds=data.get("buildTime", 0) or 0,
                function_invocations=data.get("invocations", 0) or 0,
                period_start=period_start_dt.isoformat() + "Z",
                period_end=period_end_dt.isoformat() + "Z",
                error=None,
            )
        else:
            return VercelCost(
                bandwidth=VercelBandwidth(bandwidth_bytes=0, bandwidth_gb=0.0, used_formatted="Error"),
                build_time_seconds=0,
                function_invocations=0,
                period_start=period_start_dt.isoformat() + "Z",
                period_end=period_end_dt.isoformat() + "Z",
                error=f"Vercel API error: {r.status_code}",
            )
    except Exception as e:
        return VercelCost(
            bandwidth=VercelBandwidth(bandwidth_bytes=0, bandwidth_gb=0.0, used_formatted="Error"),
            build_time_seconds=0,
            function_invocations=0,
            period_start=period_start_dt.isoformat() + "Z",
            period_end=period_end_dt.isoformat() + "Z",
            error=str(e),
        )


# ── Endpoint ────────────────────────────────────────────────────────────────

@router.get("/costs", response_model=CostsResponse)
async def get_costs() -> CostsResponse:
    """
    Unified cost monitoring dashboard (superadmin only).

    Returns LLM spend (MiniMax M2 estimated), email delivery stats,
    and Vercel bandwidth usage for the current billing period.
    """
    llm = _llm_cost()
    email = _resend_cost()
    vercel = _vercel_cost()
    return CostsResponse(
        llm=llm,
        email=email,
        vercel=vercel,
        generated_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    )
