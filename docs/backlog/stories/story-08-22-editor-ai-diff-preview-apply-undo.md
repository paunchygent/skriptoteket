---
type: story
id: ST-08-22
title: "Editor: AI proposed changes diff preview + apply/undo"
status: ready
owners: "agents"
created: 2026-01-01
updated: 2026-01-04
epic: "EPIC-08"
acceptance_criteria:
  - "Given the chat has produced a proposed edit operation list (potentially across multiple virtual files), when the user opens preview, then the UI shows diffs (current vs proposed) per targeted file before any change is applied."
  - "Given the editor becomes read-only (draft lock), when a proposal exists, then apply is disabled and the UI explains why."
  - "Given the backend returned `base_fingerprints` with the proposal, when any targeted virtual file has changed since proposal generation, then apply is blocked using fingerprint comparison (not best-effort string compares) and the UI offers a Regenerate CTA."
  - "Given checkpoints exist (ST-14-30), when the user clicks Apply, then the editor creates a labeled checkpoint immediately before applying (e.g. \"Before AI apply\")."
  - "Given the user clicks Apply, when the proposal is applied, then all file edits are applied atomically (all-or-nothing) so a single Undo action restores the prior state."
  - "Given the user has applied a proposal and has not made subsequent edits, when they click Undo, then the applied AI change is reverted across all files."
  - "Given the user has applied a proposal and then makes subsequent edits, then Undo is not offered (or is disabled) and the UI points the user to restoring via checkpoints (ST-14-30) instead."
  - "Given the user discards a proposal, when they click Discard, then the pending proposal is cleared and no editor changes occur."

dependencies:
  - "ST-14-17"
  - "ST-14-30"
  - "ST-08-21"

ui_impact: "Yes (diff preview + apply/undo UX)"
data_impact: "No (client-side apply; uses local checkpoints from ST-14-30)"
---

## Context

Chat-driven edits must be auditable and safe. Users should always see what
will change (diff preview), apply changes
explicitly, and be able to undo reliably.

## Notes

This story intentionally reuses the version diff viewer work (ST-14-17) as the
diff UI primitive so we don’t build two
diff implementations.

- **Decided:** the diff preview must use the same canonical virtual-file map
  as ST-14-17/08-21 (tool.py, entrypoint.txt, settings_schema.json,
  input_schema.json, usage_instructions.md), rendered as a list of diff items
  (tabs) with shared download/patch behavior.
- Checkpoint safety: “Apply” must create a labeled checkpoint immediately
  before applying (e.g. “Before AI apply”) so users can roll back even if Undo
  is no longer applicable after subsequent edits.
