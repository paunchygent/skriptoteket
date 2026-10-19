#!/usr/bin/env bash
# Pre-push gate for main: run the full `pdm run typecheck` and `pdm run test`
# on Hemma for the commit being pushed. A failure blocks the push. Hemma being
# unreachable pushes with a warning. Commits that only change Markdown or docs/ since
# the last passing commit reuse that result.
set -euo pipefail

[[ "${PRE_COMMIT_REMOTE_BRANCH:-}" == "refs/heads/main" ]] || exit 0
sha="${PRE_COMMIT_TO_REF:?pre-commit did not supply PRE_COMMIT_TO_REF}"
sha="$(git rev-parse "$sha^{commit}")"

hemma_repo="apps/skriptoteket"
hemma_worktree="apps/skriptoteket-verify-main"
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

if ! ssh -o BatchMode=yes -o ConnectTimeout=10 hemma true 2>/dev/null; then
  echo "hemma-check: WARNING Hemma unreachable; ${sha:0:9} is pushed UNVERIFIED." >&2
  exit 0
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
{
  git checkout -q --detach "$sha" &&
  git -C ~/$hemma_repo update-ref -d "$ref" &&
  pdm sync -q --clean &&
  pdm run fe-install --frozen-lockfile --silent &&
  pdm run fe-build >/dev/null &&
  pdm run typecheck &&
  pdm run test
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
