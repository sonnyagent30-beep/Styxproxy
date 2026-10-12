import sys
sys.path.insert(0, "/root/Styxproxy/backend")
from app.routers import auth as auth_module
print("has get_session:", hasattr(auth_module, "get_session"))
print("get_session from module:", auth_module.get_session)
