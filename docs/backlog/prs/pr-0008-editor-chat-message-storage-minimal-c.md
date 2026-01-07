---
type: pr
id: PR-0008
title: "Editor chat: normalized message storage + tail fetch"
status: done
owners: "agents"
created: 2026-01-07
updated: 2026-01-07
stories:
  - "ST-08-23"
tags: ["backend", "data"]
acceptance_criteria:
  - "Chat messages are stored in a new append-only table keyed by tool_session_id, not in tool_sessions.state."
  - "Chat history retrieval uses a tail window of 60 messages; provider context still applies prompt_budget trimming."
  - "Assistant persistence uses message_id correlation; if the user message is missing, the assistant is stored with orphaned=true metadata."
  - "DELETE /api/v1/editor/tools/{tool_id}/chat clears the message rows for that session."
  - "Existing chat history in tool_sessions is not migrated and is ignored by the new storage path."
---

## Problem

Chat streaming currently stores the full thread in tool_sessions.state (JSONB). This creates a hot read/modify/write
path that grows unbounded within TTL, risks optimistic concurrency conflicts, and is ambiguous when identical user
messages are sent concurrently.

## Goal

Normalize editor chat messages into append-only rows, fetch a bounded tail for UI/context, and keep provider context
rolling via prompt budgets. Avoid holding DB/UoW across streaming and remove state_rev conflicts tied to JSONB updates.

## Non-goals

- Backfill or preserve existing chat history stored in tool_sessions.
- Add pagination or a full chat transcript UI.
- Introduce summarization or LLM-based compression.

## Assessment: single-flight guard vs PR-0008

- The in-process guard is best-effort only (per-process) and must not be treated as correctness once PR-0008
  introduces normalized storage (multi-worker still allows overlap).
- PR-0008 should not depend on JSONB message_id/in_reply_to fields (they’re interim, no-migration). The new
  table’s message_id column becomes the source of truth.
- Keeping the guard post-PR-0008 is still useful for UX/load shedding, but correctness must come from
  message_id-based persistence in the normalized store.

## Implementation plan

1) Migration
- Add table `tool_session_messages` with columns:
  - `id` (UUID pk)
  - `tool_session_id` (UUID fk -> tool_sessions.id, on delete cascade)
  - `message_id` (UUID, unique per tool_session)
  - `role` (user|assistant)
  - `content` (text)
  - `meta` (jsonb, nullable; use for orphaned flag)
  - `sequence` (bigint, auto-increment)
  - `created_at` (timestamptz, default now)
- Indexes: `(tool_session_id, sequence desc)`, `(tool_session_id, message_id)`.

2) Protocol + repository
- Add `ToolSessionMessageRepositoryProtocol` with:
  - `append_message(tool_session_id, message_id, role, content, meta=None)`
  - `list_tail(tool_session_id, limit)`
  - `delete_all(tool_session_id)`
- Add PostgreSQL implementation + SQLAlchemy model.

3) Chat handler changes
- Generate a `message_id` for each user message.
- Persist user message row before provider call.
- Build provider context from `list_tail(..., limit=60)` then apply `apply_chat_budget` to maintain rolling window.
- Persist assistant message on success using the same `message_id` correlation; if the user message is missing, append
  assistant with `meta={"orphaned": true}`.
- Enforce thread TTL on access by comparing the last message timestamp; chat does not update
  `tool_sessions.updated_at` for freshness.
- Stop writing chat messages into tool_sessions.state (leave empty for chat context).

4) Clear endpoint
- Update DELETE /api/v1/editor/tools/{tool_id}/chat to delete message rows for that session.

5) Tests
- Update `tests/unit/application/test_editor_chat_handler.py` for new repository protocol.
- Add repository unit tests for append + tail ordering and delete.
- Add concurrency test case for duplicate user messages (message_id-based correlation).

## Coordination notes (PR-0009)

- PR-0009 introduced `message_id`/`in_reply_to` fields inside `tool_sessions.state` as a JSONB-only, no-migration
  concurrency fix. PR-0008 should not depend on that JSON structure or attempt to migrate it.
- The in-process single-flight guard added in PR-0009 is best-effort UX/load shedding only and must not be relied on
  for correctness once normalized storage is implemented (multi-worker deployments will bypass it).

## Test plan

- `pdm run pytest tests/unit/application/test_editor_chat_handler.py -q`
- `pdm run pytest tests/integration/infrastructure/repositories/test_tool_session_message_repository.py -q`
- Manual: call chat endpoint, send two identical messages quickly, verify assistant persists for each.

## Rollback plan

- Revert migration and code changes; revert to JSONB thread storage in tool_sessions.
- Data written to tool_session_messages can be discarded (no backfill performed).
