#!/usr/bin/env bash
# Pre-push helper: print `run` when the pushed range FROM..TO changes migrations
# or migration tests, else print `skip`. A new remote ref (all-zero FROM) always
# prints `run`. Exits 0 on a decision; any error (git diff failure, missing args)
# exits non-zero and prints neither word to stdout.
set -euo pipefail

from="${1:?usage: pre_push_touches_migrations.sh FROM TO}"
to="${2:?usage: pre_push_touches_migrations.sh FROM TO}"

if [[ "$from" =~ ^0+$ ]]; then
  echo run
  exit 0
fi

# Capture the list first: under pipefail, piping git diff straight into grep
# lets grep closing the pipe early fail the diff with SIGPIPE.
changed="$(git diff --name-only "$from" "$to")"
if grep -qE '^(migrations/versions/.*\.py|tests/integration/(test_migration_[^/]*|migration_[^/]*)\.py|tests/fixtures/database_fixtures\.py)$' <<<"$changed"; then
  echo run
else
  echo skip
fi
exit 0
