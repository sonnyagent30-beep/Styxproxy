"""
Betterstack status page integration — posts/clears maintenance announcements.

When maintenance mode is ENABLED:
  PATCH /api/v2/status-pages/{page_id}
    → sets announcement + announcement_embed_visible=true

When maintenance mode is DISABLED:
  PATCH /api/v2/status-pages/{page_id}
    → clears announcement

This makes the maintenance message visible on the public status page
without needing to create/resolve incidents manually.
"""

import httpx
import structlog

logger = structlog.get_logger()

_BASE = "https://uptime.betterstack.com/api/v2/status-pages"


def _headers(api_key: str) -> dict:
    return {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}


async def post_maintenance_announcement(
    page_id: str,
    api_key: str,
    message: str | None = None,
) -> dict | None:
    """
    Post a maintenance announcement to the status page.
    Called when maintenance mode is ENABLED.
    """
    body = message or (
        "Styxproxy is currently undergoing scheduled maintenance. " "Proxy provisioning is temporarily unavailable."
    )
    payload = {
        "announcement": body,
        "announcement_embed_visible": True,
    }
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.patch(
                f"{_BASE}/{page_id}",
                headers=_headers(api_key),
                json=payload,
            )
        r.raise_for_status()
        data = r.json()
        logger.info(
            "betterstack_announcement_posted",
            page_id=page_id,
            message_preview=body[:60],
        )
        return data
    except httpx.HTTPStatusError as e:
        logger.warning(
            "betterstack_http_error",
            status=e.response.status_code,
            body=e.response.text[:200],
        )
    except Exception as e:
        logger.warning("betterstack_request_failed", error=str(e))
    return None


async def clear_maintenance_announcement(
    page_id: str,
    api_key: str,
) -> dict | None:
    """
    Clear the maintenance announcement from the status page.
    Called when maintenance mode is DISABLED.
    """
    payload = {
        "announcement": None,
        "announcement_embed_visible": False,
    }
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.patch(
                f"{_BASE}/{page_id}",
                headers=_headers(api_key),
                json=payload,
            )
        r.raise_for_status()
        logger.info("betterstack_announcement_cleared", page_id=page_id)
        return r.json()
    except httpx.HTTPStatusError as e:
        logger.warning(
            "betterstack_http_error",
            status=e.response.status_code,
            body=e.response.text[:200],
        )
    except Exception as e:
        logger.warning("betterstack_request_failed", error=str(e))
    return None
