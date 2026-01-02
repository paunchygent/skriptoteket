---
type: story
id: ST-08-22
title: "Editor: AI proposed changes diff preview + apply/undo"
status: ready
owners: "agents"
created: 2026-01-01
epic: "EPIC-08"
acceptance_criteria:
  - "Given the chat has produced a proposed edit operation list (potentially across multiple virtual files), when the user opens preview, then the UI shows diffs (current vs proposed) per targeted file before any change is applied."
  - "Given the editor becomes read-only (draft lock), when a proposal exists, then apply is disabled and the UI explains why."
  - "Given the underlying text in any targeted virtual file changes after the proposal was generated, when applying is attempted, then apply is blocked and the user is prompted to regenerate the proposal."
  - "Given the user clicks Apply, when the proposal is applied, then all file edits are applied atomically (all-or-nothing) so a single Undo action restores the prior state."
  - "Given the user has applied a proposal and has not made subsequent edits, when they click Undo, then the applied AI change is reverted across all files."
  - "Given the user discards a proposal, when they click Discard, then the pending proposal is cleared and no editor changes occur."
dependencies:
  - "ST-14-17"
  - "ST-08-21"
ui_impact: "Yes (diff preview + apply/undo UX)"
data_impact: "No (client-side apply; no persistence)"
---

## Context

Chat-driven edits must be auditable and safe. Users should always see what will change (diff preview), apply changes
explicitly, and be able to undo reliably.

## Notes

This story intentionally reuses the version diff viewer work (ST-14-17) as the diff UI primitive so we don’t build two
diff implementations.
