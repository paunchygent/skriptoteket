---
type: pr
id: PR-0376
title: "ST-37-04 transcript proof lane orchestration"
status: done
owners: "agents"
created: 2026-06-23
updated: 2026-06-23
stories:
  - "ST-37-04"
tags:
  - testing
  - playwright
  - auth-edge
  - sir-convert
dependencies:
  - "PR-0368"
  - "PR-0374"
  - "PR-0375"
  - "PR-0352"
  - "REF-pr-0368-auth-edge-inventory-and-proof-plan"
acceptance_criteria:
  - "Given the Audio Transcription live proof depends on HuleEdu Gateway, Skriptoteket Docker backend, Sir Convert remote-proof, and local SSH tunnel state, when an operator runs the proof, then one committed launcher prepares and validates the chosen proof lane before Playwright or media upload starts."
  - "Given `8085`, `28085`, and `38085` have different meanings, when a proof lane is selected, then the launcher validates the expected Sir Convert service profile, Gateway backend URL, Skriptoteket producer URL, and signer/verifier fingerprints from runtime truth rather than relying on copied command arguments."
  - "Given local/downstream STT proof must use the fenced Sir Convert `remote-proof` lane, when the retained transcript parity proof runs locally, then it targets `host.docker.internal:38085`, observes `service_profile=remote-proof`, and rejects production or container-internal lanes before upload."
  - "Given the HuleEdu browser-session ceremony is fragile, when lane orchestration is added, then it preserves the shared-auth Docker service lane and does not introduce direct cookie auth, credential POST shortcuts, browser-authored identity headers, browser-direct Sir Convert calls, or browser-held Sir Convert credentials."
---

# PR-0376: ST-37-04 Transcript Proof Lane Orchestration

## Problem

The retained Audio Transcription parity proof is truthful only when several
cross-repo runtime facts agree: HuleEdu Gateway must proxy to the selected Sir
Convert lane, Skriptoteket Docker `web` and `worker` must produce against the
same lane, the local SSH tunnel must expose the expected Hemma service, and Sir
Convert must trust the Gateway signer.

Today those facts can drift independently. The proof script can be given
`--sir-convert-gateway-backend-url`, while the already-running Gateway
container still points at another backend. Operators then have to remember
which port is container-internal, production tunnel, or fenced remote-proof.
That is not durable enough for auth-edge work.

## Goal

Create a committed, lane-aware proof launcher for the retained transcript
parity proof. The launcher must make lane preparation and runtime validation
executable, typed, and fail-closed before any browser proof or media upload can
begin.

## Non-goals

- No Audio Transcription product UI or app workflow change.
- No Document Converter implementation or route activation.
- No Sir Convert production deploy, trust-key rotation, public ingress change,
  proxy timeout change, or remote-proof service topology change.
- No HuleEdu shared-auth ceremony redesign.
- No hidden compatibility fallback from `remote-proof` to production.
- No permanent mutation of local `.env` files or committed secret material.

## Review gate

`REV-PR-0376` must approve the implementation before this slice is closed.

## Implementation plan

1. Add a lane descriptor surface for the retained transcript proof. At minimum,
   it must define the local/downstream `remote-proof` lane with:
   `proof_lane=hemma-remote-proof`, local tunnel port `38085`, container target
   `http://host.docker.internal:38085`, expected Sir Convert service profile
   `remote-proof`, and the existing shared-auth base URL.
2. Add a committed launcher command that:
   - verifies or opens the required SSH tunnel;
   - checks Sir Convert `/readyz` for the expected profile/revision readiness;
   - creates temporary HuleEdu env overlay state for the selected Gateway
     backend;
   - force-recreates only HuleEdu `api_gateway_service` with the overlay;
   - runs HuleEdu `auth-integration check` as a bounded readiness wait;
   - force-recreates only Skriptoteket `web` and `worker` with the matching
     producer URL;
   - verifies the running container env for Gateway and Skriptoteket;
   - runs `scripts.audio_transcription_parity_live` with descriptor
     values, not operator-copied values; and
   - restores containers and stops any tunnel it opened.
3. Keep the existing proof script fail-closed behavior. Strengthen it only
   where needed so a mismatch between declared lane and running runtime cannot
   produce a false green.
4. Add focused red-first tests around launcher/descriptor behavior:
   wrong Gateway port, wrong Skriptoteket producer port, wrong service profile,
   missing tunnel/ready endpoint, and forbidden `8085` local proof target.
5. Update docs and handoff with the new command and the retained
   `20260623T034207Z` proof result as evidence that the remote-proof lane is
   the correct target for local/downstream STT parity proof.

## Test plan

- Red first:
  focused tests for the launcher/descriptor failure matrix must fail before the
  production implementation.
- Green:
  the same focused test command must pass after implementation.
- Script surface:
  `pdm run test tests/unit/scripts/test_playwright_script_surface.py`
- Auth lane proof after implementation:
  `pdm run run-local-pdm auth-integration check` from the HuleEdu repo, then
  the committed launcher command from Skriptoteket.
- Docs/handoff:
  `pdm run docs-validate`
  `pdm run handoff-validate`
  `git diff --check`

## Implementation summary

- Added the committed launcher command:
  `pdm run transcript-parity-proof remote-proof`.
- The `remote-proof` descriptor pins the local proof lane to:
  `proof_lane=hemma-remote-proof`, local tunnel port `38085`,
  container target `http://host.docker.internal:38085`, ready URL
  `http://127.0.0.1:38085/readyz`, expected service profile `remote-proof`,
  and default base URL `http://127.0.0.1:5173`.
- The launcher fails before Playwright or media upload when Sir Convert
  `/readyz` reports the wrong service profile, when a forbidden local
  `host.docker.internal:8085` target is selected, or when the running HuleEdu
  Gateway / Skriptoteket `web` / Skriptoteket `worker` container environment
  does not match the descriptor target.
- The retained proof invocation is built from descriptor values and calls
  `scripts.audio_transcription_parity_live` with the resolved
  Gateway signer fingerprint from HuleEdu's local trust-profile command.
- Temporary runtime overlay files are written only under
  `.artifacts/transcript-parity-proof-lane/<timestamp>/` and contain only
  non-secret lane URLs/flags.
- The Playwright proof writes new retained evidence under
  `.artifacts/audio-transcription-parity-live/<timestamp>/`.
- Review-fix pass added an explicit restore path around mutable runtime
  orchestration. After HuleEdu Gateway and Skriptoteket web/worker are recreated
  with proof-lane overlays, the launcher always recreates HuleEdu
  `api_gateway_service` and Skriptoteket `web`/`worker` again without the
  proof-lane overlay keys, including when the long Playwright proof fails.
- Follow-up review-fix pass made the `remote-proof` lane self-contained for the
  local operator. When `http://127.0.0.1:38085/readyz` is initially unreachable,
  the launcher opens an owned SSH control-socket tunnel with
  `ssh -M -S <run-dir>/remote-proof-ssh.sock -fnNT -o ExitOnForwardFailure=yes -L 38085:127.0.0.1:38085 hemma`,
  retries `/readyz`, and later stops only that control-socket tunnel. When the
  endpoint is already reachable, the launcher does not open or stop any tunnel.
- Follow-up review-fix pass made selected-service recreate a supported
  Skriptoteket command surface. The launcher uses
  `pdm run dev-stack recreate web worker` to mutate and restore only the
  Skriptoteket `web` and `worker` services with the proof-lane environment.
  Cleanup failures no longer mask an earlier proof or mutation failure; they
  are attached as cleanup diagnostics while the launcher still independently
  attempts HuleEdu Gateway restore, Skriptoteket `web`/`worker` restore when
  the producer services were actually sent through proof-lane recreate, and
  owned tunnel teardown.
- Follow-up review-fix pass added a HuleEdu-only cross-repo command
  environment sanitizer. HuleEdu `pdm run run-local-pdm ...` commands keep
  operator environment and proof-lane Gateway overlay values, but do not inherit
  Skriptoteket PDM project markers, virtualenv markers, `PYTHONPATH`, or the
  current Skriptoteket `.venv/bin` PATH entry.
- Follow-up review-fix pass made the post-recreate HuleEdu auth check a
  bounded readiness wait. After recreating Gateway with proof-lane env, the
  launcher invokes
  `pdm run run-local-pdm auth-integration check --timeout-seconds 15` up to
  three times with a short retry delay before mutating Skriptoteket `web` /
  `worker` or invoking the proof. Persistent failure still fails closed and
  writes the safe failure summary while restoring only the HuleEdu Gateway
  overlay and any owned tunnel.
- Follow-up review-fix pass added safe launcher failure diagnostics. Failed
  child commands now carry bounded, redacted stdout/stderr snippets in
  `LauncherError.metadata`, and the launcher writes
  `.artifacts/transcript-parity-proof-lane/<timestamp>/failure-summary.json`
  with blocker code, safe metadata, descriptor/readyz truth, and cleanup
  diagnostics when available. Redaction covers secret-style assignments,
  bearer-token forms, and sensitive header lists such as `Authorization`,
  `Cookie`, and `Set-Cookie`.

## Validation

- Red first:
  `pdm run test tests/unit/scripts/test_pr_0376_transcript_proof_launcher.py`
  failed before implementation with `ModuleNotFoundError` for the missing
  launcher module.
- Focused green:
  `pdm run test tests/unit/scripts/test_transcript_parity_proof_launcher.py`
  after implementation.
- Review-fix red first:
  `pdm run test tests/unit/scripts/test_transcript_parity_proof_launcher.py -k "runtime_state_is_restored"`
  failed with missing restore commands after both successful proof invocation
  and proof failure.
- Review-fix green:
  `pdm run test tests/unit/scripts/test_transcript_parity_proof_launcher.py`
  passed with 7 tests.
- Tunnel review-fix red first:
  `pdm run test tests/unit/scripts/test_transcript_parity_proof_launcher.py -k "readyz"`
  failed before the tunnel implementation with 2 failures: the launcher raised
  `sir_convert_readyz_unreachable` without opening the tunnel, and the
  profile-mismatch-after-open path never reached profile validation.
- Tunnel review-fix green:
  `pdm run test tests/unit/scripts/test_transcript_parity_proof_launcher.py -k "readyz"`
  passed with 3 tests, and
  `pdm run test tests/unit/scripts/test_transcript_parity_proof_launcher.py`
  passed with 10 tests.
- Cleanup-order red first:
  `pdm run test tests/unit/scripts/test_transcript_parity_proof_launcher.py -k "opened_tunnel_is_stopped_when_runtime_restore_fails"`
  failed because a Gateway restore failure prevented the launcher-owned SSH
  tunnel stop command from running.
- Cleanup-order green:
  `pdm run test tests/unit/scripts/test_transcript_parity_proof_launcher.py -k "opened_tunnel_is_stopped_when_runtime_restore_fails"`
  passed, and the full launcher suite now passes with 11 tests.
- Selected-service recreate red first:
  `pdm run test tests/unit/scripts/test_dev_stack.py tests/unit/scripts/test_transcript_parity_proof_launcher.py -k "recreate_can_target_specific_services_without_db_upgrade or cleanup_error_does_not_mask_primary_proof_failure"`
  failed with 2 failures: `dev-stack recreate web worker` returned exit code
  2 with `recreate does not accept extra arguments`, and a cleanup restore
  failure masked the primary `transcript_parity_proof_failed` error.
- Selected-service recreate green:
  The same focused command passed with 2 tests after `dev-stack recreate`
  accepted selected service names and the launcher preserved the primary
  failure while noting cleanup failure.
- Independent restore red first:
  `pdm run test tests/unit/scripts/test_transcript_parity_proof_launcher.py -k "cleanup_restores_skriptoteket_after_huleedu_restore_failure"`
  failed because a HuleEdu Gateway restore failure skipped the Skriptoteket
  `pdm run dev-stack recreate web worker` restore and went straight to tunnel
  teardown.
- Independent restore green:
  The same focused command passed after cleanup split HuleEdu Gateway restore,
  Skriptoteket `web`/`worker` restore, and owned tunnel teardown into
  independently attempted steps.
- HuleEdu env-sanitizer red first:
  `pdm run test tests/unit/scripts/test_transcript_parity_proof_launcher.py -k "huleedu_commands_use_cross_repo_sanitized_environment"`
  failed because HuleEdu commands inherited Skriptoteket PDM project markers,
  virtualenv markers, `PYTHONPATH`, and a current-repo `.venv/bin` PATH entry.
- HuleEdu env-sanitizer green:
  The same focused command passed after HuleEdu trust-profile, Gateway
  recreate, auth-integration check, and Gateway restore commands switched to
  the sanitized cross-repo environment while preserving proof-lane overlay
  values.
- Failure-summary red first:
  `pdm run test tests/unit/scripts/test_transcript_parity_proof_launcher.py -k "auth_integration_failure_writes_safe_failure_summary"`
  failed because failed child command metadata did not include stdout/stderr
  snippets and no run-dir failure summary artifact existed before cleanup.
- Failure-summary green:
  The same focused command passed after bounded/redacted child command snippets
  and `failure-summary.json` were added.
- Failure-summary redaction red first:
  `pdm run test tests/unit/scripts/test_transcript_parity_proof_launcher.py -k "auth_integration_failure_writes_safe_failure_summary"`
  failed after the test included fake bearer and cookie header values because
  multi-token secret values were still present in diagnostic snippets.
- Failure-summary redaction green:
  The same focused command passed after full sensitive headers and bearer-token
  values were redacted from both `LauncherError.metadata` and
  `failure-summary.json`.
- HuleEdu auth readiness red first:
  `pdm run test tests/unit/scripts/test_transcript_parity_proof_launcher.py -k "auth_integration_check_retries_gateway_settle_and_then_proceeds or persistent_auth_integration_failure_blocks_before_skriptoteket_mutation"`
  failed because the launcher treated the first post-recreate
  `auth-integration check` timeout as terminal and persistent failure attempted
  only one check.
- HuleEdu auth readiness green:
  The same focused command passed after the launcher retried the named
  HuleEdu auth check with a bounded `--timeout-seconds 15` readiness wait and
  continued to fail closed before Skriptoteket proof-lane mutation on
  persistent failure.
- Independent mutation cleanup red first:
  `pdm run test tests/unit/scripts/test_transcript_parity_proof_launcher.py -k "persistent_auth_integration_failure_blocks_before_skriptoteket_mutation"`
  failed because persistent HuleEdu auth failure still ran
  `pdm run dev-stack recreate web worker` during cleanup even though
  Skriptoteket producer services had not been proof-lane mutated.
- Independent mutation cleanup green:
  The same focused command passed after HuleEdu Gateway mutation and
  Skriptoteket producer mutation were tracked separately.
- Runtime env inspection command red first:
  `pdm run test tests/unit/scripts/test_transcript_parity_proof_launcher.py -k "runtime_env_inspection_uses_portable_docker_exec_shape"`
  failed because Gateway, Skriptoteket web, and Skriptoteket worker env
  inspection used `docker exec -T ...`, which is not a portable `docker exec`
  command shape.
- Runtime env inspection command green:
  The same focused command passed after runtime env inspection switched to
  `docker exec <container> printenv <key>` for Gateway, web, and worker.

## Stop conditions

Stop before any change that requires rotating HuleEdu/Sir Convert keys,
changing Sir Convert production or remote-proof compose topology, altering
public ingress/proxy timeout policy, adding browser-held Sir Convert
credentials, or replacing the HuleEdu browser-session ceremony.

Stop and split the work if HuleEdu needs a first-class reusable env-overlay
command or if Sir Convert needs a first-class remote-proof tunnel manager; those
belong in their owning repos with separate authority.

## Rollback plan

Remove the launcher/descriptor changes and retain the existing
`scripts.audio_transcription_parity_live` proof script. Keep the
documented manual remote-proof command only as emergency diagnostic guidance,
not as the normal close-out proof path.
