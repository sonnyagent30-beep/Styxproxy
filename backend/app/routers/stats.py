"""
Public platform stats — flag-gated homepage numbers.

Why this exists
---------------
The homepage stats strip shipped hardcoded claims: `$2M+ processed`,
`15,000+ customers`, `4.8/5 rating`, `99.9% uptime`. None were sourced. On a
trust-sensitive, FX-sensitive market an unsourced `4.8/5` is a liability, not
a sales aid — and a number nobody can back is the fastest way to lose a
customer who later checks.

Design (Dannion's directive, pre-launch)
----------------------------------------
Each stat is a FEATURE FLAG. While a flag is OFF the homepage shows
`placeholder` copy — a claim we can actually stand behind today. When the
underlying number becomes real and reviewable, flip the flag in the admin
dashboard and the computed value replaces the placeholder. No deploy, no code
change.

The real values are computed from the database on every request when the flag
is ON, so a flipped flag can never serve a stale figure.

Deliberately NOT included
-------------------------
`4.8/5 rating` has no review source anywhere in the system, so there is no
value to compute. Its flag exists so the slot is wired, but the computed value
is always None — it stays on placeholder copy until a real review source
exists. Do not "fix" this by inventing a rating.
"""

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import FeatureFlag, Order
from app.services.catalog import list_enabled_country_codes

router = APIRouter(prefix="/api", tags=["stats"])

# Paid-or-better. `pending` is an abandoned invoice, not a customer.
PAID_STATUSES = ("paid", "fulfilled")

# flag name -> (key, label, placeholder shown while the flag is OFF)
STAT_DEFINITIONS: list[tuple[str, str, str, str]] = [
    ("stat_revenue", "revenue", "processed", "Secure payments"),
    ("stat_customers", "customers", "customers", "Trusted by early users"),
    ("stat_rating", "rating", "rating", "Rated by real users"),
    ("stat_countries", "countries", "countries", "Global coverage"),
    ("stat_uptime", "uptime", "uptime", "Monitored 24/7"),
]


async def _flag_states(session: AsyncSession) -> dict[str, bool]:
    """Read every stat flag in one query. Missing flag == disabled."""
    names = [name for name, *_ in STAT_DEFINITIONS]
    rows = (
        await session.execute(select(FeatureFlag).where(FeatureFlag.name.in_(names)))
    ).scalars().all()
    found = {r.name: bool(r.enabled) for r in rows}
    return {name: found.get(name, False) for name in names}


async def _real_values(session: AsyncSession) -> dict[str, str | None]:
    """Compute the real value for each stat.

    Returns None where there is no honest number to show, which keeps the slot
    on placeholder copy even if its flag is on.
    """
    values: dict[str, str | None] = {}

    # Customers: distinct emails that actually paid for something.
    customers = (
        await session.execute(
            select(func.count(func.distinct(Order.customer_email))).where(
                Order.status.in_(PAID_STATUSES)
            )
        )
    ).scalar() or 0
    values["customers"] = f"{customers:,}+" if customers else None

    # Countries: enabled-for-sale, the same source the catalog sells from —
    # not the 197-row reference table, which would overstate what is buyable.
    codes = await list_enabled_country_codes(session)
    values["countries"] = f"{len(codes)}" if codes else None

    # Revenue: no value yet. Deliberately omitted rather than approximated —
    # FX-converting a naira total into a `$2M+` headline is exactly the
    # unbacked claim this endpoint exists to remove.
    values["revenue"] = None

    # Rating: no review source exists. Stays None by design. See module docstring.
    values["rating"] = None

    # Uptime: no SLA. Real uptime lives in Grafana and has no public API yet;
    # an SLA figure we do not offer must never render.
    values["uptime"] = None

    return values


@router.get("/platform-stats")
async def get_platform_stats(session: AsyncSession = Depends(get_session)):
    """Flag-gated homepage stats.

    Each entry carries both what to show now (`placeholder`) and the real
    figure (`value`), so the frontend needs no business logic: render
    `value` when `enabled` and `value` is non-null, else `placeholder`.
    """
    flags = await _flag_states(session)
    values = await _real_values(session)

    stats = []
    for flag_name, key, label, placeholder in STAT_DEFINITIONS:
        real = values.get(key)
        enabled = flags[flag_name] and real is not None
        stats.append(
            {
                "key": key,
                "flag": flag_name,
                "label": label,
                # A flag can be ON with no computable value (revenue, rating,
                # uptime). `enabled` reflects whether a REAL number will render,
                # so the frontend never has to guess.
                "enabled": enabled,
                "value": real if enabled else None,
                "placeholder": placeholder,
            }
        )

    return {"stats": stats}
