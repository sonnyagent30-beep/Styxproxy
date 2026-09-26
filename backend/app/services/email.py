"""Email service using Resend API.

Provides transactional email functionality with Styxproxy brand design language:
- Contact form submissions
- Charon escalation notifications
- Admin notifications (orders, refunds, etc.)
- Order confirmations and credentials delivery
- Password reset and admin invites

Design language matches the receipt PDF:
- Dark theme only (maximum email client compatibility)
- Green accent (#00D060)
- Card-based layout with dividers
- Credentials with green border

All templates use:
- Inline styles only (no CSS variables)
- Table-based layouts (no flexbox)
- No prefers-color-scheme media queries
- lang="en" on all html tags
- Proper alt text and dimensions on images
- Unsubscribe link and physical address in footer
- aria-hidden on decorative elements
- rel="noopener noreferrer" on external links
"""

import base64
import io
import json
import logging
import os
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Optional

import httpx
from PIL import Image
from pydantic import BaseModel, EmailStr

from app.config import get_settings
from app.services.logo_paths import get_logo_path

logger = logging.getLogger(__name__)

# Persistent delivery log — JSON lines, capped at 500 entries.
# Path is configurable so the container can write to a mounted volume.
# Default to /app/data/email_delivery.log.jsonl inside the container, which is
# mapped to ./backend/data on the host via docker-compose volume mount.
_DELIVERY_LOG_PATH = Path(os.environ.get("EMAIL_DELIVERY_LOG_PATH", "/app/data/email_delivery.log.jsonl"))
_DELIVERY_LOG_MAX_ENTRIES = 500


def _append_delivery_log(entry: dict) -> None:
    """Append a delivery result (success or failure) to the JSON-lines log.

    Trims the file to the last N entries so it doesn't grow forever.
    No-op if the log path's parent directory doesn't exist (e.g. local dev).
    """
    try:
        _DELIVERY_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with _DELIVERY_LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, default=str) + "\n")
        # Trim if needed
        if _DELIVERY_LOG_PATH.exists():
            lines = _DELIVERY_LOG_PATH.read_text(encoding="utf-8").splitlines()
            if len(lines) > _DELIVERY_LOG_MAX_ENTRIES:
                _DELIVERY_LOG_PATH.write_text(
                    "\n".join(lines[-_DELIVERY_LOG_MAX_ENTRIES:]) + "\n",
                    encoding="utf-8",
                )
    except Exception as exc:
        # Never let logging break the actual send path
        logger.warning("Could not write email delivery log: %s", exc)


settings = get_settings()


# =============================================================================
# Logo processing for inline embedding
# =============================================================================


def _get_logo_b64() -> str:
    """Process and return the Styxproxy logo as base64 PNG."""
    logo = Image.open(get_logo_path("dark")).convert("RGBA")
    # Resize for email header — 200px wide is enough for header logo
    target_w = 200
    ratio = target_w / logo.size[0]
    target_h = int(logo.size[1] * ratio)
    resized = logo.resize((target_w, target_h), Image.LANCZOS)
    buf = io.BytesIO()
    resized.save(buf, format="PNG", optimize=True)
    return base64.b64encode(buf.getvalue()).decode()


# Cache logo at module load time
LOGO_B64 = _get_logo_b64()


# =============================================================================
# Base email template components - matches receipt PDF design language
# =============================================================================
def _get_base_styles() -> str:
    """Get the base CSS styles for all emails - matches receipt PDF design.

    Note: Only basic reset styles are included. All other styling is done
    inline on individual elements for maximum email client compatibility.
    """
    return """
        /* Reset */
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', sans-serif;
            line-height: 1.6;
            color: #f5f5f5;
            background-color: #0f0f0f;
            margin: 0;
            padding: 0;
        }
    """


class EmailTemplate(str, Enum):
    """Predefined email templates."""

    CONTACT_FORM = "contact_form"
    CHARON_ESCALATION = "charon_escalation"
    NEW_ORDER = "new_order"
    ORDER_PAID = "order_paid"
    ORDER_CONFIRMATION = "order_confirmation"
    PROXY_CREDENTIALS = "proxy_credentials"
    REFUND_REQUEST = "refund_request"
    REFUND_APPROVED = "refund_approved"
    REFUND_PROCESSED = "refund_processed"
    REFUND_REJECTED = "refund_rejected"
    TRIAL_CLAIMED = "trial_claimed"
    ADMIN_INVITE = "admin_invite"
    PASSWORD_RESET = "password_reset"
    CREDENTIALS_ROTATED = "credentials_rotated"


class EmailRecipient(BaseModel):
    """Email recipient with email and optional name."""

    email: EmailStr
    name: Optional[str] = None


class EmailContent(BaseModel):
    """Email content for sending."""

    subject: str
    html: str
    text: Optional[str] = None


class EmailResult(BaseModel):
    """Result of an email send operation."""

    success: bool
    message_id: Optional[str] = None
    status: Optional[str] = None
    error: Optional[str] = None


async def _send_via_resend(
    recipient: EmailRecipient,
    subject: str,
    html: str,
    text: Optional[str] = None,
) -> EmailResult:
    """Send email via Resend API."""
    if not settings.resend_api_key:
        logger.warning("RESEND_API_KEY not configured, skipping email send")
        _append_delivery_log(
            {
                "ts": datetime.now(timezone.utc).isoformat(),
                "to": recipient.email,
                "subject": subject,
                "status": "skipped_no_key",
                "error": "RESEND_API_KEY missing",
            }
        )
        return EmailResult(
            success=False,
            error="Email service not configured (RESEND_API_KEY missing)",
        )

    import hashlib
    import uuid
    from email.utils import formatdate

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(10.0, connect=15.0)) as client:
            # Build the recipient dict
            to = recipient.email
            if recipient.name:
                to = f"{recipient.name} <{recipient.email}>"

            # Generate unique Message-ID for email identification
            msg_id = f"<{uuid.uuid4()}@styxproxy.com>"

            # Generate unsubscribe URL
            unsub_token = hashlib.sha1((recipient.email + ":styxproxy_unsubscribe_v1").encode(), usedforsecurity=False).hexdigest()
            unsub_url = f"https://styxproxy.com/unsubscribe?email={recipient.email}&token={unsub_token}"

            response = await client.post(
                "https://api.resend.com/emails",
                json={
                    "from": settings.from_email,
                    "to": [to],
                    "subject": subject,
                    "html": html,
                    "text": text,
                    "headers": {
                        "List-Unsubscribe": f"<{unsub_url}>",
                        "List-Unsubscribe-Post": "List-Unsubscribe=One-Click",
                        "Precedence": "bulk",
                        "Message-ID": msg_id,
                        "Date": formatdate(timeval=None, localtime=False, usegmt=True),
                    },
                },
                headers={
                    "Authorization": f"Bearer {settings.resend_api_key}",
                    "Content-Type": "application/json",
                },
            )

            if response.status_code >= 400:
                error_body = response.text
                logger.error(
                    "Resend API error: status=%s, error=%s",
                    response.status_code,
                    error_body,
                )
                _append_delivery_log(
                    {
                        "ts": datetime.now(timezone.utc).isoformat(),
                        "to": recipient.email,
                        "subject": subject,
                        "status": "api_error",
                        "error": f"{response.status_code}: {error_body[:200]}",
                    }
                )
                return EmailResult(
                    success=False,
                    status="api_error",
                    error=f"Resend API error: {response.status_code} - {error_body}",
                )

            data = response.json()
            _append_delivery_log(
                {
                    "ts": datetime.now(timezone.utc).isoformat(),
                    "to": recipient.email,
                    "subject": subject,
                    "status": "queued",
                    "message_id": data.get("id"),
                }
            )
            return EmailResult(
                success=True,
                message_id=data.get("id"),
            )

    except httpx.HTTPError as e:
        logger.error("Failed to send email: %s", e)
        _append_delivery_log(
            {
                "ts": datetime.now(timezone.utc).isoformat(),
                "to": recipient.email,
                "subject": subject,
                "status": "http_error",
                "error": str(e),
            }
        )
        return EmailResult(
            success=False,
            status="http_error",
            error=f"HTTP error: {str(e)}",
        )
    except Exception as e:
        logger.error("Unexpected error sending email: %s", e)
        _append_delivery_log(
            {
                "ts": datetime.now(timezone.utc).isoformat(),
                "to": recipient.email,
                "subject": subject,
                "status": "unexpected_error",
                "error": str(e),
            }
        )
        return EmailResult(
            success=False,
            status="unexpected_error",
            error=f"Unexpected error: {str(e)}",
        )


async def send_email(
    to: str,
    subject: str,
    html: str,
    text: Optional[str] = None,
    from_email: Optional[str] = None,
    reply_to: Optional[str] = None,
    in_reply_to: Optional[str] = None,
    references: Optional[str] = None,
) -> EmailResult:
    """
    Generic send email function with optional threading headers.

    Args:
        to: Recipient email address
        subject: Email subject
        html: HTML body
        text: Plain text body (optional)
        from_email: Custom from address (defaults to settings.from_email)
        reply_to: Reply-To header
        in_reply_to: In-Reply-To header for threading
        references: References header for threading
    """
    if not settings.resend_api_key:
        logger.warning("RESEND_API_KEY not configured, skipping email send")
        return EmailResult(
            success=False,
            error="Email service not configured (RESEND_API_KEY missing)",
        )

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(10.0, connect=15.0)) as client:
            # Build the payload
            payload = {
                "from": from_email or settings.from_email,
                "to": [to],
                "subject": subject,
                "html": html,
                "text": text,
            }

            # Add optional headers
            headers = {
                "Authorization": f"Bearer {settings.resend_api_key}",
                "Content-Type": "application/json",
            }

            # Add reply_to if provided
            if reply_to:
                payload["reply_to"] = reply_to

            # Threading + List-Unsubscribe headers
            import hashlib
            import uuid
            from email.utils import formatdate

            # Generate unique Message-ID for email threading and identification
            msg_id = f"<{uuid.uuid4()}@styxproxy.com>"

            unsub_token = hashlib.sha1((to + ":styxproxy_unsubscribe_v1").encode(), usedforsecurity=False).hexdigest()
            unsub_url = f"https://styxproxy.com/unsubscribe?email={to}&token={unsub_token}"
            custom_headers = {
                "List-Unsubscribe": f"<{unsub_url}>",
                "List-Unsubscribe-Post": "List-Unsubscribe=One-Click",
                "Precedence": "bulk",
                "Message-ID": msg_id,
                "Date": formatdate(timeval=None, localtime=False, usegmt=True),
            }
            if in_reply_to:
                custom_headers["In-Reply-To"] = in_reply_to
            if references:
                custom_headers["References"] = references
            payload["headers"] = custom_headers

            response = await client.post(
                "https://api.resend.com/emails",
                json=payload,
                headers=headers,
            )

            if response.status_code >= 400:
                error_body = response.text
                logger.error(
                    "Resend API error: status=%s, error=%s",
                    response.status_code,
                    error_body,
                )
                return EmailResult(
                    success=False,
                    status="api_error",
                    error=f"Resend API error: {response.status_code} - {error_body}",
                )

            data = response.json()
            return EmailResult(
                success=True,
                message_id=data.get("id"),
            )

    except httpx.HTTPError as e:
        logger.error("Failed to send email: %s", e)
        return EmailResult(
            success=False,
            status="http_error",
            error=f"HTTP error: {str(e)}",
        )
    except Exception as e:
        logger.error("Unexpected error sending email: %s", e)
        return EmailResult(
            success=False,
            status="unexpected_error",
            error=f"Unexpected error: {str(e)}",
        )


def _render_header(right_label: str, right_sublabel: str = "") -> str:
    """Render the email header with logo and label - table-based layout."""
    return f"""
        <div style="height: 4px; background-color: #00D060;" aria-hidden="true"></div>
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
            <tr>
                <td style="padding: 24px 24px 20px;">
                    <table role="presentation" cellpadding="0" cellspacing="0" border="0">
                        <tr>
                            <td style="vertical-align: middle;">
                                <img src="data:image/png;base64,{LOGO_B64}" alt="Styxproxy" width="200" height="58" style="display:block;">
                                <div style="font-size: 10px; color: #9ca3af; text-transform: uppercase; letter-spacing: 0.5px; margin-top: 2px;">Anonymous Proxy Service</div>
                            </td>
                            <td style="vertical-align: middle; text-align: right; padding-left: 20px;">
                                <div style="font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; color: #00D060;">{right_label}</div>
                                <div style="font-size: 9px; color: #9ca3af; margin-top: 2px;">{right_sublabel}</div>
                            </td>
                        </tr>
                    </table>
                </td>
            </tr>
        </table>
        <div style="height: 1px; background-color: #262626; margin: 0 24px;" aria-hidden="true"></div>
    """


def _render_support_footer() -> str:
    """Render the support footer section - table-based layout."""
    return """
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color: #1a1a1a; border-radius: 3px; padding: 16px; margin-top: 20px;">
            <tr>
                <td>
                    <div style="font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; color: #f5f5f5; margin-bottom: 12px;">NEED HELP?</div>
                    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                        <tr>
                            <td style="font-size: 12px; color: #9ca3af; padding-bottom: 6px;">Chat:</td>
                            <td style="font-size: 12px; text-align: right; padding-bottom: 6px;"><a href="https://styxproxy.com/contact" style="color: #00D060; text-decoration: none; font-weight: 500;" rel="noopener noreferrer">styxproxy.com/contact</a></td>
                        </tr>
                        <tr>
                            <td style="font-size: 12px; color: #9ca3af; padding-bottom: 6px;">Email:</td>
                            <td style="font-size: 12px; text-align: right; padding-bottom: 6px;"><a href="mailto:support@styxproxy.com" style="color: #00D060; text-decoration: none; font-weight: 500;">support@styxproxy.com</a></td>
                        </tr>
                        <tr>
                            <td style="font-size: 12px; color: #9ca3af;">Web:</td>
                            <td style="font-size: 12px; text-align: right;"><a href="https://styxproxy.com" style="color: #00D060; text-decoration: none; font-weight: 500;" rel="noopener noreferrer">styxproxy.com</a></td>
                        </tr>
                    </table>
                </td>
            </tr>
        </table>
    """


def _render_footer() -> str:
    """Render the email footer with unsubscribe link and physical address."""
    return """
        <div role="contentinfo" style="text-align: center; padding: 20px 24px; color: #9ca3af; font-size: 11px;">
            <div style="font-style: italic; margin-bottom: 8px;">This receipt was generated automatically. No signature required.</div>
            <div style="margin-bottom: 8px;">
                <a href="https://styxproxy.com/unsubscribe" style="color: #9ca3af; text-decoration: underline;">Unsubscribe</a>
            </div>
            <div style="margin-bottom: 8px;">Styxproxy, Lagos, Nigeria</div>
            <div style="color: #9ca3af;">&copy; 2026 Styxproxy &mdash; Anonymous proxy service for the discerning.</div>
        </div>
        <div style="height: 4px; background-color: #00D060;" aria-hidden="true"></div>
    """


# =============================================================================
# Support Reply Email Template
# =============================================================================


def _render_support_reply_email(
    customer_name: str,
    original_subject: str,
    reply_body_html: str,
    admin_name: str = "Dannion",
) -> EmailContent:
    """Render support reply email - branded wrapper around admin reply.

    This template wraps a support reply in the Styxproxy brand design:
    - Top green accent bar
    - Logo header with "Styxproxy Support" subtitle
    - "REPLY" pill (green)
    - "Hi [customer_name]," heading
    - Original subject context: "Re: [original subject]"
    - Reply body in card
    - NEED HELP? footer
    - Bottom green accent bar
    """
    base_styles = _get_base_styles()

    # Build the greeting
    greeting = f"Hi {customer_name}," if customer_name else "Hi there,"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Re: {original_subject}</title>
    <style>
        {base_styles}
    </style>
</head>
<body>
    <div style="width: 100%; background-color: #0f0f0f;">
        <div style="max-width: 600px; margin: 0 auto; padding: 0;">
            <div style="height: 4px; background-color: #00D060;" aria-hidden="true"></div>
            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                <tr>
                    <td style="padding: 24px 24px 20px;">
                        <table role="presentation" cellpadding="0" cellspacing="0" border="0">
                            <tr>
                                <td style="vertical-align: middle;">
                                    <img src="data:image/png;base64,{LOGO_B64}" alt="Styxproxy" width="200" height="58" style="display:block;">
                                    <div style="font-size: 10px; color: #9ca3af; text-transform: uppercase; letter-spacing: 0.5px; margin-top: 2px;">Styxproxy Support</div>
                                </td>
                                <td style="vertical-align: middle; text-align: right; padding-left: 20px;">
                                    <div style="font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; color: #00D060;">REPLY</div>
                                </td>
                            </tr>
                        </table>
                    </td>
                </tr>
            </table>
            <div style="height: 1px; background-color: #262626; margin: 0 24px;" aria-hidden="true"></div>

            <div role="main" style="padding: 24px;">
                <div style="font-size: 9px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; color: #9ca3af; margin-bottom: 8px;">SUPPORT REPLY</div>
                <div style="font-size: 22px; font-weight: 700; color: #f5f5f5; margin-bottom: 8px;">{greeting}</div>

                <div style="color: #9ca3af; font-size: 13px; margin-bottom: 16px;">
                    Re: {original_subject}
                </div>

                <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color: #1a1a1a; border-radius: 3px; padding: 20px; margin: 16px 0;">
                    <tr>
                        <td>
                            {reply_body_html}
                        </td>
                    </tr>
                </table>

                <p style="color: #9ca3af; font-size: 12px; margin-top: 20px;">
                    This reply was sent by {admin_name} from Styxproxy Support.
                </p>

                {_render_support_footer()}
            </div>

            <div role="contentinfo" style="text-align: center; padding: 20px 24px; color: #9ca3af; font-size: 11px;">
                <div style="font-style: italic; margin-bottom: 8px;">Automated support response</div>
                <div style="margin-bottom: 8px;">
                    <a href="https://styxproxy.com/unsubscribe" style="color: #9ca3af; text-decoration: underline;">Unsubscribe</a>
                </div>
                <div style="margin-bottom: 8px;">Styxproxy, Lagos, Nigeria</div>
                <div style="color: #9ca3af;">&copy; 2026 Styxproxy &mdash; Anonymous proxy service for the discerning.</div>
            </div>
            <div style="height: 4px; background-color: #00D060;" aria-hidden="true"></div>
        </div>
    </div>
</body>
</html>
"""

    # Simple text version - extract the HTML to text conversion
    text_reply = reply_body_html.replace("<br>", "\n").replace("<p>", "").replace("</p>", "\n")
    text = f"""Re: {original_subject}

{greeting}

{text_reply}

---
This reply was sent by {admin_name} from Styxproxy Support.

Need help? Contact us at support@styxproxy.com or visit styxproxy.com

&copy; 2026 Styxproxy
"""

    return EmailContent(
        subject=f"Re: {original_subject}",
        html=html,
        text=text,
    )


# =============================================================================
# Contact Form Email Templates
# =============================================================================


def _render_contact_form_email(
    name: str,
    email: str,
    message: str,
    phone: Optional[str] = None,
    ip_address: Optional[str] = None,
) -> EmailContent:
    """Render contact form submission email (to admin) - table-based layout."""
    phone_html = (
        f"""
                    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                        <tr>
                            <td style="padding: 12px 0; border-bottom: 1px solid #262626;">
                                <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                                    <tr>
                                        <td style="font-size: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; color: #9ca3af;">Phone</td>
                                        <td style="font-size: 14px; font-weight: 600; color: #f5f5f5; text-align: right;">{phone}</td>
                                    </tr>
                                </table>
                            </td>
                        </tr>
                    </table>"""
        if phone
        else ""
    )

    ip_html = (
        f"""
                    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                        <tr>
                            <td style="padding: 12px 0; border-bottom: 1px solid #262626;">
                                <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                                    <tr>
                                        <td style="font-size: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; color: #9ca3af;">IP Address</td>
                                        <td style="font-size: 14px; font-weight: 600; color: #f5f5f5; text-align: right;">{ip_address}</td>
                                    </tr>
                                </table>
                            </td>
                        </tr>
                    </table>"""
        if ip_address
        else ""
    )

    base_styles = _get_base_styles()

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>New Contact Form Submission</title>
    <style>
        {base_styles}
    </style>
</head>
<body>
    <div style="width: 100%; background-color: #0f0f0f;">
        <div style="max-width: 600px; margin: 0 auto; padding: 0;">
            {_render_header("CONTACT SUBMISSION", "styxproxy.com")}

            <div role="main" style="padding: 24px;">
                <div style="font-size: 9px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; color: #9ca3af; margin-bottom: 8px;">NEW MESSAGE</div>
                <div style="font-size: 22px; font-weight: 700; color: #f5f5f5; margin-bottom: 8px;">New message from {name}</div>

                <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color: #1a1a1a; border-radius: 3px; padding: 20px; margin: 16px 0;">
                    <tr>
                        <td>
                            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                                <tr>
                                    <td style="padding: 12px 0; border-bottom: 1px solid #262626;">
                                        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                                            <tr>
                                                <td style="font-size: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; color: #9ca3af;">Name</td>
                                                <td style="font-size: 14px; font-weight: 600; color: #f5f5f5; text-align: right;">{name}</td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                            </table>
                            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                                <tr>
                                    <td style="padding: 12px 0; border-bottom: 1px solid #262626;">
                                        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                                            <tr>
                                                <td style="font-size: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; color: #9ca3af;">Email</td>
                                                <td style="font-size: 14px; font-weight: 600; color: #00D060; text-align: right;">{email}</td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                            </table>
                            {phone_html}
                            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                                <tr>
                                    <td style="padding: 12px 0; border-bottom: 1px solid #262626;">
                                        <div style="font-size: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; color: #9ca3af;">Message</div>
                                    </td>
                                </tr>
                            </table>
                            <div style="padding: 12px 0; color: #f5f5f5; font-size: 14px; line-height: 1.6;">
                                {message.replace(chr(10), "<br>")}
                            </div>
                            {ip_html}
                        </td>
                    </tr>
                </table>

                <div style="text-align: center; margin-top: 20px;">
                    <a href="https://styxproxy.com/admin/contacts" style="display: inline-block; background-color: #00D060; color: #000000; font-weight: 700; padding: 14px 28px; border-radius: 4px; text-decoration: none;" rel="noopener noreferrer">View in Admin Panel</a>
                </div>

                {_render_support_footer()}
            </div>

            {_render_footer()}
        </div>
    </div>
</body>
</html>
"""

    text = f"""New Contact Form Submission

Name: {name}
Email: {email}
{phone + chr(10) if phone else ""}
Message:
{message}

Submitted at {datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")} UTC
&copy; 2026 Styxproxy
"""

    return EmailContent(
        subject="[Styxproxy] New Contact Form Submission",
        html=html,
        text=text,
    )


def _render_customer_confirmation_email(
    name: str,
) -> str:
    """Render customer confirmation email - table-based layout."""
    base_styles = _get_base_styles()

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Message Received</title>
    <style>
        {base_styles}
    </style>
</head>
<body>
    <div style="width: 100%; background-color: #0f0f0f;">
        <div style="max-width: 600px; margin: 0 auto; padding: 0;">
            {_render_header("MESSAGE RECEIVED", "styxproxy.com")}

            <div role="main" style="padding: 24px;">
                <div style="font-size: 9px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; color: #9ca3af; margin-bottom: 8px;">THANK YOU</div>
                <div style="font-size: 22px; font-weight: 700; color: #f5f5f5; margin-bottom: 8px;">Thanks for reaching out, {name}.</div>
                <div style="font-size: 14px; color: #9ca3af; margin-bottom: 20px;">We received your message and will respond within 24 hours.</div>

                <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color: #1a1a1a; border-radius: 3px; padding: 20px; margin: 16px 0;">
                    <tr>
                        <td style="text-align: center; padding: 20px 0;">
                            <div style="font-size: 40px; margin-bottom: 16px;" aria-hidden="true">&#10003;</div>
                            <div style="color: #f5f5f5; font-size: 16px;">
                                Your message has been received. Our team will get back to you as soon as possible.
                            </div>
                        </td>
                    </tr>
                </table>

                <div style="text-align: center; margin-top: 20px;">
                    <a href="https://styxproxy.com" style="display: inline-block; background-color: #00D060; color: #000000; font-weight: 700; padding: 14px 28px; border-radius: 4px; text-decoration: none;" rel="noopener noreferrer">Visit styxproxy.com</a>
                </div>

                {_render_support_footer()}
            </div>

            {_render_footer()}
        </div>
    </div>
</body>
</html>
"""


# =============================================================================
# Charon Escalation Email Template
# =============================================================================


def _render_charon_escalation_email(
    conversation_id: str,
    customer_email: Optional[str],
    customer_phone: Optional[str],
    message: str,
    history_summary: str,
) -> EmailContent:
    """Render Charon escalation notification email - alert style with amber/red."""
    contact_info = ""
    if customer_email:
        contact_info += f"""
                    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                        <tr>
                            <td style="padding: 12px 0; border-bottom: 1px solid #262626;">
                                <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                                    <tr>
                                        <td style="font-size: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; color: #9ca3af;">Email</td>
                                        <td style="font-size: 14px; font-weight: 600; color: #00D060; text-align: right;">{customer_email}</td>
                                    </tr>
                                </table>
                            </td>
                        </tr>
                    </table>"""
    if customer_phone:
        contact_info += f"""
                    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                        <tr>
                            <td style="padding: 12px 0; border-bottom: 1px solid #262626;">
                                <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                                    <tr>
                                        <td style="font-size: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; color: #9ca3af;">Phone</td>
                                        <td style="font-size: 14px; font-weight: 600; color: #f5f5f5; text-align: right;">{customer_phone}</td>
                                    </tr>
                                </table>
                            </td>
                        </tr>
                    </table>"""

    base_styles = _get_base_styles()

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Charon Escalation</title>
    <style>
        {base_styles}
    </style>
</head>
<body>
    <div style="width: 100%; background-color: #0f0f0f;">
        <div style="max-width: 600px; margin: 0 auto; padding: 0;">
            {_render_header("ESCALATION", "Action Required")}

            <div role="main" style="padding: 24px;">
                <div style="font-size: 9px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; color: #9ca3af; margin-bottom: 8px;">CHARON ESCALATION</div>
                <div style="font-size: 22px; font-weight: 700; color: #f5f5f5; margin-bottom: 8px;">Charon escalated a conversation</div>
                <div style="font-size: 14px; color: #9ca3af; margin-bottom: 20px;">Immediate attention required</div>

                <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color: #1a1a1a; border-radius: 3px; padding: 20px; margin: 16px 0;">
                    <tr>
                        <td>
                            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                                <tr>
                                    <td style="padding: 12px 0; border-bottom: 1px solid #262626;">
                                        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                                            <tr>
                                                <td style="font-size: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; color: #9ca3af;">Conversation ID</td>
                                                <td style="font-size: 18px; font-weight: 700; color: #00D060; text-align: right;">{conversation_id[:16]}...</td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                            </table>
                            {contact_info}
                            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                                <tr>
                                    <td style="padding: 12px 0; border-bottom: 1px solid #262626;">
                                        <div style="font-size: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; color: #9ca3af;">Latest Message</div>
                                    </td>
                                </tr>
                            </table>
                            <div style="padding: 12px 0; color: #f5f5f5; font-size: 14px; line-height: 1.6;">
                                {message.replace(chr(10), "<br>")}
                            </div>
                            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                                <tr>
                                    <td style="padding: 12px 0; border-bottom: 1px solid #262626;">
                                        <div style="font-size: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; color: #9ca3af;">Conversation History</div>
                                    </td>
                                </tr>
                            </table>
                            <div style="padding: 12px 0; color: #9ca3af; font-size: 12px; line-height: 1.6; font-family: monospace; white-space: pre-wrap;">
                                {history_summary}
                            </div>
                        </td>
                    </tr>
                </table>

                <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color: #1a1a1a; border-left: 4px solid #f59e0b; padding: 16px; border-radius: 0 3px 3px 0; margin: 16px 0;">
                    <tr>
                        <td style="font-size: 13px; color: #f59e0b;">
                            <strong>Action Required:</strong> Please respond to this conversation as soon as possible.
                        </td>
                    </tr>
                </table>
            </div>

            {_render_footer()}
        </div>
    </div>
</body>
</html>
"""

    text = f"""Charon Escalation Alert

Conversation ID: {conversation_id}
{("Email: " + customer_email) if customer_email else ""}
{("Phone: " + customer_phone) if customer_phone else ""}

Latest Message:
{message}

Conversation History:
{history_summary}

Escalated at {datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")} UTC
"""

    return EmailContent(
        subject=f"[Styxproxy] Charon Escalation - {conversation_id[:8]}",
        html=html,
        text=text,
    )


# =============================================================================
# Admin Notification Email Template
# =============================================================================


def _render_admin_notification_email(
    title: str,
    details: dict,
) -> EmailContent:
    """Render admin notification email - dynamic title pill."""
    details_html = "".join(
        f"""
                    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                        <tr>
                            <td style="padding: 12px 0; border-bottom: 1px solid #262626;">
                                <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                                    <tr>
                                        <td style="font-size: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; color: #9ca3af;">{k}</td>
                                        <td style="font-size: 14px; font-weight: 600; color: #f5f5f5; text-align: right;">{v}</td>
                                    </tr>
                                </table>
                            </td>
                        </tr>
                    </table>"""
        for k, v in details.items()
    )

    base_styles = _get_base_styles()

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        {base_styles}
    </style>
</head>
<body>
    <div style="width: 100%; background-color: #0f0f0f;">
        <div style="max-width: 600px; margin: 0 auto; padding: 0;">
            {_render_header(title.upper(), "Admin Notification")}

            <div role="main" style="padding: 24px;">
                <div style="font-size: 9px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; color: #9ca3af; margin-bottom: 8px;">NOTIFICATION</div>
                <div style="font-size: 22px; font-weight: 700; color: #f5f5f5; margin-bottom: 8px;">{title}</div>

                <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color: #1a1a1a; border-radius: 3px; padding: 20px; margin: 16px 0;">
                    <tr>
                        <td>
                            {details_html}
                        </td>
                    </tr>
                </table>
            </div>

            {_render_footer()}
        </div>
    </div>
</body>
</html>
"""

    text_details = "\n".join(f"{k}: {v}" for k, v in details.items())

    text = f"""{title}

{text_details}

Notification sent at {datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")} UTC
"""

    return EmailContent(
        subject=f"[Styxproxy Admin] {title}",
        html=html,
        text=text,
    )


# =============================================================================
# Admin Invite Email Template
# =============================================================================


def _render_admin_invite_email(
    email: str,
    role: str,
    invite_code: str,
    expires_in_hours: int,
) -> EmailContent:
    """Render admin invite email - table-based layout."""
    setup_link = "https://styxproxy.com/admin/setup"

    base_styles = _get_base_styles()

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Admin Invite</title>
    <style>
        {base_styles}
    </style>
</head>
<body>
    <div style="width: 100%; background-color: #0f0f0f;">
        <div style="max-width: 600px; margin: 0 auto; padding: 0;">
            {_render_header("ADMIN INVITE", "styxproxy.com")}

            <div role="main" style="padding: 24px;">
                <div style="font-size: 9px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; color: #9ca3af; margin-bottom: 8px;">INVITATION</div>
                <div style="font-size: 22px; font-weight: 700; color: #f5f5f5; margin-bottom: 8px;">You're invited to Styxproxy Admin</div>
                <div style="font-size: 14px; color: #9ca3af; margin-bottom: 20px;">You've been granted access to the admin panel</div>

                <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color: #1a1a1a; border-radius: 3px; padding: 20px; margin: 16px 0;">
                    <tr>
                        <td>
                            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                                <tr>
                                    <td style="padding: 12px 0; border-bottom: 1px solid #262626;">
                                        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                                            <tr>
                                                <td style="font-size: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; color: #9ca3af;">Role</td>
                                                <td style="font-size: 14px; font-weight: 600; color: #00D060; text-align: right;">{role}</td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                            </table>
                            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                                <tr>
                                    <td style="padding: 12px 0; border-bottom: 1px solid #262626;">
                                        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                                            <tr>
                                                <td style="font-size: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; color: #9ca3af;">Email</td>
                                                <td style="font-size: 14px; font-weight: 600; color: #f5f5f5; text-align: right;">{email}</td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                            </table>
                            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                                <tr>
                                    <td style="padding: 12px 0; border-bottom: 1px solid #262626;">
                                        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                                            <tr>
                                                <td style="font-size: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; color: #9ca3af;">Expires</td>
                                                <td style="font-size: 14px; font-weight: 600; color: #f5f5f5; text-align: right;">{expires_in_hours} hours</td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                </table>

                <div style="text-align: center; margin-top: 20px;">
                    <a href="{setup_link}" style="display: inline-block; background-color: #00D060; color: #000000; font-weight: 700; padding: 14px 28px; border-radius: 4px; text-decoration: none;" rel="noopener noreferrer">Open Setup Page</a>
                </div>

                <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-top: 20px; padding: 16px; background-color: #0f0f0f; border: 1px dashed #2a2a2a; border-radius: 8px;">
                    <tr>
                        <td>
                            <p style="margin: 0 0 8px; color: #9ca3af; font-size: 12px; text-transform: uppercase; letter-spacing: 0.5px;">
                                Your Invite Code
                            </p>
                            <p style="margin: 0; font-family: 'Courier New', monospace; font-size: 20px; font-weight: bold; color: #00D060; text-align: center; word-break: break-all;">
                                {invite_code}
                            </p>
                            <p style="margin: 8px 0 0; color: #9ca3af; font-size: 12px; text-align: center;">
                                Type this code in on the setup page. It is also bound to your email ({email}); the server will reject any other email at the credentials step.
                            </p>
                        </td>
                    </tr>
                </table>

                <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color: #1a1a1a; border-left: 4px solid #f59e0b; padding: 16px; border-radius: 0 3px 3px 0; margin: 16px 0;">
                    <tr>
                        <td style="font-size: 13px; color: #f59e0b;">
                            <strong>Important:</strong> This invite expires in {expires_in_hours} hours. If you didn't request this, please ignore this email.
                        </td>
                    </tr>
                </table>
            </div>

            {_render_footer()}
        </div>
    </div>
</body>
</html>
"""

    text = f"""Admin Invite - Styxproxy

You've been invited to join the Styxproxy Admin Panel.

Role: {role}
Email: {email}

Set up your account: {setup_link}

Your invite code (type it in on the setup page):

    {invite_code}

This code is bound to {email}. If you sign in with any other email,
the server will reject it.

This invite expires in {expires_in_hours} hours.

If you didn't request this, please ignore this email.

- Styxproxy Admin
"""

    return EmailContent(
        subject="You're invited to Styxproxy Admin",
        html=html,
        text=text,
    )


# =============================================================================
# Password Reset Email Template
# =============================================================================


def _render_password_reset_email(
    email: str,
    reset_token: str,
) -> EmailContent:
    """Render password reset email - table-based layout."""
    reset_link = f"https://styxproxy.com/admin/reset-password?token={reset_token}"

    base_styles = _get_base_styles()

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Password Reset</title>
    <style>
        {base_styles}
    </style>
</head>
<body>
    <div style="width: 100%; background-color: #0f0f0f;">
        <div style="max-width: 600px; margin: 0 auto; padding: 0;">
            {_render_header("PASSWORD RESET", "styxproxy.com")}

            <div role="main" style="padding: 24px;">
                <div style="font-size: 9px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; color: #9ca3af; margin-bottom: 8px;">SECURITY</div>
                <div style="font-size: 22px; font-weight: 700; color: #f5f5f5; margin-bottom: 8px;">Reset your admin password</div>
                <div style="font-size: 14px; color: #9ca3af; margin-bottom: 20px;">Create a new password for your account</div>

                <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color: #1a1a1a; border-radius: 3px; padding: 20px; margin: 16px 0;">
                    <tr>
                        <td style="text-align: center; padding: 20px 0;">
                            <div style="font-size: 40px; margin-bottom: 16px;" aria-hidden="true">&#128274;</div>
                            <div style="color: #f5f5f5; font-size: 14px; margin-bottom: 20px;">
                                We received a request to reset your Styxproxy Admin password.
                            </div>
                        </td>
                    </tr>
                </table>

                <div style="text-align: center; margin-top: 20px;">
                    <a href="{reset_link}" style="display: inline-block; background-color: #00D060; color: #000000; font-weight: 700; padding: 14px 28px; border-radius: 4px; text-decoration: none;" rel="noopener noreferrer">Reset Password</a>
                </div>

                <p style="color: #9ca3af; font-size: 13px; margin-top: 16px; text-align: center;">
                    Or copy this link: <span style="color: #00D060; word-break: break-all;">{reset_link}</span>
                </p>

                <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color: #1a1a1a; border-left: 4px solid #f59e0b; padding: 16px; border-radius: 0 3px 3px 0; margin: 16px 0;">
                    <tr>
                        <td style="font-size: 13px; color: #f59e0b;">
                            <strong>Note:</strong> This link expires in <strong>1 hour</strong>.<br><br>
                            If you didn't request this, please ignore this email. Your password will remain unchanged.
                        </td>
                    </tr>
                </table>
            </div>

            {_render_footer()}
        </div>
    </div>
</body>
</html>
"""

    text = f"""Password Reset - Styxproxy Admin

We received a request to reset your Styxproxy Admin password.

Reset Link: {reset_link}

This link expires in 1 hour.

If you didn't request this, please ignore this email. Your password will remain unchanged.

- Styxproxy Admin
"""

    return EmailContent(
        subject="Reset your Styxproxy Admin password",
        html=html,
        text=text,
    )


# =============================================================================
# Order Confirmation Email Template (Pending Payment)
# =============================================================================


def _render_order_confirmation_email(
    customer_name: str,
    order_id: str,
    plan_code: str,
    amount: float,
    currency: str,
    quantity: int,
) -> EmailContent:
    """Render order confirmation email (pending payment) - table-based layout."""
    base_styles = _get_base_styles()

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Order Placed</title>
    <style>
        {base_styles}
    </style>
</head>
<body>
    <div style="width: 100%; background-color: #0f0f0f;">
        <div style="max-width: 600px; margin: 0 auto; padding: 0;">
            {_render_header("PAYMENT PENDING", "styxproxy.com")}

            <div role="main" style="padding: 24px;">
                <div style="font-size: 9px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; color: #9ca3af; margin-bottom: 8px;">ORDER CONFIRMATION</div>
                <div style="font-size: 22px; font-weight: 700; color: #f5f5f5; margin-bottom: 8px;">Thanks for your order, {customer_name}!</div>
                <div style="font-size: 14px; color: #9ca3af; margin-bottom: 20px;">Complete your payment to activate your proxy</div>

                <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color: #1a1a1a; border-radius: 3px; padding: 20px; margin: 16px 0;">
                    <tr>
                        <td>
                            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                                <tr>
                                    <td style="padding: 12px 0; border-bottom: 1px solid #262626;">
                                        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                                            <tr>
                                                <td style="font-size: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; color: #9ca3af;">Order ID</td>
                                                <td style="font-size: 18px; font-weight: 700; color: #00D060; text-align: right;">{order_id[:16]}...</td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                            </table>
                            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                                <tr>
                                    <td style="padding: 12px 0; border-bottom: 1px solid #262626;">
                                        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                                            <tr>
                                                <td style="font-size: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; color: #9ca3af;">Plan</td>
                                                <td style="font-size: 14px; font-weight: 600; color: #f5f5f5; text-align: right;">{plan_code}</td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                            </table>
                            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                                <tr>
                                    <td style="padding: 12px 0; border-bottom: 1px solid #262626;">
                                        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                                            <tr>
                                                <td style="font-size: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; color: #9ca3af;">Quantity</td>
                                                <td style="font-size: 14px; font-weight: 600; color: #f5f5f5; text-align: right;">{quantity} {"unit" if quantity == 1 else "units"}</td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                            </table>
                            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                                <tr>
                                    <td style="padding: 12px 0; border-bottom: 1px solid #262626;">
                                        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                                            <tr>
                                                <td style="font-size: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; color: #9ca3af;">Amount</td>
                                                <td style="font-size: 18px; font-weight: 700; color: #00D060; text-align: right;">{currency} {amount:,.2f}</td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                </table>

                <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color: #1a1a1a; border-left: 4px solid #f59e0b; padding: 16px; border-radius: 0 3px 3px 0; margin: 16px 0;">
                    <tr>
                        <td style="font-size: 13px; color: #f59e0b;">
                            <strong>Next step:</strong> Complete your payment. Once confirmed, your proxy credentials will be sent to this email automatically.
                        </td>
                    </tr>
                </table>

                <div style="text-align: center; margin-top: 20px;">
                    <a href="https://styxproxy.com/pay/{order_id}" style="display: inline-block; background-color: #00D060; color: #000000; font-weight: 700; padding: 14px 28px; border-radius: 4px; text-decoration: none;" rel="noopener noreferrer">Complete Payment</a>
                </div>

                {_render_support_footer()}
            </div>

            {_render_footer()}
        </div>
    </div>
</body>
</html>
"""

    text = f"""Order Placed - {order_id}

Hi {customer_name},

Your order has been received. Complete your payment to activate your proxy.

Order ID: {order_id}
Plan: {plan_code}
Quantity: {quantity}
Amount: {currency} {amount:,.2f}

Next step: Complete your payment. Your proxy credentials will be sent once confirmed.

Need help? Contact us at styxproxy.com

- Styxproxy
"""

    return EmailContent(
        subject=f"[Styxproxy] Order Placed - {order_id[:8]}",
        html=html,
        text=text,
    )


# =============================================================================
# Proxy Credentials Email Template
# =============================================================================


def _render_proxy_credentials_email(
    customer_name: str,
    order_id: str,
    tx_ref: str,
    plan_code: str,
    amount: float,
    currency: str,
    quantity: int,
    styxproxy_username: str,
    styxproxy_password: str,
    proxy_ip: str,
    proxy_port: int,
    protocol: str,
    expires_at: datetime,
    payment_method: str = "Card / Bank / USSD / QR",
) -> EmailContent:
    """Render proxy credentials email (order paid + active) - table-based layout."""
    expires_str = expires_at.strftime("%Y-%m-%d %H:%M UTC") if expires_at else "N/A"
    full_format = f"http://{styxproxy_username}:{styxproxy_password}@{proxy_ip}:{proxy_port}"

    base_styles = _get_base_styles()

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Your Proxy is Ready</title>
    <style>
        {base_styles}
    </style>
</head>
<body>
    <div style="width: 100%; background-color: #0f0f0f;">
        <div style="max-width: 600px; margin: 0 auto; padding: 0;">
            {_render_header("FULFILLED", "styxproxy.com")}

            <div role="main" style="padding: 24px;">
                <div style="font-size: 9px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; color: #9ca3af; margin-bottom: 8px;">ORDER CONFIRMATION</div>
                <div style="font-size: 22px; font-weight: 700; color: #f5f5f5; margin-bottom: 8px;">Your proxy is ready, {customer_name}!</div>
                <div style="font-size: 14px; color: #9ca3af; margin-bottom: 20px;">Your payment has been confirmed and proxy is active</div>

                <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color: #1a1a1a; border-radius: 3px; padding: 20px; margin: 16px 0;">
                    <tr>
                        <td>
                            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                                <tr>
                                    <td style="padding: 12px 0; border-bottom: 1px solid #262626;">
                                        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                                            <tr>
                                                <td style="font-size: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; color: #9ca3af;">Transaction Reference</td>
                                                <td style="font-size: 14px; font-weight: 600; color: #00D060; text-align: right;">{tx_ref}</td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                            </table>
                            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                                <tr>
                                    <td style="padding: 12px 0; border-bottom: 1px solid #262626;">
                                        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                                            <tr>
                                                <td style="font-size: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; color: #9ca3af;">Order ID</td>
                                                <td style="font-size: 14px; font-weight: 600; color: #f5f5f5; text-align: right;">{order_id[:16]}...</td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                            </table>
                            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                                <tr>
                                    <td style="padding: 12px 0; border-bottom: 1px solid #262626;">
                                        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                                            <tr>
                                                <td style="font-size: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; color: #9ca3af;">Date</td>
                                                <td style="font-size: 14px; font-weight: 600; color: #f5f5f5; text-align: right;">{datetime.utcnow().strftime("%Y-%m-%d")}</td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                            </table>
                            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                                <tr>
                                    <td style="padding: 12px 0; border-bottom: 1px solid #262626;">
                                        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                                            <tr>
                                                <td style="font-size: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; color: #9ca3af;">Method</td>
                                                <td style="font-size: 14px; font-weight: 600; color: #f5f5f5; text-align: right;">{payment_method}</td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                </table>

                <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-bottom: 12px;">
                    <tr>
                        <td style="font-size: 9px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; color: #9ca3af; padding: 12px 0; border-bottom: 1px solid #262626;">ITEMS</td>
                        <td style="font-size: 9px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; color: #9ca3af; padding: 12px 0; border-bottom: 1px solid #262626; text-align: right;">AMOUNT</td>
                    </tr>
                </table>
                <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                    <tr>
                        <td style="padding: 8px 0; color: #9ca3af; font-size: 13px;">{plan_code} x {quantity}</td>
                        <td style="padding: 8px 0; color: #9ca3af; font-size: 13px; text-align: right;">{currency} {amount:,.2f}</td>
                    </tr>
                </table>

                <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color: #00D060; color: #000000; padding: 10px 16px; border-radius: 2px; margin-top: 16px;">
                    <tr>
                        <td style="font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px;">Total Paid</td>
                        <td style="font-size: 16px; font-weight: 700; text-align: right;">{currency} {amount:,.2f}</td>
                    </tr>
                </table>

                <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color: #0f0f0f; border: 1px solid #00D060; border-radius: 3px; padding: 16px; margin: 16px 0;">
                    <tr>
                        <td>
                            <div style="font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; color: #00D060; margin-bottom: 16px;">YOUR PROXY CREDENTIALS</div>
                            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                                <tr>
                                    <td style="padding: 10px 0; border-bottom: 1px solid #262626;">
                                        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                                            <tr>
                                                <td style="font-size: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; color: #9ca3af;">Username</td>
                                                <td style="font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace; font-size: 13px; font-weight: 600; color: #00D060; text-align: right; word-break: break-all;">{styxproxy_username}</td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                            </table>
                            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                                <tr>
                                    <td style="padding: 10px 0; border-bottom: 1px solid #262626;">
                                        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                                            <tr>
                                                <td style="font-size: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; color: #9ca3af;">Password</td>
                                                <td style="font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace; font-size: 13px; font-weight: 600; color: #00D060; text-align: right; word-break: break-all;">{styxproxy_password}</td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                            </table>
                            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                                <tr>
                                    <td style="padding: 10px 0; border-bottom: 1px solid #262626;">
                                        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                                            <tr>
                                                <td style="font-size: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; color: #9ca3af;">Proxy Address</td>
                                                <td style="font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace; font-size: 13px; font-weight: 600; color: #00D060; text-align: right; word-break: break-all;">{proxy_ip}:{proxy_port}</td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                            </table>
                            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                                <tr>
                                    <td style="padding: 10px 0; border-bottom: 1px solid #262626;">
                                        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                                            <tr>
                                                <td style="font-size: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; color: #9ca3af;">Protocol</td>
                                                <td style="font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace; font-size: 13px; font-weight: 600; color: #00D060; text-align: right;">{protocol.upper()}</td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                            </table>
                            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                                <tr>
                                    <td style="padding: 10px 0; border-bottom: 1px solid #262626;">
                                        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                                            <tr>
                                                <td style="font-size: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; color: #9ca3af;">Full Format</td>
                                                <td style="font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace; font-size: 11px; font-weight: 600; color: #00D060; text-align: right; word-break: break-all;">{full_format[:50]}...</td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                            </table>
                            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                                <tr>
                                    <td style="padding: 10px 0; border-bottom: 1px solid #262626;">
                                        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                                            <tr>
                                                <td style="font-size: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; color: #9ca3af;">Expires</td>
                                                <td style="font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace; font-size: 13px; font-weight: 600; color: #00D060; text-align: right;">{expires_str}</td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                            </table>
                            <div style="margin-top: 12px; padding: 12px; background-color: #1a1a1a; border-left: 4px solid #f59e0b; border-radius: 0 3px 3px 0;">
                                <div style="font-size: 12px; color: #f59e0b;">
                                    <strong>Security:</strong> Keep these credentials confidential. Do not share them with anyone.
                                </div>
                            </div>
                        </td>
                    </tr>
                </table>

                {_render_support_footer()}
            </div>

            {_render_footer()}
        </div>
    </div>
</body>
</html>
"""

    text = f"""Payment Confirmed - Your Proxy is Ready!

Hi {customer_name},

Great news! Your payment has been confirmed and your proxy is now active.

Order ID: {order_id}
Transaction Ref: {tx_ref}
Plan: {plan_code}
Quantity: {quantity}
Amount Paid: {currency} {amount:,.2f}

=== YOUR PROXY CREDENTIALS ===
Username: {styxproxy_username}
Password: {styxproxy_password}
Proxy: {proxy_ip}:{proxy_port}
Protocol: {protocol.upper()}
Full Format: {full_format}
Expires: {expires_str}
================================

You can now use your proxy immediately.

Need help? Contact us at styxproxy.com

- Styxproxy
"""

    return EmailContent(
        subject=f"[Styxproxy] Payment Confirmed - Your Proxy is Ready! - {order_id[:8]}",
        html=html,
        text=text,
    )


# =============================================================================
# Order Active Email (Combined Payment + Credentials) - The Receipt Email
# =============================================================================


async def send_order_active_email(
    customer_email: str,
    customer_name: str,
    order_id: str,
    tx_ref: str,
    plan_code: str,
    amount: float,
    currency: str,
    quantity: int,
    styxproxy_username: str,
    styxproxy_password: str,
    proxy_ip: str,
    proxy_port: int,
    protocol: str,
    expires_at: datetime,
    payment_method: str = "Card / Bank / USSD / QR",
) -> EmailResult:
    """Send order confirmation + credentials in ONE email when order is paid and proxy is active.

    This is the most important email - it looks nearly identical to the receipt PDF.
    """
    content = _render_proxy_credentials_email(
        customer_name=customer_name,
        order_id=order_id,
        tx_ref=tx_ref,
        plan_code=plan_code,
        amount=amount,
        currency=currency,
        quantity=quantity,
        styxproxy_username=styxproxy_username,
        styxproxy_password=styxproxy_password,
        proxy_ip=proxy_ip,
        proxy_port=proxy_port,
        protocol=protocol,
        expires_at=expires_at,
        payment_method=payment_method,
    )
    recipient = EmailRecipient(email=customer_email, name=customer_name)

    return await _send_via_resend(
        recipient=recipient,
        subject=content.subject,
        html=content.html,
        text=content.text,
    )


# =============================================================================
# Refund Processed Email Template
# =============================================================================


def _render_refund_processed_email(
    customer_name: str,
    order_id: str,
    original_amount: float,
    refund_amount: float,
    currency: str,
    reason: str,
) -> EmailContent:
    """Render refund processed email - table-based layout."""
    base_styles = _get_base_styles()

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Refund Processed</title>
    <style>
        {base_styles}
    </style>
</head>
<body>
    <div style="width: 100%; background-color: #0f0f0f;">
        <div style="max-width: 600px; margin: 0 auto; padding: 0;">
            {_render_header("REFUND PROCESSED", "styxproxy.com")}

            <div role="main" style="padding: 24px;">
                <div style="font-size: 9px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; color: #9ca3af; margin-bottom: 8px;">REFUND CONFIRMATION</div>
                <div style="font-size: 22px; font-weight: 700; color: #f5f5f5; margin-bottom: 8px;">Your refund has been processed, {customer_name}!</div>
                <div style="font-size: 14px; color: #9ca3af; margin-bottom: 20px;">The refund has been initiated to your original payment method</div>

                <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color: #1a1a1a; border-radius: 3px; padding: 20px; margin: 16px 0;">
                    <tr>
                        <td>
                            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                                <tr>
                                    <td style="padding: 12px 0; border-bottom: 1px solid #262626;">
                                        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                                            <tr>
                                                <td style="font-size: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; color: #9ca3af;">Order ID</td>
                                                <td style="font-size: 14px; font-weight: 600; color: #f5f5f5; text-align: right;">{order_id[:16]}...</td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                            </table>
                            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                                <tr>
                                    <td style="padding: 12px 0; border-bottom: 1px solid #262626;">
                                        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                                            <tr>
                                                <td style="font-size: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; color: #9ca3af;">Original Amount</td>
                                                <td style="font-size: 14px; font-weight: 600; color: #f5f5f5; text-align: right;">{currency} {original_amount:,.2f}</td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                            </table>
                            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                                <tr>
                                    <td style="padding: 12px 0; border-bottom: 1px solid #262626;">
                                        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                                            <tr>
                                                <td style="font-size: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; color: #9ca3af;">Refund Amount</td>
                                                <td style="font-size: 18px; font-weight: 700; color: #00D060; text-align: right;">{currency} {refund_amount:,.2f}</td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                            </table>
                            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                                <tr>
                                    <td style="padding: 12px 0; border-bottom: 1px solid #262626;">
                                        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                                            <tr>
                                                <td style="font-size: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; color: #9ca3af;">Reason</td>
                                                <td style="font-size: 14px; font-weight: 600; color: #f5f5f5; text-align: right;">{reason}</td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                </table>

                <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color: #1a1a1a; border-left: 4px solid #f59e0b; padding: 16px; border-radius: 0 3px 3px 0; margin: 16px 0;">
                    <tr>
                        <td style="font-size: 13px; color: #f59e0b;">
                            <strong>Note:</strong> Please allow 5-10 business days for the refund to appear in your account. The exact timing depends on your bank or payment provider.
                        </td>
                    </tr>
                </table>

                {_render_support_footer()}
            </div>

            {_render_footer()}
        </div>
    </div>
</body>
</html>
"""

    text = f"""Refund Processed - {order_id}

Hi {customer_name},

Your refund has been processed successfully.

Order ID: {order_id}
Original Amount: {currency} {original_amount:,.2f}
Refund Amount: {currency} {refund_amount:,.2f}
Reason: {reason}

Please allow 5-10 business days for the refund to appear in your account.

Questions? Contact us at styxproxy.com

- Styxproxy
"""

    return EmailContent(
        subject=f"[Styxproxy] Refund Processed - {order_id[:8]}",
        html=html,
        text=text,
    )


# =============================================================================
# Credentials Rotated Email Template
# =============================================================================


def _render_credentials_rotated_email(
    customer_name: str,
    order_id: str,
    new_username: str,
    new_password: str,
    proxy_ip: str,
    proxy_port: int,
    protocol: str,
) -> EmailContent:
    """Render credentials rotated email - table-based layout."""
    full_format = f"http://{new_username}:{new_password}@{proxy_ip}:{proxy_port}"

    base_styles = _get_base_styles()

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Credentials Rotated</title>
    <style>
        {base_styles}
    </style>
</head>
<body>
    <div style="width: 100%; background-color: #0f0f0f;">
        <div style="max-width: 600px; margin: 0 auto; padding: 0;">
            {_render_header("CREDENTIALS ROTATED", "styxproxy.com")}

            <div role="main" style="padding: 24px;">
                <div style="font-size: 9px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; color: #9ca3af; margin-bottom: 8px;">CREDENTIALS UPDATE</div>
                <div style="font-size: 22px; font-weight: 700; color: #f5f5f5; margin-bottom: 8px;">Your credentials have been updated, {customer_name}.</div>
                <div style="font-size: 14px; color: #9ca3af; margin-bottom: 20px;">Your proxy credentials have been rotated for security</div>

                <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color: #1a1a1a; border-radius: 3px; padding: 20px; margin: 16px 0;">
                    <tr>
                        <td>
                            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                                <tr>
                                    <td style="padding: 12px 0; border-bottom: 1px solid #262626;">
                                        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                                            <tr>
                                                <td style="font-size: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; color: #9ca3af;">Order ID</td>
                                                <td style="font-size: 14px; font-weight: 600; color: #f5f5f5; text-align: right;">{order_id[:16]}...</td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                </table>

                <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color: #0f0f0f; border: 1px solid #00D060; border-radius: 3px; padding: 16px; margin: 16px 0;">
                    <tr>
                        <td>
                            <div style="font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; color: #00D060; margin-bottom: 16px;">NEW CREDENTIALS</div>
                            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                                <tr>
                                    <td style="padding: 10px 0; border-bottom: 1px solid #262626;">
                                        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                                            <tr>
                                                <td style="font-size: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; color: #9ca3af;">Username</td>
                                                <td style="font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace; font-size: 13px; font-weight: 600; color: #00D060; text-align: right; word-break: break-all;">{new_username}</td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                            </table>
                            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                                <tr>
                                    <td style="padding: 10px 0; border-bottom: 1px solid #262626;">
                                        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                                            <tr>
                                                <td style="font-size: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; color: #9ca3af;">Password</td>
                                                <td style="font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace; font-size: 13px; font-weight: 600; color: #00D060; text-align: right; word-break: break-all;">{new_password}</td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                            </table>
                            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                                <tr>
                                    <td style="padding: 10px 0; border-bottom: 1px solid #262626;">
                                        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                                            <tr>
                                                <td style="font-size: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; color: #9ca3af;">Proxy Address</td>
                                                <td style="font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace; font-size: 13px; font-weight: 600; color: #00D060; text-align: right;">{proxy_ip}:{proxy_port}</td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                            </table>
                            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                                <tr>
                                    <td style="padding: 10px 0; border-bottom: 1px solid #262626;">
                                        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                                            <tr>
                                                <td style="font-size: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; color: #9ca3af;">Protocol</td>
                                                <td style="font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace; font-size: 13px; font-weight: 600; color: #00D060; text-align: right;">{protocol.upper()}</td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                            </table>
                            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                                <tr>
                                    <td style="padding: 10px 0; border-bottom: 1px solid #262626;">
                                        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                                            <tr>
                                                <td style="font-size: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; color: #9ca3af;">Full Format</td>
                                                <td style="font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace; font-size: 11px; font-weight: 600; color: #00D060; text-align: right; word-break: break-all;">{full_format[:50]}...</td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                            </table>
                            <div style="margin-top: 12px; padding: 12px; background-color: #1a1a1a; border-left: 4px solid #f59e0b; border-radius: 0 3px 3px 0;">
                                <div style="font-size: 12px; color: #f59e0b;">
                                    <strong>Security:</strong> Keep these credentials confidential. Do not share them with anyone.
                                </div>
                            </div>
                        </td>
                    </tr>
                </table>

                <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color: #1a1a1a; border-left: 4px solid #f59e0b; padding: 16px; border-radius: 0 3px 3px 0; margin: 16px 0;">
                    <tr>
                        <td style="font-size: 13px; color: #f59e0b;">
                            <strong>Important:</strong> Your password has been changed. Please update your proxy configuration with the new credentials immediately to avoid service interruption.
                        </td>
                    </tr>
                </table>

                {_render_support_footer()}
            </div>

            {_render_footer()}
        </div>
    </div>
</body>
</html>
"""

    text = f"""Credentials Rotated - {order_id}

Hi {customer_name},

Your proxy credentials have been rotated as requested.

Order ID: {order_id}

=== NEW CREDENTIALS ===
Username: {new_username}
Password: {new_password}
Proxy: {proxy_ip}:{proxy_port}
Protocol: {protocol.upper()}
Full Format: {full_format}
=========================

IMPORTANT: Your password has been changed. Please update your proxy configuration with the new credentials immediately.

Need help? Contact us at styxproxy.com

- Styxproxy
"""

    return EmailContent(
        subject=f"[Styxproxy] Credentials Rotated - {order_id[:8]}",
        html=html,
        text=text,
    )


# =============================================================================
# Public API - Email Sending Functions
# =============================================================================


async def send_contact_form_notification(
    name: str,
    email: str,
    message: str,
    phone: Optional[str] = None,
    ip_address: Optional[str] = None,
) -> EmailResult:
    """Send notification to admin about new contact form submission."""
    content = _render_contact_form_email(name, email, message, phone, ip_address)
    admin_recipient = EmailRecipient(email=settings.admin_email, name="Admin")

    result = await _send_via_resend(
        recipient=admin_recipient,
        subject=content.subject,
        html=content.html,
        text=content.text,
    )

    # Also send confirmation to the customer
    if result.success:
        confirmation_html = _render_customer_confirmation_email(name)
        confirmation_text = f"""Hi {name},

Thank you for reaching out! We've received your message and will get back to you within 24 hours.

Best regards,
The Styxproxy Team"""

        confirmation_content = EmailContent(
            subject="We received your message - Styxproxy",
            html=confirmation_html,
            text=confirmation_text,
        )
        customer_recipient = EmailRecipient(email=email, name=name)
        await _send_via_resend(
            recipient=customer_recipient,
            subject=confirmation_content.subject,
            html=confirmation_content.html,
            text=confirmation_content.text,
        )

    return result


async def send_charon_escalation_email(
    conversation_id: str,
    customer_email: Optional[str],
    customer_phone: Optional[str],
    message: str,
    history_summary: str,
) -> EmailResult:
    """Send escalation notification to admin when Charon escalates to human."""
    content = _render_charon_escalation_email(
        conversation_id=conversation_id,
        customer_email=customer_email,
        customer_phone=customer_phone,
        message=message,
        history_summary=history_summary,
    )
    admin_recipient = EmailRecipient(email=settings.admin_email, name="Admin")

    return await _send_via_resend(
        recipient=admin_recipient,
        subject=content.subject,
        html=content.html,
        text=content.text,
    )


async def send_admin_notification(
    title: str,
    details: dict,
) -> EmailResult:
    """Send general admin notification email."""
    content = _render_admin_notification_email(
        title=title,
        details=details,
    )
    admin_recipient = EmailRecipient(email=settings.admin_email, name="Admin")

    return await _send_via_resend(
        recipient=admin_recipient,
        subject=content.subject,
        html=content.html,
        text=content.text,
    )


async def send_new_order_notification(
    order_id: str,
    customer_phone: str,
    plan_code: str,
    amount: float,
    currency: str,
) -> EmailResult:
    """Send notification to admin about new order."""
    return await send_admin_notification(
        title="New Order",
        details={
            "Order ID": order_id,
            "Customer Phone": customer_phone,
            "Plan": plan_code,
            "Amount": f"{currency} {amount:,.2f}",
            "Status": "Pending Payment",
        },
    )


async def send_order_paid_notification(
    order_id: str,
    customer_phone: str,
    plan_code: str,
    amount: float,
    currency: str,
) -> EmailResult:
    """Send notification to admin when order is paid."""
    return await send_admin_notification(
        title="Order Paid",
        details={
            "Order ID": order_id,
            "Customer Phone": customer_phone,
            "Plan": plan_code,
            "Amount": f"{currency} {amount:,.2f}",
            "Status": "Paid - Processing",
        },
    )


async def send_refund_request_notification(
    order_id: str,
    customer_phone: str,
    reason: str,
    amount: float,
    currency: str,
) -> EmailResult:
    """Send notification to admin about refund request."""
    return await send_admin_notification(
        title="Refund Request",
        details={
            "Order ID": order_id,
            "Customer Phone": customer_phone,
            "Amount": f"{currency} {amount:,.2f}",
            "Reason": reason,
            "Action Required": "Review and approve/reject",
        },
    )


async def send_refund_approved_notification(
    order_id: str,
    customer_phone: str,
    amount: float,
    currency: str,
) -> EmailResult:
    """Send notification to admin when refund is approved."""
    return await send_admin_notification(
        title="Refund Approved",
        details={
            "Order ID": order_id,
            "Customer Phone": customer_phone,
            "Amount": f"{currency} {amount:,.2f}",
            "Status": "Refunded",
        },
    )


async def send_admin_invite_email(
    email: str,
    role: str,
    invite_code: str,
    expires_in_hours: int = 24,
) -> EmailResult:
    """Send admin invite email to a new user."""
    content = _render_admin_invite_email(
        email=email,
        role=role,
        invite_code=invite_code,
        expires_in_hours=expires_in_hours,
    )
    recipient = EmailRecipient(email=email)

    return await _send_via_resend(
        recipient=recipient,
        subject=content.subject,
        html=content.html,
        text=content.text,
    )


async def send_password_reset_email(
    email: str,
    reset_token: str,
) -> EmailResult:
    """Send password reset email to admin."""
    content = _render_password_reset_email(
        email=email,
        reset_token=reset_token,
    )
    recipient = EmailRecipient(email=email)

    return await _send_via_resend(
        recipient=recipient,
        subject=content.subject,
        html=content.html,
        text=content.text,
    )


async def send_order_confirmation_email(
    customer_email: str,
    customer_name: str,
    order_id: str,
    plan_code: str,
    amount: float,
    currency: str,
    quantity: int,
) -> EmailResult:
    """Send order confirmation email to customer (pending payment)."""
    content = _render_order_confirmation_email(
        customer_name=customer_name,
        order_id=order_id,
        plan_code=plan_code,
        amount=amount,
        currency=currency,
        quantity=quantity,
    )
    recipient = EmailRecipient(email=customer_email, name=customer_name)

    return await _send_via_resend(
        recipient=recipient,
        subject=content.subject,
        html=content.html,
        text=content.text,
    )


async def send_proxy_credentials_email(
    customer_email: str,
    customer_name: str,
    order_id: str,
    tx_ref: str,
    plan_code: str,
    amount: float,
    currency: str,
    quantity: int,
    styxproxy_username: str,
    styxproxy_password: str,
    proxy_ip: str,
    proxy_port: int,
    protocol: str,
    expires_at: datetime,
    payment_method: str = "Card / Bank / USSD / QR",
) -> EmailResult:
    """Send proxy credentials email to customer (order paid + active)."""
    content = _render_proxy_credentials_email(
        customer_name=customer_name,
        order_id=order_id,
        tx_ref=tx_ref,
        plan_code=plan_code,
        amount=amount,
        currency=currency,
        quantity=quantity,
        styxproxy_username=styxproxy_username,
        styxproxy_password=styxproxy_password,
        proxy_ip=proxy_ip,
        proxy_port=proxy_port,
        protocol=protocol,
        expires_at=expires_at,
        payment_method=payment_method,
    )
    recipient = EmailRecipient(email=customer_email, name=customer_name)

    return await _send_via_resend(
        recipient=recipient,
        subject=content.subject,
        html=content.html,
        text=content.text,
    )


async def send_refund_processed_email(
    customer_email: str,
    customer_name: str,
    order_id: str,
    original_amount: float,
    refund_amount: float,
    currency: str,
    reason: str,
) -> EmailResult:
    """Send refund processed email to customer."""
    content = _render_refund_processed_email(
        customer_name=customer_name,
        order_id=order_id,
        original_amount=original_amount,
        refund_amount=refund_amount,
        currency=currency,
        reason=reason,
    )
    recipient = EmailRecipient(email=customer_email, name=customer_name)

    return await _send_via_resend(
        recipient=recipient,
        subject=content.subject,
        html=content.html,
        text=content.text,
    )


async def send_credentials_rotated_email(
    customer_email: str,
    customer_name: str,
    order_id: str,
    new_username: str,
    new_password: str,
    proxy_ip: str,
    proxy_port: int,
    protocol: str,
) -> EmailResult:
    """Send credentials rotated email to customer."""
    content = _render_credentials_rotated_email(
        customer_name=customer_name,
        order_id=order_id,
        new_username=new_username,
        new_password=new_password,
        proxy_ip=proxy_ip,
        proxy_port=proxy_port,
        protocol=protocol,
    )
    recipient = EmailRecipient(email=customer_email, name=customer_name)

    return await _send_via_resend(
        recipient=recipient,
        subject=content.subject,
        html=content.html,
        text=content.text,
    )


async def send_support_reply_email(
    customer_email: str,
    customer_name: str,
    original_subject: str,
    reply_body_html: str,
    admin_name: str = "Dannion",
    in_reply_to: Optional[str] = None,
    references: Optional[str] = None,
) -> EmailResult:
    """
    Send a support reply email to a customer.

    This wraps the reply in the branded support template and sends from support@styxproxy.com
    with proper threading headers for Gmail/Outlook.
    """
    content = _render_support_reply_email(
        customer_name=customer_name,
        original_subject=original_subject,
        reply_body_html=reply_body_html,
        admin_name=admin_name,
    )

    return await send_email(
        to=customer_email,
        subject=content.subject,
        html=content.html,
        text=content.text,
        from_email="Styxproxy Support <support@styxproxy.com>",
        reply_to="support@styxproxy.com",
        in_reply_to=in_reply_to,
        references=references,
    )


# =============================================================================
# Renewal Reminder Email Template  (S2.5)
# =============================================================================


def _render_renewal_reminder_email(
    customer_name: str,
    order_id: str,
    plan_code: str,
    expires_at: datetime,
    days_remaining: int,
) -> EmailContent:
    """Render renewal reminder email - table-based layout."""
    base_styles = _get_base_styles()
    # Calculate dynamic expiry message
    if days_remaining <= 0:
        expiry_headline = "Your proxy has expired"
        expiry_sub = "Renew now to keep your IP and avoid interruption."
        badge_bg = "#ef4444"
        badge_text = "EXPIRED"
    elif days_remaining == 1:
        expiry_headline = "Your proxy expires tomorrow"
        expiry_sub = "Renew now to keep your IP and avoid interruption."
        badge_bg = "#ef4444"
        badge_text = "EXPIRES SOON"
    else:
        expiry_headline = f"Your proxy expires in {days_remaining} days"
        expiry_sub = "Renew now to keep your IP and avoid interruption."
        badge_bg = "#f59e0b"
        badge_text = f"{days_remaining} DAYS LEFT"

    # Format expiry date
    expires_str = expires_at.strftime("%B %d, %Y")

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Your Proxy Expires Soon</title>
    <style>
        {base_styles}
    </style>
</head>
<body>
    <div style="width: 100%; background-color: #0f0f0f;">
        <div style="max-width: 600px; margin: 0 auto; padding: 0;">
            <div style="height: 4px; background-color: #00D060;" aria-hidden="true"></div>

            {_render_header("RENEWAL REMINDER", "styxproxy.com")}

            <div style="height: 1px; background-color: #262626; margin: 0 24px;" aria-hidden="true"></div>

            <div role="main" style="padding: 24px;">
                <!-- Section label -->
                <div style="font-size: 9px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; color: #9ca3af; margin-bottom: 8px;">Subscription Alert</div>

                <!-- Main heading -->
                <div style="font-size: 22px; font-weight: 700; color: #f5f5f5; margin-bottom: 8px;">{expiry_headline}</div>
                <div style="font-size: 14px; color: #9ca3af; margin-bottom: 20px;">{expiry_sub}</div>

                <!-- Status badge -->
                <div style="margin-bottom: 20px;">
                    <span style="display: inline-block; padding: 6px 14px; border-radius: 4.5px; font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; background-color: {badge_bg}; color: #000000;">{badge_text}</span>
                </div>

                <!-- Order details card -->
                <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color: #1a1a1a; border-radius: 3px; padding: 20px; margin: 16px 0;">
                    <tr>
                        <td>
                            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                                <tr>
                                    <td style="padding: 12px 0; border-bottom: 1px solid #262626;">
                                        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                                            <tr>
                                                <td style="font-size: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; color: #9ca3af;">Order ID</td>
                                                <td style="font-size: 14px; font-weight: 600; color: #00D060; text-align: right;">{order_id}</td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                            </table>
                            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                                <tr>
                                    <td style="padding: 12px 0; border-bottom: 1px solid #262626;">
                                        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                                            <tr>
                                                <td style="font-size: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; color: #9ca3af;">Plan</td>
                                                <td style="font-size: 14px; font-weight: 600; color: #f5f5f5; text-align: right;">{plan_code}</td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                            </table>
                            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                                <tr>
                                    <td style="padding: 12px 0; border-bottom: 1px solid #262626;">
                                        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                                            <tr>
                                                <td style="font-size: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; color: #9ca3af;">Expiry Date</td>
                                                <td style="font-size: 14px; font-weight: 600; color: #f5f5f5; text-align: right;">{expires_str}</td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                </table>

                <!-- Warning box -->
                <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color: #1a1a1a; border-left: 4px solid #f59e0b; padding: 16px; border-radius: 0 3px 3px 0; margin: 16px 0;">
                    <tr>
                        <td style="font-size: 13px; color: #f59e0b;">
                            <strong>Don't lose your IP.</strong> Once your proxy expires, the IP address is released back into the pool and may no longer be available when you renew. Act now to keep the same IP address.
                        </td>
                    </tr>
                </table>

                <!-- CTA Button -->
                <div style="text-align: center; margin: 24px 0;">
                    <a href="https://styxproxy.com/manage" style="display: inline-block; background-color: #00D060; color: #000000; font-weight: 700; padding: 14px 28px; border-radius: 4px; text-decoration: none;" rel="noopener noreferrer">
                        Renew Now
                    </a>
                </div>

                <!-- Support section -->
                <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color: #1a1a1a; border-radius: 3px; padding: 16px; margin-top: 20px;">
                    <tr>
                        <td>
                            <div style="font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; color: #f5f5f5; margin-bottom: 12px;">NEED HELP?</div>
                            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                                <tr>
                                    <td style="font-size: 12px; color: #9ca3af; padding-bottom: 6px;">Chat:</td>
                                    <td style="font-size: 12px; text-align: right; padding-bottom: 6px;"><a href="https://styxproxy.com/contact" style="color: #00D060; text-decoration: none; font-weight: 500;" rel="noopener noreferrer">styxproxy.com/contact</a></td>
                                </tr>
                                <tr>
                                    <td style="font-size: 12px; color: #9ca3af; padding-bottom: 6px;">Email:</td>
                                    <td style="font-size: 12px; text-align: right; padding-bottom: 6px;"><a href="mailto:support@styxproxy.com" style="color: #00D060; text-decoration: none; font-weight: 500;">support@styxproxy.com</a></td>
                                </tr>
                                <tr>
                                    <td style="font-size: 12px; color: #9ca3af;">Web:</td>
                                    <td style="font-size: 12px; text-align: right;"><a href="https://styxproxy.com" style="color: #00D060; text-decoration: none; font-weight: 500;" rel="noopener noreferrer">styxproxy.com</a></td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                </table>
            </div>

            <div style="height: 1px; background-color: #262626; margin: 0 24px;" aria-hidden="true"></div>

            <div role="contentinfo" style="text-align: center; padding: 20px 24px; color: #9ca3af; font-size: 11px;">
                <div style="font-style: italic; margin-bottom: 8px;">You received this email because you have an active Styxproxy subscription.</div>
                <div style="margin-bottom: 8px;">To manage your email preferences, visit your account settings.</div>
                <div style="margin-bottom: 8px;">
                    <a href="https://styxproxy.com/unsubscribe" style="color: #9ca3af; text-decoration: underline;">Unsubscribe</a>
                </div>
                <div style="margin-bottom: 8px;">Styxproxy, Lagos, Nigeria</div>
                <div style="color: #9ca3af;">&copy; 2026 Styxproxy &mdash; Anonymous proxy service for the discerning.</div>
            </div>

            <div style="height: 4px; background-color: #00D060;" aria-hidden="true"></div>
        </div>
    </div>
</body>
</html>"""

    # Plain text fallback
    text = f"""Styxproxy Renewal Reminder

{expiry_headline}

Order ID: {order_id}
Plan: {plan_code}
Expires: {expires_str}

Don't lose your IP address. Renew now at https://styxproxy.com/manage

If you have questions, contact support@styxproxy.com or visit styxproxy.com/contact

&copy; 2026 Styxproxy
"""

    subject = f"{expiry_headline} - renew at styxproxy.com/manage"
    return EmailContent(subject=subject, html=html, text=text)


async def send_renewal_reminder_email(
    customer_email: str,
    customer_name: str,
    order_id: str,
    plan_code: str,
    expires_at: datetime,
    days_remaining: int,
) -> EmailResult:
    """Send renewal reminder email to customer.

    Args:
        customer_email: Recipient email address.
        customer_name: Customer's display name.
        order_id: The order ID (ORD-XXXXXX).
        plan_code: The plan code (e.g. RESI-US-5GB).
        expires_at: When the proxy subscription expires.
        days_remaining: Days until expiry (used for subject / badge copy).
    """
    content = _render_renewal_reminder_email(
        customer_name=customer_name,
        order_id=order_id,
        plan_code=plan_code,
        expires_at=expires_at,
        days_remaining=days_remaining,
    )
    recipient = EmailRecipient(email=customer_email, name=customer_name)

    return await _send_via_resend(
        recipient=recipient,
        subject=content.subject,
        html=content.html,
        text=content.text,
    )


async def send_rotation_notification_email(
    customer_email: str,
    styxproxy_username: str,
    styxproxy_password: str,
    proxy_ip: str,
    proxy_port: int,
    order_id: str,
) -> EmailResult:
    """Send rotation notification email (alias for backward compatibility)."""
    content = _render_credentials_rotated_email(
        customer_name="Customer",
        order_id=order_id,
        new_username=styxproxy_username,
        new_password=styxproxy_password,
        proxy_ip=proxy_ip,
        proxy_port=proxy_port,
        protocol="socks5",
    )
    recipient = EmailRecipient(email=customer_email, name="Customer")

    return await _send_via_resend(
        recipient=recipient,
        subject=content.subject,
        html=content.html,
        text=content.text,
    )

async def send_new_admin_notification_email(
    new_admin_email: str,
    role: str,
    created_by: str,
    superadmin_emails: list[str],
) -> None:
    """Send notification to all superadmins when a new admin is created."""
    for email in superadmin_emails:
        try:
            await send_email(
                to_email=email,
                subject=f"[Styxproxy] New Admin Created: {new_admin_email}",
                html_content=f"""
                <html lang="en">
                <body style="font-family: Arial, sans-serif; background: #0a0a0a; color: #f5f5f5; padding: 2rem;">
                    <h2 style="color: #0AD25A;">New Admin Created</h2>
                    <p>A new admin account has been created:</p>
                    <ul>
                        <li><strong>Email:</strong> {new_admin_email}</li>
                        <li><strong>Role:</strong> {role}</li>
                        <li><strong>Created by:</strong> {created_by}</li>
                    </ul>
                    <p style="color: #737373; font-size: 0.875rem;">This is an automated notification.</p>
                </body>
                </html>
                """,
            )
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Failed to send new admin notification to {email}: {e}")
