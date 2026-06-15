---
type: review
id: REV-PR-0352
title: "Review: PR-0352 remote inference live-proof trust-lane preflight"
status: approved
owners: "agents"
created: 2026-06-14
updated: 2026-06-15
reviewer: "ruthless-review-subagent"
prs:
  - PR-0352
links:
  - ST-21-09
  - EPIC-21
  - docs/backlog/reviews/review-pr-0351-transcript-completion-progress-and-export-ux.md
---

## TL;DR

Approved on the latest 2026-06-15 re-review. The scoped working tree now
governs the new native progress semantics, the focused snapshot tests are
typed without escapes, and the PR-0354 validation timeline is split cleanly
between the 2026-06-14 closeout bundle and the 2026-06-15 follow-up script
regression lane.

## Problem Statement

The review must verify that the recurring local HuleEdu Gateway to Sir Convert
internal identity mismatch is now blocked by tooling, not remembered as
session guidance. The task must keep Sir Convert's hosted model/runtime estate
remote by default while preventing incoherent local-signer to Hemma-verifier
lanes from running silently.

## Proposed Solution

Add a browser-free preflight helper used by the PR-0349/PR-0351 transcript live
proof. The helper validates public lane metadata before source media is copied
or Playwright is launched. Production/Hemma remote proof is allowed; mixed
local-Gateway to Hemma-Sir-Convert tunnel use requires explicit opt-in and
matching public signer/verifier fingerprints.

## Artifacts to Review

| File | Focus | Time |
|------|-------|------|
| `docs/backlog/prs/pr-0352-st-21-09-remote-inference-live-proof-trust-lane-preflight.md` | Scope, acceptance, evidence | 10 min |
| `docs/backlog/stories/story-21-09-conversion-hub-remote-inference-proof-trust-lane.md` | Parent story and hosted runtime boundary | 5 min |
| `scripts/_sir_convert_trust_lane_preflight.py` | Preflight semantics, redaction, typing, maintainability | 25 min |
| `scripts/playwright_pr_0349_transcript_parity_live.py` | Hook placement before media copy/job submit | 15 min |
| `tests/unit/scripts/test_sir_convert_trust_lane_preflight.py` | Behavioral proof and redaction coverage | 15 min |
| Adjacent script tests and validators | Regression proof | 10 min |

**Total estimated time:** ~80 minutes

## Key Decisions

| Decision | Rationale | Approve? |
|----------|-----------|----------|
| Preflight before media copy | Proves the blocker happens before upload/job creation. | [x] |
| Remote hosted runtime remains default | Avoids making local model/runtime hosting a prerequisite. | [x] |
| Mixed tunnel requires opt-in plus fingerprint agreement | Keeps debugging possible without silent incoherent defaults. | [x] |
| Failure summaries are redacted public metadata only | Retained artifacts must not leak secrets, transcript text, or media content. | [x] |

## Review Checklist

- [x] Governing docs-as-code authority is valid and current.
- [x] Preflight blocks local-signer to Hemma-verifier mismatch before upload.
- [x] Production/Hemma remote proof remains usable.
- [x] Mixed tunnel debug mode cannot run without explicit opt-in.
- [x] Public fingerprint checks are strict and fail closed.
- [x] No local model/runtime hosting or remote signing-secret copy path was added.
- [x] Proof summaries do not expose private keys, tokens, cookies, passwords,
  transcript text, or media content.
- [x] Tests prove behavior at the script/helper boundary without brittle
  implementation-only assertions.
- [x] Python files remain within repo line budgets and pass lint/typecheck.

## Review Feedback

**Reviewer:** @ruthless-review-subagent
**Date:** 2026-06-14
**Verdict:** approved

### Monitoring Delta Review - 2026-06-15

Decision: `approved`.

Scope:

- `scripts/_proof_live_monitoring.py`
- `scripts/_transcript_parity_evidence.py`
- `scripts/playwright_pr_0349_transcript_parity_live.py`
- `tests/unit/scripts/test_proof_live_monitoring.py`
- `tests/unit/scripts/test_playwright_pr_0349_summary_truthfulness.py`
- `docs/backlog/prs/pr-0352-st-21-09-remote-inference-live-proof-trust-lane-preflight.md`
- `docs/backlog/prs/pr-0354-st-21-08-transcript-export-selector-and-responsive-layout-remediation.md`
- `.codex/handoff.md`

No findings.

Verified in this pass:

- Native Hemma monitoring stays inside the governed `PR-0352` / `ST-21-09`
  proof lane and does not change the proof command's public contract beyond
  adding retained evidence artifacts.
- The new capture helper retains bounded Docker state plus per-service logs
  without reintroducing container environment retention.
- Proof-summary truthfulness remains aligned with the retained artifact lane:
  `service-monitoring.json` and `service-logs/*.log` are surfaced when present,
  while the existing redacted network/console summary behavior is unchanged.
- Focused tests cover the safe Docker-state snapshot and the proof-summary
  artifact listing for native service monitoring.

Residual validation gap:

- This review did not include a fresh native Hemma rerun; it validates the
  uncommitted monitoring delta, docs authority, and focused automated evidence
  only.

Validation rerun for this monitoring review:

```bash
pdm run test tests/unit/scripts/test_proof_live_monitoring.py tests/unit/scripts/test_playwright_pr_0349_summary_truthfulness.py
pdm run python -m py_compile scripts/_proof_live_monitoring.py scripts/_transcript_parity_evidence.py scripts/playwright_pr_0349_transcript_parity_live.py
```

Results: 7 passed and `py_compile` passed.

### Current Review Pass - 2026-06-15

Decision: `changes_requested`.

Scope: uncommitted delta limited to
`scripts/playwright_pr_0349_transcript_parity_live.py`.

#### Findings

1. `blocker` `scripts/playwright_pr_0349_transcript_parity_live.py:145`

   What is wrong:
   The patch changes the accepted transcript-proof contract from the previous
   raw-counter snapshot to a new shape: phase text plus workflow
   steps/current-step, optional upload percent/bytes, and
   `terminal_reached_before_snapshot=true` as an allowed fast-completion case.
   The working tree does not amend the governing docs surfaces that own those
   proof semantics: `PR-0354` for the progress contract, `PR-0352` for the
   native proof lane, and `.codex/handoff.md` for current-state guidance.

   Why it matters:
   This repo requires docs-as-code authority before implementation, especially
   when a retained proof script changes what counts as passing evidence. Without
   a governed amendment, future agents will keep reading the closed PR-0352 /
   PR-0354 records as if native proof still required the removed raw fields and
   did not allow terminal-before-snapshot fast completion.

   Concrete fix:
   Amend the relevant governed docs to record the 2026-06-15 native Hemma proof
   failure, the current honest progress contract, and the explicit
   fast-completion allowance. At minimum, update `PR-0354`, `REV-PR-0352`, and
   `.codex/handoff.md`, then rerun the repo validators.

   Proof requirement:
   `pdm run docs-validate`
   `pdm run handoff-validate`
   `git diff --check`

2. `medium` `scripts/playwright_pr_0349_transcript_parity_live.py:145`

   What is wrong:
   There is still no focused regression test for `_capture_progress_snapshot`
   covering the three cases this patch now depends on:
   current job with phase + steps/current-step, upload-owned percent/bytes
   before job handoff, and terminal-before-snapshot fast completion.

   Why it matters:
   This exact proof drift already escaped until a native Hemma run failed. With
   no boundary test on the snapshot classifier, the next selector or truthfulness
   drift will again only surface in an expensive live proof lane.

   Concrete fix:
   Add a focused `tests/unit/scripts/` module for this function. If direct
   Playwright fakes are awkward, extract the snapshot acceptance predicate into
   a small pure helper and test that helper instead of relying only on live
   browser proof.

   Proof requirement:
   `pdm run test tests/unit/scripts/test_playwright_pr_0349_progress_snapshot.py tests/unit/scripts/test_playwright_pr_0349_summary_truthfulness.py`
   `pdm run python -m py_compile scripts/playwright_pr_0349_transcript_parity_live.py`

Validation rerun for this review:

```bash
pdm run test tests/unit/scripts/test_playwright_pr_0349_summary_truthfulness.py tests/unit/scripts/test_sir_convert_trust_lane_preflight.py
pdm run fe-test -- --run frontend/apps/skriptoteket/src/views/apps/conversion-hub-transcript/TranscriptWorkspaceShell.spec.ts frontend/apps/skriptoteket/src/views/apps/conversion-hub-transcript/TranscriptWorkspaceShell.pr0351.spec.ts
pdm run python -m py_compile scripts/playwright_pr_0349_transcript_parity_live.py
```

Results: 25 passed, 12 passed, and `py_compile` passed. No focused
`_capture_progress_snapshot` test exists yet.

#### Resolution Applied Before Re-Review

- `PR-0354` now governs the native transcript proof's honest progress snapshot:
  phase + workflow steps/current-step after job handoff, upload percent/bytes
  only while the browser owns upload, and `terminal_reached_before_snapshot=true`
  for fast completion.
- `PR-0354` splits the original 2026-06-14 remediation validation from the
  2026-06-15 proof-script regression validation.
- `.codex/handoff.md` records the 2026-06-15 native Hemma failure at
  `/home/paunchygent/apps/skriptoteket/.artifacts/playwright-pr-0352-transcript-parity-native/20260615T155823Z/proof-summary.json`
  and the pending rerun sequence.
- `tests/unit/scripts/test_playwright_pr_0349_progress_snapshot.py` covers
  job-owned progress, upload-owned progress, no-evidence rejection, and
  terminal-before-snapshot fast completion.
- `_capture_progress_snapshot` now accepts a small page/locator protocol, so the
  focused test uses a typed fake without `type: ignore`.

Validation before re-review:

```bash
pdm run test tests/unit/scripts/test_playwright_pr_0349_progress_snapshot.py tests/unit/scripts/test_playwright_pr_0349_summary_truthfulness.py
pdm run python -m py_compile scripts/playwright_pr_0349_transcript_parity_live.py
```

Results: 10 passed and `py_compile` passed.

### Follow-Up Re-Review - 2026-06-15

Decision: `changes_requested`.

Scope:

- `scripts/playwright_pr_0349_transcript_parity_live.py`
- `tests/unit/scripts/test_playwright_pr_0349_progress_snapshot.py`
- `docs/backlog/prs/pr-0354-st-21-08-transcript-export-selector-and-responsive-layout-remediation.md`
- `docs/backlog/reviews/review-pr-0352-remote-inference-live-proof-trust-lane-preflight.md`
- `.codex/handoff.md`

#### Findings

1. `medium` `tests/unit/scripts/test_playwright_pr_0349_progress_snapshot.py:126`

   What is wrong:
   The new focused regression lane still suppresses the script boundary's type
   contract with `# type: ignore[arg-type]` when calling
   `_capture_progress_snapshot`.

   Why it matters:
   This repo's review standard forbids `type: ignore` escapes because they hide
   interface drift. Here the test is meant to protect a proof-critical boundary,
   so bypassing the `Page` contract weakens the exact surface we want the test
   to keep honest.

   Concrete fix:
   Remove the ignore by typing the capture helper against a small protocol that
   covers the methods it actually uses, or extract the terminal-fast-completion
   branch into a pure/helper seam that the fake page can satisfy without a type
   escape.

   Proof requirement:
   `pdm run test tests/unit/scripts/test_playwright_pr_0349_progress_snapshot.py tests/unit/scripts/test_playwright_pr_0349_summary_truthfulness.py`
   `pdm run python -m py_compile scripts/playwright_pr_0349_transcript_parity_live.py`

2. `low` `docs/backlog/prs/pr-0354-st-21-08-transcript-export-selector-and-responsive-layout-remediation.md:206`

   What is wrong:
   The PR doc now adds the new focused script-regression command to the test
   plan, but still says "All listed commands passed on 2026-06-14." That is no
   longer strictly true because this specific command was added and run as a
   2026-06-15 follow-up after the failed native Hemma proof.

   Why it matters:
   Retained proof docs are supposed to be audit-grade. Blending the original
   2026-06-14 closeout bundle with the 2026-06-15 follow-up regression lane
   makes the validation timeline less trustworthy than it should be.

   Concrete fix:
   Split the original 2026-06-14 closeout commands from the 2026-06-15 follow-up
   proof-script validation, or revise the sentence so it names which commands
   passed on which date.

   Proof requirement:
   `pdm run docs-validate`

Validation rerun for this re-review:

```bash
pdm run test tests/unit/scripts/test_playwright_pr_0349_progress_snapshot.py tests/unit/scripts/test_playwright_pr_0349_summary_truthfulness.py
pdm run python -m py_compile scripts/playwright_pr_0349_transcript_parity_live.py
pdm run docs-validate
pdm run handoff-validate
git diff --check
```

Results: 10 passed, `py_compile` passed, `docs-validate` passed,
`handoff-validate` passed, and `git diff --check` passed.

### Final Re-Review - 2026-06-15

Decision: `approved`.

Scope:

- `scripts/playwright_pr_0349_transcript_parity_live.py`
- `tests/unit/scripts/test_playwright_pr_0349_progress_snapshot.py`
- `docs/backlog/prs/pr-0354-st-21-08-transcript-export-selector-and-responsive-layout-remediation.md`
- `docs/backlog/reviews/review-pr-0352-remote-inference-live-proof-trust-lane-preflight.md`
- `.codex/handoff.md`

No findings.

Resolved since the previous pass:

- `_capture_progress_snapshot` now uses the small
  `_ProgressSnapshotPage` / `_ProgressSnapshotLocator` protocol seam, so the
  focused fake-page regression test is fully typed with no `type: ignore`.
- `PR-0354` now separates the original 2026-06-14 remediation validation from
  the 2026-06-15 proof-script regression commands, so the retained validation
  timeline is truthful.
- `.codex/handoff.md` still records the failed native Hemma artifact and the
  pending redeploy/rerun follow-up, which is the correct remaining operational
  state.

Validation rerun for this final re-review:

```bash
pdm run test tests/unit/scripts/test_playwright_pr_0349_progress_snapshot.py tests/unit/scripts/test_playwright_pr_0349_summary_truthfulness.py
pdm run python -m py_compile scripts/playwright_pr_0349_transcript_parity_live.py
pdm run typecheck
pdm run docs-validate
pdm run handoff-validate
git diff --check
```

Results: 10 passed, `py_compile` passed, `typecheck` passed, `docs-validate`
passed, `handoff-validate` passed, and `git diff --check` passed.

### Current Review Pass - 2026-06-14

Decision: `approved`.

No findings. The prior blocker is resolved in the committed state:

- `scripts/_sir_convert_trust_lane_preflight.py:217` now requires
  `_has_sanctioned_remote_proof_gateway` before a `remote-proof-gateway` lane can
  reach `_check_matching_fingerprints`, and `_uses_remote_compute` only reports
  remote compute for that lane after the sanctioned gateway check
  (`scripts/_sir_convert_trust_lane_preflight.py:383`).
- `tests/unit/scripts/test_sir_convert_trust_lane_preflight.py:201` and
  `tests/unit/scripts/test_sir_convert_trust_lane_preflight.py:225` prove the
  previous bypass fails closed when the gateway target is missing or local.
- `scripts/playwright_pr_0349_transcript_parity_live.py:361` runs preflight and
  running-backend target checks before source media is copied at line 394, so
  unresolved proof lanes block before upload/job submit.
- `src/skriptoteket/infrastructure/curated_apps/apps/conversion_hub/sir_convert_transcript_formatter_producer.py:86`
  accepts Sir Convert `200`/`202`, polls `/v2/convert/jobs/{job_id}` to a
  terminal status at line 92, and only reads `/result`, `/artifacts`, and named
  artifact bytes after success at lines 107-145. The regression test at
  `tests/unit/infrastructure/curated_apps/apps/conversion_hub/test_sir_convert_transcript_formatter_producer.py:36`
  asserts the exact async submit -> poll -> result/artifacts order.
- Sir Convert commit `159e82d5e674213ba58d5e2d959e8baba383dadb` narrows worker
  recovery to generic-runtime routes only:
  `scripts/sir_convert_a_lot/infrastructure/job_store_v2.py:392` skips
  `dispatches_runtime_jobs=false` routes, and
  `scripts/sir_convert_a_lot/domain/service_routes_v2.py:241` marks
  `transcript_json -> transcript_bundle` as non-dispatching. The cross-process
  recovery regression lives at
  `tests/sir_convert_a_lot/test_transcript_formatter_replay_fast_lane_v2.py:205`.
- Durable guidance is updated where future agents will read it:
  `skills/hemma-devops/references/skriptoteket.md:115` requires native Hemma
  production proof, `skills/sir-convert-a-lot-client/references/service-v2.md:171`
  documents async formatter polling, and
  `docs/reference/ref-stt-proof-lanes-and-admission-operations.md:74` records the
  Sir Convert formatter recovery invariant.

Local proof first, production proof second is acceptable because the retained
evidence matches the ordered doctrine:

- Local proof
  `.artifacts/playwright-pr-0349-transcript-parity-live/20260614T184817Z/proof-summary.json`
  passed with `lane_kind=hemma_remote_proof`, `remote_compute=true`,
  `mixed_tunnel=false`, formatter artifact count `4`, all TXT/MD/VTT/SRT
  downloads `200`, and Mina filer save `200`. The same run's
  `backend-container.json` shows the running product backend targeted
  `http://host.docker.internal:28085`.
- Native Hemma proof
  `/home/paunchygent/apps/skriptoteket/.artifacts/playwright-pr-0352-transcript-parity-native/20260614T191738Z/proof-summary.json`
  passed with `lane_kind=hemma_production`, `remote_compute=true`,
  `mixed_tunnel=false`, formatter artifact count `4`, all TXT/MD/VTT/SRT
  downloads `200`, and Mina filer save `200`.
- Native Hemma container logs retained under
  `/home/paunchygent/apps/skriptoteket/.artifacts/pr-0352-native-proof-logs/20260614T191737Z/`
  show Skriptoteket `POST /formatter-exports` `200`, all four
  formatter-artifact downloads `200`, Mina filer save `200`, Sir Convert
  `transcript_formatter_replay_fast_lane_completed route=transcript_json->transcript_bundle status=succeeded`,
  and all named artifact GETs `200`.

Validation rerun for this review:

```bash
pdm run test tests/unit/scripts/test_sir_convert_trust_lane_preflight.py tests/unit/scripts/test_playwright_pr_0349_summary_truthfulness.py tests/unit/scripts/test_playwright_script_surface.py
pdm run test tests/unit/infrastructure/curated_apps/apps/conversion_hub/test_sir_convert_transcript_formatter_producer.py tests/unit/application/curated_apps/handlers/test_conversion_hub_transcript_formatter_exports.py tests/unit/infrastructure/curated_apps/apps/conversion_hub/test_sir_convert_client_v2.py
cd /Users/olofs_mba/Documents/Repos/sir-convert-a-lot && pdm run pytest-root tests/sir_convert_a_lot/test_transcript_formatter_replay_fast_lane_v2.py::test_replay_fast_lane_terminalizes_during_cross_process_recovery_sweep tests/sir_convert_a_lot/test_job_store_v2.py::test_recover_running_jobs_to_queued_recovers_only_orphaned_running_jobs -q
```

Results: 28 passed, 18 passed, and 2 passed.

Retained validation evidence inspected from the PR docs/handoff:

```bash
pdm run typecheck
pdm run lint
pdm run docs-validate
pdm run handoff-validate
git diff --check
```

Recorded result: passed before this independent review pass.

### Historical Review Pass - 2026-06-14

### Findings

1. **resolved blocker - unresolved remote proof gateway lane can pass on fingerprints alone**

   `scripts/_sir_convert_trust_lane_preflight.py:184` routes every
   `remote-proof-gateway` local proof to `_check_matching_fingerprints`, and
   `_uses_remote_compute` treats `proof_lane == "remote-proof-gateway"` as
   remote compute at `scripts/_sir_convert_trust_lane_preflight.py:340` before
   checking any gateway/backend target. `_check_matching_fingerprints` then
   only requires signer and verifier fingerprints at
   `scripts/_sir_convert_trust_lane_preflight.py:365`.

   This means a local UI/backend proof can pass preflight with
   `--sir-convert-proof-lane remote-proof-gateway` plus matching fingerprint
   metadata even when `gateway_backend_url` and ready/profile metadata are
   absent or still point at a local/non-sanctioned backend. That violates
   `PR-0352` acceptance that unresolved lanes block before media copy/job
   submit and that the active lane is resolved from the HuleEdu Gateway target,
   Sir Convert readiness/profile metadata, and public fingerprints.

   Corrective shape: require a resolved sanctioned remote proof gateway target
   for `remote-proof-gateway` before allowing `_check_matching_fingerprints`.
   At minimum, missing `gateway_backend_url` should block with
   `sir_convert_trust_lane_unresolved`, and local/private/default backend
   targets should not be accepted as `remote-proof-gateway`. Keep the
   production/Hemma public product-host allowance separate from local proof
   gateway validation.

   Proof required:

   ```bash
   pdm run test tests/unit/scripts/test_sir_convert_trust_lane_preflight.py
   pdm run test tests/unit/scripts/test_sir_convert_trust_lane_preflight.py tests/unit/scripts/test_playwright_pr_0349_summary_truthfulness.py tests/unit/scripts/test_playwright_script_surface.py
   pdm run python -m py_compile scripts/_sir_convert_trust_lane_preflight.py scripts/playwright_pr_0349_transcript_parity_live.py
   pdm run typecheck
   pdm run lint
   pdm run docs-validate
   pdm run handoff-validate
   git diff --check
   ```

### Required Changes

- Add a negative test proving `proof_lane="remote-proof-gateway"` with matching
  fingerprints but no gateway target blocks before media copy/job submit.
- Add a negative test proving `remote-proof-gateway` rejects local/private
  gateway targets such as `http://127.0.0.1:8085` or
  `http://host.docker.internal:8085`.
- Update the preflight logic so `remote-proof-gateway` is remote only after a
  sanctioned gateway target/profile is resolved, then rerun the proof commands
  listed above.

### Suggestions (Optional)

Pending.

### Decision Approvals

- [x] Preflight before media copy
- [x] Remote hosted runtime remains default
- [x] Mixed tunnel opt-in and fingerprint agreement
- [x] Redacted retained failure summaries

## Changes Made

| Change | Artifact | Description |
|--------|----------|-------------|
| 1 | `PR-0352` | Added implementation summary, red-first evidence, and validation evidence. |
| 2 | `scripts/_sir_convert_trust_lane_preflight.py` | Added browser-free proof-lane preflight helper. |
| 3 | `scripts/playwright_pr_0349_transcript_parity_live.py` | Runs preflight before media copy and browser launch. |
| 4 | `tests/unit/scripts/test_sir_convert_trust_lane_preflight.py` | Adds focused trust-lane preflight tests. |
