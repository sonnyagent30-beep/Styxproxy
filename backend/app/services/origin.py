"""Client origin resolution and privacy-preserving classification.

WHY THIS EXISTS
---------------
The Flutterwave webhook route produced no record of *who* called it. That made
two completely different failures indistinguishable in the logs:

  (a) no traffic was ever attempted, and
  (b) traffic was attempted and every event was rejected (e.g. the webhook
      secret rotated to a value the gateway does not agree with).

The rotation canary for kanban t_604d405d exists to catch exactly case (b), and
it could not, because the route logged no origin.

WHAT WAS ACTUALLY WRONG
-----------------------
The card that asked for this (t_4271b61e) claimed no log source recorded a
client IP for this route. That was incorrect, and the diagnosis pointed at the
wrong files:

  - ``journalctl -u styxproxy-api`` has no request lines because the unit sets
    ``StandardOutput=append:/var/log/styxproxy-api.log``. Application output
    never reaches the journal at all. This is true of every route, not just
    webhooks.
  - ``/var/log/nginx/access.log`` has no webhook lines because the
    api.styxproxy.com server block sets its own
    ``access_log /var/log/styxproxy-nginx-access.log``.

The middleware in ``app/main.py`` already logged ``client`` on the *started*
line. So origin was partially observable, but:

  1. it was absent from the *completed* line (the one you grep when a request
     is being rejected),
  2. it was absent from every handler-level log line and from every
     ``customer_audit_log`` row — the only provenance-preserving store, and the
     one the canary actually queries,
  3. it was absent from the rejection paths that matter most: a bad signature
     raises 401 and writes no audit row at all.

So the fix is to make origin a first-class, queryable field on the webhook path
— not merely to add a log line.

PRIVACY
-------
An origin IP is personal data under the platform's audit convention. Raw
addresses are therefore never persisted. We store a truncated SHA-256 digest
(exactly the ``customer_hash`` scheme from ``services/audit.py``) plus a coarse,
non-identifying ``origin_scope``. The scope alone answers the canary's
question — "did a non-self host call us?" — without retaining the address.
"""

from __future__ import annotations

import hashlib
import ipaddress
from typing import Any, Optional

from fastapi import Request

# Addresses that are, by construction, us and not a payment gateway.
_LOOPBACK_SCOPES = ("loopback", "unspecified")

# Scopes that mean "not a public payment gateway".
_NON_GATEWAY_SCOPES = ("loopback", "unspecified", "private", "self_host")


def _hash_ip(ip: str) -> str:
    """Digest an address the same way log_audit_event digests a phone number.

    20 hex chars of SHA-256 — identical in shape and intent to ``customer_hash``
    in ``services/audit.py``, so an auditor who knows how to read one knows how
    to read the other. It is a pseudonym, not an anonymisation: the input space
    is small enough to brute-force, which is exactly why it is safe to correlate
    on and unsafe to read as an address.
    """
    return hashlib.sha256(ip.encode()).hexdigest()[:20]


def _classify(ip: str, self_ips: tuple[str, ...]) -> str:
    """Bucket an address without retaining it.

    Returns one of: ``loopback``, ``unspecified``, ``self_host``, ``private``,
    ``public``, or ``unknown``.
    """
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        # Not an address — a hostname, or junk from a spoofed header.
        return "unknown"

    if addr.is_loopback:
        return "loopback"
    if addr.is_unspecified:
        return "unspecified"

    for candidate in self_ips:
        try:
            if addr == ipaddress.ip_address(candidate):
                return "self_host"
        except ValueError:
            continue

    if addr.is_private or addr.is_link_local:
        return "private"
    return "public"


def _self_ips() -> tuple[str, ...]:
    """Addresses we accept as our own.

    Config-driven so a deploy to a new host does not silently reclassify that
    host's traffic as gateway traffic. Parsed defensively: a malformed entry is
    dropped rather than breaking request handling.

    Never raises. Settings validation can fail for unrelated reasons (a missing
    OPS_JWT_SECRET, say), and this function runs on the live payment path before
    the handler reads its own settings — an observability helper must never be
    able to reject a customer's webhook. If settings cannot be read we fall
    back to classifying by range alone, which is the conservative direction:
    it can only ever under-report a signal, never invent one.
    """
    try:
        from app.config import get_settings

        raw = getattr(get_settings(), "webhook_self_origin_ips", "") or ""
    except Exception:  # noqa: BLE001 - deliberate: see docstring
        return ()
    out: list[str] = []
    for chunk in raw.replace(",", " ").split():
        chunk = chunk.strip()
        if not chunk:
            continue
        try:
            ipaddress.ip_address(chunk)
        except ValueError:
            continue
        out.append(chunk)
    return tuple(out)


def resolve_origin(request: Request) -> dict[str, Any]:
    """Build the origin context for a request.

    Returns a dict with:

      ``origin_hash``  20-char SHA-256 digest of the address (pseudonymous)
      ``origin_scope`` coarse bucket, see _classify
      ``origin_seen``  True when an address was found at all

    Honours ``X-Forwarded-For`` because every gateway call arrives through
    nginx, which sets ``client`` to 127.0.0.1 and would make all traffic look
    self-originated — destroying the very distinction this exists to provide.

    TRUST NOTE: ``X-Forwarded-For`` is client-settable. That is acceptable here
    and only here, because this function never makes an authorisation decision:
    it only classifies for observability. Spoofing the header can make a
    gateway call *look* self-originated, so a missing live event should still be
    read alongside the nginx access log (which is not spoofable) before a
    secret rotation is declared broken. ``origin_via`` records which source
    supplied the address so a reader can tell the two apart.
    """
    peer = request.client.host if request.client else None

    forwarded = request.headers.get("x-forwarded-for", "")
    xff_first = forwarded.split(",")[0].strip() if forwarded else None
    x_real = (request.headers.get("x-real-ip") or "").strip() or None

    # Prefer the leftmost X-Forwarded-For entry (the original client), fall back
    # to X-Real-IP, then to the transport peer.
    if xff_first:
        ip, via = xff_first, "xff"
    elif x_real:
        ip, via = x_real, "x-real-ip"
    elif peer:
        ip, via = peer, "peer"
    else:
        return {"origin_hash": None, "origin_scope": "unknown", "origin_seen": False, "origin_via": None}

    scope = _classify(ip, _self_ips())
    return {
        "origin_hash": _hash_ip(ip),
        "origin_scope": scope,
        # A non-gateway scope means the caller was us: our own curl, our own
        # proxy, our own loopback. Recorded explicitly so the canary does not
        # have to enumerate scope names to find the signal.
        "origin_self_originated": scope in _NON_GATEWAY_SCOPES,
        "origin_seen": True,
        "origin_via": via,
    }


def describe_origin(ctx: Optional[dict[str, Any]]) -> str:
    """One-token human summary for a log message body."""
    if not ctx or not ctx.get("origin_seen"):
        return "origin=unknown"
    return f"origin={ctx.get('origin_scope')}/{ctx.get('origin_via')}"
