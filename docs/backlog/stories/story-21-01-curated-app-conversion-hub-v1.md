---
type: story
id: ST-21-01
title: "Curated app: Conversion Hub (v1)"
status: in_progress
owners: "agents"
created: 2026-03-01
epic: "EPIC-21"
dependencies:
  - "ADR-0066"
  - "ADR-0022"
  - "ADR-0023"
  - "ADR-0024"
acceptance_criteria:
  - "Given a signed-in user opens the Conversion Hub curated app, when the app loads, then it renders a bespoke view under `/apps/:appId` (no generic fallback renderer) and fetches app metadata from `/api/v1/apps/:appId`."
  - "Given a user selects a supported conversion route (as defined by Sir Convert-a-Lot v2), when they submit one or more input files, then Skriptoteket submits v2 job(s), polls deterministically, and provides downloadable artifacts on success."
  - "Given the user selects a PDF output format where layout presets apply, when they choose paper size and orientation, then requests map to v2 `conversion.pdf_layout` and the resulting PDF reflects the chosen layout."
  - "Given the user runs a batch conversion (N files), when results return, then the UI shows per-file status and provides per-file artifact download links (and does not collapse the batch into a single opaque output)."
  - "Given a conversion fails, when the job reaches terminal failure, then the UI shows a stable error summary including correlation id and does not require the user to change filenames to re-run after a fix."
ui_impact: "Yes (new curated app view + conversion workflow UI)"
data_impact: "No (no new DB tables; stores only normal tool_sessions/tool_runs artifacts, consistent with curated apps platform)"
---

## Context

The existing `html-to-pdf-preview` tool script (`src/skriptoteket/script_bank/scripts/html_to_pdf_preview.py`) is a
production path today, but it duplicates conversion capability and hardcodes an interactive flow that is not the
long-term conversion strategy.

Skriptoteket should instead ship a curated app UI that routes conversion work to the canonical conversion engine:
Sir Convert-a-Lot v2.

## PR Tasks (ordered)

- [x] 1. PR-0063: ADR + EPIC/Story scaffolding (docs-as-code; review-ready)
- [x] 2. PR-0064: Backend Sir Convert-a-Lot v2 client + curated app API surface (submit/poll/download)
- [ ] 3. PR-0065: SPA Conversion Hub bespoke UI (batch + preview + pdf_layout controls)

## Notes

- Curated apps registry: `src/skriptoteket/infrastructure/curated_apps/registry.py`
- SPA host: `frontend/apps/skriptoteket/src/views/AppHostView.vue`
- Existing tool dependencies to retire are tracked in ST-21-02.
