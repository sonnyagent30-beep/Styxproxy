import sys
sys.path.insert(0, "/root/Styxproxy/backend")
try:
    from app.main import app
    print("app.main loaded OK")
    print("app:", app)
except Exception as e:
    print("ERROR:", e)
