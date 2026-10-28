---
type: story
id: ST-SKRIPT-21-01
title: 'Curated app: Conversion Hub (v1)'
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: '2026-07-31'
status: canceled
closeout_review:
  record: inline
  status: approved
  reviewer: orchestrator
  decided_at: '2026-10-28'
  approval_protocol: agent-overseer:approved-review-closeout
  approval_evidence: 'ST-SKRIPT-21-01#closeout'
epic: EPIC-SKRIPT-21
links:
  decisions:
    - ADR-SKRIPT-0066
    - ADR-SKRIPT-0022
    - ADR-SKRIPT-0023
    - ADR-SKRIPT-0024
acceptance_criteria:
  - Given a signed-in user opens the Conversion Hub curated app, when the app loads, then it renders a bespoke view under `/apps/:appId` (no generic fallback renderer) and fetches app metadata from `/api/v1/apps/:appId`.
  - Given a user selects a supported conversion route (as defined by Sir Convert-a-Lot v2), when they submit one or more input files, then Skriptoteket creates local conversion jobs, submits the upstream work, polls deterministically, and provides downloadable artifacts on success without exposing raw upstream job ids as the primary user contract.
  - Given the user selects a PDF output format where layout presets apply, when they choose paper size and orientation, then requests map to v2 `conversion.pdf_layout` and the resulting PDF reflects the chosen layout.
  - Given the user runs a batch conversion (N files), when results return, then the UI shows per-file status and provides per-file artifact download links (and does not collapse the batch into a single opaque output).
  - Given a conversion fails, when the job reaches terminal failure, then the UI shows a stable error summary including correlation id and does not require the user to change filenames to re-run after a fix.
  - Given a user polls status or downloads an artifact, when the request is handled, then Skriptoteket authorizes access through its local Conversion Hub job ledger and does not rely on raw upstream job ids as the ownership boundary.
  - Given Skriptoteket and Sir Convert run on the same host, when trusted local transport is configured, then the integration supports a Unix domain socket path with `127.0.0.1` HTTP fallback and does not require internal HTTPS between the co-located services.
retired_ids:
  - ST-21-01
backlog_document_profile: contract-derived
---

## Slice Contract

Canceled on 2026-10-28 under TASK-SKRIPT-REP-0056 D5, because its acceptance does not hold on main and its only child task is canceled. The original story text below is kept as history; see Closeout.

## Context

### Source: Context

The existing `html-to-pdf-preview` tool script (`src/skriptoteket/script_bank/scripts/html_to_pdf_preview.py`) is a
production path today, but it duplicates conversion capability and hardcodes an interactive flow that is not the
long-term conversion strategy.

Skriptoteket should instead ship a curated app UI that routes conversion work to the canonical
conversion engine: Sir Convert-a-Lot v2, while still owning the local job/auth boundary expected of
a first-class product surface.

## Epic Contract Slice

The source does not provide a separate story contract section.

## ADR Coverage

The source does not record separate ADR coverage.

## Contract Inputs

The source does not record separate contract inputs.

## Tasks

- TASK-SKRIPT-21-01-01 (canceled)

## Verification

The source record did not define a separate section for this package heading.

## Decided Contract Terms

| ID  | Decided contract term                                                                                                                                                                                                 |
| --- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| D1  | Canceled on 2026-10-28 because the story's acceptance does not hold on main and every child task is canceled (orchestrator decision 2026-10-28, TASK-SKRIPT-REP-0056 D5); the Closeout section names what is on main. |

## Live Verification Plan

### Source: PR Tasks (ordered)

- [x] 1. PR-0063: ADR + EPIC/Story scaffolding (docs-as-code; review-ready)
- [x] 2. PR-0064: Backend Sir Convert-a-Lot v2 client + curated app API surface (submit/poll/download)
- [x] 3. PR-0148: Conversion Hub local job ledger and owned status/download boundary
- [ ] 4. TASK-SKRIPT-21-01-01: SPA Conversion Hub bespoke UI (batch + preview + pdf_layout controls) (canceled)

## Non-Goals

The source does not record separate non-goals.

## Notes

### Source: Notes

- Curated apps registry: `src/skriptoteket/infrastructure/curated_apps/registry.py`
- SPA host: `frontend/apps/skriptoteket/src/views/AppHostView.vue`
- Existing tool dependencies to retire are tracked in ST-SKRIPT-21-02.

## Decision And Assumption Ledger

The source does not record a separate decision and assumption ledger.

## Plan Document Review

The source does not include a plan document review record.

## Story Closeout Review

The source does not include a story closeout review record.

## Closeout

Canceled on 2026-10-28 under TASK-SKRIPT-REP-0056 D5 (orchestrator closeout). Its only child, TASK-SKRIPT-21-01-01, is canceled as superseded, and no acceptance criterion holds in full on main. Per criterion:

1. Bespoke view under `/apps/:appId`: partly. `documents.conversion_hub` maps to `ExamWorkspaceTeacherHost.vue` (`frontend/apps/skriptoteket/src/views/curatedAppHostRegistry.ts:47-50`); the conversion UI is the static route `/apps/document-converter` (`router/routes.ts:20-25`), outside `/apps/:appId`.
2. Route selection, local jobs, deterministic polling, downloads: partly. Each upload gets a local job and status and download go through the ledger (`src/skriptoteket/application/curated_apps/handlers/document_converter_jobs.py:106-162`), but all three UI routes run locally (`document_converter_producers.py:50-76`); the only upstream submit is the `/jobs` handler (`web/api/v1/apps_conversion_hub.py:152-194`), which no frontend code calls.
3. Paper size and orientation mapped to `conversion.pdf_layout`: not met. The single-file request hard-codes `a4`, `portrait` and 12 mm (`views/apps/document-converter/documentConverterFileApi.ts:75-81`).
4. Batch with per-file status and download links: partly. One failed file drops the artifacts of the successful ones (`documentConverterSingleFileSubmission.ts:143, 164-179`), and there is no per-file status table.
5. Error summary with correlation id, re-run without renaming: partly. `DocumentConverterJobStatusResult` carries no correlation id (`application/curated_apps/document_converter.py:165-173`); re-run restores the same files (`useDocumentConverterSingleFile.ts:229-232`).
6. Authorization through the local job ledger: met (`handlers/conversion_hub_document_converter.py:95-100`).
7. Unix domain socket with `127.0.0.1` fallback: met in code (`infrastructure/curated_apps/apps/conversion_hub/sir_convert_client_v2.py:182-197`); no UI route reaches the upstream client.

Dropped, not built: a conversion-route selector, PDF orientation and margin controls, and a per-file batch status table with per-file rerun. Code only; no walk of the app.
