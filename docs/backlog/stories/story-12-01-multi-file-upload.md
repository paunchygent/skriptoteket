---
type: story
id: ST-12-01
title: "Multi-file upload support"
status: done
owners: "agents"
created: 2025-12-21
epic: "EPIC-12"
acceptance_criteria:
  - "Given user selects multiple files in the upload form, when the form is submitted, then all files are sent to the runner"
  - "Given user uploads multiple files with colliding sanitized filenames, when the form is submitted, then the request is rejected with a validation error instructing the user to rename locally"
  - "Given multiple files are uploaded, when the script runs, then all files are available in /work/input/"
  - "Given a script runs, when it reads SKRIPTOTEKET_INPUT_DIR, then it points to /work/input/"
  - "Given multiple files are uploaded, when the script reads SKRIPTOTEKET_INPUT_MANIFEST, then JSON contains metadata for all files"
  - "Given the platform enforces upload caps, when the user uploads files exceeding per-file or total limits, then the request is rejected with a validation error (no runner execution)"
  - "Given a tool run exists, when inspecting it in the admin UI or DB, then ToolRun stores an input_manifest (names + bytes) for audit/debugging"
  - "Given the knowledge base, when an LLM generates a multi-file script, then the documented patterns work correctly"
ui_impact: "Upload form supports multiple file selection; file list shown before submit"
data_impact: "ToolRun stores input_manifest JSON (names + bytes) for audit/debugging"
dependencies: ["ADR-0031"]
---

## Context

The current runner contract restricts scripts to a single input file. This prevents tools that need to process
related files together, such as HTML with external CSS, or cross-file data comparison.

PRD-script-hub-v0.2 defines "Advanced Input Handling (Multi-File & External Sources)" as a key v0.2 feature.

## Scope

- Frontend: Add `multiple` attribute to file inputs; show selected files list (single-file default UI)
- Validation: Sanitize filenames and reject duplicates after sanitization
- Limits: Enforce per-file and total upload size caps (settings-driven)
- Command layer: Accept `list[tuple[str, bytes]]` instead of single file
- Runner: Place all files in `/work/input/`; generate `SKRIPTOTEKET_INPUT_MANIFEST` with `{"files":[{name,path,bytes}]}`
- Runner: Set `SKRIPTOTEKET_INPUT_DIR=/work/input` and remove `SKRIPTOTEKET_INPUT_PATH`
- Persistence: Store input_manifest (names + bytes) on ToolRun
- Knowledge base: Add multi-file script patterns

## Out of scope

- External data source fetchers (future story)
- ZIP auto-extraction
- File type validation per tool
- Tool-defined input slots/required files (future story)

## Dependencies

- ADR-0031 (Multi-file input contract)

## Implemented (2025-12-21)

- Runner contract: `SKRIPTOTEKET_INPUT_MANIFEST` (stable minimal shape) + all files placed in `/work/input/`.
- Runner contract: `SKRIPTOTEKET_INPUT_DIR=/work/input` (scripts discover inputs via the manifest).
- Validation: reject filename collisions after sanitization with a clear user error.
- Safety: settings-driven upload caps enforced while reading uploads (per-file + total).
- Persistence: `tool_runs.input_manifest` JSONB (names + bytes only) with migration + idempotency contract test.
