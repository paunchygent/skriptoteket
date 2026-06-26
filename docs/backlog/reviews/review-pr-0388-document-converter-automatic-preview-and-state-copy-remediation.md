---
type: review
id: REV-PR-0388
title: "Review: PR-0388 Document Converter automatic preview and state-copy remediation"
status: approved
owners: "agents"
created: 2026-06-25
updated: 2026-06-26
reviewer: "codex-independent-reviewer"
prs:
  - PR-0388
links:
  - ST-37-04
  - EPIC-37
  - PR-0384
  - REV-PR-0384
  - PR-0387
---

# Review: PR-0388 Document Converter Automatic Preview And State-Copy Remediation

## TL;DR

Pre-implementation review remains valid, and the route/composable/test patch is
aligned with the approved PR-0388 behavior. The retained re-review of the
repaired Grid fallback package is now complete and approved.

Grid-heavy teacher HTML/CSS remains in scope for this slice. The scoped preview
contract is best-effort teacher output: native Grid rendering is attempted
first, and if WeasyPrint hits the known internal Grid `AssertionError`, the app
must degrade through an owned print-compatibility path rather than fail the
whole preview. Exact native Grid layout fidelity is not a separate
teacher-facing contract for this slice.

## Problem Statement

`PR-0384` made `/apps/document-converter` truthful enough to ship as a
route-visible MVP, but it still presents a manual `Förhandsvisa` flow and
artifact-oriented preview state rather than a real embedded PDF preview. This
review checks whether `PR-0388` describes the next implementation slice
precisely enough to let a frontend specialist land the remediation without
guessing about stale preview truthfulness, copy boundaries, artifact authority,
or proof expectations.

## Proposed Solution

Move preview generation into app-owned automatic behavior, debounce render
triggers after governed input changes, ignore stale responses, embed the
current server-owned PDF artifact visually, and remove the manual preview
button plus the readiness/eyebrow state-copy leftover from `PR-0384`.

## Artifacts to Review

| File | Focus | Time |
|------|-------|------|
| `docs/backlog/prs/pr-0388-st-37-04-document-converter-automatic-preview-and-state-copy-remediation.md` | Governing behavior, proof plan, stop conditions | 45 min |
| `docs/backlog/prs/pr-0384-st-37-04-document-converter-route-visible-mvp-implementation.md` | Current route-visible contract being amended | 20 min |
| `docs/backlog/reviews/review-pr-0384-document-converter-route-visible-mvp-implementation.md` | Accepted repair history, especially stale-preview recovery | 25 min |
| `docs/backlog/prs/pr-0387-st-37-04-document-converter-small-screen-mockup-remediation.md` | Confirmed UI/copy boundaries already settled | 10 min |
| `frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterView.vue` | Current manual-preview/readiness/eyebrow surface | 25 min |
| `frontend/apps/skriptoteket/src/views/apps/document-converter/useDocumentConverterProjectPreview.ts` | Current preview state, retry, and stale behavior | 30 min |
| `frontend/apps/skriptoteket/src/views/apps/document-converter/documentConverterProjectPreviewApi.ts` | Artifact authority and preview-download boundary | 15 min |

**Total estimated time:** ~2.5 hours

## Key Decisions

| Decision | Rationale | Approve? |
|----------|-----------|----------|
| Automatic preview should replace the persistent `Förhandsvisa` button. | The current route is product-misaligned and asks teachers to drive app timing manually. | [x] |
| The success state must be a real embedded PDF, not artifact-only state. | `Preview` is not truthful unless the teacher can actually see the rendered PDF. | [x] |
| Preview artifact authority must remain server-owned through Skriptoteket endpoints only. | Prevents raw paths, browser-authored authority, or direct Sir Convert browser calls. | [x] |
| The package must explicitly define stale failed-refresh behavior before implementation. | Automatic refresh makes stale artifact truthfulness a core contract, not an implementation detail. | [x] |
| Proof must target the legacy readiness/eyebrow surfaces structurally, not ban generic words like `Mall` or `PDF`. | The route still needs legitimate template/media vocabulary after remediation. | [x] |

## Review Checklist

- [x] The package keeps the route inside the existing scoped project-preview API boundary.
- [x] The package removes the persistent preview button and readiness bookkeeping as intended.
- [x] The package requires a real embedded PDF preview rather than artifact-only state.
- [x] The package keeps artifact authority server-owned and forbids raw paths/direct Sir Convert browser calls.
- [x] The package fully specifies how auto-refresh failure interacts with a previously successful preview.
- [x] The proof language distinguishes forbidden legacy surfaces from still-allowed product vocabulary.

## Review Feedback

**Reviewer:** `codex-independent-reviewer`
**Date:** `2026-06-26`
**Verdict:** `approved`

### Pre-Implementation Outcome

The two prior blockers are resolved:

1. `PR-0388` now defines the failed-refresh contract directly in acceptance
   criteria, product decisions, implementation plan, and proof obligations:
   after a successful preview, a failed automatic refresh may leave the old PDF
   visible only as recovery context while `Ladda ned` / `Spara i Mina filer`
   stay disabled until the latest selected state renders successfully.
2. The proof plan now targets the real forbidden surfaces structurally: the
   readiness-status section that pairs `Filer` / `Mall` / `PDF` with `Klar`,
   the persistent `Förhandsvisa` button, and the `Tillfällig förhandsvisning`
   eyebrow/status label. The doc also explicitly preserves truthful uses of the
   template label `Mall` and ordinary `PDF` media/result copy.

No remaining blocking findings were identified in the package.

### Required Changes

None.

### Suggestions (Non-blocking)

- Once the blocking clarifications land, extend the live proof to change at
  least one governed output control after the first successful preview so the
  retained artifact shows automatic refresh beyond initial upload.
- Keep the browser-proof artifact machine-readable enough to record which
  preview artifact was current before the download/save enablement check.

### Post-Implementation Review

The implemented route/composable/test changes still match the approved product
shape in the reviewed frontend code:

- automatic debounced preview replaced the persistent `Förhandsvisa` button;
- the readiness-status section, eyebrow label, and discard CTA are removed;
- the route embeds a blob-backed PDF iframe and disables download/save while the
  current selection is stale, loading, or failed;
- focused Vitest covers auto-preview, stale-render race, failed-refresh recovery,
  and object-URL cleanup behaviors.

The repaired backend renderer/proof portion now also satisfies the retained
review requirements:

- the new grid-compat helper scopes softening to CSS surfaces and preserves
  visible teacher body text in the forced fallback proof;
- the retry gate no longer catches unrelated assertions and now requires a
  WeasyPrint `layout/grid.py` traceback before activating compatibility retry;
- the retained browser-proof artifact now proves a real rendered PDF through
  downloaded-PDF text extraction plus rendered PNG checks, not only iframe
  presence.

#### Blocking Findings

None.

### Implementer Evidence Reviewed (2026-06-26)

- `pyproject.toml` / `pdm.lock` now lock WeasyPrint `69.0`; host and container
  probes through PDM both printed `69.0`.
- BuildKit image rebuilds were run after the dependency/source changes. The
  final clean rebuild log is retained at `.artifacts/pr-0388-web-build-final-clean.log`
  and ends with `Image windsurf-project-web Built`; `skriptoteket_web` was
  recreated from that image.
- Focused backend renderer lane passed:
  `DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib pdm run test tests/unit/application/curated_apps/test_document_converter_project_manifest.py tests/unit/infrastructure/documents/test_document_converter_project_previews.py tests/unit/infrastructure/documents/test_document_converter_project_renderer_best_effort.py`
  plus `tests/unit/cli/test_cleanup_document_converter_project_previews.py`
  passed with `43 passed`.
- Fresh governed live proof passed:
  `/opt/homebrew/bin/pdm run python -m scripts.authenticated_home_work_apps`
  produced `.artifacts/authenticated-home-work-apps/20260626T031626Z/`; the
  manifest records `grid_layout_fixture_rendered=true`, expected text,
  CSS/image accent pixels, missing-resource text, no raw external URL text, no
  raw filesystem path text, refreshed blob iframe source, and enabled artifact
  actions.
- The matching Docker log window records native WeasyPrint Grid `AssertionError`,
  then `Document Converter project preview retried with grid compatibility
  fallback.`, followed by preview POST/artifact GET `200` responses. That is
  acceptable evidence for the scoped best-effort preview contract and should be
  reviewed for sandboxing, product truthfulness, and maintainability.

## Verification

- Reviewed `AGENTS.md`, `.codex/handoff.md`, `.codex/rules/000-rule-index.md`,
  `.codex/rules/096-review-workflow.md`, `docs/index.md`,
  `docs/reference/ref-review-workflow.md`,
  `docs/backlog/prs/pr-0388-st-37-04-document-converter-automatic-preview-and-state-copy-remediation.md`,
  `docs/backlog/prs/pr-0384-st-37-04-document-converter-route-visible-mvp-implementation.md`,
  `docs/backlog/reviews/review-pr-0384-document-converter-route-visible-mvp-implementation.md`,
  `docs/backlog/prs/pr-0387-st-37-04-document-converter-small-screen-mockup-remediation.md`,
  and the routed `ruthless-code-review`, `testing`, `agent-docs-governance`,
  `integrated-frontend-stack`, and `local-devops` guidance.
- `git status --short`
  Confirmed a dirty docs worktree already existed in `main`; no unrelated edits
  were reverted or overwritten.
- Calibrated the package against the current route/manual-preview behavior in
  `DocumentConverterView.vue`, `useDocumentConverterProjectPreview.ts`, and
  `documentConverterProjectPreviewApi.ts`.
- Re-reviewed the amended `PR-0388` package and confirmed both prior blockers
  are resolved in the governing doc itself.
- Overeer-supplied validation evidence:
  `git diff --check`
  Passed before re-review request.
- Post-implementation scope reviewed:
  `src/skriptoteket/infrastructure/documents/document_converter_project_preview_grid_compat.py`,
  `src/skriptoteket/infrastructure/documents/document_converter_project_previews.py`,
  `src/skriptoteket/infrastructure/documents/document_converter_project_preview_store.py`,
  `src/skriptoteket/di/curated_apps.py`,
  `src/skriptoteket/cli/commands/cleanup_document_converter_project_previews.py`,
  `tests/unit/infrastructure/documents/test_document_converter_project_previews.py`,
  `tests/unit/infrastructure/documents/test_document_converter_project_renderer_best_effort.py`,
  `tests/unit/cli/test_cleanup_document_converter_project_previews.py`,
  `frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterView.vue`,
  `frontend/apps/skriptoteket/src/views/apps/document-converter/useDocumentConverterProjectPreview.ts`,
  `frontend/apps/skriptoteket/src/views/apps/document-converter/documentConverterProjectPreviewApi.ts`,
  `frontend/apps/skriptoteket/src/views/apps/document-converter/documentConverterWorkspace.css`,
  `frontend/apps/skriptoteket/src/views/apps/document-converter/documentConverterPreview.css`,
  `frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterView.spec.ts`,
  `scripts/authenticated_home_work_apps.py`, and
  `.artifacts/authenticated-home-work-apps/20260626T031626Z/manifest.redacted.json`
  plus the retained route screenshots and rendered preview PDF/PNG metadata.
- Inspected current WeasyPrint stable docs for custom `URLFetcher` restrictions
  and documented Grid limitations to calibrate the bounded compatibility retry.
- `pdm run fe-test -- --run src/views/apps/document-converter/DocumentConverterView.spec.ts`
  Passed: `1` file, `8` tests.
- `DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib /opt/homebrew/bin/pdm run test tests/unit/infrastructure/documents/test_document_converter_project_previews.py tests/unit/infrastructure/documents/test_document_converter_project_renderer_best_effort.py tests/unit/cli/test_cleanup_document_converter_project_previews.py`
  Passed: `28` tests. This rerun directly exercised the forced Grid fallback,
  unrelated-assertion rejection, preview-store behavior, and cleanup CLI.
- `PYTHONPATH=src python3`
  Probed `prepare_grid_compatibility_html(...)` directly to confirm visible body
  text containing `display:grid` stays unchanged while CSS in `<style>` blocks
  is softened only on the fallback path.
- `pdm run docs-validate`
  Passed.
- `pdm run handoff-validate`
  Passed.

## Changes Made

| Change | Artifact | Description |
|--------|----------|-------------|
| 1 | `REV-PR-0388` | Created the retained independent review record for the pre-implementation PR-0388 package. |
| 2 | `REV-PR-0388` | Recorded two blocking package-level findings covering stale failed-refresh truthfulness and ambiguous forbidden-copy proof language. |
| 3 | `REV-PR-0388` | Re-reviewed the amended PR package, confirmed both blockers were resolved, and approved the implementation package. |
| 4 | `REV-PR-0388` | Added the post-implementation review pass and kept the review pending while the repaired best-effort Grid proof is audited. |
| 5 | `REV-PR-0388` | Completed the retained re-review of the repaired Grid fallback package and approved the implementation/evidence package. |
