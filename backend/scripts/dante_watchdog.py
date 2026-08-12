#!/usr/bin/env python3
"""Dante health watchdog — checks Dante SOCKS5 every 5 min, restarts if down."""

import subprocess
import time
from datetime import datetime

LOG = "/var/log/dante_watchdog.log"
STATE = "/var/run/dante_watchdog.state"
HOST = "127.0.0.1"
PORT = 1080
TIMEOUT = 5

def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"{ts} DANTE_WATCHDOG: {msg}"
    print(line)
    with open(LOG, "a") as f:
        f.write(line + "\n")

def check_dante() -> bool:
    """TCP connect to Dante SOCKS5 port. Returns True if reachable."""
    import socket
    try:
        s = socket.create_connection((HOST, PORT), timeout=TIMEOUT)
        s.close()
        return True
    except Exception:
        return False

def main():
    log("Watchdog check started")
    
    if check_dante():
        log("Dante SOCKS5 healthy on 127.0.0.1:1080")
        # Reset crash counter on healthy check
        with open(STATE, "w") as f:
            f.write("0\n")
        return

    log("Dante SOCKS5 UNREACHABLE on 127.0.0.1:1080 — restarting...")
    
    # Attempt restart
    r = subprocess.run(["systemctl", "restart", "danted"], capture_output=True, text=True)
    if r.returncode == 0:
        log("Restart command succeeded, waiting 8s for Dante to bind")
        time.sleep(8)
        if check_dante():
            log("Dante recovered after restart")
            return
        else:
            log("WARNING: Dante still down after restart")
    else:
        log(f"ERROR: systemctl restart failed: {r.stderr.strip()}")

if __name__ == "__main__":
    main()
