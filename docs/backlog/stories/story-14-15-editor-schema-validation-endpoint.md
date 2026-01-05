---
type: story
id: ST-14-15
title: "Editor: schema validation endpoint (settings_schema/input_schema)"
status: done
owners: "agents"
created: 2025-12-29
updated: 2026-01-05
epic: "EPIC-14"
acceptance_criteria:
  - "Given an author has draft schema JSON, when calling the validation endpoint, then the backend validates JSON shape, Pydantic parsing, and domain normalization rules."
  - "Given validation fails, then the response includes structured errors suitable for UI display (including field paths where possible)."
  - "Given validation succeeds, then the endpoint returns a success response without creating/updating versions."
  - "Given input_schema contains a file field, when validating, then the endpoint enforces file field invariants and rejects values that exceed server upload limits (e.g. max > UPLOAD_MAX_FILES)."
dependencies:
  - "ST-14-04"
  - "ST-14-09"
ui_impact: "Indirect (enables UI feedback)"
data_impact: "No (no persistence; new API only)"
---

## Notes

Reference: `docs/reference/ref-tool-editor-dx-review-2025-12-29.md`

## Decisions (locked in)

- Validation is not an error/exception: the endpoint returns `200 OK` with `{ valid: boolean, issues: [...] }`.
  - Rationale: invalid schemas are expected while editing; using `DomainError`/422 would generate warning log spam via the
    DomainError middleware.
- Validation issues should be stable + UI-friendly:
  - `schema`: `"settings_schema"` | `"input_schema"`
  - `path`: JSON Pointer-ish string where possible (e.g. `"/0/max"`), derived from Pydantic `loc`.
  - `message`: user-actionable message (what/where/how to fix).
  - `details`: optional machine details for debugging (kept small).

## API (proposed contract)

- `POST /api/v1/editor/tools/{tool_id}/validate-schemas`
- Request body:
  - `settings_schema`: nullable (JSON array when present)
  - `input_schema`: required (JSON array; `null` is invalid)
  - Use permissive JSON types in the request model so parseable-but-wrong-shape becomes `issues[]` (not FastAPI 422).
- Response body:
  - Always `200 OK` for validation results (`valid=true/false`).
  - Non-200 only for real failures (e.g. `403` permissions, `404` tool/version not found).

## Implementation Plan

- Domain:
  - Add a pure validator for file upload limits (accept `upload_max_files` as an argument) and enforce:
    - `file.max <= upload_max_files`
    - `file.min <= upload_max_files`
  - Keep enforcement in domain normalization/validation to match runtime behavior (avoid “passes validation but fails at run”).
- Application:
  - Add a `ValidateToolSchemasHandler` (protocol-first DI) that:
    - enforces editor access (contributor must be maintainer; admin/superuser allowed)
    - parses schemas with Pydantic and runs existing normalization (`normalize_tool_input_schema`, `normalize_tool_settings_schema`)
    - maps Pydantic validation errors + `DomainError(VALIDATION_ERROR)` into `issues[]`
    - enforces upload max files using `Settings.UPLOAD_MAX_FILES`
    - never raises for “invalid schema”; returns `valid=false` + issues.
- Web/API:
  - Add request/response Pydantic models for the endpoint under `src/skriptoteket/web/api/v1/editor/models.py`.
  - Add a new editor router module for schema validation and include it from `src/skriptoteket/web/api/v1/editor/__init__.py`.
- Tests:
  - Unit-test domain helpers (file field limits).
  - Unit-test handler behavior (permissions + `issues[]` mapping + upload max enforcement) using protocol mocks.

## Verification (planned)

- `pdm run lint`
- `pdm run typecheck`
- `pdm run test`
