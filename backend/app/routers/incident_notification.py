"""Betterstack incident webhook receiver.

Betterstack Uptime sends webhook POSTs to this endpoint when the monitor
status changes (down → up). The endpoint logs the incident.

Usage:
    POST /api/internal/incidents/webhook
"""

import json

import httpx
import structlog
from fastapi import APIRouter, Header, HTTPException, Request, status

from app.config import get_settings

logger = structlog.get_logger()

router = APIRouter(prefix="/api/internal", tags=["incidents"])


def _parse_betterstack_payload(data: dict) -> dict | None:
    """Parse Betterstack uptime webhook payload into a normalized dict."""
    incident = data.get("incident") or {}
    monitor = data.get("monitor") or {}
    mon_status = data.get("status") or incident.get("status") or ""

    if mon_status not in ("down", "degraded", "up"):
        return None

    return {
        "incident_id": incident.get("id", ""),
        "monitor_id": monitor.get("id", ""),
        "monitor_name": monitor.get("name", incident.get("name", "Styxproxy API")),
        "monitor_url": monitor.get("url", incident.get("url", "")),
        "status": mon_status,
        "cause": incident.get("cause", ""),
        "started_at": incident.get("started_at", ""),
        "resolved_at": incident.get("resolved_at"),
    }


@router.post("/incidents/webhook")
async def betterstack_incident_webhook(
    request: Request,
    x_betterstack_signature: str | None = Header(None, alias="X-Betterstack-Signature"),
):
    """
    Receive Betterstack uptime incident webhooks.

    Configure in Betterstack dashboard:
    Alerts → Add alert → Webhook → URL: https://api.styxproxy.com/api/internal/incidents/webhook
    """
    body = await request.body()
    payload = json.loads(body)

    incident_data = _parse_betterstack_payload(payload)
    if not incident_data:
        logger.warning("betterstack_webhook_invalid_payload", keys=list(payload.keys()))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid payload")

    status_str = incident_data["status"]
    monitor_name = incident_data["monitor_name"]
    cause = incident_data["cause"]

    logger.info(
        "betterstack_incident_received",
        status=status_str,
        monitor=monitor_name,
        cause=cause,
        incident_id=incident_data["incident_id"],
    )

    return {"received": True, "status": status_str, "monitor": monitor_name}


@router.post("/incidents/trigger")
async def trigger_incident_check(
    reason: str = "manual_check",
):
    """
    Manually trigger a Betterstack monitor check via their API.

    Betterstack's API lets you request an on-demand check of the monitor.
    This forces Betterstack to immediately check the endpoint and fire
    webhooks if the status has changed.
    """
    settings = get_settings()
    api_key = settings.betterstack_api_key
    monitor_id = settings.betterstack_monitor_id

    if not api_key or not monitor_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Betterstack not configured",
        )

    url = f"https://uptime.betterstack.com/api/v2/monitors/{monitor_id}/actions/run"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.post(url, headers=headers, json={})
        if r.status_code == 204 or r.status_code == 200:
            logger.info("betterstack_manual_check_triggered", monitor_id=monitor_id)
            return {"triggered": True, "monitor_id": monitor_id, "reason": reason}
        else:
            logger.warning("betterstack_trigger_failed", status=r.status_code, body=r.text[:200])
            raise HTTPException(
                status_code=r.status_code,
                detail=f"Betterstack API error: {r.text[:200]}",
            )
    except httpx.HTTPStatusError as e:
        logger.warning("betterstack_trigger_http_error", status=e.response.status_code)
        raise HTTPException(status_code=e.response.status_code, detail=str(e))
    except Exception as e:
        logger.warning("betterstack_trigger_error", error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
