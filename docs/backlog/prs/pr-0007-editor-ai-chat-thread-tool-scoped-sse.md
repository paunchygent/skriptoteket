---
type: pr
id: PR-0007
title: "AI editor: tool-scoped SSE chat + server-side thread (ST-08-23)"
status: done
owners: "agents"
created: 2026-01-07
updated: 2026-01-07
stories:
  - "ST-08-23"
adrs:
  - "ADR-0051"
  - "ADR-0052"
tags: ["backend", "editor", "ai", "sse"]
acceptance_criteria:
  - "Chat text endpoint is tool-scoped and message-only: POST /api/v1/editor/tools/{tool_id}/chat with body {message}."
  - "Canonical chat thread is persisted server-side per {user_id, tool_id} with 30-day TTL since updated_at."
  - "Provider context uses sliding window (drop oldest turns first) and never truncates the system prompt."
  - "If newest user message cannot fit with full system prompt + reserved output budget, return 422 with Swedish copy and do not mutate stored history."
  - "Clear endpoint exists: DELETE /api/v1/editor/tools/{tool_id}/chat clears the per-user thread for that tool."
  - "Logging is metadata-only (no prompts/code/messages/model output text)."
  - "Unit tests cover persistence semantics (A): persist user message immediately; persist assistant message only on successful completion."
---

## Problem

The current chat streaming backend is stateless and accepts client-managed message arrays. This conflicts with the
chat-first UX goal (multi-turn assistant memory) and leads to drift across chat-first endpoints (text now, edit-ops
later).

## Goal

Make the backend the canonical source of truth for chat history so all editor AI chat-first flows share the same thread
semantics and budgeting behavior.

## Non-goals

- No frontend/UI changes (ST-08-20 is out of scope for this PR).
- No edit-ops protocol implementation (ST-08-21/22 are out of scope for this PR).
- No database migrations: reuse existing `tool_sessions` state storage.

## Implementation plan

1) **API contract + routing**

   - Replace the legacy endpoint with:
     - `POST /api/v1/editor/tools/{tool_id}/chat` (SSE), body `{ "message": "..." }`
     - `DELETE /api/v1/editor/tools/{tool_id}/chat` (clear thread)
   - Keep the SSE event format stable: `meta` → `delta`* → `done`.
   - Ensure validation errors (e.g. message too long) return HTTP 422 as normal JSON (not SSE).

2) **Authorization**

   - Require contributor auth + CSRF (same as other editor endpoints).
   - Enforce tool access using existing maintainer/admin checks (mirror editor boot).

3) **Thread persistence**

   - Store chat thread in `tool_sessions` under context `editor_chat`, keyed by `{tool_id, user_id, context}`.
   - TTL policy: if `updated_at` is older than 30 days, treat the thread as empty.
   - Persistence semantics (A):
     - Persist the newest user message immediately (before streaming starts).
     - Persist the assistant message only on successful completion.

4) **Budgeting (ADR-0052 alignment)**

   - Never truncate the system prompt.
   - When calling the provider, use a sliding window: drop oldest turns first until prompt fits.
   - If the newest user message cannot fit with the full system prompt + reserved output budget:
     - return HTTP 422 with `För långt meddelande: korta ned eller starta en ny chatt.`
     - do not mutate stored history.

5) **Provider compatibility**

   - Continue to use OpenAI-compatible HTTP `/v1/chat/completions`.
   - Add llama-server optimization: include `cache_prompt: true` only when `LLM_CHAT_BASE_URL` is local `:8082`.

6) **Unit tests**

   - Mock protocols (provider/uow/session repo/clock/id generator).
   - Cover:
     - disabled/misconfigured (done disabled; no provider call)
     - happy path (meta/delta/done; persistence A)
     - timeout/error (done error; only user message persisted)
     - TTL expiry (old history ignored)
     - over-budget newest message (422; no mutation)

## Test plan

- `pdm run pytest tests/unit/application/test_editor_chat_handler.py -q`
- `pdm run pytest tests/unit/application -q`
- Manual SSE smoke (required for route changes):
  - `pdm run dev`
  - Authenticated `curl -N` to `POST /api/v1/editor/tools/{tool_id}/chat`
  - `DELETE /api/v1/editor/tools/{tool_id}/chat`
  - Record verification in `.agent/handoff.md`.

## Rollback plan

- Revert the PR. No migrations are introduced and chat state is stored in existing `tool_sessions` rows; reverting only
  leaves unused session context data.
