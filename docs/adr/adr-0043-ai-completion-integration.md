---
type: adr
id: ADR-0043
title: "AI-assisted inline completions for script editor"
status: proposed
owners: "agents"
deciders: ["user-lead"]
created: 2025-12-26
---

## Context

The script editor intelligence system (ST-08-10/11/12) provides static analysis-based assistance: import autocomplete,
contract validation, security linting, and hover documentation. While helpful, these features are limited to predefined
patterns and cannot generate novel code suggestions.

Script authors would benefit from AI-powered inline completions (Copilot-style ghost text) that understand Skriptoteket's
runner constraints and Contract v2 requirements.

### Constraints

- Must work with local models (Ollama) and remote APIs (OpenRouter, OpenAI)
- API keys must never be exposed to the frontend
- Must inject Skriptoteket knowledge base (runner constraints, Contract v2, helper docs) into prompts
- Must integrate with existing CodeMirror 6 extension architecture
- Swedish UI for any user-facing messages
- Performance: ghost text should appear within 2-3 seconds of typing pause

### Options Considered

1. **No AI integration** - Keep static analysis only. Simple but limits discoverability.
2. **Claude API (Anthropic)** - High quality but vendor lock-in and requires Anthropic API key.
3. **OpenAI-compatible API** - Works with Ollama (local), OpenRouter, OpenAI, and other providers.
4. **Both Anthropic + OpenAI-compatible** - Maximum flexibility but increased complexity.

## Decision

Use an **OpenAI-compatible backend proxy** with knowledge base injection.

### Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│ Frontend (CodeMirror 6)                                                  │
│  └─ skriptoteketGhostText extension                                     │
│       ├─ Debounced auto-trigger (1500ms)                                │
│       ├─ Manual trigger (Alt+\)                                         │
│       ├─ Ghost text decorations (semi-transparent)                      │
│       └─ Tab to accept, Escape to dismiss                               │
│                                    │                                     │
│                    POST /api/v1/editor/completions                       │
└─────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ Backend                                                                  │
│  ├─ LLMCompletionHandler (application layer)                            │
│  │    └─ Injects KB context into system prompt                          │
│  └─ OpenAICompatibleProvider (infrastructure layer)                     │
│       └─ Calls OpenAI-compatible /chat/completions endpoint             │
└─────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ LLM Provider (Ollama / OpenRouter / OpenAI)                             │
└─────────────────────────────────────────────────────────────────────────┘
```

### Protocol Design

```python
class LLMProviderProtocol(Protocol):
    async def complete(
        self,
        *,
        request: LLMCompletionRequest,
        system_prompt: str,
    ) -> LLMCompletionResponse: ...
```

### Prompt Strategy

Use fill-in-the-middle format with KB injection:

```
System: You are an AI code completion assistant for Skriptoteket...
        [Knowledge base content from ref-ai-script-generation-kb.md]

User: {prefix}<FILL_ME>{suffix}
```

Rules:

- The completion MAY span multiple lines; preserve indentation and newlines.
- Return ONLY the code to insert (no markdown, no explanations).
- Prefer returning a complete coherent block rather than a partial fragment.

Stop tokens (recommended): triple backticks

Truncation policy: if the upstream provider indicates truncation (e.g. `finish_reason == "length"`), the backend must
discard the completion and return an empty completion to avoid partial blocks.

### Configuration

```
LLM_COMPLETION_ENABLED=true
LLM_COMPLETION_BASE_URL=http://localhost:11434/v1
LLM_COMPLETION_API_KEY=sk-...        # Optional for Ollama/local
LLM_COMPLETION_MODEL=codellama:7b
LLM_COMPLETION_MAX_TOKENS=256
LLM_COMPLETION_TEMPERATURE=0.2
LLM_COMPLETION_TIMEOUT_SECONDS=30
```

### File Layout

```
src/skriptoteket/
├─ protocols/llm.py                           # Protocol definitions
├─ infrastructure/llm/
│   └─ openai_provider.py                     # OpenAI-compatible client
├─ application/editor/
│   └─ completion_handler.py                  # Handler with KB injection
└─ di/llm.py                                  # DI provider

frontend/apps/skriptoteket/src/composables/editor/
└─ skriptoteketGhostText.ts                   # Ghost text extension
```

### Integration

Add ghost text to existing intelligence bundle:

```typescript
skriptoteketIntelligence(config)
├─ skriptoteketCompletions (existing)
├─ skriptoteketHover (existing)
├─ skriptoteketLinter (existing)
└─ skriptoteketGhostText (NEW)
```

## Consequences

### Positive

- **Flexible provider support**: Works with Ollama (local/free), OpenRouter (many models), OpenAI (quality)
- **Secure by design**: API keys stored on backend only
- **Context-aware**: KB injection ensures suggestions follow runner constraints
- **Composable**: Integrates with existing extension architecture
- **Graceful degradation**: Returns `enabled: false` when LLM not configured

### Negative

- **Latency**: Network round-trip adds 1-3 seconds per suggestion
- **Cost**: Remote APIs (OpenAI, OpenRouter) incur per-token costs
- **Quality variance**: Local models (CodeLlama 7B) may produce lower quality than GPT-4
- **No streaming**: MVP uses single response; ghost text appears all at once

### Mitigations

- Configurable debouncing reduces unnecessary requests (recommend measuring; typical range 500–1500ms)
- Cancel pending requests on document change
- Consider per-user rate limiting (e.g. 10 requests/minute) to prevent abuse and control costs (follow-up if not in MVP)
- Quality: document recommended models in reference doc
- KB injection must be production-safe: package KB content with the application, load once, and cache in memory
- Privacy: never log raw prefix/suffix/prompt/code; log metadata only (lengths, provider, timing, status)

## References

- [ADR-0035: Script editor intelligence architecture](adr-0035-script-editor-intelligence-architecture.md)
- [ST-08-14: AI inline completions MVP](../backlog/stories/story-08-14-ai-inline-completions.md)
- [EPIC-08: Contextual help and onboarding](../backlog/epics/epic-08-contextual-help-and-onboarding.md)
- [ref-ai-script-generation-kb.md](../reference/ref-ai-script-generation-kb.md) - KB content to inject
