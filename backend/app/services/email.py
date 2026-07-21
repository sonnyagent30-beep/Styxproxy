"""Email service using Resend API.

Provides transactional email functionality:
- Contact form submissions
- Charon escalation notifications
- Admin notifications (orders, refunds, etc.)
"""
import logging
import base64
import io
from datetime import datetime
from enum import Enum
from typing import Optional

import httpx
from PIL import Image
from pydantic import BaseModel, EmailStr

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


# =============================================================================
# Logo processing for inline embedding
# =============================================================================
def _get_logo_b64() -> str:
    """Process and return the Styxproxy logo as base64 PNG."""
    logo = Image.open("/app/app/assets/styxproxy_logo.png")
    scale_y = logo.size[1] / 3264
    crop_y = int(377 * scale_y)
    crop_h = int(877 * scale_y)
    cropped = logo.crop((0, crop_y, logo.size[0], crop_y + crop_h))
    cropped = cropped.resize((480, 137), Image.LANCZOS)
    buf = io.BytesIO()
    cropped.save(buf, format="PNG", optimize=True)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode()


# Cache the logo at module load time
LOGO_B64 = _get_logo_b64()


# =============================================================================
# Base email template components
# =============================================================================
def _get_base_styles() -> str:
    """Get the base CSS styles for all emails - Styxproxy Dark Theme."""
    return """
        /* Reset and base styles */
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        /* Styxproxy Brand Colors - Dark Theme */
        :root {
            --brand-primary: #0AD25A;
            --brand-primary-dark: #059669;
            --brand-primary-light: #22FF7A;
            --brand-accent: #f59e0b;
            --brand-bg: #000000;
            --brand-surface: #111111;
            --brand-card: #1a1a1a;
            --brand-card-hover: #252525;
            --brand-border: #2a2a2a;
            --brand-foreground: #f5f5f5;
            --brand-muted: #737373;
            --brand-success: #22c55e;
            --brand-warning: #f59e0b;
            --brand-error: #ef4444;
        }
        
        /* Dark theme (default) */
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', sans-serif;
            line-height: 1.6;
            color: #f5f5f5;
            background-color: #000000;
            margin: 0;
            padding: 0;
        }
        
        .email-container {
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
        }
        
        .header-bar {
            background: #0AD25A;
            padding: 0;
            text-align: center;
        }
        
        .header-bar img {
            display: block;
            width: 100%;
            max-width: 480px;
            height: auto;
        }
        
        .accent-bar {
            height: 4px;
            background: linear-gradient(90deg, #0AD25A 0%, #22FF7A 100%);
        }
        
        .content-card {
            background: #1a1a1a;
            border-radius: 16px;
            padding: 32px 24px;
            margin-top: 0;
        }
        
        .content-card.escalation {
            border-top: 4px solid #ef4444;
        }
        
        .content-card.success {
            border-top: 4px solid #22c55e;
        }
        
        .content-card.warning {
            border-top: 4px solid #f59e0b;
        }
        
        .content-card.info {
            border-top: 4px solid #0AD25A;
        }
        
        h1 {
            font-size: 24px;
            font-weight: 700;
            color: #f5f5f5;
            margin-bottom: 8px;
        }
        
        h2 {
            font-size: 20px;
            font-weight: 600;
            color: #f5f5f5;
            margin-bottom: 16px;
        }
        
        p {
            margin-bottom: 16px;
            color: #a3a3a3;
        }
        
        .field {
            margin-bottom: 16px;
        }
        
        .label {
            font-size: 12px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: #737373;
            margin-bottom: 4px;
        }
        
        .value {
            font-size: 16px;
            color: #f5f5f5;
        }
        
        .message-box {
            background: #111111;
            border-left: 4px solid #0AD25A;
            padding: 16px;
            border-radius: 0 8px 8px 0;
            margin: 16px 0;
            color: #f5f5f5;
        }
        
        .credentials-box {
            background: #111111;
            border: 1px solid #2a2a2a;
            border-left: 4px solid #0AD25A;
            padding: 20px;
            border-radius: 8px;
            margin: 20px 0;
        }
        
        .cred-row {
            margin-bottom: 16px;
        }
        
        .cred-row:last-child {
            margin-bottom: 0;
        }
        
        .cred-label {
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: #737373;
            margin-bottom: 6px;
        }
        
        .cred-value {
            font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
            font-size: 15px;
            background: #0a0a0a;
            border: 1px solid #2a2a2a;
            padding: 10px 14px;
            border-radius: 6px;
            word-break: break-all;
            color: #f5f5f5;
        }
        
        .details-table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }
        
        .details-table tr {
            border-bottom: 1px solid #2a2a2a;
        }
        
        .details-table td {
            padding: 12px 0;
        }
        
        .details-table td:first-child {
            color: #737373;
            font-weight: 500;
        }
        
        .details-table td:last-child {
            text-align: right;
            font-weight: 600;
            color: #f5f5f5;
        }
        
        .total-amount {
            font-size: 28px;
            font-weight: 700;
            color: #0AD25A;
            text-align: center;
            margin: 20px 0;
        }
        
        .order-id {
            background: #0AD25A;
            color: #000000;
            font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
            font-size: 16px;
            padding: 12px 20px;
            border-radius: 8px;
            text-align: center;
            margin: 20px 0;
            word-break: break-all;
            font-weight: 600;
        }
        
        .cta-button {
            display: inline-block;
            background: #0AD25A;
            color: #000000;
            font-weight: 700;
            padding: 14px 28px;
            border-radius: 8px;
            text-decoration: none;
            margin: 16px 0;
        }
        
        .cta-button:hover {
            background: #22FF7A;
        }
        
        .warning-box {
            background: #1a1a1a;
            border-left: 4px solid #f59e0b;
            padding: 16px;
            border-radius: 0 8px 8px 0;
            margin: 20px 0;
            font-size: 14px;
            color: #f59e0b;
        }
        
        .help-box {
            background: #111111;
            padding: 16px;
            border-radius: 8px;
            margin-top: 20px;
            font-size: 14px;
            color: #a3a3a3;
        }
        
        .footer {
            text-align: center;
            padding: 24px 20px;
            color: #737373;
            font-size: 12px;
        }
        
        .footer a {
            color: #0AD25A;
            text-decoration: none;
        }
        
        .social-links {
            margin-top: 12px;
        }
        
        .social-links a {
            display: inline-block;
            margin: 0 8px;
            color: #737373;
            text-decoration: none;
        }
        
        .muted-text {
            color: #737373;
            font-size: 14px;
        }
        
        .link-text {
            color: #0AD25A;
            word-break: break-all;
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
        return EmailResult(
            success=False,
            error="Email service not configured (RESEND_API_KEY missing)",
        )

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(10.0, connect=15.0)) as client:
            # Build the recipient dict
            to = recipient.email
            if recipient.name:
                to = f"{recipient.name} <{recipient.email}>"

            response = await client.post(
                "https://api.resend.com/emails",
                json={
                    "from": settings.from_email,
                    "to": [to],
                    "subject": subject,
                    "html": html,
                    "text": text,
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


def _render_contact_form_email(
    name: str,
    email: str,
    message: str,
    phone: Optional[str] = None,
) -> EmailContent:
    """Render contact form submission email (to admin)."""
    phone_html = f"""<div class="field">
                        <div class="label">Phone</div>
                        <div class="value">{phone}</div>
                    </div>""" if phone else ""

    base_styles = _get_base_styles()

    html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>New Contact Form Submission</title>
    <style>
        {base_styles}
    </style>
</head>
<body>
    <div class="email-container">
        <div class="header-bar">
            <img src="data:image/png;base64,{LOGO_B64}" alt="Styxproxy">
        </div>
        <div class="accent-bar"></div>
        
        <div class="content-card">
            <h1>📬 New Contact Form Submission</h1>
            
            <div class="field">
                <div class="label">Name</div>
                <div class="value">{name}</div>
            </div>
            
            <div class="field">
                <div class="label">Email</div>
                <div class="value"><a href="mailto:{email}" style="color: #0AD25A;">{email}</a></div>
            </div>
            
            {phone_html}
            
            <div class="field">
                <div class="label">Message</div>
                <div class="message-box">{message.replace(chr(10), '<br>')}</div>
            </div>
        </div>
        
        <div class="footer">
            Submitted at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC<br>
            © 2024 Styxproxy. All rights reserved.
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

Submitted at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC
"""

    return EmailContent(
        subject="[Styxproxy] New Contact Form Submission",
        html=html,
        text=text,
    )


def _render_charon_escalation_email(
    conversation_id: str,
    customer_email: Optional[str],
    customer_phone: Optional[str],
    message: str,
    history_summary: str,
) -> EmailContent:
    """Render Charon escalation notification email (alert style)."""
    contact_info = ""
    if customer_email:
        contact_info += f"""<div class="field">
                            <div class="label">Email</div>
                            <div class="value"><a href='mailto:{customer_email}' style="color: #0AD25A;">{customer_email}</a></div>
                        </div>"""
    if customer_phone:
        contact_info += f"""<div class="field">
                            <div class="label">Phone</div>
                            <div class="value">{customer_phone}</div>
                        </div>"""

    base_styles = _get_base_styles()

    html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Charon Escalation</title>
    <style>
        {base_styles}
    </style>
</head>
<body>
    <div class="email-container">
        <div class="header-bar" style="background: #ef4444;">
            <img src="data:image/png;base64,{LOGO_B64}" alt="Styxproxy">
        </div>
        <div class="accent-bar" style="background: #ef4444;"></div>
        
        <div class="content-card escalation">
            <h1>⚠️ Charon Escalation</h1>
            
            <div class="field">
                <div class="label">Conversation ID</div>
                <div class="order-id">{conversation_id}</div>
            </div>
            
            {contact_info}
            
            <div class="field">
                <div class="label">Latest Message</div>
                <div class="message-box">{message.replace(chr(10), '<br>')}</div>
            </div>
            
            <div class="field">
                <div class="label">Conversation History</div>
                <div class="message-box" style="white-space: pre-wrap; font-family: monospace; font-size: 13px;">{history_summary}</div>
            </div>
        </div>
        
        <div class="footer">
            Escalated at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC<br>
            © 2024 Styxproxy. All rights reserved.
        </div>
    </div>
</body>
</html>
"""

    text = f"""Charon Escalation Alert

Conversation ID: {conversation_id}
{('Email: ' + customer_email) if customer_email else ''}
{('Phone: ' + customer_phone) if customer_phone else ''}

Latest Message:
{message}

Conversation History:
{history_summary}

Escalated at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC
"""

    return EmailContent(
        subject=f"[Styxproxy] Charon Escalation - {conversation_id[:8]}",
        html=html,
        text=text,
    )


def _render_admin_notification_email(
    notification_type: str,
    title: str,
    details: dict,
) -> EmailContent:
    """Render admin notification email."""
    details_html = "".join(
        f"""<tr>
                <td>{k}</td>
                <td>{v}</td>
            </tr>"""
        for k, v in details.items()
    )

    base_styles = _get_base_styles()

    html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        {base_styles}
    </style>
</head>
<body>
    <div class="email-container">
        <div class="header-bar">
            <img src="data:image/png;base64,{LOGO_B64}" alt="Styxproxy">
        </div>
        <div class="accent-bar"></div>
        
        <div class="content-card">
            <h1>🔔 {title}</h1>
            
            <table class="details-table">
                {details_html}
            </table>
        </div>
        
        <div class="footer">
            Notification sent at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC<br>
            © 2024 Styxproxy. All rights reserved.
        </div>
    </div>
</body>
</html>
"""

    text_details = "\n".join(f"{k}: {v}" for k, v in details.items())

    text = f"""{title}

{text_details}

Notification sent at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC
"""

    return EmailContent(
        subject=f"[Styxproxy Admin] {title}",
        html=html,
        text=text,
    )


# =============================================================================
# Public API
# =============================================================================


async def send_contact_form_notification(
    name: str,
    email: str,
    message: str,
    phone: Optional[str] = None,
) -> EmailResult:
    """Send notification to admin about new contact form submission."""
    content = _render_contact_form_email(name, email, message, phone)
    admin_recipient = EmailRecipient(email=settings.admin_email, name="Admin")

    result = await _send_via_resend(
        recipient=admin_recipient,
        subject=content.subject,
        html=content.html,
        text=content.text,
    )

    # Also send confirmation to the customer
    if result.success:
        base_styles = _get_base_styles()
        confirmation_html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Message Received</title>
    <style>
        {base_styles}
    </style>
</head>
<body>
    <div class="email-container">
        <div class="header-bar">
            <img src="data:image/png;base64,{LOGO_B64}" alt="Styxproxy">
        </div>
        <div class="accent-bar"></div>
        
        <div class="content-card success">
            <h1>✅ Message Received</h1>
            
            <p>Hi {name},</p>
            
            <p>Thank you for reaching out! We've received your message and will get back to you within 24 hours.</p>
            
            <p>If you have any urgent questions, you can reply to this email or WhatsApp us directly.</p>
            
            <p>Best regards,<br>The Styxproxy Team</p>
        </div>
        
        <div class="footer">
            © 2024 Styxproxy. All rights reserved.
        </div>
    </div>
</body>
</html>
"""
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
    notification_type: str,
    title: str,
    details: dict,
) -> EmailResult:
    """Send general admin notification email."""
    content = _render_admin_notification_email(
        notification_type=notification_type,
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
        notification_type="new_order",
        title="🛒 New Order",
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
        notification_type="order_paid",
        title="✅ Order Paid",
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
        notification_type="refund_request",
        title="💰 Refund Request",
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
        notification_type="refund_approved",
        title="✅ Refund Approved",
        details={
            "Order ID": order_id,
            "Customer Phone": customer_phone,
            "Amount": f"{currency} {amount:,.2f}",
            "Status": "Refunded",
        },
    )


# =============================================================================
# Admin Auth Email Templates
# =============================================================================


def _render_admin_invite_email(
    email: str,
    role: str,
    invite_code: str,
    expires_in_hours: int,
) -> EmailContent:
    """Render admin invite email (dark themed)."""
    invite_link = f"https://styxproxy.com/admin/setup?code={invite_code}"

    base_styles = _get_base_styles()

    html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>You've Been Invited</title>
    <style>
        {base_styles}
    </style>
</head>
<body>
    <div class="email-container">
        <div class="header-bar" style="background: #0AD25A;">
            <img src="data:image/png;base64,{LOGO_B64}" alt="Styxproxy">
        </div>
        <div class="accent-bar"></div>
        
        <div class="content-card">
            <h1>🚀 You've Been Invited to Styxproxy Admin</h1>
            
            <p>Hi,</p>
            
            <p>You've been invited to join the <strong style="color: #0AD25A;">Styxproxy Admin Panel</strong> with the role of <strong>{role}</strong>.</p>
            
            <div class="credentials-box">
                <div class="cred-row">
                    <div class="cred-label">Your Role</div>
                    <div class="cred-value" style="background: transparent; border: none; padding: 0;">{role}</div>
                </div>
            </div>
            
            <p style="text-align: center;">
                <a href="{invite_link}" class="cta-button">Set Up Account</a>
            </p>
            
            <p class="muted-text">
                Or copy this link: <span class="link-text">{invite_link}</span>
            </p>
            
            <div class="warning-box">
                ⚠️ <strong>Important:</strong> This invite expires in {expires_in_hours} hours. If you didn't request this, please ignore this email.
            </div>
        </div>
        
        <div class="footer">
            Styxproxy Admin Panel · Sent at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC<br>
            © 2024 Styxproxy. All rights reserved.
        </div>
    </div>
</body>
</html>
"""

    text = f"""You've Been Invited to Styxproxy Admin

Hi,

You've been invited to join the Styxproxy Admin Panel with the role of {role}.

Your Invite Link: {invite_link}

This invite expires in {expires_in_hours} hours.

If you didn't request this, please ignore this email.

- Styxproxy Admin
"""

    return EmailContent(
        subject="You've been invited to Styxproxy Admin",
        html=html,
        text=text,
    )


def _render_password_reset_email(
    email: str,
    reset_token: str,
) -> EmailContent:
    """Render password reset email (dark themed)."""
    reset_link = f"https://styxproxy.com/admin/reset-password?token={reset_token}"

    base_styles = _get_base_styles()

    html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Reset Your Password</title>
    <style>
        {base_styles}
    </style>
</head>
<body>
    <div class="email-container">
        <div class="header-bar" style="background: #0AD25A;">
            <img src="data:image/png;base64,{LOGO_B64}" alt="Styxproxy">
        </div>
        <div class="accent-bar"></div>
        
        <div class="content-card">
            <h1>🔐 Reset Your Styxproxy Admin Password</h1>
            
            <p>Hi,</p>
            
            <p>We received a request to reset your Styxproxy Admin password. Click the button below to create a new password:</p>
            
            <p style="text-align: center;">
                <a href="{reset_link}" class="cta-button">Reset Password</a>
            </p>
            
            <p class="muted-text">
                Or copy this link: <span class="link-text">{reset_link}</span>
            </p>
            
            <p class="muted-text">
                ⏱️ This link expires in <strong>1 hour</strong>.
            </p>
            
            <div class="warning-box">
                ⚠️ <strong>If you didn't request this</strong>, please ignore this email. Your password will remain unchanged.
            </div>
        </div>
        
        <div class="footer">
            Styxproxy Admin Panel · Sent at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC<br>
            © 2024 Styxproxy. All rights reserved.
        </div>
    </div>
</body>
</html>
"""

    text = f"""Reset Your Styxproxy Admin Password

Hi,

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


# =============================================================================
# Customer Purchase Emails
# =============================================================================


def _render_order_confirmation_email(
    customer_name: str,
    order_id: str,
    plan_code: str,
    amount: float,
    currency: str,
    quantity: int,
) -> EmailContent:
    """Render order confirmation email (pending payment)."""
    base_styles = _get_base_styles()

    html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Order Placed</title>
    <style>
        {base_styles}
    </style>
</head>
<body>
    <div class="email-container">
        <div class="header-bar">
            <img src="data:image/png;base64,{LOGO_B64}" alt="Styxproxy">
        </div>
        <div class="accent-bar"></div>
        
        <div class="content-card">
            <h1>📋 Order Placed — Payment Pending</h1>
            <p class="muted-text" style="margin-top: -8px; margin-bottom: 24px;">Awaiting your payment</p>
            
            <p>Hi {customer_name},</p>
            
            <p>Your order has been received. Complete your payment to activate your proxy.</p>
            
            <div class="order-id">{order_id}</div>
            
            <table class="details-table">
                <tr>
                    <td>Plan</td>
                    <td>{plan_code}</td>
                </tr>
                <tr>
                    <td>Quantity</td>
                    <td>{quantity}</td>
                </tr>
                <tr>
                    <td>Amount</td>
                    <td style="font-size: 20px; color: #0AD25A;">{currency} {amount:,.2f}</td>
                </tr>
            </table>
            
            <div class="warning-box">
                <strong>Next step:</strong> Complete your payment. Once confirmed, your proxy credentials will be sent to this email automatically.
            </div>
            
            <div class="help-box">
                <strong>Need help?</strong> Reply to this email or WhatsApp us. We're here to help!
            </div>
        </div>
        
        <div class="footer">
            Styxproxy · Order placed at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC<br>
            © 2024 Styxproxy. All rights reserved.
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

Next step: Complete your payment. Your proxy credentials will be sent to this email once confirmed.

Need help? Reply to this email or WhatsApp us.

- Styxproxy
"""

    return EmailContent(
        subject=f"[Styxproxy] Order Placed - {order_id}",
        html=html,
        text=text,
    )


def _render_proxy_credentials_email(
    customer_name: str,
    order_id: str,
    plan_code: str,
    bun_username: str,
    proxy_ip: str,
    proxy_port: int,
    protocol: str,
    expires_at: datetime,
) -> EmailContent:
    """Render proxy credentials email (order paid + active)."""
    expires_str = expires_at.strftime('%Y-%m-%d %H:%M UTC') if expires_at else "N/A"

    base_styles = _get_base_styles()

    html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Your Proxy is Ready</title>
    <style>
        {base_styles}
    </style>
</head>
<body>
    <div class="email-container">
        <div class="header-bar" style="background: #0AD25A;">
            <img src="data:image/png;base64,{LOGO_B64}" alt="Styxproxy">
        </div>
        <div class="accent-bar"></div>
        
        <div class="content-card success">
            <h1>🎉 Your Proxy is Ready!</h1>
            <p class="muted-text" style="margin-top: -8px; margin-bottom: 24px;">Order {order_id}</p>
            
            <p>Hi {customer_name},</p>
            
            <p>Great news! Your proxy is now active. Here are your credentials:</p>
            
            <div class="order-id">{order_id}</div>
            
            <div class="credentials-box">
                <div class="cred-row">
                    <div class="cred-label">Username</div>
                    <div class="cred-value">{bun_username}</div>
                </div>
                <div class="cred-row">
                    <div class="cred-label">Proxy Address</div>
                    <div class="cred-value">{proxy_ip}:{proxy_port}</div>
                </div>
                <div class="cred-row">
                    <div class="cred-label">Protocol</div>
                    <div class="cred-value">{protocol.upper()}</div>
                </div>
            </div>
            
            <table class="details-table">
                <tr>
                    <td>Plan</td>
                    <td>{plan_code}</td>
                </tr>
                <tr>
                    <td>Expires</td>
                    <td>{expires_str}</td>
                </tr>
            </table>
            
            <p>You can now use your proxy. Need help getting started?</p>
            
            <div class="help-box">
                <strong>Having issues?</strong> Reply to this email or WhatsApp us immediately. We'll help you sort it out!
            </div>
        </div>
        
        <div class="footer">
            Styxproxy · Powered by Styxproxy<br>
            © 2024 Styxproxy. All rights reserved.
        </div>
    </div>
</body>
</html>
"""

    text = f"""Your Proxy is Ready! - {order_id}

Hi {customer_name},

Great news! Your proxy is now active.

Order ID: {order_id}
Plan: {plan_code}
Expires: {expires_str}

=== YOUR CREDENTIALS ===
Username: {bun_username}
Proxy: {proxy_ip}:{proxy_port}
Protocol: {protocol.upper()}
=========================

You can now use your proxy.

Having issues? Reply to this email or WhatsApp us immediately. We'll help you sort it out!

- Styxproxy
"""

    return EmailContent(
        subject=f"[Styxproxy] Your Proxy is Ready! - {order_id}",
        html=html,
        text=text,
    )


def _render_refund_processed_email(
    customer_name: str,
    order_id: str,
    amount: float,
    currency: str,
    reason: str,
) -> EmailContent:
    """Render refund processed email to customer."""
    base_styles = _get_base_styles()

    html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Refund Processed</title>
    <style>
        {base_styles}
    </style>
</head>
<body>
    <div class="email-container">
        <div class="header-bar" style="background: #f59e0b;">
            <img src="data:image/png;base64,{LOGO_B64}" alt="Styxproxy">
        </div>
        <div class="accent-bar" style="background: #f59e0b;"></div>
        
        <div class="content-card warning">
            <h1>💵 Refund Processed</h1>
            <p class="muted-text" style="margin-top: -8px; margin-bottom: 24px;">Order {order_id}</p>
            
            <p>Hi {customer_name},</p>
            
            <p>Your refund has been processed successfully.</p>
            
            <div class="order-id">{order_id}</div>
            
            <div class="total-amount">{currency} {amount:,.2f}</div>
            
            <table class="details-table">
                <tr>
                    <td>Original Amount</td>
                    <td>{currency} {amount:,.2f}</td>
                </tr>
                <tr>
                    <td>Refund Amount</td>
                    <td>{currency} {amount:,.2f}</td>
                </tr>
                <tr>
                    <td>Reason</td>
                    <td>{reason}</td>
                </tr>
            </table>
            
            <p>Please allow 5-10 business days for the refund to appear in your account.</p>
            
            <div class="help-box">
                <strong>Questions about your refund?</strong> Reply to this email or WhatsApp us with your order ID.
            </div>
        </div>
        
        <div class="footer">
            Styxproxy · Refund processed at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC<br>
            © 2024 Styxproxy. All rights reserved.
        </div>
    </div>
</body>
</html>
"""

    text = f"""Refund Processed - {order_id}

Hi {customer_name},

Your refund has been processed successfully.

Order ID: {order_id}
Refund Amount: {currency} {amount:,.2f}
Reason: {reason}

Please allow 5-10 business days for the refund to appear in your account.

Questions? Reply to this email or WhatsApp us with your order ID.

- Styxproxy
"""

    return EmailContent(
        subject=f"[Styxproxy] Refund Processed - {order_id}",
        html=html,
        text=text,
    )


def _render_credentials_rotated_email(
    customer_name: str,
    order_id: str,
    new_username: str,
    proxy_ip: str,
    proxy_port: int,
    protocol: str,
) -> EmailContent:
    """Render credentials rotated email to customer."""
    base_styles = _get_base_styles()

    html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Credentials Rotated</title>
    <style>
        {base_styles}
    </style>
</head>
<body>
    <div class="email-container">
        <div class="header-bar" style="background: #0AD25A;">
            <img src="data:image/png;base64,{LOGO_B64}" alt="Styxproxy">
        </div>
        <div class="accent-bar"></div>
        
        <div class="content-card info">
            <h1>🔄 Credentials Rotated</h1>
            <p class="muted-text" style="margin-top: -8px; margin-bottom: 24px;">Order {order_id}</p>
            
            <p>Hi {customer_name},</p>
            
            <p>Your proxy credentials have been rotated as requested.</p>
            
            <div class="order-id">{order_id}</div>
            
            <div class="credentials-box">
                <div class="cred-row">
                    <div class="cred-label">New Username</div>
                    <div class="cred-value">{new_username}</div>
                </div>
                <div class="cred-row">
                    <div class="cred-label">Proxy Address</div>
                    <div class="cred-value">{proxy_ip}:{proxy_port}</div>
                </div>
                <div class="cred-row">
                    <div class="cred-label">Protocol</div>
                    <div class="cred-value">{protocol.upper()}</div>
                </div>
            </div>
            
            <div class="warning-box">
                ⚠️ <strong>Important:</strong> Your password has been changed. Please update your proxy configuration with the new credentials.
            </div>
        </div>
        
        <div class="footer">
            Styxproxy · Rotated at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC<br>
            © 2024 Styxproxy. All rights reserved.
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
Proxy: {proxy_ip}:{proxy_port}
Protocol: {protocol.upper()}
=========================

⚠️ IMPORTANT: Your password has been changed. Please update your proxy configuration with the new credentials.

- Styxproxy
"""

    return EmailContent(
        subject=f"[Styxproxy] Credentials Rotated - {order_id}",
        html=html,
        text=text,
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
    """Send order confirmation email to customer (pending payment — one email, no credentials yet)."""
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


async def send_order_active_email(
    customer_email: str,
    customer_name: str,
    order_id: str,
    plan_code: str,
    amount: float,
    currency: str,
    quantity: int,
    bun_username: str,
    proxy_ip: str,
    proxy_port: int,
    protocol: str,
    expires_at: datetime,
) -> EmailResult:
    """Send order confirmation + credentials in ONE email when order is paid and proxy is active."""
    expires_str = expires_at.strftime('%Y-%m-%d %H:%M UTC') if expires_at else "N/A"

    base_styles = _get_base_styles()

    # Combined HTML: order details header → credentials block
    combined_html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Payment Confirmed - Your Proxy is Ready</title>
    <style>
        {base_styles}
    </style>
</head>
<body>
    <div class="email-container">
        <div class="header-bar" style="background: #0AD25A;">
            <img src="data:image/png;base64,{LOGO_B64}" alt="Styxproxy">
        </div>
        <div class="accent-bar"></div>
        
        <div class="content-card success">
            <h1>🎉 Payment Confirmed — Your Proxy is Ready!</h1>
            <p class="muted-text" style="margin-top: -8px; margin-bottom: 24px;">Order {order_id}</p>
            
            <p>Hi {customer_name},</p>
            
            <p>Great news! Your payment has been confirmed and your proxy is now active. Here are your full order details and credentials:</p>
            
            <div class="order-id">{order_id}</div>
            
            <div class="credentials-box">
                <div class="cred-row">
                    <div class="cred-label">Username</div>
                    <div class="cred-value">{bun_username}</div>
                </div>
                <div class="cred-row">
                    <div class="cred-label">Proxy Address</div>
                    <div class="cred-value">{proxy_ip}:{proxy_port}</div>
                </div>
                <div class="cred-row">
                    <div class="cred-label">Protocol</div>
                    <div class="cred-value">{protocol.upper()}</div>
                </div>
                <div class="cred-row" style="margin-bottom: 0;">
                    <div class="cred-label">Expires</div>
                    <div class="cred-value">{expires_str}</div>
                </div>
            </div>
            
            <table class="details-table">
                <tr>
                    <td>Plan</td>
                    <td>{plan_code}</td>
                </tr>
                <tr>
                    <td>Quantity</td>
                    <td>{quantity}</td>
                </tr>
                <tr>
                    <td>Amount Paid</td>
                    <td style="font-size: 20px; color: #0AD25A;">{currency} {amount:,.2f}</td>
                </tr>
            </table>
            
            <div class="help-box">
                <strong>Having issues?</strong> Reply to this email or WhatsApp us immediately. We'll help you get started!
            </div>
        </div>
        
        <div class="footer">
            Styxproxy · Order confirmed at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC<br>
            © 2024 Styxproxy. All rights reserved.
        </div>
    </div>
</body>
</html>
"""

    combined_text = f"""[Styxproxy] Payment Confirmed — Your Proxy is Ready! - {order_id}

Hi {customer_name},

Great news! Your payment has been confirmed and your proxy is now active.

Order ID: {order_id}
Plan: {plan_code}
Quantity: {quantity}
Amount Paid: {currency} {amount:,.2f}

=== YOUR PROXY CREDENTIALS ===
Username: {bun_username}
Proxy: {proxy_ip}:{proxy_port}
Protocol: {protocol.upper()}
Expires: {expires_str}
================================

You can now use your proxy immediately.

Having issues? Reply to this email or WhatsApp us immediately.

- Styxproxy
"""

    recipient = EmailRecipient(email=customer_email, name=customer_name)
    return await _send_via_resend(
        recipient=recipient,
        subject=f"[Styxproxy] Payment Confirmed — Your Proxy is Ready! - {order_id}",
        html=combined_html,
        text=combined_text,
    )


async def send_proxy_credentials_email(
    customer_email: str,
    customer_name: str,
    order_id: str,
    plan_code: str,
    bun_username: str,
    proxy_ip: str,
    proxy_port: int,
    protocol: str,
    expires_at: datetime,
) -> EmailResult:
    """Send proxy credentials email to customer."""
    content = _render_proxy_credentials_email(
        customer_name=customer_name,
        order_id=order_id,
        plan_code=plan_code,
        bun_username=bun_username,
        proxy_ip=proxy_ip,
        proxy_port=proxy_port,
        protocol=protocol,
        expires_at=expires_at,
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
    amount: float,
    currency: str,
    reason: str,
) -> EmailResult:
    """Send refund processed email to customer."""
    content = _render_refund_processed_email(
        customer_name=customer_name,
        order_id=order_id,
        amount=amount,
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
    proxy_ip: str,
    proxy_port: int,
    protocol: str,
) -> EmailResult:
    """Send credentials rotated email to customer."""
    content = _render_credentials_rotated_email(
        customer_name=customer_name,
        order_id=order_id,
        new_username=new_username,
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


# Alias for backward compatibility with orders.py
async def send_rotation_notification_email(
    customer_email: str,
    bun_username: str,
    bun_password: str,
    proxy_ip: str,
    proxy_port: int,
    order_id: str,
) -> EmailResult:
    """Send rotation notification email (alias for backward compatibility)."""
    # This is used in orders.py but we don't have customer_name here
    # Use a generic greeting since we don't have the name
    content = _render_credentials_rotated_email(
        customer_name="Customer",
        order_id=order_id,
        new_username=bun_username,
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
