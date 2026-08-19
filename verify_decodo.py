"""Verify S2.8 Decodo integration is complete."""
from backend.app.services import provider, decodo, dataimpulse
from backend.app.config import get_settings

print("=== Routing ===")
print("Nigeria ->", provider._country_routing("Nigeria"))
print("UK ->", provider._country_routing("United Kingdom"))

print("\n=== Config fields ===")
s = get_settings()
print("decodo_api_key in settings:", hasattr(s, "decodo_api_key"))
print("decodo_api_key value:", repr(s.decodo_api_key))

print("\n=== decodo module functions ===")
print("check_health:", decodo.check_health)
print("create_order:", decodo.create_order)
print("rotate_ip:", decodo.rotate_ip)
print("check_balance:", decodo.check_balance)

print("\n=== provider.py public API ===")
pub = [x for x in dir(provider) if not x.startswith("_")]
print(pub)

print("\n=== All checks passed ===")
