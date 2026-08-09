#!/usr/bin/env python3
"""Dante SOCKS5 bandwidth tracker — parses journalctl logs, stores daily stats to JSON.

Dante logs connection byte counts at end of each log line:
  "info: pass(1): tcp/connect ... (BYTES)"

Run daily via cron. Persists stats to /opt/styxproxy/backend/data/bandwidth_stats.json.

Owner: Operations / Sonny
"""

import subprocess, re, json
from datetime import datetime, timezone, timedelta
from pathlib import Path

DB_PATH = "/opt/styxproxy/backend/data/bandwidth_stats.json"
LOGFILE = "/var/log/dante_bandwidth.log"

# Example: "info: pass(1): tcp/connect -: 104.21.82.192.443 162.35.184.69.443 -> ... (2708)"
BYTES_RE = re.compile(r"\((\d+)\)\s*$")


def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"{ts} BANDWIDTH: {msg}"
    print(line)
    Path(LOGFILE).parent.mkdir(parents=True, exist_ok=True)
    with open(LOGFILE, "a") as f:
        f.write(line + "\n")


def _fmt(n: int) -> str:
    if n >= 1_073_741_824:
        return f"{n/1_073_741_824:.2f} GB"
    elif n >= 1_048_576:
        return f"{n/1_048_576:.2f} MB"
    elif n >= 1024:
        return f"{n/1024:.1f} KB"
    return f"{n} B"


def fetch_logs(n_lines: int = 500) -> list[str]:
    """Fetch N recent Dante log lines from journal."""
    r = subprocess.run(
        ["journalctl", "-u", "danted", "-n", str(n_lines),
         "--no-pager", "-o", "cat"],
        capture_output=True, text=True, timeout=30
    )
    if r.returncode not in (0, 1):
        log(f"journalctl failed: {r.stderr.strip()[:100]}")
        return []
    return r.stdout.splitlines()


def parse(lines: list[str]) -> tuple[int, int]:
    """Parse total bytes + connections from Dante log lines."""
    total_bytes = 0
    connections = 0
    for line in lines:
        if "pass(1):" in line:
            connections += 1
            m = BYTES_RE.search(line)
            if m:
                total_bytes += int(m.group(1))
    return total_bytes, connections


def load_stats() -> dict:
    if Path(DB_PATH).exists():
        try:
            with open(DB_PATH) as f:
                return json.load(f)
        except Exception:
            pass
    return {"daily": {}, "total": {"bytes": 0, "connections": 0}}


def save_stats(stats: dict):
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    with open(DB_PATH, "w") as f:
        json.dump(stats, f, indent=2)


def main():
    log("Bandwidth tracker started")
    lines = fetch_logs(n_lines=500)
    bytes_total, connections = parse(lines)
    log(f"Recent: {_fmt(bytes_total)} across {connections} connections (last 500 log lines)")

    stats = load_stats()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    if today not in stats["daily"]:
        stats["daily"][today] = {"bytes": 0, "connections": 0}

    stats["daily"][today]["bytes"] += bytes_total
    stats["daily"][today]["connections"] += connections
    stats["total"]["bytes"] += bytes_total
    stats["total"]["connections"] += connections
    stats["total"]["updated_at"] = datetime.now(timezone.utc).isoformat()

    # Keep 90 days
    cutoff = (datetime.now(timezone.utc) - timedelta(days=90)).strftime("%Y-%m-%d")
    stats["daily"] = {k: v for k, v in stats["daily"].items() if k >= cutoff}

    save_stats(stats)

    daily = stats["daily"][today]
    log(f"Saved — today ({today}): {_fmt(daily['bytes'])} / {daily['connections']} connections | "
        f"Total tracked: {_fmt(stats['total']['bytes'])}")

    # Print last 7 days summary
    days = sorted(stats["daily"].keys(), reverse=True)[:7]
    print("\nLast 7 days:")
    for d in days:
        s = stats["daily"][d]
        print(f"  {d}: {_fmt(s['bytes']):>12s}  {s['connections']:>6} conns")


if __name__ == "__main__":
    main()
