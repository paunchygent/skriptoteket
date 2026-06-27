---
type: review
id: REV-PR-0396
title: "Review: PR-0396 Document Converter save/export naming adoption"
status: approved
owners: "agents"
created: 2026-06-27
updated: 2026-06-27
reviewer: "codex"
prs:
  - "PR-0396"
links:
  - "EPIC-37"
  - "ST-37-05"
  - "PR-0385"
  - "REV-ST-37-05"
---

## TL;DR

The second pass resolves the two first-pass proof gaps. The protected
Document Converter download/save router tests now prove `filename_stem`
plumbing and backend-owned final filenames, and the route-visible view spec now
proves the editable filename field drives save/download actions. No blocking
findings remain.

## Problem Statement

`PR-0396` adopts the ST-37-05 save/export naming protocol for Document
Converter single-file outputs and HTML/CSS project previews. This review checks
whether the working-tree change keeps filename authority on the protected
backend/API, preserves the PR-0385 saved-source boundary, and proves the new
editable filename flow at the right boundaries.

## Proposed Solution

Introduce a backend-owned Document Converter naming helper, thread optional
`filename_stem` intent through the protected download/save endpoints, expose the
editable stem in the result panel, and reuse Vault-side disambiguation for
repeated saves.

## Artifacts to Review

| File | Focus | Time |
|------|-------|------|
| `docs/backlog/prs/pr-0396-st-37-05-document-converter-save-export-naming-adoption.md` | Governing scope and acceptance criteria | 5 min |
| `docs/reference/ref-file-naming-save-export-protocol-v1.md` | Shared filename protocol authority | 5 min |
| `src/skriptoteket/application/curated_apps/document_converter_file_naming.py` | Backend filename authority and validation | 10 min |
| `src/skriptoteket/web/api/v1/apps_conversion_hub.py` | Single-file protected API contract | 5 min |
| `src/skriptoteket/web/api/v1/apps_conversion_hub_document_converter_project_previews.py` | Project-preview protected API contract | 5 min |
| `frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterView.vue` | Route-visible filename editing flow | 10 min |
| `tests/unit/application/curated_apps/handlers/test_document_converter_naming_adoption.py` | Application-level proof | 10 min |
| `tests/unit/web/conversion_hub/test_apps_document_converter_api.py` | Single-file API proof | 5 min |
| `tests/unit/web/conversion_hub/test_apps_document_converter_project_preview_api.py` | Project-preview API proof | 5 min |
| `frontend/apps/skriptoteket/src/views/apps/document-converter/*.spec.ts` | Route-visible UI proof | 10 min |

**Total estimated time:** ~70 minutes

## Key Decisions

| Decision | Rationale | Approve? |
|----------|-----------|----------|
| Keep backend/API as the final filename authority | Matches ST-37-05 and avoids browser-owned filename truth | [x] |
| Reuse separate labels for single-file and project-preview outputs | Matches the reviewed protocol vocabulary | [x] |
| Use repeat-save disambiguation instead of update-in-place saves | Matches the default shared collision policy | [x] |
| Accept the current proof as sufficient for the new `filename_stem` flow | Public and route-visible proof now covers the contract | [x] |

## Review Checklist

- [x] Scope is bounded and appropriate
- [x] Acceptance criteria or proof obligations are reviewable
- [x] Risks and structural fault lines are called out explicitly
- [x] Verification plan matches the claimed contract
- [x] Backend/application tests prove default naming and repeat-save behavior
- [x] Public API and route-visible UI proof fully cover the editable stem flow

## Review Feedback

**Reviewer:** codex
**Date:** 2026-06-27
**Verdict:** approved

### First Pass 2026-06-27

#### [Medium] Missing FastAPI contract proof for the new `filename_stem` query surface

**File reference:** `tests/unit/web/conversion_hub/test_apps_document_converter_api.py:425`

The protected download/save routes now accept `filename_stem` and pass it into
the application handlers at `src/skriptoteket/web/api/v1/apps_conversion_hub.py:363-410`,
and the project-preview routes do the same at
`src/skriptoteket/web/api/v1/apps_conversion_hub_document_converter_project_previews.py:103-152`.
But the retained router tests still exercise only the legacy "ID-only" shape in
`tests/unit/web/conversion_hub/test_apps_document_converter_api.py:425-474` and
`tests/unit/web/conversion_hub/test_apps_document_converter_project_preview_api.py:232-267`.
They never call the endpoints with `filename_stem`, never assert that the
handler receives it, and never prove that the backend-owned final filename is
what comes back through `Content-Disposition` or the save response.

Why it matters: the public contract changed on four protected endpoints. A
regression in FastAPI query parsing or handler plumb-through would leave the
frontend helper specs green while the real API silently ignores teacher-edited
names.

Concrete fix: extend both web test modules so each download/save route is
exercised with a non-empty `filename_stem`, the fake handler call records that
value, and the asserted response filename comes from the backend-owned final
name rather than a hard-coded legacy stub.

Proof requirement: rerun
`/opt/homebrew/bin/pdm run test tests/unit/application/curated_apps/handlers/test_document_converter_artifact_saves.py tests/unit/application/curated_apps/handlers/test_document_converter_project_previews.py tests/unit/application/curated_apps/handlers/test_document_converter_naming_adoption.py tests/unit/web/conversion_hub/test_apps_document_converter_api.py tests/unit/web/conversion_hub/test_apps_document_converter_project_preview_api.py`
and show the updated router assertions passing.

#### [Medium] Route-visible tests do not prove that the editable filename field drives save/download actions

**File reference:** `frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterView.spec.ts:164`

`DocumentConverterView.vue` now owns a new user-visible contract: it seeds
`filenameStemIntent`, renders the `Filnamn` input, and forwards the edited stem
into both live-project and history save/download actions at
`frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterView.vue:193-299`.
But the focused view specs under
`frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterView.spec.ts:164-260`
and `DocumentConverterProjectResult.spec.ts:137-229` were not extended for that
behavior. The only new frontend proof is in the API helper specs, which assert
query-string construction after the route has already decided what to send.

Why it matters: the acceptance criterion is teacher-facing. A wiring bug in the
view or filename-intent composable would still let the helper specs pass while
the `/apps/document-converter` UI ignores the edited name the teacher typed.

Concrete fix: add route-visible Vitest coverage that types into
`[data-testid="document-converter-filename-stem"]`, triggers download/save for
both a live project-preview result and a history-backed result, and asserts the
mocked API boundaries receive the edited stem. Also prove the field resets when
the selected artifact/result changes.

Proof requirement: rerun
`/opt/homebrew/bin/pdm run fe-test -- --run src/views/apps/document-converter/documentConverterFileApi.spec.ts src/views/apps/document-converter/documentConverterProjectPreviewApi.spec.ts src/views/apps/document-converter/DocumentConverterView.spec.ts src/views/apps/document-converter/DocumentConverterSingleFileView.spec.ts src/views/apps/document-converter/DocumentConverterProjectResult.spec.ts`
with the new route-level assertions included.

### Second Pass Re-Review 2026-06-27

**Scope reviewed**

- `tests/unit/web/conversion_hub/test_apps_document_converter_api.py`
- `tests/unit/web/conversion_hub/test_apps_document_converter_project_preview_api.py`
- `frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterView.spec.ts`

The second pass resolves both first-pass findings:

- The single-file and project-preview FastAPI router tests now call the routes
  with `filename_stem`, assert the handler receives that value, and assert the
  response/save payload surfaces the backend-owned final filename instead of a
  browser-reconstructed name.
- The route-visible `DocumentConverterView.spec.ts` now edits
  `[data-testid="document-converter-filename-stem"]` and proves the mocked
  save/download API boundary receives the teacher-edited stem for both the
  live project-preview result and the history-backed result path after the mode
  switch.

I did not find a regression or truthfulness issue in the new tests. They assert
the real boundary that would fail if the new filename-intent wiring were broken.

No blocking findings remain.

### Suggestions (Optional)

- Add one focused backend unit test for `filename_stem` validation and
  duplicate-extension stripping in
  `tests/unit/application/curated_apps/handlers/test_document_converter_naming_adoption.py`
  so the helper contract is not only covered indirectly.

### Decision Approvals

- [x] Backend/API remains the final filename authority.
- [x] Canonical purpose labels and repeated-save disambiguation match ST-37-05.
- [x] The current proof is sufficient to approve the new editable-stem flow.

## Changes Made

| Change | Artifact | Description |
|--------|----------|-------------|
| 1 | `REV-PR-0396` | Created the retained PR review record for the working-tree PR-0396 implementation. |
| 2 | `REV-PR-0396` | Recorded public-API proof gaps for the new `filename_stem` contract. |
| 3 | `REV-PR-0396` | Recorded route-visible UI proof gaps for the editable filename field. |
| 4 | `REV-PR-0396` | Re-reviewed Aristotle's second-pass test updates and confirmed both findings are resolved. |
| 5 | `REV-PR-0396` | Flipped the retained review decision to `approved`. |

## Verification

- `/opt/homebrew/bin/pdm run test tests/unit/application/curated_apps/handlers/test_document_converter_artifact_saves.py tests/unit/application/curated_apps/handlers/test_document_converter_project_previews.py tests/unit/application/curated_apps/handlers/test_document_converter_naming_adoption.py tests/unit/web/conversion_hub/test_apps_document_converter_api.py tests/unit/web/conversion_hub/test_apps_document_converter_project_preview_api.py` -> `34 passed in 2.00s`
- `/opt/homebrew/bin/pdm run fe-test -- --run src/views/apps/document-converter/documentConverterFileApi.spec.ts src/views/apps/document-converter/documentConverterProjectPreviewApi.spec.ts src/views/apps/document-converter/DocumentConverterView.spec.ts src/views/apps/document-converter/DocumentConverterSingleFileView.spec.ts src/views/apps/document-converter/DocumentConverterProjectResult.spec.ts` -> `5 passed, 20 passed`
- `/opt/homebrew/bin/pdm run test tests/unit/web/conversion_hub/test_apps_document_converter_api.py tests/unit/web/conversion_hub/test_apps_document_converter_project_preview_api.py` -> `17 passed in 1.06s`
- `/opt/homebrew/bin/pdm run fe-test -- --run src/views/apps/document-converter/DocumentConverterView.spec.ts` -> `1 file passed, 7 tests passed`
- `/opt/homebrew/bin/pdm run docs-validate` -> passed
- `git diff --check` -> passed

## Residual Risks / Gates Not Run

- Did not rerun `pdm run lint`, `pdm run typecheck`, `pdm run fe-type-check`,
  `pdm run fe-lint`, `pdm run fe-build`, `pdm run fe-gen-api-types`, or
  `pdm run handoff-validate` during this second-pass re-review.
