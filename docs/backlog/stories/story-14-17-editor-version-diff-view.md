---
type: story
id: ST-14-17
title: "Editor: version diff view (code + schemas + instructions)"
status: ready
owners: "agents"
created: 2025-12-29
updated: 2026-01-04
epic: "EPIC-14"
acceptance_criteria:
  - "Given two visible tool versions, when a reviewer opens the diff view, then they can compare source_code, entrypoint, settings_schema, input_schema, and usage_instructions."
  - "Given the reviewer lacks access to a version, then they cannot diff it and the UI is explicit about the restriction."
  - "Given diffs are large, then the UI remains usable and supports copy + download of compared content (before.txt, after.txt, and a unified patch)."
  - "Given a user downloads a unified patch, then it uses stable pseudo-paths derived from the canonical virtual file ids (e.g. a/tool.py → b/tool.py)."
  - "Given the diff viewer will be reused for AI 'proposed changes' previews, when implementing the diff view, then diff rendering is built as a reusable component that can compare arbitrary before/after text blobs (not hard-coded to version IDs)."

dependencies:
  - "ADR-0027"

ui_impact: "Yes"
data_impact: "No (read-only view)"
---

## Notes

AI alignment: implement a single diff viewer primitive that can later power
chat-based edit previews (current text vs proposed text) without duplicating
diff logic.

Reference: `docs/reference/ref-tool-editor-dx-review-2025-12-29.md`

See also:

- Compare routing + deep links: `docs/backlog/stories/story-14-18-editor-
review-navigation-and-compare.md`
- Working copy restore diff: `docs/backlog/stories/story-14-30-editor-working-
copy-persistence-indexeddb.md`
- AI diff preview: `docs/backlog/stories/story-08-22-editor-ai-diff-preview-
apply-undo.md`

## Implementation decisions

- Implement a reusable diff viewer component that accepts a **list of diff
  items** (tabs) where each item is arbitrary before/after text + labels, so it
  can be reused by:
  - version compare (ST-14-18)
  - working-copy restore diff (ST-14-30)
  - AI “proposed changes” previews (ST-08-22)
- Prefer CodeMirror-based diff rendering (merge/diff view) for performance and
  code ergonomics (large diffs, copyable text).
- Standardize the editor “virtual files” mapping (shared across version
  compare, working copy, and AI edit ops):
  - `tool.py` → `source_code`
  - `entrypoint.txt` → `entrypoint`
  - `settings_schema.json` → `settings_schema`
  - `input_schema.json` → `input_schema`
  - `usage_instructions.md` → `usage_instructions`
  - **Canonicality:** these virtual file ids are the single source of truth
  for:
    - ST-14-18 `field=` deep links
    - ST-08-21 edit-ops `target_file`
    - ST-08-22 diff preview tabs
- Support downloads for the currently selected virtual file:
  - `before.txt` (full “before” snapshot)
  - `after.txt` (full “after” snapshot)
  - `changes.patch` (unified patch / git-style diff)
    - Patch MUST use stable pseudo-paths derived from the virtual file id
  (e.g. `a/tool.py` → `b/tool.py`).
    - Patch SHOULD be LF-normalized and include a trailing newline.
