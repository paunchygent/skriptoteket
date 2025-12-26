---
type: reference
id: REF-ai-completion-architecture
title: "AI Completion Architecture Technical Specification"
status: active
owners: "agents"
created: 2025-12-26
topic: "ai-completion"
---

This document specifies the technical architecture for AI-assisted inline completions in the Skriptoteket script editor.

---

## 1. Overview

The AI completion system provides Copilot-style ghost text suggestions while users write scripts. It integrates with the
existing CodeMirror 6 intelligence bundle and uses an OpenAI-compatible backend proxy for LLM access.

**Key features:**

- Ghost text appears after typing pause (debounced auto-trigger)
- Manual trigger via Alt+\ keyboard shortcut
- Tab to accept, Escape to dismiss
- Backend proxy handles LLM calls and KB injection
- Works with Ollama (local), OpenRouter, OpenAI, and other providers

---

## 2. API Contract

### 2.1 Request

```
POST /api/v1/editor/completions
Content-Type: application/json
X-CSRFToken: <csrf_token>

{
  "prefix": "<code before cursor>",
  "suffix": "<code after cursor>"
}
```

**Limits:**

- `prefix`: max 8000 characters
- `suffix`: max 4000 characters

### 2.2 Response

```json
{
  "completion": "<suggested code to insert>",
  "enabled": true
}
```

**When LLM is disabled:**

```json
{
  "completion": "",
  "enabled": false
}
```

### 2.3 Error Handling

| Scenario | Response |
|----------|----------|
| LLM disabled | `{ "completion": "", "enabled": false }` |
| LLM timeout | `{ "completion": "", "enabled": true }` |
| LLM error | `{ "completion": "", "enabled": true }` |
| Unauthorized | HTTP 401 |
| Missing CSRF | HTTP 403 |

---

## 3. Fill-in-the-Middle Prompt Format

The backend constructs the prompt in fill-in-the-middle (FIM) format:

```
System: You are an AI code completion assistant for Skriptoteket...

        ## Skriptoteket Knowledge Base
        [Content from ref-ai-script-generation-kb.md]

        ## Rules
        - Complete the code at <FILL_ME> marker
        - Return ONLY the code to insert
        - NO markdown formatting, NO explanations
        - Follow Contract v2 format for returns

User: {prefix}<FILL_ME>{suffix}
```

**Stop tokens:** `\n\n`, `def `, `class `, triple backticks

---

## 4. Knowledge Base Injection

The handler loads `docs/reference/ref-ai-script-generation-kb.md` and injects it into the system prompt. This ensures
the LLM understands:

- Runner constraints (no network, sandbox environment)
- Contract v2 format (outputs, next_actions, state)
- Available helpers (pdf_helper, tool_errors)
- Input/output conventions (SKRIPTOTEKET_INPUTS, manifest)

---

## 5. CodeMirror Extension Architecture

### 5.1 Extension Composition

```typescript
skriptoteketIntelligence(config)
├─ skriptoteketCompletions (existing)
├─ skriptoteketHover (existing)
├─ skriptoteketLinter (existing)
└─ skriptoteketGhostText (NEW)
```

### 5.2 Ghost Text State

```typescript
type GhostTextState = {
  text: string | null;     // Suggested completion
  from: number;            // Cursor position when suggested
  decorations: DecorationSet;
};
```

### 5.3 State Effects

- `setGhostText({ text, from })` - Display ghost text at position
- `clearGhostText` - Remove ghost text

### 5.4 Triggers

| Trigger | Behavior |
|---------|----------|
| Typing pause (1500ms) | Auto-fetch completion if enabled |
| Alt+\ | Manual fetch completion |
| Tab | Accept ghost text |
| Escape | Dismiss ghost text |
| Any document change | Clear ghost text |

### 5.5 Request Management

- Cancel pending requests on document change
- Ignore stale responses (cursor moved since request)
- Debounce auto-trigger to reduce API load

---

## 6. Configuration

### 6.1 Backend (Environment Variables)

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_COMPLETION_ENABLED` | `false` | Enable/disable feature |
| `LLM_COMPLETION_BASE_URL` | `http://localhost:11434/v1` | OpenAI-compatible API URL |
| `LLM_COMPLETION_API_KEY` | `None` | API key (optional for Ollama) |
| `LLM_COMPLETION_MODEL` | `codellama:7b` | Model name |
| `LLM_COMPLETION_MAX_TOKENS` | `256` | Max tokens in response |
| `LLM_COMPLETION_TEMPERATURE` | `0.2` | Sampling temperature |
| `LLM_COMPLETION_TIMEOUT_SECONDS` | `30` | Request timeout |

### 6.2 Frontend (Intelligence Config)

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

## 7. Security Considerations

### 7.1 API Key Protection

- API keys stored as environment variables on backend only
- Never exposed to frontend
- Backend proxies all LLM requests

### 7.2 Authentication

- Endpoint requires `require_contributor_api` (authenticated contributor+)
- CSRF token required for all POST requests

### 7.3 Rate Limiting

- Consider per-user rate limiting (10 requests/minute)
- Prevents abuse and controls costs

### 7.4 Input Validation

- Prefix/suffix length limits prevent oversized payloads
- Sanitize before sending to LLM (optional PII filtering)

---

## 8. Provider Compatibility

### 8.1 Ollama (Local)

```bash
LLM_COMPLETION_BASE_URL=http://localhost:11434/v1
LLM_COMPLETION_MODEL=codellama:7b
# No API key needed
```

### 8.2 OpenRouter

```bash
LLM_COMPLETION_BASE_URL=https://openrouter.ai/api/v1
LLM_COMPLETION_API_KEY=sk-or-...
LLM_COMPLETION_MODEL=meta-llama/llama-3.1-70b-instruct
```

### 8.3 OpenAI

```bash
LLM_COMPLETION_BASE_URL=https://api.openai.com/v1
LLM_COMPLETION_API_KEY=sk-...
LLM_COMPLETION_MODEL=gpt-4o-mini
```

---

## 9. Recommended Models

| Provider | Model | Quality | Speed | Cost |
|----------|-------|---------|-------|------|
| Ollama | codellama:7b | Medium | Fast | Free |
| Ollama | codellama:13b | Good | Medium | Free |
| OpenRouter | llama-3.1-70b | Very Good | Medium | Low |
| OpenAI | gpt-4o-mini | Excellent | Fast | Medium |

For code completion, prioritize speed over quality. `codellama:7b` is a good starting point.

---

## 10. Files

### 10.1 Backend

| Path | Purpose |
|------|---------|
| `src/skriptoteket/protocols/llm.py` | Protocol definitions |
| `src/skriptoteket/infrastructure/llm/openai_provider.py` | OpenAI-compatible client |
| `src/skriptoteket/application/editor/completion_handler.py` | Handler with KB injection |
| `src/skriptoteket/di/llm.py` | DI provider |
| `src/skriptoteket/config.py` | Configuration settings |
| `src/skriptoteket/web/api/v1/editor.py` | API endpoint |

### 10.2 Frontend

| Path | Purpose |
|------|---------|
| `frontend/apps/skriptoteket/src/composables/editor/skriptoteketGhostText.ts` | Ghost text extension |
| `frontend/apps/skriptoteket/src/composables/editor/skriptoteketIntelligence.ts` | Bundle integration |
| `frontend/apps/skriptoteket/src/composables/editor/useSkriptoteketIntelligenceExtensions.ts` | Config composable |

---

## 11. Testing

### 11.1 Backend

- Unit: Provider formats FIM request correctly
- Unit: Handler injects KB into system prompt
- Integration: Endpoint requires auth + CSRF
- Integration: Returns `enabled=false` when disabled

### 11.2 Frontend

- Unit: Ghost text displays at cursor position
- Unit: Tab accepts, Escape dismisses
- Unit: Document change clears ghost text
- E2E: Full flow with mock LLM server

---

## 12. References

- [ADR-0043: AI completion integration](../adr/adr-0043-ai-completion-integration.md)
- [ADR-0035: Script editor intelligence architecture](../adr/adr-0035-script-editor-intelligence-architecture.md)
- [ref-ai-script-generation-kb.md](ref-ai-script-generation-kb.md) - Knowledge base content
