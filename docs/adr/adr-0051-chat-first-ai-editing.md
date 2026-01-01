---
type: adr
id: ADR-0051
title: "Chat-first AI editing (structured CRUD ops + diff preview + apply/undo)"
status: accepted
owners: "agents"
deciders: ["user-lead"]
created: 2026-01-01
links: ["EPIC-08", "ST-08-20", "ST-08-21", "ST-08-22", "ADR-0043"]
---

## Context

Skriptoteket’s editor currently has:

- Static “editor intelligence” (lint, hover, completions).
- AI inline completions (“ghost text”, ST-08-14).
- AI edit suggestions MVP (ST-08-16) that returns raw replacement text for a selected range.

This works for experienced script authors, but it is not beginner-friendly:

- Ghost text assumes the author can already start writing code.
- The edit MVP depends on the author selecting the correct region and cannot naturally express insert/delete operations.
- The preview is not a diff and does not clearly communicate “what will change”.

We want a chat-first authoring experience where a novice can describe intent in Swedish and iteratively refine a script,
while the platform maintains deterministic, auditable edits.

Constraints:

- Privacy: never log prompts, code, or conversation content; metadata-only observability.
- Safety: proposed edits must be previewable (diff), explicitly applied, and easy to undo.
- Budgeting: local inference context window constraints apply (existing budgeting + template system).
- Architecture: keep protocol-first DI and keep web/api layers thin (handlers own business logic).

## Decision

Introduce a chat-first AI assistant in the script editor that proposes **structured CRUD edit operations** and uses a
safe preview/apply flow.

### 1) UI placement: editor drawer

- Place AI chat in the editor as a drawer/panel that can be opened without leaving the editor.
- Keep conversation history client-side (local storage) to avoid server-side persistence of message content.

### 2) Edit protocol: structured CRUD operations (v1)

The backend returns a validated list of edit operations that support:

- `insert` (at cursor)
- `replace` (selection or whole document)
- `delete` (selection)

Targets are intentionally limited in v1 to keep edits deterministic:

- whole document
- current selection
- cursor insertion

If the model response is invalid, truncated, or over budget, the system must fail safely (no partial edits).

### 3) Guardrails: diff preview + atomic apply + undo

- The UI MUST render a diff preview of “current” vs “proposed” before applying any changes.
- Applying a proposal MUST be a single atomic CodeMirror transaction so a single undo reverts the change.
- If the underlying editor content changes after the proposal is generated, apply MUST be blocked and the user prompted
  to regenerate.

### 4) Observability + evaluation

- Log metadata only (template id, lengths, outcome, provider/model, latency if available).
- Never log prompt text, code text, conversation messages, or model outputs.
- Keep eval-only response metadata behind an admin-gated dev-only mode (existing `X-Skriptoteket-Eval` pattern).

## Consequences

### Positive

- Beginner-friendly entry point (“describe what you want”) without requiring region selection expertise.
- Deterministic, auditable changes via structured ops + diff preview.
- Lower risk of “AI did something surprising” due to explicit apply and easy undo.

### Negative / trade-offs

- Requires new backend schema validation and failure-handling paths for model responses.
- Requires a reusable diff viewer component and a stronger preview/apply UX than the current edit MVP.
- Limiting targets in v1 reduces capability (no multi-range or semantic refactors) but improves safety.

### Follow-ups (out of scope for this ADR)

- Multi-range operations, anchor/pattern-based targeting, or protected/locked regions.
- Server-side conversation persistence or shared conversations.
- Metrics dashboards; only metadata logging is in scope.
