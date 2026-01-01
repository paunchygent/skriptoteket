---
type: story
id: ST-08-17
title: "Tabby edit suggestions + prompt A/B evaluation"
status: ready
owners: "agents"
created: 2025-12-31
epic: "EPIC-08"
acceptance_criteria:
  - "Given LLM edit suggestions are enabled and provider=tabby, when an edit is requested, then the backend calls Tabby /v1/chat/completions and returns enabled=true with a raw replacement suggestion"
  - "Given provider=llama (default), when an edit is requested, then behavior matches the ST-08-16 llama-only path (no regression)"
  - "Given a configured prompt variant, when an edit is requested, then the selected prompt template is applied and the variant id is logged (metadata only)"
  - "Given the A/B evaluation script is run, when it completes, then it writes a summary report (success/empty/truncated/latency) to .artifacts/ai-edit-ab/ without logging prompt or code content"
ui_impact: "None - backend/provider + evaluation harness only."
data_impact: "None - requests are stateless."
dependencies: ["ST-08-16", "ADR-0043", "ADR-0050"]
---

## Context

ST-08-16 validates llama-server-only edit suggestions first. This follow-up adds an optional Tabby chat provider and
introduces prompt A/B evaluation so we can choose the most reliable prompt shape before expanding UI features.

## Scope

### Backend

- Add a Tabby chat provider for edit suggestions (OpenAI-compatible /v1/chat/completions).
- Add a provider switch for edit suggestions (e.g., llama vs tabby) without affecting inline completions.
- Keep failure behavior unchanged: return enabled=false + empty suggestion on timeout/truncation/unavailable provider.

### Prompt Variants (A/B)

- Define prompt variants in code/config with stable IDs.
- Add a selector (config or request header) to choose the variant per request for testing.
- Log only metadata: provider, model, latency, variant id, selection length, status.

### Evaluation Harness

- Add a script that runs a fixed fixture set against each prompt variant and writes a summary report to
  `.artifacts/ai-edit-ab/` (no prompt/code content stored).

## Testing

- Unit: prompt-variant selector uses the expected template and logs variant id.
- Unit: provider routing selects Tabby vs llama based on config.
- Integration: mock Tabby chat response returns raw replacement suggestion.
- Script run: A/B evaluation script emits a summary report without prompt/code content.

## Out of Scope

- UI changes for edit suggestions (handled in ST-08-16).
- Streaming responses or structured JSON outputs.
- Tabby repository indexing or prompt_template tuning.
