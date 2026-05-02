#!/usr/bin/env bash
# Launch the canonical Hemma deploy script as a detached remote process.
# The remote raw log remains authoritative; this launcher only hands off
# cleanly, prints PID/log breadcrumbs, and exits.

set -euo pipefail

SSH_HOST="${SKRIPTOTEKET_HEMMA_HOST:-hemma}"
REMOTE_REPO_DIR="${SKRIPTOTEKET_HEMMA_REPO_DIR:-/home/paunchygent/apps/skriptoteket}"
REMOTE_SCRIPT_REL="${SKRIPTOTEKET_HEMMA_DEPLOY_SCRIPT:-scripts/hemma_deploy_and_verify_seating_export.sh}"

usage() {
  cat <<EOF
Usage: pdm run hemma-deploy [--host <ssh-host>] [--repo-dir <remote-repo-dir>] [--script <remote-script-relpath>]

Starts the checked-in Hemma deploy/readiness script as a detached remote process.

Options:
  --host      SSH host alias to use (default: ${SSH_HOST})
  --repo-dir  Remote Skriptoteket checkout path (default: ${REMOTE_REPO_DIR})
  --script    Deploy script path relative to the remote repo root
              (default: ${REMOTE_SCRIPT_REL})
  --help      Show this help text
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --host)
      SSH_HOST="$2"
      shift 2
      ;;
    --repo-dir)
      REMOTE_REPO_DIR="$2"
      shift 2
      ;;
    --script)
      REMOTE_SCRIPT_REL="$2"
      shift 2
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

ssh "$SSH_HOST" /bin/bash -s -- "$REMOTE_REPO_DIR" "$REMOTE_SCRIPT_REL" <<'EOF'
set -euo pipefail

repo_dir="$1"
script_rel="$2"

if [[ ! -d "$repo_dir" ]]; then
  echo "Remote repo directory not found: $repo_dir" >&2
  exit 1
fi

cd "$repo_dir"
mkdir -p .artifacts

script_path="$repo_dir/$script_rel"
if [[ "$script_rel" = /* ]]; then
  script_path="$script_rel"
fi

if [[ ! -f "$script_path" ]]; then
  current_branch="$(git rev-parse --abbrev-ref HEAD)"
  if [[ "$current_branch" != "main" ]]; then
    echo "Requested deploy script is missing; switching remote checkout from ${current_branch} to main."
    git checkout main
  fi
  echo "Requested deploy script is missing; fast-forwarding remote main before retrying."
  git fetch origin main
  git pull --ff-only origin main
fi

if [[ ! -f "$script_path" ]]; then
  echo "Remote deploy script not found: $script_path" >&2
  exit 1
fi

run_stamp="$(date +%Y%m%d-%H%M%S)"
log_path="$repo_dir/.artifacts/hemma-deploy-${run_stamp}.log"
pid_path="$repo_dir/.artifacts/hemma-deploy-${run_stamp}.pid"

nohup /bin/bash "$script_path" >"$log_path" 2>&1 </dev/null &
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
