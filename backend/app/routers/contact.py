"""Contact form API endpoints."""
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr, Field

from app.services.email import send_contact_form_notification

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/contact", tags=["contact"])


class ContactFormRequest(BaseModel):
    """Contact form submission request."""

    name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    message: str = Field(..., min_length=1, max_length=5000)
    phone: Optional[str] = Field(None, max_length=20)


class ContactFormResponse(BaseModel):
    """Contact form submission response."""

    success: bool
    message: str


@router.post(
    "/submit",
    response_model=ContactFormResponse,
    status_code=status.HTTP_201_CREATED,
)
async def submit_contact_form(request: ContactFormRequest):
    """Submit a contact form message.

    Sends notification to admin and confirmation email to customer.
    """
    logger.info(
        "Contact form submission",
        extra={
            "name": request.name,
            "email": request.email,
            "message_length": len(request.message),
        },
    )

    result = await send_contact_form_notification(
        name=request.name,
        email=request.email,
        message=request.message,
        phone=request.phone,
    )

    if not result.success:
        logger.error(
            "Failed to send contact form notification",
            extra={"error": result.error},
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to send message. Please try again or contact us via WhatsApp.",
        )

    return ContactFormResponse(
        success=True,
        message="Your message has been sent! We'll get back to you within 24 hours.",
    )
