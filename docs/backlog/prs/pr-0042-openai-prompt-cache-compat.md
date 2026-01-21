---
type: pr
id: PR-0042
title: "AI: model capability gating + OpenAI prompt caching alignment"
status: done
owners: "agents"
created: 2026-01-18
updated: 2026-01-21
stories:
  - "ST-08-14"
tags: ["backend", "ai", "cost"]
acceptance_criteria:
  - "Given `LLM_COMPLETION_MODEL=gpt-5-nano`, inline completion requests omit unsupported fields (`stop`, `prompt_cache_retention`) and return 200 from OpenAI."
  - "Given an OpenAI model that supports extended prompt caching (gpt-5, gpt-5.1, gpt-5.1-codex-mini, gpt-5.2, gpt-4.1), requests include `prompt_cache_retention=24h` and `prompt_cache_key` only when cost parity with in-memory caching is explicitly enabled in configuration."
  - "Given a local llama-server base URL, request payloads remain compatible (no GPT-5-only params, no remote-only cache params)."
  - "Extended prompt cache retention remains off unless `LLM_PROMPT_CACHE_RETENTION_MODE=24h` (default `in_memory`), even though `LLM_PROMPT_CACHE_EXTENDED_ALLOWED=true` by default."
  - "When `LLM_PROMPT_CACHE_RETENTION_MODE=24h` and `LLM_PROMPT_CACHE_EXTENDED_ALLOWED=false`, the logs explain that `prompt_cache_retention` was suppressed."
---

## Problem

Inline completions fail with OpenAI `gpt-5-nano` because the current payload always includes
`stop` and `prompt_cache_retention`, which the model rejects. This blocks completions and
prevents us from benefitting from OpenAI prompt caching, which is a significant cost lever
across inline completions, chat, and chat-ops.

## Goal

- Add model capability checks so `stop` and `prompt_cache_retention` are only sent when supported.
- Preserve prompt caching benefits by continuing to send `prompt_cache_key` (and retention where
  allowed) for OpenAI-backed requests.
- Keep the implementation aligned with the LLM provider boundary (no domain/web-layer logic).

## Non-goals

- Rewriting prompts or changing prompt structure.
- Migrating endpoints to the Responses API.
- Changing UI behavior or editor UX.
- Observability/dashboard work (deferred to a follow-up PR doc).

## Implementation plan

1. Add a small model-capability helper in `src/skriptoteket/infrastructure/llm/` (or extend
   `model_families.py`) covering:
   - `supports_stop_sequences(model)` (false for `gpt-5-nano` based on observed API behavior).
   - `supports_prompt_cache_retention(model)` (true only for models that support extended
     retention; otherwise omit `prompt_cache_retention`).
2. Update `build_chat_payload` to consult these capabilities before attaching `stop` and
   `prompt_cache_retention`.
3. Keep `prompt_cache_key` enabled for OpenAI requests (for better cache hit rates), but avoid
   sending retention settings to unsupported models.
4. Introduce a config guard for extended retention:
   - `LLM_PROMPT_CACHE_RETENTION_MODE=in_memory|24h` (default: `in_memory`)
   - `LLM_PROMPT_CACHE_EXTENDED_ALLOWED=true|false` (default: `true`)
   The code only sends `prompt_cache_retention=24h`
   when the guard is enabled and cost parity is explicitly confirmed in config.
5. Apply the same payload gating across inline completions, chat streaming, and chat-ops.
6. Add a log line when `LLM_PROMPT_CACHE_RETENTION_MODE=24h` but
   `LLM_PROMPT_CACHE_EXTENDED_ALLOWED=false` to explain suppression.
7. Add unit tests for payload construction:
   - `gpt-5-nano` excludes `stop` + `prompt_cache_retention`.
   - `gpt-5` / `gpt-5.1` / `gpt-5.1-codex-mini` / `gpt-5.2` include `prompt_cache_retention=24h`
     when configured.
   - Local llama-server paths remain unchanged.

## Test plan

- Unit tests for payload construction (new cases around capability gating).
- Manual: run `/api/v1/editor/completions` with `LLM_COMPLETION_MODEL=gpt-5-nano`; confirm 200
  responses from OpenAI and no inline completion 400s in logs.
- Manual: send a >=1024-token prompt with OpenAI models that support caching and confirm
  `usage.prompt_tokens_details.cached_tokens` is present in the response.

## Rollback plan

- Revert the capability gating and switch `LLM_COMPLETION_MODEL` to a local model until the
  upstream compatibility is resolved.
