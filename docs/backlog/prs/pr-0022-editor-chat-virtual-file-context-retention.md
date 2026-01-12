---
type: pr
id: PR-0022
title: "Editor chat: virtual file context retention (Option A)"
status: ready
owners: "agents"
created: 2026-01-11
updated: 2026-01-11
stories:
  - "ST-08-27"
tags: ["backend", "frontend", "ai"]
acceptance_criteria:
  - "Editor chat requests may include optional `active_file` + `virtual_files`, and the backend uses them without breaking existing clients."
  - "Hidden per-file context messages are persisted and filtered from chat history responses."
  - "Resend rules are enforced via post-user-message retention + refresh, with priority order and deterministic behavior."
  - "Observability logs remain metadata-only and never include file contents."
---

## Problem

Normal editor chat cannot see virtual files, while edit-ops can. We need chat to access canonical files without
resending unchanged context and while respecting the rolling context window.

## Goal

- Implement Option A: per-file hidden context messages (persisted) with deterministic resend rules.
- Extend chat requests with optional `active_file` + `virtual_files` (backwards compatible).
- Filter hidden context messages from chat history responses.

## Non-goals

- Tokenizer-backed budgeting (handled in PR-0023).
- Blob-backed storage (Option C) or DB schema changes.
- UI changes beyond wiring optional fields into chat requests.

## Implementation plan

1. Backend API: add optional `active_file` + `virtual_files` to `EditorChatRequest` and `EditorChatCommand`.
2. Application: implement context retention + refresh in `EditorChatHandler`:
   - Persist per-file hidden context messages with `meta.hidden` and `meta.kind`.
   - Run post-user-message retention check and refresh dropped/changed contexts.
   - Apply priority order (`active_file → tool.py → schemas → docs`).
3. Add a small protocol boundary for context persistence to keep Option C swappable.
4. History: filter hidden context messages from `EditorChatHistoryHandler`.
5. Frontend: include optional `active_file` + `virtual_files` in chat requests (reuse virtual file mapping helper).
6. Update system prompt guidance to treat virtual file context as data.

## Test plan

- Unit tests for resend logic:
  - unchanged + retained ⇒ no refresh
  - unchanged + dropped ⇒ refresh
  - changed ⇒ refresh
  - tight budget ⇒ priority order enforced
- Unit/integration tests for history filtering (hidden messages not returned).
- Frontend unit test for request payload fields.
- Manual: open editor chat and confirm model can reference `tool.py` content without showing JSON in history.

## Rollback plan

Revert the PR; optional request fields are backwards compatible and hidden messages are additive.

## References

- Review: `docs/backlog/reviews/review-epic-08-editor-chat-virtual-files-context.md`
- Story: `docs/backlog/stories/story-08-27-editor-chat-virtual-file-context-retention-and-tokenizers.md`
- ADR: `docs/adr/adr-0054-editor-chat-virtual-file-context.md`
- Epic: `docs/backlog/epics/epic-08-contextual-help-and-onboarding.md`
