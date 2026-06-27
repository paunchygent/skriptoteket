---
type: review
id: REV-PR-0397
title: "Review: PR-0397 Document Converter file operations layout remediation"
status: approved
owners: "agents"
created: 2026-06-27
updated: 2026-06-27
reviewer: "codex"
prs:
  - "PR-0397"
links:
  - "EPIC-37"
  - "ST-37-05"
  - "PR-0396"
  - "REV-PR-0396"
---

# Review: PR-0397 Document Converter File Operations Layout Remediation

## TL;DR

`approved`. The final correction keeps generated-output selection in the
middle operations column, leaves the preview column preview-only, removes the
old eyebrow/status row, and passes the retained handoff gate that blocked the
previous review pass.

## Problem Statement

`PR-0397` remediates a layout regression in `/apps/document-converter`: the
filename field, download action, and save action were cramped into the preview
footer instead of living in a stable operations column. The governing contract
requires the same left-source / middle-operations / right-preview grammar for
both `HTML/CSS-projekt` and `Filkonvertering`.

## Proposed Solution

Refactor the route so source intake and source review stay in the left rail,
all file operations live in the middle rail through a shared component, and the
right rail becomes preview-only. Prove that contract with focused behavioral
tests, especially across the single-file success path that uses the
history-backed result state instead of the live project-preview branch.

## Artifacts to Review

| File | Focus |
|---|---|
| `docs/backlog/prs/pr-0397-st-37-05-document-converter-file-operations-layout-remediation.md` | Governing scope, acceptance criteria, test plan |
| `frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterView.vue` | Shared three-column workspace composition |
| `frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterSourceIntake.vue` | Source intake extraction and single-source-of-truth boundary |
| `frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterResultActions.vue` | Shared file-operations ownership and drift control |
| `frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterResultPanel.vue` | Preview-only right-column behavior |
| `frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterSingleFileControls.vue` | Single-file operations-column behavior |
| `frontend/apps/skriptoteket/src/views/apps/document-converter/documentConverterWorkspace.css` | Column geometry and responsive ownership |
| `frontend/apps/skriptoteket/src/views/apps/document-converter/documentConverterPreview.css` | Preview and result-action styles split out of workspace geometry |
| `frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterLayoutOwnership.spec.ts` | Project layout ownership proof |
| `frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterView.spec.ts` | Route behavioral proof |
| `frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterSingleFileView.spec.ts` | Single-file behavioral proof |
| `frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterArtifactSelector.vue` | Generated-output selector ownership |
| `.artifacts/pr-0397-layout-screenshots/20260627T104912Z/manifest.redacted.json` | Retained layout screenshot matrix |
| `.artifacts/authenticated-home-work-apps/20260627T104130Z/manifest.redacted.json` | Retained authenticated browser proof coverage |

## Key Decisions

| Decision | Rationale | Approve? |
|---|---|---|
| Keep the shared file-operations surface centralized in one component | Controls duplication and layout drift between modes | [x] |
| Treat preview-only ownership as a behavioral contract, not just DOM structure | The user-approved issue was visual/user-facing, not internal | [x] |
| Require proof for `Filkonvertering` success state before approval | That mode is explicitly in scope and uses a different result path | [x] |

## Review Checklist

- [x] Scoped the current working-tree files relevant to PR-0397.
- [x] Checked the route composition against the governing three-column contract.
- [x] Reviewed the token-driven CSS ownership and responsive geometry.
- [x] Ran focused frontend verification commands on the current tree.
- [x] Confirmed truthful succeeded-state proof for `Filkonvertering`.
- [x] Checked the retained authenticated proof artifact for residual gaps.

## Findings

No findings.

## Decision

`approved`

The current tree resolves the prior handoff blocker and satisfies the final
contract: artifact selection is in the operations column, preview is preview
only, the eyebrow/header row is gone, and both modes share the same source /
operations / preview ownership.

## Scope Reviewed

- Governing doc: `docs/backlog/prs/pr-0397-st-37-05-document-converter-file-operations-layout-remediation.md`
- Current working-tree frontend scope:
  - `frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterResultActions.vue`
  - `frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterArtifactSelector.vue`
  - `frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterResultPanel.vue`
  - `frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterSingleFileControls.vue`
  - `frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterSingleFileView.spec.ts`
  - `frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterSourceIntake.vue`
  - `frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterSourcePanel.vue`
  - `frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterLayoutOwnership.spec.ts`
  - `frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterView.spec.ts`
  - `frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterView.vue`
  - `frontend/apps/skriptoteket/src/views/apps/document-converter/documentConverterPreview.css`
  - `frontend/apps/skriptoteket/src/views/apps/document-converter/documentConverterWorkspace.css`
- Docs/workflow scope touched by the worktree:
  - `docs/backlog/stories/story-37-05-cross-app-save-export-file-naming-protocol.md`
  - `docs/index.md`
  - `.codex/handoff.md`

## Verification

- `pdm run fe-test -- --run frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterSingleFileView.spec.ts frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterView.spec.ts` -> passed, `2` files and `13` tests. This includes the strengthened succeeded-state single-file proof at `DocumentConverterSingleFileView.spec.ts:269`.
- `pdm run fe-type-check` -> passed.
- `pdm run docs-validate` -> passed.
- `git diff --check` -> passed.
- Author-reported current-tree validation already green before this review pass: `pdm run fe-lint` and the wider focused Document Converter Vitest suite with `22 passed`.
- Reviewed `.artifacts/authenticated-home-work-apps/20260627T084211Z/manifest.redacted.json` and confirmed the retained live proof still covers HTML/CSS auto-preview at desktop and compact widths rather than a successful `Filkonvertering` browser run. That remains a residual validation gap, not a blocker for this retained proof-only review scope, because the strengthened Vitest now directly exercises the alternate single-file success path.
- Third pass cleanup verification: `pdm run fe-test -- --run frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterLayoutOwnership.spec.ts frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterProjectResult.spec.ts frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterSingleFileView.spec.ts frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterView.spec.ts frontend/apps/skriptoteket/src/views/apps/document-converter/documentConverterFileApi.spec.ts frontend/apps/skriptoteket/src/views/apps/document-converter/documentConverterProjectPreviewApi.spec.ts` -> passed, `6` files and `22` tests.
- Third pass cleanup verification: `pdm run fe-type-check` -> passed.
- Third pass cleanup verification: `pdm run docs-validate` -> passed.
- Third pass cleanup verification: `pdm run handoff-validate` -> passed.
- Third pass cleanup verification: `git diff --check` -> passed.
- Third pass file-size check: `DocumentConverterView.vue` is `474` lines,
  `documentConverterWorkspace.css` is `445` lines,
  `DocumentConverterSourceIntake.vue` is `159` lines, and
  `DocumentConverterLayoutOwnership.spec.ts` is `175` lines.
- Reviewed `.artifacts/authenticated-home-work-apps/20260627T101211Z/manifest.redacted.json` as the current retained live proof artifact for the cleanup pass.
- Final visual-polish verification: `pdm run fe-test -- --run frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterLayoutOwnership.spec.ts frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterProjectResult.spec.ts frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterSingleFileView.spec.ts frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterView.spec.ts frontend/apps/skriptoteket/src/views/apps/document-converter/documentConverterFileApi.spec.ts frontend/apps/skriptoteket/src/views/apps/document-converter/documentConverterProjectPreviewApi.spec.ts` -> passed, `6` files and `22` tests.
- Final visual-polish verification: `pdm run fe-type-check` -> passed.
- Final visual-polish verification: `git diff --check` -> passed.
- Final visual-polish verification: `pdm run handoff-validate` -> failed because `.codex/handoff.md` is `202` lines against the `200` line budget.
- Final visual-polish verification after review-artifact update: `pdm run docs-validate` -> passed.
- Final visual-polish verification after review-artifact update: `git diff --check` -> passed.
- Reviewed `.artifacts/pr-0397-layout-screenshots/20260627T102406Z/manifest.redacted.json`, desktop active screenshots for both modes, tablet active single-file screenshot, compact active project screenshot, and compact active single-file screenshot. The proof matrix covers empty and active `HTML/CSS-projekt` plus `Filkonvertering` at desktop, tablet, and compact widths.
- Reviewed `.artifacts/authenticated-home-work-apps/20260627T102509Z/manifest.redacted.json` and compact route screenshot. The authenticated proof remains green with `document_converter_forbidden_surfaces_absent=true`.
- Final corrected-contract verification: `pdm run fe-test -- --run frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterLayoutOwnership.spec.ts frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterProjectResult.spec.ts frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterSingleFileView.spec.ts frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterView.spec.ts frontend/apps/skriptoteket/src/views/apps/document-converter/documentConverterFileApi.spec.ts frontend/apps/skriptoteket/src/views/apps/document-converter/documentConverterProjectPreviewApi.spec.ts` -> passed, `6` files and `22` tests.
- Final corrected-contract verification: `pdm run fe-type-check` -> passed.
- Final corrected-contract verification: `pdm run handoff-validate` -> passed.
- Final corrected-contract verification: `git diff --check` -> passed.
- Final corrected-contract file-size check: `DocumentConverterView.vue` is `460` lines, `DocumentConverterArtifactSelector.vue` is `51` lines, `DocumentConverterResultPanel.vue` is `51` lines, `DocumentConverterResultActions.vue` is `117` lines, `DocumentConverterSingleFileControls.vue` is `87` lines, `documentConverterWorkspace.css` is `499` lines, and `documentConverterPreview.css` is `192` lines.
- Reviewed `.artifacts/pr-0397-layout-screenshots/20260627T104006Z/manifest.redacted.json`; the current screenshot matrix covers empty and active `HTML/CSS-projekt` plus `Filkonvertering` at desktop, tablet, and compact widths.
- Reviewed `.artifacts/authenticated-home-work-apps/20260627T104130Z/manifest.redacted.json`; authenticated proof remains green with `document_converter_forbidden_surfaces_absent=true`.
- Reviewed `.artifacts/pr-0397-layout-screenshots/20260627T104912Z/compact-single-file-active-screen.png`; the compact selected-source summary is demoted from heading scale and route-local typography uses shared text-size tokens.

## Review Feedback

**Reviewer:** `codex`
**Date:** `2026-06-27`
**Verdict:** `approved`

The earlier retained layout blocker remains closed:
`frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterSingleFileView.spec.ts:269`
now submits a real succeeded single-file job, waits for the
history-backed ready state via `getDocumentConverterJobStatus`, and then proves
the same left-source / middle-operations / right-preview ownership after
success. That closes the exact blocker from the prior pass because the test
would fail if the single-file success path pushed filename, download, or save
back into the preview column.

Second review pass on `2026-06-27` revalidated that outcome against the
current working tree after Harvey's follow-up. The rerun still passes and I did
not find a new regression in the changed route or layout ownership specs.

Third review pass on `2026-06-27` rechecked the overseer cleanup delta:
`DocumentConverterSourceIntake.vue`, the action-style split between
`documentConverterWorkspace.css` and `documentConverterPreview.css`, and the
new `DocumentConverterLayoutOwnership.spec.ts`. No findings. The extraction
does not introduce hidden alternate source truth: the route and composables
still own project and single-file state, while `DocumentConverterSourceIntake`
only owns local input element refs and emits typed source-intake events back to
the parent. The CSS split preserves layout ownership because workspace geometry
remains in `documentConverterWorkspace.css`, while result actions stay out of
the preview DOM and are still proven by the project and single-file ownership
tests.

Final visual-polish review pass on `2026-06-27` rechecked the screenshot-driven
CSS delta. No visual findings. `documentConverterWorkspace.css:14` through
`documentConverterWorkspace.css:21` keeps the viewport height budget in CSS,
`documentConverterWorkspace.css:101` through
`documentConverterWorkspace.css:105` preserves the desktop source /
operations / preview grid, and `documentConverterWorkspace.css:394` through
`documentConverterWorkspace.css:445` keeps the responsive single-column port
declarative. `documentConverterPreview.css:134` through
`documentConverterPreview.css:166` places file operations immediately below
the conversion controls and makes the download/save row full-width instead of
half-width. The retained screenshots show the buttons no longer wrap or crowd,
and the refreshed authenticated compact route screenshot shows the action area
and preview below it without the old preview-footer controls.

Residual note: the separate compact "fullpage" layout screenshots in
`.artifacts/pr-0397-layout-screenshots/20260627T102406Z/` are effectively
viewport-height captures, so I treated the authenticated compact route
screenshot at
`.artifacts/authenticated-home-work-apps/20260627T102509Z/document-converter-compact.png`
as the decisive compact visual proof for the polished action area. This is not
approval-blocking because the authenticated proof captures the relevant
no-cramped-buttons state and the focused specs still prove column ownership.

Final corrected-contract review pass on `2026-06-27` rechecked the latest
user-requested delta. No findings. `DocumentConverterView.vue:426` through
`DocumentConverterView.vue:449` renders the generated-output selector and file
actions in the middle operations column, while `DocumentConverterView.vue:452`
through `DocumentConverterView.vue:457` passes only preview state into the
right column. `DocumentConverterArtifactSelector.vue:33` through
`DocumentConverterArtifactSelector.vue:49` renders teacher-facing filenames,
not raw ids, and `documentConverterWorkspace.css:234` through
`documentConverterWorkspace.css:276` bounds the selector with a scrollable
operations-column container. `DocumentConverterResultPanel.vue:21` through
`DocumentConverterResultPanel.vue:50` is preview-only. The removed eyebrow row
is covered by negative assertions in `DocumentConverterLayoutOwnership.spec.ts:140`
through `DocumentConverterLayoutOwnership.spec.ts:142` and
`DocumentConverterSingleFileView.spec.ts:89` through
`DocumentConverterSingleFileView.spec.ts:92`. The previous handoff blocker is
resolved; `pdm run handoff-validate` now passes.

## Changes Made

| Change | Artifact | Description |
|---|---|---|
| 1 | `REV-PR-0397` | Re-reviewed the current PR-0397 working-tree slice against the retained blocker only. |
| 2 | `REV-PR-0397` | Confirmed the strengthened succeeded-state single-file spec now proves the shared three-column contract after success. |
| 3 | `REV-PR-0397` | Marked the decision as `approved` and recorded the remaining live-proof note as residual risk rather than a blocker. |
| 4 | `REV-PR-0397` | Second review pass confirmed the same approval still holds on the latest working tree after Harvey's follow-up. |
| 5 | `REV-PR-0397` | Third review pass confirmed the cleanup extraction, CSS split, and spec split preserve the approved PR-0397 layout contract. |
| 6 | `REV-PR-0397` | Final visual-polish pass confirmed the CSS spacing, full-width action rows, viewport height adjustment, and retained screenshots preserve the approved layout contract. |
| 7 | `REV-PR-0397` | Changed the decision to `changes_requested` because `pdm run handoff-validate` fails on the current tree line budget. |
| 8 | `REV-PR-0397` | Final corrected-contract pass approved the current tree after artifact selection moved to operations, preview became preview-only, stale eyebrow copy was removed, and handoff validation passed. |
| 9 | `REV-PR-0397` | Final typography pass approved the compact selected-source summary demotion and shared text-token cleanup. |
