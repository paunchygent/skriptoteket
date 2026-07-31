---
type: adr
id: ADR-SKRIPT-0054
title: Editor chat virtual file context (hidden snapshots)
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
status: proposed
deciders:
- user-lead
retired_ids:
- ADR-0054
---

## Context

### Source: Context

Normal editor chat does not receive virtual files, while edit-ops does. We need editor chat to see the current
canonical virtual files without repeatedly resending unchanged file content, and without changing the chat UI.
Research is captured in:

- `docs/reference/reports/ref-editor-chat-virtual-file-context-tokenizers-2026-01-11.md`

## Decision

### Source: Decision

- Represent each virtual file as a **hidden assistant message** stored in `tool_session_messages` with metadata
  (`meta.hidden=true`, `meta.kind="virtual_file_context"`, `meta.file_id`, `meta.fingerprint`).
- Add optional `active_file` + `virtual_files` to `EditorChatRequest` (backwards compatible).
- Use a **post-user-message retention + refresh** algorithm:
  - No resend when unchanged and retained.
  - Refresh when dropped by budget or changed.
  - Prioritize `active_file → tool.py → schemas → docs` when budget is tight.
- **Budgeting rule:** trimming may drop leading assistant messages **except** those that are marked as
  virtual file context (`meta.kind="virtual_file_context"` or `virtual_file_context` envelope).
- Filter hidden context messages out of the chat history API response.
- Implement context persistence behind a protocol so a future swap to blob-backed storage (Option C) is trivial.

## Non-Decisions

The source does not authorize additional alternatives or scope beyond the decision above.

## Consequences

### Source: Consequences

- Minimal DB changes (no new tables required).
- Requires filtering hidden context messages from chat history responses.
- Storage growth is bounded but may require pruning if usage scales.
- Design supports a future refactor to blob-backed context storage without changing domain logic.
