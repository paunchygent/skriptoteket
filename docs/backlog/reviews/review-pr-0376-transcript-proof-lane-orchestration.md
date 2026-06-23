---
type: review
id: REV-PR-0376
title: "Review: PR-0376 transcript proof lane orchestration"
status: approved
owners: "agents"
created: 2026-06-23
updated: 2026-06-23
reviewer: "codex-independent-reviewer"
prs:
  - PR-0376
links:
  - EPIC-37
  - ST-37-04
  - PR-0368
  - PR-0374
  - PR-0375
  - PR-0377
---

## TL;DR

PR-0376 is approved on pass 11. The launcher now uses the portable non-interactive Docker CLI shape `docker exec <container> printenv <key>` for Gateway, Skriptoteket web, and Skriptoteket worker runtime env inspection, while preserving the prior tunnel, readiness, sanitizer, cleanup, and safe-diagnostics protections.

## Problem Statement

The review checks whether the retained Audio Transcription transcript parity proof can be launched through one committed remote-proof lane without operator port guesses, direct auth shortcuts, browser-held Sir Convert credentials, or unsafe local runtime residue.

## Proposed Solution

The implementation adds `pdm run transcript-parity-proof remote-proof`, descriptor-pins the local proof to `http://host.docker.internal:38085`, validates Sir Convert `/readyz` for `service_profile=remote-proof`, recreates only the required HuleEdu Gateway and Skriptoteket producer services with lane overlay env, verifies running container env, invokes `scripts.audio_transcription_parity_live` with descriptor values, and restores the touched runtime after the proof.

## Artifacts to Review

| File | Focus | Time |
|------|-------|------|
| `AGENTS.md` | Repo review, docs-as-code, shared-auth, and validation rules | 5 min |
| `.codex/handoff.md` | Current operator proof guidance | 5 min |
| `docs/backlog/prs/pr-0376-st-37-04-transcript-proof-lane-orchestration.md` | Scope, acceptance criteria, validation claims | 15 min |
| `scripts/transcript_parity_proof_launcher.py` | Descriptor, preflight, mutable runtime orchestration, restore behavior | 35 min |
| `scripts/audio_transcription_parity_live.py` | HuleEdu browser-session path and pre-upload trust gate | 15 min |
| `scripts/_sir_convert_trust_lane_preflight.py` | Fail-closed trust-lane validation | 10 min |
| `tests/unit/scripts/test_transcript_parity_proof_launcher.py` | Launcher behavior, restoration proof, command surface | 20 min |
| `tests/unit/scripts/test_sir_convert_trust_lane_preflight.py` | Pre-upload trust-lane behavior | 10 min |

**Total estimated time:** ~115 minutes

## Key Decisions

| Decision | Rationale | Approve? |
|----------|-----------|----------|
| Use one committed domain command for the retained local remote-proof lane. | Removes copied proof arguments from the normal operator path. | [x] |
| Pin local transcript parity proof to `host.docker.internal:38085` and `service_profile=remote-proof`. | Prevents accidental production or local `8085` proof. | [x] |
| Preserve HuleEdu browser-session login and server-side Gateway/Sir Convert auth. | The proof continues through `login_via_auth_entry` and does not add direct app auth or browser-held Sir Convert credentials. | [x] |
| Restore mutated HuleEdu Gateway and Skriptoteket runtime state after proof. | Prevents proof-lane residue from misleading later shared-auth work. | [x] |

## Review Checklist

- [x] Governing PR doc exists.
- [x] Lane selection is executable through a committed command.
- [x] Forbidden local `8085` target fails before proof.
- [x] Wrong Sir Convert profile fails before runtime recreate.
- [x] Gateway and Skriptoteket runtime env mismatches fail before proof upload.
- [x] HuleEdu browser-session ceremony is preserved.
- [x] Runtime cleanup/restore is implemented and tested for success, proof failure, and cleanup-step failure.

## Review Feedback

**Reviewer:** codex-independent-reviewer
**Date:** 2026-06-23
**Verdict:** approved

### Pass 1 Finding Resolution

| Previous finding | Resolution | Evidence |
|------------------|------------|----------|
| `high`: launcher mutated proof-lane runtime state without restoring it after success/failure. | Resolved. The mutable orchestration is wrapped in `try`/`finally`, and `_restore_runtime_state(...)` recreates HuleEdu Gateway and Skriptoteket `web`/`worker` with the proof overlay keys removed. | `scripts/transcript_parity_proof_launcher.py:132`, `scripts/transcript_parity_proof_launcher.py:199`, `scripts/transcript_parity_proof_launcher.py:445` |
| Missing focused restoration proof. | Resolved. Focused tests assert restore commands run after successful proof and after proof-command failure, and that proof overlay env keys are not passed to restore. | `tests/unit/scripts/test_transcript_parity_proof_launcher.py:181`, `tests/unit/scripts/test_transcript_parity_proof_launcher.py:202` |

### Findings

None.

### Suggestions (Optional)

None.

### Decision Approvals

- [x] Descriptor-pinned `remote-proof` lane.
- [x] Fail-closed pre-upload trust lane behavior.
- [x] HuleEdu browser-session proof preservation.
- [x] Cleanup/restore safety.

## Pass 3 Tunnel-Management Review

**Reviewer:** codex-independent-reviewer
**Date:** 2026-06-23
**Verdict:** approved

### Scope

This pass re-reviewed the follow-up tunnel-management fix after the overseer found that `http://127.0.0.1:38085/readyz` failed when no tunnel was already open. Reviewed surfaces:

| File | Focus |
|------|-------|
| `scripts/transcript_parity_proof_launcher.py` | Optional SSH tunnel open/stop behavior, ordering before runtime mutation, cleanup ordering |
| `tests/unit/scripts/test_transcript_parity_proof_launcher.py` | Behavior-focused tunnel and cleanup tests |
| `docs/backlog/prs/pr-0376-st-37-04-transcript-proof-lane-orchestration.md` | Updated implementation summary and red/green evidence |
| `.codex/handoff.md` | Current operator guidance for the launcher |

### Review Questions

| Question | Decision | Evidence |
|----------|----------|----------|
| Does the launcher open a sanctioned remote-proof SSH tunnel only when `38085/readyz` is initially unreachable? | Approved | `_fetch_readyz_with_optional_tunnel(...)` tries `readyz` first and opens a tunnel only for `sir_convert_readyz_unreachable`; `test_unreachable_readyz_opens_owned_tunnel_before_runtime_mutation` covers this. |
| Does it avoid opening/stopping anything when the endpoint is already reachable? | Approved | `test_readyz_reachable_does_not_open_or_stop_tunnel` asserts no SSH commands are issued. |
| Does it stop only the tunnel it opened, using an owned control socket or equivalent? | Approved | `_open_remote_proof_tunnel(...)` creates `<run-dir>/remote-proof-ssh.sock` with `ssh -M -S ...`; `_stop_remote_proof_tunnel(...)` uses `ssh -S <same-socket> -O exit hemma`; no process-kill or broad tunnel cleanup is introduced. |
| Does cleanup still run even if runtime restore fails or proof fails? | Approved | `_cleanup_runtime_and_tunnel(...)` attempts runtime restore and then owned tunnel stop, preserving a cleanup error after attempting both. `test_opened_tunnel_is_stopped_when_runtime_restore_fails` covers the critical ordering. |
| Does readiness/profile validation still happen before HuleEdu/Skriptoteket mutation and before upload? | Approved | `main(...)` fetches and validates readyz before signer lookup and before `runtime_mutated = True`; `test_unreachable_readyz_profile_mismatch_stops_tunnel_before_runtime_mutation` proves no runtime mutation when profile validation fails after tunnel open. |
| Are tests behavior-focused and sufficient? | Approved | The tests model the operator-visible contract: unreachable readyz opens owned tunnel, reachable readyz does not, profile mismatch stops before runtime mutation, proof/restore failures still trigger cleanup, and command values remain pinned to remote-proof `38085`. |
| Are docs/handoff truthful without fallback/operator-guess paths? | Approved | PR doc and handoff describe the committed launcher, owned tunnel socket, no-op behavior when the endpoint is already reachable, and no manual fallback as the normal path. |

### Findings

None.

### Verification Evidence

| Command / check | Outcome |
|-----------------|---------|
| `pdm run test tests/unit/scripts/test_transcript_parity_proof_launcher.py` | Passed: 11 tests. |
| `pdm run test tests/unit/scripts/test_transcript_parity_proof_launcher.py tests/unit/scripts/test_audio_transcription_parity_progress_snapshot.py tests/unit/scripts/test_audio_transcription_parity_summary_truthfulness.py tests/unit/scripts/test_sir_convert_trust_lane_preflight.py tests/unit/scripts/test_playwright_script_surface.py` | Passed: 47 tests. |
| Code review of `scripts/transcript_parity_proof_launcher.py:123` through `scripts/transcript_parity_proof_launcher.py:383` | Passed: readyz/profile validation happens before runtime mutation; the launcher stops only its owned SSH control-socket tunnel and still attempts tunnel cleanup after runtime restore failure. |

## Pass 4 Selected-Service Recreate / Cleanup Review

**Reviewer:** codex-independent-reviewer
**Date:** 2026-06-23
**Verdict:** changes_requested

### Scope

This pass re-reviewed the follow-up fix after the full launcher failed with `skriptoteket_restore_failed` because `pdm run dev-stack recreate web worker` was not a supported selected-service wrapper.

| File | Focus |
|------|-------|
| `scripts/dev_stack.py` | Selected-service `recreate` command generation and no-arg full-stack behavior |
| `tests/unit/scripts/test_dev_stack.py` | Wrapper contract regression proof |
| `scripts/transcript_parity_proof_launcher.py` | Named command use, restore/error preservation, owned tunnel cleanup |
| `tests/unit/scripts/test_transcript_parity_proof_launcher.py` | Cleanup-error behavior and launcher command assertions |
| `docs/backlog/prs/pr-0376-st-37-04-transcript-proof-lane-orchestration.md` | Updated implementation summary and red/green evidence |
| `.codex/handoff.md` | Current operator guidance |

### Findings

#### High: HuleEdu restore failure still skips Skriptoteket restore

`scripts/transcript_parity_proof_launcher.py:374` calls `_restore_runtime_state(...)` as one cleanup unit, and `_restore_runtime_state(...)` runs HuleEdu restore before Skriptoteket restore at `scripts/transcript_parity_proof_launcher.py:574` through `scripts/transcript_parity_proof_launcher.py:587`. If the HuleEdu `dev-recreate api_gateway_service` restore fails, `_run_required(...)` raises immediately and `pdm run dev-stack recreate web worker` is never attempted. The outer cleanup catches that error and still tears down the owned SSH tunnel, but it can leave Skriptoteket `web`/`worker` running with `SIR_CONVERT_A_LOT_V2_BASE_URL=http://host.docker.internal:38085`.

Why it matters: the PR contract requires restoring HuleEdu Gateway and Skriptoteket producer runtime after proof success/failure, and the handoff now tells operators that both are restored. A single restore failure should not prevent the independent product runtime restore, especially because this launcher intentionally mutates two separate repos/services.

Concrete fix: split restore cleanup into independently attempted steps. Run HuleEdu Gateway restore and Skriptoteket selected-service restore in separate `try` blocks, accumulate cleanup diagnostics, then attempt owned tunnel teardown. Preserve the primary proof/mutation error when one exists; if there is no primary error, raise a typed cleanup failure that reports all failed cleanup steps.

Proof required: add a focused launcher test where proof fails, the HuleEdu restore command fails, and an owned tunnel was opened; assert that `("pdm", "run", "dev-stack", "recreate", "web", "worker")` is still invoked without `SIR_CONVERT_A_LOT_V2_BASE_URL`, the owned `ssh -S <socket> -O exit hemma` command still runs, and the raised primary error remains `transcript_parity_proof_failed` with cleanup diagnostics. Run `pdm run test tests/unit/scripts/test_transcript_parity_proof_launcher.py`.

### Approved Checks

| Review question | Result | Evidence |
|-----------------|--------|----------|
| `pdm run dev-stack recreate web worker` maps to exactly `docker compose ... up -d --force-recreate web worker` | Approved | `scripts/dev_stack.py:50` through `scripts/dev_stack.py:59` allows args for `recreate`; `_commands_for(...)` appends args only to the first compose command at `scripts/dev_stack.py:108` through `scripts/dev_stack.py:117`; `tests/unit/scripts/test_dev_stack.py:45` through `tests/unit/scripts/test_dev_stack.py:53` proves no DB upgrade follows selected-service recreate. |
| No-arg `dev-stack recreate` retains prior full-stack behavior and DB upgrade semantics | Approved by code review | With no extra args, `_commands_for(...)` returns the original `spec.commands` at `scripts/dev_stack.py:111` through `scripts/dev_stack.py:112`; the `recreate` spec still contains full-stack `up -d --force-recreate` followed by `DB_UPGRADE` at `scripts/dev_stack.py:55` through `scripts/dev_stack.py:58`. |
| Launcher still uses named repo command surfaces | Approved | Mutation and restore use `pdm run run-local-pdm dev-recreate api_gateway_service` and `pdm run dev-stack recreate web worker` at `scripts/transcript_parity_proof_launcher.py:141` through `scripts/transcript_parity_proof_launcher.py:168` and `scripts/transcript_parity_proof_launcher.py:574` through `scripts/transcript_parity_proof_launcher.py:587`; no raw Docker recreate path is introduced in the launcher. |
| Prior PR-0376 fail-closed protections remain intact | Approved | Ready/profile validation precedes runtime mutation at `scripts/transcript_parity_proof_launcher.py:124` through `scripts/transcript_parity_proof_launcher.py:140`; runtime env validation precedes proof upload at `scripts/transcript_parity_proof_launcher.py:155` through `scripts/transcript_parity_proof_launcher.py:178`; forbidden local targets remain rejected at `scripts/transcript_parity_proof_launcher.py:256` through `scripts/transcript_parity_proof_launcher.py:269`. |
| Cleanup preserves primary proof/mutation error when cleanup also fails | Partially approved | `scripts/transcript_parity_proof_launcher.py:205` through `scripts/transcript_parity_proof_launcher.py:221` records the primary error and attaches cleanup notes instead of masking it; the finding above blocks approval because independent runtime restore steps are still not all attempted. |
| Docs/handoff are truthful | Changes requested | They correctly describe the selected-service wrapper, but the current cleanup implementation does not yet guarantee the documented HuleEdu plus Skriptoteket restore behavior after a restore-step failure. |

### Verification Evidence

| Command / check | Outcome |
|-----------------|---------|
| `pdm run test tests/unit/scripts/test_dev_stack.py tests/unit/scripts/test_transcript_parity_proof_launcher.py` | Passed: 17 tests. |
| `pdm run test tests/unit/scripts/test_transcript_parity_proof_launcher.py tests/unit/scripts/test_audio_transcription_parity_progress_snapshot.py tests/unit/scripts/test_audio_transcription_parity_summary_truthfulness.py tests/unit/scripts/test_sir_convert_trust_lane_preflight.py tests/unit/scripts/test_playwright_script_surface.py tests/unit/scripts/test_dev_stack.py` | Passed: 53 tests. |
| `pdm run docs-validate` | Passed. |
| `pdm run handoff-validate` | Passed. |
| `git diff --check` | Passed. |
| Code review of `scripts/dev_stack.py`, `scripts/transcript_parity_proof_launcher.py`, and focused tests | Selected-service wrapper fix is correct; cleanup independence gap remains. |

## Pass 5 Independent Cleanup Remediation Review

**Reviewer:** codex-independent-reviewer
**Date:** 2026-06-23
**Verdict:** approved

### Scope

This pass re-reviewed the remediation for the pass 4 high finding that a failed HuleEdu Gateway restore skipped the independent Skriptoteket `web`/`worker` restore.

| File | Focus |
|------|-------|
| `scripts/transcript_parity_proof_launcher.py` | Independent cleanup attempts and primary-error preservation |
| `tests/unit/scripts/test_transcript_parity_proof_launcher.py` | Regression proof for HuleEdu restore failure plus Skriptoteket restore and tunnel teardown |
| `scripts/dev_stack.py` | Prior selected-service `recreate` wrapper contract |
| `tests/unit/scripts/test_dev_stack.py` | Wrapper regression coverage |
| `docs/backlog/prs/pr-0376-st-37-04-transcript-proof-lane-orchestration.md` | Independent cleanup red/green evidence |
| `.codex/handoff.md` | Current operator guidance |

### Finding Resolution

| Previous finding | Resolution | Evidence |
|------------------|------------|----------|
| `high`: HuleEdu restore failure still skips Skriptoteket restore. | Resolved. `_cleanup_runtime_and_tunnel(...)` now runs HuleEdu restore, Skriptoteket restore, and owned tunnel stop in separate `try` blocks and accumulates cleanup errors instead of short-circuiting after the first failure. | `scripts/transcript_parity_proof_launcher.py:361` through `scripts/transcript_parity_proof_launcher.py:395` |
| Missing proof for exact pass 4 failure. | Resolved. The focused regression test opens an owned tunnel, makes proof fail, makes HuleEdu restore fail, then asserts Skriptoteket restore still runs without producer overlay env and the owned tunnel stop still runs, while the raised error remains `transcript_parity_proof_failed` with cleanup diagnostics. | `tests/unit/scripts/test_transcript_parity_proof_launcher.py:350` through `tests/unit/scripts/test_transcript_parity_proof_launcher.py:377` |

### Review Questions

| Question | Decision | Evidence |
|----------|----------|----------|
| Are HuleEdu restore, Skriptoteket restore, and owned tunnel stop independently attempted when applicable? | Approved | `_cleanup_runtime_and_tunnel(...)` appends errors from each cleanup step and continues to the next step; the regression test proves Skriptoteket restore and tunnel stop still happen after HuleEdu restore failure. |
| Is the primary proof/mutation error preserved while cleanup diagnostics are retained? | Approved | `main(...)` records `primary_error`, attaches cleanup notes when cleanup errors exist, and re-raises the original error path; `_raise_cleanup_errors(...)` is reserved for cleanup-only failures. |
| Does the test prove the exact previous high finding? | Approved | `test_cleanup_restores_skriptoteket_after_huleedu_restore_failure` exercises proof failure plus HuleEdu restore failure plus owned tunnel and asserts the missed Skriptoteket restore from pass 4 now occurs. |
| Do previous wrapper/tunnel/profile safeguards remain intact? | Approved | Selected-service recreate still emits only `docker compose ... up -d --force-recreate web worker`; readyz/profile validation still precedes runtime mutation; forbidden `8085` remains rejected before proof; reachable readyz still opens no tunnel. |
| Are docs/handoff truthful? | Approved | PR doc and handoff now state that HuleEdu restore, Skriptoteket restore, and owned tunnel teardown are independently attempted; that matches the implementation and tests. |

### Findings

None.

### Verification Evidence

| Command / check | Outcome |
|-----------------|---------|
| `pdm run test tests/unit/scripts/test_dev_stack.py tests/unit/scripts/test_transcript_parity_proof_launcher.py` | Passed: 17 tests. |
| `pdm run test tests/unit/scripts/test_transcript_parity_proof_launcher.py tests/unit/scripts/test_audio_transcription_parity_progress_snapshot.py tests/unit/scripts/test_audio_transcription_parity_summary_truthfulness.py tests/unit/scripts/test_sir_convert_trust_lane_preflight.py tests/unit/scripts/test_playwright_script_surface.py tests/unit/scripts/test_dev_stack.py` | Passed: 53 tests. |
| `pdm run docs-validate` | Passed. |
| `pdm run handoff-validate` | Passed. |
| `git diff --check` | Passed. |
| Code review of `scripts/transcript_parity_proof_launcher.py`, `tests/unit/scripts/test_transcript_parity_proof_launcher.py`, `.codex/handoff.md`, and `docs/backlog/prs/pr-0376-st-37-04-transcript-proof-lane-orchestration.md` | Passed: cleanup independence, primary-error preservation, previous wrapper/tunnel/profile safeguards, and operator guidance align. |

## Pass 6 HuleEdu Env-Contamination Remediation Review

**Reviewer:** codex-independent-reviewer
**Date:** 2026-06-23
**Verdict:** approved

### Scope

This pass re-reviewed the remediation for the full-launcher failure where HuleEdu `auth-integration check` could inherit Skriptoteket `pdm run` process state (`PDM_*`, virtualenv, `PYTHONPATH`, and current repo `.venv/bin` PATH entry).

| File | Focus |
|------|-------|
| `scripts/transcript_parity_proof_launcher.py` | HuleEdu-only sanitized env construction and command application |
| `tests/unit/scripts/test_transcript_parity_proof_launcher.py` | Regression proof for cross-repo HuleEdu env sanitization |
| `docs/backlog/prs/pr-0376-st-37-04-transcript-proof-lane-orchestration.md` | Env-sanitizer red/green evidence |
| `.codex/handoff.md` | Current operator guidance |

### Review Questions

| Question | Decision | Evidence |
|----------|----------|----------|
| Does the sanitizer remove repo-local PDM/venv/PYTHONPATH contamination and preserve needed env/overlay values? | Approved | `_sanitized_huleedu_base_env(...)` removes `PDM_*`, `PYTHONHOME`, `PYTHONPATH`, `VIRTUAL_ENV`, `VIRTUAL_ENV_PROMPT`, and strips the current repo `.venv/bin` PATH entry; `_huleedu_command_env(...)` merges proof-lane overrides after sanitization, so Gateway overlay values win. |
| Is it applied to every HuleEdu command and not to Skriptoteket/Docker commands? | Approved | HuleEdu trust-profile, Gateway recreate, auth-integration check, and Gateway restore use `_huleedu_command_env(...)` or `_huleedu_restore_env(...)`; Skriptoteket recreate/restore still use `_merged_env(...)`/`_restore_env(...)`, and Docker env inspection still receives no sanitized env. |
| Do previous tunnel/wrapper/cleanup/primary-error safeguards remain intact? | Approved | Code review and focused tests still cover readyz-before-mutation, owned tunnel open/stop, selected-service `dev-stack recreate web worker`, independent cleanup, and primary-error preservation. |
| Are diagnostics safe with no new secret exposure? | Approved | The change removes ambient process contamination and records only command/return-code metadata on failure; docs/tests mention env key names and non-secret local lane URLs, not secret values. |
| Are tests behavior-focused and sufficient? | Approved | `test_huleedu_commands_use_cross_repo_sanitized_environment` runs the launcher through its public entrypoint under contaminated parent env, then asserts every HuleEdu `run-local-pdm` command receives a sanitized env while the Gateway mutation preserves the proof-lane backend overlay. |
| Are docs/handoff truthful? | Approved | PR doc and handoff state that only HuleEdu `run-local-pdm` calls use a cross-repo sanitized env; that matches the implementation. |

### Findings

None.

### Verification Evidence

| Command / check | Outcome |
|-----------------|---------|
| `pdm run test tests/unit/scripts/test_dev_stack.py tests/unit/scripts/test_transcript_parity_proof_launcher.py` | Passed: 18 tests. |
| `pdm run test tests/unit/scripts/test_transcript_parity_proof_launcher.py tests/unit/scripts/test_audio_transcription_parity_progress_snapshot.py tests/unit/scripts/test_audio_transcription_parity_summary_truthfulness.py tests/unit/scripts/test_sir_convert_trust_lane_preflight.py tests/unit/scripts/test_playwright_script_surface.py tests/unit/scripts/test_dev_stack.py` | Passed: 54 tests. |
| `pdm run docs-validate` | Passed. |
| `pdm run handoff-validate` | Passed. |
| `git diff --check` | Passed. |
| Code review of `scripts/transcript_parity_proof_launcher.py`, `tests/unit/scripts/test_transcript_parity_proof_launcher.py`, `.codex/handoff.md`, and `docs/backlog/prs/pr-0376-st-37-04-transcript-proof-lane-orchestration.md` | Passed: HuleEdu-only sanitizer removes cross-repo contamination, preserves overlay values, and does not disturb Skriptoteket/Docker env paths. |

## Pass 7 Failure-Diagnostics Review

**Reviewer:** codex-independent-reviewer
**Date:** 2026-06-23
**Verdict:** changes_requested

### Scope

This pass re-reviewed the diagnostics remediation after the full launcher still failed at HuleEdu `auth-integration check` without enough child process output or a failure artifact before `launch-manifest.json`.

| File | Focus |
|------|-------|
| `scripts/transcript_parity_proof_launcher.py` | Bounded/redacted child stdout/stderr metadata, `failure-summary.json`, prior cleanup/tunnel/env safeguards |
| `tests/unit/scripts/test_transcript_parity_proof_launcher.py` | Auth-check failure diagnostic contract regression proof |
| `docs/backlog/prs/pr-0376-st-37-04-transcript-proof-lane-orchestration.md` | Failure-summary implementation and red/green evidence |
| `.codex/handoff.md` | Operator guidance for the diagnostic artifact |

### Findings

#### High: Authorization/cookie header redaction can leave the secret value in `failure-summary.json`

`scripts/transcript_parity_proof_launcher.py:64` through `scripts/transcript_parity_proof_launcher.py:67` matches sensitive assignments with a value pattern of only `[^\s]+`, and `_redact_sensitive_text(...)` at `scripts/transcript_parity_proof_launcher.py:603` through `scripts/transcript_parity_proof_launcher.py:612` relies on that match before writing child stdout/stderr snippets into `LauncherError.metadata` and `failure-summary.json`. For common diagnostics such as `Authorization: Bearer child-token` or `Cookie: session=abc csrf=def`, the current regex redacts only the first whitespace-delimited value segment (`Bearer` or `session=abc`) and leaves the actual token or additional cookie material in the retained artifact.

Why it matters: the new artifact is explicitly intended for failed HuleEdu/Gateway proof debugging. Even if child commands should not print secrets, the launcher-owned diagnostic boundary must not preserve auth headers, cookies, or tokens when they appear in child stderr/stdout. This violates the pass goal to provide safe metadata without env dumps/secrets.

Concrete fix: strengthen `_redact_sensitive_text(...)` to redact the full value for sensitive key/header lines, including multi-token `Authorization:` values, cookie lists, and bearer-token forms. Keep the useful non-secret surrounding lines and bounded length behavior. Add a focused regression case to `test_auth_integration_failure_writes_safe_failure_summary` or a sibling test with child stdout/stderr containing `Authorization: Bearer child-secret-token` and `Cookie: session=child-secret; csrf=child-secret`, then assert those raw values are absent from both raised metadata and `failure-summary.json`.

Proof required: run `pdm run test tests/unit/scripts/test_transcript_parity_proof_launcher.py` plus the combined proof-script suite, `pdm run docs-validate`, `pdm run handoff-validate`, and `git diff --check`.

### Approved Checks

| Review question | Result | Evidence |
|-----------------|--------|----------|
| Are stdout/stderr snippets bounded? | Approved | `_command_output_snippet(...)` caps redacted child output at `COMMAND_OUTPUT_SNIPPET_CHARS = 800` with an explicit truncation marker at `scripts/transcript_parity_proof_launcher.py:595` through `scripts/transcript_parity_proof_launcher.py:600`. |
| Does `failure-summary.json` include the needed blocker and runtime truth fields? | Approved | `_write_failure_summary(...)` writes `blocker_code`, `blocker_message`, sanitized metadata, cleanup diagnostics, exception notes, descriptor truth, and readyz summary at `scripts/transcript_parity_proof_launcher.py:615` through `scripts/transcript_parity_proof_launcher.py:638`. |
| Is a summary written for the HuleEdu auth-check failure before proof invocation? | Approved | `main(...)` writes the failure summary in the post-run-dir `except` path at `scripts/transcript_parity_proof_launcher.py:225` through `scripts/transcript_parity_proof_launcher.py:233`; `test_auth_integration_failure_writes_safe_failure_summary` asserts the artifact exists before Gateway cleanup at `tests/unit/scripts/test_transcript_parity_proof_launcher.py:450` through `tests/unit/scripts/test_transcript_parity_proof_launcher.py:493`. |
| Are previous tunnel/wrapper/cleanup/env/profile safeguards preserved? | Approved | Readyz/profile validation still precedes runtime mutation; HuleEdu commands still use `_huleedu_command_env(...)`; selected Skriptoteket mutation/restoration still uses `pdm run dev-stack recreate web worker`; cleanup still independently attempts HuleEdu restore, Skriptoteket restore, and owned tunnel stop. |
| Are docs/handoff truthful? | Approved with the redaction caveat above | The PR doc and handoff accurately describe the failure summary path and bounded/redacted intent, but the implementation must harden redaction before that guidance is safe. |

### Verification Evidence

| Command / check | Outcome |
|-----------------|---------|
| `pdm run test tests/unit/scripts/test_dev_stack.py tests/unit/scripts/test_transcript_parity_proof_launcher.py` | Passed: 19 tests. |
| `pdm run test tests/unit/scripts/test_transcript_parity_proof_launcher.py tests/unit/scripts/test_audio_transcription_parity_progress_snapshot.py tests/unit/scripts/test_audio_transcription_parity_summary_truthfulness.py tests/unit/scripts/test_sir_convert_trust_lane_preflight.py tests/unit/scripts/test_playwright_script_surface.py tests/unit/scripts/test_dev_stack.py` | Passed: 55 tests. |
| `pdm run docs-validate` | Passed. |
| `pdm run handoff-validate` | Passed. |
| `git diff --check` | Passed. |
| Code review of `scripts/transcript_parity_proof_launcher.py`, `tests/unit/scripts/test_transcript_parity_proof_launcher.py`, `.codex/handoff.md`, and `docs/backlog/prs/pr-0376-st-37-04-transcript-proof-lane-orchestration.md` | Changes requested: diagnostic artifact is present and bounded, but sensitive multi-token header/cookie output is not safely redacted. |

## Pass 8 Diagnostics Redaction Remediation Review

**Reviewer:** codex-independent-reviewer
**Date:** 2026-06-23
**Verdict:** approved

### Scope

This pass re-reviewed the remediation for the pass 7 high finding that common `Authorization: Bearer ...` and cookie-style child command output could leak trailing token material into `failure-summary.json`.

| File | Focus |
|------|-------|
| `scripts/transcript_parity_proof_launcher.py` | Sensitive child-output redaction, bounded snippets, failure-summary safety |
| `tests/unit/scripts/test_transcript_parity_proof_launcher.py` | Behavior proof that raw auth/cookie/bearer values are absent from metadata and failure summary |
| `docs/backlog/prs/pr-0376-st-37-04-transcript-proof-lane-orchestration.md` | Redaction remediation evidence and operator contract |
| `.codex/handoff.md` | Current launcher diagnostic guidance |

### Finding Resolution

| Previous finding | Resolution | Evidence |
|------------------|------------|----------|
| `high`: Authorization/cookie header redaction can leave the secret value in `failure-summary.json`. | Resolved. `SENSITIVE_HEADER_PATTERN` redacts full `Authorization`, `Proxy-Authorization`, `Cookie`, and `Set-Cookie` header lines; `BEARER_TOKEN_PATTERN` redacts free-text bearer token values before summary writing; existing secret assignment and environment-value redaction still runs. | `scripts/transcript_parity_proof_launcher.py:64` through `scripts/transcript_parity_proof_launcher.py:71`; `scripts/transcript_parity_proof_launcher.py:607` through `scripts/transcript_parity_proof_launcher.py:618` |
| Missing behavior proof for the unsafe header/token cases. | Resolved. The auth-check failure test injects fake API key, password, Authorization bearer token, Cookie, Set-Cookie, and free-text bearer values, then asserts those raw values are absent from both `LauncherError.metadata` snippets and `failure-summary.json` while useful non-secret context remains. | `tests/unit/scripts/test_transcript_parity_proof_launcher.py:94` through `tests/unit/scripts/test_transcript_parity_proof_launcher.py:110`; `tests/unit/scripts/test_transcript_parity_proof_launcher.py:454` through `tests/unit/scripts/test_transcript_parity_proof_launcher.py:507` |

### Review Questions

| Question | Decision | Evidence |
|----------|----------|----------|
| Does redaction cover full header values without leaving trailing token material? | Approved | Full sensitive header lines are replaced before snippets are persisted, and free-text `bearer <token>` values are reduced to `Bearer [REDACTED]`. |
| Are snippets still bounded and useful enough for HuleEdu auth-check debugging? | Approved | `_command_output_snippet(...)` still caps output at 800 characters and the test preserves non-secret context such as `auth integration preflight started` and `gateway check failed`. |
| Does failure summary remain safe? | Approved | The summary contains blocker code/message, sanitized metadata, descriptor/readyz truth, cleanup diagnostics, and notes; it does not dump env, secret values, media contents, or conversion payloads. |
| Are prior PR-0376 protections preserved? | Approved | The same focused suite still covers HuleEdu env sanitization, owned tunnel open/stop, selected-service `dev-stack recreate web worker`, independent cleanup, primary-error preservation, readyz/profile checks, and pre-upload runtime env checks. |
| Are docs/handoff truthful? | Approved | PR doc and handoff describe bounded/redacted failure summaries and the retained launcher path without adding manual fallback or operator-guess guidance. |

### Findings

None.

### Verification Evidence

| Command / check | Outcome |
|-----------------|---------|
| `pdm run test tests/unit/scripts/test_dev_stack.py tests/unit/scripts/test_transcript_parity_proof_launcher.py` | Passed: 19 tests. |
| `pdm run test tests/unit/scripts/test_transcript_parity_proof_launcher.py tests/unit/scripts/test_audio_transcription_parity_progress_snapshot.py tests/unit/scripts/test_audio_transcription_parity_summary_truthfulness.py tests/unit/scripts/test_sir_convert_trust_lane_preflight.py tests/unit/scripts/test_playwright_script_surface.py tests/unit/scripts/test_dev_stack.py` | Passed: 55 tests. |
| `pdm run docs-validate` | Passed. |
| `pdm run handoff-validate` | Passed. |
| `git diff --check` | Passed. |
| Code review of `scripts/transcript_parity_proof_launcher.py`, `tests/unit/scripts/test_transcript_parity_proof_launcher.py`, `.codex/handoff.md`, and `docs/backlog/prs/pr-0376-st-37-04-transcript-proof-lane-orchestration.md` | Passed: pass 7 redaction finding is resolved and previous diagnostics/proof-lane safeguards remain intact. |

## Pass 9 HuleEdu Auth Readiness Retry Review

**Reviewer:** codex-independent-reviewer
**Date:** 2026-06-23
**Verdict:** changes_requested

### Scope

This pass re-reviewed the readiness-race remediation after full launcher diagnostics showed HuleEdu `auth-integration check` timing out at `gateway-localhost-session` immediately after Gateway recreate, while the same lane passed once Gateway settled.

| File | Focus |
|------|-------|
| `scripts/transcript_parity_proof_launcher.py` | HuleEdu auth-check retry bounds, ordering before Skriptoteket mutation/proof, cleanup gating |
| `tests/unit/scripts/test_transcript_parity_proof_launcher.py` | Transient success and persistent failure behavior proof |
| `docs/backlog/prs/pr-0376-st-37-04-transcript-proof-lane-orchestration.md` | Retry contract and validation evidence |
| `.codex/handoff.md` | Current operator guidance for the launcher |

### Findings

#### High: Persistent HuleEdu auth failure still mutates Skriptoteket during cleanup

`scripts/transcript_parity_proof_launcher.py:169` sets the single `runtime_mutated` flag immediately before HuleEdu Gateway recreate, then `_wait_for_huleedu_auth_integration(...)` runs at `scripts/transcript_parity_proof_launcher.py:177` before the normal Skriptoteket proof-lane mutation at `scripts/transcript_parity_proof_launcher.py:190`. If the HuleEdu readiness wait fails persistently, the `finally` block passes `runtime_mutated=True` into `_cleanup_runtime_and_tunnel(...)` at `scripts/transcript_parity_proof_launcher.py:243` through `scripts/transcript_parity_proof_launcher.py:250`; `_cleanup_runtime_and_tunnel(...)` then unconditionally calls `_restore_skriptoteket_runtime_state(...)` at `scripts/transcript_parity_proof_launcher.py:420` through `scripts/transcript_parity_proof_launcher.py:435`, which runs `pdm run dev-stack recreate web worker` at `scripts/transcript_parity_proof_launcher.py:839` through `scripts/transcript_parity_proof_launcher.py:850`.

Why it matters: the readiness fix promises that persistent HuleEdu auth failure blocks before Skriptoteket runtime mutation and proof invocation. The main proof-lane mutation is blocked, but cleanup still recreates Skriptoteket `web`/`worker` even though this launcher run never changed them. That is still a runtime mutation, and it can churn the local product runtime after a pre-Skriptoteket failure.

The focused test misses this because `_skriptoteket_proof_lane_mutations(...)` at `tests/unit/scripts/test_transcript_parity_proof_launcher.py:259` through `tests/unit/scripts/test_transcript_parity_proof_launcher.py:265` filters for only `dev-stack recreate web worker` calls carrying the proof-lane producer overlay. `test_persistent_auth_integration_failure_blocks_before_skriptoteket_mutation` at `tests/unit/scripts/test_transcript_parity_proof_launcher.py:539` through `tests/unit/scripts/test_transcript_parity_proof_launcher.py:574` therefore passes even when the cleanup path issues a no-overlay Skriptoteket recreate.

Concrete fix: track HuleEdu Gateway mutation and Skriptoteket producer mutation independently. On persistent HuleEdu auth-check failure, restore HuleEdu Gateway and tear down any owned tunnel, but do not run Skriptoteket `dev-stack recreate web worker` unless the launcher actually recreated Skriptoteket with the proof-lane producer env. Keep independent cleanup attempts for paths where both runtimes were mutated.

Proof required: update the persistent auth-failure test to assert no `("pdm", "run", "dev-stack", "recreate", "web", "worker")` command at all after persistent pre-Skriptoteket auth failure, while still asserting HuleEdu restore and owned tunnel teardown when applicable. Add or keep a proof-failure test showing Skriptoteket restore still runs after Skriptoteket was actually mutated. Run `pdm run test tests/unit/scripts/test_dev_stack.py tests/unit/scripts/test_transcript_parity_proof_launcher.py` plus the combined proof-script suite, `pdm run docs-validate`, `pdm run handoff-validate`, and `git diff --check`.

### Approved Checks

| Review question | Result | Evidence |
|-----------------|--------|----------|
| Is the retry bounded and deterministic? | Approved | `HULEEDU_AUTH_CHECK_ATTEMPTS = 3`, retry delay `2.0`, HuleEdu check HTTP timeout `15`, and process timeout `30` are explicit constants; the loop sleeps only between failed attempts. |
| Does it use the existing named HuleEdu check surface? | Approved | `_huleedu_auth_integration_check_command(...)` builds `pdm run run-local-pdm auth-integration check --timeout-seconds 15`; no custom curl/readiness probe is introduced. |
| Does transient failure then success proceed without weakening prior protections? | Approved | The transient-success test exercises the launcher through `main(...)`, observes one retry, then continues to container env validation, Skriptoteket mutation, and proof invocation with the existing remote-proof lane values. |
| Are snippets and failure summary still safe? | Approved | Persistent failure still raises `huleedu_auth_integration_check_failed` and writes `failure-summary.json` with bounded/redacted child command metadata. |
| Are docs/handoff truthful? | Changes requested | They correctly describe the bounded named HuleEdu readiness wait, but the implementation does not yet satisfy the stronger “block before Skriptoteket runtime mutation” contract because cleanup still recreates Skriptoteket after a pre-Skriptoteket failure. |

### Verification Evidence

| Command / check | Outcome |
|-----------------|---------|
| `pdm run test tests/unit/scripts/test_dev_stack.py tests/unit/scripts/test_transcript_parity_proof_launcher.py` | Passed: 21 tests. |
| `pdm run test tests/unit/scripts/test_transcript_parity_proof_launcher.py tests/unit/scripts/test_audio_transcription_parity_progress_snapshot.py tests/unit/scripts/test_audio_transcription_parity_summary_truthfulness.py tests/unit/scripts/test_sir_convert_trust_lane_preflight.py tests/unit/scripts/test_playwright_script_surface.py tests/unit/scripts/test_dev_stack.py` | Passed: 57 tests. |
| `pdm run docs-validate` | Passed. |
| `pdm run handoff-validate` | Passed. |
| `git diff --check` | Passed. |
| Code review of `scripts/transcript_parity_proof_launcher.py`, `tests/unit/scripts/test_transcript_parity_proof_launcher.py`, `.codex/handoff.md`, and `docs/backlog/prs/pr-0376-st-37-04-transcript-proof-lane-orchestration.md` | Changes requested: retry is bounded and named-surface based, but cleanup still mutates Skriptoteket on persistent pre-Skriptoteket HuleEdu auth failure. |

## Pass 10 Independent Mutation-Tracking Remediation Review

**Reviewer:** codex-independent-reviewer
**Date:** 2026-06-23
**Verdict:** approved

### Scope

This pass re-reviewed the remediation for the pass 9 high finding that persistent HuleEdu auth-readiness failure could still recreate Skriptoteket during cleanup before Skriptoteket producer services had been proof-lane mutated.

| File | Focus |
|------|-------|
| `scripts/transcript_parity_proof_launcher.py` | Independent HuleEdu/Skriptoteket mutation tracking, cleanup gating, preserved tunnel/wrapper/diagnostic safeguards |
| `tests/unit/scripts/test_transcript_parity_proof_launcher.py` | Persistent pre-Skriptoteket auth failure, post-Skriptoteket cleanup, prior launcher behavior |
| `scripts/dev_stack.py` and `tests/unit/scripts/test_dev_stack.py` | Selected-service recreate wrapper remains available for actual Skriptoteket mutations/restores |
| `docs/backlog/prs/pr-0376-st-37-04-transcript-proof-lane-orchestration.md` | Updated cleanup and readiness contract |
| `.codex/handoff.md` | Current operator guidance |

### Finding Resolution

| Previous finding | Resolution | Evidence |
|------------------|------------|----------|
| `high`: persistent HuleEdu auth failure still mutates Skriptoteket during cleanup. | Resolved. The launcher now keeps `huleedu_gateway_mutated` and `skriptoteket_producer_mutated` as separate state, flips each immediately before its own recreate command, and passes both flags separately into cleanup. Cleanup restores HuleEdu only when HuleEdu was mutated, restores Skriptoteket only when the producer recreate was attempted, and still stops any owned tunnel independently. | `scripts/transcript_parity_proof_launcher.py:146` through `scripts/transcript_parity_proof_launcher.py:153`; `scripts/transcript_parity_proof_launcher.py:170` through `scripts/transcript_parity_proof_launcher.py:198`; `scripts/transcript_parity_proof_launcher.py:244` through `scripts/transcript_parity_proof_launcher.py:253`; `scripts/transcript_parity_proof_launcher.py:413` through `scripts/transcript_parity_proof_launcher.py:449` |
| Missing proof that pre-Skriptoteket auth failure does not issue a no-overlay Skriptoteket recreate. | Resolved. The persistent auth-failure test now asserts three bounded HuleEdu checks, no `pdm run dev-stack recreate web worker` command at all, no proof invocation, and a safe failure summary before cleanup. | `tests/unit/scripts/test_transcript_parity_proof_launcher.py:539` through `tests/unit/scripts/test_transcript_parity_proof_launcher.py:577` |

### Review Questions

| Question | Decision | Evidence |
|----------|----------|----------|
| Are HuleEdu and Skriptoteket mutation states tracked independently and set around actual mutation attempts? | Approved | Separate flags are initialized false and flipped immediately before the relevant recreate commands, which covers partial command failures without marking untouched downstream runtime as mutated. |
| Does pre-Skriptoteket failure avoid all Skriptoteket recreate/restore commands? | Approved | Persistent auth failure occurs before `skriptoteket_producer_mutated = True`, and the regression test asserts no `dev-stack recreate web worker` command appears anywhere in the recorded launcher commands. |
| Do post-Skriptoteket failures still restore both independently and stop an owned tunnel? | Approved | The proof-failure/HuleEdu-restore-failure regression still proves HuleEdu restore is attempted, Skriptoteket restore continues after that failure, and the owned SSH control-socket stop still runs. |
| Are bounded auth retry, safe failure summary/redaction, HuleEdu env sanitizer, selected-service wrapper, and profile/runtime checks preserved? | Approved | The code still validates readyz/profile before mutation, uses the named HuleEdu `auth-integration check --timeout-seconds 15` retry, sanitizes HuleEdu command env only, uses `pdm run dev-stack recreate web worker` for Skriptoteket mutation/restore, and writes bounded/redacted diagnostics without env dumps or payloads. |
| Are tests behavior-focused and docs/handoff truthful? | Approved | Tests exercise `main(...)` through command recording rather than helper-call-only assertions. The PR doc and handoff now state that persistent auth failure restores HuleEdu and any owned tunnel without running Skriptoteket restore before Skriptoteket was actually mutated. |

### Findings

None.

### Verification Evidence

| Command / check | Outcome |
|-----------------|---------|
| `pdm run test tests/unit/scripts/test_dev_stack.py tests/unit/scripts/test_transcript_parity_proof_launcher.py` | Passed: 21 tests. |
| `pdm run test tests/unit/scripts/test_transcript_parity_proof_launcher.py tests/unit/scripts/test_audio_transcription_parity_progress_snapshot.py tests/unit/scripts/test_audio_transcription_parity_summary_truthfulness.py tests/unit/scripts/test_sir_convert_trust_lane_preflight.py tests/unit/scripts/test_playwright_script_surface.py tests/unit/scripts/test_dev_stack.py` | Passed: 57 tests. |
| `pdm run docs-validate` | Passed. |
| `pdm run handoff-validate` | Passed. |
| `git diff --check` | Passed. |
| Code review of `scripts/transcript_parity_proof_launcher.py`, `tests/unit/scripts/test_transcript_parity_proof_launcher.py`, `docs/backlog/prs/pr-0376-st-37-04-transcript-proof-lane-orchestration.md`, and `.codex/handoff.md` | Passed: the pass 9 independent mutation-tracking gap is resolved and previous PR-0376 safeguards remain intact. |

## Pass 11 Docker Exec Command-Shape Review

**Reviewer:** codex-independent-reviewer
**Date:** 2026-06-23
**Verdict:** approved

### Scope

This pass re-reviewed the remediation after the full launcher failure summary showed `docker exec -T ...` failing with `unknown shorthand flag: 'T' in -T`.

| File | Focus |
|------|-------|
| `scripts/transcript_parity_proof_launcher.py` | Runtime env inspection command shape and fail-closed pre-upload behavior |
| `tests/unit/scripts/test_transcript_parity_proof_launcher.py` | Gateway/web/worker Docker exec command-shape regression proof |
| `docs/backlog/prs/pr-0376-st-37-04-transcript-proof-lane-orchestration.md` | Red/green evidence for portable runtime env inspection |
| `.codex/handoff.md` | Current launcher/operator guidance |

### Review Questions

| Question | Decision | Evidence |
|----------|----------|----------|
| Is the env inspection command valid and non-interactive enough for Docker CLI here? | Approved | `_assert_container_env(...)` now runs `("docker", "exec", container_name, "printenv", key)` with no `-i`, no `-t`, and no Compose-only `-T`. Docker CLI `exec` without stdin/TTY flags is non-interactive and suitable for `printenv` checks. |
| Does the test cover all three runtime env inspections and prevent `-T` regression? | Approved | `test_runtime_env_inspection_uses_portable_docker_exec_shape` executes `main(...)` and asserts the exact Gateway, Skriptoteket web, and Skriptoteket worker inspection commands; any reintroduced `-T` would change the command tuple and fail the test. |
| Are previous readiness/tunnel/env-sanitizer/cleanup/failure-summary protections preserved? | Approved | The focused launcher suite still covers owned tunnel open/stop, reachable-readyz no-op behavior, bounded named HuleEdu auth retry, HuleEdu env sanitization, independent mutation cleanup, safe failure-summary redaction, and fail-closed runtime mismatch before proof invocation. |
| Are docs/handoff truthful? | Approved | The PR doc records red/green evidence for the portable Docker exec shape, and handoff remains accurate for the launcher workflow without adding manual fallback guidance. |

### Findings

None.

### Verification Evidence

| Command / check | Outcome |
|-----------------|---------|
| `pdm run test tests/unit/scripts/test_dev_stack.py tests/unit/scripts/test_transcript_parity_proof_launcher.py` | Passed: 22 tests. |
| `pdm run test tests/unit/scripts/test_transcript_parity_proof_launcher.py tests/unit/scripts/test_audio_transcription_parity_progress_snapshot.py tests/unit/scripts/test_audio_transcription_parity_summary_truthfulness.py tests/unit/scripts/test_sir_convert_trust_lane_preflight.py tests/unit/scripts/test_playwright_script_surface.py tests/unit/scripts/test_dev_stack.py` | Passed: 58 tests. |
| `pdm run docs-validate` | Passed. |
| `pdm run handoff-validate` | Passed. |
| `git diff --check` | Passed. |
| Code review of `scripts/transcript_parity_proof_launcher.py`, `tests/unit/scripts/test_transcript_parity_proof_launcher.py`, `docs/backlog/prs/pr-0376-st-37-04-transcript-proof-lane-orchestration.md`, and `.codex/handoff.md` | Passed: runtime env inspection no longer uses the invalid `docker exec -T` shape, all three env inspections are covered, and prior PR-0376 safeguards remain intact. |

## Verification Evidence

| Command / check | Outcome |
|-----------------|---------|
| `pdm run test tests/unit/scripts/test_transcript_parity_proof_launcher.py tests/unit/scripts/test_audio_transcription_parity_summary_truthfulness.py tests/unit/scripts/test_sir_convert_trust_lane_preflight.py tests/unit/scripts/test_audio_transcription_parity_progress_snapshot.py tests/unit/scripts/test_playwright_script_surface.py` | Passed: 43 tests. |
| Code review of `scripts/transcript_parity_proof_launcher.py` | Passed: mutable proof-lane runtime now restores in `finally` after proof success/failure. |
| `rg -n "pr_0349\|playwright_pr_0349\|proof_kind" scripts/audio_transcription_parity_live.py scripts/_sir_convert_trust_lane_preflight.py tests/unit/scripts/test_audio_transcription_parity_summary_truthfulness.py tests/unit/scripts/test_sir_convert_trust_lane_preflight.py -S` | Passed for PR-0376 scope; active proof metadata is now domain-owned for the shared transcript proof. |

`pdm run docs-validate`, `pdm run handoff-validate`, and `git diff --check` are recorded in final close-out for this pass.

## Changes Made

| Change | Artifact | Description |
|--------|----------|-------------|
| 1 | `REV-PR-0376` | Created retained pass-2 review record and approved the implementation after the runtime-restore finding was resolved. |
