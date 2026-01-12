---
type: story
id: ST-08-26
title: "AI: chat/chat-ops provider routing + OpenAI failover (opt-in)"
status: done
owners: "agents"
created: 2026-01-11
updated: 2026-01-11
epic: "EPIC-08"
acceptance_criteria:
  - "Given chat is configured with a local llama.cpp primary and an OpenAI fallback, when a streaming chat request fails before the first streamed delta due to connect/timeout/HTTP 429/HTTP 5xx, then the backend retries once against the fallback provider and streams the response without switching mid-stream."
  - "Given the primary provider fails after at least one streamed delta, when streaming chat, then the backend does not attempt provider failover and completes the stream with `reason=error`."
  - "Given edit ops (chat-ops) is configured with a primary and fallback provider, when a chat-ops request fails due to connect/timeout/HTTP 429/HTTP 5xx, then the backend retries once against the fallback provider."
  - "Given OpenAI fallback is required, when `allow_remote_fallback=false` (default), then the backend does not send prompts off-box and responds with a user-actionable error (and the SPA can prompt for opt-in)."
  - "Given a thread `{user_id, tool_id}` has switched to fallback, when subsequent chat/chat-ops requests happen within 10 minutes since last activity, then the backend keeps routing that thread to the fallback provider to avoid frequent switching."
  - "Given the primary provider is failing repeatedly, when the circuit breaker is open, then new requests do not pay repeated slow timeouts and are routed directly to the healthy provider (subject to the privacy opt-in)."
ui_impact: "Yes (chat drawer opt-in prompt + plumbing)."
data_impact: "No"
dependencies:
  - "ST-08-23"
  - "ST-08-25"
---

## Context

We currently support OpenAI-compatible `/v1/chat/completions` providers via `LLM_CHAT_*` and `LLM_CHAT_OPS_*`.
This works for a single configured provider (local llama.cpp or OpenAI) but does not provide automatic failover
when the local model is unavailable or overloaded.

We want a tiered model setup:

- Inline completions use a cheap model (`gpt-5-nano`, `reasoning_effort=minimal`) when configured to use OpenAI.
- Chat and chat-ops use `gpt-5.2` with `reasoning_effort=low` when configured to use OpenAI.

Failover is limited to **chat + chat-ops** first (streaming UX + reliability), and must include a privacy guard:
falling back to OpenAI sends prompts/code off-box and requires explicit opt-in.

## Notes / constraints

- Failover triggers must be conservative for streaming: only retry when we have not emitted any deltas yet.
- Avoid mid-response provider switching.
- Add a per-process circuit breaker per provider to avoid repeated slow timeouts when a provider is down.
- Add a short TTL “sticky” provider decision per `{user_id, tool_id}` to reduce switching within the same thread.
- Use OpenAI as a load-shedding option when local inference concurrency is too high (opt-in).
