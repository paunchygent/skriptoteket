#!/usr/bin/env bash

set -euo pipefail

docker_command=(/snap/bin/docker)

main() {
  if (( $# != 1 )); then
    echo "Expected exactly one cleanup selector." >&2
    exit 2
  fi

  selector="$1"
  container_names="$("${docker_command[@]}" ps --all --filter 'name=^/skriptoteket-web$' --format '{{.Names}}')"

  if [[ -z "$container_names" ]]; then
    container_state=absent
  elif [[ "$container_names" != "skriptoteket-web" ]]; then
    printf 'Expected exactly one container named skriptoteket-web; received: %s\n' "$container_names" >&2
    exit 1
  else
    running="$("${docker_command[@]}" inspect --type container --format '{{.State.Running}}' skriptoteket-web)"
    case "$running" in
      false) container_state=stopped ;;
      true) container_state=running ;;
      *)
        printf 'Expected Docker running state true or false for skriptoteket-web; received: %s\n' "$running" >&2
        exit 1
        ;;
    esac
  fi

  case "$selector" in
    cleanup-session-files|cleanup-sandbox-snapshots)
      ;;
    *)
      printf 'Unsupported cleanup selector for skriptoteket-web: %s\n' "$selector" >&2
      exit 2
      ;;
  esac

  if [[ "$container_state" != "running" ]]; then
    printf 'Cleanup skipped: state=%s container=skriptoteket-web.\n' "$container_state"
    exit 0
  fi

  exec "${docker_command[@]}" exec -e PYTHONPATH=/app/src skriptoteket-web pdm run python -m skriptoteket.cli "$selector"
}

if [[ ${BASH_SOURCE[0]} == "$0" ]]; then
  main "$@"
fi
