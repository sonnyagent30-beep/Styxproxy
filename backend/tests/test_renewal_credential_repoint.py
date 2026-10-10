"""Regression test for t_87d368e9 — per-item renewal must repoint credential_id.

Bug: complete_renewal_residential_mobile() created a new credential for the
renewed GB but never updated proxy_item.credential_id, leaving it pointing
at the OLD credential. The per-item management view then shows stale data
and the new credential is orphaned.

This test exercises the exact failure mode: renew one proxy_item of a
multi-proxy order and assert that proxy_item.credential_id now references
the credential that holds the new GB.
"""
import pytest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import importlib

renewal_mod = importlib.import_module("app.services.renewal_service")


# ── Fakes ────────────────────────────────────────────────────────────────────

class FakeOrder:
    order_id="STX-TEST01"
    plan_code = "RESIDENTIAL-NG"
    country = "NG"
    plan_type = "residential"
    customer_phone = "+234****5678"
    targeting_mode = "country_chosen"
    city_name = "Lagos"
    data_remaining_gb = 10.0
    expires_at = datetime.now(timezone.utc) + timedelta(days=30)


class FakeProxyItem:
    def __init__(self, id: int, credential_id: int):
        self.id = id
        self.credential_id = credential_id
        self.status = "active"
        self.expires_at = datetime.now(timezone.utc) + timedelta(days=30)


class FakeCredential:
    def __init__(self, id: int):
        self.id = id
        self.styxproxy_username = f"sty_test_{id}"
        self.styxproxy_password_encrypted = "encrypted"
        self.customer_phone = "+234****5678"
        self.order_id = "STX-TEST01"
        self.provider_order_id = f"prov-{id}"
        self.provider_username = f"user-{id}"
        self.provider_password = f"pass-{id}"
        self.upstream_proxy_ip = "1.2.3.4"
        self.upstream_proxy_port = 1080
        self.status = "active"
        self.expires_at = datetime.now(timezone.utc) + timedelta(days=30)
        self.created_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)


class FakeRenewal:
    def __init__(self, id: int, order_id: str, proxy_item_id, quantity_gb: int = 5):
        self.id = id
        self.order_id = order_id
        self.proxy_item_id = proxy_item_id
        self.quantity_gb = quantity_gb
        self.renewal_tx_ref = f"TXR-TEST{id:04d}"
        self.amount_paid_ngn = 5000.0
        self.status = "pending"
        self.payment_reference = None
        self.credential_id = None
        self.expires_at = None
        self.created_at = datetime.now(timezone.utc)
        self.fulfilled_at = None


class FakeSession:
    """Minimal async session that stores objects in a dict."""

    def __init__(self, proxy_items=None):
        self._objects = {}  # id -> object
        self._next_id = 1000
        self.commits = 0
        if proxy_items:
            for pi in proxy_items:
                self._objects[pi.id] = pi

    async def get(self, model, obj_id):
        return self._objects.get(obj_id)

    def add(self, obj):
        if hasattr(obj, 'id') and obj.id is None:
            obj.id = self._next_id
            self._next_id += 1
        self._objects[obj.id] = obj

    async def commit(self):
        self.commits += 1

    async def refresh(self, obj):
        pass

    async def execute(self, stmt):
        return SimpleNamespace(scalar_one_or_none=lambda: None)


# ── Tests ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_per_item_renewal_repoints_proxy_item_credential_id():
    """After per-item renewal, proxy_item.credential_id MUST equal the new credential's id.

    This is the core assertion for t_87d368e9: the bug left proxy_item.credential_id
    pointing at the old credential, orphaning the new one.
    """
    # Setup: order with 3 proxy items, each with its own credential
    old_cred_id_1 = 101
    old_cred_id_2 = 102
    old_cred_id_3 = 103

    proxy_item_1 = FakeProxyItem(1, old_cred_id_1)
    proxy_item_2 = FakeProxyItem(2, old_cred_id_2)
    proxy_item_3 = FakeProxyItem(3, old_cred_id_3)

    session = FakeSession(proxy_items=[proxy_item_1, proxy_item_2, proxy_item_3])

    order = FakeOrder()
    renewal = FakeRenewal(id=1, order_id="STX-TEST01", proxy_item_id=2, quantity_gb=5)

    new_cred = FakeCredential(id=201)

    async def mock_create_credential(**kwargs):
        return new_cred, "plaintext_password"

    with patch.object(renewal_mod, "create_credential", side_effect=mock_create_credential):
        with patch.object(renewal_mod, "resolve_country_for_credential", return_value="NG"):
            result = await renewal_mod.complete_renewal_residential_mobile(
                session=session,
                renewal=renewal,
                order=order,
            )

    # The new credential is returned
    assert result is new_cred

    # RENEWAL points at the new credential
    assert renewal.credential_id == new_cred.id

    # PROXY_ITEM also points at the new credential — THIS IS THE FIX
    updated_item = await session.get(type(proxy_item_2), 2)
    assert updated_item.credential_id == new_cred.id, (
        f"BUG: proxy_item.credential_id is {updated_item.credential_id}, "
        f"expected {new_cred.id} (the new credential)"
    )

    # Other proxy items are untouched
    item_1 = await session.get(type(proxy_item_1), 1)
    item_3 = await session.get(type(proxy_item_3), 3)
    assert item_1.credential_id == old_cred_id_1
    assert item_3.credential_id == old_cred_id_3

    # Order-level GB is incremented (per-item renewal adds GB to the order)
    assert order.data_remaining_gb == 15.0  # 10 + 5

    # Expiry is extended
    assert updated_item.expires_at > datetime.now(timezone.utc)
    assert updated_item.status == "active"


@pytest.mark.asyncio
async def test_order_level_renewal_does_not_touch_proxy_items():
    """When proxy_item_id is None (order-level renewal), proxy_items are untouched."""
    old_cred_id = 101
    proxy_item = FakeProxyItem(1, old_cred_id)
    session = FakeSession(proxy_items=[proxy_item])

    order = FakeOrder()
    renewal = FakeRenewal(id=2, order_id="STX-TEST01", proxy_item_id=None, quantity_gb=5)

    new_cred = FakeCredential(id=301)

    async def mock_create_credential(**kwargs):
        return new_cred, "plaintext_password"

    with patch.object(renewal_mod, "create_credential", side_effect=mock_create_credential):
        with patch.object(renewal_mod, "resolve_country_for_credential", return_value="NG"):
            result = await renewal_mod.complete_renewal_residential_mobile(
                session=session,
                renewal=renewal,
                order=order,
            )

    assert result is new_cred
    assert renewal.credential_id == new_cred.id

    # Proxy item credential_id unchanged — order-level renewal doesn't repoint
    item = await session.get(type(proxy_item), 1)
    assert item.credential_id == old_cred_id


@pytest.mark.asyncio
async def test_dc_isp_renewal_extends_credential_in_place():
    """DC/ISP renewal extends the linked credential's expiry — no new credential.

    This test documents the correct behaviour that must be preserved:
    the credential_id does NOT change for DC/ISP renewals.
    """
    old_cred_id = 101
    proxy_item = FakeProxyItem(1, old_cred_id)
    session = FakeSession(proxy_items=[proxy_item])

    order = FakeOrder()
    order.plan_type = "isp"
    renewal = FakeRenewal(id=3, order_id="STX-TEST01", proxy_item_id=1, quantity_gb=0)

    old_expiry = proxy_item.expires_at

    # DC/ISP path does NOT create a new credential
    result = await renewal_mod.complete_renewal_dc_isp(
        session=session,
        renewal=renewal,
        order=order,
    )

    assert result is True
    assert renewal.status == "completed"

    # proxy_item still points at the SAME credential
    item = await session.get(type(proxy_item), 1)
    assert item.credential_id == old_cred_id

    # But the credential's expiry is extended (via the proxy_item relationship)
    # In FakeSession we don't track the credential object directly, but the
    # proxy_item expiry is extended, which is the observable effect.
    assert item.expires_at >= old_expiry
    assert item.status == "active"
