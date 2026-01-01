---
type: reference
id: REF-ai-edit-suggestions-kb-context-budget-blocker
title: "AI Edit Suggestions Context Budget Blocker"
status: active
owners: "skriptoteket"
created: 2025-12-31
topic: "ai"
links:
  - docs/backlog/sprints/sprint-2026-01-05-tool-editor-vertical-slice.md
  - docs/backlog/epics/epic-08-contextual-help-and-onboarding.md
  - docs/backlog/stories/story-08-14-ai-inline-completions.md
  - docs/backlog/stories/story-08-16-ai-edit-suggestions.md
  - docs/backlog/stories/story-08-17-tabby-edit-suggestions-ab-testing.md
---

## Executive Summary

ST-08-16 edit suggestions currently return **500 Internal Server Error** because the request payload exceeds the LLM context window. The backend loads a **human-oriented 900 LoC knowledge base** (`docs/reference/ref-ai-script-generation-kb.md`) and sends it verbatim as the system prompt. Combined with the user content (instruction + prefix/selection/suffix) and the reserved output tokens (`max_tokens`), the request can exceed llama.cpp’s context limit (`n_ctx=4096`). This is a blocker for real pipeline validation and must be addressed with an **LLM-optimized KB + enforced context budget**.

## Scope & Links

- Sprint: `docs/backlog/sprints/sprint-2026-01-05-tool-editor-vertical-slice.md`
- Epic: `docs/backlog/epics/epic-08-contextual-help-and-onboarding.md`
- Stories:
  - `docs/backlog/stories/story-08-14-ai-inline-completions.md`
  - `docs/backlog/stories/story-08-16-ai-edit-suggestions.md`
  - `docs/backlog/stories/story-08-17-tabby-edit-suggestions-ab-testing.md`

## Current Behavior (Observed)

- `POST /api/v1/editor/edits` returns **500** when the LLM is enabled and reachable.
- llama.cpp responds **400 exceed_context_size_error** when the system prompt includes the full KB.
- Because `httpx.HTTPStatusError` is not handled by the edit handler, the backend raises an unhandled exception and returns 500.
 - In dev, the UI uses the **host** backend (via Vite proxy to `127.0.0.1:8000`), so container logs do not show the 500.

## Root Causes

1. **Oversized KB prompt**
   `load_kb_text()` loads the full `ref-ai-script-generation-kb.md` (human-readable, ~900 LoC). The resulting system prompt is ~26k characters before any user context, which exceeds llama.cpp’s 4096-token window.

2. **No context budget enforcement**
   The edit handler passes full KB + prefix + selection + suffix without a token/char budget. There is no truncation strategy that accounts for the model’s window. Additionally, llama.cpp enforces `prompt_tokens + max_tokens <= n_ctx`, so the configured output cap directly reduces the available prompt budget.

3. **HTTPStatusError not handled**
   `EditSuggestionHandler` catches only `httpx.TimeoutException` and `httpx.RequestError`. `HTTPStatusError` (400 from upstream) is not caught, producing a 500.

## Impact

- Blocks real pipeline testing for ST-08-16.
- Produces user-facing 500 errors for “Föreslå ändring”.
- Prevents iterative prompt tuning because failures are systemic, not prompt-specific.

## Dev Log Location (Succinct)

- If the UI is running via Vite (`pnpm … dev`), look at the **host** backend logs from `pdm run dev`
  (the Vite proxy targets `127.0.0.1:8000`). Container logs will only show traffic if the UI points
  at the container port directly.

## Decision Needed

**Adopt an LLM-optimized KB and enforce a strict context budget in the backend.**
We control the backend and must cap the prompt to fit the current model context window.

## Clarifications (Terminology)

- **Context window (`n_ctx`)**: the model/server’s maximum total tokens for **prompt + generated tokens** (llama.cpp).
- **`max_tokens` / `max_new_tokens`**: the cap on **generated tokens**; it is **not** the context window, but it consumes budget because `prompt + max_tokens` must fit in the window.
- **Chat roles**: with `/v1/chat/completions`, system/developer messages are still normal input tokens and count toward the same context window; the benefit is *instruction separation and priority*, not “free tokens”.

## Options Considered (Decision Tree)

### Option 1: Keep llama.cpp `n_ctx=4096` and enforce a strict backend prompt budget (**chosen**)

- Use dedicated **system prompt templates** (repo-owned, no YAML frontmatter / dev prose) for system prompt injection.
- Enforce a deterministic prompt budget and trim user context around the cursor/selection.

Pros:
- Fixes overflow at the source without requiring more memory/KV cache.
- Keeps latency predictable (important for inline completions).
- Works across providers (the budgeting logic is backend-owned).

Cons:
- Requires token-aware budgeting (or a conservative approximation) in the backend.

### Option 2: Increase llama.cpp context window (`n_ctx`) and still budget

Pros:
- Retains more prefix/suffix/selection before trimming.

Cons:
- Higher KV cache cost → increased latency and memory pressure; can violate the 2–3s ghost-text UX target.
- Still needs budgeting because user code can always exceed any fixed `n_ctx`.

### Option 3: Keep the full human KB and do retrieval/summarization per request

Pros:
- Potentially best quality per token (only relevant KB sections).

Cons:
- Most complex; higher risk and harder to validate; still requires budgeting.

## Concrete Prompt Budget Split (llama.cpp `n_ctx=4096`)

These are **target token budgets** for our current handler shapes. They assume:
- a safety margin for chat formatting + provider variability
- output tokens are reserved up front
- we trim suffix first, then prefix, and reduce KB last (if needed)

### Inline completions (ghost text) — `InlineCompletionHandler`

Shape:
- System: “completion assistant rules” + KB
- User: FIM prompt (`<|fim_prefix|>{prefix}<|fim_suffix|>{suffix}<|fim_middle|>`)

Target budgets:
- Context window (`n_ctx`): 4096
- Reserved output tokens (`max_tokens`): 256
- Safety margin (chat wrapping, variance): 256
- System prompt (rules + **LLM KB**): 1024
- User prompt budget: 2560
  - Prefix: 2048
  - Suffix: 512

### Edit suggestions — `EditSuggestionHandler`

Shape:
- System: “editing assistant rules” + KB
- User: instruction + selection + prefix + suffix (plain text sections)

Target budgets:
- Context window (`n_ctx`): 4096
- Reserved output tokens (`max_tokens`): 512
- Safety margin (chat wrapping, variance): 256
- System prompt (rules + **LLM KB**): 1024
- User prompt budget: 2304
  - Instruction: 128
  - Selection (keep intact, trim last): 896
  - Prefix: 1024
  - Suffix: 256

Notes:
- If selection alone exceeds its budget, we either (a) hard-trim it or (b) fail gracefully with empty suggestion.
- For edits, reducing `max_tokens` is an emergency lever to recover prompt space, but the primary fix is budgeting + LLM KB.

## Proposed Plan (Persisted Between Sessions)

### 1) Introduce an LLM-optimized KB artifact

- Use dedicated system prompt templates:
  - Inline: `src/skriptoteket/application/editor/system_prompts/inline_completion_v1.txt`
  - Edits: `src/skriptoteket/application/editor/system_prompts/edit_suggestion_v1.txt`
- Keep it **short, structured, and instruction-oriented**:
  - Bullet rules, short examples, no narrative prose.
  - Prioritize constraints the model must follow.
  - Target size: **< 1–2k tokens**.

### 2) Add a context budget + truncation strategy

- Define a **max prompt token budget** (configurable) that accounts for:
  - system prompt (KB)
  - instruction
  - selection
  - prefix/suffix
  - expected completion tokens
- Enforce a deterministic budget:
  - Always keep selection intact.
  - Truncate prefix/suffix aggressively.
  - Optionally trim KB further if still over budget.

### 3) Handle upstream “context too large” gracefully

- Treat `httpx.HTTPStatusError` with “exceed_context_size_error” as a **non-fatal** failure:
  - Return `{ enabled: true, suggestion: "" }`
  - Log the over-budget event with sizes (no code content).

### 4) Track the budget in tests

- Add a unit test that asserts:
  - Large KB + selection does **not** cause a 500.
  - Handler returns an empty suggestion when the prompt would exceed budget.

## Non-Goals (Explicit)

- No Tabby integration here (defer to ST-08-17 / follow-up story).
- No prompt A/B testing in ST-08-16 (handled in ST-08-17).

## Next Actions (Sequenced)

1. Confirm and freeze the Option 1 budget split (this doc) for `n_ctx=4096`.
2. Switch backend prompt injection to the system prompt templates:
   - `src/skriptoteket/application/editor/system_prompts/inline_completion_v1.txt`
   - `src/skriptoteket/application/editor/system_prompts/edit_suggestion_v1.txt`
3. Add config settings for model context window + prompt budget + safety margin.
4. Implement deterministic truncation in edit/completion handlers (budget-first; selection preserved).
5. Add HTTPStatusError handling and a targeted unit test for the over-budget path.
6. Re-test the real pipeline with llama.cpp.

## Tracking (Status Log)

- 2025-12-31: Decision taken — Option 1 (LLM KB + strict prompt budgeting; keep llama.cpp `n_ctx=4096`).
- 2025-12-31: Documented concrete budget splits for inline + edit handlers.
