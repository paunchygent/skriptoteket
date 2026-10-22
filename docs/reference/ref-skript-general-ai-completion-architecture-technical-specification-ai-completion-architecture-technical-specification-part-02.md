---
type: reference
id: REF-SKRIPT-GENERAL-ai-completion-architecture-technical-specification-PART-02
title: AI Completion Architecture Technical Specification — part 02
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: '2026-07-31'
root: REF-SKRIPT-GENERAL-ai-completion-architecture-technical-specification
part: 2
---

### 7.1 Extension Composition

```typescript
skriptoteketIntelligence(config)
├─ skriptoteketCompletions (existing)
├─ skriptoteketHover (existing)
├─ skriptoteketLinter (existing)
├─ skriptoteketLintPanel (existing)
└─ skriptoteketGhostText
```

### 7.2 Ghost Text State

```typescript
type GhostTextState = {
  text: string | null;     // Suggested completion
  from: number | null;     // Cursor position when suggested
  replaceSuffixChars: number;
  decorations: DecorationSet;
};
```

### 7.3 Triggers

| Trigger               | Behavior                         |
| --------------------- | -------------------------------- |
| Typing pause (1500ms) | Auto-fetch completion if enabled |
| Alt+\\                | Manual fetch completion          |
| Tab                   | Accept ghost text                |
| Escape                | Dismiss ghost text               |
| Any document change   | Clear ghost text                 |

### 7.4 Request Management

- Cancel pending requests on document change
- Ignore stale responses (cursor moved since request)
- Debounce auto-trigger to reduce API load
- A 429 `AI_DAILY_LIMIT_REACHED` answer marks the shared AI limit state; no further requests start until it clears, and
  the note shows inline in the AI area
- A 429 `AI_TRY_AGAIN` answer shows the try-again note inline for chat and edit and leaves the controls enabled;
  inline completion shows nothing and tries again on the next request

______________________________________________________________________

### Source: 8. Configuration

### 8.1 Backend (Environment Variables)

Door connection (shared with the exam apps):

| Variable                        | Default                                    | Description                                |
| ------------------------------- | ------------------------------------------ | ------------------------------------------ |
| `HULEEDU_LLM_PROVIDER_BASE_URL` | `http://huleedu_llm_provider_service:8080` | Door base URL on the shared `hule-network` |
| `HULEEDU_INTERNAL_API_KEY`      | `""`                                       | Internal key sent as `X-Internal-API-Key`  |

Prompt templates:

- `LLM_COMPLETION_TEMPLATE_ID` (default: `inline_completion_gpt5_v1`)
- `LLM_CHAT_TEMPLATE_ID` (default: `editor_chat_v1`)
- `LLM_CHAT_OPS_TEMPLATE_ID` (default: `editor_chat_ops_v1`)

Notes:

- Templates are repo-owned text files with placeholders like `{{CONTRACT_V2_FRAGMENT}}`.
- Placeholders are replaced with code-owned fragments sourced from canonical Contract v2 + policy definitions.
- There are no per-profile base URL, API key, temperature, stop, prompt-cache or extra-header settings. The door
  owns the key and caching; neither model accepts temperature.

Inline completions (small-model pool):

| Variable                                      | Default                     | Description                                            |
| --------------------------------------------- | --------------------------- | ------------------------------------------------------ |
| `LLM_COMPLETION_ENABLED`                      | `false`                     | Enable/disable feature                                 |
| `LLM_COMPLETION_TEMPLATE_ID`                  | `inline_completion_gpt5_v1` | Prompt template ID for system prompt composition       |
| `LLM_COMPLETION_MODEL`                        | `gpt-6-luna`                | Door model id                                          |
| `LLM_COMPLETION_REASONING_EFFORT`             | `none`                      | Responses `reasoning.effort`                           |
| `LLM_COMPLETION_TEXT_VERBOSITY`               | `low`                       | Responses `text.verbosity`                             |
| `LLM_COMPLETION_MAX_TOKENS`                   | `64`                        | `max_output_tokens`                                    |
| `LLM_COMPLETION_TIMEOUT_SECONDS`              | `30`                        | Door call timeout                                      |
| `LLM_COMPLETION_CONTEXT_WINDOW_TOKENS`        | `4096`                      | Budgeting window (prompt + output)                     |
| `LLM_COMPLETION_CONTEXT_SAFETY_MARGIN_TOKENS` | `256`                       | Reserved prompt budget for variance                    |
| `LLM_COMPLETION_SYSTEM_PROMPT_MAX_TOKENS`     | `2048`                      | Target max tokens for system prompt (rules + KB)       |
| `LLM_COMPLETION_PREFIX_MAX_TOKENS`            | `2048`                      | Target max tokens for prefix (keeps tail near cursor)  |
| `LLM_COMPLETION_SUFFIX_MAX_TOKENS`            | `512`                       | Target max tokens for suffix (keeps head after cursor) |

Chat (streaming, full-model pool):

| Variable                                | Default          | Description                                      |
| --------------------------------------- | ---------------- | ------------------------------------------------ |
| `LLM_CHAT_ENABLED`                      | `false`          | Enable/disable feature                           |
| `LLM_CHAT_TEMPLATE_ID`                  | `editor_chat_v1` | Prompt template ID for system prompt composition |
| `LLM_CHAT_MODEL`                        | `gpt-6.1-sol`    | Door model id                                    |
| `LLM_CHAT_REASONING_EFFORT`             | `low`            | Responses `reasoning.effort`                     |
| `LLM_CHAT_TEXT_VERBOSITY`               | unset            | Responses `text.verbosity` (omitted when unset)  |
| `LLM_CHAT_MAX_TOKENS`                   | `8192`           | `max_output_tokens`                              |
| `LLM_CHAT_TIMEOUT_SECONDS`              | `120`            | Door call timeout                                |
| `LLM_CHAT_CONTEXT_WINDOW_TOKENS`        | `65536`          | Budgeting window (prompt + output)               |
| `LLM_CHAT_CONTEXT_SAFETY_MARGIN_TOKENS` | `256`            | Reserved prompt budget for variance              |
| `LLM_CHAT_SYSTEM_PROMPT_MAX_TOKENS`     | `8192`           | Target max tokens for system prompt (rules + KB) |
| `LLM_CHAT_TAIL_MAX_MESSAGES`            | `60`             | Most recent thread messages considered           |

Chat edit-ops (non-streaming, full-model pool):

| Variable                                    | Default              | Description                                                         |
| ------------------------------------------- | -------------------- | ------------------------------------------------------------------- |
| `LLM_CHAT_OPS_ENABLED`                      | `false`              | Enable/disable feature                                              |
| `LLM_CHAT_OPS_TEMPLATE_ID`                  | `editor_chat_ops_v1` | Prompt template ID for system prompt composition                    |
| `LLM_CHAT_OPS_MODEL`                        | `gpt-6.1-sol`        | Door model id                                                       |
| `LLM_CHAT_OPS_REASONING_EFFORT`             | `low`                | Responses `reasoning.effort`                                        |
| `LLM_CHAT_OPS_TEXT_VERBOSITY`               | unset                | Responses `text.verbosity` (omitted when unset)                     |
| `LLM_CHAT_OPS_MAX_TOKENS`                   | `8192`               | `max_output_tokens`                                                 |
| `LLM_CHAT_OPS_TIMEOUT_SECONDS`              | `120`                | Door call timeout                                                   |
| `LLM_CHAT_OPS_CONTEXT_WINDOW_TOKENS`        | `65536`              | Budgeting window (prompt + output)                                  |
| `LLM_CHAT_OPS_CONTEXT_SAFETY_MARGIN_TOKENS` | `256`                | Reserved prompt budget for variance                                 |
| `LLM_CHAT_OPS_SYSTEM_PROMPT_MAX_TOKENS`     | `8192`               | Target max tokens for system prompt (rules, strict JSON schema, KB) |

Platform debug capture (off by default; written under `ARTIFACTS_ROOT`, may contain tool code and model output):

| Variable                         | Default | Description                                                                                  |
| -------------------------------- | ------- | -------------------------------------------------------------------------------------------- |
| `LLM_CAPTURE_ON_ERROR_ENABLED`   | `false` | Capture failed chat-ops responses                                                            |
| `LLM_CAPTURE_ON_SUCCESS_ENABLED` | `false` | Dev-only: capture successful completion and chat-ops responses for admins outside production |

### 8.2 Frontend (Intelligence Config)

```typescript
type SkriptoteketIntelligenceConfig = {
  entrypointName: string;
  ghostText?: {
    enabled: boolean;       // Enable ghost text
    autoTrigger: boolean;   // Auto-trigger on typing pause
    debounceMs: number;     // Debounce delay (default: 1500)
  };
};
```

______________________________________________________________________

### Source: 9. Security Considerations

### 9.1 Credential Protection

- Skriptoteket holds one door credential, `HULEEDU_INTERNAL_API_KEY`, as a backend environment variable; provider
  keys live with the door
- Never exposed to frontend
- Backend proxies all LLM requests and sends the teacher's user id so the door meters per user

### 9.2 Authentication

- Completions, chat (`POST`) and edit-ops (`POST /edit-ops`) require `require_app_ai_api` (admin or superuser; a
  temporary gate until the AI spend limits ship, TASK-SKRIPT-REP-0044)
- Chat history read/clear, edit-ops preview and apply require contributor access to the tool
- CSRF token required for all POST requests

### 9.3 Rate Limiting

- The door meters the daily pools, per-user shares and the USD ceiling; Skriptoteket adds no request-rate limit of its
  own
- A refusal reaches the teacher as HTTP 429 `AI_DAILY_LIMIT_REACHED` (section 6.3)
- A busy door, or this process's door slots full, reaches the teacher as HTTP 429 `AI_TRY_AGAIN` (S6)
- Chat allows one in-flight turn per `{user_id, tool_id}` in each process (`InProcessChatInFlightGuard`)

### 9.4 Privacy & Logging

- Do not log raw prefix/suffix/prompt/code
- Log only metadata (lengths, token counts, model, timing, status)
- The door relays teacher code to OpenAI; no per-user consent setting exists

______________________________________________________________________

### Source: 10. Files

### 10.1 Backend

| Path                                                                       | Purpose                                                                                   |
| -------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------- |
| `src/skriptoteket/protocols/llm/`                                          | Editor AI protocols (providers take an `AiDoorCaller`), `EditorLlmProviderError`          |
| `src/skriptoteket/protocols/llm_door.py`                                   | Door client protocol, `DoorOperation`, `DoorReply`, `DoorStream`                          |
| `src/skriptoteket/domain/llm_door.py`                                      | `AiDoorCaller`, `door_caller_for`, `AiDailyLimit`, `AiDailyLimitReached`, `ai_limit_note` |
| `src/skriptoteket/infrastructure/llm/door/client.py`                       | Door HTTP client (`send`, `stream`)                                                       |
| `src/skriptoteket/infrastructure/llm/openai/inline_completion_provider.py` | Completion provider (Responses body, parse)                                               |
| `src/skriptoteket/infrastructure/llm/openai/inline_completion_prompt.py`   | Delimited prefix/suffix user prompt                                                       |
| `src/skriptoteket/infrastructure/llm/openai/chat_stream_provider.py`       | Chat SSE provider                                                                         |
| `src/skriptoteket/infrastructure/llm/openai/chat_ops_provider.py`          | Chat-ops provider                                                                         |
| `src/skriptoteket/infrastructure/llm/openai/edit_ops_text_format.py`       | Patch-only JSON schema for chat ops                                                       |
| `src/skriptoteket/infrastructure/llm/openai/payloads.py`                   | Responses body builder                                                                    |
| `src/skriptoteket/infrastructure/llm/openai/door_replies.py`               | Door answer to `EditorLlmProviderError` mapping                                           |
| `src/skriptoteket/infrastructure/llm/openai/parsing.py`                    | Responses output and stream-delta parsing                                                 |
| `src/skriptoteket/infrastructure/llm/token_counter_resolver.py`            | `tiktoken` token counters                                                                 |
| `src/skriptoteket/application/editor/completion_handler.py`                | Handler entrypoint (completion orchestration)                                             |
| `src/skriptoteket/application/editor/completion/`                          | Completion flow submodules (attempts/normalization/capture/telemetry)                     |
| `src/skriptoteket/application/editor/chat_stream_orchestrator.py`          | Chat stream orchestration and limit refusal                                               |
| `src/skriptoteket/application/editor/edit_ops/`                            | Edit-ops flow, execution, preview and apply                                               |
| `src/skriptoteket/di/llm.py`                                               | DI provider                                                                               |
| `src/skriptoteket/config.py`                                               | Configuration settings                                                                    |
| `src/skriptoteket/application/editor/prompt_templates.py`                  | Prompt template registry (IDs + required placeholders)                                    |
| `src/skriptoteket/application/editor/prompt_fragments.py`                  | Code-owned fragments (Contract v2 + runner constraints + helpers)                         |
| `src/skriptoteket/application/editor/prompt_composer.py`                   | Template composition + validation (placeholders + budget)                                 |
| `src/skriptoteket/application/editor/prompt_budget.py`                     | Deterministic prompt budgeting                                                            |
| `src/skriptoteket/web/api/v1/editor/completions.py`                        | Inline completions API endpoint                                                           |
| `src/skriptoteket/web/api/v1/editor/chat.py`                               | Chat SSE API endpoint                                                                     |
| `src/skriptoteket/web/api/v1/editor/edit_ops.py`                           | Edit-ops API endpoints                                                                    |

### 10.2 Frontend

| Path                                                                                         | Purpose                           |
| -------------------------------------------------------------------------------------------- | --------------------------------- |
| `frontend/apps/skriptoteket/src/composables/editor/skriptoteketGhostText.ts`                 | Ghost text extension              |
| `frontend/apps/skriptoteket/src/composables/editor/skriptoteketIntelligence.ts`              | Bundle integration                |
| `frontend/apps/skriptoteket/src/composables/editor/useSkriptoteketIntelligenceExtensions.ts` | Config composable                 |
| `frontend/apps/skriptoteket/src/composables/aiDailyLimit.ts`                                 | Shared daily-limit state and note |

______________________________________________________________________

### Source: 11. Testing

### 11.1 Backend

- Unit: Providers send a Responses body with the configured model, reasoning effort and `max_output_tokens`, and no
  temperature or stop sequences
- Unit: Each provider passes the teacher's `AiDoorCaller` to the door
- Unit: System prompt template composes (placeholders resolved, within budget)
- Unit: Door timeout, transport failure, `context_length_exceeded` and other statuses map to the right
  `EditorLlmProviderError` kind
- Unit: A door daily limit becomes 429 `AI_DAILY_LIMIT_REACHED` with the matching note and `details.limit`; chat
  refuses before its first SSE event
- Unit: A busy door becomes 429 `AI_TRY_AGAIN` on all three paths; an open chat stream holds its door slot until it
  closes, and the editor providers share the door client's sized pool
- Integration: Endpoint requires auth + CSRF
- Integration: Returns `enabled=false` when disabled
- Integration: Truncated response returns empty completion

### 11.2 Frontend

- Unit: Ghost text displays at cursor position
- Unit: Multi-line ghost text preserves indentation/newlines
- Unit: Tab accepts, Escape dismisses
- Unit: Document change clears ghost text
- Unit: A 429 daily-limit answer shows the note inline and stops further requests
- E2E: Full flow with a stubbed door

______________________________________________________________________

### Source: 12. References

- [ADR-0043: AI completion integration](../decisions/adr-skript-0043-ai-assisted-inline-completions-for-script-editor.md)
- [ADR-0035: Script editor intelligence architecture](../decisions/adr-skript-0035-script-editor-intelligence-architecture-codemirror-6.md)
- [ADR-0051: Chat-first AI editing](../decisions/adr-skript-0051-chat-first-ai-editing-structured-crud-ops-diff-preview-apply-undo.md)
- [ADR-0052: LLM prompt budgeting and KB fragments](../decisions/adr-skript-0052-llm-prompt-budgeting-kb-fragments-for-ai-editor-features.md)
- [AI script generation knowledge base](ref-skript-general-ai-script-generation-knowledge-base-ai-script-generation-knowledge-base.md)
- [Editor AI pipeline runbook](../runbooks/run-skript-runbook-editor-ai-pipeline-completion-chat-edit-ops-runbook-editor-ai-pipeline-completion-chat-edit-ops.md)

## Decisions And Interpretation

- Every editor model call goes through HuleEdu's LLM provider door with the teacher's user id (TASK-SKRIPT-41-01-02,
  S1, S2). There is no second route.
- Inline completion runs on `gpt-6-luna` (small-model pool, S2); chat, chat ops and edit run on `gpt-6.1-sol` at low
  reasoning (full-model pool, S1, S4).
- A door daily limit is HTTP 429 `AI_DAILY_LIMIT_REACHED` with the teacher note inline, and no toast (S5).
- A busy door is HTTP 429 `AI_TRY_AGAIN` with the try-again note; editor streams share the door bounds (S6).
