#!/usr/bin/env bash
# Canonical on-host deploy + seating-export readiness gate for Hemma.
# Start it only with `pdm run hemma-deploy`: the launcher
# (scripts/hemma_deploy_start.sh) syncs the checkout to origin/main and opens
# this worker under the production secrets set.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

COMPOSE=(sudo docker compose -f compose.prod.yaml)
COMPOSE_SECRETS=(
  sudo --preserve-env="${AGENT_SECRETS_VARIABLES:-}"
  docker compose -f compose.prod.yaml -f compose.secrets.prod.yaml
)
RUN_STAMP="$(date +%Y%m%d-%H%M%S)"
CORRELATION_PREFIX="pr-0146-seat-export-${RUN_STAMP}"
ARTIFACT_DIR="${ROOT_DIR}/.artifacts/pr-0146-seat-export-cutover-${RUN_STAMP}"

require_env() {
  local key="$1"
  if [[ -z "${!key:-}" ]]; then
    echo "Missing required env var: $key" >&2
    exit 1
  fi
}

if [[ $# -gt 0 ]]; then
  echo "This worker takes no arguments; start it with pdm run hemma-deploy." >&2
  exit 2
fi

if [[ ! -f .env ]]; then
  echo "Missing .env in $ROOT_DIR." >&2
  exit 1
fi

# .env carries configuration only. One dotenv parser reads just the named,
# non-secret settings this worker uses; a value already in the environment wins.
config="$(pdm run python scripts/hemma_deploy_config.py .env \
  BOOTSTRAP_SUPERUSER_EMAIL \
  SIR_CONVERT_A_LOT_V2_BASE_URL \
  HULEEDU_INTERNAL_IDENTITY_PUBLIC_KEY_HOST_DIR)"
while IFS='=' read -r name value; do
  [[ -n "$name" ]] || continue
  if [[ -z "${!name:-}" ]]; then
    export "${name}=${value}"
  fi
done <<<"$config"

export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1

require_env "BOOTSTRAP_SUPERUSER_EMAIL"
require_env "BOOTSTRAP_SUPERUSER_PASSWORD"
require_env "SKRIPTOTEKET_DB_PASSWORD"
require_env "SECRET_KEY"

sir_convert_base_url="${SIR_CONVERT_A_LOT_V2_BASE_URL:-http://sir_convert_a_lot_prod:8085}"
if [[ "${sir_convert_base_url}" == "https://convert.hule.education" ]]; then
    echo "SIR_CONVERT_A_LOT_V2_BASE_URL must target the hule-network Sir Convert service; convert.hule.education is retired. Use the private backend http://sir_convert_a_lot_prod:8085." >&2
    exit 1
fi
export SIR_CONVERT_A_LOT_V2_BASE_URL="${sir_convert_base_url}"

export HULEEDU_INTERNAL_IDENTITY_PUBLIC_KEY_HOST_DIR="${HULEEDU_INTERNAL_IDENTITY_PUBLIC_KEY_HOST_DIR:-/home/paunchygent/apps/huledu/secrets/hemma-runtime/internal-identity}"
HULEEDU_INTERNAL_IDENTITY_PUBLIC_KEY_HOST_PATH="${HULEEDU_INTERNAL_IDENTITY_PUBLIC_KEY_HOST_DIR}/gateway-internal-identity-public-key.pem"
if [[ ! -r "${HULEEDU_INTERNAL_IDENTITY_PUBLIC_KEY_HOST_PATH}" ]]; then
  echo "Missing readable HuleEdu internal identity public key: ${HULEEDU_INTERNAL_IDENTITY_PUBLIC_KEY_HOST_PATH}" >&2
  exit 1
fi

mkdir -p "$ARTIFACT_DIR"
echo "==> Writing PR-0146 cutover artifacts to ${ARTIFACT_DIR}"

echo "==> Building runner image"
"${COMPOSE_SECRETS[@]}" --profile build-only build runner

echo "==> Deploying Skriptoteket web + worker"
"${COMPOSE_SECRETS[@]}" up -d --build

echo "==> Applying database migrations"
"${COMPOSE[@]}" exec -T -e PYTHONPATH=/app/src web pdm run db-upgrade

echo "==> Running local seating export smoke"
sudo --preserve-env="BOOTSTRAP_SUPERUSER_EMAIL,BOOTSTRAP_SUPERUSER_PASSWORD" \
  docker exec \
  -e PYTHONPATH=/app/src \
  -e BOOTSTRAP_SUPERUSER_EMAIL \
  -e BOOTSTRAP_SUPERUSER_PASSWORD \
  skriptoteket-web \
  pdm run python -m skriptoteket.cli smoke-seating-export-readiness \
  --correlation-id "${CORRELATION_PREFIX}-smoke" \
  | tee "${ARTIFACT_DIR}/smoke-result.json"

echo "Seating export deploy/readiness gate passed."
echo "Artifacts: ${ARTIFACT_DIR}"
