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
└─ skriptoteketGhostText (NEW)
```

### 7.2 Ghost Text State

```typescript
type GhostTextState = {
  text: string | null;     // Suggested completion
  from: number;            // Cursor position when suggested
  decorations: DecorationSet;
};
```

### 7.3 Triggers

| Trigger | Behavior |
| ------- | -------- |
| Typing pause (1500ms) | Auto-fetch completion if enabled |
| Alt+\ | Manual fetch completion |
| Tab | Accept ghost text |
| Escape | Dismiss ghost text |
| Any document change | Clear ghost text |

### 7.4 Request Management

- Cancel pending requests on document change
- Ignore stale responses (cursor moved since request)
- Debounce auto-trigger to reduce API load

---

### Source: 8. Configuration


### 8.1 Backend (Environment Variables)

Prompt templates:

- `LLM_COMPLETION_TEMPLATE_ID` (default: `inline_completion_v1`)
- `LLM_CHAT_TEMPLATE_ID` (default: `editor_chat_v1`)
- `LLM_CHAT_OPS_TEMPLATE_ID` (default: `editor_chat_ops_v1`)

Notes:

- Templates are repo-owned text files with placeholders like `{{CONTRACT_V2_FRAGMENT}}`.
- Placeholders are replaced with code-owned fragments sourced from canonical Contract v2 + policy definitions.

Provider caching + headers (applies per profile):

- `LLM_COMPLETION_PROMPT_CACHE_RETENTION` /
  `LLM_CHAT_PROMPT_CACHE_RETENTION` / `LLM_CHAT_OPS_PROMPT_CACHE_RETENTION`:
  Optional prompt cache retention. Use `24h` for GPT-5-2 family (prompt caching), or omit for providers
  that do not support it.
- `LLM_COMPLETION_PROMPT_CACHE_KEY` /
  `LLM_CHAT_PROMPT_CACHE_KEY` / `LLM_CHAT_OPS_PROMPT_CACHE_KEY`:
  Optional stable key to improve cache routing (example: `skriptoteket:chat_ops`).
- `LLM_COMPLETION_EXTRA_HEADERS` /
  `LLM_CHAT_EXTRA_HEADERS` / `LLM_CHAT_OPS_EXTRA_HEADERS`:
  JSON object of provider-specific headers (example: `{"HTTP-Referer":"https://example.com","X-Title":"Skriptoteket"}`).

Inline completions:

| Variable | Default | Description |
| -------- | ------- | ----------- |
| `LLM_COMPLETION_TEMPLATE_ID` | `inline_completion_v1` | Prompt template ID for system prompt composition |
| `LLM_COMPLETION_ENABLED` | `false` | Enable/disable feature |
| `LLM_COMPLETION_BASE_URL` | `http://localhost:8082` | LLM API URL |
| `OPENAI_LLM_COMPLETION_API_KEY` | `""` | API key (optional for self-hosted) |
| `LLM_COMPLETION_MODEL` | `Devstral-Small-2-24B` | Model name |
| `LLM_COMPLETION_MAX_TOKENS` | `256` | Max tokens in response |
| `LLM_COMPLETION_TEMPERATURE` | `0.2` | Sampling temperature |
| `LLM_COMPLETION_TIMEOUT_SECONDS` | `30` | Request timeout |
| `LLM_COMPLETION_CONTEXT_WINDOW_TOKENS` | `4096` | Context window (prompt + output), matches llama.cpp `n_ctx` |
| `LLM_COMPLETION_CONTEXT_SAFETY_MARGIN_TOKENS` | `256` | Reserved prompt budget for chat wrapping/variance |
| `LLM_COMPLETION_SYSTEM_PROMPT_MAX_TOKENS` | `2048` | Target max tokens for system prompt (rules + KB) |
| `LLM_COMPLETION_PREFIX_MAX_TOKENS` | `2048` | Target max tokens for prefix (keeps tail near cursor) |
| `LLM_COMPLETION_SUFFIX_MAX_TOKENS` | `512` | Target max tokens for suffix (keeps head after cursor) |

Chat (streaming):

| Variable | Default | Description |
| -------- | ------- | ----------- |
| `LLM_CHAT_TEMPLATE_ID` | `editor_chat_v1` | Prompt template ID for system prompt composition |
| `LLM_CHAT_ENABLED` | `false` | Enable/disable feature |
| `LLM_CHAT_BASE_URL` | `http://localhost:8082` | LLM API URL |
| `OPENAI_LLM_CHAT_API_KEY` | `""` | API key (optional for self-hosted) |
| `LLM_CHAT_MODEL` | `Devstral-Small-2-24B` | Model name |
| `LLM_CHAT_MAX_TOKENS` | `1500` | Max tokens in response |
| `LLM_CHAT_TEMPERATURE` | `0.2` | Sampling temperature |
| `LLM_CHAT_TIMEOUT_SECONDS` | `60` | Request timeout |
| `LLM_CHAT_CONTEXT_WINDOW_TOKENS` | `16384` | Context window (prompt + output), matches llama.cpp `n_ctx` |
| `LLM_CHAT_CONTEXT_SAFETY_MARGIN_TOKENS` | `256` | Reserved prompt budget for variance |
| `LLM_CHAT_SYSTEM_PROMPT_MAX_TOKENS` | `1024` | Target max tokens for system prompt (rules + KB) |

Chat edit-ops (non-streaming):

| Variable | Default | Description |
| -------- | ------- | ----------- |
| `LLM_CHAT_OPS_TEMPLATE_ID` | `editor_chat_ops_v1` | Prompt template ID for system prompt composition |
| `LLM_CHAT_OPS_ENABLED` | `false` | Enable/disable feature |
| `LLM_CHAT_OPS_BASE_URL` | `http://localhost:8082` | LLM API URL |
| `OPENAI_LLM_CHAT_OPS_API_KEY` | `""` | API key (optional for self-hosted) |
| `LLM_CHAT_OPS_MODEL` | `Devstral-Small-2-24B` | Model name |
| `LLM_CHAT_OPS_MAX_TOKENS` | `1500` | Max tokens in response |
| `LLM_CHAT_OPS_TEMPERATURE` | `0.2` | Sampling temperature |
| `LLM_CHAT_OPS_TIMEOUT_SECONDS` | `60` | Request timeout |
| `LLM_CHAT_OPS_CONTEXT_WINDOW_TOKENS` | `16384` | Context window (prompt + output), matches llama.cpp `n_ctx` |
| `LLM_CHAT_OPS_CONTEXT_SAFETY_MARGIN_TOKENS` | `256` | Reserved prompt budget for variance |
| `LLM_CHAT_OPS_SYSTEM_PROMPT_MAX_TOKENS` | `1024` | Target max tokens for system prompt (rules + KB) |

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

---

### Source: 9. Security Considerations


### 9.1 API Key Protection

- API keys stored as environment variables on backend only
- Never exposed to frontend
- Backend proxies all LLM requests

### 9.2 Authentication

- Endpoint requires `require_contributor_api` (authenticated contributor+)
- CSRF token required for all POST requests

### 9.3 Rate Limiting

- Consider per-user rate limiting (10 requests/minute)
- Prevents abuse and controls costs

### 9.4 Privacy & Logging

- Do not log raw prefix/suffix/prompt/code
- Log only metadata (lengths, provider, timing, status)
- Document that remote providers receive user code; recommend self-hosted for sensitive content

---

### Source: 10. Files


### 10.1 Backend

| Path | Purpose |
| ---- | ------- |
| `src/skriptoteket/protocols/llm/` | Protocol definitions |
| `src/skriptoteket/infrastructure/llm/openai_provider.py` | OpenAI-compatible client |
| `src/skriptoteket/application/editor/completion_handler.py` | Handler entrypoint (completion orchestration) |
| `src/skriptoteket/application/editor/completion/` | Completion flow submodules (prepare/provider/normalize) |
| `src/skriptoteket/di/llm.py` | DI provider |
| `src/skriptoteket/config.py` | Configuration settings |
| `src/skriptoteket/application/editor/prompt_templates.py` | Prompt template registry (IDs + required placeholders) |
| `src/skriptoteket/application/editor/prompt_fragments.py` | Code-owned fragments (Contract v2 + runner constraints + helpers) |
| `src/skriptoteket/application/editor/prompt_composer.py` | Template composition + validation (placeholders + budget) |
| `src/skriptoteket/web/api/v1/editor/completions.py` | Inline completions API endpoint |
| `src/skriptoteket/web/api/v1/editor/chat.py` | Chat SSE API endpoint |
| `src/skriptoteket/web/api/v1/editor/edit_ops.py` | Edit-ops API endpoints |

### 10.2 Frontend

| Path | Purpose |
| ---- | ------- |
| `frontend/apps/skriptoteket/src/composables/editor/skriptoteketGhostText.ts` | Ghost text extension |
| `frontend/apps/skriptoteket/src/composables/editor/skriptoteketIntelligence.ts` | Bundle integration |
| `frontend/apps/skriptoteket/src/composables/editor/useSkriptoteketIntelligenceExtensions.ts` | Config composable |

---

### Source: 11. Testing


### 11.1 Backend

- Unit: Provider formats FIM request correctly
- Unit: System prompt template composes (placeholders resolved, within budget)
- Integration: Endpoint requires auth + CSRF
- Integration: Returns `enabled=false` when disabled
- Integration: Truncated response returns empty completion

### 11.2 Frontend

- Unit: Ghost text displays at cursor position
- Unit: Multi-line ghost text preserves indentation/newlines
- Unit: Tab accepts, Escape dismisses
- Unit: Document change clears ghost text
- E2E: Full flow with mock LLM server

---

### Source: 12. References


- [ADR-0043: AI completion integration](../adr/adr-0043-ai-completion-integration.md)
- [ADR-SKRIPT-0050: Self-hosted LLM infrastructure](../decisions/adr-skript-0050-self-hosted-llm-infrastructure-for-ai-code-completion.md)
- [ADR-0035: Script editor intelligence architecture](../adr/adr-0035-script-editor-intelligence-architecture.md)
- [ref-ai-script-generation-kb.md](ref-ai-script-generation-kb.md) - Full knowledge base
- [Tabby Config.toml](https://tabby.tabbyml.com/docs/administration/config-toml/) - Tabby configuration
- [Tabby Code Completion](https://tabby.tabbyml.com/docs/administration/code-completion/) - Tabby settings

## Decisions And Interpretation

No separate decisions and interpretation is stated in the source.
