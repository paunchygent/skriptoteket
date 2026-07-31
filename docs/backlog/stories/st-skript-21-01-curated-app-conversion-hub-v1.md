---
type: story
id: ST-SKRIPT-21-01
title: 'Curated app: Conversion Hub (v1)'
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
status: active
readiness_review:
  record: inline
  status: not_started
closeout_review:
  record: inline
  status: not_started
epic: EPIC-SKRIPT-21
links:
  decisions:
  - ADR-SKRIPT-0066
  - ADR-SKRIPT-0022
  - ADR-SKRIPT-0023
  - ADR-SKRIPT-0024
acceptance_criteria:
- Given a signed-in user opens the Conversion Hub curated app, when the app loads,
  then it renders a bespoke view under `/apps/:appId` (no generic fallback renderer)
  and fetches app metadata from `/api/v1/apps/:appId`.
- Given a user selects a supported conversion route (as defined by Sir Convert-a-Lot
  v2), when they submit one or more input files, then Skriptoteket creates local conversion
  jobs, submits the upstream work, polls deterministically, and provides downloadable
  artifacts on success without exposing raw upstream job ids as the primary user contract.
- Given the user selects a PDF output format where layout presets apply, when they
  choose paper size and orientation, then requests map to v2 `conversion.pdf_layout`
  and the resulting PDF reflects the chosen layout.
- Given the user runs a batch conversion (N files), when results return, then the
  UI shows per-file status and provides per-file artifact download links (and does
  not collapse the batch into a single opaque output).
- Given a conversion fails, when the job reaches terminal failure, then the UI shows
  a stable error summary including correlation id and does not require the user to
  change filenames to re-run after a fix.
- Given a user polls status or downloads an artifact, when the request is handled,
  then Skriptoteket authorizes access through its local Conversion Hub job ledger
  and does not rely on raw upstream job ids as the ownership boundary.
- Given Skriptoteket and Sir Convert run on the same host, when trusted local transport
  is configured, then the integration supports a Unix domain socket path with `127.0.0.1`
  HTTP fallback and does not require internal HTTPS between the co-located services.
retired_ids:
- ST-21-01
---

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

## Live Verification Plan

### Source: PR Tasks (ordered)

- [x] 1. PR-0063: ADR + EPIC/Story scaffolding (docs-as-code; review-ready)
- [x] 2. PR-0064: Backend Sir Convert-a-Lot v2 client + curated app API surface (submit/poll/download)
- [x] 3. PR-0148: Conversion Hub local job ledger and owned status/download boundary
- [ ] 4. TASK-SKRIPT-21-01-01: SPA Conversion Hub bespoke UI (batch + preview + pdf_layout controls)

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
