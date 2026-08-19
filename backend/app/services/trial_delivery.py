"""
Trial delivery pipeline — TheoremReach survey completion → trial credentials.

Triggered by the theorem-reach webhook (POST /api/webhooks/theorem-reach).
The webhook fires `process_theorem_reach_trial()` as a background asyncio task,
so the HTTP response returns 200 immediately.

Flow (per survey completion):
  1. Lookup platform_account by device_id (anonymous session).
  2. Check trial limit: 1 survey = 2 hours, max 24 hours per device.
     If already at 24h cap, skip credential creation (still record survey).
  3. Allocate 3proxy port from THREEPROXY_PORT_RANGE.
  4. Call DataImpulse API to create trial credentials ($5 trial gives 5 GB).
  5. Store TrialSession row with trial_started_at / trial_expires_at.
  6. Trigger n8n webhook to deliver credentials via WhatsApp/Telegram.

Sec-177 SEC finding (S2.3): TheoremReach webhook had no signature verification.
Signature verification is done in the webhook handler before this is called.
"""

import asyncio
import logging
import random
import string
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_password_hash
from app.config import get_settings
from app.models import PlatformAccount, StyxproxyCredential, TrialSession

logger = logging.getLogger(__name__)

# Business rules
SURVEY_REWARD_HOURS = 2.0  # 1 survey completion = 2 hours trial credit
MAX_TOTAL_TRIAL_HOURS = 24.0  # max 24 hours per device across all surveys


# ─── Background task ──────────────────────────────────────────────────────────


async def process_theorem_reach_trial(
    device_id: str,
    survey_id: str,
    reward_usd: float,
    country: str = "Nigeria",
) -> dict:
    """
    Main entry point — called as a fire-and-forget asyncio task from the
    theorem-reach webhook handler.

    Returns a dict with keys: status, trial_session_id, threeproxy_port, error.
    """
    try:
        result = await _process_trial_impl(
            device_id=device_id,
            survey_id=survey_id,
            reward_usd=reward_usd,
            country=country,
        )
        logger.info(
            f"theorem_reach_trial: device_id={device_id} survey_id={survey_id} "
            f"result={result}"
        )
        return result
    except Exception as e:
        logger.exception(
            f"theorem_reach_trial: device_id={device_id} survey_id={survey_id} error={e}"
        )
        return {"status": "error", "error": str(e)}


# ─── Core pipeline ────────────────────────────────────────────────────────────


async def _process_trial_impl(
    device_id: str,
    survey_id: str,
    reward_usd: float,
    country: str,
) -> dict:
    """
    Implement the trial delivery pipeline:
      1. Look up platform_account by device_id
      2. Compute new trial window (capped at 24 hours total per device)
      3. Allocate 3proxy port
      4. Call DataImpulse for trial credentials
      5. Persist TrialSession + StyxproxyCredential
      6. Fire n8n credential-delivered webhook
    """
    # Import here to avoid circular imports
    from app.database import async_session
    from app.services.dataimpulse import create_dataimpulse_trial_order
    from app.services.n8n import trigger_credentials_delivered_webhook

    session: AsyncSession
    async with async_session() as session:
        # ── Step 1: Lookup platform_account ───────────────────────────────
        platform_account = await _lookup_platform_account(session, device_id)

        # ── Step 2: Check / update trial limits ──────────────────────────
        trial_session, hours_to_add = await _compute_trial_window(
            session, device_id, survey_id, platform_account
        )
        if hours_to_add <= 0:
            # Already at 24h cap — record the survey for analytics but skip creds
            logger.info(
                f"trial_delivery: device_id={device_id} at 24h cap, skipping credential creation"
            )
            return {
                "status": "capped",
                "device_id": device_id,
                "survey_id": survey_id,
                "message": "Device already at maximum 24-hour trial limit",
            }

        # ── Step 3: Allocate 3proxy port ────────────────────────────────
        threeproxy_port = await _allocate_threeproxy_port(session)
        if threeproxy_port is None:
            raise RuntimeError("No 3proxy ports available in THREEPROXY_PORT_RANGE")

        # ── Step 4: Create DataImpulse trial credentials ──────────────────
        dataimpulse_order = await create_dataimpulse_trial_order(
            device_id=device_id,
            country=country,
        )

        # ── Step 5: Create StyxproxyCredential ────────────────────────────
        username = f"trial_{''.join(random.choices(string.ascii_lowercase, k=8))}"
        password_plain = "".join(random.choices(string.ascii_letters + string.digits, k=16))

        credential = StyxproxyCredential(
            styxproxy_username=username,
            password_hash=get_password_hash(password_plain),
            customer_phone=platform_account.customer.phone if platform_account.customer else None,
            pool_type="trial",
            upstream_proxy_ip=dataimpulse_order.get("proxy_ip", ""),
            upstream_proxy_port=dataimpulse_order.get("proxy_port", 1080),
            dante_port=threeproxy_port,
            status="active",
            expires_at=trial_session.trial_expires_at,
        )
        session.add(credential)
        await session.flush()

        # ── Step 6: Update TrialSession with credential + port ───────────
        trial_session.styxproxy_credential_id = credential.id
        trial_session.threeproxy_port = threeproxy_port
        trial_session.status = "active"

        await session.commit()
        await session.refresh(trial_session)

        # ── Step 7: Trigger n8n credential delivery webhook ───────────────
        phone = platform_account.customer.phone if platform_account.customer else None
        await trigger_credentials_delivered_webhook(
            order_id=f"TRIAL-{trial_session.id}",
            tx_ref=f"TR-{survey_id}",
            phone=phone or "",
            channel="whatsapp",  # default; n8n workflow can route based on customer preference
            bun_username=username,
            bun_password=password_plain,
            proxy_ip=dataimpulse_order.get("proxy_ip", ""),
            proxy_port=dataimpulse_order.get("proxy_port", 1080),
            expires_at=trial_session.trial_expires_at,
        )

        return {
            "status": "delivered",
            "trial_session_id": trial_session.id,
            "threeproxy_port": threeproxy_port,
            "dataimpulse_order_id": dataimpulse_order.get("order_id"),
        }


# ─── Platform account lookup ───────────────────────────────────────────────────


async def _lookup_platform_account(
    session: AsyncSession, device_id: str
) -> Optional[PlatformAccount]:
    """Find the platform_account for this device_id, if any."""
    result = await session.execute(
        select(PlatformAccount).where(PlatformAccount.device_id == device_id)
    )
    return result.scalar_one_or_none()


# ─── Trial window computation ──────────────────────────────────────────────────


async def _compute_trial_window(
    session: AsyncSession,
    device_id: str,
    survey_id: str,
    platform_account: Optional[PlatformAccount],
) -> tuple[Optional[TrialSession], float]:
    """
    Compute how many hours to add for this survey, respecting the 24h cap.

    Returns (trial_session, hours_to_add):
      - If device has no active session: creates a new TrialSession, hours = SURVEY_REWARD_HOURS
      - If device has an active session within 24h cap: extends trial_expires_at
      - If device already at 24h cap: returns (existing_session, 0.0)

    Each survey completion adds 2 hours (SURVEY_REWARD_HOURS), up to 24h max.
    """
    now = datetime.now(timezone.utc)
    hours_to_add = float(SURVEY_REWARD_HOURS)

    # Find any existing active trial session for this device
    existing = None
    if device_id:
        result = await session.execute(
            select(TrialSession).where(
                TrialSession.device_id == device_id,
                TrialSession.status.in_(["pending", "active", "expiring_soon"]),
            )
        )
        existing = result.scalar_one_or_none()

    if existing:
        # How many hours can we still add?
        remaining = MAX_TOTAL_TRIAL_HOURS - float(existing.total_hours_granted)
        if remaining <= 0:
            # Already at cap
            existing.status = "active"  # ensure status is correct even if capped
            await session.commit()
            return existing, 0.0

        hours_to_add = min(hours_to_add, remaining)
        new_total = float(existing.total_hours_granted) + hours_to_add
        new_expires = datetime.now(timezone.utc) + timedelta(hours=new_total)

        existing.total_hours_granted = new_total
        existing.trial_expires_at = new_expires
        # Extend the session instead of creating a new one
        await session.commit()
        await session.refresh(existing)
        return existing, hours_to_add

    # No existing session — create a new one
    new_session = TrialSession(
        platform_account_id=platform_account.id if platform_account else None,
        device_id=device_id,
        survey_id=survey_id,
        trial_started_at=now,
        trial_expires_at=now + timedelta(hours=hours_to_add),
        total_hours_granted=hours_to_add,
        status="pending",
    )
    session.add(new_session)
    await session.flush()
    await session.commit()
    await session.refresh(new_session)
    return new_session, hours_to_add


# ─── 3proxy port allocation ───────────────────────────────────────────────────


async def _allocate_threeproxy_port(session: AsyncSession) -> Optional[int]:
    """
    Allocate an unused 3proxy SOCKS5 port from THREEPROXY_PORT_RANGE.

    Scans StyxproxyCredential.dante_port for ports already in use and picks
    the first available port in the range. This is a simple first-fit approach;
    for high-concurrency scenarios a dedicated port allocation table would be
    better (see S2.3 n8n workflow notes).
    """
    settings = get_settings()
    port_start = settings.threeproxy_port_range_start
    port_end = settings.threeproxy_port_range_end

    # Get all currently allocated dante_ports in the range
    result = await session.execute(
        select(StyxproxyCredential.dante_port).where(
            StyxproxyCredential.dante_port >= port_start,
            StyxproxyCredential.dante_port <= port_end,
            StyxproxyCredential.dante_port.isnot(None),
        )
    )
    allocated = {row[0] for row in result.fetchall()}

    for port in range(port_start, port_end + 1):
        if port not in allocated:
            return port

    return None  # No ports available
