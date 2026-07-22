"""Email service using Resend API.

Provides transactional email functionality with Styxproxy brand design language:
- Contact form submissions
- Charon escalation notifications  
- Admin notifications (orders, refunds, etc.)
- Order confirmations and credentials delivery
- Password reset and admin invites

Design language matches the receipt PDF:
- Dark theme by default (#0f0f0f background)
- Light theme via prefers-color-scheme
- Green accent (#0AD25A / #10B981)
- Card-based layout with dividers
- Credentials with green border
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
# Logo processing for inline embedding (dual mode support)
# =============================================================================
def _get_logo_b64_dark() -> str:
    """Process and return the dark mode Styxproxy logo as base64 PNG."""
    logo = Image.open("/app/app/assets/styxproxy_logo_dark.png")
    # The image is already cropped to just the logo (icon + wordmark)
    # Resize for email header — 480px wide, aspect ratio preserved
    target_w = 480
    ratio = target_w / logo.size[0]
    target_h = int(logo.size[1] * ratio)
    resized = logo.resize((target_w, target_h), Image.LANCZOS)
    buf = io.BytesIO()
    resized.save(buf, format="PNG", optimize=True)
    return base64.b64encode(buf.getvalue()).decode()


def _get_logo_b64_light() -> str:
    """Process and return the light mode Styxproxy logo as base64 PNG."""
    logo = Image.open("/app/app/assets/styxproxy_logo_light.png")
    # The image is already cropped to just the logo (icon + wordmark)
    target_w = 480
    ratio = target_w / logo.size[0]
    target_h = int(logo.size[1] * ratio)
    resized = logo.resize((target_w, target_h), Image.LANCZOS)
    buf = io.BytesIO()
    resized.save(buf, format="PNG", optimize=True)
    return base64.b64encode(buf.getvalue()).decode()


# Cache logos at module load time
LOGO_DARK_B64 = _get_logo_b64_dark()
LOGO_LIGHT_B64 = _get_logo_b64_light()


# =============================================================================
# Base email template components - matches receipt PDF design language
# =============================================================================
def _get_base_styles() -> str:
    """Get the base CSS styles for all emails - matches receipt PDF design."""
    return """
        /* Reset and base styles */
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        /* Styxproxy Brand Colors - matches receipt PDF */
        :root {
            --brand-primary: #10B981;
            --brand-primary-brighter: #0AD25A;
            --brand-accent: #f59e0b;
            --brand-bg: #0f0f0f;
            --brand-card: #1a1a1a;
            --brand-foreground: #f5f5f5;
            --brand-muted: #9ca3af;
            --brand-border: #2a2a2a;
            --brand-divider: #262626;
        }
        
        @media (prefers-color-scheme: light) {
            :root {
                --brand-bg: #ffffff;
                --brand-card: #f9fafb;
                --brand-foreground: #0f0f0f;
                --brand-muted: #6b7280;
                --brand-border: #e5e7eb;
                --brand-divider: #e5e7eb;
                --brand-primary: #059669;
            }
        }
        
        /* Dark theme (default) */
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', sans-serif;
            line-height: 1.6;
            color: var(--brand-foreground);
            background-color: var(--brand-bg);
            margin: 0;
            padding: 0;
        }
        
        .email-wrapper {
            width: 100%;
            background-color: var(--brand-bg);
        }
        
        .email-container {
            max-width: 600px;
            margin: 0 auto;
            padding: 0;
        }
        
        /* Top accent bar - 4mm thin green bar */
        .accent-bar-top {
            height: 4px;
            background: linear-gradient(90deg, #10B981 0%, #0AD25A 50%, #22FF7A 100%);
        }
        
        /* Bottom accent bar */
        .accent-bar-bottom {
            height: 4px;
            background: linear-gradient(90deg, #22FF7A 0%, #0AD25A 50%, #10B981 100%);
        }
        
        /* Header section */
        .header-section {
            padding: 24px 24px 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .logo-section {
            display: flex;
            align-items: center;
            gap: 12px;
        }
        
        .logo-dark { display: block; }
        .logo-light { display: none; }
        
        @media (prefers-color-scheme: light) {
            .logo-dark { display: none !important; }
            .logo-light { display: block !important; }
        }
        
        .logo-subtitle {
            font-size: 10px;
            color: var(--brand-muted);
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-top: 2px;
        }
        
        .header-label {
            font-size: 11px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: var(--brand-primary-brighter);
            text-align: right;
        }
        
        .header-sublabel {
            font-size: 9px;
            color: var(--brand-muted);
            margin-top: 2px;
        }
        
        /* Horizontal divider */
        .divider {
            height: 1px;
            background-color: var(--brand-divider);
            margin: 0 24px;
        }
        
        /* Content section */
        .content-section {
            padding: 24px;
        }
        
        /* Section label - small uppercase muted */
        .section-label {
            font-size: 9px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: var(--brand-muted);
            margin-bottom: 8px;
        }
        
        /* Main heading - 22pt bold */
        .main-heading {
            font-size: 22px;
            font-weight: 700;
            color: var(--brand-foreground);
            margin-bottom: 8px;
        }
        
        .subheading {
            font-size: 14px;
            color: var(--brand-muted);
            margin-bottom: 20px;
        }
        
        /* Pill badges */
        .pill {
            display: inline-block;
            padding: 6px 14px;
            border-radius: 4.5px;
            font-size: 10px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        .pill-green {
            background-color: #10B981;
            color: #000000;
        }
        
        .pill-amber {
            background-color: #f59e0b;
            color: #000000;
        }
        
        .pill-red {
            background-color: #ef4444;
            color: #ffffff;
        }
        
        /* Card - matches receipt PDF: #1a1a1a bg, rounded 3mm corners */
        .card {
            background-color: var(--brand-card);
            border-radius: 3px;
            padding: 20px;
            margin: 16px 0;
        }
        
        /* Card row with divider */
        .card-row {
            display: flex;
            justify-content: space-between;
            padding: 12px 0;
            border-bottom: 1px solid var(--brand-divider);
        }
        
        .card-row:last-child {
            border-bottom: none;
        }
        
        .card-label {
            font-size: 10px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: var(--brand-muted);
        }
        
        .card-value {
            font-size: 14px;
            font-weight: 600;
            color: var(--brand-foreground);
            text-align: right;
        }
        
        .card-value-primary {
            color: var(--brand-primary-brighter);
        }
        
        .card-value-large {
            font-size: 18px;
            font-weight: 700;
        }
        
        /* Items section */
        .items-header {
            display: flex;
            justify-content: space-between;
            padding: 12px 0;
            border-bottom: 1px solid var(--brand-divider);
            margin-bottom: 12px;
        }
        
        .items-label {
            font-size: 9px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: var(--brand-muted);
        }
        
        .item-row {
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            color: var(--brand-muted);
            font-size: 13px;
        }
        
        .item-name {
            color: var(--brand-foreground);
        }
        
        /* Total paid pill */
        .total-pill {
            background-color: #10B981;
            color: #000000;
            padding: 10px 16px;
            border-radius: 2px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-top: 16px;
        }
        
        .total-label {
            font-size: 10px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        .total-amount {
            font-size: 16px;
            font-weight: 700;
        }
        
        /* Credentials section with green border */
        .credentials-card {
            background-color: var(--brand-bg);
            border: 1px solid var(--brand-primary-brighter);
            border-radius: 3px;
            padding: 16px;
            margin: 16px 0;
        }
        
        .credentials-header {
            font-size: 11px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: var(--brand-primary-brighter);
            margin-bottom: 16px;
        }
        
        .cred-row {
            display: flex;
            justify-content: space-between;
            padding: 10px 0;
            border-bottom: 1px solid var(--brand-divider);
        }
        
        .cred-row:last-child {
            border-bottom: none;
        }
        
        .cred-label {
            font-size: 10px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: var(--brand-muted);
        }
        
        .cred-value {
            font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
            font-size: 13px;
            font-weight: 600;
            color: var(--brand-primary-brighter);
            text-align: right;
            word-break: break-all;
        }
        
        /* Support section */
        .support-card {
            background-color: var(--brand-card);
            border-radius: 3px;
            padding: 16px;
            margin-top: 20px;
        }
        
        .support-title {
            font-size: 11px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: var(--brand-foreground);
            margin-bottom: 12px;
        }
        
        .support-row {
            display: flex;
            justify-content: space-between;
            font-size: 12px;
            margin-bottom: 6px;
        }
        
        .support-label {
            color: var(--brand-muted);
        }
        
        .support-link {
            color: var(--brand-primary-brighter);
            text-decoration: none;
            font-weight: 500;
        }
        
        /* CTA Button */
        .cta-button {
            display: inline-block;
            background: #10B981;
            color: #000000;
            font-weight: 700;
            padding: 14px 28px;
            border-radius: 4px;
            text-decoration: none;
            margin: 16px 0;
        }
        
        .cta-button:hover {
            background: #0AD25A;
        }
        
        /* Warning box */
        .warning-box {
            background-color: var(--brand-card);
            border-left: 4px solid #f59e0b;
            padding: 16px;
            border-radius: 0 3px 3px 0;
            margin: 16px 0;
            font-size: 13px;
            color: #f59e0b;
        }
        
        /* Footer */
        .footer {
            text-align: center;
            padding: 20px 24px;
            color: var(--brand-muted);
            font-size: 11px;
        }
        
        .footer-auto {
            font-style: italic;
            margin-bottom: 8px;
        }
        
        .footer-copyright {
            color: var(--brand-muted);
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
            
            # Resend supports custom headers for threading
            custom_headers = {}
            if in_reply_to:
                custom_headers["In-Reply-To"] = in_reply_to
            if references:
                custom_headers["References"] = references
            
            if custom_headers:
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
    """Render the email header with logo and label - matches receipt PDF."""
    return f"""
        <div class="accent-bar-top"></div>
        <div class="header-section">
            <div class="logo-section">
                <img class="logo-dark" src="data:image/png;base64,{LOGO_DARK_B64}" alt="Styxproxy" width="200" height="58" style="display:block;width:200px;height:auto;">
                <img class="logo-light" src="data:image/png;base64,{LOGO_LIGHT_B64}" alt="Styxproxy" width="200" height="58" style="display:none;width:200px;height:auto;">
                <div class="logo-subtitle">Anonymous Proxy Service</div>
            </div>
            <div>
                <div class="header-label">{right_label}</div>
                <div class="header-sublabel">{right_sublabel}</div>
            </div>
        </div>
        <div class="divider"></div>
    """


def _render_support_footer() -> str:
    """Render the support footer section - matches receipt PDF."""
    return """
        <div class="support-card">
            <div class="support-title">NEED HELP?</div>
            <div class="support-row">
                <span class="support-label">Chat:</span>
                <a href="https://styxproxy.com/contact" class="support-link">styxproxy.com/contact</a>
            </div>
            <div class="support-row">
                <span class="support-label">Email:</span>
                <a href="mailto:support@styxproxy.com" class="support-link">support@styxproxy.com</a>
            </div>
            <div class="support-row" style="margin-bottom: 0;">
                <span class="support-label">Web:</span>
                <a href="https://styxproxy.com" class="support-link">styxproxy.com</a>
            </div>
        </div>
    """


def _render_footer() -> str:
    """Render the email footer - matches receipt PDF."""
    return f"""
        <div class="footer">
            <div class="footer-auto">This receipt was generated automatically. No signature required.</div>
            <div class="footer-copyright">© 2026 Styxproxy — Anonymous proxy service for the discerning.</div>
        </div>
        <div class="accent-bar-bottom"></div>
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
    
    html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="color-scheme" content="light dark">
    <meta name="supported-color-schemes" content="light dark">
    <title>Re: {original_subject}</title>
    <style>
        {base_styles}
    </style>
</head>
<body>
    <div class="email-wrapper">
        <div class="email-container">
            <div class="accent-bar-top"></div>
            <div class="header-section">
                <div class="logo-section">
                    <img class="logo-dark" src="data:image/png;base64,{LOGO_DARK_B64}" alt="Styxproxy" width="200" height="58" style="display:block;width:200px;height:auto;">
                    <img class="logo-light" src="data:image/png;base64,{LOGO_LIGHT_B64}" alt="Styxproxy" width="200" height="58" style="display:none;width:200px;height:auto;">
                    <div class="logo-subtitle">Styxproxy Support</div>
                </div>
                <div>
                    <div class="header-label">REPLY</div>
                </div>
            </div>
            <div class="divider"></div>
            
            <div class="content-section">
                <div class="section-label">SUPPORT REPLY</div>
                <div class="main-heading">{greeting}</div>
                
                <div style="color: var(--brand-muted); font-size: 13px; margin-bottom: 16px;">
                    Re: {original_subject}
                </div>
                
                <div class="card">
                    {reply_body_html}
                </div>
                
                <p style="color: var(--brand-muted); font-size: 12px; margin-top: 20px;">
                    This reply was sent by {admin_name} from Styxproxy Support.
                </p>
                
                {_render_support_footer()}
            </div>
            
            <div class="footer">
                <div class="footer-auto">Automated support response</div>
                <div class="footer-copyright">© 2026 Styxproxy — Anonymous proxy service for the discerning.</div>
            </div>
            <div class="accent-bar-bottom"></div>
        </div>
    </div>
</body>
</html>
"""
    
    # Simple text version - extract the HTML to text conversion
    text_reply = reply_body_html.replace('<br>', '\n').replace('<p>', '').replace('</p>', '\n')
    text = f"""Re: {original_subject}

{greeting}

{text_reply}

---
This reply was sent by {admin_name} from Styxproxy Support.

Need help? Contact us at support@styxproxy.com or visit styxproxy.com

© 2026 Styxproxy
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
    """Render contact form submission email (to admin) - matches receipt design."""
    phone_html = f"""
        <div class="card-row">
            <span class="card-label">Phone</span>
            <span class="card-value">{phone}</span>
        </div>
    """ if phone else ""
    
    ip_html = f"""
        <div class="card-row">
            <span class="card-label">IP Address</span>
            <span class="card-value">{ip_address}</span>
        </div>
    """ if ip_address else ""

    base_styles = _get_base_styles()

    html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="color-scheme" content="light dark">
    <meta name="supported-color-schemes" content="light dark">
    <title>New Contact Form Submission</title>
    <style>
        {base_styles}
    </style>
</head>
<body>
    <div class="email-wrapper">
        <div class="email-container">
            {_render_header("CONTACT SUBMISSION", "styxproxy.com")}
            
            <div class="content-section">
                <div class="section-label">NEW MESSAGE</div>
                <div class="main-heading">New message from {name}</div>
                
                <div class="card">
                    <div class="card-row">
                        <span class="card-label">Name</span>
                        <span class="card-value">{name}</span>
                    </div>
                    <div class="card-row">
                        <span class="card-label">Email</span>
                        <span class="card-value card-value-primary">{email}</span>
                    </div>
                    {phone_html}
                    <div class="card-row">
                        <span class="card-label">Message</span>
                    </div>
                    <div style="padding: 12px 0; color: var(--brand-foreground); font-size: 14px; line-height: 1.6;">
                        {message.replace(chr(10), '<br>')}
                    </div>
                    {ip_html}
                </div>
                
                <div style="text-align: center; margin-top: 20px;">
                    <a href="https://styxproxy.com/admin/contacts" class="cta-button">View in Admin Panel →</a>
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

Submitted at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC
© 2026 Styxproxy
"""

    return EmailContent(
        subject="[Styxproxy] New Contact Form Submission",
        html=html,
        text=text,
    )


def _render_customer_confirmation_email(
    name: str,
) -> str:
    """Render customer confirmation email - matches receipt design."""
    base_styles = _get_base_styles()

    return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="color-scheme" content="light dark">
    <meta name="supported-color-schemes" content="light dark">
    <title>Message Received</title>
    <style>
        {base_styles}
    </style>
</head>
<body>
    <div class="email-wrapper">
        <div class="email-container">
            {_render_header("MESSAGE RECEIVED", "styxproxy.com")}
            
            <div class="content-section">
                <div class="section-label">THANK YOU</div>
                <div class="main-heading">Thanks for reaching out, {name}.</div>
                <div class="subheading">We received your message and will respond within 24 hours.</div>
                
                <div class="card">
                    <div style="text-align: center; padding: 20px 0;">
                        <div style="font-size: 40px; margin-bottom: 16px;">✓</div>
                        <div style="color: var(--brand-foreground); font-size: 16px;">
                            Your message has been received. Our team will get back to you as soon as possible.
                        </div>
                    </div>
                </div>
                
                <div style="text-align: center; margin-top: 20px;">
                    <a href="https://styxproxy.com" class="cta-button">Visit styxproxy.com →</a>
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
            <div class="card-row">
                <span class="card-label">Email</span>
                <span class="card-value card-value-primary">{customer_email}</span>
            </div>
        """
    if customer_phone:
        contact_info += f"""
            <div class="card-row">
                <span class="card-label">Phone</span>
                <span class="card-value">{customer_phone}</span>
            </div>
        """

    base_styles = _get_base_styles()

    html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="color-scheme" content="light dark">
    <meta name="supported-color-schemes" content="light dark">
    <title>Charon Escalation</title>
    <style>
        {base_styles}
    </style>
</head>
<body>
    <div class="email-wrapper">
        <div class="email-container">
            {_render_header("ESCALATION", "Action Required")}
            
            <div class="content-section">
                <div class="section-label">CHARON ESCALATION</div>
                <div class="main-heading">Charon escalated a conversation</div>
                <div class="subheading">Immediate attention required</div>
                
                <div class="card">
                    <div class="card-row">
                        <span class="card-label">Conversation ID</span>
                        <span class="card-value card-value-primary card-value-large">{conversation_id[:16]}...</span>
                    </div>
                    {contact_info}
                    <div class="card-row">
                        <span class="card-label">Latest Message</span>
                    </div>
                    <div style="padding: 12px 0; color: var(--brand-foreground); font-size: 14px; line-height: 1.6;">
                        {message.replace(chr(10), '<br>')}
                    </div>
                    <div class="card-row">
                        <span class="card-label">Conversation History</span>
                    </div>
                    <div style="padding: 12px 0; color: var(--brand-muted); font-size: 12px; line-height: 1.6; font-family: monospace; white-space: pre-wrap;">
                        {history_summary}
                    </div>
                </div>
                
                <div class="warning-box">
                    ⚠️ <strong>Action Required:</strong> Please respond to this conversation as soon as possible.
                </div>
            </div>
            
            {_render_footer()}
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


# =============================================================================
# Admin Notification Email Template
# =============================================================================

def _render_admin_notification_email(
    title: str,
    details: dict,
    pill_type: str = "green",
) -> EmailContent:
    """Render admin notification email - dynamic title pill."""
    pill_class = "pill-green"
    if pill_type == "amber":
        pill_class = "pill-amber"
    elif pill_type == "red":
        pill_class = "pill-red"
    
    details_html = "".join(
        f"""
        <div class="card-row">
            <span class="card-label">{k}</span>
            <span class="card-value">{v}</span>
        </div>
        """
        for k, v in details.items()
    )

    base_styles = _get_base_styles()

    html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="color-scheme" content="light dark">
    <meta name="supported-color-schemes" content="light dark">
    <title>{title}</title>
    <style>
        {base_styles}
    </style>
</head>
<body>
    <div class="email-wrapper">
        <div class="email-container">
            {_render_header(title.upper(), "Admin Notification")}
            
            <div class="content-section">
                <div class="section-label">NOTIFICATION</div>
                <div class="main-heading">{title}</div>
                
                <div class="card">
                    {details_html}
                </div>
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

Notification sent at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC
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
    """Render admin invite email - matches receipt design."""
    invite_link = f"https://styxproxy.com/admin/setup?code={invite_code}"

    base_styles = _get_base_styles()

    html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="color-scheme" content="light dark">
    <meta name="supported-color-schemes" content="light dark">
    <title>Admin Invite</title>
    <style>
        {base_styles}
    </style>
</head>
<body>
    <div class="email-wrapper">
        <div class="email-container">
            {_render_header("ADMIN INVITE", "styxproxy.com")}
            
            <div class="content-section">
                <div class="section-label">INVITATION</div>
                <div class="main-heading">You're invited to Styxproxy Admin</div>
                <div class="subheading">You've been granted access to the admin panel</div>
                
                <div class="card">
                    <div class="card-row">
                        <span class="card-label">Role</span>
                        <span class="card-value card-value-primary">{role}</span>
                    </div>
                    <div class="card-row">
                        <span class="card-label">Email</span>
                        <span class="card-value">{email}</span>
                    </div>
                    <div class="card-row">
                        <span class="card-label">Expires</span>
                        <span class="card-value">{expires_in_hours} hours</span>
                    </div>
                </div>
                
                <div style="text-align: center; margin-top: 20px;">
                    <a href="{invite_link}" class="cta-button">Set Up Account →</a>
                </div>
                
                <p style="color: var(--brand-muted); font-size: 13px; margin-top: 16px; text-align: center;">
                    Or copy this link: <span style="color: var(--brand-primary-brighter); word-break: break-all;">{invite_link}</span>
                </p>
                
                <div class="warning-box">
                    ⚠️ <strong>Important:</strong> This invite expires in {expires_in_hours} hours. If you didn't request this, please ignore this email.
                </div>
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

Set up your account: {invite_link}

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
    """Render password reset email - matches receipt design."""
    reset_link = f"https://styxproxy.com/admin/reset-password?token={reset_token}"

    base_styles = _get_base_styles()

    html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="color-scheme" content="light dark">
    <meta name="supported-color-schemes" content="light dark">
    <title>Password Reset</title>
    <style>
        {base_styles}
    </style>
</head>
<body>
    <div class="email-wrapper">
        <div class="email-container">
            {_render_header("PASSWORD RESET", "styxproxy.com")}
            
            <div class="content-section">
                <div class="section-label">SECURITY</div>
                <div class="main-heading">Reset your admin password</div>
                <div class="subheading">Create a new password for your account</div>
                
                <div class="card">
                    <div style="text-align: center; padding: 20px 0;">
                        <div style="font-size: 40px; margin-bottom: 16px;">🔐</div>
                        <div style="color: var(--brand-foreground); font-size: 14px; margin-bottom: 20px;">
                            We received a request to reset your Styxproxy Admin password.
                        </div>
                    </div>
                </div>
                
                <div style="text-align: center; margin-top: 20px;">
                    <a href="{reset_link}" class="cta-button">Reset Password →</a>
                </div>
                
                <p style="color: var(--brand-muted); font-size: 13px; margin-top: 16px; text-align: center;">
                    Or copy this link: <span style="color: var(--brand-primary-brighter); word-break: break-all;">{reset_link}</span>
                </p>
                
                <div class="warning-box">
                    ⏱️ <strong>Note:</strong> This link expires in <strong>1 hour</strong>.<br><br>
                    If you didn't request this, please ignore this email. Your password will remain unchanged.
                </div>
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
    """Render order confirmation email (pending payment) - matches receipt design."""
    base_styles = _get_base_styles()

    html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="color-scheme" content="light dark">
    <meta name="supported-color-schemes" content="light dark">
    <title>Order Placed</title>
    <style>
        {base_styles}
    </style>
</head>
<body>
    <div class="email-wrapper">
        <div class="email-container">
            {_render_header("PAYMENT PENDING", "styxproxy.com")}
            
            <div class="content-section">
                <div class="section-label">ORDER CONFIRMATION</div>
                <div class="main-heading">Thanks for your order, {customer_name}!</div>
                <div class="subheading">Complete your payment to activate your proxy</div>
                
                <div class="card">
                    <div class="card-row">
                        <span class="card-label">Order ID</span>
                        <span class="card-value card-value-primary card-value-large">{order_id[:16]}...</span>
                    </div>
                    <div class="card-row">
                        <span class="card-label">Plan</span>
                        <span class="card-value">{plan_code}</span>
                    </div>
                    <div class="card-row">
                        <span class="card-label">Quantity</span>
                        <span class="card-value">{quantity} {"unit" if quantity == 1 else "units"}</span>
                    </div>
                    <div class="card-row">
                        <span class="card-label">Amount</span>
                        <span class="card-value card-value-primary card-value-large">{currency} {amount:,.2f}</span>
                    </div>
                </div>
                
                <div class="warning-box">
                    <strong>Next step:</strong> Complete your payment. Once confirmed, your proxy credentials will be sent to this email automatically.
                </div>
                
                <div style="text-align: center; margin-top: 20px;">
                    <a href="https://styxproxy.com/pay/{order_id}" class="cta-button">Complete Payment →</a>
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
    bun_username: str,
    bun_password: str,
    proxy_ip: str,
    proxy_port: int,
    protocol: str,
    expires_at: datetime,
    payment_method: str = "Card / Bank / USSD / QR",
) -> EmailContent:
    """Render proxy credentials email (order paid + active) - matches receipt design."""
    expires_str = expires_at.strftime('%Y-%m-%d %H:%M UTC') if expires_at else "N/A"
    full_format = f"http://{bun_username}:{bun_password}@{proxy_ip}:{proxy_port}"

    base_styles = _get_base_styles()

    html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="color-scheme" content="light dark">
    <meta name="supported-color-schemes" content="light dark">
    <title>Your Proxy is Ready</title>
    <style>
        {base_styles}
    </style>
</head>
<body>
    <div class="email-wrapper">
        <div class="email-container">
            {_render_header("FULFILLED", "styxproxy.com")}
            
            <div class="content-section">
                <div class="section-label">ORDER CONFIRMATION</div>
                <div class="main-heading">Your proxy is ready, {customer_name}!</div>
                <div class="subheading">Your payment has been confirmed and proxy is active</div>
                
                <div class="card">
                    <div class="card-row">
                        <span class="card-label">Transaction Reference</span>
                        <span class="card-value card-value-primary">{tx_ref}</span>
                    </div>
                    <div class="card-row">
                        <span class="card-label">Order ID</span>
                        <span class="card-value">{order_id[:16]}...</span>
                    </div>
                    <div class="card-row">
                        <span class="card-label">Date</span>
                        <span class="card-value">{datetime.utcnow().strftime('%Y-%m-%d')}</span>
                    </div>
                    <div class="card-row">
                        <span class="card-label">Method</span>
                        <span class="card-value">{payment_method}</span>
                    </div>
                </div>
                
                <div class="items-header">
                    <span class="items-label">ITEMS</span>
                    <span class="items-label" style="text-align: right;">AMOUNT</span>
                </div>
                <div class="item-row">
                    <span class="item-name">🇳🇬 {plan_code} × {quantity}</span>
                    <span>{currency} {amount:,.2f}</span>
                </div>
                
                <div class="total-pill">
                    <span class="total-label">Total Paid</span>
                    <span class="total-amount">{currency} {amount:,.2f}</span>
                </div>
                
                <div class="credentials-card">
                    <div class="credentials-header">YOUR PROXY CREDENTIALS</div>
                    <div class="cred-row">
                        <span class="cred-label">Username</span>
                        <span class="cred-value">{bun_username}</span>
                    </div>
                    <div class="cred-row">
                        <span class="cred-label">Password</span>
                        <span class="cred-value">{bun_password}</span>
                    </div>
                    <div class="cred-row">
                        <span class="cred-label">Proxy Address</span>
                        <span class="cred-value">{proxy_ip}:{proxy_port}</span>
                    </div>
                    <div class="cred-row">
                        <span class="cred-label">Protocol</span>
                        <span class="cred-value">{protocol.upper()}</span>
                    </div>
                    <div class="cred-row">
                        <span class="cred-label">Full Format</span>
                        <span class="cred-value" style="font-size: 11px;">{full_format[:50]}...</span>
                    </div>
                    <div class="cred-row">
                        <span class="cred-label">Expires</span>
                        <span class="cred-value">{expires_str}</span>
                    </div>
                </div>
                
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
Username: {bun_username}
Password: {bun_password}
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
        subject=f"[Styxproxy] Payment Confirmed — Your Proxy is Ready! - {order_id[:8]}",
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
    bun_username: str,
    bun_password: str,
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
        bun_username=bun_username,
        bun_password=bun_password,
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
    """Render refund processed email - matches receipt design."""
    base_styles = _get_base_styles()

    html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="color-scheme" content="light dark">
    <meta name="supported-color-schemes" content="light dark">
    <title>Refund Processed</title>
    <style>
        {base_styles}
    </style>
</head>
<body>
    <div class="email-wrapper">
        <div class="email-container">
            {_render_header("REFUND PROCESSED", "styxproxy.com")}
            
            <div class="content-section">
                <div class="section-label">REFUND CONFIRMATION</div>
                <div class="main-heading">Your refund has been processed, {customer_name}!</div>
                <div class="subheading">The refund has been initiated to your original payment method</div>
                
                <div class="card">
                    <div class="card-row">
                        <span class="card-label">Order ID</span>
                        <span class="card-value">{order_id[:16]}...</span>
                    </div>
                    <div class="card-row">
                        <span class="card-label">Original Amount</span>
                        <span class="card-value">{currency} {original_amount:,.2f}</span>
                    </div>
                    <div class="card-row">
                        <span class="card-label">Refund Amount</span>
                        <span class="card-value card-value-primary card-value-large">{currency} {refund_amount:,.2f}</span>
                    </div>
                    <div class="card-row">
                        <span class="card-label">Reason</span>
                        <span class="card-value">{reason}</span>
                    </div>
                </div>
                
                <div style="background: var(--brand-card); padding: 16px; border-radius: 3px; margin: 16px 0; border-left: 4px solid #f59e0b;">
                    <div style="color: #f59e0b; font-size: 13px;">
                        <strong>Note:</strong> Please allow 5-10 business days for the refund to appear in your account. The exact timing depends on your bank or payment provider.
                    </div>
                </div>
                
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
    """Render credentials rotated email - matches receipt design."""
    full_format = f"http://{new_username}:{new_password}@{proxy_ip}:{proxy_port}"

    base_styles = _get_base_styles()

    html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="color-scheme" content="light dark">
    <meta name="supported-color-schemes" content="light dark">
    <title>Credentials Rotated</title>
    <style>
        {base_styles}
    </style>
</head>
<body>
    <div class="email-wrapper">
        <div class="email-container">
            {_render_header("CREDENTIALS ROTATED", "styxproxy.com")}
            
            <div class="content-section">
                <div class="section-label">CREDENTIALS UPDATE</div>
                <div class="main-heading">Your credentials have been updated, {customer_name}.</div>
                <div class="subheading">Your proxy credentials have been rotated for security</div>
                
                <div class="card">
                    <div class="card-row">
                        <span class="card-label">Order ID</span>
                        <span class="card-value">{order_id[:16]}...</span>
                    </div>
                </div>
                
                <div class="credentials-card">
                    <div class="credentials-header">NEW CREDENTIALS</div>
                    <div class="cred-row">
                        <span class="cred-label">Username</span>
                        <span class="cred-value">{new_username}</span>
                    </div>
                    <div class="cred-row">
                        <span class="cred-label">Password</span>
                        <span class="cred-value">{new_password}</span>
                    </div>
                    <div class="cred-row">
                        <span class="cred-label">Proxy Address</span>
                        <span class="cred-value">{proxy_ip}:{proxy_port}</span>
                    </div>
                    <div class="cred-row">
                        <span class="cred-label">Protocol</span>
                        <span class="cred-value">{protocol.upper()}</span>
                    </div>
                    <div class="cred-row">
                        <span class="cred-label">Full Format</span>
                        <span class="cred-value" style="font-size: 11px;">{full_format[:50]}...</span>
                    </div>
                </div>
                
                <div class="warning-box">
                    ⚠️ <strong>Important:</strong> Your password has been changed. Please update your proxy configuration with the new credentials immediately to avoid service interruption.
                </div>
                
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

⚠️ IMPORTANT: Your password has been changed. Please update your proxy configuration with the new credentials immediately.

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
    pill_type: str = "green",
) -> EmailResult:
    """Send general admin notification email."""
    content = _render_admin_notification_email(
        title=title,
        details=details,
        pill_type=pill_type,
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
        title="🛒 New Order",
        details={
            "Order ID": order_id,
            "Customer Phone": customer_phone,
            "Plan": plan_code,
            "Amount": f"{currency} {amount:,.2f}",
            "Status": "Pending Payment",
        },
        pill_type="amber",
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
        title="✅ Order Paid",
        details={
            "Order ID": order_id,
            "Customer Phone": customer_phone,
            "Plan": plan_code,
            "Amount": f"{currency} {amount:,.2f}",
            "Status": "Paid - Processing",
        },
        pill_type="green",
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
        title="💰 Refund Request",
        details={
            "Order ID": order_id,
            "Customer Phone": customer_phone,
            "Amount": f"{currency} {amount:,.2f}",
            "Reason": reason,
            "Action Required": "Review and approve/reject",
        },
        pill_type="amber",
    )


async def send_refund_approved_notification(
    order_id: str,
    customer_phone: str,
    amount: float,
    currency: str,
) -> EmailResult:
    """Send notification to admin when refund is approved."""
    return await send_admin_notification(
        title="✅ Refund Approved",
        details={
            "Order ID": order_id,
            "Customer Phone": customer_phone,
            "Amount": f"{currency} {amount:,.2f}",
            "Status": "Refunded",
        },
        pill_type="green",
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
    bun_username: str,
    bun_password: str,
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
        bun_username=bun_username,
        bun_password=bun_password,
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


async def send_rotation_notification_email(
    customer_email: str,
    bun_username: str,
    bun_password: str,
    proxy_ip: str,
    proxy_port: int,
    order_id: str,
) -> EmailResult:
    """Send rotation notification email (alias for backward compatibility)."""
    content = _render_credentials_rotated_email(
        customer_name="Customer",
        order_id=order_id,
        new_username=bun_username,
        new_password=bun_password,
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
