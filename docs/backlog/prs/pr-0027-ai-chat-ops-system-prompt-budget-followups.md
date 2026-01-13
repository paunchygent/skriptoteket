---
type: pr
id: PR-0027
title: "AI: chat-ops system prompt budget + follow-ups"
status: ready
owners: "agents"
created: 2026-01-13
updated: 2026-01-13
stories:
  - "ST-08-21"
  - "ST-08-23"
  - "ST-08-27"
tags: ["backend", "frontend", "ai"]
acceptance_criteria:
  - "Edit-ops (Föreslå ändringar) no longer returns enabled=false due to chat-ops system prompt budget validation."
  - "LLM_CHAT_OPS_SYSTEM_PROMPT_MAX_TOKENS is high enough for editor_chat_ops_v1 under conservative token counting."
  - "A regression test composes chat/chat-ops prompts using the real TokenCounterResolver (not FakeTokenCounter)."
  - "Config naming clarifies turn-based history usage (tail max turns vs messages)."
  - "Concurrent turn creation failures return a clear 409 instead of leaking IntegrityError."
---

## Problem

We have a user-visible regression in the script editor:

- **Chat (Skicka)** works and the assistant can see virtual files as expected.
- **Edit-ops (Föreslå ändringar)** returns `enabled=false` with the toast:
  `AI-redigering är inte tillgänglig just nu. Försök igen senare.`

Root cause: `editor_chat_ops_v1` fails system prompt composition because it exceeds
`LLM_CHAT_OPS_SYSTEM_PROMPT_MAX_TOKENS` under tokenizer-backed budgeting (or conservative fallback).

Observed locally with the current `SettingsBasedTokenCounterResolver`:

- `editor_chat_v1`: **1921 / 2048** tokens ✅
- `editor_chat_ops_v1`: **2635 / 2048** tokens ❌ → `PromptTemplateError` → edit-ops disabled

This is currently hard to diagnose in production because the handler logs `ai_chat_ops_system_prompt_unavailable`
without the exception message/token counts.

## Goal

- Make edit-ops available again by aligning **system prompt budgets** with the actual prompt size under token counting.
- Add **regression coverage** so we never ship a prompt that fails composition in real runtime settings.
- Improve **diagnostics** so operators can tell “feature disabled” vs “prompt over budget” vs “provider unreachable”.

## Non-goals

- Redesigning the edit-ops schema or diff/preview/apply flow.
- Changing provider routing/failover semantics.

## Implementation plan

1. **Fix budget**
   - Increase `LLM_CHAT_OPS_SYSTEM_PROMPT_MAX_TOKENS` default (recommend 4096), and document the env override.
   - Consider also raising `LLM_CHAT_SYSTEM_PROMPT_MAX_TOKENS` only if we later grow `editor_chat_v1`.

2. **Add runtime diagnostics**
   - When catching `PromptTemplateError` in `EditOpsHandler`, include `error=str(exc)` in the `ai_chat_ops_system_prompt_unavailable` log event.
   - Add a `failure_outcome` value like `system_prompt_over_budget` when we disable due to prompt composition errors.

3. **Add regression tests with real token counters**
   - Add a unit test that composes `editor_chat_v1` and `editor_chat_ops_v1` using `SettingsBasedTokenCounterResolver`
     (devstral model + heuristic fallback) and asserts they compose under the configured budgets.
   - Keep the existing FakeTokenCounter tests for placeholder resolution, but ensure we also cover real budgeting.

4. **Follow-up hardening**
   - Rename `LLM_CHAT_TAIL_MAX_MESSAGES` to `LLM_CHAT_TAIL_MAX_TURNS` (and update code + docs accordingly).
   - Ensure concurrent pending-turn creation surfaces as `409` with a stable error code/message.

## Test plan

- Backend:
  - Unit: new system prompt composition budget test using real token counters.
  - Existing: `pdm run test` (includes integration + migrations coverage).
- Frontend:
  - `pdm run fe-test` (edit-ops still displays disabled state if backend returns enabled=false; expected).

## Rollback plan

- Revert the budget increase and diagnostic logging changes (expect edit-ops to fall back to disabled again if prompt still exceeds budget).

## References

- Epic: `docs/backlog/epics/epic-08-contextual-help-and-onboarding.md`
- Stories:
  - `docs/backlog/stories/story-08-21-ai-structured-crud-edit-ops-protocol-v1.md`
  - `docs/backlog/stories/story-08-23-ai-chat-streaming-proxy-and-config.md`
  - `docs/backlog/stories/story-08-27-editor-chat-virtual-file-context-retention-and-tokenizers.md`
- Implementation PR docs:
  - `docs/backlog/prs/pr-0013-editor-ai-edit-ops-protocol-v1.md`
  - `docs/backlog/prs/pr-0007-editor-ai-chat-thread-tool-scoped-sse.md`
  - `docs/backlog/prs/pr-0008-editor-chat-message-storage-minimal-c.md`
  - `docs/backlog/prs/pr-0023-tokenizer-backed-prompt-budgeting.md`
  - `docs/backlog/prs/pr-0021-ai-chat-ops-response-capture-on-error.md`
