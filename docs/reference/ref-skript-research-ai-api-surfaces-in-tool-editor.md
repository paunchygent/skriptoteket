---
type: reference
id: REF-SKRIPT-RESEARCH-ai-api-surfaces-in-tool-editor
title: AI API Surfaces in Tool Editor
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: '2026-07-31'
status: active
reference_kind: research
summary: 'Traces the four AI API surfaces in the tool editor: inline completions for ghost text, streaming chat for conversation, edit-ops for structured code editing, and the provider wiring that sends every call through the HuleEdu LLM provider door.'
links:
  references:
    - ADR-SKRIPT-0035
    - ADR-SKRIPT-0043
    - ADR-SKRIPT-0050
    - ADR-SKRIPT-0051
    - ADR-SKRIPT-0052
    - ADR-SKRIPT-0054
    - ADR-SKRIPT-0055
    - REF-SKRIPT-GENERAL-ai-completion-architecture-technical-specification
---

## Research Purpose And Boundary

### Source: Purpose

Traces the four AI API surfaces in the tool editor: inline completions for ghost text, streaming chat for conversation, edit-ops for structured code editing, and the provider wiring. Every call goes through the HuleEdu LLM provider door on the Responses route with the teacher's user id. There is no local model endpoint, no in-process failover and no remote-provider consent.

| Surface               | Model         | Reasoning effort |
| --------------------- | ------------- | ---------------- |
| Inline completion     | `gpt-6-luna`  | `none`           |
| Chat                  | `gpt-6.1-sol` | `low`            |
| Chat ops and edit-ops | `gpt-6.1-sol` | `low`            |

The models, efforts, token limits and timeouts are `LLM_COMPLETION_*`, `LLM_CHAT_*` and `LLM_CHAT_OPS_*` settings in `src/skriptoteket/config.py`. The door address and key are `HULEEDU_LLM_PROVIDER_BASE_URL` and `HULEEDU_INTERNAL_API_KEY`. Neither model accepts temperature.

## Evidence And Sources

### Source: Quick Index (Code + Docs)

### Inline Completions

- **API Endpoint**: `src/skriptoteket/web/api/v1/editor/completions.py`
- **Application Handler**: `src/skriptoteket/application/editor/completion_handler.py`
- **Infrastructure Provider**: `src/skriptoteket/infrastructure/llm/openai/inline_completion_provider.py`

### Streaming Chat

- **API Endpoint**: `src/skriptoteket/web/api/v1/editor/chat.py`
- **Application Handler**: `src/skriptoteket/application/editor/chat_handler.py`
- **Infrastructure Provider**: `src/skriptoteket/infrastructure/llm/openai/chat_stream_provider.py`

### Edit-Ops (Structured Editing)

- **API Endpoint**: `src/skriptoteket/web/api/v1/editor/edit_ops.py`
- **Application Handler**: `src/skriptoteket/application/editor/edit_ops/execution.py`
- **Infrastructure Provider**: `src/skriptoteket/infrastructure/llm/openai/chat_ops_provider.py`
- **Structured output format**: `src/skriptoteket/infrastructure/llm/openai/edit_ops_text_format.py`

### Door Client And Wiring

- **DI Container**: `src/skriptoteket/di/llm.py`
- **Door client**: `src/skriptoteket/infrastructure/llm/door/client.py`
- **Door protocol**: `src/skriptoteket/protocols/llm_door.py`
- **Request payloads**: `src/skriptoteket/infrastructure/llm/openai/payloads.py`
- **Door replies and provider errors**: `src/skriptoteket/infrastructure/llm/openai/door_replies.py`

______________________________________________________________________

## Findings And Interpretation

### Source: Execution Flows

### 1. Inline Completion Flow

Ghost text completions on `gpt-6-luna` through the door.

```text
Inline Completion Request Flow
├── POST /completions                        completions.py
│   └── InlineCompletionHandler.handle()     completion_handler.py
│       └── OpenAIInlineCompletionProvider.complete_inline()
│           ├── delimited prefix/suffix prompt
│           ├── build_responses_payload()     payloads.py
│           └── send_responses_call()         door_replies.py
│               └── HuleEduLlmDoorClient.send()   door/client.py
│                   └── POST door /responses with the caller's user id
└── provider failure -> EditorLlmProviderError (no second provider)
```

### 2. Streaming Chat Flow

Real-time conversational AI with server-sent events on `gpt-6.1-sol`.

```text
Streaming Chat Flow
├── POST /tools/{tool_id}/chat               chat.py
│   ├── EditorChatHandler.stream()           chat_handler.py
│   │   └── OpenAIChatStreamProvider.stream_chat()
│   │       └── HuleEduLlmDoorClient.stream()   door/client.py
│   │           └── async chunk iteration -> events
│   └── StreamingResponse with SSE encoding  chat.py
└── Frontend consumption                     frontend/apps/skriptoteket/src/composables/editor/chat/editorChatStreamClient.ts
```

### 3. Edit-Ops Structured Editing

Code modifications as a JSON patch-only text format on `gpt-6.1-sol`.

```text
Edit-Ops Structured Editing Flow
├── POST edit-ops                            edit_ops.py
│   └── EditOpsHandler                       edit_ops_handler.py, edit_ops/execution.py
│       └── OpenAIChatOpsProvider.complete_chat_ops()
│           ├── build_responses_payload() with the patch-only text format
│           │                                edit_ops_text_format.py
│           ├── send_responses_call()        door_replies.py
│           └── extract_response_output_text()  parsing.py
```

### 4. Provider Wiring

One door client serves all three providers.

```text
Provider DI System
├── LlmProvider                              di/llm.py
│   ├── llm_door_client() -> HuleEduLlmDoorClient
│   │   (base URL, internal API key, per-job overage cap from Settings)
│   ├── inline_completion_provider(settings, door)
│   ├── chat_stream_provider(settings, door)
│   └── chat_ops_provider(settings, door)
```

______________________________________________________________________

## Evidence Gaps And Follow-Up

The source does not state separate evidence gaps and follow-up.
