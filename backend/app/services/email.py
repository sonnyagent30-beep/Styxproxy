"""Email service using Resend API.

Provides transactional email functionality:
- Contact form submissions
- Charon escalation notifications
- Admin notifications (orders, refunds, etc.)
"""
import logging
from datetime import datetime
from enum import Enum
from typing import Optional

import httpx
from pydantic import BaseModel, EmailStr

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class EmailTemplate(str, Enum):
    """Predefined email templates."""

    CONTACT_FORM = "contact_form"
    CHARON_ESCALATION = "charon_escalation"
    NEW_ORDER = "new_order"
    ORDER_PAID = "order_paid"
    REFUND_REQUEST = "refund_request"
    REFUND_APPROVED = "refund_approved"
    REFUND_REJECTED = "refund_rejected"
    TRIAL_CLAIMED = "trial_claimed"


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
                    "Resend API error",
                    status=response.status_code,
                    error=error_body,
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
        logger.error("Failed to send email", error=str(e))
        return EmailResult(
            success=False,
            status="http_error",
            error=f"HTTP error: {str(e)}",
        )
    except Exception as e:
        logger.error("Unexpected error sending email", error=str(e))
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
    """Render contact form submission email."""
    phone_html = f"<p><strong>Phone:</strong> {phone}</p>" if phone else ""

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: #1a1a2e; color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }}
            .content {{ background: #f9f9f9; padding: 20px; border-radius: 0 0 8px 8px; }}
            .field {{ margin-bottom: 15px; }}
            .label {{ font-weight: bold; color: #555; }}
            .message {{ background: white; padding: 15px; border-radius: 4px; border-left: 4px solid #1a1a2e; }}
            .footer {{ text-align: center; margin-top: 20px; color: #888; font-size: 12px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h2 style="margin:0;">📬 New Contact Form Submission</h2>
            </div>
            <div class="content">
                <div class="field">
                    <span class="label">Name:</span> {name}
                </div>
                <div class="field">
                    <span class="label">Email:</span> <a href="mailto:{email}">{email}</a>
                </div>
                {phone_html}
                <div class="field">
                    <span class="label">Message:</span>
                    <div class="message">{message.replace(chr(10), '<br>')}</div>
                </div>
            </div>
            <div class="footer">
                Submitted at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC
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
        subject="[Bunche] New Contact Form Submission",
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
    """Render Charon escalation notification email."""
    contact_info = ""
    if customer_email:
        contact_info += f"<p><strong>Email:</strong> <a href='mailto:{customer_email}'>{customer_email}</a></p>"
    if customer_phone:
        contact_info += f"<p><strong>Phone:</strong> {customer_phone}</p>"

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: #e74c3c; color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }}
            .content {{ background: #f9f9f9; padding: 20px; border-radius: 0 0 8px 8px; }}
            .message {{ background: white; padding: 15px; border-radius: 4px; border-left: 4px solid #e74c3c; }}
            .conversation-id {{ background: #333; color: #fff; padding: 8px 12px; border-radius: 4px; font-family: monospace; }}
            .footer {{ text-align: center; margin-top: 20px; color: #888; font-size: 12px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h2 style="margin:0;">⚠️ Charon Escalation</h2>
            </div>
            <div class="content">
                <p><strong>Conversation ID:</strong> <span class="conversation-id">{conversation_id}</span></p>
                {contact_info}
                <p><strong>Latest Message:</strong></p>
                <div class="message">{message.replace(chr(10), '<br>')}</div>
                
                <h3>Conversation History:</h3>
                <pre style="background: white; padding: 15px; border-radius: 4px; white-space: pre-wrap;">{history_summary}</pre>
            </div>
            <div class="footer">
                Escalated at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC
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
        subject=f"[Bunche] Charon Escalation - {conversation_id[:8]}",
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
        f"<tr><td style='padding: 8px; border-bottom: 1px solid #eee;'><strong>{k}:</strong></td><td style='padding: 8px; border-bottom: 1px solid #eee;'>{v}</td></tr>"
        for k, v in details.items()
    )

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: #3498db; color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }}
            .content {{ background: #f9f9f9; padding: 20px; border-radius: 0 0 8px 8px; }}
            table {{ width: 100%; border-collapse: collapse; }}
            .footer {{ text-align: center; margin-top: 20px; color: #888; font-size: 12px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h2 style="margin:0;">🔔 {title}</h2>
            </div>
            <div class="content">
                <table>
                    {details_html}
                </table>
            </div>
            <div class="footer">
                Notification sent at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC
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
        subject=f"[Bunche Admin] {title}",
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
        confirmation_content = EmailContent(
            subject="We received your message - Bunche",
            html=f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <style>
                    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background: #1a1a2e; color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }}
                    .content {{ background: #f9f9f9; padding: 20px; border-radius: 0 0 8px 8px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h2 style="margin:0;">✅ Message Received</h2>
                    </div>
                    <div class="content">
                        <p>Hi {name},</p>
                        <p>Thank you for reaching out! We've received your message and will get back to you within 24 hours.</p>
                        <p>If you have any urgent questions, you can reply to this email or WhatsApp us directly.</p>
                        <p>Best regards,<br>The Bunche Team</p>
                    </div>
                </div>
            </body>
            </html>
            """,
            text=f"Hi {name},\n\nThank you for reaching out! We've received your message and will get back to you within 24 hours.\n\nBest regards,\nThe Bunche Team",
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
