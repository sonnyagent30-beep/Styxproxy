#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────
# Styxproxy — Health Check
# Run: ./scripts/healthcheck.sh
# Exit 0 = all healthy, Exit 1 = something is down
# ─────────────────────────────────────────────────────────

set -euo pipefail

COMPOSE_FILE="${COMPOSE_FILE:-/opt/styxproxy/infrastructure/docker-compose.yml}"
FAILED=0

echo "=== Styxproxy Health Check — $(date) ==="
echo ""

# ── Docker Services ───────────────────────────────────────
echo "--- Docker Services ---"
docker compose -f "$COMPOSE_FILE" ps --format json 2>/dev/null \
  | jq -r '.Name + ": " + .State + " (" + .Status + ")"' || echo "[WARN] jq not available"
echo ""

# ── Postgres ──────────────────────────────────────────────
echo "--- Database ---"
CONTAINER=$(docker compose -f "$COMPOSE_FILE" ps -q postgres 2>/dev/null || true)
if [[ -n "$CONTAINER" ]]; then
  if docker exec "$CONTAINER" pg_isready -U styxproxy -d styxproxy &>/dev/null; then
    echo "[OK] PostgreSQL — accepting connections"
  else
    echo "[FAIL] PostgreSQL — not ready"
    FAILED=1
  fi
else
  echo "[FAIL] PostgreSQL container not running"
  FAILED=1
fi

# ── Redis ─────────────────────────────────────────────────
echo ""
echo "--- Cache ---"
CONTAINER=$(docker compose -f "$COMPOSE_FILE" ps -q redis 2>/dev/null || true)
if [[ -n "$CONTAINER" ]]; then
  if docker exec "$CONTAINER" redis-cli -a "${REDIS_PASSWORD:-}" ping 2>/dev/null | grep -q PONG; then
    echo "[OK] Redis — PONG"
  else
    echo "[FAIL] Redis — not responding"
    FAILED=1
  fi
else
  echo "[FAIL] Redis container not running"
  FAILED=1
fi

# ── API ───────────────────────────────────────────────────
echo ""
echo "--- API ---"
CONTAINER=$(docker compose -f "$COMPOSE_FILE" ps -q api 2>/dev/null || true)
if [[ -n "$CONTAINER" ]]; then
  HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 http://localhost:8000/health 2>/dev/null || echo "000")
  if [[ "$HTTP_CODE" == "200" ]]; then
    echo "[OK] API — HTTP $HTTP_CODE"
  else
    echo "[FAIL] API — HTTP $HTTP_CODE (expected 200)"
    FAILED=1
  fi
else
  echo "[FAIL] API container not running"
  FAILED=1
fi

# ── Nginx ─────────────────────────────────────────────────
echo ""
echo "--- Nginx ---"
CONTAINER=$(docker compose -f "$COMPOSE_FILE" ps -q nginx 2>/dev/null || true)
if [[ -n "$CONTAINER" ]]; then
  HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 http://localhost/health 2>/dev/null || echo "000")
  if [[ "$HTTP_CODE" == "200" ]]; then
    echo "[OK] Nginx — HTTP $HTTP_CODE"
  else
    echo "[FAIL] Nginx — HTTP $HTTP_CODE"
    FAILED=1
  fi
else
  echo "[FAIL] Nginx container not running"
  FAILED=1
fi

# ── n8n ───────────────────────────────────────────────────
echo ""
echo "--- n8n ---"
CONTAINER=$(docker compose -f "$COMPOSE_FILE" ps -q n8n 2>/dev/null || true)
if [[ -n "$CONTAINER" ]]; then
  HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 http://localhost:5678/healthz 2>/dev/null || echo "000")
  if [[ "$HTTP_CODE" == "200" ]]; then
    echo "[OK] n8n — HTTP $HTTP_CODE"
  else
    echo "[FAIL] n8n — HTTP $HTTP_CODE"
    FAILED=1
  fi
else
  echo "[FAIL] n8n container not running"
  FAILED=1
fi

echo ""
echo "=== Done — $(date) ==="
[[ $FAILED -eq 1 ]] && { echo "[FAIL] One or more checks failed"; exit 1; } || { echo "[OK] All checks passed"; exit 0; }
