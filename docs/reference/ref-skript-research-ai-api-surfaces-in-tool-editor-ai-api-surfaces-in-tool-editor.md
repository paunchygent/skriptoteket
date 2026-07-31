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
summary: 'Traces the four AI API surfaces in the tool editor: inline completions for
  ghost text, streaming chat for conversation, edit-ops for structured code editing,
  and the provider configuration system that enables local-fi…'
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

Traces the four AI API surfaces in the tool editor: inline completions for ghost text, streaming chat for conversation, edit-ops for structured code editing, and the provider configuration system that enables local-first with remote fallback. Key locations include the HTTP endpoint construction, FIM prompt building, SSE event encoding, GBNF grammar application, and local server detection.

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

### Provider Configuration

- **DI Container**: `src/skriptoteket/di/llm.py`
- **Common LLM Logic**: `src/skriptoteket/infrastructure/llm/openai/common.py`

---

### Source: Key Locations

| ID | Title | Path |
| -- | ----- | ---- |
| 1a | API Endpoint Entry | `src/skriptoteket/web/api/v1/editor/completions.py:46` |
| 1b | Primary Provider Call | `src/skriptoteket/application/editor/completion_handler.py:450` |
| 1c | HTTP Request Construction | `src/skriptoteket/infrastructure/llm/openai/inline_completion_provider.py:83` |
| 1d | FIM Prompt Building | `src/skriptoteket/infrastructure/llm/openai/inline_completion_provider.py:86` |
| 1e | Response Processing | `src/skriptoteket/infrastructure/llm/openai/inline_completion_provider.py:167` |
| 2a | Chat Stream Initiation | `src/skriptoteket/web/api/v1/editor/chat.py:62` |
| 2b | Failover Routing | `src/skriptoteket/application/editor/chat_handler.py:120` |
| 2c | Stream Processing | `src/skriptoteket/application/editor/chat_handler.py:140` |
| 2d | Chat API Endpoint | `src/skriptoteket/infrastructure/llm/openai/chat_stream_provider.py:79` |
| 2e | SSE Event Encoding | `src/skriptoteket/web/api/v1/editor/chat.py:70` |
| 3a | Edit-Ops Request | `src/skriptoteket/web/api/v1/editor/edit_ops.py:72` |
| 3b | Chat-Ops Execution | `src/skriptoteket/application/editor/edit_ops/execution.py:85` |
| 3c | Grammar Selection | `src/skriptoteket/infrastructure/llm/openai/chat_ops_provider.py:126` |
| 3d | GBNF Grammar Application | `src/skriptoteket/infrastructure/llm/openai/chat_ops_provider.py:127` |
| 3e | Structured Response | `src/skriptoteket/infrastructure/llm/openai/chat_ops_provider.py:155` |
| 4a | Primary Provider Instantiation | `src/skriptoteket/di/llm.py:110` |
| 4b | Fallback Provider Creation | `src/skriptoteket/di/llm.py:113` |
| 4c | URL Configuration | `src/skriptoteket/infrastructure/llm/openai/inline_completion_provider.py:46` |
| 4d | Local Server Detection | `src/skriptoteket/infrastructure/llm/openai/common.py:21` |
| 4e | Provider Set Assembly | `src/skriptoteket/di/llm.py:125` |

### Source: Execution Flows

### 1. Inline Completion Flow

Ghost text completions using local Llama.cpp with OpenAI fallback.

```text
Inline Completion Request Flow
├── POST /completions API endpoint <-- 1a
│   └── InlineCompletionHandler.handle() <-- completion_handler.py:200
│       ├── Remote fallback check <-- completion_handler.py:420
│       └── Provider selection logic <-- completion_handler.py:440
│           └── Primary provider call <-- 1b
│               └── OpenAIInlineCompletionProvider <-- llm.py:110
│                   ├── URL construction <-- 1c
│                   │   └── Targets localhost:8082
│                   ├── FIM prompt building <-- 1d
│                   │   └── Formats prefix/suffix
│                   └── HTTP POST request <-- inline_completion_provider.py:152
│                       └── Response parsing <-- 1e
└── Fallback provider (if needed) <-- completion_handler.py:480
    └── OpenAI API call <-- inline_completion_provider.py:152
```

### 2. Streaming Chat Flow

Real-time conversational AI with server-sent events.

```text
Streaming Chat Flow
├── POST /tools/{tool_id}/chat <-- 2a
│   ├── handler.stream() entry point <-- chat_handler.py:69
│   │   ├── failover.decide_route() <-- 2b
│   │   │   └── selects primary provider <-- chat_failover_router.py:45
│   │   └── providers.primary.stream_chat() <-- 2c
│   │       ├── OpenAI chat API call <-- chat_stream_provider.py:117
│   │       │   └── /chat/completions endpoint <-- 2d
│   │       └── async chunk iteration <-- chat_stream_provider.py:128
│   │           └── yield _encode_sse_event(event) <-- 2e
│   └── StreamingResponse wrapper <-- chat.py:72
│       └── SSE encoding loop <-- chat.py:66
└── Frontend consumption <-- editorChatStreamClient.ts:15
    └── EventSource stream client <-- editorChatStreamClient.ts:45
```

### 3. Edit-Ops Structured Editing

Code modifications using GBNF grammars and JSON schemas.

```text
Edit-Ops Structured Editing Flow
├── API Endpoint receives request <-- 3a
│   └── EditOpsHandler processes command <-- edit_ops_handler.py:59
│       └── EditOpsExecution calls LLM <-- 3b
│           └── ChatOpsProvider builds request <-- chat_ops_provider.py:36
│               ├── Detects local server <-- common.py:19
│               │   └── Supports GBNF grammar? <-- 3c
│               ├── Applies constraints <-- chat_ops_provider.py:95
│               │   └── Adds GBNF grammar <-- 3d
│               └── Returns structured response <-- 3e
```

### 4. Provider Configuration & DI

How AI providers are wired up with local/remote fallback.

```text
Provider DI System
├── LlmProvider.configure_providers() <-- llm.py:77
│   ├── inline_completion_providers() <-- 4a
│   │   ├── OpenAIInlineCompletionProvider() <-- inline_completion_provider.py:34
│   │   │   └── normalize_base_url() <-- 4c
│   │   └── is_local_llama_server() <-- 4d
│   └── fallback provider creation <-- 4b
└── Provider Set Assembly <-- 4e
    └── InlineCompletionProviders() <-- provider_sets.py:41
        ├── primary provider <-- provider_sets.py:42
        └── fallback provider <-- provider_sets.py:43
```

---

## Findings And Interpretation

### Source: Execution Flows

### 1. Inline Completion Flow

Ghost text completions using local Llama.cpp with OpenAI fallback.

```text
Inline Completion Request Flow
├── POST /completions API endpoint <-- 1a
│   └── InlineCompletionHandler.handle() <-- completion_handler.py:200
│       ├── Remote fallback check <-- completion_handler.py:420
│       └── Provider selection logic <-- completion_handler.py:440
│           └── Primary provider call <-- 1b
│               └── OpenAIInlineCompletionProvider <-- llm.py:110
│                   ├── URL construction <-- 1c
│                   │   └── Targets localhost:8082
│                   ├── FIM prompt building <-- 1d
│                   │   └── Formats prefix/suffix
│                   └── HTTP POST request <-- inline_completion_provider.py:152
│                       └── Response parsing <-- 1e
└── Fallback provider (if needed) <-- completion_handler.py:480
    └── OpenAI API call <-- inline_completion_provider.py:152
```

### 2. Streaming Chat Flow

Real-time conversational AI with server-sent events.

```text
Streaming Chat Flow
├── POST /tools/{tool_id}/chat <-- 2a
│   ├── handler.stream() entry point <-- chat_handler.py:69
│   │   ├── failover.decide_route() <-- 2b
│   │   │   └── selects primary provider <-- chat_failover_router.py:45
│   │   └── providers.primary.stream_chat() <-- 2c
│   │       ├── OpenAI chat API call <-- chat_stream_provider.py:117
│   │       │   └── /chat/completions endpoint <-- 2d
│   │       └── async chunk iteration <-- chat_stream_provider.py:128
│   │           └── yield _encode_sse_event(event) <-- 2e
│   └── StreamingResponse wrapper <-- chat.py:72
│       └── SSE encoding loop <-- chat.py:66
└── Frontend consumption <-- editorChatStreamClient.ts:15
    └── EventSource stream client <-- editorChatStreamClient.ts:45
```

### 3. Edit-Ops Structured Editing

Code modifications using GBNF grammars and JSON schemas.

```text
Edit-Ops Structured Editing Flow
├── API Endpoint receives request <-- 3a
│   └── EditOpsHandler processes command <-- edit_ops_handler.py:59
│       └── EditOpsExecution calls LLM <-- 3b
│           └── ChatOpsProvider builds request <-- chat_ops_provider.py:36
│               ├── Detects local server <-- common.py:19
│               │   └── Supports GBNF grammar? <-- 3c
│               ├── Applies constraints <-- chat_ops_provider.py:95
│               │   └── Adds GBNF grammar <-- 3d
│               └── Returns structured response <-- 3e
```

### 4. Provider Configuration & DI

How AI providers are wired up with local/remote fallback.

```text
Provider DI System
├── LlmProvider.configure_providers() <-- llm.py:77
│   ├── inline_completion_providers() <-- 4a
│   │   ├── OpenAIInlineCompletionProvider() <-- inline_completion_provider.py:34
│   │   │   └── normalize_base_url() <-- 4c
│   │   └── is_local_llama_server() <-- 4d
│   └── fallback provider creation <-- 4b
└── Provider Set Assembly <-- 4e
    └── InlineCompletionProviders() <-- provider_sets.py:41
        ├── primary provider <-- provider_sets.py:42
        └── fallback provider <-- provider_sets.py:43
```

---

## Evidence Gaps And Follow-Up

The source does not state separate evidence gaps and follow-up.
