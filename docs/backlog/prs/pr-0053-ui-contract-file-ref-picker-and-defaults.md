---
type: pr
id: PR-0053
title: "UI contract: file-ref picker + defaults + validation"
status: done
owners: "agents"
created: 2026-01-24
updated: 2026-06-18
stories:
  - "ST-14-24"
tags: ["frontend", "api"]
acceptance_criteria:
  - "File-ref selection is per field: multiple file fields in the same run/action are supported."
  - "File field values are always FileRef[] (array), even when max=1."
  - "UI never exposes runner filesystem paths; it only shows labels + metadata (name/bytes/date) and opaque FileRef identifiers."
  - "Defaults (settings/action prefill) preselect when available; missing defaults block execution with an actionable validation error."
  - "Submitted FileRefs resolve to staged /work/input paths via the resolver pipeline and preserve field ownership in the input manifest."
---

## Problem

ST-14-24 requires first-class file references in the UI contract, including a picker, default preselects, and
validation when defaults are missing. Without this, tools must pass filenames manually and the UI leaks paths.

Parent: EPIC-14. Dependencies: ST-19-01/02/03, ST-14-19.

## Goal

Define and implement the UI contract for file-ref fields in run/action forms, including defaults and validation,
without adding parallel identifiers or path-based fallbacks.

## Decisions (LOCKED)

- **Multi file fields are REQUIRED now:** both `input_schema` and `next_actions[].fields` MUST support more than one
  file field in the same form.
- **Value shape is always list:** a file field’s value MUST be `FileRef[]` (array of strings). There is no scalar
  `FileRef` value shape (no `file_ref` vs `file_refs` split).
- **UiActionField file refs use a dedicated field kind:** action forms and tool settings MUST use a new
  `UiActionField.kind="file_ref"` (NOT `kind="file"`), with:
  - `min: int`, `max: int` (value is always `FileRef[]`)
  - optional `sources?: ["session","vault"]` (default: both)
- **Per-field mapping is REQUIRED end-to-end:** the platform MUST preserve which field each file belongs to:
  - Wire contract MUST be per-field (no flat lists):
    - Non-file inputs are sent as JSON only (existing behavior).
    - File refs are sent as `file_refs_by_field: Record[field_name, FileRef[]]`.
    - Uploads are sent as `files[]` plus `file_fields[]` (see below).
  - The platform MUST write file-ref arrays into `/work/request.json` for tools:
    - Initial runs: `inputs.values[field_name] = FileRef[]`
    - Action runs: `action.input[field_name] = FileRef[]`
  - `/work/request.json` MUST include enough metadata for tools to map staged files back to their field (e.g. a
    `field` property per manifest entry).
- **Multipart upload field mapping (REQUIRED):** when uploading files, the request MUST include `file_fields` as a JSON
  array aligned with `files` order (same length). The server MUST validate that the lengths match.
- **No path leakage:** list APIs and UI MUST NOT return or display filesystem paths; only `ref`, `name`, and `bytes`
  (plus optional UI metadata like timestamps).
- **Available FileRefs API shape (REQUIRED):** implement new endpoints (do not overload session-files):
  - `GET /api/v1/tools/{tool_id}/file-refs?context=default`
  - `GET /api/v1/editor/tool-versions/{version_id}/file-refs?snapshot_id=...`
- **Source selection per field:** for a given field, users MUST choose either uploads OR existing refs (session/vault).
  Mixing sources within the same field is FORBIDDEN; mixing across different fields in the same run is allowed.
- **Tool settings use vault-only file refs:** tool settings file pickers MUST be vault-only (no session refs), and
  `sources` is effectively `["vault"]` for settings fields.
- **Session file reuse preserves field ownership:** session files MUST store per-file `field` metadata (persisted) and
  session reuse MUST map by `field` (not “all files to all fields”).
- **Duplicate filenames across fields:** duplicates (after sanitization) are DISALLOWED globally for a run (keep flat
  `/work/input/<name>` paths; no namespacing by field).

## Non-goals

- User file vault persistence (ST-14-36).
- Runner contract changes beyond existing file-ref resolver pipeline.
- UI overhaul unrelated to file-ref selection.

## Implementation plan

- UI contract: add a file field kind in action schemas and form renderer (value = `FileRef[]`).
- Picker UI: list available file refs via API, display labels only, no paths.
- Defaults: support settings/action prefill values; preselect when available; block execution with validation error if
  missing.
- Submission:
  - Actions: submit per-field `FileRef[]` values as part of the action input payload.
  - Runs: submit uploads/refs per field (no flat `files[]`/`file_refs[]` semantics).
- Resolver + manifest: ensure the staged input manifest preserves field ownership for each staged file.
- Tests: unit tests for normalization + validation; update OpenAPI types if needed.
- Docs: keep contracts explicit and non-ambiguous (MUST/FORBIDDEN language).

## Test plan

- Frontend: `pdm run fe-test`
- Backend (if API changes): `pdm run test` or targeted tests
- Playwright: relevant picker/action flows (no overlap with sandbox file-refs reuse script)

## Rollback plan

- Revert commit; remove UI field kind and picker wiring; restore previous form rendering.

## Closeout Status (as of 2026-06-18)

`PR-0359` repairs this slice to `done`. The current repo ships the dedicated
file-ref field rendering, defaults/validation behavior, available-file-refs
endpoints, and resolver-backed per-field submission path described here.
