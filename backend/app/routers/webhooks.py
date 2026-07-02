"""Webhooks router."""
import json
from typing import Any, Optional
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_session
from app.config import get_settings
from app.services.flutterwave import verify_flutterwave_signature, is_webhook_processed, mark_webhook_processed, process_payment_webhook
from app.services.audit import log_audit_event
from app.schemas import FlutterwaveWebhookPayload
