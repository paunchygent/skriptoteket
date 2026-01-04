---
type: story
id: ST-14-30
title: "Editor: working copy persistence (IndexedDB) + checkpoints + restore"
status: ready
owners: "agents"
created: 2026-01-04
updated: 2026-01-04
epic: "EPIC-14"
acceptance_criteria:
  - "Given a tool author has unsaved changes, when the browser is reloaded or reopened, then the editor can restore a local working copy for the same user + tool."
  - "Given a local working copy exists and differs from the server-loaded version, then the UI shows a restore prompt with: View diff, Restore working copy, and Discard."
  - "Given the working copy is being edited, then the editor autosaves the working copy head to IndexedDB (debounced) and the head expires after 30 days."
  - "Given the working copy is dirty, then the editor creates rolling checkpoints (max 20) approximately every 60s while dirty, and also on key events (beforeunload, before server Save, before applying an AI proposal)."
  - "Given auto checkpoints exist, then they expire after 7 days."
  - "Given the user explicitly creates a checkpoint (\"Skapa återställningspunkt\"), then it is pinned and does not expire."
  - "Given checkpoints exist, then the user can restore an older/newer checkpoint (undo/redo across browser reloads) without affecting server versions until they Save."
  - "Given the user restores to the current server version, then the local working copy head and all checkpoints are cleared and the editor buffers match the server-loaded version."
dependencies:
  - "ADR-0027"
  - "ST-14-17"
  - "ST-14-18"
ui_impact: "Yes"
data_impact: "No (client-side persistence only)"
---

## Notes

- Store is scoped per user + tool (prevents cross-account mixing on shared machines).
- Use a small IndexedDB helper library (e.g. `idb`) to avoid raw IndexedDB boilerplate.
- AI alignment: chat/edit proposals operate on the working copy, so persistence reduces “lost work” risk.

## Implementation decisions

- Storage:
  - Use IndexedDB via `idb`.
  - Implement a small shared IndexedDB helper for editor persistence so other editor surfaces can reuse it (e.g. chat history in ST-08-20).
  - **Decided keying:** scope all editor working-copy persistence by `{user_id, tool_id}` (never by `version_id`).
  - Store `base_version_id` as metadata inside the persisted payload (not in the key) so saving/new versions do not “lose” the working copy.
  - Persist only the 5 editor fields: `source_code`, `entrypoint`, `settings_schema`, `input_schema`, `usage_instructions`.
- Autosave head:
  - Debounced write (≈1–2s while dirty).
  - TTL: 30 days.
- Checkpoints:
  - Rolling max: 20 auto checkpoints.
  - Auto checkpoint cadence: ~60s while dirty + on key events (beforeunload, before server Save, before applying an AI proposal).
  - AI apply safety: create a clearly labeled auto checkpoint (e.g. “Before AI apply”) immediately before applying a proposal (ST-08-22) so users can restore even after subsequent manual edits.
  - Auto checkpoint TTL: 7 days.
  - Manual checkpoints (“Skapa återställningspunkt”) are pinned and do not expire.
- UX:
  - If a working copy exists and differs from the server-loaded version, show a restore prompt that can open the ST-14-17 diff viewer for “working vs server”.
  - “Restore to current server version” resets buffers to the loaded version and clears all local data (head + checkpoints).
