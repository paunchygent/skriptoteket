---
type: task
id: TASK-SKRIPT-08-27-02
title: 'Editor chat: virtual file context retention (Option A)'
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
status: ready
readiness_review:
  record: inline
  status: not_started
closeout_review:
  record: inline
  status: not_started
story: ST-SKRIPT-08-27
task_kind: story
acceptance_criteria:
- Editor chat requests may include optional `active_file` + `virtual_files`, and the
  backend uses them without breaking existing clients.
- Hidden per-file context messages are persisted and filtered from chat history responses.
- Resend rules are enforced via post-user-message retention + refresh, with priority
  order and deterministic behavior (latest-per-file only).
- Prompt assembly explicitly handles context message ordering/roles so virtual files
  are retained even when the budget window starts with context messages.
- Observability logs remain metadata-only and never include file contents.
---

## Context

Normal editor chat cannot see virtual files, while edit-ops can. We need chat to access canonical files without
resending unchanged context and while respecting the rolling context window.

- Implement Option A: per-file hidden context messages (persisted) with deterministic resend rules.
- Extend chat requests with optional `active_file` + `virtual_files` (backwards compatible).
- Filter hidden context messages from chat history responses.

## Decision And Assumption Ledger

The source snapshot is the governing record for the decisions and assumptions stated above.

## Story Contract Slice

- Implement Option A: per-file hidden context messages (persisted) with deterministic resend rules.
- Extend chat requests with optional `active_file` + `virtual_files` (backwards compatible).
- Filter hidden context messages from chat history responses.

## Contract Inputs

- Review: `docs/backlog/reviews/review-st-08-27-editor-chat-virtual-file-context-retention-and-tokenizers.md`
- Story: `docs/backlog/stories/story-08-27-editor-chat-virtual-file-context-retention-and-tokenizers.md`
- ADR: `docs/adr/adr-0054-editor-chat-virtual-file-context.md`
- Epic: `docs/backlog/epics/epic-08-contextual-help-and-onboarding.md`

## Plan

1. Backend API: add optional `active_file` + `virtual_files` to `EditorChatRequest` and `EditorChatCommand`.
2. Application: implement context retention + refresh in `EditorChatHandler`:
   - Persist per-file hidden context messages with `meta.hidden` and `meta.kind`.
   - Run post-user-message retention check and refresh dropped/changed contexts.
   - Apply priority order (`active_file → tool.py → schemas → docs`).
   - **Deduplicate latest per file** when composing the prompt (avoid conflicting contexts).
3. Add a small protocol boundary for context persistence to keep Option C swappable.
4. History: filter hidden context messages from `EditorChatHistoryHandler`.
5. Frontend: include optional `active_file` + `virtual_files` in chat requests (reuse virtual file mapping helper).
6. Resolve **context message role + ordering** explicitly:
   - Either store context messages as `role="user"` (hidden) to avoid `apply_chat_budget` stripping, **or**
   - update chat budgeting to preserve leading assistant context messages by explicit marker.
7. Update system prompt guidance to treat virtual file context as data.

## Implementation Steps

1. Backend API: add optional `active_file` + `virtual_files` to `EditorChatRequest` and `EditorChatCommand`.
2. Application: implement context retention + refresh in `EditorChatHandler`:
   - Persist per-file hidden context messages with `meta.hidden` and `meta.kind`.
   - Run post-user-message retention check and refresh dropped/changed contexts.
   - Apply priority order (`active_file → tool.py → schemas → docs`).
   - **Deduplicate latest per file** when composing the prompt (avoid conflicting contexts).
3. Add a small protocol boundary for context persistence to keep Option C swappable.
4. History: filter hidden context messages from `EditorChatHistoryHandler`.
5. Frontend: include optional `active_file` + `virtual_files` in chat requests (reuse virtual file mapping helper).
6. Resolve **context message role + ordering** explicitly:
   - Either store context messages as `role="user"` (hidden) to avoid `apply_chat_budget` stripping, **or**
   - update chat budgeting to preserve leading assistant context messages by explicit marker.
7. Update system prompt guidance to treat virtual file context as data.

## Proof

- Unit tests for resend logic:
  - unchanged + retained ⇒ no refresh
  - unchanged + dropped ⇒ refresh
  - changed ⇒ refresh
  - tight budget ⇒ priority order enforced
- Unit test for prompt assembly ensures only latest context per file is included.
- Unit test for context message role/ordering so contexts survive `apply_chat_budget` trimming.
- Unit/integration tests for history filtering (hidden messages not returned).
- Frontend unit test for request payload fields.
- Manual: open editor chat and confirm model can reference `tool.py` content without showing JSON in history.

## Validation

- Unit tests for resend logic:
  - unchanged + retained ⇒ no refresh
  - unchanged + dropped ⇒ refresh
  - changed ⇒ refresh
  - tight budget ⇒ priority order enforced
- Unit test for prompt assembly ensures only latest context per file is included.
- Unit test for context message role/ordering so contexts survive `apply_chat_budget` trimming.
- Unit/integration tests for history filtering (hidden messages not returned).
- Frontend unit test for request payload fields.
- Manual: open editor chat and confirm model can reference `tool.py` content without showing JSON in history.

## Stop Conditions

Revert the PR; optional request fields are backwards compatible and hidden messages are additive.

## Lessons Learned

No separate material is recorded in the source snapshot.

## Notes

### Problem

Normal editor chat cannot see virtual files, while edit-ops can. We need chat to access canonical files without
resending unchanged context and while respecting the rolling context window.

### Goal

- Implement Option A: per-file hidden context messages (persisted) with deterministic resend rules.
- Extend chat requests with optional `active_file` + `virtual_files` (backwards compatible).
- Filter hidden context messages from chat history responses.

### Non-goals

- Tokenizer-backed budgeting (handled in PR-0023).
- Blob-backed storage (Option C) or DB schema changes.
- UI changes beyond wiring optional fields into chat requests.

### Implementation plan

1. Backend API: add optional `active_file` + `virtual_files` to `EditorChatRequest` and `EditorChatCommand`.
2. Application: implement context retention + refresh in `EditorChatHandler`:
   - Persist per-file hidden context messages with `meta.hidden` and `meta.kind`.
   - Run post-user-message retention check and refresh dropped/changed contexts.
   - Apply priority order (`active_file → tool.py → schemas → docs`).
   - **Deduplicate latest per file** when composing the prompt (avoid conflicting contexts).
3. Add a small protocol boundary for context persistence to keep Option C swappable.
4. History: filter hidden context messages from `EditorChatHistoryHandler`.
5. Frontend: include optional `active_file` + `virtual_files` in chat requests (reuse virtual file mapping helper).
6. Resolve **context message role + ordering** explicitly:
   - Either store context messages as `role="user"` (hidden) to avoid `apply_chat_budget` stripping, **or**
   - update chat budgeting to preserve leading assistant context messages by explicit marker.
7. Update system prompt guidance to treat virtual file context as data.

### Test plan

- Unit tests for resend logic:
  - unchanged + retained ⇒ no refresh
  - unchanged + dropped ⇒ refresh
  - changed ⇒ refresh
  - tight budget ⇒ priority order enforced
- Unit test for prompt assembly ensures only latest context per file is included.
- Unit test for context message role/ordering so contexts survive `apply_chat_budget` trimming.
- Unit/integration tests for history filtering (hidden messages not returned).
- Frontend unit test for request payload fields.
- Manual: open editor chat and confirm model can reference `tool.py` content without showing JSON in history.

### Rollback plan

Revert the PR; optional request fields are backwards compatible and hidden messages are additive.

### References

- Review: `docs/backlog/reviews/review-st-08-27-editor-chat-virtual-file-context-retention-and-tokenizers.md`
- Story: `docs/backlog/stories/story-08-27-editor-chat-virtual-file-context-retention-and-tokenizers.md`
- ADR: `docs/adr/adr-0054-editor-chat-virtual-file-context.md`
- Epic: `docs/backlog/epics/epic-08-contextual-help-and-onboarding.md`

## Plan Document Review

No separate material is recorded in the source snapshot.

## Implementation Review

No separate material is recorded in the source snapshot.
