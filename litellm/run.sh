#!/bin/bash
# litellm/run.sh - production startup script for the LiteLLM proxy sidecar.
#
# P1-1 (Jul 22 2026): docker compose's spawn-from-compose path leaves
# LiteLLM's uvicorn worker unable to bind port 4000 (upstream behavior).
# Verified that running it directly with this script's exact flags
# DOES work — both `/health/liveliness` returns 200 AND
# `/v1/chat/completions` actually reaches Ollama through LiteLLM.
#
# P0-5 (Jul 22 2026): Add --foreground mode so systemd can supervise the
# container directly (without -d, the container runs as a child of this
# script, and systemd restarts the whole stack if anything dies).
#
# So: instead of `docker compose up -d litellm`, run this script.
# (The compose service definition is preserved in docker-compose.yml for
# when the upstream issue is fixed; for now, run this script.)
#
# Usage:
#   ./backend/litellm/run.sh --background  # spawn container with -d, exit immediately
#   ./backend/litellm/run.sh --foreground  # run in foreground (systemd supervision)
#   ./backend/litellm/run.sh --watch       # spawn + tail logs (interactive)
#
# Production: styxproxy-litellm.service (systemd) calls --foreground.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
cd "$PROJECT_ROOT"

LITELLM_PORT="${LITELLM_PORT:-4000}"
LITELLM_API_KEY="${LITELLM_API_KEY:-sk-styxproxy-local-dev-only}"
LITELLM_IMAGE="${LITELLM_IMAGE:-ghcr.io/berriai/litellm:main-stable}"
CONFIG_PATH="$SCRIPT_DIR/config.yaml"

MODE="${1:-background}"

if [[ ! -f "$CONFIG_PATH" ]]; then
    echo "FATAL: config not found: $CONFIG_PATH" >&2
    exit 1
fi

# Ensure the prior compose-managed container is gone (port 4000 only one
# owner at a time).
docker rm -f styxproxy-local-litellm-1 2>/dev/null || true

DOCKER_RUN_ARGS=(
    --rm
    --name litellm-prod
    -e "LITELLM_API_KEY=${LITELLM_API_KEY}"
    -e "PYTHONUNBUFFERED=1"
    -v "${CONFIG_PATH}:/app/config.yaml:ro"
    --network host
)

# P0-5: optional env vars for the cloud route + Prisma DB connection.
# Only pass them when set in the parent env so unused vars don't pollute
# the container.
EXTRA_ENV=()
if [[ -n "${LITELLM_CLOUD_API_KEY:-}" ]]; then
    EXTRA_ENV+=(-e "LITELLM_CLOUD_API_KEY=${LITELLM_CLOUD_API_KEY}")
fi
if [[ -n "${DATABASE_URL:-}" ]]; then
    EXTRA_ENV+=(-e "DATABASE_URL=${DATABASE_URL}")
fi
if [[ -n "${MINIMAX_API_KEY:-}" ]]; then
    EXTRA_ENV+=(-e "MINIMAX_API_KEY=${MINIMAX_API_KEY}")
fi

DOCKER_RUN_ARGS+=(
    "${EXTRA_ENV[@]}"
    "$LITELLM_IMAGE"
    --config /app/config.yaml
    --port "$LITELLM_PORT"
    --num_workers 1
)

case "$MODE" in
    --foreground)
        # Run in foreground so systemd can supervise the container directly.
        # When the container dies, this script exits, and systemd restarts it.
        echo "Starting LiteLLM in foreground (systemd mode) on port ${LITELLM_PORT}..."
        exec docker run "${DOCKER_RUN_ARGS[@]}"
        ;;
    --watch)
        # Background + tail logs (interactive).
        echo "Starting LiteLLM in background, tailing logs..."
        docker run -d "${DOCKER_RUN_ARGS[@]}"
        echo "Waiting for /health/liveliness ..."
        for i in $(seq 1 30); do
            if curl -sS --max-time 1 "http://127.0.0.1:${LITELLM_PORT}/health/liveliness" 2>/dev/null | grep -q "alive"; then
                echo "LiteLLM is alive on http://127.0.0.1:${LITELLM_PORT}"
                exec docker logs -f litellm-prod
            fi
            sleep 1
        done
        echo "ERROR: LiteLLM did not respond in 30s. Last logs:"
        docker logs --tail 20 litellm-prod 2>&1
        exit 1
        ;;
    --background|*)
        # Original behavior: spawn detached, exit.
        echo "Starting LiteLLM in background on port ${LITELLM_PORT}..."
        docker run -d "${DOCKER_RUN_ARGS[@]}"
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
        ;;
esac

