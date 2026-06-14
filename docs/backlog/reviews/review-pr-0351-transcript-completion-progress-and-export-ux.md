---
type: review
id: REV-PR-0351
title: "Review: PR-0351 Transcript completion, progress, and export UX"
status: approved
owners: "agents"
created: 2026-06-14
updated: 2026-06-14
reviewer: "skriptoteket_reviewer"
prs:
  - PR-0351
links:
  - ST-21-08
  - EPIC-21
  - MOCK-pr-0351-transcript-progress-export-ux
---

## TL;DR

Approved after final re-review. The prior high finding is fixed:
selected-format export now requires persisted non-empty names for every
canonical speaker in the transcript at both the frontend readiness gate and
backend producer submission boundary. The final spec split and closeout docs
preserve the PR-0351 acceptance proof, and no new blocker was found.

## Problem Statement

The implementation must remove the confusing transcript completion/export UX
without regressing the product-owned replay/export boundary from `PR-0350`.
The review should focus on teacher-visible behavior, stable layout, and proof
that the browser does not regain producer-workflow ownership.

## Proposed Solution

Implement the approved mockup direction:

- truthful running progress with normal Swedish copy;
- autosaved transcript completion with no generic manual save gate;
- transcript reading surface plus `Talare och export` inspector;
- stable format selector plus one-line `Ladda ner` and `Mina filer` actions;
- planned/reserved pending, running, failed, and warning states.

## Artifacts to Review

| File | Focus | Time |
|------|-------|------|
| `docs/backlog/prs/pr-0351-st-21-08-transcript-completion-progress-and-export-ux.md` | Scope, non-goals, acceptance | 10 min |
| `docs/mockups/pr-0351-transcript-progress-export-ux/README.md` | Approved UX contract | 10 min |
| `frontend/apps/skriptoteket/src/views/apps/conversion-hub-transcript/` | Runtime transcript workspace | 40 min |
| `frontend/apps/skriptoteket/src/api/` transcript/export clients | Product endpoint ownership | 20 min |
| Focused Vitest/backend/browser proof artifacts | Behavioral coverage | 30 min |

**Total estimated time:** ~110 minutes

## Key Decisions

| Decision | Rationale | Approve? |
|----------|-----------|----------|
| Autosave on successful transcript completion | Manual `Spara` is not a meaningful teacher choice after successful STT completion and currently hides the useful workspace. | [x] |
| Stable export control block | Format is selected once; actions stay `Ladda ner` and `Mina filer` without duplicated download buttons or dynamic two-line labels. | [x] |
| No jump-scare status surfaces | Pending/running/failed/warning states must have reserved layout or separate planned state layouts. | [x] |
| No internal/Swenglish copy | Producer stages must map to normal Swedish teacher language. | [x] |
| Browser remains product-observer only | `PR-0351` must not restore browser-owned Sir Convert replay submit/poll/download/base64/complete behavior. | [x] |

## Review Checklist

- [x] Scope is bounded to transcript progress/completion/export UX.
- [x] Runtime follows the approved mockup hierarchy without pixel-match
  cargo-culting.
- [x] Transcript column keeps readable width at desktop and moves inspector
  below before the transcript is squeezed.
- [x] Running state does not show a fake full workspace before transcript
  content exists.
- [x] Progress bar/ETA is based on available product/producer data and does
  not fabricate completion from heartbeat alone.
- [x] Visible Swedish copy avoids internal terms such as raw diarization stage
  names.
- [x] Completed transcript autosaves and lands directly in the useful
  workspace.
- [x] Export has no duplicated download affordance, no selected-file metadata
  cards, no dropdown chevron without a menu, and no dynamic format suffix in
  visible action labels.
- [x] Pending/running/failed/warning UI states are planned and do not alter
  layout unexpectedly.
- [x] Focused tests prove old labels/actions are absent on the normal path.
- [x] Browser proof uses the HuleEdu browser-session ceremony only.

## Review Feedback

**Reviewer:** @skriptoteket_reviewer
**Date:** 2026-06-14
**Verdict:** approved

### Scope Reviewed

- Current working-tree diff and untracked files from `git status --short`,
  including the new transcript progress/completed/export components, new
  transcript progress parsers, backend formatter export contract/parsing
  modules, deleted replay source files, and updated PR-0349 Playwright proof.
- Governing docs: `PR-0351`, retained `REV-PR-0351`, approved mockup bundle,
  `PR-0350`, `ST-21-08`, and `EPIC-21`.
- Rules/skills: repo AGENTS entrypoint, handoff, docs index, rule index plus
  task-relevant frontend/backend/testing/browser/review rules, `testing`,
  `ruthless-code-review`, `integrated-frontend-stack`,
  `skriptoteket-frontend-specialist`, `skriptoteket-testing`, and
  `agent-docs-governance`.

### Findings

1. **Resolved high - Partial speaker overlays could be exported with canonical fallback labels.**
   `frontend/apps/skriptoteket/src/views/apps/conversion-hub-transcript/ConversionHubTranscriptHost.vue:110`
   previously enabled formatter export when `speakerOverlayEntries.length > 0`,
   not when every canonical speaker label in the transcript had a persisted
   display-name overlay. The backend boundary had the same gap:
   `src/skriptoteket/application/curated_apps/handlers/conversion_hub_transcript_formatter_exports.py:102`
   rejects only the empty-overlay case, while
   `src/skriptoteket/application/curated_apps/handlers/conversion_hub_transcript_formatter_export_support.py:190`
   verifies only that submitted overlay labels exist in the transcript. The
   pre-remediation frontend test fixture made the problem explicit:
   `frontend/apps/skriptoteket/src/views/apps/conversion-hub-transcript/ConversionHubTranscriptHost.spec.ts:279`
   returned only `SPEAKER_00` for a two-speaker transcript, and export/download
   tests still passed. That violated the ST-21-08/export proof expectation that
   overlay-aware formatter downloads exclude canonical fallback labels. The
   remediation now requires the saved overlay set to cover the transcript's
   canonical speaker label inventory before enabling `Ladda ner`/`Mina filer`
   and before the backend submits to Sir Convert.

### Required Changes

- None.

### Suggestions (Optional)

- Optional: keep the selected-format action labels exactly as implemented
  (`Ladda ner`, `Mina filer`); this part matches the approved UX direction.

### Decision Approvals

- [x] Autosave completion path
- [x] Stable export control block
- [x] No jump-scare status surfaces
- [x] No internal/Swenglish copy
- [x] Browser remains product-observer only

### Verification Evidence

Original reviewer-run checks before remediation:

```bash
git status --short
git diff --check
pdm run fe-test -- --run src/views/apps/conversion-hub-transcript/TranscriptWorkspaceShell.pr0351.spec.ts src/views/apps/conversion-hub-transcript/ConversionHubTranscriptHost.spec.ts
pdm run test tests/unit/application/curated_apps/handlers/test_conversion_hub_transcript_formatter_exports.py
```

Observed original results:

- `git diff --check` passed.
- Focused PR-0351/host Vitest passed: 2 files, 11 tests.
- Focused backend formatter export pytest passed: 9 tests.
- The passing Vitest host tests are not sufficient approval evidence because
  they currently allow the partial-overlay export path described above.

### Re-review Findings

No open findings.

Prior finding closure:

- Frontend export readiness now requires `speakerOverlayCoverageComplete` and a
  saved overlay status before selected-format actions can request export
  (`frontend/apps/skriptoteket/src/views/apps/conversion-hub-transcript/ConversionHubTranscriptHost.vue:110`).
  Coverage is computed from `transcript.segments` and only counts non-empty
  persisted overlay names
  (`frontend/apps/skriptoteket/src/views/apps/conversion-hub-transcript/ConversionHubTranscriptHost.vue:280`).
- Overlay readback and save keep partial persisted coverage in `idle`, so the
  inspector remains truthful and selected-format actions stay disabled until all
  transcript speakers are named
  (`frontend/apps/skriptoteket/src/views/apps/conversion-hub-transcript/ConversionHubTranscriptHost.vue:222`,
  `frontend/apps/skriptoteket/src/views/apps/conversion-hub-transcript/ConversionHubTranscriptHost.vue:252`).
- Backend export submission now validates that non-empty overlays exactly cover
  the canonical speaker labels before building or submitting the Sir Convert
  formatter request
  (`src/skriptoteket/application/curated_apps/handlers/conversion_hub_transcript_formatter_exports.py:102`,
  `src/skriptoteket/application/curated_apps/handlers/conversion_hub_transcript_formatter_export_support.py:190`).
- The new backend regression test proves partial coverage raises
  `validation_error` before producer submission and before an export job is
  created
  (`tests/unit/application/curated_apps/handlers/test_conversion_hub_transcript_formatter_exports.py:143`).
  The new frontend regression test proves a two-speaker transcript with only one
  persisted overlay keeps both selected-format actions disabled and does not call
  the formatter export client
  (`frontend/apps/skriptoteket/src/views/apps/conversion-hub-transcript/ConversionHubTranscriptHost.spec.ts:382`).
- Re-scan of active transcript/export source found no retained browser-owned
  formatter replay component, command, or shim. Remaining literal
  `transcript_formatter_replay_v1`,
  `transcript_replay_bundle_manifest.json`, and
  `transcript_json_to_transcript_bundle_replay_v2` values are upstream
  task-363/PR-0350 contract values, not active Skriptoteket-owned legacy UI or
  workflow surfaces.

### Re-review Verification Evidence

Re-reviewer-run checks:

```bash
git status --short
git diff --check
pdm run test tests/unit/application/curated_apps/handlers/test_conversion_hub_transcript_formatter_exports.py::test_product_export_rejects_partial_speaker_overlays_before_producer_submission
pdm run fe-test -- --run src/views/apps/conversion-hub-transcript/ConversionHubTranscriptHost.spec.ts -t "keeps export disabled until all transcript speakers have persisted names"
pdm run test tests/unit/application/curated_apps/handlers/test_conversion_hub_transcript_formatter_exports.py tests/unit/application/curated_apps/handlers/test_conversion_hub_transcript_artifact_actions.py tests/unit/application/curated_apps/handlers/test_conversion_hub_transcript_saves.py tests/unit/web/conversion_hub/test_apps_conversion_hub_transcript_saves_api.py
pdm run fe-test -- --run src/api/sirConvertGateway/transcriptClient.spec.ts src/api/sirConvertGateway/transcriptProgressParsers.spec.ts src/views/apps/conversion-hub-transcript/TranscriptWorkspaceShell.spec.ts src/views/apps/conversion-hub-transcript/TranscriptWorkspaceShell.pr0351.spec.ts src/views/apps/conversion-hub-transcript/ConversionHubTranscriptHost.spec.ts src/api/conversionHubTranscriptFormatterArtifactActions.spec.ts src/views/apps/conversion-hub-transcript/useTranscriptGatewayRuntime.spec.ts
```

Observed re-review results:

- `git diff --check` passed.
- Backend red-first remediation test passed: 1 test.
- Frontend red-first remediation test passed: 1 test, 9 skipped by filter.
- Focused backend transcript/export bundle passed: 31 tests.
- Focused frontend transcript/export bundle passed: 7 files, 44 tests.

Residual risks:

- No live authenticated browser proof was rerun by this reviewer during the
  re-review. Acceptance relies on retained implementer proof plus focused
  unit/component coverage for the remediated export readiness boundary.

### Final Re-review Findings

No open findings.

Final pass notes:

- The host spec split keeps behavioral assertions in the DOM/API-boundary tests
  rather than reducing them to helper-only coverage. The shared harness now
  provides the two-speaker transcript and complete persisted-overlay happy path
  (`frontend/apps/skriptoteket/src/views/apps/conversion-hub-transcript/ConversionHubTranscriptHost.specSupport.ts:101`,
  `frontend/apps/skriptoteket/src/views/apps/conversion-hub-transcript/ConversionHubTranscriptHost.specSupport.ts:240`),
  while PR-0351-specific tests still prove autosave/no manual save gate,
  selected-format labels, no redundant labels, and partial-overlay export
  blocking
  (`frontend/apps/skriptoteket/src/views/apps/conversion-hub-transcript/ConversionHubTranscriptHost.pr0351.spec.ts:38`,
  `frontend/apps/skriptoteket/src/views/apps/conversion-hub-transcript/ConversionHubTranscriptHost.pr0351.spec.ts:55`,
  `frontend/apps/skriptoteket/src/views/apps/conversion-hub-transcript/ConversionHubTranscriptHost.pr0351.spec.ts:107`,
  `frontend/apps/skriptoteket/src/views/apps/conversion-hub-transcript/ConversionHubTranscriptHost.pr0351.spec.ts:130`).
- The runtime still gates selected-format export on complete saved speaker
  overlays (`frontend/apps/skriptoteket/src/views/apps/conversion-hub-transcript/ConversionHubTranscriptHost.vue:110`)
  and the backend still rejects partial overlays before producer submission
  (`src/skriptoteket/application/curated_apps/handlers/conversion_hub_transcript_formatter_exports.py:102`,
  `src/skriptoteket/application/curated_apps/handlers/conversion_hub_transcript_formatter_export_support.py:190`).
- Forbidden PR-0351 UI strings and action labels remain absent from active UI
  code; occurrences found by grep are negative assertions or upstream/provider
  contract fields. The active selected-format panel still renders a single
  selector with stable `Ladda ner` and `Mina filer` actions and a reserved
  status line
  (`frontend/apps/skriptoteket/src/views/apps/conversion-hub-transcript/TranscriptFormatterExportPanel.vue:127`,
  `frontend/apps/skriptoteket/src/views/apps/conversion-hub-transcript/TranscriptFormatterExportPanel.vue:156`).
- The final local live proof artifact is correctly recorded as an external
  trust-lane blocker: the protected route loaded and progress/cancel surfaces
  were captured, but Sir Convert rejected product-backend submission with
  `auth_invalid_internal_identity` /
  `invalid_internal_identity_signature` on
  `POST /sir-convert/v2/convert/jobs?wait_seconds=0`
  (`.artifacts/playwright-pr-0349-transcript-parity-live/20260614T082007Z/proof-summary.json`).
  This is retained as residual external verification risk, not a PR-0351 UI
  regression.

### Final Re-review Verification Evidence

Final reviewer-run checks:

```bash
git status --short
git diff --check
pdm run test tests/unit/application/curated_apps/handlers/test_conversion_hub_transcript_formatter_exports.py tests/unit/application/curated_apps/handlers/test_conversion_hub_transcript_artifact_actions.py tests/unit/application/curated_apps/handlers/test_conversion_hub_transcript_saves.py tests/unit/web/conversion_hub/test_apps_conversion_hub_transcript_saves_api.py
pdm run fe-test -- --run src/api/sirConvertGateway/transcriptClient.spec.ts src/api/sirConvertGateway/transcriptProgressParsers.spec.ts src/views/apps/conversion-hub-transcript/TranscriptWorkspaceShell.spec.ts src/views/apps/conversion-hub-transcript/TranscriptWorkspaceShell.pr0351.spec.ts src/views/apps/conversion-hub-transcript/ConversionHubTranscriptHost.spec.ts src/views/apps/conversion-hub-transcript/ConversionHubTranscriptHost.pr0351.spec.ts src/api/conversionHubTranscriptFormatterArtifactActions.spec.ts src/views/apps/conversion-hub-transcript/useTranscriptGatewayRuntime.spec.ts
pdm run docs-validate
pdm run handoff-validate
git diff --check
```

Observed final results:

- `git diff --check` passed before and after the review artifact update.
- Focused backend transcript/export bundle passed: 31 tests.
- Focused frontend transcript/export bundle passed: 8 files, 44 tests.
- `pdm run docs-validate` passed.
- `pdm run handoff-validate` passed.

Final residual risk:

- A fresh completion-path live browser proof remains blocked by the local
  product-backend to Sir Convert internal identity signature mismatch recorded
  in
  `.artifacts/playwright-pr-0349-transcript-parity-live/20260614T082007Z/proof-summary.json`.
  Prior retained production proof plus focused PR-0351 tests cover the product
  behavior until that trust lane is repaired.

## Changes Made

| Change | Artifact | Description |
|--------|----------|-------------|
| 1 | `REV-PR-0351` | Recorded changes-requested decision after independent review. |
| 2 | `REV-PR-0351` | Recorded approved re-review decision after partial-overlay remediation. |
| 3 | `REV-PR-0351` | Recorded final approved re-review after spec split and closeout docs. |
