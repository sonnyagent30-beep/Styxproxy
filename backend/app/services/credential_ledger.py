"""Send ledger for credential delivery.

`credential_notifications` had zero rows and zero references in `app/` for its
entire life, so nothing recorded whether a customer's proxy credentials were
ever sent. `send_order_active_email()` returns an `EmailResult` carrying
`success` / `status` / `error`; when the fulfillment worker discarded it, a
Resend rejection was indistinguishable from a delivery.

This module is the writer. It records one row per delivery attempt — success,
provider rejection, raised exception, and the "no address could be resolved"
case — so the outcome is queryable from the database without reading logs.

Deliberate properties
---------------------
* **Never raises into the caller.** A ledger write failing must not turn a
  fulfilled order into a failed one, or mask the real delivery outcome. Every
  exception is caught, logged at ERROR, and reported in the return value so
  the caller can log it too.
* **Commits on the caller's session, immediately.** The worker marks the order
  `fulfilled` and commits *before* it attempts delivery, so by the time this
  runs there is no enclosing transaction to lose. Committing here means a send
  that actually happened stays recorded even if the worker's later generic
  `except` handler rolls the order back to `failed_manual_review` — the
  delivery did occur, and the ledger must not un-record it.
* **Does not invent a target.** `target` is NOT NULL, and for the
  no-address case there is no address. Rather than write a fake one that a
  later query would read as a real delivery, those rows get an explicit
  sentinel that is obviously not an address.

Asserting on this table, not on `orders.emails_sent`
----------------------------------------------------
`orders.emails_sent` is written in exactly one place — `services/renewal.py`,
inside `check_and_send_renewal_reminder` — for renewal reminders.
`send_order_active_email` never touches it, so `emails_sent = 0` means "no
renewal reminder fired", which is expected for most orders. It is not a
credential-delivery signal and an assertion against it passes or fails for an
unrelated reason.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import CredentialNotification

logger = logging.getLogger(__name__)

# Sentinel written to the NOT NULL `target` column when no address could be
# resolved. Deliberately not a valid address: a query that counts real
# deliveries by `target LIKE '%@%'` will never match it, so these rows cannot
# be mistaken for a send.
NO_ADDRESS_TARGET = "(no deliverable address)"

# RFC 2606 reserved domains. An anonymous checkout sends the gateway a
# synthesized `guest-anond<hash>@example.com`; the provider accepts it and
# reports the message as sent, but it can never reach a human. The worker
# already rejects these before sending — the ledger enforces it again so that
# no future caller can record an unroutable address as a delivery.
PLACEHOLDER_EMAIL_DOMAINS = ("example.com", "example.org", "example.net")

# Ledger status values. See CredentialNotification.status for the contract.
STATUS_SENT = "sent"
STATUS_FAILED = "failed"
STATUS_NO_ADDRESS = "no_address"
STATUS_SKIPPED = "skipped"

# notification_type / channel for a credential email.
# `channel` is varchar(20) in the live schema, so this must stay short.
NOTIFICATION_TYPE_EMAIL = "email"
CHANNEL_EMAIL = "email"


def is_placeholder_target(target: str | None) -> bool:
    """True if the address cannot reach a human.

    Covers the empty case and RFC 2606 reserved domains. The worker's
    ``_is_placeholder_email`` makes the same judgement before attempting a
    send; repeating it here means the ledger cannot be tricked into recording
    an unroutable address as a delivery by a future caller.
    """
    if not target:
        return True
    domain = target.rsplit("@", 1)[-1].strip().lower()
    return domain in PLACEHOLDER_EMAIL_DOMAINS


async def record_credential_send(
    db_session: AsyncSession,
    *,
    credential_id: int,
    order_id: Optional[str],
    target: Optional[str],
    status: str,
    error: Optional[str] = None,
    message_id: Optional[str] = None,
) -> Optional[int]:
    """Write one credential-delivery outcome to the ledger.

    Returns the new row's id, or None if the write failed. Never raises.

    Args:
        credential_id: FK target. Required — the table's NOT NULL FK.
        order_id: the order this send belongs to. Recorded directly because it
            is not reliably derivable: `styxproxy_credentials.order_id` is
            nullable, and a multi-quantity order mints several credentials.
        target: the address used. Pass None (or an empty/placeholder address)
            together with ``status=STATUS_NO_ADDRESS`` and the sentinel is
            written instead.
        status: one of the ``STATUS_*`` constants.
        error: ``EmailResult.error`` or the exception text, verbatim.
        message_id: provider message id, for correlation with provider logs.
    """
    if not credential_id:
        # Without this the INSERT violates the NOT NULL FK and the only
        # record of the outcome would be this log line.
        logger.error(
            "cannot write credential send ledger: no credential_id "
            "(order_id=%s status=%s)",
            order_id,
            status,
        )
        return None

    row_target = (target or "").strip()
    if is_placeholder_target(row_target):
        # A send recorded against an address nobody can receive is the
        # silent-credential-loss failure mode. Downgrade it so the row tells
        # the truth, whatever the caller believed.
        if status not in (STATUS_NO_ADDRESS, STATUS_SKIPPED):
            logger.error(
                "ledger downgrading %s to %s — target is not deliverable: %r "
                "(order_id=%s)",
                status,
                STATUS_NO_ADDRESS,
                target,
                order_id,
            )
        row_target = NO_ADDRESS_TARGET
        if status != STATUS_SKIPPED:
            status = STATUS_NO_ADDRESS

    row = CredentialNotification(
        credential_id=credential_id,
        notification_type=NOTIFICATION_TYPE_EMAIL,
        channel=CHANNEL_EMAIL,
        target=row_target[:255],
        enabled=True,
        order_id=(order_id or None),
        status=status,
        error=(error or None),
        message_id=(message_id or None),
    )

    try:
        db_session.add(row)
        await db_session.commit()
        await db_session.refresh(row)
        logger.info(
            "credential send ledgered",
            extra={
                "ledger_id": row.id,
                "credential_id": credential_id,
                "order_id": order_id,
                "status": status,
                "target": row_target,
                "message_id": message_id,
            },
        )
        return row.id
    except Exception as exc:
        # Roll back so this failure does not poison the caller's transaction.
        try:
            await db_session.rollback()
        except Exception:
            pass
        logger.error(
            "FAILED to write credential send ledger — the delivery outcome is "
            "now invisible in the DB: order_id=%s credential_id=%s status=%s "
            "error=%s",
            order_id,
            credential_id,
            status,
            exc,
            exc_info=True,
        )
        return None


async def record_email_result(
    db_session: AsyncSession,
    result,
    *,
    credential_id: int,
    order_id: Optional[str],
    target: Optional[str],
) -> Optional[int]:
    """Record an `EmailResult` as a ledger row.

    Thin adapter so callers pass the object `send_order_active_email` already
    returns rather than re-deriving success from its fields.
    """
    status = STATUS_SENT if getattr(result, "success", False) else STATUS_FAILED
    return await record_credential_send(
        db_session,
        credential_id=credential_id,
        order_id=order_id,
        target=target,
        status=status,
        error=getattr(result, "error", None),
        message_id=getattr(result, "message_id", None),
    )


async def ensure_ledger_columns(db_session: AsyncSession) -> bool:
    """Idempotently add the 026 outcome columns. Returns True if the table is ready.

    The fulfillment worker is an RQ process, not the FastAPI app, so it never
    runs ``app.main``'s lifespan startup patches. Without this the worker could
    start before any migration run and every ledger write would then fail on an
    undefined column — the writes are caught and logged, which means the ledger
    would be *silently* empty rather than loudly broken.

    Uses ADD COLUMN IF NOT EXISTS, so it is a no-op once 026 has been applied.
    Never raises: returns False and logs on failure so a permissions problem
    does not stop the worker from starting.
    """
    from sqlalchemy import text

    columns = (
        ("order_id", "VARCHAR(20)"),
        ("status", "VARCHAR(20)"),
        ("error", "TEXT"),
        ("message_id", "VARCHAR(255)"),
    )
    try:
        for col_name, col_type in columns:
            await db_session.execute(
                text(
                    "ALTER TABLE credential_notifications "
                    f"ADD COLUMN IF NOT EXISTS {col_name} {col_type}"
                )
            )
        await db_session.commit()
        logger.info("credential_notifications ledger columns verified")
        return True
    except Exception as exc:
        try:
            await db_session.rollback()
        except Exception:
            pass
        logger.error(
            "credential_notifications ledger columns could not be verified — "
            "credential send outcomes will not be recorded in the DB: %s",
            exc,
            exc_info=True,
        )
        return False


def ledger_query_for_order(order_id: str):
    """Select every ledger row for an order, newest first.

    Provided so callers and tests query the ledger the same way.
    """
    from sqlalchemy import select

    return (
        select(CredentialNotification)
        .where(CredentialNotification.order_id == order_id)
        .order_by(CredentialNotification.created_at.desc())
    )


__all__ = [
    "CHANNEL_EMAIL",
    "NO_ADDRESS_TARGET",
    "NOTIFICATION_TYPE_EMAIL",
    "PLACEHOLDER_EMAIL_DOMAINS",
    "STATUS_FAILED",
    "STATUS_NO_ADDRESS",
    "STATUS_SENT",
    "STATUS_SKIPPED",
    "ensure_ledger_columns",
    "is_placeholder_target",
    "ledger_query_for_order",
    "record_credential_send",
    "record_email_result",
]
