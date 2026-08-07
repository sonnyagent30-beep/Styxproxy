"""Routers package."""
from app.routers.admin import router as admin
from app.routers.admin_proxies import router as admin_proxies
from app.routers.admin_support import router as admin_support
from app.routers.auth import router as auth
from app.routers.blog import router as blog
from app.routers.catalog import router as catalog
from app.routers.charon import router as charon
from app.routers.contact import router as contact
from app.routers.costs import router as costs
from app.routers.credentials import router as credentials
from app.routers.health import router as health
from app.routers.inbound import router as inbound
from app.routers.maintenance import router as maintenance
from app.routers.unsubscribe import router as unsubscribe
from app.routers.orders import router as orders
from app.routers.payment_status import router as payment_status
from app.routers.payments import router as payments
from app.routers.permissions import router as permissions
from app.routers.platform import router as platform
from app.routers.products import router as products
from app.routers.proxies import router as proxies
from app.routers.rls import router as rls
from app.routers.session import router as session
from app.routers.superadmin import router as superadmin
from app.routers.trials import router as trials
from app.routers.webhooks import router as webhooks

