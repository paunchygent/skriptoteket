---
type: review
id: REV-PR-0405
title: "Review: PR-0405 Document Converter column hierarchy and preview empty state"
status: approved
owners: "agents"
created: 2026-06-29
updated: 2026-06-29
reviewer: "Codex independent review"
prs:
  - PR-0405
links:
  - ST-37-04
---

## TL;DR

Approved. The current PR-0405 worktree, including the final CSS-only
typography/height adjustment after `5cf76513`, satisfies the route-visible
polish contract: `Källa`, `Konvertering`, and `Resultat` are stable column
headers across both Document Converter modes; shared column headers now use the
quieter `text-base` / `bold` token treatment with a `3.75rem` aligned header
band; the empty filename field is disabled, empty, and uses placeholder
`filnamn`; the empty preview is a preview-shaped `Förhandsvisning` surface; and
download/save/filename/artifact selection ownership remains in the operations
column rather than moving back into preview.

## Problem Statement

`PR-0405` checks a narrow Document Converter presentation correction under
`ST-37-04`: the workbench needed a stronger left/middle/right column grammar
and quieter empty-result semantics without changing backend, API, artifact,
save, download, preview touch/pinch, or conversion behavior.

## Proposed Solution

The implementation introduces route-local column headers for the source,
operations, and result columns, keeps mode-specific controls as subordinate
field labels, separates preview title copy from editable filename state, adds a
token-driven preview empty-state silhouette labeled `Förhandsvisning`, aligns
all shared column header bands at `3.75rem` with `text-base` / `bold` headings,
and updates retained proof helpers so result filenames are asserted in the
operations filename field.

## Artifacts to Review

| File | Focus | Reviewed |
|------|-------|----------|
| `docs/backlog/prs/pr-0405-st-37-04-document-converter-column-hierarchy-and-preview-empty-state.md` | Authority, acceptance criteria, evidence | yes |
| `docs/backlog/stories/story-37-04-app-presentation-decomposition-and-naming-reset.md` | Parent story and scope boundary | yes |
| `.codex/handoff.md` | Volatile state and retained proof path | yes |
| `docs/index.md` | Docs index link | yes |
| `frontend/apps/skriptoteket/src/views/apps/document-converter/*` | UI ownership, copy, CSS-only header alignment, tests | yes |
| `scripts/_document_converter_proof.py` | Project-preview proof helper filename ownership | yes |
| `scripts/_document_converter_single_file_proof.py` | Single-file proof helper filename ownership | yes |
| `.artifacts/authenticated-home-work-apps/20260629T005352Z/manifest.redacted.json` | Existing retained shared-auth proof evidence | yes |

## Key Decisions

| Decision | Rationale | Approve? |
|----------|-----------|----------|
| Keep file actions and filename editing in the operations column | Matches `PR-0397` and `PR-0403` ownership; preview remains display-only apart from zoom controls | yes |
| Use `Resultat` as the preview column header, not the editable filename fallback | Prevents the empty filename field from implying a fake result exists | yes |
| Preserve `Konvertering` as the middle-column header in both modes | Gives `HTML/CSS-projekt` and `Filkonvertering` the same column grammar while leaving mode-specific labels below | yes |
| Tone shared column headers down to `text-base` / `bold` and `3.75rem` | Keeps the column hierarchy distinct without making workbench headers read like app/page titles; the change is CSS-only and token-driven | yes |
| Accept existing shared-auth proof without rerun after the final CSS-only typography/height tweak | Operator explicitly requested no auth-heavy rerun because the HuleEdu auth lane recently hit `RATE_LIMIT`; focused post-tweak tests, static CSS review, and the existing retained proof cover the narrow presentation risk | yes |

## Review Checklist

- [x] Scope is bounded to PR-0405 and does not reopen backend/API/artifact contracts.
- [x] Acceptance criteria are directly represented in rendered UI tests.
- [x] Column headers are stable across both modes.
- [x] Empty filename state is disabled, empty, and uses placeholder `filnamn`.
- [x] Empty preview state is labeled `Förhandsvisning` and does not repeat source instructions.
- [x] File actions, artifact selection, download, save, and filename editing stay outside preview.
- [x] Final CSS-only alignment and typography/height adjustment keep layout ownership in CSS.
- [x] Proof-helper updates assert filenames in operations rather than preview header.
- [x] Verification evidence is truthful and tied to current command surfaces.

## Review Feedback

**Reviewer:** Codex independent review
**Date:** 2026-06-29
**Verdict:** approved

### Required Changes

None.

### Findings

None.

### Evidence Reviewed

- Existing retained shared-auth proof:
  `.artifacts/authenticated-home-work-apps/20260629T005352Z/manifest.redacted.json`
  has `status: ok`, route screenshots for desktop/tablet/compact, successful
  Document Converter render/download proof, zoom-control proof, and no
  forbidden artifact marker hits.
- Retained desktop screenshot from that artifact shows the `Källa` /
  `Konvertering` / `Resultat` header band with preview zoom controls visible
  and no file actions in the preview column. The later token/height tweak was
  reviewed from the current CSS worktree rather than by rerunning the
  authenticated proof.
- Current CSS inspection confirms the final shared header tokens:
  `frontend/apps/skriptoteket/src/views/apps/document-converter/documentConverterWorkspace.css`
  sets `.dc-column-header` to `min-height: 3.75rem`,
  `var(--huleedu-text-base)`, and `var(--huleedu-font-bold)`;
  `frontend/apps/skriptoteket/src/views/apps/document-converter/documentConverterPreview.css`
  applies the same `3.75rem`, `text-base`, and `bold` treatment to
  `.dc-column-header--preview`.
- Current focused post-alignment test rerun:
  `pdm run fe-test -- --run frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterLayoutOwnership.spec.ts frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterResultPanel.spec.ts`
  passed with 13 tests.
- Current full focused PR-0405 frontend test rerun:
  `pdm run fe-test -- --run frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterLayoutOwnership.spec.ts frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterResultPanel.spec.ts frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterView.spec.ts frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterSingleFileView.spec.ts frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterProjectResult.spec.ts`
  passed with 33 tests.
- Current script-surface test rerun:
  `pdm run test tests/unit/scripts/test_playwright_script_surface.py`
  passed with 7 tests.
- `git diff --check 5cf76513^ 5cf76513` passed.
- Current reviewer rerun of `git diff --check` passed for the worktree that
  includes the final CSS-only typography/height adjustment.

### Notes

- The review did not rerun
  `pdm run python -m scripts.authenticated_home_work_apps --base-url http://localhost:5173 --artifact-root .artifacts/authenticated-home-work-apps --timeout-seconds 120`
  because the user explicitly instructed reviewers not to rerun the auth-heavy
  shared-auth proof after the final CSS-only presentation tweaks, and the lane
  had recently hit the real HuleEdu `RATE_LIMIT` guard. The existing retained
  proof path, current focused PR-0405 tests, `git diff --check`, and static CSS
  inspection are sufficient for this narrow approval.
- `DocumentConverterView.vue` is now just over the repo's rough 400-500 LoC
  target at 506 lines. That is a residual maintainability risk, not a blocker
  for this narrow polish slice, because the PR behavior is covered and no new
  responsibility was moved into the route host.

### Suggestions (Optional)

None required for PR-0405.

### Decision Approvals

- [x] Approve PR-0405 column hierarchy and empty preview state.
- [x] Approve proof-helper updates for operations-column filename ownership.
- [x] Approve recorded evidence without an additional shared-auth rerun.

## Changes Made

| Change | Artifact | Description |
|--------|----------|-------------|
| 1 | `PR-0405` | Added stable column headers and empty-state copy/placeholder behavior. |
| 2 | `PR-0405` | Updated retained proof helpers to assert filenames in operations. |
| 3 | `PR-0405` | Applied the final CSS-only shared-header treatment: `text-base`, `bold`, and `3.75rem`. |
| 4 | `REV-PR-0405` | Recorded independent retained review decision as approved, including the no-Playwright-rerun rationale. |
