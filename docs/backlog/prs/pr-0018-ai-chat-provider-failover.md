---
type: pr
id: PR-0018
title: "AI provider: chat/chat-ops routing + opt-in OpenAI failover"
status: done
owners: "agents"
created: 2026-01-11
updated: 2026-01-11
stories:
  - "ST-08-26"
tags: ["backend", "frontend", "ai", "reliability"]
acceptance_criteria:
  - "Chat streaming retries only before first delta and never switches mid-stream."
  - "Chat-ops retries once on eligible failures and returns a single coherent response."
  - "Fallback to OpenAI requires explicit opt-in and never leaks prompts off-box without it."
  - "Circuit breaker + sticky routing prevents repeated slow timeouts and reduces provider flapping."
  - "Backend + SPA tests cover routing + opt-in behavior, and live verification is recorded in `.agent/handoff.md`."
---

## Problem

Our chat + chat-ops providers are configured as a single OpenAI-compatible endpoint per profile. When local llama.cpp
is down or overloaded, users get timeouts or errors and the streaming UX suffers.

## Goal

- Add an in-process router for chat + chat-ops that can:
  - Prefer local llama.cpp (or configured primary)
  - Fail over to OpenAI (or configured fallback) on eligible failures
  - Load-shed to OpenAI when local concurrency is high
  - Avoid mid-response switching for streaming
  - Require explicit opt-in before sending prompts off-box

## Non-goals

- Automatic failover for inline completions (`LLM_COMPLETION_*`) in this PR.
- Persisting “allow remote fallback” to the database (client-side opt-in only for now).
- Cross-process circuit breaking (this is per-process MVP).

## Implementation plan

1. Backend: add routing settings for `LLM_CHAT_*` + `LLM_CHAT_OPS_*` (primary + fallback provider config).
2. Backend: implement in-process circuit breaker + sticky routing per `{user_id, tool_id}`.
3. Backend: wire routing into editor chat streaming + edit ops (chat-ops), including privacy opt-in enforcement.
4. Frontend: add a user-facing opt-in toggle/prompt and send `allow_remote_fallback` on chat + edit-ops requests.
5. Tests: add unit tests for router behavior + a focused streaming failover case.

## Test plan

- `pdm run pytest tests/unit -q`
- `pdm run fe-test`
- `pdm run fe-gen-api-types`
- Live check: `pdm run dev-local` (record manual verification in `.agent/handoff.md`)

### Live OpenAI verification (manual; no secrets)

1. Configure granular API keys (per LLM profile) in `.env`:
   - `OPENAI_LLM_COMPLETION_API_KEY` (completions)
   - `OPENAI_LLM_CHAT_API_KEY` (chat)
   - `OPENAI_LLM_CHAT_OPS_API_KEY` (chat-ops)
2. Developer containers default to OpenAI base URLs + models (see `compose.yaml`).
3. Verify GPT‑5 payload compatibility:
   - Set `LLM_CHAT_MODEL=gpt-5.2`, `LLM_CHAT_REASONING_EFFORT=low`
   - Set `LLM_CHAT_OPS_MODEL=gpt-5.2`, `LLM_CHAT_OPS_REASONING_EFFORT=low`
   - Set `LLM_COMPLETION_MODEL=gpt-5-nano`, `LLM_COMPLETION_REASONING_EFFORT=minimal`
   - Exercise the editor chat + edit-ops flows; requests should succeed without “unsupported parameter”
     errors (GPT‑5 family should not receive `temperature`/`max_tokens`).
4. Verify failover + UX (pre-first-delta only):
   - Configure a local primary + OpenAI fallback (`LLM_CHAT_FALLBACK_*`, `LLM_CHAT_OPS_FALLBACK_*`), then
     force a primary failure (e.g., stop llama.cpp or point the primary base URL to an unreachable address).
   - In the editor chat drawer, enable the “Tillåt fjärr‑AI (OpenAI)” toggle and send a message.
   - Expect a notice event + response from the fallback provider; no mid-stream switching.

## Rollback plan

- Revert the PR; the new config keys are additive and default to “no failover”.
