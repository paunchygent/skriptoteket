---
type: task
id: TASK-SKRIPT-REP-0051
title: The pre-push check runs directly on Hemma and refuses a push it cannot verify
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: '2026-10-21'
status: ready
closeout_review:
  record: inline
  status: not_started
task_kind: repository
acceptance_criteria:
  - On the Hemma checkout itself, the pre-push check for main runs the verification steps directly, with no ssh to hemma
  - When verification cannot run at all, the push is refused with a clear message; no push passes as UNVERIFIED
  - A focused test covers both cases, failing before the fix
backlog_document_profile: contract-derived
---

## Implementation Contract

User decision 2026-10-21, relayed by the Mac orchestrator: the pre-push check is a defect to repair now. `scripts/hemma_pre_push_check.sh` verifies a push to `main` by `ssh hemma`. Run from the Hemma checkout itself, that SSH fails, the script prints "hemma-check: WARNING Hemma unreachable; <sha> is pushed UNVERIFIED." and exits 0, so the push goes through with no checks run.

This task makes the check run its verification steps directly when it runs on Hemma, and refuse the push when verification cannot run at all.

## Contract Inputs

- `scripts/hemma_pre_push_check.sh` (the `ssh -o BatchMode=yes -o ConnectTimeout=10 hemma true` probe, the remote heredoc, the `hemma-verified-sha` file and the docs-only reuse).
- `.pre-commit-config.yaml` (the pre-push hook entry) and `handoff.md` Facts (the line that says unreachable Hemma warns).
- Pushes from the Hemma checkout on 2026-10-21 that printed UNVERIFIED: `66b3dc8e`, `a7f61563` and `4b321fa1`, plus the later pushes up to `d9fab7e2`. The full suite run on `d9fab7e2` (Hemma retained root `01a15f48-0f71-77ba-b7df-f48c8e838efb`, `evidence/admission/full-suite-d9fab7e24/`: frontend 639 files and 4391 tests, backend 7983 passed and 59 skipped, migrations 121 passed) covers all of them. The pushes after it (`c8cb87fc`, `4dece25e`) changed docs only.

## Core Vertical And Performance

A push of `main` from the Hemma checkout runs the same steps as the remote route (detached checkout of the pushed commit in the verify worktree, `pdm sync --clean`, `fe-install --frozen-lockfile`, `fe-build`, `typecheck`, `test`, and `test-migrations` when the range changes migrations) under the same lock, with no SSH. A push from another host keeps the SSH route. When neither route can run, the push stops with exit 1. Run time is the same as the remote route.

## Validation

- A focused test that fails before the fix: (1) on Hemma, the check runs the steps locally and makes no SSH call; (2) when verification cannot run, the check exits non-zero with a clear message and no "UNVERIFIED" pass. Use command doubles for `ssh`, `git` and `pdm` as the existing script tests do, if any; never run the real suite in the test.
- `pdm run lint` (ShellCheck covers the script) and `pdm run docs-validate`.

## Stop Conditions

- Stop and report if the check cannot tell reliably that it is running on Hemma.

## Decided Contract Terms

| ID  | Decided contract term                                                                                                                                                                |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| D1  | On Hemma the check runs the verification steps directly, with no `ssh hemma`. How it knows it is on Hemma is explicit (for example the host name), never inferred from a failed SSH. |
| D2  | When verification cannot run at all, the check refuses the push (exit 1) with a message that names the reason. No push passes as UNVERIFIED.                                         |
| D3  | The docs-only reuse of the last verified commit, the migration stage rule and the lock stay as they are.                                                                             |
| D4  | The handoff Facts line about the pre-push check is updated to the new behaviour.                                                                                                     |
| D5  | Medium, admitted by the Hemma orchestrator on focused proof (user decision 2026-10-21).                                                                                              |

## Progress

### Implementation 2026-10-21 (worktree skriptoteket-task-skript-rep-0051)

- `scripts/hemma_pre_push_check.sh`: on Hemma (hostname `paunchygent-server`) the check runs the verification steps directly in `~/apps/skriptoteket-verify-main` under the same `flock` lock with no `ssh`; the steps live in one shared `run_verify_steps` function used by both the direct and the `ssh hemma` routes (remote route additionally clears `refs/verify/<sha>`). Off Hemma with unreachable Hemma the check exits 1 with the reason; no UNVERIFIED pass remains. Docs-only reuse, migration rule and lock unchanged.
- Tests: new `tests/unit/scripts/test_hemma_pre_push_check.py` (both cases, command doubles for `hostname`/`ssh`/`git`/`pdm`/`flock`, fake HOME; fails before, passes after). Updated the three adapter tests in `test_pre_push_touches_migrations.py` to the refusal behaviour plus a non-Hemma `hostname` double.
- Proof: focused pytest 14 passed, `pdm run lint` exit 0 (ShellCheck clean), `pdm run docs-validate` exit 0. Logs in the session `evidence/` root.
- Handoff Facts pre-push line updated to the new behaviour.
- Repair 2026-10-21 (env leak): first real push through the repaired hook failed `test_adapter_first_push_runs_migrations` because the hook inherited the outer push's `PRE_COMMIT_*`/`GIT_*` variables. `run_verify_steps` in `scripts/hemma_pre_push_check.sh` now unsets every `PRE_COMMIT_*`/`GIT_*` name computed from the environment (same clean env as the ssh route); both script test files build their subprocess env through shared `tests/unit/scripts/pre_push_hook_env.py:hook_env`, and `test_on_hemma_steps_see_no_pre_commit_or_git_env` proves the direct route's steps see none. Proof: both files 15 passed with and without `PRE_COMMIT_*` exported, `pdm run lint` and `pdm run docs-validate` exit 0; logs in the session `evidence/` root.
