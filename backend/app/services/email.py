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
        confirmation_content = EmailContent(
            subject="We received your message - Styxproxy",
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
                        <p>Best regards,<br>The Styxproxy Team</p>
                    </div>
                </div>
            </body>
            </html>
            """,
            text=f"Hi {name},\n\nThank you for reaching out! We've received your message and will get back to you within 24 hours.\n\nBest regards,\nThe Styxproxy Team",
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
    """Render admin invite email."""
    invite_link = f"https://styxproxy.com/admin/setup?code={invite_code}"

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #e0e0e0; background-color: #0d0d1a; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: #1a1a2e; color: white; padding: 30px 20px; text-align: center; border-radius: 12px 12px 0 0; }}
            .content {{ background: #16162a; padding: 30px 20px; border-radius: 0 0 12px 12px; }}
            .button {{ display: inline-block; background: #4DA3FF; color: #1a1a2e; padding: 14px 28px; text-decoration: none; border-radius: 8px; font-weight: 600; margin: 20px 0; }}
            .details {{ background: #1a1a2e; padding: 15px; border-radius: 8px; margin: 20px 0; }}
            .label {{ color: #888; font-size: 12px; text-transform: uppercase; letter-spacing: 1px; }}
            .value {{ color: #4DA3FF; font-size: 18px; font-weight: 600; margin-top: 5px; }}
            .footer {{ text-align: center; margin-top: 20px; color: #666; font-size: 12px; }}
            .warning {{ background: #2d1f1f; border-left: 4px solid #e74c3c; padding: 15px; border-radius: 4px; margin-top: 20px; font-size: 14px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h2 style="margin:0;">🚀 You've Been Invited to Styxproxy Admin</h2>
            </div>
            <div class="content">
                <p>Hi,</p>
                <p>You've been invited to join the <strong>Styxproxy Admin Panel</strong> with the role of <strong style="color: #4DA3FF;">{role}</strong>.</p>
                
                <div class="details">
                    <div class="label">Your Role</div>
                    <div class="value">{role}</div>
                </div>
                
                <p>Click the button below to set up your account:</p>
                <p style="text-align: center;">
                    <a href="{invite_link}" class="button">Set Up Account</a>
                </p>
                
                <p style="color: #888; font-size: 14px;">
                    Or copy this link: <span style="color: #4DA3FF;">{invite_link}</span>
                </p>
                
                <div class="warning">
                    ⚠️ <strong>Important:</strong> This invite expires in {expires_in_hours} hours. If you didn't request this, please ignore this email.
                </div>
            </div>
            <div class="footer">
                Styxproxy Admin Panel · Sent at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC
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
    """Render password reset email."""
    reset_link = f"https://styxproxy.com/admin/reset-password?token={reset_token}"

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #e0e0e0; background-color: #0d0d1a; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: #1a1a2e; color: white; padding: 30px 20px; text-align: center; border-radius: 12px 12px 0 0; }}
            .content {{ background: #16162a; padding: 30px 20px; border-radius: 0 0 12px 12px; }}
            .button {{ display: inline-block; background: #4DA3FF; color: #1a1a2e; padding: 14px 28px; text-decoration: none; border-radius: 8px; font-weight: 600; margin: 20px 0; }}
            .warning {{ background: #2d1f1f; border-left: 4px solid #e74c3c; padding: 15px; border-radius: 4px; margin-top: 20px; font-size: 14px; }}
            .footer {{ text-align: center; margin-top: 20px; color: #666; font-size: 12px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h2 style="margin:0;">🔐 Reset Your Styxproxy Admin Password</h2>
            </div>
            <div class="content">
                <p>Hi,</p>
                <p>We received a request to reset your Styxproxy Admin password. Click the button below to create a new password:</p>
                
                <p style="text-align: center;">
                    <a href="{reset_link}" class="button">Reset Password</a>
                </p>
                
                <p style="color: #888; font-size: 14px;">
                    Or copy this link: <span style="color: #4DA3FF;">{reset_link}</span>
                </p>
                
                <p style="color: #888; font-size: 14px; margin-top: 20px;">
                    ⏱️ This link expires in <strong>1 hour</strong>.
                </p>
                
                <div class="warning">
                    ⚠️ <strong>If you didn't request this</strong>, please ignore this email. Your password will remain unchanged.
                </div>
            </div>
            <div class="footer">
                Styxproxy Admin Panel · Sent at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC
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
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: #1a1a2e; color: white; padding: 30px 20px; text-align: center; border-radius: 12px 12px 0 0; }}
            .header-active {{ background: #27ae60; color: white; padding: 30px 20px; text-align: center; border-radius: 12px 12px 0 0; }}
            .content {{ background: #f9f9f9; padding: 30px 20px; border-radius: 0 0 12px 12px; }}
            .order-id {{ background: #1a1a2e; color: #fff; padding: 12px 20px; border-radius: 8px; font-family: monospace; font-size: 18px; text-align: center; margin: 20px 0; }}
            .credentials {{ background: white; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #27ae60; }}
            .cred-row {{ margin-bottom: 15px; }}
            .cred-label {{ color: #666; font-size: 12px; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 4px; }}
            .cred-value {{ font-family: monospace; font-size: 16px; background: #f5f5f5; padding: 8px 12px; border-radius: 4px; word-break: break-all; }}
            .details {{ background: white; padding: 20px; border-radius: 8px; margin: 20px 0; }}
            .detail-row {{ display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid #eee; }}
            .detail-row:last-child {{ border-bottom: none; }}
            .label {{ color: #666; }}
            .value {{ font-weight: 600; }}
            .total {{ font-size: 20px; color: #27ae60; }}
            .footer {{ text-align: center; margin-top: 20px; color: #888; font-size: 12px; }}
            .help {{ background: #e8f4f8; padding: 15px; border-radius: 8px; margin-top: 20px; font-size: 14px; }}
            .pending-note {{ background: #fff3cd; padding: 15px; border-radius: 8px; margin-top: 15px; border-left: 4px solid #ffc107; font-size: 14px; }}
            .section-title {{ font-size: 14px; font-weight: 700; color: #1a1a2e; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 10px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h2 style="margin:0;">📋 Order Placed — Payment Pending</h2>
                <p style="margin:10px 0 0 0; opacity: 0.8;">Awaiting your payment</p>
            </div>
            <div class="content">
                <p>Hi {customer_name},</p>
                <p>Your order has been received. Complete your payment to activate your proxy.</p>

                <div class="order-id">{order_id}</div>

                <div class="details">
                    <div class="detail-row">
                        <span class="label">Plan</span>
                        <span class="value">{plan_code}</span>
                    </div>
                    <div class="detail-row">
                        <span class="label">Quantity</span>
                        <span class="value">{quantity}</span>
                    </div>
                    <div class="detail-row">
                        <span class="label">Amount</span>
                        <span class="value total">{currency} {amount:,.2f}</span>
                    </div>
                </div>

                <div class="pending-note">
                    <strong>Next step:</strong> Complete your payment. Once confirmed, your proxy credentials will be sent to this email automatically.
                </div>

                <div class="help">
                    <strong>Need help?</strong> Reply to this email or WhatsApp us. We're here to help!
                </div>
            </div>
            <div class="footer">
                Styxproxy · Order placed at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC
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
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: #27ae60; color: white; padding: 30px 20px; text-align: center; border-radius: 12px 12px 0 0; }}
            .content {{ background: #f9f9f9; padding: 30px 20px; border-radius: 0 0 12px 12px; }}
            .order-id {{ background: #1a1a2e; color: #fff; padding: 12px 20px; border-radius: 8px; font-family: monospace; font-size: 18px; text-align: center; margin: 20px 0; }}
            .credentials {{ background: white; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #27ae60; }}
            .cred-row {{ margin-bottom: 15px; }}
            .cred-label {{ color: #666; font-size: 12px; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 4px; }}
            .cred-value {{ font-family: monospace; font-size: 16px; background: #f5f5f5; padding: 8px 12px; border-radius: 4px; word-break: break-all; }}
            .cred-value.copy {{ cursor: pointer; }}
            .details {{ background: white; padding: 20px; border-radius: 8px; margin: 20px 0; }}
            .detail-row {{ display: flex; justify-content: space-between; padding: 8px 0; }}
            .label {{ color: #666; }}
            .value {{ font-weight: 600; }}
            .footer {{ text-align: center; margin-top: 20px; color: #888; font-size: 12px; }}
            .help {{ background: #e8f4f8; padding: 15px; border-radius: 8px; margin-top: 20px; font-size: 14px; }}
            .cta {{ display: inline-block; background: #4DA3FF; color: white; padding: 12px 24px; text-decoration: none; border-radius: 8px; font-weight: 600; margin: 10px 0; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h2 style="margin:0;">🎉 Your Proxy is Ready!</h2>
                <p style="margin:10px 0 0 0; opacity: 0.9;">Order {order_id}</p>
            </div>
            <div class="content">
                <p>Hi {customer_name},</p>
                <p>Great news! Your proxy is now active. Here are your credentials:</p>
                
                <div class="order-id">{order_id}</div>
                
                <div class="credentials">
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
                
                <div class="details">
                    <div class="detail-row">
                        <span class="label">Plan</span>
                        <span class="value">{plan_code}</span>
                    </div>
                    <div class="detail-row">
                        <span class="label">Expires</span>
                        <span class="value">{expires_str}</span>
                    </div>
                </div>
                
                <p>You can now use your proxy. Need help getting started?</p>
                
                <div class="help">
                    <strong>Having issues?</strong> Reply to this email or WhatsApp us immediately. We'll help you sort it out!
                </div>
            </div>
            <div class="footer">
                Bunche · Powered by Styxproxy
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
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: #e67e22; color: white; padding: 30px 20px; text-align: center; border-radius: 12px 12px 0 0; }}
            .content {{ background: #f9f9f9; padding: 30px 20px; border-radius: 0 0 12px 12px; }}
            .order-id {{ background: #1a1a2e; color: #fff; padding: 12px 20px; border-radius: 8px; font-family: monospace; font-size: 18px; text-align: center; margin: 20px 0; }}
            .refund-amount {{ font-size: 32px; color: #27ae60; font-weight: bold; text-align: center; margin: 20px 0; }}
            .details {{ background: white; padding: 20px; border-radius: 8px; margin: 20px 0; }}
            .detail-row {{ display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid #eee; }}
            .detail-row:last-child {{ border-bottom: none; }}
            .label {{ color: #666; }}
            .value {{ font-weight: 600; }}
            .footer {{ text-align: center; margin-top: 20px; color: #888; font-size: 12px; }}
            .help {{ background: #e8f4f8; padding: 15px; border-radius: 8px; margin-top: 20px; font-size: 14px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h2 style="margin:0;">💵 Refund Processed</h2>
                <p style="margin:10px 0 0 0; opacity: 0.9;">Order {order_id}</p>
            </div>
            <div class="content">
                <p>Hi {customer_name},</p>
                <p>Your refund has been processed successfully.</p>
                
                <div class="order-id">{order_id}</div>
                
                <div class="refund-amount">{currency} {amount:,.2f}</div>
                
                <div class="details">
                    <div class="detail-row">
                        <span class="label">Original Amount</span>
                        <span class="value">{currency} {amount:,.2f}</span>
                    </div>
                    <div class="detail-row">
                        <span class="label">Refund Amount</span>
                        <span class="value">{currency} {amount:,.2f}</span>
                    </div>
                    <div class="detail-row">
                        <span class="label">Reason</span>
                        <span class="value">{reason}</span>
                    </div>
                </div>
                
                <p>Please allow 5-10 business days for the refund to appear in your account.</p>
                
                <div class="help">
                    <strong>Questions about your refund?</strong> Reply to this email or WhatsApp us with your order ID.
                </div>
            </div>
            <div class="footer">
                Bunche · Refund processed at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC
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
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: #3498db; color: white; padding: 30px 20px; text-align: center; border-radius: 12px 12px 0 0; }}
            .content {{ background: #f9f9f9; padding: 30px 20px; border-radius: 0 0 12px 12px; }}
            .order-id {{ background: #1a1a2e; color: #fff; padding: 12px 20px; border-radius: 8px; font-family: monospace; font-size: 18px; text-align: center; margin: 20px 0; }}
            .credentials {{ background: white; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #3498db; }}
            .cred-row {{ margin-bottom: 15px; }}
            .cred-label {{ color: #666; font-size: 12px; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 4px; }}
            .cred-value {{ font-family: monospace; font-size: 16px; background: #f5f5f5; padding: 8px 12px; border-radius: 4px; word-break: break-all; }}
            .warning {{ background: #fff3cd; border-left: 4px solid #ffc107; padding: 15px; border-radius: 4px; margin-top: 20px; }}
            .footer {{ text-align: center; margin-top: 20px; color: #888; font-size: 12px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h2 style="margin:0;">🔄 Credentials Rotated</h2>
                <p style="margin:10px 0 0 0; opacity: 0.9;">Order {order_id}</p>
            </div>
            <div class="content">
                <p>Hi {customer_name},</p>
                <p>Your proxy credentials have been rotated as requested.</p>
                
                <div class="order-id">{order_id}</div>
                
                <div class="credentials">
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
                
                <div class="warning">
                    <strong>⚠️ Important:</strong> Your password has been changed. Please update your proxy configuration with the new credentials.
                </div>
            </div>
            <div class="footer">
                Bunche · Rotated at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC
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
    # Order confirmation section (pending removal once we consolidate templates)
    order_content = _render_order_confirmation_email(
        customer_name=customer_name,
        order_id=order_id,
        plan_code=plan_code,
        amount=amount,
        currency=currency,
        quantity=quantity,
    )
    # Credentials section
    cred_content = _render_proxy_credentials_email(
        customer_name=customer_name,
        order_id=order_id,
        plan_code=plan_code,
        bun_username=bun_username,
        proxy_ip=proxy_ip,
        proxy_port=proxy_port,
        protocol=protocol,
        expires_at=expires_at,
    )

    expires_str = expires_at.strftime('%Y-%m-%d %H:%M UTC') if expires_at else "N/A"

    # Combined HTML: order details header → credentials block
    combined_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: #27ae60; color: white; padding: 30px 20px; text-align: center; border-radius: 12px 12px 0 0; }}
            .content {{ background: #f9f9f9; padding: 30px 20px; border-radius: 0 0 12px 12px; }}
            .order-id {{ background: #1a1a2e; color: #fff; padding: 12px 20px; border-radius: 8px; font-family: monospace; font-size: 18px; text-align: center; margin: 20px 0; }}
            .section {{ background: white; padding: 20px; border-radius: 8px; margin: 20px 0; }}
            .section-title {{ font-size: 12px; font-weight: 700; color: #4DA3FF; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 12px; }}
            .detail-row {{ display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #eee; }}
            .detail-row:last-child {{ border-bottom: none; }}
            .label {{ color: #666; }}
            .value {{ font-weight: 600; }}
            .total {{ font-size: 20px; color: #27ae60; }}
            .cred-value {{ font-family: monospace; font-size: 16px; background: #f5f5f5; padding: 8px 12px; border-radius: 4px; word-break: break-all; }}
            .credentials-box {{ background: white; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #27ae60; }}
            .cred-row {{ margin-bottom: 15px; }}
            .cred-label {{ color: #666; font-size: 12px; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 4px; }}
            .footer {{ text-align: center; margin-top: 20px; color: #888; font-size: 12px; }}
            .help {{ background: #e8f4f8; padding: 15px; border-radius: 8px; margin-top: 20px; font-size: 14px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h2 style="margin:0;">🎉 Payment Confirmed — Your Proxy is Ready!</h2>
                <p style="margin:10px 0 0 0; opacity: 0.9;">Order {order_id}</p>
            </div>
            <div class="content">
                <p>Hi {customer_name},</p>
                <p>Great news! Your payment has been confirmed and your proxy is now active. Here are your full order details and credentials:</p>

                <div class="order-id">{order_id}</div>

                <div class="section">
                    <div class="section-title">Order Details</div>
                    <div class="detail-row">
                        <span class="label">Plan</span>
                        <span class="value">{plan_code}</span>
                    </div>
                    <div class="detail-row">
                        <span class="label">Quantity</span>
                        <span class="value">{quantity}</span>
                    </div>
                    <div class="detail-row">
                        <span class="label">Amount Paid</span>
                        <span class="value total">{currency} {amount:,.2f}</span>
                    </div>
                </div>

                <div class="section">
                    <div class="section-title">Your Proxy Credentials</div>
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
                    <div class="cred-row" style="margin-bottom:0;">
                        <div class="cred-label">Expires</div>
                        <div class="cred-value">{expires_str}</div>
                    </div>
                </div>

                <div class="help">
                    <strong>Having issues?</strong> Reply to this email or WhatsApp us immediately. We'll help you get started!
                </div>
            </div>
            <div class="footer">
                Styxproxy · Order confirmed at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC
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
