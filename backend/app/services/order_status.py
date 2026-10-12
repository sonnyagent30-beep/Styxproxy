"""Shared order status predicates.

Centralizes the definition of "live" order status so that renewal reminders,
payment status, and Charon tools all agree on which orders qualify.

The canonical live statuses are:
  - "fulfilled" — set by the Flutterwave webhook after payment
  - "active"    — set by admin re-fulfill and the newer catalog flow

Both mean the same thing: the customer has a usable proxy subscription.
"""

# Statuses that mean the order is live and the customer has a usable proxy.
LIVE_ORDER_STATUSES = frozenset({"active", "fulfilled"})


def is_live_order(status: str | None) -> bool:
    """Return True if the order status means the order is live and usable.

    Args:
        order_status: The order.status string to check.

    Returns:
        True if the status is "active" or "fulfilled", False otherwise.
    """
    return status in LIVE_ORDER_STATUSES
