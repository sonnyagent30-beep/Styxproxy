"""Alerting service with multi-path delivery.

Primary: Resend email (via existing email service)
Fallback 1: Telegram Bot API (push notification to phone)
Fallback 2: ntfy.sh (zero-config push notification, no account needed)

If Resend fails (expired key, rate limit, incident), alerts still reach
a human via Telegram or ntfy. This eliminates the single-point-of-failure
where one expired Resend key silences all alerts.

Configuration (in .env):
    TELEGRAM_BOT_TOKEN=       — Telegram bot token from @BotFather
    TELEGRAM_ALERT_CHAT_ID=   — Your chat ID from @userinfobot
    NTFY_TOPIC=               — ntfy.sh topic name (e.g. styxproxy-alerts-x7k2)
"""

from datetime import datetime, timezone
from typing import Optional

import httpx
import structlog

from app.config import get_settings

logger = structlog.get_logger(__name__)


# =============================================================================
# Telegram Bot API
# =============================================================================


async def send_telegram_alert(
    message: str,
    parse_mode: str = "HTML",
) -> bool:
    """Send an alert via Telegram Bot API.

    Returns True if the message was delivered, False otherwise.
    Failures are logged but never raised — alerting must not crash the caller.
    """
    settings = get_settings()
    token = settings.telegram_bot_token
    chat_id = settings.telegram_alert_chat_id

    if not token or not chat_id:
        logger.warning("Telegram alerting not configured — skipping fallback")
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": parse_mode,
        "disable_web_page_preview": True,
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.post(url, json=payload)
            if r.status_code == 200:
                logger.info("telegram_alert_sent", chat_id=chat_id)
                return True
            else:
                logger.error(
                    "telegram_alert_failed",
                    status=r.status_code,
                    body=r.text[:200],
                )
                return False
    except Exception as e:
        logger.error("telegram_alert_exception", error=str(e))
        return False


# =============================================================================
# ntfy.sh (zero-config push notification)
# =============================================================================


async def send_ntfy_alert(
    message: str,
    title: str = "Styxproxy Alert",
    priority: str = "high",
) -> bool:
    """Send an alert via ntfy.sh.

    ntfy.sh is a free push notification service. No account needed — just pick
    a topic name and subscribe via the ntfy phone app or web.

    Returns True if the message was delivered, False otherwise.
    """
    settings = get_settings()
    topic = settings.ntfy_topic

    if not topic:
        logger.warning("ntfy alerting not configured — skipping")
        return False

    url = f"https://ntfy.sh/{topic}"
    headers = {
        "Title": title,
        "Priority": priority,
        "Tags": "rotating_light",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.post(url, content=message, headers=headers)
            if r.status_code == 200:
                logger.info("ntfy_alert_sent", topic=topic)
                return True
            else:
                logger.error(
                    "ntfy_alert_failed",
                    status=r.status_code,
                    body=r.text[:200],
                )
                return False
    except Exception as e:
        logger.error("ntfy_alert_exception", error=str(e))
        return False


# =============================================================================
# Unified alert dispatch with fallback
# =============================================================================


async def send_alert_with_fallback(
    subject: str,
    message: str,
    details: Optional[dict] = None,
) -> dict:
    """Send an alert via Resend email, falling back to Telegram then ntfy.

    This is the primary entry point for critical alerts. It tries the
    existing email path first; if that fails (Resend down, expired key,
    rate limit), it sends a Telegram message, then ntfy.

    Returns a dict with the delivery result for each path.
    """
    from app.services.email import send_admin_notification

    result = {
        "email": {"attempted": False, "success": False, "error": None},
        "telegram": {"attempted": False, "success": False, "error": None},
        "ntfy": {"attempted": False, "success": False, "error": None},
        "delivered": False,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    # Build detail string for email
    detail_str = message
    if details:
        detail_str = message + "\n\n" + "\n".join(
            f"{k}: {v}" for k, v in details.items()
        )

    # Try email first
    try:
        email_result = await send_admin_notification(
            title=subject,
            details={"Message": message, **(details or {})},
        )
        result["email"]["attempted"] = True
        result["email"]["success"] = email_result.success
        if email_result.success:
            result["delivered"] = True
            return result
        result["email"]["error"] = email_result.error
    except Exception as e:
        result["email"]["attempted"] = True
        result["email"]["error"] = str(e)
        logger.error("email_alert_failed", error=str(e))

    # Fallback 1: Telegram
    telegram_message = f"<b>🚨 {subject}</b>\n\n{message}"
    if details:
        telegram_message += "\n\n" + "\n".join(
            f"<b>{k}:</b> {v}" for k, v in details.items()
        )
    telegram_ok = await send_telegram_alert(telegram_message)
    result["telegram"]["attempted"] = True
    result["telegram"]["success"] = telegram_ok
    if telegram_ok:
        result["delivered"] = True
        return result
    result["telegram"]["error"] = "Telegram delivery failed"

    # Fallback 2: ntfy
    ntfy_message = f"{subject}\n\n{message}"
    if details:
        ntfy_message += "\n\n" + "\n".join(f"{k}: {v}" for k, v in details.items())
    ntfy_ok = await send_ntfy_alert(ntfy_message, title=subject)
    result["ntfy"]["attempted"] = True
    result["ntfy"]["success"] = ntfy_ok
    if ntfy_ok:
        result["delivered"] = True
    else:
        result["ntfy"]["error"] = "ntfy delivery failed"

    return result


# =============================================================================
# Test / status helpers
# =============================================================================


async def test_telegram_path() -> dict:
    """Test the Telegram delivery path. Returns status info."""
    settings = get_settings()
    if not settings.telegram_bot_token or not settings.telegram_alert_chat_id:
        return {
            "configured": False,
            "error": "Telegram bot token or chat ID not set",
        }

    test_message = "✅ Styxproxy alerting test — Telegram path is working."
    ok = await send_telegram_alert(test_message)
    return {
        "configured": True,
        "delivered": ok,
        "chat_id": settings.telegram_alert_chat_id,
    }


async def test_ntfy_path() -> dict:
    """Test the ntfy delivery path. Returns status info."""
    settings = get_settings()
    if not settings.ntfy_topic:
        return {
            "configured": False,
            "error": "ntfy topic not set",
        }

    test_message = "✅ Styxproxy alerting test — ntfy path is working."
    ok = await send_ntfy_alert(test_message, title="Styxproxy Test")
    return {
        "configured": True,
        "delivered": ok,
        "topic": settings.ntfy_topic,
    }


async def get_alerting_status() -> dict:
    """Report which alerting paths are configured and ready."""
    settings = get_settings()
    return {
        "email": {
            "configured": bool(settings.resend_api_key),
            "provider": "resend",
        },
        "telegram": {
            "configured": bool(settings.telegram_bot_token and settings.telegram_alert_chat_id),
            "provider": "telegram",
            "chat_id": settings.telegram_alert_chat_id or None,
        },
        "ntfy": {
            "configured": bool(settings.ntfy_topic),
            "provider": "ntfy.sh",
            "topic": settings.ntfy_topic or None,
        },
        "fallback_ready": bool(
            (settings.telegram_bot_token and settings.telegram_alert_chat_id)
            or settings.ntfy_topic
        ),
    }
