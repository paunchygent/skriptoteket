---
type: review
id: REV-PR-0350
title: "Review: PR-0350 Product-owned transcript replay export boundary"
status: approved
owners: "agents"
created: 2026-06-14
updated: 2026-06-14
reviewer: "skriptoteket_reviewer"
prs:
  - PR-0350
links:
  - ST-21-08
  - EPIC-21
  - docs/backlog/reviews/review-pr-0349-transcript-parity-live-proof-and-closeout.md
  - /Users/olofs_mba/Documents/Repos/sir-convert-a-lot/docs/backlog/tasks/task-363-fast-transcript-formatter-replay-lane-outside-heavy-conversion-queue.md
---

## TL;DR

PR-0350 now satisfies the product-owned transcript replay export boundary.
The browser-owned replay submit/poll/download/base64/complete path is removed,
transport failures fail closed into product state, `running` exports remain
refreshable through the product GET endpoint, and requested artifact subsets
persist across pending/running/failed/succeeded export states.

Implementation review is approved. Authenticated live browser proof is still
outstanding and remains a closeout requirement for PR-0349/PR-0350, but it is
not a blocking code-review finding against this remediated PR slice.

## Problem Statement

PR-0350 is the retained review gate for the product-owned transcript export
boundary that replaces the earlier browser-owned replay saga.

## Proposed Solution

Skriptoteket must own formatter export intent, producer submission, artifact
verification, persistence, and durable readback while the SPA only records
intent, observes product status, and performs product-authorized download/save
actions.

## Artifacts to Review

| File | Focus | Time |
|------|-------|------|
| `docs/backlog/prs/pr-0350-st-21-08-product-owned-transcript-replay-export-boundary.md` | Scope and acceptance | 5 min |
| `src/skriptoteket/web/api/v1/apps_conversion_hub_transcript_saves.py` | Product export API boundary | 10 min |
| `src/skriptoteket/application/curated_apps/` | Export handler, producer protocol use, persistence flow | 20 min |
| `frontend/apps/skriptoteket/src/api/conversionHubTranscriptFormatterExports.ts` | Browser records product export intent and reads product state | 10 min |
| `frontend/apps/skriptoteket/src/api/sirConvertGateway/client.ts` | Direct browser replay methods are not exposed | 5 min |
| `frontend/apps/skriptoteket/src/views/apps/conversion-hub-transcript/` | Product status rendering | 10 min |
| `tests/` and frontend specs | Behavioral proof and old saga cleanup | 20 min |

**Total estimated time:** ~75 minutes

## Key Decisions

| Decision | Rationale | Approve? |
|----------|-----------|----------|
| Consume only the accepted task-363 producer contract server-side | Keeps Sir Convert as artifact producer and Skriptoteket as product owner | [x] |
| Remove browser submit/poll/download/base64/complete replay orchestration | Eliminates the P0 architecture violation from PR-0349 review | [x] |
| Persist explicit export state for pending/failure/success | Prevents silent foreground waits and supports durable product UX | [x] |

## Review Checklist

- [x] Scope is bounded to PR-0350 and the accepted task-363 contract.
- [x] Browser cannot submit, poll, download, base64, or complete replay artifacts.
- [x] Backend verifies producer artifact authority before persistence.
- [x] Pending, running, failure, and success states are explicit and product-owned.
- [x] Tests prove product behavior rather than retired saga internals.
- [ ] Live proof uses the HuleEdu browser-session ceremony.

## Verification

Commands run:

```bash
git status --short
git branch --show-current
rg -n "requestConversionHubTranscriptFormatterReplay|transcriptReplayClient|artifact_payloads|arrayBufferToBase64|formatter-replay/prepare|formatter-replay/complete|/sir-convert/v2/convert/jobs" frontend/apps/skriptoteket src/skriptoteket tests/unit scripts
pdm run test tests/unit/application/curated_apps/handlers/test_conversion_hub_transcript_formatter_exports.py tests/unit/web/conversion_hub/test_apps_conversion_hub_transcript_saves_api.py
pdm run fe-test -- --run frontend/apps/skriptoteket/src/api/conversionHubTranscriptFormatterExports.spec.ts frontend/apps/skriptoteket/src/views/apps/conversion-hub-transcript/ConversionHubTranscriptHost.spec.ts frontend/apps/skriptoteket/src/views/apps/conversion-hub-transcript/TranscriptWorkspaceShell.spec.ts
pdm run test --override-ini addopts='' 'tests/integration/test_migration_revision_coverage_idempotent.py::test_uncovered_migration_revision_is_idempotent[f4c8e2a6b9d1]'
```

Results:

- Branch and handoff point at
  `codex/skriptoteket-pr-0350-product-owned-transcript-replay-export`.
- Code search still shows no active browser-owned replay submit/poll/download/
  base64/complete flow in the PR-0350 product surfaces. Remaining
  `/sir-convert/v2/convert/jobs` hits are in the transcript upload gateway,
  older proof scripts, and unrelated gateway specs, not in the formatter
  export boundary under review.
- `pdm run test ...` passed with `18 passed`.
- `pdm run fe-test -- --run ...` passed with `18 passed`.
- Migration idempotency for `f4c8e2a6b9d1` passed with `1 passed` using the
  docker-marked revision coverage test lane.
- I did not rerun authenticated live browser proof for PR-0349/PR-0350, so
  closeout still requires that separate proof lane.

## Review Feedback

**Reviewer:** skriptoteket_reviewer
**Date:** 2026-06-14
**Verdict:** approved

### Findings

No remaining findings. I rechecked the three retained issues and verified that
they are fixed in code and in focused tests:

- Producer transport failures are normalized to sanitized `DomainError`
  instances in
  [sir_convert_transcript_formatter_producer.py](/Users/olofs_mba/Documents/Repos/CascadeProjects/windsurf-project/src/skriptoteket/infrastructure/curated_apps/apps/conversion_hub/sir_convert_transcript_formatter_producer.py:142),
  and the handler records product `failed` export state instead of surfacing a
  raw `500`.
- `running` exports remain refreshable because the host now refreshes through
  product GET for both `pending` and `running`, while a separate in-flight flag
  prevents duplicate clicks at
  [ConversionHubTranscriptHost.vue](/Users/olofs_mba/Documents/Repos/CascadeProjects/windsurf-project/frontend/apps/skriptoteket/src/views/apps/conversion-hub-transcript/ConversionHubTranscriptHost.vue:98)
  and
  [ConversionHubTranscriptHost.vue](/Users/olofs_mba/Documents/Repos/CascadeProjects/windsurf-project/frontend/apps/skriptoteket/src/views/apps/conversion-hub-transcript/ConversionHubTranscriptHost.vue:269).
- Requested artifact subsets now persist in explicit export-state rows through
  the new model/repository/migration at
  [conversion_hub_transcript_formatter_export_states.py](/Users/olofs_mba/Documents/Repos/CascadeProjects/windsurf-project/src/skriptoteket/infrastructure/repositories/conversion_hub_transcript_formatter_export_states.py:28),
  [conversion_hub_transcript_formatter_export_state.py](/Users/olofs_mba/Documents/Repos/CascadeProjects/windsurf-project/src/skriptoteket/infrastructure/db/models/conversion_hub_transcript_formatter_export_state.py:28),
  and
  [f4c8e2a6b9d1_add_transcript_formatter_export_states.py](/Users/olofs_mba/Documents/Repos/CascadeProjects/windsurf-project/migrations/versions/f4c8e2a6b9d1_add_transcript_formatter_export_states.py:1),
  and POST/GET now preserve the subset across nonterminal and failed states.

### Positive Checks

- The browser-owned replay submit/poll/artifact-download/base64/complete saga
  is removed from the PR-0350 surfaces under review. The SPA now requests
  `/formatter-exports` and uses product download/save routes only.
- The backend now owns producer request construction, result/manifest parsing,
  artifact-byte verification, and local persistence before exposing export
  state.
- The user-facing copy in the reviewed transcript export UI remains Swedish and
  does not leak Sir Convert routes, payload fields, or receipt internals.

### Decision Approvals

- [x] Consume task-363 server-side producer contract
- [x] Remove browser-owned replay saga
- [x] Persist product-owned export state

### Remediation Verification

- Verified `httpx.RequestError` failures now map to product-owned failed export
  state through the producer client and handler path.
- Verified `running` export state remains manually refreshable through
  `GET /formatter-exports`.
- Verified requested artifact subsets persist across pending, running, failed,
  and succeeded responses.

## Changes Made

| Change | Artifact | Description |
|--------|----------|-------------|
| 1 | Backend export boundary | Added product-owned POST/GET formatter export handlers and producer protocol/client consumption for task-363. |
| 2 | Frontend export state | Replaced the browser saga with Skriptoteket product endpoint calls and Swedish pending/success/failure/retry UI state. |
| 3 | Cleanup and proof | Removed direct replay Gateway client/tests, regenerated OpenAPI types, and updated PR-0349 proof scripts to wait on `/formatter-exports`. |
| 4 | Producer failure mapping | Mapped `httpx` transport/timeouts/protocol request errors into product failed export state through `DomainError`. |
| 5 | Export-state persistence | Added `conversion_hub_transcript_formatter_export_states` migration/model/repository for requested artifact intent. |
| 6 | Running refresh UI | Made `running` exports manually refreshable through `/formatter-exports` without reintroducing browser producer ownership. |
