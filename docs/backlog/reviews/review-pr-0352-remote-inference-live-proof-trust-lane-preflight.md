---
type: review
id: REV-PR-0352
title: "Review: PR-0352 remote inference live-proof trust-lane preflight"
status: approved
owners: "agents"
created: 2026-06-14
updated: 2026-06-14
reviewer: "ruthless-review-subagent"
prs:
  - PR-0352
links:
  - ST-21-09
  - EPIC-21
  - docs/backlog/reviews/review-pr-0351-transcript-completion-progress-and-export-ux.md
---

## TL;DR

Approved after independent re-review of the committed Skriptoteket, Sir Convert,
and shared skill-repo state plus retained local and native Hemma proof evidence.
The previous blocker is resolved: `remote-proof-gateway` no longer passes on
fingerprints alone, and the full local-first, native-production-second proof
sequence is retained with matching container logs.

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
