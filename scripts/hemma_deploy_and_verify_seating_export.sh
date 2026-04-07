#!/usr/bin/env bash
# Canonical on-host deploy + seating-export readiness gate for Hemma.
# Run this from ~/apps/skriptoteket.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

COMPOSE=(sudo docker compose -f compose.prod.yaml)
RUN_STAMP="$(date +%Y%m%d-%H%M%S)"
CORRELATION_PREFIX="pr-0146-seat-export-${RUN_STAMP}"
ARTIFACT_DIR="${ROOT_DIR}/.artifacts/pr-0146-seat-export-cutover-${RUN_STAMP}"

require_clean_git_checkout() {
  if ! git diff --quiet || ! git diff --cached --quiet; then
    echo "Refusing to deploy with local git changes in ${ROOT_DIR}." >&2
    exit 1
  fi
}

sync_checkout_to_origin_main() {
  local current_branch
  current_branch="$(git rev-parse --abbrev-ref HEAD)"

  if [[ "$current_branch" != "main" ]]; then
    echo "==> Switching deployment checkout from ${current_branch} to main"
    git checkout main
  fi

  echo "==> Fetching latest origin/main"
  git fetch origin main
  echo "==> Fast-forwarding local main to origin/main"
  git pull --ff-only origin main
  echo "==> Deploying commit $(git rev-parse HEAD)"
}

require_env() {
  local key="$1"
  if [[ -z "${!key:-}" ]]; then
    echo "Missing required env var: $key" >&2
    exit 1
  fi
}

if [[ ! -f .env ]]; then
  echo "Missing .env in $ROOT_DIR." >&2
  exit 1
fi

require_clean_git_checkout
sync_checkout_to_origin_main

set -a
# shellcheck disable=SC1091
source .env
set +a

export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1

require_env "BOOTSTRAP_SUPERUSER_EMAIL"
require_env "BOOTSTRAP_SUPERUSER_PASSWORD"
require_env "SKRIPTOTEKET_DB_PASSWORD"
require_env "SECRET_KEY"

mkdir -p "$ARTIFACT_DIR"
echo "==> Writing PR-0146 cutover artifacts to ${ARTIFACT_DIR}"

echo "==> Building runner image"
"${COMPOSE[@]}" --profile build-only build runner

echo "==> Deploying Skriptoteket web + worker"
"${COMPOSE[@]}" up -d --build

echo "==> Applying database migrations"
"${COMPOSE[@]}" exec -T -e PYTHONPATH=/app/src web pdm run db-upgrade

echo "==> Running local seating export smoke"
sudo docker exec \
  -e PYTHONPATH=/app/src \
  -e BOOTSTRAP_SUPERUSER_EMAIL="${BOOTSTRAP_SUPERUSER_EMAIL}" \
  -e BOOTSTRAP_SUPERUSER_PASSWORD="${BOOTSTRAP_SUPERUSER_PASSWORD}" \
  skriptoteket-web \
  pdm run python -m skriptoteket.cli smoke-seating-export-readiness \
  --correlation-id "${CORRELATION_PREFIX}-smoke" \
  | tee "${ARTIFACT_DIR}/smoke-result.json"

echo "Seating export deploy/readiness gate passed."
echo "Artifacts: ${ARTIFACT_DIR}"
