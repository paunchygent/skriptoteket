#!/usr/bin/env bash
# Pre-push gate for main: run the full `pdm run typecheck` and `pdm run test`
# on Hemma for the commit being pushed. When the pushed range changes migrations
# or migration tests, `pdm run test-migrations` also runs. A failure blocks the
# push. When run on Hemma itself (host paunchygent-server) the steps run
# directly in ~/apps/skriptoteket-verify-main under the same lock, with no ssh;
# when verification cannot run at all the push is blocked. Commits that only
# change Markdown or docs/ since the last passing commit reuse that result.
set -euo pipefail

[[ "${PRE_COMMIT_REMOTE_BRANCH:-}" == "refs/heads/main" ]] || exit 0
if [[ -n "${PRE_COMMIT_TO_REF:-}" ]]; then
  sha="$(git rev-parse "$PRE_COMMIT_TO_REF^{commit}")"
  decision="$(scripts/pre_push_touches_migrations.sh "${PRE_COMMIT_FROM_REF:?pre-commit supplied TO without FROM}" "$sha")"
else
  # Pre-commit all-files mode: the push includes the repository root commit,
  # so the whole tree is new and the migration stage must run.
  sha="$(git rev-parse "${PRE_COMMIT_LOCAL_BRANCH:?pre-commit did not supply PRE_COMMIT_LOCAL_BRANCH}^{commit}")"
  decision=run
fi

run_migrations=0
if [[ $decision == run ]]; then
  run_migrations=1
  echo "hemma-check: pushed range changes migrations; docker migration tests will run."
fi

hemma_repo="apps/skriptoteket"
hemma_worktree="apps/skriptoteket-verify-main"
hemma_hostname="paunchygent-server"
current_host="$(hostname 2>/dev/null || true)"
verified_file="$(git rev-parse --git-common-dir)/hemma-verified-sha"
verified="$(cat "$verified_file" 2>/dev/null || true)"

if [[ -n "$verified" ]] && git merge-base --is-ancestor "$verified" "$sha" 2>/dev/null; then
  # Capture the list first: under pipefail, grep -q closing the pipe early makes
  # a long diff fail with SIGPIPE, which would read as "only docs changed".
  changed="$(git diff --name-only "$verified" "$sha")"
  if ! grep -qvE '(\.md$|^docs/)' <<<"$changed"; then
    echo "hemma-check: only docs changed since verified ${verified:0:9}; skipping."
    exit 0
  fi
fi

# One copy of the verification steps, shared by the direct (on Hemma) and ssh
# routes. Args: $1 = commit sha, $2 = run_migrations flag (0/1). Keep it
# self-contained (no outer locals) so the ssh route can send it with declare -f.
run_verify_steps() {
  local target_sha="$1" want_migrations="$2" name
  # The hook runs inside pre-commit's pre-push environment, so PRE_COMMIT_*
  # and GIT_* variables from the outer push leak in here. The ssh route runs
  # in a fresh login shell and never sees them, so strip every such variable
  # (names computed from the environment, not a hard-coded list) to give both
  # routes the same clean environment for the verification steps.
  while IFS= read -r name; do
    case "$name" in
      PRE_COMMIT_* | GIT_*) unset "$name" ;;
    esac
  done < <(compgen -e)
  git checkout -q --detach "$target_sha" &&
    pdm sync -q --clean &&
    pdm run fe-install --frozen-lockfile --silent &&
    pdm run fe-build >/dev/null &&
    pdm run typecheck &&
    pdm run test &&
    { [[ $want_migrations == 0 ]] || pdm run test-migrations; }
}

# The pushed commit is already in the local repository on Hemma, so no
# refs/verify push is needed on this route.
if [[ "$current_host" == "$hemma_hostname" ]]; then
  echo "hemma-check: running typecheck and tests for ${sha:0:9} directly on Hemma (log ~/logs/pre-push-${sha:0:9}.log)"
  mkdir -p ~/logs
  log=~/logs/pre-push-${sha:0:9}.log
  exec 9>~/.cache/skriptoteket-pre-push.lock
  flock 9
  if (
    cd ~/"$hemma_worktree" || exit 1
    run_verify_steps "$sha" "$run_migrations"
  ) >"$log" 2>&1; then
    status=0
  else
    status=$?
  fi
  tail -n 15 "$log"
  if [[ $status == 0 ]]; then
    echo "$sha" >"$verified_file"
    echo "hemma-check: ${sha:0:9} passed."
  else
    echo "hemma-check: ${sha:0:9} FAILED on Hemma; push blocked. Full log: ~/logs/pre-push-${sha:0:9}.log" >&2
    exit 1
  fi
  exit 0
fi

if ! ssh -o BatchMode=yes -o ConnectTimeout=10 hemma true 2>/dev/null; then
  echo "hemma-check: ERROR cannot verify ${sha:0:9}: not on Hemma (host ${current_host:-unknown}) and Hemma unreachable over ssh; push blocked." >&2
  exit 1
fi

ref="refs/verify/$sha"
git push -q --no-verify "hemma:$hemma_repo" "$sha:$ref"
echo "hemma-check: running typecheck and tests for ${sha:0:9} on Hemma (log ~/logs/pre-push-${sha:0:9}.log)"

# shellcheck disable=SC2087  # expand the variables locally, run remotely
if ssh -o BatchMode=yes hemma bash -s <<EOF
set -uo pipefail
export PATH=\$HOME/.local/bin:\$PATH
mkdir -p ~/logs
log=~/logs/pre-push-${sha:0:9}.log
exec 9>~/.cache/skriptoteket-pre-push.lock
flock 9
cd ~/$hemma_worktree
$(declare -f run_verify_steps)
{
  git -C ~/$hemma_repo update-ref -d "$ref" &&
  run_verify_steps "$sha" "$run_migrations"
} >"\$log" 2>&1
status=\$?
tail -n 15 "\$log"
exit \$status
EOF
then
  echo "$sha" >"$verified_file"
  echo "hemma-check: ${sha:0:9} passed."
else
  echo "hemma-check: ${sha:0:9} FAILED on Hemma; push blocked. Full log: hemma:~/logs/pre-push-${sha:0:9}.log" >&2
  exit 1
fi
