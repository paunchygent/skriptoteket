---
type: story
id: ST-08-14
title: "AI inline completions MVP (Copilot-style ghost text)"
status: ready
owners: "agents"
created: 2025-12-26
epic: "EPIC-08"
acceptance_criteria:
  - "Given the user types and pauses for 1.5 seconds, when LLM is enabled, then ghost text suggestion appears at cursor"
  - "Given ghost text is visible, when user presses Tab, then the suggestion is inserted into the document"
  - "Given the suggestion contains multiple lines, when ghost text is visible, then whitespace/newlines are preserved and Tab inserts the entire suggestion verbatim"
  - "Given ghost text is visible, when user presses Escape, then the ghost text is dismissed"
  - "Given ghost text is visible, when user types any character, then the ghost text is cleared"
  - "Given user presses Alt+\\, when LLM is enabled, then a completion is requested immediately (manual trigger)"
  - "Given LLM is disabled in config, when completion is requested, then response returns enabled=false gracefully"
  - "Given LLM request times out, when ghost text is pending, then no error is shown and ghost text remains empty"
  - "Given the upstream LLM response is truncated (finish_reason=length), when completion is requested, then no ghost text is shown (completion is empty) to avoid partial blocks"
ui_impact: "Adds semi-transparent ghost text suggestions in the script editor, similar to GitHub Copilot."
data_impact: "None - LLM requests are stateless."
dependencies: ["ST-08-10", "ADR-0043"]
---

## Context

Script authors benefit from AI-powered code suggestions that understand Skriptoteket's runner constraints and Contract v2
requirements. This story adds Copilot-style inline completions that appear as ghost text while typing.

This builds on the static intelligence system (ST-08-10/11/12) by adding dynamic, LLM-powered suggestions.

This story covers the **inline completion** capability only. Chat-style edit suggestions that apply CodeMirror changes
use a separate protocol surface and are tracked in ST-08-16.

## Technical Decisions

See [ADR-0043: AI completion integration](../../adr/adr-0043-ai-completion-integration.md) for architecture decisions
(OpenAI-compatible backend proxy, KB injection, CodeMirror extension design).

See [ref-ai-completion-architecture.md](../../reference/ref-ai-completion-architecture.md) for technical specification.

## Scope

### Backend

#### Protocol (`src/skriptoteket/protocols/llm.py`)

```python
class InlineCompletionProviderProtocol(Protocol):
    async def complete_inline(
        self,
        *,
        request: LLMCompletionRequest,
        system_prompt: str,
    ) -> LLMCompletionResponse: ...
```

#### Provider (`src/skriptoteket/infrastructure/llm/openai_provider.py`)

- OpenAI-compatible HTTP client using httpx
- Configurable base URL, model, timeout, temperature
- Formats fill-in-the-middle prompt

#### Handler (`src/skriptoteket/application/editor/completion_handler.py`)

- Loads KB from `docs/reference/ref-ai-script-generation-kb.md`
- Injects KB into system prompt
- Formats user message as `{prefix}<FILL_ME>{suffix}`

#### API Endpoint (`POST /api/v1/editor/completions`)

- Requires `require_contributor_api` authentication
- Requires CSRF token
- Returns `{ completion: string, enabled: boolean }`

### Frontend

#### Ghost Text Extension (`skriptoteketGhostText.ts`)

- `StateField` for ghost text state (text, position, decorations)
- `GhostTextWidget` renders semi-transparent text
- Debounced auto-trigger (1500ms default)
- Keymap: Tab (accept), Escape (dismiss), Alt+\ (manual trigger)

#### Integration

- Add to `skriptoteketIntelligence.ts` bundle
- Add config to `useSkriptoteketIntelligenceExtensions.ts`
- Pass config from `EditorWorkspacePanel.vue`

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

## Files

### Create

- `src/skriptoteket/protocols/llm.py`
- `src/skriptoteket/infrastructure/llm/__init__.py`
- `src/skriptoteket/infrastructure/llm/openai_provider.py`
- `src/skriptoteket/application/editor/__init__.py`
- `src/skriptoteket/application/editor/completion_handler.py`
- `src/skriptoteket/di/llm.py`
- `frontend/apps/skriptoteket/src/composables/editor/skriptoteketGhostText.ts`

### Modify

- `src/skriptoteket/config.py` - Add LLM settings
- `src/skriptoteket/di/__init__.py` - Register LLMProvider
- `src/skriptoteket/web/api/v1/editor.py` - Add `/completions` endpoint
- `frontend/apps/skriptoteket/src/composables/editor/skriptoteketIntelligence.ts` - Add ghost text
- `frontend/apps/skriptoteket/src/composables/editor/useSkriptoteketIntelligenceExtensions.ts` - Add config

## Testing

### Backend

- Unit: Provider formats FIM request correctly
- Unit: Handler injects KB into system prompt
- Integration: Endpoint requires auth + CSRF
- Integration: Returns `enabled=false` when disabled
- Integration: Truncated upstream response (finish_reason="length") returns empty completion

### Frontend

- Unit: Ghost text displays at cursor position
- Unit: Multi-line ghost text preserves indentation/newlines
- Unit: Tab accepts, Escape dismisses
- Unit: Tab inserts all suggestion lines verbatim
- Unit: Document change clears ghost text

### E2E

- Playwright script with mock LLM server
- Test auto-trigger, manual trigger, accept, dismiss
- Test truncated completion suppression (no partial blocks)

## Out of Scope

- Streaming responses (ghost text appears character-by-character)
- User preference settings UI
- Per-user rate limiting (consider for follow-up)

## Notes

- Ghost text should be visually distinct (semi-transparent, italic)
- Cancel pending requests when cursor moves or document changes
- Log LLM errors but don't expose to user
