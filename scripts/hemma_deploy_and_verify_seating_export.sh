#!/usr/bin/env bash
# Canonical on-host deploy + seating-export readiness gate for Hemma.
# Run this from ~/apps/skriptoteket after pull.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

COMPOSE=(sudo docker compose -f compose.prod.yaml)
SIR_CONVERT_ROOT="${SIR_CONVERT_A_LOT_HEMMA_ROOT:-$HOME/apps/sir-convert-a-lot}"
SIR_CONVERT_HOST_LANE_URL="${SIR_CONVERT_A_LOT_HOST_LANE_URL:-http://127.0.0.1:28085}"
CORRELATION_PREFIX="pr-0122-seat-export-$(date +%Y%m%d-%H%M%S)"

require_env() {
  local key="$1"
  if [[ -z "${!key:-}" ]]; then
    echo "Missing required env var: $key" >&2
    exit 1
  fi
}

probe_sir_convert() {
  curl -fsS "${SIR_CONVERT_HOST_LANE_URL}/readyz" >/dev/null
  curl -fsS \
    -H "X-API-Key: ${SIR_CONVERT_A_LOT_V2_API_KEY}" \
    "${SIR_CONVERT_HOST_LANE_URL}/v2/push/webhooks/subscriptions" >/dev/null
}

recreate_sir_convert() {
  if [[ ! -d "$SIR_CONVERT_ROOT/.git" ]]; then
    echo "Sir Convert repo not found at ${SIR_CONVERT_ROOT}. Cannot recreate service." >&2
    exit 1
  fi
  (
    cd "$SIR_CONVERT_ROOT"
    pdm run dev-recreate sir_convert_a_lot_prod
  )
}

if [[ ! -f .env ]]; then
  echo "Missing .env in $ROOT_DIR." >&2
  exit 1
fi

set -a
source .env
set +a

export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1

require_env "SIR_CONVERT_A_LOT_V2_BASE_URL"
require_env "SIR_CONVERT_A_LOT_V2_API_KEY"
require_env "SIR_CONVERT_A_LOT_V2_CALLBACK_BASE_URL"
require_env "BOOTSTRAP_SUPERUSER_EMAIL"
require_env "BOOTSTRAP_SUPERUSER_PASSWORD"
require_env "SKRIPTOTEKET_DB_PASSWORD"
require_env "SECRET_KEY"

echo "==> Probing Sir Convert-a-Lot on ${SIR_CONVERT_HOST_LANE_URL}"
if ! probe_sir_convert; then
  echo "Sir Convert preflight failed; recreating sir_convert_a_lot_prod via the supported Hemma surface."
  recreate_sir_convert
  probe_sir_convert
fi

echo "==> Building runner image"
"${COMPOSE[@]}" --profile build-only build runner

echo "==> Deploying Skriptoteket web + worker"
"${COMPOSE[@]}" up -d --build

echo "==> Applying database migrations"
"${COMPOSE[@]}" exec -T -e PYTHONPATH=/app/src web pdm run db-upgrade

echo "==> Verifying production Sir Convert env wiring inside skriptoteket-web"
sudo docker exec skriptoteket-web env | grep '^SIR_CONVERT_A_LOT_V2_BASE_URL=' >/dev/null
sudo docker exec skriptoteket-web env | grep '^SIR_CONVERT_A_LOT_V2_API_KEY=' >/dev/null
sudo docker exec skriptoteket-web env | grep '^SIR_CONVERT_A_LOT_V2_CALLBACK_BASE_URL=' >/dev/null

echo "==> Re-probing Sir Convert-a-Lot after Skriptoteket deploy"
probe_sir_convert

echo "==> Reconciling seating-export webhook state"
sudo docker exec \
  -e PYTHONPATH=/app/src \
  skriptoteket-web \
  pdm run python -m skriptoteket.cli reconcile-seating-export-webhooks \
  --correlation-id "${CORRELATION_PREFIX}-reconcile"

echo "==> Running callback-capable seating export smoke"
sudo docker exec \
  -e PYTHONPATH=/app/src \
  -e BOOTSTRAP_SUPERUSER_EMAIL="${BOOTSTRAP_SUPERUSER_EMAIL}" \
  -e BOOTSTRAP_SUPERUSER_PASSWORD="${BOOTSTRAP_SUPERUSER_PASSWORD}" \
  skriptoteket-web \
  pdm run python -m skriptoteket.cli smoke-seating-export-readiness \
  --timeout-seconds 240 \
  --poll-interval-seconds 2 \
  --correlation-id "${CORRELATION_PREFIX}-smoke"

echo "Seating export deploy/readiness gate passed."
