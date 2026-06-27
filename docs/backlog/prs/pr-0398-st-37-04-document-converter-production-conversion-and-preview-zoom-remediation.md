---
type: pr
id: PR-0398
title: "ST-37-04 Document Converter production conversion and preview zoom remediation"
status: in_progress
owners: "agents"
created: 2026-06-27
updated: 2026-06-27
stories:
  - "ST-37-04"
tags:
  - frontend
  - backend
  - document-converter
  - observability
  - production
dependencies:
  - "PR-0384"
  - "PR-0397"
  - "PR-0399"
acceptance_criteria:
  - "Given a teacher starts a production Document Converter single-file PDF conversion, when the request fails, then the retained evidence identifies the root cause from bounded production observability or container logs before implementation changes are accepted."
  - "Given `PR-0399` enforces the Sir Convert v2 status vocabulary, when a teacher converts a supported PDF, then Document Converter consumes that contract and completes the conversion or truthfully disables unsupported route choices instead of showing a generic start failure."
  - "Given a conversion attempt fails, when an older preview or result exists, then the UI does not present the failed attempt as ready for review and keeps stale successful state visually distinct."
  - "Given any previewable PDF output is selected, when the preview loads or the pane resizes, then the preview automatically fits the available pane until the teacher manually zooms."
  - "Given the teacher inspects a PDF preview, when using zoom in, zoom out, fit-to-view, or touch pinch gestures, then the preview scale changes through working controls using shared icon/control semantics and without layout drift across desktop, tablet, and compact widths."
---

# PR-0398: ST-37-04 Document Converter Production Conversion And Preview Zoom Remediation

## Problem

After `PR-0397` shipped the corrected Document Converter layout, production
single-file PDF conversion can still fail with the teacher-facing message
`Konverteringen kunde inte starta.`. The UI also lacks real preview affordances:
there is no automatic fit-to-pane behavior, no working zoom in/out controls,
and no touch pinch zoom for PDF preview inspection.

## Goal

Find and fix the production conversion failure from observability evidence, then
add truthful PDF preview zoom behavior using the existing shared zoom/control
language rather than reintroducing inert preview controls.

## Non-goals

- No direct Sir Convert browser calls.
- No fake page navigation, fake zoom, or copy-only controls.
- No new labels, eyebrows, or explanatory clutter in the Document Converter
  workspace.
- No broad cross-app preview framework unless a small shared primitive is needed
  to avoid duplication.
- No cross-service status vocabulary implementation; `PR-0399` owns the
  Sir Convert v2 status contract.
- No production deploy, commit, or push unless explicitly requested after the
  reviewed implementation is accepted.

## Required Root-Cause Evidence

The implementation must start by reproducing or tracing the failed production
conversion with a bounded evidence path:

1. use a known or captured `correlation_id` for the failing conversion request;
2. inspect bounded `skriptoteket-web` and, if relevant, `skriptoteket-worker`
   logs for that interval;
3. pivot to trace/span identifiers when present;
4. record whether the root cause is frontend request shape, backend validation,
   producer routing, missing production dependency, worker dispatch, or an
   unsupported conversion route exposed as available.

Retained proof must avoid raw uploaded file contents, credentials, cookies, or
PII.

## Implementation Plan

1. Add red-first focused backend/API or frontend tests that prove the failing
   production PDF conversion behavior or the unsupported-route truthfulness
   issue identified from logs.
2. Consume the `PR-0399` status contract for the production conversion failure;
   do not add tolerant status aliases or route-local string normalization.
3. Repair the smallest owning layer: frontend request shape, backend route/
   handler validation, producer routing, production dependency wiring, or UI
   capability gating.
4. Strengthen failure-state handling so a failed current conversion is not
   presented as a ready preview while any older successful preview remains
   clearly stale.
5. Add a document-preview zoom primitive or component that reuses the existing
   zoom/fit icon semantics and the established fit/manual-zoom/pinch model
   without coupling Document Converter to room-builder domain semantics.
6. Integrate the preview zoom surface into both HTML/CSS project outputs and
   single-file PDF outputs.

## Test Plan

- Focused backend/API test for the proven PDF conversion failure or unsupported
  conversion-route contract.
- Focused contract-consumption tests for the `PR-0399` status vocabulary in the
  Document Converter path.
- Focused frontend test for failed conversion state truthfulness.
- Focused frontend tests for PDF preview fit-to-pane, zoom in, zoom out,
  fit-reset, and touch pinch gesture behavior.
- Focused Document Converter browser proof at desktop, tablet, and compact
  widths for the authenticated `HTML/CSS-projekt` project-preview flow, plus
  focused shared result-panel tests proving the same preview zoom surface used
  by `HTML/CSS-projekt` and `Filkonvertering` supports fit, zoom, pinch, and
  one-finger touch panning.
- `pdm run fe-type-check`
- `pdm run fe-lint`
- `pdm run fe-build`
- Relevant focused backend tests for any backend repair.
- `pdm run docs-validate`
- `pdm run handoff-validate`
- `git diff --check`

## Progress

- Created this governed remediation slice after production screenshots showed
  PDF conversion start failures and missing real preview zoom controls.
- Captured bounded read-only Hemma/container evidence for the production
  failure. The failing path was not frontend request shape, worker dispatch, or
  a missing producer dependency: `skriptoteket-web` successfully submitted jobs
  to Sir Convert and then failed while normalizing upstream poll status.
- First implementation pass identified the status boundary but used a tolerant
  `running -> processing` alias; that approach is rejected. `PR-0399` now owns
  the durable Sir Convert v2 status vocabulary contract, while this slice owns
  Document Converter's consumption, failure-state UX, and preview zoom.
- Added a document-preview zoom primitive for previewable PDF outputs with
  fit-to-pane default behavior, explicit zoom out/in/fit controls, and
  two-finger touch pinch support without importing room-builder domain modules.
- Extended the retained authenticated Document Converter browser proof so the
  live route now exercises the preview zoom controls after a real PDF preview
  render.
- Pauli repair pass: restored fail-closed unknown-status coverage, changed the
  PDF preview scroller so one-finger touch panning remains available after
  zoom, and corrected retained-proof claims to match the browser artifact.
- Added a committed Sir Convert v2 status contract fixture so unit tests fail if
  the local enum drifts from the retained v2 OpenAPI vocabulary.
- Reviewer B repair pass: changed failed project auto-refresh behavior so the
  previous successful PDF is retained only as `Visar föregående PDF.`, the
  current failure copy asks the teacher to retry for a new PDF, and filename,
  download, save, and artifact-selection actions are unavailable until retry
  succeeds.
- Reviewer B second repair pass: narrowed the stale-preview branch to retryable
  project-preview failures instead of generic project errors, so failed
  download/save actions keep the current preview ready, keep file actions
  available, and show the action error without labeling the PDF as previous.

## Verification Notes

- Production root-cause evidence, redacted:
  `skriptoteket-web` at `2026-06-27T12:27:18.568836Z` submitted a Document
  Converter job with correlation `3c56978e-f3b3-4696-b7f4-2cd7cfdab4f2` to
  `sir_convert_a_lot_prod` and received upstream `202 Accepted`; the local POST
  returned `200`. At `2026-06-27T12:27:19.755876Z`, correlation
  `449db22e-8c29-4420-afe7-812c7f54f204`, trace
  `81d0bdffe36e17930621f1b279b09aa1`, upstream job
  `jobv2_69354e8330db46e99a2ab275b3` returned Sir Convert `200 OK`, followed
  immediately by Skriptoteket `SERVICE_UNAVAILABLE`/`503` for local job
  `3f6e1d19-d5a8-4bcd-8f7b-da34747754d6`.
- Additional bounded log evidence showed the same pattern at
  `2026-06-27T12:27:28.366607Z` for correlation
  `20c81fc1-721a-4464-a1d9-6ef45d697f8a`, trace
  `f61b7c86b270e3bbff30cbcd9d2dd152`, and upstream job
  `jobv2_e01dea427c214e3b8ce8bff381`; and at
  `2026-06-27T12:27:34.005835Z` for correlation
  `29c884dd-23f2-48f4-8f15-de2d5d9a656b`, trace
  `39e90cb6f3855160b442a600f9aaa4aa`, and upstream job
  `jobv2_9f225e65244542d0a8021c8f9c`.
- `skriptoteket-worker` had no matching Document Converter dispatch evidence in
  the bounded interval. `sir_convert_a_lot_prod` showed matching accepted/polled
  requests with no producer crash. Code inspection then identified
  `ConversionHubJobStatus.from_upstream()` rejecting upstream `running`, which
  caused the local polling `503` despite upstream `200 OK`.
- Red-first backend evidence:
  `pdm run test tests/unit/application/curated_apps/handlers/test_document_converter_artifact_saves.py -k running_upstream`
  failed before the fix with `DomainError: Unsupported Conversion Hub upstream
  status: running`.
- Red-first frontend evidence:
  `pdm run fe-test -- --run frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterResultPanel.spec.ts`
  failed before the preview implementation because
  `[data-testid="document-converter-pdf-surface"]` and
  `[data-testid="document-converter-pdf-viewport"]` did not exist.
- Pauli repair red evidence:
  `pdm run fe-test -- --run frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterResultPanel.spec.ts`
  failed with `touch-action: none` where the repair spec required
  `touch-action: pan-x pan-y`; the restored unknown-status backend regression
  passed immediately because production still failed closed for truly unknown
  statuses.
- Redirection red evidence for the rejected alias replacement:
  `pdm run test tests/unit/infrastructure/curated_apps/apps/conversion_hub/test_sir_convert_client_v2.py -k 'job_status or unknown_upstream_status'`
  and `pdm run test tests/unit/application/curated_apps/test_conversion_hub_status_mapping.py`
  both failed collection before the repair because `SirConvertJobStatusV2` did
  not exist.
- Cross-service status contract green evidence:
  `pdm run test tests/unit/infrastructure/curated_apps/apps/conversion_hub/test_sir_convert_client_v2.py tests/unit/application/curated_apps/test_conversion_hub_status_mapping.py`
  passed with `11 passed`, proving the enum matches
  `tests/fixtures/sir_convert_a_lot_v2_job_status_contract.json`, unknown
  values fail closed at parse/client boundary, and every upstream enum maps to a
  local status explicitly.
- Adjacent Sir Convert client boundary green evidence:
  `pdm run test tests/unit/infrastructure/curated_apps/apps/conversion_hub/test_sir_convert_transcript_formatter_producer.py tests/unit/infrastructure/curated_apps/apps/conversion_hub/test_public_exam_converter_upstream_clients.py`
  passed with `4 passed`; these clients now consume the same typed upstream job
  status vocabulary instead of free-form strings.
- Focused green backend evidence:
  `pdm run test tests/unit/application/curated_apps/handlers/test_conversion_hub_jobs.py tests/unit/application/curated_apps/handlers/test_document_converter_artifact_saves.py tests/unit/application/curated_apps/handlers/test_document_converter_producer_routing.py tests/unit/application/curated_apps/handlers/test_conversion_hub_transcript_formatter_exports.py tests/unit/web/test_public_apps_exam_converter_runtime.py`
  passed with `40 passed`.
- Focused green frontend evidence:
  `pdm run fe-test -- --run frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterResultPanel.spec.ts frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterSingleFileView.spec.ts frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterProjectResult.spec.ts frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterLayoutOwnership.spec.ts frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterView.spec.ts frontend/apps/skriptoteket/src/views/apps/document-converter/documentConverterFileApi.spec.ts frontend/apps/skriptoteket/src/views/apps/document-converter/documentConverterProjectPreviewApi.spec.ts`
  passed with `26 passed`.
- Focused Pauli repair frontend rerun:
  `pdm run fe-test -- --run frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterResultPanel.spec.ts frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterView.spec.ts`
  passed with `10 passed`, including one-finger touch pan ownership and two-finger
  pinch zoom behavior.
- Original live authenticated proof:
  `pdm run python -m scripts.authenticated_home_work_apps --timeout-seconds 90`
  passed with artifact directory
  `.artifacts/authenticated-home-work-apps/20260627T125219Z/`.
  `manifest.redacted.json` records
  `document_converter_zoom_controls_working=true` for desktop and compact route
  captures; the observed labels were `56% -> 66% -> 56%` and
  `37% -> 47% -> 37%`.
- Pauli repair live authenticated proof:
  `pdm run python -m scripts.authenticated_home_work_apps --timeout-seconds 90`
  passed with artifact directory
  `.artifacts/authenticated-home-work-apps/20260627T132700Z/`.
  `manifest.redacted.json` records desktop/tablet/compact project-preview
  captures, `document_converter_zoom_controls_working=true` for all three, and
  computed `touch_action="pan-x pan-y"` for the PDF preview scroller. This
  proof intentionally covers the project-preview browser flow; both-mode zoom
  behavior is covered by the shared result-panel Vitest because the preview
  panel is consumed by both `HTML/CSS-projekt` and `Filkonvertering`.
- Subagent B red browser-proof evidence:
  `pdm run python -m scripts.authenticated_home_work_apps --timeout-seconds 90`
  first failed at the HuleEdu auth ceremony with `RATE_LIMIT` (`limit=5`,
  `window_seconds=60`) before reaching Document Converter. The redacted failure
  manifest is
  `.artifacts/authenticated-home-work-apps/20260627T134039Z/manifest.redacted.json`.
- Subagent B live authenticated proof:
  after the login window cooled, the same command passed with artifact directory
  `.artifacts/authenticated-home-work-apps/20260627T134816Z/`.
  `manifest.redacted.json` records desktop/tablet/compact project-preview
  captures; tablet and compact contexts use `has_touch=true`; all three
  captures record `touch_action="pan-x pan-y"`, two-finger pinch changing the
  zoom label (`55% -> 138%`, `59% -> 148%`, `37% -> 93%`), one-finger
  `touchmove` not being prevented before or after pinch, and bounded preview
  scrolling after pinch (`scroll_top_after_set=32` with `scroll_height` greater
  than `client_height`). This proof intentionally covers the project-preview
  browser flow; both-mode zoom behavior remains covered by the shared
  result-panel Vitest because `HTML/CSS-projekt` and `Filkonvertering` consume
  the same `DocumentConverterResultPanel`.
- Reviewer B repair red frontend evidence:
  `pdm run fe-test -- --run frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterView.spec.ts`
  failed after the spec correction because the old route still showed
  `PDF klart för granskning.`, did not show `Visar föregående PDF.`, and kept
  stale download/save behavior as the expected contract.
- Reviewer B repair implementation red evidence:
  the same focused command then failed once more because the production fix
  correctly reloaded the retained previous PDF through history, creating a new
  blob URL; the spec was narrowed away from object-URL identity and kept the
  user-facing stale-state/action assertions.
- Reviewer B repair green frontend evidence:
  `pdm run fe-test -- --run frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterView.spec.ts`
  passed with `6 passed`, and the focused Document Converter set
  `pdm run fe-test -- --run frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterView.spec.ts frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterProjectResult.spec.ts frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterResultPanel.spec.ts frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterSingleFileView.spec.ts frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterLayoutOwnership.spec.ts frontend/apps/skriptoteket/src/views/apps/document-converter/documentConverterFileApi.spec.ts frontend/apps/skriptoteket/src/views/apps/document-converter/documentConverterProjectPreviewApi.spec.ts`
  passed with `26 passed`.
- Reviewer B repair gates:
  `pdm run fe-type-check`, `pdm run fe-lint`, and `pdm run fe-build` passed.
  `fe-build` retained the existing dynamic/static import and large-chunk
  warnings.
- Reviewer B second repair red frontend evidence:
  `pdm run fe-test -- --run frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterView.spec.ts`
  failed after adding the action-error regression because a failed project
  download switched the route to `Visar föregående PDF.` and removed
  `PDF klart för granskning.` from the current preview state.
- Reviewer B second repair green frontend evidence:
  the same focused `DocumentConverterView.spec.ts` command passed with
  `7 passed` after the predicate was narrowed to retryable preview failures;
  the retained failed-refresh regression and retry recovery stayed green. The
  focused Document Converter set then passed with `7 passed / 27 tests`.
- Reviewer B second repair gates:
  `pdm run fe-type-check`, `pdm run fe-lint`, `pdm run fe-build`,
  `pdm run docs-validate`, and `git diff --check` passed. `fe-build` retained
  the existing dynamic/static import and large-chunk warnings.
- Gates passed locally after the alias removal: `pdm run fe-type-check`,
  `pdm run fe-lint`, `pdm run fe-build`, `pdm run lint`, and
  `pdm run typecheck`. `fe-build` retained the existing dynamic/static import
  and large-chunk warnings.
- Final docs/proof-surface hygiene passed:
  `pdm run test tests/unit/scripts/test_playwright_script_surface.py`,
  `pdm run docs-validate`, `pdm run handoff-validate`, and
  `git diff --check`.

## Rollback Plan

Revert this slice to restore the `PR-0397` layout and current preview behavior,
while preserving any retained production evidence artifact for follow-up
debugging.
