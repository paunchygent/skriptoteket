---
type: review
id: REV-PR-0385
title: "Review: PR-0385 Document Converter files and history follow-up"
status: approved
owners: "agents"
created: 2026-06-26
updated: 2026-06-26
reviewer: "codex-independent-reviewer"
prs:
  - PR-0385
links:
  - ST-37-04
  - EPIC-37
  - PR-0379
  - REV-PR-0379
  - PR-0384
  - REV-PR-0384
  - PR-0388
  - REV-PR-0388
---

# Review: PR-0385 Document Converter Files And History Follow-up

## TL;DR

The fixed-pass re-review is approved. The current worktree now reopens older
HTML/CSS history entries truthfully, keeps long-running single-file jobs pending
instead of mislabeling them as failed, preserves reopened multi-artifact project
history choices, and correctly hydrates immediately succeeded local single-file
jobs as ready results.

## Problem Statement

`PR-0385` extends the route-visible Document Converter MVP with two sensitive
continuity surfaces: starting from teacher-owned saved files in `Mina filer`
and returning to recent route-session results without pretending there is
durable history. That makes truthfulness the primary review burden: the browser
must not become artifact authority, history must reopen the result the teacher
picked, and nonterminal jobs must not be mislabeled as failures.

## Proposed Solution

Expose scoped saved-file listing and saved-file job submission under the
Document Converter backend namespace, reuse the existing job-creation handler
for server-side reads, and expand `/apps/document-converter` with a single-file
lane plus route-session history for recent preview/job results.

## Artifacts to Review

| File | Focus | Time |
|------|-------|------|
| `docs/backlog/prs/pr-0385-st-37-04-document-converter-files-and-history-follow-up.md` | Scope, goals, decision boundary, claimed proof | 25 min |
| `src/skriptoteket/application/curated_apps/handlers/document_converter_saved_sources.py`, `src/skriptoteket/web/api/v1/apps_conversion_hub_document_converter_saved_files.py`, `src/skriptoteket/application/curated_apps/document_converter.py`, `src/skriptoteket/di/curated_apps.py` | Owner scoping, saved-file authority, route wiring, shared job flow reuse | 45 min |
| `frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterView.vue`, `useDocumentConverterSingleFile.ts`, `useDocumentConverterSessionHistory.ts`, `useDocumentConverterHistoryBridge.ts` | Session-history truthfulness, stale state, retry semantics, preview selection | 75 min |
| `frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterSingleFileControls.vue`, `DocumentConverterSourcePanel.vue`, `DocumentConverterResultPanel.vue`, `documentConverterFileApi.ts` | Visible UI contract, source-selector scope, protected API usage | 35 min |
| `tests/unit/application/curated_apps/handlers/test_document_converter_saved_sources.py`, `tests/unit/web/conversion_hub/test_apps_document_converter_api.py`, `frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterView.spec.ts`, `DocumentConverterSingleFileView.spec.ts`, `documentConverterFileApi.spec.ts` | Behavioral proof strength and missing coverage | 45 min |

**Total estimated time:** ~3.5 hours

## Key Decisions

| Decision | Rationale | Approve? |
|----------|-----------|----------|
| Saved-file intake must stay owner-scoped and server-authoritative through Vault refs, not browser-uploaded bytes. | This is Goal 1’s trust boundary and the current backend implementation follows it. | [x] |
| Current-session history must reopen the result the teacher actually selected, not silently fall back to the latest live preview. | Goal 2 promises useful route-session continuity, so history selection must be truthful. | [x] |
| Nonterminal single-file jobs must remain visibly pending or retryable, not be recorded as failed by timeout heuristics. | A queued/running job is not the same thing as a failed result. | [x] |
| Reopen from saved output remains single-file reuse only, not project-workspace restore. | The current slice must not overbuild a fake saved-project story. | [x] |

## Review Checklist

- [x] Saved-file listing is owner-scoped and filters out unsupported file types.
- [x] Saved-file submission reuses the backend job-creation path without browser byte authority.
- [x] Cross-owner/deleted saved-file refs fail closed in the application layer.
- [x] Route-session history truthfully returns the teacher to the selected earlier project preview.
- [x] Single-file status handling distinguishes nonterminal work from real failure.
- [x] Visible UI copy avoids raw preview ids, artifact ids, producer names, TTLs, and filesystem/path leaks.

## Review Feedback

**Reviewer:** `codex-independent-reviewer`
**Date:** `2026-06-26`
**Verdict:** `approved`

### Required Changes

None.

### Suggestions (Non-blocking)

- The current PR does not appear to worsen Document Converter saved-output naming, and the stable `source_artifact_id` boundary from earlier slices is still intact. The broader cross-app filename protocol concern should stay a separate governed follow-up rather than being quietly expanded here.

### Re-review Outcome

The fixed-pass worktree resolves both prior high findings and the adjacent
frontend regressions called out during remediation close-out:

1. `frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterView.vue`
   now treats only `history.activeEntry.id === project.activePreviewEntryId`
   as live project state, so selecting an older project-history entry reloads
   that entry's own preview/actions instead of silently falling back to the
   newest live preview.
2. `frontend/apps/skriptoteket/src/views/apps/document-converter/useDocumentConverterSessionHistory.ts`
   and `useDocumentConverterHistoryBridge.ts` now preserve per-entry artifact
   lists and artifact-scoped preview/download/save callbacks for reopened
   historical `separate_pdfs` results.
3. `frontend/apps/skriptoteket/src/views/apps/document-converter/useDocumentConverterSingleFile.ts`
   no longer translates bounded `queued`/`running` polling into failure; it
   leaves those jobs pending and fetches the real status for immediately
   terminal jobs so ready local conversions become ready history entries.
4. Focused Vitest now truthfully covers the repaired history revisit, pending
   long-running single-file jobs, immediate ready single-file jobs, and the
   reopened multi-artifact project-history regression.

No blocking findings remain in the PR-0385 implementation scope.

## Verification

- Reviewed `AGENTS.md`, `.codex/handoff.md`, `.codex/rules/000-rule-index.md`,
  `.codex/rules/040-fastapi-blueprint.md`,
  `.codex/rules/042-async-di-patterns.md`,
  `.codex/rules/045-huleedu-design-system.md`,
  `.codex/rules/050-python-standards.md`,
  `.codex/rules/070-testing-standards.md`,
  `.codex/rules/096-review-workflow.md`,
  `docs/index.md`,
  `docs/reference/ref-review-workflow.md`,
  `docs/backlog/prs/pr-0385-st-37-04-document-converter-files-and-history-follow-up.md`,
  and the routed `ruthless-code-review`, `testing`,
  `skriptoteket-testing`, and `skriptoteket-backend-dev` guidance.
- `git status --short`
  Confirmed the worktree is dirty in the expected PR-0385 scope plus existing
  handoff/doc updates; no unrelated edits were reverted.
- `git diff --stat`
  Confirmed the reviewed scope is the saved-file backend/API slice, the
  expanded Document Converter frontend route, generated API types, and focused
  tests.
- `pdm run fe-test -- --run src/views/apps/document-converter/DocumentConverterView.spec.ts src/views/apps/document-converter/DocumentConverterProjectResult.spec.ts src/views/apps/document-converter/DocumentConverterSingleFileView.spec.ts src/views/apps/document-converter/documentConverterFileApi.spec.ts`
  Passed: `4` files, `16` tests after the visible history rail was removed.
- `pdm run docs-validate`
  Passed.
- Inspected the backend saved-file flow in
  `src/skriptoteket/application/curated_apps/handlers/document_converter_saved_sources.py`
  and confirmed it reuses `CreateDocumentConverterJobsHandler` with a
  server-built `ConversionHubUpload`.
- Inspected the existing save-artifact coverage in
  `tests/unit/application/curated_apps/handlers/test_document_converter_artifact_saves.py`
  and `tests/unit/application/curated_apps/handlers/test_document_converter_local_artifact_actions.py`
  to confirm the stable saved-name/source-reference boundary still exists from
  prior approved slices.
- I did not rerun live authenticated browser proof for this fixed-pass review.
  The approved changes are contained to route-state truthfulness and focused
  Vitest coverage was sufficient for this scope.

## Changes Made

| Change | Artifact | Description |
|--------|----------|-------------|
| 1 | `REV-PR-0385` | Created the retained independent review record for the Document Converter files/history follow-up slice. |
| 2 | `REV-PR-0385` | Recorded the original blocking findings covering project-history revisit truthfulness and single-file timeout-to-failure misclassification. |
| 3 | `REV-PR-0385` | Re-reviewed the remediation pass, confirmed the two high findings and adjacent frontend regressions are fixed, and approved the slice. |

## Remediation Follow-up

On `2026-06-26`, the implementer applied a narrow follow-up pass against the
review findings and the adjacent regressions surfaced by the first sole-reviewer
rerun:

- Project-mode history now treats only the active live preview entry as live
  state, while older HTML/CSS history selections reload their own preview blob
  and per-artifact download/save callbacks.
- Historical `separate_pdfs` project results now preserve access to their full
  artifact set instead of collapsing to the first PDF only.
- Single-file polling now keeps queued/running jobs pending after the bounded
  polling budget and hydrates immediately terminal jobs from the real status
  endpoint so ready local conversions do not become false failures.

Focused remediation proof captured locally:

- Red:
  - `pdm run fe-test -- --run src/views/apps/document-converter/DocumentConverterView.spec.ts`
    failed before the fix because older multi-artifact history entries reopened
    without any artifact selector.
  - `pdm run fe-test -- --run src/views/apps/document-converter/DocumentConverterSingleFileView.spec.ts`
    failed before the fix because an immediately succeeded local job never
    fetched job status and was recorded as failed.
- Green:
  - `pdm run fe-test -- --run src/views/apps/document-converter/DocumentConverterView.spec.ts`
  - `pdm run fe-test -- --run src/views/apps/document-converter/DocumentConverterSingleFileView.spec.ts`
  - `pdm run fe-test -- --run src/views/apps/document-converter/DocumentConverterView.spec.ts src/views/apps/document-converter/DocumentConverterProjectResult.spec.ts src/views/apps/document-converter/DocumentConverterSingleFileView.spec.ts`
  - `pdm run fe-type-check`
  - `pdm run fe-lint`
  - `pdm run docs-validate`
  - `pdm run handoff-validate`
  - `git diff --check`

The fixed-pass independent re-review is complete and approved.

## Product Correction Addendum

On `2026-06-27`, product direction superseded the visible route-session history
surface approved above. The saved-file backend boundary remains valid, but the
route-visible UI now removes the history rail, uses tabs above the
mode-specific workspace, names the file lane `Filkonvertering`, keeps
current-result state private to the route, and exposes ordered local upload
batches through the existing backend upload job contract. Multi-source
`Mina filer` batches and combined/concatenated general file-conversion outputs
remain unapproved until a backend artifact contract exists.
