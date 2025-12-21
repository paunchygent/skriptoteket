---
type: story
id: ST-12-01
title: "Multi-file upload support"
status: ready
owners: "agents"
created: 2025-12-21
epic: "EPIC-12"
acceptance_criteria:
  - "Given user selects multiple files in the upload form, when the form is submitted, then all files are sent to the runner"
  - "Given multiple files are uploaded, when the script runs, then all files are available in /work/input/"
  - "Given multiple files are uploaded, when the script reads SKRIPTOTEKET_INPUT_MANIFEST, then JSON contains metadata for all files"
  - "Given a single file is uploaded, when the script runs, then SKRIPTOTEKET_INPUT_PATH points to that file (backward compatibility)"
  - "Given the knowledge base, when an LLM generates a multi-file script, then the documented patterns work correctly"
ui_impact: "Upload form supports multiple file selection; file list shown before submit"
data_impact: "ToolRun may store multiple input filenames in metadata"
---

## Context

The current runner contract restricts scripts to a single input file. This prevents tools that need to process
related files together, such as HTML with external CSS, or cross-file data comparison.

PRD-script-hub-v0.2 defines "Advanced Input Handling (Multi-File & External Sources)" as a key v0.2 feature.

## Scope

- Frontend: Add `multiple` attribute to file inputs; show selected files list
- Command layer: Accept `list[tuple[str, bytes]]` instead of single file
- Runner: Place all files in `/work/input/`; generate `SKRIPTOTEKET_INPUT_MANIFEST`
- Backward compat: Preserve `SKRIPTOTEKET_INPUT_PATH` for single-file uploads
- Knowledge base: Add multi-file script patterns

## Out of scope

- External data source fetchers (future story)
- ZIP auto-extraction
- File type validation per tool

## Dependencies

- ADR-0031 (Multi-file input contract)
