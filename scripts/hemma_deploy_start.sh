#!/usr/bin/env bash
# Launch one of the two checked-in Hemma deploy workers as a detached remote
# process. The launcher syncs the fixed production checkout to origin/main,
# refuses unless that directory is its own Git root, HEAD equals the fetched
# main and the mode's worker is tracked there, and only then opens that worker
# from the Git root under `agent-secrets run --set skriptoteket-prod`. Neither
# the checkout nor the worker path can be chosen by the caller, so the
# production set reaches no other program. The remote raw log remains
# authoritative; this launcher only hands off cleanly, prints PID/log
# breadcrumbs, and exits.

set -euo pipefail

SSH_HOST="${SKRIPTOTEKET_HEMMA_HOST:-hemma}"
REMOTE_REPO_DIR="/home/paunchygent/apps/skriptoteket"
MODE="seating-export"

usage() {
  cat <<EOF
Usage: pdm run hemma-deploy [--host <ssh-host>] [--mode seating-export|share-previews]

Starts a checked-in Hemma deploy/readiness worker from the production checkout
${REMOTE_REPO_DIR} as a detached remote process.

Options:
  --host      SSH host alias to use (default: ${SSH_HOST})
  --mode      Deploy mode (default: seating-export):
                seating-export  scripts/hemma_deploy_and_verify_seating_export.sh
                share-previews  scripts/hemma_deploy_and_verify_share_previews.sh
  --help      Show this help text
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --host)
      SSH_HOST="$2"
      shift 2
      ;;
    --mode)
      MODE="${2:-}"
      shift $(( $# > 1 ? 2 : 1 ))
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

case "$MODE" in
  seating-export)
    REMOTE_SCRIPT_REL="scripts/hemma_deploy_and_verify_seating_export.sh"
    ;;
  share-previews)
    REMOTE_SCRIPT_REL="scripts/hemma_deploy_and_verify_share_previews.sh"
    ;;
  *)
    echo "Unknown deploy mode: ${MODE} (expected seating-export or share-previews)" >&2
    usage >&2
    exit 1
    ;;
esac

ssh "$SSH_HOST" /bin/bash -s -- "$REMOTE_REPO_DIR" "$REMOTE_SCRIPT_REL" <<'EOF'
set -euo pipefail

repo_dir="$1"
script_rel="$2"

if [[ ! -d "$repo_dir" ]]; then
  echo "Remote repo directory not found: $repo_dir" >&2
  exit 1
fi

cd "$repo_dir"

repo_root="$(git rev-parse --show-toplevel)"
if [[ "$repo_root" != "$(pwd -P)" ]]; then
  echo "Refusing to deploy: $repo_dir is not the root of its Git worktree ($repo_root)." >&2
  exit 1
fi

mkdir -p .artifacts

if ! git diff --quiet || ! git diff --cached --quiet; then
  echo "Refusing to deploy: local git changes in $repo_dir." >&2
  exit 1
fi

current_branch="$(git rev-parse --abbrev-ref HEAD)"
if [[ "$current_branch" != "main" ]]; then
  echo "Switching remote checkout from ${current_branch} to main before deploy."
  git checkout main
fi
echo "Syncing remote checkout to origin/main before deploy."
git fetch origin main
git pull --ff-only origin main

if [[ "$(git rev-parse HEAD)" != "$(git rev-parse FETCH_HEAD)" ]]; then
  echo "Refusing to deploy: local main in $repo_root differs from the fetched origin/main." >&2
  exit 1
fi

if ! git ls-files --error-unmatch -- "$script_rel" >/dev/null 2>&1; then
  echo "Refusing to deploy: $script_rel is not tracked at the synced revision in $repo_root." >&2
  exit 1
fi

script_path="$repo_root/$script_rel"

run_stamp="$(date +%Y%m%d-%H%M%S)"
log_path="$repo_dir/.artifacts/hemma-deploy-${run_stamp}.log"
pid_path="$repo_dir/.artifacts/hemma-deploy-${run_stamp}.pid"

# The worker is a fixed child: it reads secrets only from the production set
# this launcher opens it under, and never syncs or re-enters itself.
nohup agent-secrets run --set skriptoteket-prod -- /bin/bash "$script_path" >"$log_path" 2>&1 </dev/null &
pid="$!"
printf '%s\n' "$pid" >"$pid_path"

sleep 1

if ! kill -0 "$pid" 2>/dev/null; then
  echo "Detached deploy failed to stay alive after launch." >&2
  echo "Remote log: $log_path" >&2
  if [[ -f "$log_path" ]]; then
    tail -n 40 "$log_path" >&2 || true
  fi
  exit 1
fi

echo "Detached Hemma deploy handoff succeeded."
echo "Remote PID: $pid"
echo "Remote log: $log_path"
echo "Remote PID file: $pid_path"
echo "Monitor command: pdm run hemma-deploy-monitor -- $log_path"
echo "Deploy completion status: follow the remote log or monitor command above."
EOF
