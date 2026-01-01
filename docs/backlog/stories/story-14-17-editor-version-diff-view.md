---
type: story
id: ST-14-17
title: "Editor: version diff view (code + schemas + instructions)"
status: ready
owners: "agents"
created: 2025-12-29
updated: 2026-01-01
epic: "EPIC-14"
acceptance_criteria:
  - "Given two visible tool versions, when a reviewer opens the diff view, then they can compare source_code, entrypoint, settings_schema, input_schema, and usage_instructions."
  - "Given the reviewer lacks access to a version, then they cannot diff it and the UI is explicit about the restriction."
  - "Given diffs are large, then the UI remains usable and allows copy/download of compared content."
  - "Given the diff viewer will be reused for AI 'proposed changes' previews, when implementing the diff view, then diff rendering is built as a reusable component that can compare arbitrary before/after text blobs (not hard-coded to version IDs)."
dependencies:
  - "ADR-0027"
ui_impact: "Yes"
data_impact: "No (read-only view)"
---

## Notes

AI alignment: implement a single diff viewer primitive that can later power chat-based edit previews (current text vs proposed text) without duplicating diff logic.

Reference: `docs/reference/ref-tool-editor-dx-review-2025-12-29.md`
