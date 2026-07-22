#!/bin/bash
# litellm/run.sh - production startup script for the LiteLLM proxy sidecar.
#
# P1-1 (Jul 22 2026): docker compose's spawn-from-compose path leaves
# LiteLLM's uvicorn worker unable to bind port 4000 (upstream behavior).
# Verified that running it directly with this script's exact flags
# DOES work — both `/health/liveliness` returns 200 AND
# `/v1/chat/completions` actually reaches Ollama through LiteLLM.
#
# So: instead of `docker compose up -d litellm`, run this script.
# (The compose service definition is preserved in docker-compose.yml for
# when the upstream issue is fixed; for now, run this script.)
#
# Usage:
#   ./backend/litellm/run.sh           # foreground
#   ./backend/litellm/run.sh --detach  # background, returns immediately
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
cd "$PROJECT_ROOT"

LITELLM_PORT="${LITELLM_PORT:-4000}"
LITELLM_API_KEY="${LITELLM_API_KEY:-sk-styxproxy-local-dev-only}"
LITELLM_IMAGE="${LITELLM_IMAGE:-ghcr.io/berriai/litellm:main-stable}"
CONFIG_PATH="$SCRIPT_DIR/config.yaml"

if [[ ! -f "$CONFIG_PATH" ]]; then
    echo "FATAL: config not found: $CONFIG_PATH" >&2
    exit 1
fi

# Ensure the prior compose-managed container is gone (port 4000 only one
# owner at a time).
docker rm -f bunche-local-litellm-1 2>/dev/null || true

DOCKER_RUN_ARGS=(
    --rm
    -d
    --name litellm-prod
    -e "LITELLM_API_KEY=${LITELLM_API_KEY}"
    -e "PYTHONUNBUFFERED=1"
    -v "${CONFIG_PATH}:/app/config.yaml:ro"
    --network host
    "$LITELLM_IMAGE"
    --config /app/config.yaml
    --port "$LITELLM_PORT"
    --num_workers 1
)

# --detach is opt-in (used by whoever invokes this script from a hook).
if [[ "${1:-}" == "--detach" ]]; then
    shift
fi

echo "Starting LiteLLM on port ${LITELLM_PORT}..."
docker run "${DOCKER_RUN_ARGS[@]}"

# Wait for /health/liveliness to come up (max 30s).
echo "Waiting for /health/liveliness ..."
for i in $(seq 1 30); do
    if curl -sS --max-time 1 "http://127.0.0.1:${LITELLM_PORT}/health/liveliness" 2>/dev/null | grep -q "alive"; then
        echo "LiteLLM is alive on http://127.0.0.1:${LITELLM_PORT}"
        exit 0
    fi
    sleep 1
done

echo "ERROR: LiteLLM did not respond in 30s. Last logs:"
docker logs --tail 20 litellm-prod 2>&1
exit 1
