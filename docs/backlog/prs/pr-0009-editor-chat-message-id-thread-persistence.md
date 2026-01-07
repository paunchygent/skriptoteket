---
type: pr
id: PR-0009
title: "Editor chat: message_id thread persistence + conflict retry + best-effort single-flight"
status: done
owners: "agents"
created: 2026-01-07
updated: 2026-01-07
stories:
  - "ST-08-23"
tags: ["backend", "editor", "ai", "concurrency"]
acceptance_criteria:
  - "Chat messages persisted in tool_sessions.state include message_id/in_reply_to JSON fields for correlation."
  - "On tool_sessions state_rev conflict during user message persist, handler retries and merges latest thread before continuing."
  - "Assistant message is inserted after its matching user message_id (not required to be last)."
  - "Best-effort in-process single-flight guard returns 409 with Swedish message when a concurrent request is already in flight."
  - "No database migrations are introduced."
---

## Problem

Chat messages stored in tool_sessions.state are vulnerable to optimistic concurrency conflicts and ambiguous assistant
persistence when identical user messages arrive concurrently.

## Goal

Make JSONB-based chat thread persistence concurrency-safe without migrations, by correlating messages using message_id
and inserting assistant responses after the matching user message. Add a best-effort, per-process single-flight guard
for UX/load shedding (not correctness).

## Non-goals

- Normalize chat storage (see PR-0008).
- Hold DB transactions across streaming.
- Change the frontend UI or SSE wire format.
- Rely on the single-flight guard for correctness in multi-worker deployments.

## Implementation plan

1) **Message identity**
   - Add `message_id` and `in_reply_to` fields to persisted chat messages.
   - Serialize to JSON-safe values (UUID as string).

2) **Conflict retry**
   - On `state_rev` conflict while persisting the user message, retry with a fresh read and merged thread.

3) **Assistant insertion**
   - Persist assistant output by inserting after the matching user `message_id`, not “must be last”.

4) **Best-effort guard**
   - Add a per-process in-flight guard that returns 409 with Swedish copy if a request is already streaming for the same
     `{user_id, tool_id}`.

5) **Tests**
   - Update handler unit tests to include message_id/in_reply_to.
   - Add concurrency tests for conflict retry and assistant insertion order.

## Test plan

- `pdm run pytest tests/unit/application/test_editor_chat_handler.py -q`
- `pdm run pytest tests/unit/application -q`

## Rollback plan

- Revert this PR; JSONB message fields are optional and ignored by older code.
