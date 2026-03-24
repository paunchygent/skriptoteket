---
type: pr
id: PR-0119
title: "Klassrumskartan: seating PDF poster renderer and artifact delivery"
status: done
owners: "agents"
created: 2026-03-24
updated: 2026-03-24
stories:
  - "ST-26-01"
tags: ["backend", "pdf", "klassrumskartan", "export", "rendering"]
acceptance_criteria:
  - "The current seating draft can be rendered as a one-page PDF artifact using the standalone poster-scene model."
  - "The poster-scene model is rendered first into export-specific HTML/CSS and that HTML/CSS is the canonical intermediate source handed to Sir Convert-a-Lot for final PDF conversion."
  - "The first shipped layout renders as `pretty_brutalist_poster` with high contrast, strong room geometry, large readable labels, and light branding only."
  - "The generated PDF is delivered through an explicit export action and remains separate from autosave, history, and ordinary draft continuation."
---

## Problem

The export contract alone does not produce the teacher-facing artifact needed for classroom printing.

## Goal

Render and deliver the first poster-grade seating PDF artifact.

## Current status

- Implemented locally on `main`.
- The async export lane now renders the canonical `poster_scene` into dedicated
  `index.html` + `poster.css`, submits a multi-file HTML/CSS job to
  Sir Convert-a-Lot, persists the finished PDF to Vault, and exposes typed
  create/status/download routes.
- Review follow-up fixes are included:
  - webhook-onboarding failures now mark the local job as `failed`
  - polling can recover a completed upstream job if webhook delivery is missed
  - the renderer-owned teacher-facing filename is preserved through Vault and
    download instead of collapsing to `output.pdf`

## Non-goals

- Adding extra PDF pages or low-value metadata blocks.
- Implementing teacher-selectable layouts.
- Implementing XLSX export.

## Implementation plan

- Keep `POST /api/v1/apps/classroom.group-seating-studio/drafts/seating/{draft_id}/exports`
  as the PR-0118 prepare-contract endpoint.
- Add an async execution surface at
  `POST /api/v1/apps/classroom.group-seating-studio/drafts/seating/{draft_id}/exports/jobs`.
- Accept a typed request body with `export_kind`, `layout_id`, and
  `paper_size` where `paper_size` is `a3_landscape` or `a4_landscape`.
- Add status and delivery routes at
  `GET /api/v1/apps/classroom.group-seating-studio/exports/jobs/{job_id}` and
  `GET /api/v1/apps/classroom.group-seating-studio/exports/jobs/{job_id}/download`.
- Introduce a dedicated `SeatingExportJob` persistence model and repository rather than
  overloading generic tool-run state as the public export job seam.
- Render the standalone `poster_scene` into export-specific `index.html` + `poster.css`
  owned by the backend export lane rather than by the live planner UI.
- Widen the Skriptoteket Sir Convert-a-Lot v2 client/protocol to support multi-file
  HTML/CSS submission instead of a single uploaded file only.
- Submit export jobs to Sir Convert-a-Lot using async push/webhook completion.
- Handle Sir Convert completion through a small shared internal callback route that
  dispatches the completed conversion back to the owning export job handler.
- Download the finished PDF artifact after successful callback completion and save it
  immediately to Vault as the durable teacher-facing artifact.
- Keep the output independent from live planner print styles, screenshot export, and
  DOM-printing approaches.

## Locked design decisions

- `poster_scene` from PR-0118 remains the canonical renderer input for PR-0119.
- `pretty_brutalist_poster` remains the only valid `layout_id` in this slice.
- `paper_size` is explicit user input and is limited to `a3_landscape` and
  `a4_landscape`.
- A3 landscape remains the poster-grade default intent, but A4 landscape is also
  supported as an explicit teacher choice.
- The public export-job API is classroom-planner-specific and does not expose raw Sir
  Convert or generic runner records.
- The finished PDF is persisted to Vault immediately rather than remaining only as a
  transient download or internal run artifact.

## Proposed contract shape

### Create export job

`POST /api/v1/apps/classroom.group-seating-studio/drafts/seating/{draft_id}/exports/jobs`

Request body:

```json
{
  "export_kind": "pdf",
  "layout_id": "pretty_brutalist_poster",
  "paper_size": "a3_landscape"
}
```

Response shape:

```json
{
  "job_id": "uuid",
  "draft_id": "uuid",
  "export_kind": "pdf",
  "layout_id": "pretty_brutalist_poster",
  "paper_size": "a3_landscape",
  "status": "submitted",
  "created_at": "2026-03-24T12:00:00Z",
  "download_url": null,
  "vault_artifact": null,
  "error": null
}
```

### Poll export job

`GET /api/v1/apps/classroom.group-seating-studio/exports/jobs/{job_id}`

- Returns the same typed export job envelope with status transitions:
  `submitted`, `processing`, `succeeded`, `failed`.
- On success, includes `download_url` and `vault_artifact`.
- On failure, includes a teacher-safe `error` payload.
- Polling must recover a terminal upstream job even if the push callback is delayed
  or missed, so teachers do not get stranded on a finished export.

### Download finished export

`GET /api/v1/apps/classroom.group-seating-studio/exports/jobs/{job_id}/download`

- Streams the Vault-backed PDF artifact when the job has succeeded.
- Rejects unfinished jobs without exposing Vault internals as the public contract.
- Preserves the renderer-owned teacher-facing filename instead of falling back to a
  generic upstream `output.pdf`.

## Module placement

- Application:
  `classroom_planner/exports/rendering.py` for renderer-facing contracts and
  `handlers/seating_export_jobs.py` for create/status/callback orchestration.
- Infrastructure:
  classroom-planner-specific poster HTML/CSS renderer, dedicated
  `SeatingExportJob` repository implementation, widened Sir Convert-a-Lot client,
  and the small shared callback dispatcher.
- Web:
  seating export job DTO module plus seating/export job routes under the existing
  classroom-planner API surface.

## Test plan

- Focused rendering tests for canonical label placement, room composition, and A3/A4
  paper-size contract handling.
- Tests proving the HTML/CSS intermediate source is built from the standalone
  poster-scene model rather than from planner DOM reuse.
- Focused application tests for create-job, callback completion, Vault persistence,
  and typed status/download behavior.
- Focused API tests for create/status/download/callback routes.
- Live manual end-to-end export verification, including visual PDF readability checks,
  recorded in handoff when implemented.

## Rollback plan

- Remove PDF rendering and delivery while preserving the explicit export contract.
