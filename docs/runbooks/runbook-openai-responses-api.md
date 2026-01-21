---
type: runbook
id: RUN-openai-responses-api
title: "Runbook: OpenAI Responses API + Prompt Caching"
status: active
owners: "agents"
created: 2026-01-18
updated: 2026-01-21
system: "skriptoteket"
---

Authoritative guidance for OpenAI usage in Skriptoteket. This runbook is the source of truth
for parameters, caching behavior, and best practices. Do not rely on training data for OpenAI
changes; always verify against the linked docs.

## Scope

- Responses API usage and parameters
- Prompt caching behavior, retention, and routing
- Reasoning model best practices
- Required references for model capabilities

## Source of Truth (Required Reading)

- Prompt caching guide: https://platform.openai.com/docs/guides/prompt-caching
- Responses API reference: https://platform.openai.com/docs/api-reference/responses
- Chat Completions reference: https://platform.openai.com/docs/api-reference/chat
- Responses vs Chat Completions: https://platform.openai.com/docs/guides/responses-vs-chat-completions
- Reasoning best practices: https://platform.openai.com/docs/guides/reasoning-best-practices
- Cookbook: GPT-5 new params and tools:
  https://cookbook.openai.com/examples/gpt-5/gpt-5_new_params_and_tools
- Cookbook: Responses API index:
  https://cookbook.openai.com/examples/responses_api/
- Cookbook: Responses API reasoning items + caching:
  https://cookbook.openai.com/examples/responses_api/reasoning_items/
- Cookbook: Prompt Caching 101:
  https://cookbook.openai.com/examples/prompt_caching101/

## Responses API vs Chat Completions

- Chat Completions is stateless; reasoning items are not included in context.
- Responses API supports reasoning item persistence (via `previous_response_id` or explicit
  input items) and is recommended for complex tool usage and caching efficiency.
- For reasoning models, include prior reasoning items or use `previous_response_id`; irrelevant
  reasoning items are ignored by the API.

## GPT-5 New Params and Tools (Cookbook)

- Verbosity control via `text.verbosity` (low/medium/high). Use the parameter instead of
  rewriting prompts to control detail level.
- Free-form function calling: send raw text payloads to custom tools when JSON isn't required.
- Context-free grammar (CFG): constrain outputs with grammar rules for strict formats.
- Minimal reasoning: set reasoning effort to `minimal` for low-latency, deterministic tasks.
- Supported models: `gpt-5`, `gpt-5-mini`, `gpt-5-nano`.
- Supported endpoints: Responses API and Chat Completions.
- Recommendation: prefer Responses API for GPT-5 for best performance.

## Responses API Caching Notes (Cookbook)

- Caching only impacts prompts longer than 1024 tokens.
- The cookbook reports higher cache utilization when moving from Chat Completions to Responses API
  for reasoning workflows.
- Prior-turn reasoning items are ignored if not relevant; including them is safe but may reduce
  full cache hits when they are omitted.

## Prompt Caching: What Can Be Cached

Prompt caching works on prompt prefixes. Cache hits require exact prefix matches.

- Static text (instructions/examples) should appear first.
- Variable content should appear last.
- Images and tools must be identical and in the same order between requests to be cacheable.
- Structured output schemas are part of the prompt prefix and should be stable for caching.
- Image `detail` parameters must match between requests.
- Tool lists contribute to the 1024-token minimum for cache eligibility.

Caching is enabled automatically for prompts of 1024 tokens or more. All requests still return
`cached_tokens` in `usage.prompt_tokens_details`; for prompts under 1024 tokens this will be zero.

## Prompt Cache Routing

- Requests are routed using a hash of the prompt prefix; `prompt_cache_key` is mixed into the
  hash to increase cache hit rates for shared prefixes.
- High request bursts with the same prefix may be distributed to multiple machines, which can
  reduce cache effectiveness.
- Keep each prefix + `prompt_cache_key` combination below ~15 requests/minute to avoid cache
  overflow to other machines.

## Retention Policies

- Default retention is `in_memory` if `prompt_cache_retention` is omitted.
- `in_memory` keeps cached prefixes for 5-10 minutes of inactivity (up to ~1 hour).
- `24h` retention is available only for the models listed in the prompt caching guide.
- Pricing is the same for `in_memory` and `24h`.
  - Note: the prompt caching guide lists `gp5-5.1-codex-max` (verify model naming against the
    model cards before use).

## Model Cards and Parameters

Do not assume payload or supported parameters. Use the model card and API reference:

- Model cards: https://platform.openai.com/docs/models
- Responses API parameters: https://platform.openai.com/docs/api-reference/responses
- Chat Completions parameters: https://platform.openai.com/docs/api-reference/chat

## Structured Output: Chat Completions vs Responses

OpenAI has two similar-but-not-identical structured output mechanisms. Mixing the shapes will
cause hard 400s (common symptom: missing required parameter errors).

### Chat Completions (`/v1/chat/completions`)

- Use `response_format`.
- For JSON schema outputs, the shape is:

```json
{
  "response_format": {
    "type": "json_schema",
    "json_schema": {
      "name": "my_schema_name",
      "schema": {}
    }
  }
}
```

### Responses (`/v1/responses`)

- Use `text.format` (nested under `text`).
- For JSON schema outputs, the shape is:

```json
{
  "text": {
    "format": {
      "type": "json_schema",
      "name": "my_schema_name",
      "schema": {}
    }
  }
}
```

### Message content item types (Responses)

When sending `input` items to `/v1/responses`, each message `content[]` item has a `type`:

- `user` messages should use `{"type":"input_text","text":"..."}`
- `assistant` history should use `{"type":"output_text","text":"..."}`

If you send assistant history as `input_text`, OpenAI returns a 400 invalid request error.

### Implementation notes (Skriptoteket)

- Keep Chat Completions and Responses types separate in code to avoid accidental shape mixups.
- Normalize schema formats before sending to Responses:
  - `src/skriptoteket/infrastructure/llm/openai/payloads.py` (`_normalize_responses_text_format`)
  - `src/skriptoteket/infrastructure/llm/openai/types.py` (`JsonSchemaResponseFormat` vs
    `ResponsesTextFormat`)

## Operational Checklist

- Confirm model supports required params using model card + API reference.
- Ensure prompt prefix is stable and long enough (>= 1024 tokens) for caching.
- Use `prompt_cache_key` for shared prefixes to improve cache hits.
- Prefer Responses API for reasoning models and tool-heavy workflows.
- Log `usage.prompt_tokens_details.cached_tokens` to measure cache hit rate.
