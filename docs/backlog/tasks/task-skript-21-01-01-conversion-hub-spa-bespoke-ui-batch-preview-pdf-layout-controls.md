---
type: task
id: TASK-SKRIPT-21-01-01
title: 'Conversion Hub: SPA bespoke UI (batch + preview + pdf_layout controls)'
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
status: ready
readiness_review:
  record: inline
  status: not_started
closeout_review:
  record: inline
  status: not_started
story: ST-SKRIPT-21-01
task_kind: story
acceptance_criteria:
- Given a user opens `/apps/:appId`, when the app is Conversion Hub, then the bespoke
  view renders and supports selecting a conversion route supported by Sir Convert-a-Lot
  v2.
- Given the user uploads N files and runs batch conversion, when results return, then
  the UI shows per-file status and provides artifact download links.
- Given a PDF output is selected, when the user changes paper size and orientation,
  then those map to v2 `conversion.pdf_layout` and are reflected in results.
- Given a failure occurs, when the job reaches terminal failure, then the UI renders
  a stable error summary (including correlation id) and provides an easy rerun action.
---

## Context

We need a first-class UI that replaces the `html-to-pdf-preview` tool-run view and provides a complete conversion
interface backed by Sir Convert-a-Lot v2.

- Add a bespoke Conversion Hub view integrated with the curated apps host.
- Provide batch + preview UX aligned to v2 job semantics.
- Keep UI deterministic and typed via OpenAPI TS types.

## Decision And Assumption Ledger

The source snapshot is the governing record for the decisions and assumptions stated above.

## Story Contract Slice

- Add a bespoke Conversion Hub view integrated with the curated apps host.
- Provide batch + preview UX aligned to v2 job semantics.
- Keep UI deterministic and typed via OpenAPI TS types.

## Contract Inputs

No separate material is recorded in the source snapshot.

## Plan

- [ ] 1. Ensure bespoke routing works (fail-closed safety):
  - Add `documents.conversion_hub` async import in
    `frontend/apps/skriptoteket/src/views/AppHostView.vue` bespoke registry.
- [ ] 2. Create the bespoke view + file layout skeleton:
  - Add `frontend/apps/skriptoteket/src/views/apps/ConversionHubView.vue` (thin orchestration + layout only).
  - Add folder `frontend/apps/skriptoteket/src/views/apps/conversion-hub/` for small UI-only components.
- [ ] 3. Add app-local typed aliases (OpenAPI → app language):
  - Add `frontend/apps/skriptoteket/src/views/apps/conversion-hub/types.ts` mirroring the ReagentPrepChef pattern.
- [ ] 4. Add app-specific composables (logic must not live in the view):
  - Add `frontend/apps/skriptoteket/src/composables/conversionHub/useConversionHubRoutes.ts`:
    loads route list from `/api/v1/apps/documents.conversion_hub/routes`, exposes select options.
  - Add `frontend/apps/skriptoteket/src/composables/conversionHub/useConversionHubBatch.ts`:
    batch state machine:
    - inputs: selected route, optional `pdf_layout`, files[],
    - submit: `POST /api/v1/apps/documents.conversion_hub/jobs` (multipart: `job_spec_json`, `files[]`, `wait_seconds`),
    - poll: `GET /api/v1/apps/documents.conversion_hub/jobs/{job_id}` until terminal,
    - download: `GET /api/v1/apps/documents.conversion_hub/jobs/{job_id}/artifact` (blob),
    - rerun: resubmit same spec/files without requiring filename changes.
  - Add `frontend/apps/skriptoteket/src/composables/conversionHub/useConversionHubCorrelationId.ts`:
    generates a UUID per run and returns `{ correlationId, headers }` for API calls.
- [ ] 5. Implement the UX primitives (token-driven styling + button primitives):
  - route selector (from backend routes result),
  - file picker (multi-file upload),
  - PDF layout selector shown only when output format is `pdf`:
    paper size (A5/A4/A3), orientation, margins (mm),
  - per-file batch table:
    input filename, current status, actions: download artifact, preview (PDF-only), rerun (on failure).
  - error panel:
    - API errors show message + correlation id (if present),
    - job failures show terminal status + the run correlation id.
- [ ] 6. Regenerate OpenAPI TS types and keep repo consistent:
  - Run `pdm run fe-gen-api-types` (exports `frontend/apps/skriptoteket/openapi.json` then updates
    `frontend/apps/skriptoteket/src/api/openapi.d.ts`).
- [ ] 7. Add Vitest coverage for the batch state machine:
  - unit tests for `useConversionHubBatch`:
    - submit shapes `FormData` correctly (job_spec_json, files[], wait_seconds),
    - polling loop reaches terminal states deterministically,
    - rerun creates a new correlation id and resets per-file state.

## Implementation Steps

- [ ] 1. Ensure bespoke routing works (fail-closed safety):
  - Add `documents.conversion_hub` async import in
    `frontend/apps/skriptoteket/src/views/AppHostView.vue` bespoke registry.
- [ ] 2. Create the bespoke view + file layout skeleton:
  - Add `frontend/apps/skriptoteket/src/views/apps/ConversionHubView.vue` (thin orchestration + layout only).
  - Add folder `frontend/apps/skriptoteket/src/views/apps/conversion-hub/` for small UI-only components.
- [ ] 3. Add app-local typed aliases (OpenAPI → app language):
  - Add `frontend/apps/skriptoteket/src/views/apps/conversion-hub/types.ts` mirroring the ReagentPrepChef pattern.
- [ ] 4. Add app-specific composables (logic must not live in the view):
  - Add `frontend/apps/skriptoteket/src/composables/conversionHub/useConversionHubRoutes.ts`:
    loads route list from `/api/v1/apps/documents.conversion_hub/routes`, exposes select options.
  - Add `frontend/apps/skriptoteket/src/composables/conversionHub/useConversionHubBatch.ts`:
    batch state machine:
    - inputs: selected route, optional `pdf_layout`, files[],
    - submit: `POST /api/v1/apps/documents.conversion_hub/jobs` (multipart: `job_spec_json`, `files[]`, `wait_seconds`),
    - poll: `GET /api/v1/apps/documents.conversion_hub/jobs/{job_id}` until terminal,
    - download: `GET /api/v1/apps/documents.conversion_hub/jobs/{job_id}/artifact` (blob),
    - rerun: resubmit same spec/files without requiring filename changes.
  - Add `frontend/apps/skriptoteket/src/composables/conversionHub/useConversionHubCorrelationId.ts`:
    generates a UUID per run and returns `{ correlationId, headers }` for API calls.
- [ ] 5. Implement the UX primitives (token-driven styling + button primitives):
  - route selector (from backend routes result),
  - file picker (multi-file upload),
  - PDF layout selector shown only when output format is `pdf`:
    paper size (A5/A4/A3), orientation, margins (mm),
  - per-file batch table:
    input filename, current status, actions: download artifact, preview (PDF-only), rerun (on failure).
  - error panel:
    - API errors show message + correlation id (if present),
    - job failures show terminal status + the run correlation id.
- [ ] 6. Regenerate OpenAPI TS types and keep repo consistent:
  - Run `pdm run fe-gen-api-types` (exports `frontend/apps/skriptoteket/openapi.json` then updates
    `frontend/apps/skriptoteket/src/api/openapi.d.ts`).
- [ ] 7. Add Vitest coverage for the batch state machine:
  - unit tests for `useConversionHubBatch`:
    - submit shapes `FormData` correctly (job_spec_json, files[], wait_seconds),
    - polling loop reaches terminal states deterministically,
    - rerun creates a new correlation id and resets per-file state.

## Proof

- `pdm run fe-gen-api-types`
- `pdm run fe-type-check`
- `pdm run fe-test`

## Validation

- `pdm run fe-gen-api-types`
- `pdm run fe-type-check`
- `pdm run fe-test`

## Stop Conditions

- Remove the bespoke view mapping and leave the app hidden from catalog placements until stable.

## Lessons Learned

No separate material is recorded in the source snapshot.

## Notes

### Problem

We need a first-class UI that replaces the `html-to-pdf-preview` tool-run view and provides a complete conversion
interface backed by Sir Convert-a-Lot v2.

### Goal

- Add a bespoke Conversion Hub view integrated with the curated apps host.
- Provide batch + preview UX aligned to v2 job semantics.
- Keep UI deterministic and typed via OpenAPI TS types.

### Non-goals

- No E2E test migration in this PR (PR-0066).

### Decisions (locked for PR-0065)

- App id is `documents.conversion_hub` (must be mapped in the SPA bespoke registry to avoid fail-closed blocking).
- The Conversion Hub SPA MUST use the curated app bespoke surface and MUST NOT reuse generic tool-run UI flows
  (`ui_mode=bespoke_required` rule).
- Route options are sourced from `GET /api/v1/apps/documents.conversion_hub/routes` (no hardcoded route list in the UI).
- Upload-only in PR-0065: the backend accepts `files[]` multipart uploads; vault/session-file selection is out of scope.
- Batch is first-class: submit N files in one request and render per-file status and download links.
- Preview is “one PDF at a time”: any succeeded PDF artifact can be previewed in-app (modal) using a blob URL.
- Correlation id is stable per batch run:
  - the SPA generates a UUID and sends it as `X-Correlation-ID` on submit/poll/download,
  - the UI displays that correlation id on failures (job failures and API errors) for support/debug.
- Rerun UX is filename-independent:
  - rerun re-submits the same spec + same File objects (new `X-Correlation-ID` per run),
  - no “rename the file to bypass idempotency” behavior is required.
- OpenAPI TS types are authoritative:
  - regenerate types via `pdm run fe-gen-api-types`,
  - app-local `types.ts` aliases use `components["schemas"][...]` from `src/api/openapi.d.ts`.

### Implementation plan

- [ ] 1. Ensure bespoke routing works (fail-closed safety):
  - Add `documents.conversion_hub` async import in
    `frontend/apps/skriptoteket/src/views/AppHostView.vue` bespoke registry.
- [ ] 2. Create the bespoke view + file layout skeleton:
  - Add `frontend/apps/skriptoteket/src/views/apps/ConversionHubView.vue` (thin orchestration + layout only).
  - Add folder `frontend/apps/skriptoteket/src/views/apps/conversion-hub/` for small UI-only components.
- [ ] 3. Add app-local typed aliases (OpenAPI → app language):
  - Add `frontend/apps/skriptoteket/src/views/apps/conversion-hub/types.ts` mirroring the ReagentPrepChef pattern.
- [ ] 4. Add app-specific composables (logic must not live in the view):
  - Add `frontend/apps/skriptoteket/src/composables/conversionHub/useConversionHubRoutes.ts`:
    loads route list from `/api/v1/apps/documents.conversion_hub/routes`, exposes select options.
  - Add `frontend/apps/skriptoteket/src/composables/conversionHub/useConversionHubBatch.ts`:
    batch state machine:
    - inputs: selected route, optional `pdf_layout`, files[],
    - submit: `POST /api/v1/apps/documents.conversion_hub/jobs` (multipart: `job_spec_json`, `files[]`, `wait_seconds`),
    - poll: `GET /api/v1/apps/documents.conversion_hub/jobs/{job_id}` until terminal,
    - download: `GET /api/v1/apps/documents.conversion_hub/jobs/{job_id}/artifact` (blob),
    - rerun: resubmit same spec/files without requiring filename changes.
  - Add `frontend/apps/skriptoteket/src/composables/conversionHub/useConversionHubCorrelationId.ts`:
    generates a UUID per run and returns `{ correlationId, headers }` for API calls.
- [ ] 5. Implement the UX primitives (token-driven styling + button primitives):
  - route selector (from backend routes result),
  - file picker (multi-file upload),
  - PDF layout selector shown only when output format is `pdf`:
    paper size (A5/A4/A3), orientation, margins (mm),
  - per-file batch table:
    input filename, current status, actions: download artifact, preview (PDF-only), rerun (on failure).
  - error panel:
    - API errors show message + correlation id (if present),
    - job failures show terminal status + the run correlation id.
- [ ] 6. Regenerate OpenAPI TS types and keep repo consistent:
  - Run `pdm run fe-gen-api-types` (exports `frontend/apps/skriptoteket/openapi.json` then updates
    `frontend/apps/skriptoteket/src/api/openapi.d.ts`).
- [ ] 7. Add Vitest coverage for the batch state machine:
  - unit tests for `useConversionHubBatch`:
    - submit shapes `FormData` correctly (job_spec_json, files[], wait_seconds),
    - polling loop reaches terminal states deterministically,
    - rerun creates a new correlation id and resets per-file state.

### Test plan

- `pdm run fe-gen-api-types`
- `pdm run fe-type-check`
- `pdm run fe-test`

### Rollback plan

- Remove the bespoke view mapping and leave the app hidden from catalog placements until stable.

## Plan Document Review

No separate material is recorded in the source snapshot.

## Implementation Review

No separate material is recorded in the source snapshot.
