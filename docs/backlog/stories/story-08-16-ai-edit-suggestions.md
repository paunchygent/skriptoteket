---
type: story
id: ST-08-16
title: "AI edit suggestions MVP (apply CodeMirror changes)"
status: done
owners: "agents"
created: 2025-12-27
updated: 2026-01-01
epic: "EPIC-08"
acceptance_criteria:
  - "Given the user selects a range and requests an AI edit, when LLM edit suggestions are enabled, then the UI shows a preview of the suggested change"
  - "Given the user accepts the preview, when applied, then the editor is updated via CodeMirror changes (preserving undo history)"
  - "Given LLM edit suggestions are disabled, when an edit is requested, then the response returns enabled=false gracefully"
  - "Given the upstream LLM response is truncated (finish_reason=length), when an edit is requested, then no suggestion is shown (empty result) to avoid partial edits"
ui_impact: "Adds a chat-style edit assistant that proposes and applies changes to the editor."
data_impact: "None - requests are stateless."
dependencies: ["ADR-0043", "ST-08-14"]
---

## Context

Inline completions (ST-08-14) are optimized for low-latency, local-first suggestions. Edit suggestions are a different
capability: they require more context and typically benefit from larger remote models. To keep DI protocol-first, edit
suggestions use a separate protocol surface and separate provider configuration.

## Scope

### Backend

- Add a dedicated endpoint for edit suggestions (separate from `/completions`), returning structured edits.
- Enforce "no partial edits": if the upstream provider indicates truncation (e.g. `finish_reason == "length"`), return
  an empty suggestion.
- Apply privacy/logging rules: never log code/prompt; log metadata only.

### Protocol-first DI

Define a separate protocol surface (in addition to inline completions):

```python
class EditSuggestionProviderProtocol(Protocol):
    async def suggest_edits(
        self,
        *,
        request: LLMEditRequest,
        system_prompt: str,
    ) -> LLMEditResponse: ...
```

This enables injecting a remote/large model for edits while keeping a local/small model for inline completions.

### Frontend

- Provide a "suggest edit" UI (modal or side panel) that previews the change before applying.
- Apply accepted edits using CodeMirror transactions (`changes`) so the user can undo/redo naturally.

### Configuration

Use a separate provider configuration for edit suggestions (distinct from `LLM_COMPLETION_*` used for ghost text):

```
LLM_EDIT_ENABLED=false
LLM_EDIT_BASE_URL=https://openrouter.ai/api/v1
LLM_EDIT_API_KEY=sk-or-...           # Typically required
LLM_EDIT_MODEL=...                   # e.g. a larger chat/edit model
LLM_EDIT_MAX_TOKENS=512
LLM_EDIT_TEMPERATURE=0.2
LLM_EDIT_TIMEOUT_SECONDS=30
```

## Out of Scope

- Streaming edit suggestions
- Auto-trigger edits while typing (edits are manual/explicit)
- Per-user rate limiting (consider follow-up if needed)
