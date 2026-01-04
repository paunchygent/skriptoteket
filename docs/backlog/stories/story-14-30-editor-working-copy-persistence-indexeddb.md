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
  - "Given a tool author has unsaved changes, when the browser is reloaded or
reopened, then the editor can restore a local working copy for the same user +
tool."
  - "Given a local working copy exists and differs from the server-loaded
version, then the UI shows a restore prompt with: View diff, Restore working
copy, and Discard."
  - "Given the working copy is being edited, then the editor autosaves the
working copy head to IndexedDB (debounced) and the head expires after 30
days."
  - "Given the working copy is dirty, then the editor creates rolling
checkpoints (max 20) approximately every 60s while dirty, and also on key
events (before server Save, before applying an AI proposal, and best-effort on
navigation/reload)."
  - "Given auto checkpoints exist, then they expire after 7 days."
  - "Given the user explicitly creates a checkpoint (\"Skapa
återställningspunkt\"), then it is pinned and does not expire."
  - "Given pinned checkpoints exist, then they are user-deletable and capped
(e.g. max 20 pinned per {user_id, tool_id}) so IndexedDB growth remains
bounded."
  - "Given checkpoints exist, then the user can restore an older/newer
checkpoint (undo/redo across browser reloads) without affecting server
versions until they Save."
  - "Given the user restores to the current server version, then the local
working copy head and all checkpoints are cleared and the editor buffers match
the server-loaded version."
dependencies:
  - "ADR-0027"
  - "ST-14-17"
ui_impact: "Yes"
data_impact: "No (client-side persistence only)"
---

## Notes

- Store is scoped per user + tool (prevents cross-account mixing on shared
  machines).
- Use a small IndexedDB helper library (e.g. `idb`) to avoid raw IndexedDB
  boilerplate.
- AI alignment: chat/edit proposals operate on the working copy, so
  persistence reduces “lost work” risk.

See also:

- Diff viewer primitive: `docs/backlog/stories/story-14-17-editor-version-
diff-view.md`
- Compare uses `compare=working`: `docs/backlog/stories/story-14-18-editor-
review-navigation-and-compare.md`
- Chat history reuse of the same IndexedDB helper: `docs/backlog/stories/
story-08-20-editor-ai-chat-drawer-mvp.md`
- AI apply safety checkpoints: `docs/backlog/stories/story-08-22-editor-ai-
diff-preview-apply-undo.md`

## Implementation decisions

### Storage + keying

- Use IndexedDB via a small helper (e.g. `idb`).
- Implement a shared editor persistence module so other editor surfaces can
  reuse it (e.g. chat history in ST-08-20).
- **Decided keying:** scope all editor working-copy persistence by `{user_id,
  tool_id}` (never by `version_id`).
- Store `base_version_id` as metadata inside the persisted payload (not in the
  key) so saving/new versions do not “lose” the working copy.
- Persist only the 5 editor fields:
  - `source_code`
  - `entrypoint`
  - `settings_schema`
  - `input_schema`
  - `usage_instructions`

### Persistence schema (explicit)

- Database name: `skriptoteket_editor` (versioned; bump when adding stores/
  indices).
- Object stores:
  - `working_copy_heads`
    - Primary key: `{ user_id, tool_id }`
    - Value: `{ base_version_id, fields..., updated_at, expires_at }`
  - `checkpoints`
    - Primary key: `{ user_id, tool_id, checkpoint_id }`
    - Value: `{ kind: auto|pinned, label, base_version_id, fields...,
created_at, expires_at|null }`
    - Query needs: list by `{user_id, tool_id}` ordered by `created_at`
  - (Reserved now for ST-08-20 to avoid schema churn) `chat_threads`
- All stored text must be treated as opaque bytes for diff/fingerprint
  purposes (no normalization beyond what the editor produces).

### Autosave head (working copy)

- Debounced write while dirty (≈1–2s).
- TTL: 30 days (`expires_at`).
- On load/open, purge expired heads for the current user (and
  opportunistically purge old records for space hygiene).

### Checkpoints

- Rolling max: 20 auto checkpoints per `{user_id, tool_id}`.
- Auto checkpoint cadence: ~60s while dirty + on key events:
  - before server Save
  - before applying an AI proposal (ST-08-22)
  - on `pagehide` / `visibilitychange` (best-effort safety on navigation/
reload)
- Auto checkpoint TTL: 7 days (`expires_at`).
- Manual checkpoints (“Skapa återställningspunkt”) are pinned:
  - `expires_at = null` (no TTL)
  - Must be user-deletable
  - Must be capped (e.g. max 20 pinned per `{user_id, tool_id}`); when
exceeded, block creation with a clear message or require deleting an older
pinned checkpoint.
- AI apply safety: create a clearly labeled auto checkpoint (e.g. “Before AI
  apply”) immediately before applying a proposal so users can restore even after
  subsequent manual edits.

### UX

- If a working copy exists and differs from the server-loaded version, show a
  restore prompt with:
  - View diff (reuse ST-14-17 diff viewer for “working vs server”)
  - Restore working copy
  - Discard working copy
- “Restore to current server version” resets buffers to the loaded version and
  clears all local data (head + checkpoints) for `{user_id, tool_id}`.
