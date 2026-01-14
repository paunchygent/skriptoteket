---
type: adr
id: ADR-0051
title: "Chat-first AI editing (structured CRUD ops + diff preview + apply/
undo)"
status: accepted
owners: "agents"
deciders: ["user-lead"]
created: 2026-01-01
updated: 2026-01-14
links: ["EPIC-08", "ST-08-20", "ST-08-21", "ST-08-22", "ST-08-24", "ST-14-17",
"ST-14-30", "ST-08-28", "ADR-0043"]
---

## Context

Skriptoteket’s editor currently has:

- Static —editor intelligence— (lint, hover, completions).
- AI inline completions (—ghost text—, ST-08-14).
- AI edit suggestions MVP (ST-08-16) that returns raw replacement text for a
  selected range.

This works for experienced script authors, but it is not beginner-friendly:

- Ghost text assumes the author can already start writing code.
- The edit MVP depends on the author selecting the correct region and cannot
  naturally express insert/delete operations.
- The preview is not a diff and does not clearly communicate —what will
  change—.

We want a chat-first authoring experience where a novice can describe intent
in Swedish and iteratively refine a script,
while the platform maintains deterministic, auditable edits.

Constraints:

- Privacy: never log prompts, code, or conversation content; metadata-only
  observability.
- Safety: proposed edits must be previewable (diff), explicitly applied, and
  easy to undo.
- Budgeting: local inference context window constraints apply (existing
  budgeting + template system).
- Architecture: keep protocol-first DI and keep web/api layers thin (handlers
  own business logic).

## Decision

Introduce a chat-first AI assistant in the script editor that proposes
**structured CRUD edit operations** and uses a
safe preview/apply flow.

### 1) UI placement: editor drawer

- Place AI chat in the editor as a drawer/panel that can be opened without
  leaving the editor.
- Store conversation history server-side as the canonical source of truth (not
  client-side only).

### 2) Edit protocol: structured CRUD operations (v1)

*Note: v1 CRUD operations (insert/replace/delete at cursor/selection) remain in the protocol definition for backward compatibility but are **deprecated** for the primary chat-ops workflow. The assistant is instructed to use Patch Ops (v2) exclusively.*

The backend returns a validated list of edit operations that support:

- `insert` (at cursor)
- `replace` (selection or whole document)
- `delete` (selection)

Targets are intentionally limited in v1 to keep edits deterministic:

- whole document
- current selection
- cursor insertion

If the model response is invalid, truncated, or over budget, the system must
fail safely (no partial edits).

### 2.1 Virtual files (multi-document context)

To support tool authoring where —code + schemas + instructions— must be edited
together without boundary violations, AI
edit proposals are expressed against a small set of named **virtual files**:

- `tool.py` (the main script)
- `entrypoint.txt`
- `settings_schema.json`
- `input_schema.json`
- `usage_instructions.md`

The UI may render these as separate editors or as a combined —Pro mode— bundle
view, but the AI protocol targets virtual
files explicitly so:

- diffs can be shown per file
- apply/undo can be atomic across all targeted files
- the assistant cannot accidentally mix JSON schema edits into Python (and
  vice versa)

### 2.2 Edit protocol v2: patch-only targets (alignment)

To match coding-assistant expectations and reduce ambiguity/hallucination, we align on a **patch-only** strategy. The assistant must use unified diffs to express changes.

- **Patch only**: The assistant must emit `patch` operations that carry a unified diff for a single virtual file.
- **Strict apply**: The diff must reference the same canonical virtual file id in the `a/` and `b/` headers, and apply is strict (all hunks must match; bounded fuzz allowed).
- **No cursor/anchor targeting in v2**: The system prompt excludes v1 CRUD (cursor/selection targets) and v2 anchor targets so the model must think in diffs, which improves coherence and reduces —invalid anchor— errors.

#### 2.2.1 Triggering v2 + request semantics (required)

Because a CodeMirror editor always has an internal cursor, **v2 must be triggered by request semantics**, not by
—whatever the editor happens to have—.

Definitions:

- **Explicit selection/cursor**: a location that the user intentionally targeted in the active virtual file, and that
  the frontend can resolve at the time it sends `POST /api/v1/editor/edit-ops`.
- **Implicit/unknown location**: the user did not explicitly target a location, or the frontend cannot reliably resolve
  selection/cursor for the active file at send time (e.g. editor view unavailable / not focused).

Frontend rules:

- If a selection exists in the active file, include **both**:
  - `selection: { from, to }`
  - `cursor: { pos }` (cursor position MUST be explicitly defined; default to the selection end)
- If there is no selection but there is an explicitly targeted cursor in the active file, include:
  - `cursor: { pos }`
- If the location is implicit/unknown, omit **both** `selection` and `cursor` to intentionally trigger v2.

Backend rules:

- When `selection` and `cursor` are omitted (or when operating in v2 mode), the system prompt MUST instruct the model to use `patch` ONLY and MUST treat other op types (cursor/anchor) as invalid (safe-fail).

#### 2.2.2 Patch op (v2)

Patch ops apply against a single virtual file with backend-first unified-diff application (sanitization + bounded fuzz).

Shape (conceptual):

```json
{
  "op": "patch",
  "target_file": "tool.py",
  "patch": "diff --git a/tool.py b/tool.py\n--- a/tool.py\n+++ b/tool.py\n@@ ...\n"
}
```

Rules:

- `target_file` MUST be one of the canonical virtual file ids.
- The patch MUST reference the same canonical id in both headers (`a/<id>` and `b/<id>`).
- Backend MUST sanitize/normalize predictable LLM noise (code fences, indentation, CRLF, invisible chars, missing
  headers) before attempting apply.
- Apply MUST be atomic (—all hunks or nothing—). Multi-file diffs are rejected.
- Apply uses a **bounded fuzz ladder** to reduce regeneration loops:
  - Stage 0: strict apply (fuzz 0)
  - Stage 0b: whitespace-tolerant strict apply (ignore whitespace in context)
  - Stage 1: fuzz 1
  - Stage 2: fuzz 2
- Safety policy:
  - If `max_offset > 50` lines, treat the diff as stale and fail with a regenerate message.
  - If `fuzz>0` OR `max_offset>10`, the UI MUST show a warning and require an extra confirmation before apply.

#### 2.2.3 Anchor target (v2) - DEPRECATED

*Note: Anchor targeting was proposed as an alternative to cursors but proved brittle and ambiguous compared to unified diffs. It is removed from the system prompt in favor of patch-only.*

### 3) Guardrails: diff preview + atomic apply + undo

- The UI MUST render a diff preview of —current— vs —proposed— before applying
  any changes.
- The diff preview UI SHOULD be purpose-built for AI proposals (minimal controls), even if it reuses the underlying diff
  engine used elsewhere in the editor.
- Applying a proposal MUST be a single atomic CodeMirror transaction so a
  single undo reverts the change.
- If the underlying editor content changes after the proposal is generated, apply MUST be blocked and the user prompted
    to regenerate.
- Preview and apply MUST be version-gated so —what the user saw is what gets applied—:
  - Preview returns `base_hash` + `patch_id` for the exact base + normalized ops/diff.
  - Apply MUST include the same tokens and MUST return `409` on mismatch; the user must re-preview and confirm again.

### 3.1 Multi-turn conversation (server-side)

- Conversation history MUST be persisted server-side as a per-user chat thread
  keyed by `{user_id, tool_id}` (30-day TTL since last activity, and clear on
  user demand).
- The frontend renders the thread and sends only the newest user message to
  chat-first endpoints (no client-managed transcript rules that drift across
  endpoints).
- When calling the provider, the backend enforces prompt budgets
  deterministically (ADR-0052) using a sliding window:
  drop oldest turns first, and **never truncate** the system prompt.
- If the newest user message cannot fit together with the full system prompt
  and reserved output budget, fail with a user-actionable validation error and
  do not mutate the stored thread.

### 4) Observability + evaluation

- Log metadata only (template id, lengths, outcome, provider/model, latency if
  available).
- Never log prompt text, code text, conversation messages, or model outputs.
- Platform-only —full model response capture— is allowed **only** as an explicit debug
  mechanism when enabled by server config (default: OFF). Captures are written to
  artifact storage with TTL cleanup and are retrievable only via server filesystem access.
  When enabled, captures are written automatically on edit-ops generation and preview failures
  for all users (no per-request opt-in).
  (no tool-developer-facing API surface).
- Keep eval-only response metadata behind an admin-gated dev-only mode
  (existing `X-Skriptoteket-Eval` pattern).

## Consequences

### Positive

- Beginner-friendly entry point (—describe what you want—) without requiring
  region selection expertise.
- Deterministic, auditable changes via structured ops + diff preview.
- Lower risk of —AI did something surprising— due to explicit apply and easy
  undo.
- **Patch-only alignment**: Reduces model ambiguity (one way to edit) and leverages the strong diff-repair logic in the backend.

### Negative / trade-offs

- Requires new backend schema validation and failure-handling paths for model
  responses.
- Requires a reusable diff viewer component and a stronger preview/apply UX
  than the current edit MVP.
- Patch/anchor apply adds validation complexity and stricter failure cases
  (invalid hunks or ambiguous anchors must safe-fail).
- Limiting targets in v1 reduces capability (no multi-range or semantic
  refactors) but improves safety.

### Follow-ups (out of scope for this ADR)

- Multi-range operations, semantic refactors, or protected/locked regions.
- Shared conversations across users/maintainers.
- Metrics dashboards; only metadata logging is in scope.
