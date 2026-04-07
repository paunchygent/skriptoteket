#!/usr/bin/env bash
# Tail the authoritative Hemma deploy raw log and filter it down to milestone
# markers plus obvious failure patterns for human-readable monitoring.

set -euo pipefail

SSH_HOST="${SKRIPTOTEKET_HEMMA_HOST:-hemma}"
REMOTE_REPO_DIR="${SKRIPTOTEKET_HEMMA_REPO_DIR:-/home/paunchygent/apps/skriptoteket}"
REMOTE_LOG_PATH=""

usage() {
  cat <<EOF
Usage: pdm run hemma-deploy-monitor [--host <ssh-host>] [--repo-dir <remote-repo-dir>] [<remote-log-path>]

Without an explicit remote log path, tails the latest Hemma deploy log under:
  ${REMOTE_REPO_DIR}/.artifacts/hemma-deploy-*.log

This is a best-effort filtered monitor over the authoritative raw remote log.
It replays existing milestone/failure lines first, then follows new ones.
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
    --help|-h)
      usage
      exit 0
      ;;
    *)
      if [[ -n "$REMOTE_LOG_PATH" ]]; then
        echo "Only one remote log path may be provided." >&2
        usage >&2
        exit 1
      fi
      REMOTE_LOG_PATH="$1"
      shift
      ;;
  esac
done

ssh "$SSH_HOST" /bin/bash -s -- "$REMOTE_REPO_DIR" "$REMOTE_LOG_PATH" <<'EOF'
set -euo pipefail

repo_dir="$1"
requested_log_path="$2"

if [[ -n "$requested_log_path" ]]; then
  log_path="$requested_log_path"
else
  latest_log="$(find "$repo_dir/.artifacts" -maxdepth 1 -type f -name 'hemma-deploy-*.log' -print | sort | tail -n 1)"
  if [[ -z "$latest_log" ]]; then
    echo "No Hemma deploy logs found under $repo_dir/.artifacts." >&2
    exit 1
  fi
  log_path="$latest_log"
fi

if [[ ! -f "$log_path" ]]; then
  echo "Remote deploy log not found: $log_path" >&2
  exit 1
fi

pattern='(^==>)|(passed\.)|([Ww]arn(ing)?)|([Ee]rror)|([Ff]ailed)|([Ff]atal)|([Ee]xception)|([Tt]raceback)'

echo "Monitoring remote log: $log_path" >&2
echo "Replaying existing milestone/failure lines, then following new ones..." >&2

grep -E "$pattern" "$log_path" || true
tail -n 0 -F "$log_path" 2>&1 | grep --line-buffered -E "$pattern"
EOF
