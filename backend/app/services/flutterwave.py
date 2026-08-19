"""Flutterwave service for payment processing."""

import hashlib
import hmac
import logging
import uuid
from typing import Any, Optional

import httpx

from app.config import get_settings
from app.services.credential import create_credential
from app.services.n8n import trigger_credentials_delivered_webhook

logger = logging.getLogger(__name__)
settings = get_settings()

_sentry_dsn = str(getattr(settings, "sentry_dsn", "") or "").strip()


def _capture_money_event(
    level: str,
    title: str,
    extra: dict[str, Any],
    fingerprint: Optional[str] = None,
) -> None:
    """Capture a money-path event in Sentry if configured.

    Safe to call even when Sentry DSN is not set — no-op in that case.
    """
    if not _sentry_dsn:
        return
    try:
        import sentry_sdk

        with sentry_sdk.push_scope() as scope:
            scope.set_level(level)  # type: ignore[arg-type]
            scope.set_tag("domain", "money")
            for k, v in extra.items():
                scope.set_extra(k, v)
            if fingerprint:
                scope.fingerprint = [fingerprint]
            sentry_sdk.capture_message(title)  # type: ignore[arg-type]
    except Exception:
        pass  # Never let observability crash the payment path


def verify_flutterwave_signature(payload: bytes, signature: str, secret: str) -> bool:
    computed = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(computed, signature)


async def is_webhook_processed(db_session, event_id: str) -> bool:
    from sqlalchemy import select

    from app.models import ProcessedWebhook

    return (
        await db_session.execute(select(ProcessedWebhook).where(ProcessedWebhook.webhook_id == event_id))
    ).scalar_one_or_none() is not None


async def mark_webhook_processed(
    db_session, webhook_id: str, provider: str, event_type: str, extra_data: Optional[dict] = None
) -> None:
    from app.models import ProcessedWebhook

    processed = ProcessedWebhook(webhook_id=webhook_id, provider=provider, event_type=event_type, extra_data=extra_data)
    db_session.add(processed)
    await db_session.commit()


# ─── Refund helper ──────────────────────────────────────────────────────────────


async def _flutterwave_refund(tx_ref: str, amount: float, secret_key: str) -> dict:
    """
    Call Flutterwave POST /v3/transactions/{id}/refund.
    Looks up the transaction by tx_ref first, then issues a full refund.
    Returns the Flutterwave API response dict.
    Raises on network/HTTP errors.
    """
    async with httpx.AsyncClient(timeout=httpx.Timeout(10.0, connect=5.0)) as client:
        # 1. Look up the Flutterwave transaction ID by tx_ref
        lookup_resp = await client.get(
            f"https://api.flutterwave.com/v3/transactions/verify/by-ref/{tx_ref}",
            headers={"Authorization": f"Bearer {secret_key}"},
        )
        lookup_resp.raise_for_status()
        lookup_data = lookup_resp.json().get("data", {})
        flw_tx_id = lookup_data.get("id")

        if not flw_tx_id:
            raise ValueError(f"No Flutterwave transaction ID found for tx_ref={tx_ref}")

        # 2. Issue full refund
        refund_resp = await client.post(
            f"https://api.flutterwave.com/v3/transactions/{flw_tx_id}/refund",
            headers={"Authorization": f"Bearer {secret_key}", "Content-Type": "application/json"},
            json={"amount": str(amount), "currency": "NGN"},
        )
        refund_resp.raise_for_status()
        return refund_resp.json()


# ─── Invoice creation ──────────────────────────────────────────────────────────


async def create_flutterwave_invoice(
    amount: float,
    customer_email: str,
    customer_phone: str,
    currency: str = "NGN",
    callback_url: Optional[str] = None,
    description: Optional[str] = None,
    device_id: Optional[str] = None,
) -> dict:
    tx_ref = f"TXF-{uuid.uuid4().hex[:8].upper()}"
    payload_meta: dict[str, str] = {}
    if device_id:
        payload_meta["device_id"] = device_id

    async with httpx.AsyncClient(timeout=httpx.Timeout(3.0, connect=10.0)) as client:
        try:
            json_body: dict[str, Any] = {
                "tx_ref": tx_ref,
                "amount": amount,
                "currency": currency,
                "customer": {"email": customer_email, "phone_number": customer_phone},
                "customizations": {
                    "title": "Styxproxy Proxy Service",
                    "description": description or "Proxy service payment",
                },
                "callback_url": callback_url,
            }
            if payload_meta:
                json_body["meta"] = payload_meta

            response = await client.post(
                "https://api.flutterwave.com/v3/payments",
                json=json_body,
                headers={
                    "Authorization": f"Bearer {settings.flutterwave_secret_key}",
                    "Content-Type": "application/json",
                },
            )
            response.raise_for_status()
            data = response.json()
            return {
                "payment_id": data.get("data", {}).get("id"),
                "checkout_url": data.get("data", {}).get("link"),
                "tx_ref": tx_ref,
            }
        except httpx.HTTPError as e:
            from app.services.audit import log_audit_event

            await log_audit_event(
                db_session=None, event_type="payment_initiate_failed", details={"error": str(e), "tx_ref": tx_ref}
            )
            raise


async def verify_flutterwave_payment(tx_ref: str) -> dict:
    async with httpx.AsyncClient(timeout=httpx.Timeout(3.0, connect=10.0)) as client:
        try:
            response = await client.get(
                f"https://api.flutterwave.com/v3/transactions/verify/by-ref/{tx_ref}",
                headers={"Authorization": f"Bearer {settings.flutterwave_secret_key}"},
            )
            response.raise_for_status()
            return response.json().get("data", {})
        except httpx.HTTPError:
            raise


# ─── Webhook processing ────────────────────────────────────────────────────────


async def process_payment_webhook(db_session, event_data: dict) -> Optional[dict]:
    event_type = event_data.get("event")
    data = event_data.get("data", {})

    if event_type == "charge.completed":
        tx_ref = data.get("tx_ref")
        status = data.get("status")

        if status == "successful":
            # ── Step 1: Look up order BEFORE any state mutation ──────────────────
            from sqlalchemy import select

            from app.models import Order

            order = (
                await db_session.execute(select(Order).where(Order.payment_reference == tx_ref))
            ).scalar_one_or_none()

            if not order:
                # Payment confirmed by Flutterwave but no matching order.
                # Acknowledge without marking as processed so we can investigate.
                logger.warning("flutterwave webhook: no order found for tx_ref=%s", tx_ref)
                return {"status": "no_order_found"}

            # Already processed — safe to acknowledge without re-marking.
            if order.status in ("paid", "fulfilled", "active"):
                return {"status": "already_processed", "order_id": order.order_id}

            # ── Step 2: Mark order paid ────────────────────────────────────────
            order.status = "paid"
            order.amount_paid_ngn = data.get("amount")
            await db_session.commit()

            # ── Step 3: Attempt fulfillment ────────────────────────────────────
            fulfillment_error = None
            try:
                credential, plaintext_password = await create_credential(
                    db_session=db_session,
                    order_id=order.order_id,
                    customer_phone=order.customer_phone or "",
                    plan_code=order.plan_code or "unknown",
                    country=order.country or "NG",
                    proxy_type="isp",
                    quantity=1,
                    duration_days=30,
                    protocol="socks5",
                    pool_type="paid",
                )
                order.styxproxy_credential_id = credential.id
                order.status = "fulfilled"
                await db_session.commit()

                if credential.expires_at:
                    await trigger_credentials_delivered_webhook(
                        order_id=order.order_id,
                        tx_ref=tx_ref,
                        phone=order.customer_phone or "",
                        channel=order.channel or "web",
                        bun_username=credential.styxproxy_username,
                        bun_password=plaintext_password,
                        proxy_ip=credential.upstream_proxy_ip or "",
                        proxy_port=credential.upstream_proxy_port or 1080,
                        expires_at=credential.expires_at,
                    )

            except RuntimeError as e:
                # Provider exhausted all 5 retries — customer paid but can't be fulfilled.
                # Flag for auto-refund immediately.
                fulfillment_error = str(e)
                order.status = "failed_unfulfilled"
                await db_session.commit()

            except Exception as e:
                # Non-provider errors — don't auto-refund, flag for manual review.
                fulfillment_error = str(e)
                order.status = "failed_manual_review"
                await db_session.commit()
                _capture_money_event(
                    level="error",
                    title=f"Payment succeeded but fulfillment FAILED — manual review needed: {tx_ref}",
                    extra={
                        "tx_ref": tx_ref,
                        "order_id": order.order_id,
                        "amount": data.get("amount", 0),
                        "error": fulfillment_error,
                    },
                    fingerprint=f"manual-review-{tx_ref}",
                )

            # ── Step 4: Apply referral credit if referee just made their first payment ─
            # Only trigger for customers who were referred (referred_by != null)
            # and only on their first confirmed payment (each referee earns at most once).
            try:
                from app.models import Customer
                from app.services.referral import apply_referral_credit

                customer_stmt = select(Customer).where(Customer.phone == order.customer_phone)
                customer = (await db_session.execute(customer_stmt)).scalar_one_or_none()
                if customer and customer.referred_by is not None:
                    await apply_referral_credit(
                        db_session,
                        referee_customer_id=customer.id,
                        referee_payment_tx_ref=tx_ref,
                    )
            except Exception as referral_error:
                # Referral credit failures must NOT roll back the payment confirmation.
                # Log and continue — the credit can be applied manually or via a reconciliation job.
                import sentry_sdk
                try:
                    sentry_sdk.capture_exception(referral_error)
                except Exception:
                    pass
                logger.warning(
                    "Failed to apply referral credit for order %s (customer %s): %s",
                    order.order_id,
                    order.customer_phone,
                    referral_error,
                )

            # ── Step 5: Audit log (after all state mutations) ─────────────────
            from app.services.audit import log_audit_event

            if fulfillment_error:
                await log_audit_event(
                    db_session,
                    event_type="credential_creation_failed",
                    phone=order.customer_phone,
                    order_id=order.order_id,
                    details={"error": fulfillment_error, "tx_ref": tx_ref},
                )
                logger.error("Failed to create credential for order %s: %s", order.order_id, fulfillment_error)

                # Auto-refund if provider was the failure
                if fulfillment_error.startswith("Provider proxy unavailable"):
                    await log_audit_event(
                        db_session,
                        event_type="auto_refund_triggered",
                        phone=order.customer_phone,
                        order_id=order.order_id,
                        details={"reason": fulfillment_error, "tx_ref": tx_ref},
                    )
                    try:
                        await _flutterwave_refund(tx_ref, data.get("amount", 0), settings.flutterwave_secret_key)
                        order.status = "refunded"
                        order.refund_requested = True
                        order.refund_reason = f"Auto-refund: provider unavailable — {fulfillment_error}"
                        await db_session.commit()
                        _capture_money_event(
                            level="warning",
                            title=f"Auto-refund triggered for {tx_ref}",
                            extra={
                                "tx_ref": tx_ref,
                                "order_id": order.order_id,
                                "amount": data.get("amount", 0),
                                "reason": fulfillment_error,
                            },
                            fingerprint=f"auto-refund-{tx_ref}",
                        )
                    except Exception as refund_error:
                        logger.warning(
                            "Flutterwave refund call failed for tx_ref=%s: %s", tx_ref, refund_error
                        )
                        _capture_money_event(
                            level="error",
                            title=f"MONEY BUG: auto-refund FAILED for {tx_ref}",
                            extra={
                                "tx_ref": tx_ref,
                                "order_id": order.order_id,
                                "amount": data.get("amount", 0),
                                "refund_error": str(refund_error),
                                "fulfillment_error": fulfillment_error,
                            },
                            fingerprint=f"refund-failed-{tx_ref}",
                        )
            else:
                await log_audit_event(
                    db_session,
                    event_type="credential_creation_success",
                    phone=order.customer_phone,
                    order_id=order.order_id,
                    details={"tx_ref": tx_ref},
                )

            # ── Step 5b: Record trial-to-paid conversion (S2.4) ───────────────
            # If this payment completes an active trial session for the same
            # platform_account (or device), mark it as converted.
            try:
                from datetime import datetime, timezone as tz
                from sqlalchemy import select

                from app.models import TrialSession

                # Look up the most recent active trial session for this platform_account.
                # device_id lookup via platform_account is the prerequisite noted in SPEC.
                if order.platform_account_id is not None:
                    trial_stmt = (
                        select(TrialSession)
                        .where(TrialSession.platform_account_id == order.platform_account_id)
                        .where(TrialSession.status == "active")
                        .order_by(TrialSession.trial_started_at.desc())
                        .limit(1)
                    )
                    trial_session = (await db_session.execute(trial_stmt)).scalar_one_or_none()

                    if trial_session is not None:
                        # Only mark converted if the trial was still valid at payment time.
                        now = datetime.now(tz.utc)
                        if trial_session.trial_expires_at >= now:
                            trial_session.converted_at = now
                            trial_session.status = "converted"
                            await log_audit_event(
                                db_session,
                                event_type="trial_converted",
                                phone=order.customer_phone,
                                order_id=order.order_id,
                                details={
                                    "trial_session_id": trial_session.id,
                                    "trial_started_at": str(trial_session.trial_started_at),
                                    "trial_expires_at": str(trial_session.trial_expires_at),
                                    "tx_ref": tx_ref,
                                },
                            )
            except Exception as trial_conv_error:
                # Conversion tracking failures must NOT roll back or block payment processing.
                import sentry_sdk

                try:
                    sentry_sdk.capture_exception(trial_conv_error)
                except Exception:
                    pass
                logger.warning(
                    "Trial conversion tracking failed for order %s (tx_ref=%s): %s",
                    order.order_id,
                    tx_ref,
                    trial_conv_error,
                )

            # ── Step 6: Mark processed ONLY after all mutations succeeded ──────
            await mark_webhook_processed(
                db_session,
                webhook_id=tx_ref,
                provider="flutterwave",
                event_type=event_type,
                extra_data=data,
            )

            return {"status": "processed", "order_id": order.order_id}

    # ── payment.expired ──────────────────────────────────────────────────────────
    # Flutterwave sends this when a payment link expires before the customer paid.
    # If the order was already paid/fulfilled, ignore — the customer already got value.
    # If the order is still pending/created, mark it expired so it can't be used.
    if event_type == "payment.expired":
        tx_ref = data.get("tx_ref")
        if not tx_ref:
            return {"status": "ignored"}

        from sqlalchemy import select

        from app.models import Order

        order = (
            await db_session.execute(select(Order).where(Order.payment_reference == tx_ref))
        ).scalar_one_or_none()

        if not order:
            logger.warning("payment.expired: no order found for tx_ref=%s", tx_ref)
            return {"status": "no_order_found"}

        if order.status in ("paid", "fulfilled", "active"):
            # Customer already paid and got served — ignore the expired notification
            return {"status": "already_processed"}

        # Order is still pending — mark it expired
        order.status = "payment_expired"
        await db_session.commit()

        from app.services.audit import log_audit_event
        await log_audit_event(
            db_session,
            event_type="payment_expired",
            phone=order.customer_phone,
            order_id=order.order_id,
            details={"tx_ref": tx_ref},
        )

        await mark_webhook_processed(
            db_session,
            webhook_id=tx_ref,
            provider="flutterwave",
            event_type=event_type,
            extra_data=data,
        )
        return {"status": "processed", "order_id": order.order_id}

    # ── charge.failed ────────────────────────────────────────────────────────────
    # Customer's card was declined or payment failed after initiating a payment.
    # Mark the order as failed so the payment link can't be reused.
    if event_type == "charge.failed":
        tx_ref = data.get("tx_ref")
        status = data.get("status")
        failure_message = data.get("processor_response", {}).get("remark", "") if isinstance(data.get("processor_response"), dict) else str(data.get("processor_response", ""))

        if not tx_ref:
            return {"status": "ignored"}

        from sqlalchemy import select

        from app.models import Order

        order = (
            await db_session.execute(select(Order).where(Order.payment_reference == tx_ref))
        ).scalar_one_or_none()

        if not order:
            logger.warning("charge.failed: no order found for tx_ref=%s", tx_ref)
            return {"status": "no_order_found"}

        if order.status in ("paid", "fulfilled", "active", "failed"):
            return {"status": "already_processed"}

        order.status = "failed"
        order.refund_reason = f"Payment failed: {failure_message}"
        await db_session.commit()

        from app.services.audit import log_audit_event
        await log_audit_event(
            db_session,
            event_type="payment_charge_failed",
            phone=order.customer_phone,
            order_id=order.order_id,
            details={"tx_ref": tx_ref, "status": status, "failure": failure_message},
        )

        await mark_webhook_processed(
            db_session,
            webhook_id=tx_ref,
            provider="flutterwave",
            event_type=event_type,
            extra_data=data,
        )
        return {"status": "processed", "order_id": order.order_id}

    return {"status": "ignored"}
