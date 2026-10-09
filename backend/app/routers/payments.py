"""Payments router — Payment Flow Rewrite (Sprint 025).

Key changes:
- Idempotency key support (Idempotency-Key header)
- Backend-owned tx_ref generation (frontend never sends payment_reference)
- Structured logging at every step
- Order expiry (30 min TTL)
- No silent except:pass — every failure is logged
"""
import logging
import re
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import FeatureFlag, Order
from app.schemas import PaymentInitiateResponse
from app.routers.schemas import PaymentInitiateRequest, PaymentInitiateBasketRequest, PaymentInitiateBasketResponse
from app.services.capture import (
    GATEWAY_STATUS_PENDING,
    UNIT_MAJOR,
    UNIT_MINOR,
    record_capture,
)
from app.services.customer import get_or_create_customer, placeholder_email_from_device
from app.services.flutterwave import create_flutterwave_invoice
from app.services.paystack import create_paystack_transaction

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/payments", tags=["payments"])

# Order TTL — pending orders expire after 30 minutes
ORDER_TTL_MINUTES = 30


@router.post("/initiate", response_model=PaymentInitiateResponse, status_code=status.HTTP_201_CREATED)
async def initiate_payment(
    request: PaymentInitiateRequest,
    session: AsyncSession = Depends(get_session),
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
):
    """Initiate a payment — create order and return gateway checkout URL.

    Idempotency: if Idempotency-Key header is provided and an order with
    that key already exists, return the original order instead of creating
    a duplicate. On failure, attempt to delete any partial order with that
    key so the client can retry safely.
    """
    log_ctx = {"idempotency_key": idempotency_key, "plan_code": request.plan_code, "gateway": request.gateway}

    # ── Kill switch ───────────────────────────────────────────────────────
    kill_switch = (
        await session.execute(select(FeatureFlag).where(FeatureFlag.name == "checkout_disabled"))
    ).scalar_one_or_none()
    if kill_switch and kill_switch.enabled:
        logger.warning("checkout disabled by feature flag", extra=log_ctx)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Checkout is temporarily disabled.",
        )

    # ── Resolve plan + price ─────────────────────────────────────────────
    # NOTE: this MUST run before the idempotency check below. The 409 guard
    # compares the request payload against the stored order, and the replay
    # path returns the ORIGINAL invoice amount — not today's price. Reading
    # `total_amount` before it was assigned (the historical bug at this file's
    # line 75) made every retry carrying an Idempotency-Key raise
    # UnboundLocalError -> 500, and the friendly 409 underneath it was
    # unreachable dead code.
    from app.routers.orders import resolve_plan, generate_order_id

    plan = await resolve_plan(session, request.plan_code)
    if not plan:
        logger.warning("invalid plan code", extra=log_ctx)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid plan code")

    # Sprint 13 pricing model — identical to /api/orders/create so the two
    # endpoints can never disagree about what a plan costs:
    #   residential/mobile: price_per_gb x quantity_gb
    #   datacenter/ISP:     price_ngn    x quantity (per-IP)
    plan_type = (plan.plan_type or "").lower()
    if plan_type in ("residential", "mobile"):
        if plan.price_per_gb is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Plan has no price_per_gb configured. Admin must set it in /admin/plans.",
            )
        # Backward compatibility with a client that predates `quantity_gb`.
        # That client sent the GB count under `quantity` while putting a UUID
        # in `effective_quantity` (an 11-positional-arg shift), so there is no
        # trustworthy GB in the request. Hard-failing it with
        # "Minimum purchase is N GB (you sent 1)" took checkout to 100% for
        # every stale tab and cached chunk, which is a worse outcome than
        # billing the plan's bundled GB. Charge the bundled quantity and log
        # it loudly so the stale client is identifiable instead of silent.
        gb = request.quantity_gb
        if gb is None:
            gb = plan.quantity or plan.min_gb or 1
            logger.warning(
                "initiate received no quantity_gb — charging bundled GB (stale client)",
                extra={**log_ctx, "assumed_gb": gb, "plan_code": request.plan_code},
            )
        if gb < plan.min_gb:
            # Never silently bill above what was asked for: clamp UP to the
            # plan minimum so the customer is charged at least the minimum,
            # which is what the checkout UI quoted them.
            logger.warning(
                "quantity_gb below plan minimum — clamping to minimum",
                extra={**log_ctx, "requested_gb": gb, "min_gb": plan.min_gb},
            )
            gb = plan.min_gb
        if gb > plan.max_gb:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Maximum purchase is {plan.max_gb} GB (you sent {gb})",
            )
        total_amount = float(plan.price_per_gb) * gb
    else:
        if plan.price_ngn is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Plan has no price_ngn configured",
            )
        price = float(plan.price_ngn)

        # Parse quantity from plan code suffix (e.g., "MOBILE-GH-5IP" -> 5)
        quantity = request.quantity
        if '-' in request.plan_code and request.plan_code.endswith('IP'):
            parts = request.plan_code.rsplit('-', 2)
            if len(parts) >= 3:
                match = re.match(r'^(\d+)IP$', parts[2])
                if match:
                    suffix_qty = int(match.group(1))
                    if suffix_qty > 0:
                        quantity = suffix_qty

        total_amount = price * quantity

    # ── Idempotency check ────────────────────────────────────────────────
    # Replay semantics: an idempotent retry must return the ORIGINAL order and
    # the ORIGINAL amount. Comparing `existing.amount_paid_ngn` against a
    # freshly computed `total_amount` is wrong — if an admin edits a price
    # between the two attempts, a genuine retry would be rejected as a
    # "different payload". Compare request identity instead (plan, quantity,
    # email, gateway), which is what the key actually promises.
    if idempotency_key:
        existing = (
            await session.execute(
                select(Order).where(Order.idempotency_key == idempotency_key)
            )
        ).scalars().first()
        if existing:
            # A dead order must not lock the key forever. If the original
            # attempt expired, was cancelled or failed, release the key and
            # fall through to create a fresh order — otherwise the cart is
            # permanently unpayable on that device.
            still_live = (
                existing.status in ("pending", "processing", "active")
                and existing.expires_at is not None
                and existing.expires_at > datetime.now(timezone.utc)
            )
            if not still_live:
                logger.info(
                    "idempotency key held by a dead order — releasing and creating a new one",
                    extra={**log_ctx, "order_id": existing.order_id, "status": existing.status},
                )
                existing = None

        if existing:
            same_payload = (
                existing.plan_code == request.plan_code
                and (existing.customer_email or "") == (request.customer_email or "")
                and int(existing.quantity or 1) == int(request.quantity)
                # provider is NULL on every order written before this fix, so
                # only enforce the gateway match when we actually recorded one.
                and (not existing.provider or existing.provider == request.gateway)
            )
            if not same_payload:
                logger.warning(
                    "idempotency key reused with different payload — rejecting",
                    extra={**log_ctx, "order_id": existing.order_id},
                )
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Idempotency-Key was already used with a different payload",
                )

            logger.info(
                "idempotent replay — returning existing order",
                extra={**log_ctx, "order_id": existing.order_id},
            )
            return PaymentInitiateResponse(
                payment_id=str(uuid.uuid4()),
                order_id=existing.order_id,
                checkout_url="",
                amount_ngn=float(existing.amount_paid_ngn or 0),
                expires_at=existing.expires_at or datetime.now(timezone.utc) + timedelta(minutes=ORDER_TTL_MINUTES),
                tx_ref=existing.tx_ref or "",
            )

    # ── Get or create customer ───────────────────────────────────────────
    # An anonymous customer (no email, no phone) is a first-class case here:
    # the checkout UI says "No signup required" and labels email optional, so
    # the device_id supplies a stable identity instead of rejecting them.
    #
    # The UI's promise must not depend on the client remembering to send
    # device_id. When neither identity field is present, fall back to a
    # per-attempt synthetic identity derived from the idempotency key (or a
    # fresh UUID). Previously this returned 400 "We couldn't start that
    # payment." on a page that explicitly told the buyer no signup was
    # required — i.e. every no-signup buyer who blocked or stripped
    # localStorage was refused at the last step.
    effective_device_id = request.device_id or f"anon-{idempotency_key or uuid.uuid4().hex}"
    customer = await get_or_create_customer(
        session,
        phone=None,
        email=request.customer_email,
        platform_account=None,
        device_id=effective_device_id,
    )
    if not customer:
        # Last resort: a per-attempt guest identity. Same rule as above —
        # never refuse a buyer at the final step for lacking an identifier
        # the product never asked them for.
        customer = await get_or_create_customer(
            session,
            phone=None,
            email=None,
            platform_account=None,
            device_id=f"anon-{uuid.uuid4().hex}",
        )
    if not customer:
        logger.error("could not establish any customer identity", extra=log_ctx)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            # Customer-safe wording. "No customer profile found" is our schema
            # leaking through to the checkout page; the real reason goes to logs.
            detail="We couldn't start that payment. Please try again.",
        )

    # ── Backend-owned tx_ref ─────────────────────────────────────────────
    tx_ref = f"TXF-{uuid.uuid4().hex[:12].upper()}"

    # ── Gateway-facing contact ───────────────────────────────────────────
    # Flutterwave v3 hard-requires customer.email; Paystack requires it too.
    # An anonymous order has none, so synthesize a stable device-derived
    # placeholder from the SAME identity used for the customer row above —
    # using request.device_id here meant a request that arrived without one
    # cleared the customer check and then died at the gateway on an empty
    # email (502). The receipt email is only sent when the customer supplied a
    # real address, so this can never be delivered to anyone.
    gateway_email = request.customer_email or placeholder_email_from_device(effective_device_id)

    # ── Generate order_id ────────────────────────────────────────────────
    order_id = generate_order_id()

    callback_url = f"https://styxproxy.com/thank-you?order_id={order_id}"

    # ── Create gateway transaction ───────────────────────────────────────
    try:
        if request.gateway == "paystack":
            # tx_ref MUST be passed: the webhook joins on orders.payment_reference
            # using whatever reference Paystack echoes back, so the reference we
            # send here is the reference the order row has to carry.
            result = await create_paystack_transaction(
                amount_ngn=total_amount,
                customer_email=gateway_email,
                customer_phone=customer.phone or "",
                callback_url=callback_url,
                description=f"Payment for {request.plan_code}",
                tx_ref=tx_ref,
            )
        else:
            result = await create_flutterwave_invoice(
                amount=total_amount,
                customer_email=gateway_email,
                customer_phone=customer.phone,
                currency="NGN",
                tx_ref=tx_ref,
                callback_url=callback_url,
                description=f"Payment for {request.plan_code}",
            )
    except Exception as e:
        logger.error(
            "gateway transaction creation failed",
            extra={**log_ctx, "error": str(e), "error_type": type(e).__name__},
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Payment gateway error: {str(e)}",
        )

    # ── Reconcile against the gateway's own answer ──────────────────────
    # Persist the reference the gateway CONFIRMED, not merely the one we
    # asked for. A gateway that echoes back a different reference has charged
    # that other value, and storing our request instead leaves the charged
    # reference recorded nowhere — which is precisely what makes the payment
    # unreconcilable after the fact. Falling back to the requested reference
    # keeps callers that don't return one working unchanged.
    gateway_reference = result.get("tx_ref") or tx_ref
    provider_order_id = result.get("provider_order_id")
    if gateway_reference != tx_ref:
        logger.error(
            "gateway returned a different reference than requested — storing the gateway's",
            extra={
                **log_ctx,
                "requested_reference": tx_ref,
                "gateway_reference": gateway_reference,
                "order_id": order_id,
            },
        )
    tx_ref = gateway_reference

    # ── Create order ─────────────────────────────────────────────────────
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=ORDER_TTL_MINUTES)
    order = Order(
        order_id=order_id,
        platform_account_id=None,
        customer_phone=customer.phone,
        customer_email=request.customer_email or "",
        plan_type=plan.plan_type.lower(),
        plan_code=request.plan_code,
        country=plan.country,
        # quantity stays the IP count: the fulfillment worker reads
        # order.quantity to decide how many credentials to mint, and a 5 GB
        # residential plan is ONE gateway carrying 5 GB, not five gateways.
        quantity=request.quantity,
        # The GB the customer actually bought lives here, so nothing that
        # drives credential creation can confuse GB with IP count.
        data_total_gb=(request.quantity_gb if plan_type in ("residential", "mobile") else None),
        amount_paid_ngn=total_amount,
        payment_reference=tx_ref,
        tx_ref=tx_ref,
        # The gateway's own transaction id. The webhook falls back to this when
        # the reference does not join, which is the only way an order created
        # before the reference was persisted can still be recovered.
        provider_order_id=provider_order_id,
        # Record which gateway this invoice was raised on. Every order written
        # before this had provider = NULL, which is why gateway reconciliation
        # could never be answered from our side.
        provider=request.gateway,
        status="pending",
        idempotency_key=idempotency_key,
        expires_at=expires_at,
    )
    # Record what the gateway says it will charge, as PENDING capture evidence,
    # straight from the gateway's own initialize response. This is not a
    # capture — no money has moved yet, so gateway_status stays `pending` and
    # `captured_at` stays NULL; the webhook promotes it to `success`. Writing it
    # here means the amount we expect to be charged is on the row before the
    # customer reaches checkout, so a later divergence is visible.
    #
    # Never fall back to `total_amount` (our invoice arithmetic) if the gateway
    # omitted the figure: amount_paid_ngn already holds that, and letting it
    # stand in as a gateway figure is precisely the confusion this column
    # exists to remove.
    record_capture(
        order,
        provider=request.gateway,
        gateway_status=GATEWAY_STATUS_PENDING,
        gateway_amount=result.get("gateway_amount"),
        amount_unit=(UNIT_MINOR if request.gateway == "paystack" else UNIT_MAJOR),
        gateway_reference=result.get("tx_ref") or tx_ref,
        gateway_currency=result.get("gateway_currency"),
        gateway_transaction_id=result.get("provider_order_id"),
    )
    session.add(order)

    try:
        await session.commit()
    except Exception as e:
        await session.rollback()
        
        # Check if this is an IntegrityError from the unique idempotency index
        from sqlalchemy.exc import IntegrityError
        if isinstance(e, IntegrityError) and idempotency_key:
            # Concurrent request won the race — fetch and return the existing order
            try:
                existing = (
                    await session.execute(
                        select(Order).where(Order.idempotency_key == idempotency_key)
                    )
                ).scalars().first()
                if existing:
                    logger.info(
                        "concurrent request won race — returning existing order",
                        extra={**log_ctx, "order_id": existing.order_id},
                    )
                    return PaymentInitiateResponse(
                        payment_id=str(uuid.uuid4()),
                        order_id=existing.order_id,
                        checkout_url="",
                        amount_ngn=float(existing.amount_paid_ngn or 0),
                        expires_at=existing.expires_at or datetime.now(timezone.utc) + timedelta(minutes=ORDER_TTL_MINUTES),
                        tx_ref=existing.tx_ref or "",
                    )
            except Exception:
                pass  # Fall through to error handling
        
        # Idempotency failure path: attempt to delete partial order
        if idempotency_key:
            try:
                await session.execute(
                    Order.__table__.delete().where(Order.idempotency_key == idempotency_key)
                )
                await session.commit()
                logger.info(
                    "idempotency key released after failure",
                    extra={**log_ctx, "error": str(e)},
                )
            except Exception as delete_err:
                # Key stays locked — customer can generate a new key
                logger.error(
                    "idempotency key release failed — key stays locked",
                    extra={**log_ctx, "delete_error": str(delete_err)},
                )
        logger.error(
            "order creation failed",
            extra={**log_ctx, "error": str(e), "error_type": type(e).__name__},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create order. Please try again.",
        )

    logger.info(
        "payment initiated",
        extra={
            **log_ctx,
            "order_id": order_id,
            "tx_ref": tx_ref,
            "amount": total_amount,
            "customer_phone": customer.phone,
        },
    )

    return PaymentInitiateResponse(
        payment_id=str(uuid.uuid4()),
        order_id=order_id,
        checkout_url=result.get("checkout_url", ""),
        amount_ngn=total_amount,
        expires_at=expires_at,
        tx_ref=tx_ref,
    )


# ============== Basket (multi-item) payment ─────────────────────────────────

@router.post("/initiate-basket", response_model=PaymentInitiateBasketResponse, status_code=status.HTTP_201_CREATED)
async def initiate_basket_payment(
    request: PaymentInitiateBasketRequest,
    session: AsyncSession = Depends(get_session),
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
):
    """Initiate payment for multiple items in ONE gateway charge.

    Unlike the single-item /initiate endpoint, this creates ONE order with
    the SUM of all item prices and stores every item in basket_items JSONB.
    The customer pays once for the whole cart. Fulfillment reads basket_items
    to create the right number of credentials.
    """
    log_ctx = {"idempotency_key": idempotency_key, "item_count": len(request.items), "gateway": request.gateway}

    # ── Kill switch ───────────────────────────────────────────────────────
    kill_switch = (
        await session.execute(select(FeatureFlag).where(FeatureFlag.name == "checkout_disabled"))
    ).scalar_one_or_none()
    if kill_switch and kill_switch.enabled:
        logger.warning("checkout disabled by feature flag", extra=log_ctx)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Checkout is temporarily disabled.",
        )

    # ── Resolve each item's plan and price ────────────────────────────────
    from app.routers.orders import resolve_plan, generate_order_id

    basket_items = []
    total_amount = 0.0

    for item in request.items:
        plan = await resolve_plan(session, item.plan_code)
        if not plan:
            logger.warning("invalid plan code in basket", extra={**log_ctx, "plan_code": item.plan_code})
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid plan code: {item.plan_code}")

        plan_type = (plan.plan_type or "").lower()
        if plan_type in ("residential", "mobile"):
            if plan.price_per_gb is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Plan {item.plan_code} has no price_per_gb configured.",
                )
            gb = item.quantity_gb
            if gb is None:
                gb = plan.quantity or plan.min_gb or 1
                logger.warning(
                    "basket item missing quantity_gb — charging bundled GB",
                    extra={**log_ctx, "plan_code": item.plan_code, "assumed_gb": gb},
                )
            if gb < plan.min_gb:
                gb = plan.min_gb
            if gb > plan.max_gb:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Maximum purchase is {plan.max_gb} GB for {item.plan_code} (you sent {gb})",
                )
            item_price = float(plan.price_per_gb) * gb
            item_quantity = 1  # one gateway carrying N GB
        else:
            if plan.price_ngn is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Plan {item.plan_code} has no price_ngn configured.",
                )
            price = float(plan.price_ngn)
            quantity = item.quantity
            # Parse quantity from plan code suffix (e.g., "MOBILE-GH-5IP" -> 5)
            if '-' in item.plan_code and item.plan_code.endswith('IP'):
                parts = item.plan_code.rsplit('-', 2)
                if len(parts) >= 3:
                    match = re.match(r'^(\d+)IP$', parts[2])
                    if match:
                        suffix_qty = int(match.group(1))
                        if suffix_qty > 0:
                            quantity = suffix_qty
            item_price = price * quantity
            item_quantity = quantity

        total_amount += item_price
        basket_items.append({
            "plan_code": item.plan_code,
            "quantity": item_quantity,
            "quantity_gb": item.quantity_gb if plan_type in ("residential", "mobile") else None,
            "price_ngn": item_price,
            "name": item.name or item.plan_code,
            "country_code": item.country_code or plan.country,
            "plan_type": plan.plan_type,
            "city_id": item.city_id,
            "city_name": item.city_name,
        })

    # ── Idempotency check ─────────────────────────────────────────────────
    if idempotency_key:
        existing = (
            await session.execute(
                select(Order).where(Order.idempotency_key == idempotency_key)
            )
        ).scalars().first()
        if existing:
            still_live = (
                existing.status in ("pending", "processing", "active")
                and existing.expires_at is not None
                and existing.expires_at > datetime.now(timezone.utc)
            )
            if not still_live:
                logger.info(
                    "idempotency key held by a dead order — releasing and creating a new one",
                    extra={**log_ctx, "order_id": existing.order_id, "status": existing.status},
                )
                existing = None

        if existing:
            logger.info(
                "idempotent replay — returning existing basket order",
                extra={**log_ctx, "order_id": existing.order_id},
            )
            return PaymentInitiateBasketResponse(
                payment_id=str(uuid.uuid4()),
                order_id=existing.order_id,
                checkout_url="",
                amount_ngn=float(existing.amount_paid_ngn or 0),
                expires_at=existing.expires_at or datetime.now(timezone.utc) + timedelta(minutes=ORDER_TTL_MINUTES),
                item_count=len(existing.basket_items or []),
                tx_ref=existing.tx_ref or "",
            )

    # ── Get or create customer ───────────────────────────────────────────
    effective_device_id = request.device_id or f"anon-{idempotency_key or uuid.uuid4().hex}"
    customer = await get_or_create_customer(
        session,
        phone=None,
        email=request.customer_email,
        platform_account=None,
        device_id=effective_device_id,
    )
    if not customer:
        customer = await get_or_create_customer(
            session,
            phone=None,
            email=None,
            platform_account=None,
            device_id=f"anon-{uuid.uuid4().hex}",
        )
    if not customer:
        logger.error("could not establish any customer identity", extra=log_ctx)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="We couldn't start that payment. Please try again.",
        )

    # ── Backend-owned tx_ref ─────────────────────────────────────────────
    tx_ref = f"TXF-{uuid.uuid4().hex[:12].upper()}"

    gateway_email = request.customer_email or placeholder_email_from_device(effective_device_id)

    # ── Generate order_id ────────────────────────────────────────────────
    order_id = generate_order_id()
    callback_url = f"https://styxproxy.com/thank-you?order_id={order_id}"

    # ── Create gateway transaction for the SUM ──────────────────────────
    try:
        if request.gateway == "paystack":
            result = await create_paystack_transaction(
                amount_ngn=total_amount,
                customer_email=gateway_email,
                customer_phone=customer.phone or "",
                callback_url=callback_url,
                description=f"Payment for {len(request.items)} item(s)",
                tx_ref=tx_ref,
            )
        else:
            result = await create_flutterwave_invoice(
                amount=total_amount,
                customer_email=gateway_email,
                customer_phone=customer.phone,
                currency="NGN",
                tx_ref=tx_ref,
                callback_url=callback_url,
                description=f"Payment for {len(request.items)} item(s)",
            )
    except Exception as e:
        logger.error(
            "gateway transaction creation failed",
            extra={**log_ctx, "error": str(e), "error_type": type(e).__name__},
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Payment gateway error: {str(e)}",
        )

    # ── Reconcile gateway reference ──────────────────────────────────────
    gateway_reference = result.get("tx_ref") or tx_ref
    provider_order_id = result.get("provider_order_id")
    if gateway_reference != tx_ref:
        logger.error(
            "gateway returned a different reference than requested — storing the gateway's",
            extra={**log_ctx, "requested_reference": tx_ref, "gateway_reference": gateway_reference, "order_id": order_id},
        )
    tx_ref = gateway_reference

    # ── Create order with basket_items ───────────────────────────────────
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=ORDER_TTL_MINUTES)
    order = Order(
        order_id=order_id,
        platform_account_id=None,
        customer_phone=customer.phone,
        customer_email=request.customer_email or "",
        plan_type=basket_items[0]["plan_type"].lower() if basket_items else None,
        plan_code=", ".join(item["plan_code"] for item in basket_items),
        country=basket_items[0]["country_code"] if basket_items else None,
        quantity=sum(item["quantity"] for item in basket_items),
        data_total_gb=sum(item["quantity_gb"] or 0 for item in basket_items if item["quantity_gb"]),
        amount_paid_ngn=total_amount,
        payment_reference=tx_ref,
        tx_ref=tx_ref,
        provider_order_id=provider_order_id,
        provider=request.gateway,
        status="pending",
        idempotency_key=idempotency_key,
        expires_at=expires_at,
        basket_items=basket_items,
    )
    record_capture(
        order,
        provider=request.gateway,
        gateway_status=GATEWAY_STATUS_PENDING,
        gateway_amount=result.get("gateway_amount"),
        amount_unit=(UNIT_MINOR if request.gateway == "paystack" else UNIT_MAJOR),
        gateway_reference=result.get("tx_ref") or tx_ref,
        gateway_currency=result.get("gateway_currency"),
        gateway_transaction_id=result.get("provider_order_id"),
    )
    session.add(order)

    try:
        await session.commit()
    except Exception as e:
        await session.rollback()
        from sqlalchemy.exc import IntegrityError
        if isinstance(e, IntegrityError) and idempotency_key:
            try:
                existing = (
                    await session.execute(
                        select(Order).where(Order.idempotency_key == idempotency_key)
                    )
                ).scalars().first()
                if existing:
                    logger.info(
                        "concurrent request won race — returning existing order",
                        extra={**log_ctx, "order_id": existing.order_id},
                    )
                    return PaymentInitiateBasketResponse(
                        payment_id=str(uuid.uuid4()),
                        order_id=existing.order_id,
                        checkout_url="",
                        amount_ngn=float(existing.amount_paid_ngn or 0),
                        expires_at=existing.expires_at or datetime.now(timezone.utc) + timedelta(minutes=ORDER_TTL_MINUTES),
                        item_count=len(existing.basket_items or []),
                        tx_ref=existing.tx_ref or "",
                    )
            except Exception:
                pass

        if idempotency_key:
            try:
                await session.execute(
                    Order.__table__.delete().where(Order.idempotency_key == idempotency_key)
                )
                await session.commit()
                logger.info("idempotency key released after failure", extra={**log_ctx, "error": str(e)})
            except Exception as delete_err:
                logger.error(
                    "idempotency key release failed — key stays locked",
                    extra={**log_ctx, "delete_error": str(delete_err)},
                )
        logger.error(
            "basket order creation failed",
            extra={**log_ctx, "error": str(e), "error_type": type(e).__name__},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create order. Please try again.",
        )

    logger.info(
        "basket payment initiated",
        extra={
            **log_ctx,
            "order_id": order_id,
            "tx_ref": tx_ref,
            "amount": total_amount,
            "item_count": len(basket_items),
        },
    )

    return PaymentInitiateBasketResponse(
        payment_id=str(uuid.uuid4()),
        order_id=order_id,
        checkout_url=result.get("checkout_url", ""),
        amount_ngn=total_amount,
        expires_at=expires_at,
        item_count=len(basket_items),
        tx_ref=tx_ref,
    )


# ============== Gateways ==============

@router.get("/gateways")
async def list_gateways(session: AsyncSession = Depends(get_session)):
    """List available payment gateways with their status."""
    flags = {}
    for name in ("flutterwave_enabled", "paystack_enabled", "stripe_enabled", "paynow_enabled"):
        flag = (
            await session.execute(select(FeatureFlag).where(FeatureFlag.name == name))
        ).scalar_one_or_none()
        flags[name] = bool(flag and flag.enabled)

    return {
        "gateways": {
            "flutterwave": {
                "available": flags["flutterwave_enabled"],
                "label": "Flutterwave",
                "icon": "💳",
                "description": "Card, Bank Transfer, USSD, QR",
            },
            "paystack": {
                "available": flags["paystack_enabled"],
                "label": "Paystack",
                "icon": "🏦",
                "description": "Card, Bank Transfer, USSD",
            },
            "stripe": {
                "available": flags["stripe_enabled"],
                "label": "Stripe",
                "icon": "💰",
                "description": "International cards",
            },
            "paynow": {
                "available": flags["paynow_enabled"],
                "label": "Paynow",
                "icon": "₿",
                "description": "Bitcoin, USDT, Crypto",
            },
        }
    }
