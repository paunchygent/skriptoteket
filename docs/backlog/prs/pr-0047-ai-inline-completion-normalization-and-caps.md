---
type: pr
id: PR-0047
title: "AI: inline completion normalization + token budgets"
status: in_progress
owners: "agents"
created: 2026-01-19
updated: 2026-01-21
stories:
  - "ST-08-33"
tags: ["backend", "ai"]
acceptance_criteria:
  - "Local FIM inline completions use `max_tokens=64` and keep the existing FIM prompt format."
  - "GPT-5 family inline completions (e.g. `gpt-5-nano`) use the delimiter prompt format via the OpenAI Responses API."
  - "GPT-5-nano inline completions use `max_output_tokens=64`, `reasoning.effort=minimal`, `text.verbosity=low`, `store=false`, `truncation=auto`."
  - "Inline completion normalization unwraps fenced/quoted output, drops obvious prefix/suffix echo (contiguous-echo heuristic), strips duplicate lines (>=12 non-whitespace chars), and returns empty when nothing usable remains."
  - "Inline completion normalization prevents cursor-boundary duplication by removing any overlap where the completion starts with the suffix of the provided prefix (e.g. no `def run_tooldef run_tool(...)`)."
  - "If upstream returns partial output with `finish_reason=length` / `finish_reason=incomplete`, we still normalize and return a best-effort insertion (it is not hard-discarded)."
  - "Inline completion responses may include `replace_suffix_chars` to replace a small right-side window when completing a partially typed token."
---

## Problem

Inline completions must be small and insert-ready. We currently see two classes of failures:

1) **Echo/duplication**: the model repeats large parts of the prefix/suffix, producing noisy insertions.
2) **Truncation handling**: OpenAI Responses can return `finish_reason=length` / `finish_reason=incomplete` while
   still providing useful partial output. Discarding these responses yields “no ghost text”.

## Goal

- Keep local **FIM** behavior stable and fast (`max_tokens=64`).
- Use the delimiter prompt format for GPT‑5 family completions, with a small but usable output cap
  (`max_output_tokens=64`).
- Apply a shared, deterministic normalization pass that removes duplicated context while still allowing
  best-effort partial inserts when the model hits the output cap.

## Non-goals

- Structured-output (Option C) inline completions.
- Streaming or UI changes.
- Provider selection/failover policy changes beyond token caps.

## Implementation plan

1. **Config + provider caps**
   - Ensure inline completions use `max_output_tokens=64` (shared cap across providers).
   - Ensure GPT‑5 family uses the delimiter prompt format via Responses API (no structured output path).
2. **Normalization (shared)**
   - Extend inline completion normalization to:
     - Strip fenced blocks / surrounding quotes.
     - Remove cursor-boundary overlap (completion starting with a suffix of the prefix; loop-safe).
     - Drop completion only when the contiguous-echo ratio is high (near-total echo or small completions with >=60% echoed lines).
     - Otherwise strip exact duplicate lines (>=12 non-whitespace chars) found in prefix/suffix.
     - Return empty if nothing remains after normalization.
   - Compute right-side replacement metadata for partial-token completions (`replace_suffix_chars`).
3. **Handler integration**
   - Apply normalization after provider parsing, for both local and remote responses.
   - If upstream is truncated (`finish_reason=length` / `finish_reason=incomplete`), still normalize and return
     best-effort output (log the truncation but don’t hard-discard).

## Validation checklist

- [x] **Unit/quality gates**:
  - [x] `pdm run lint`
  - [x] `pdm run typecheck`
  - [x] `pdm run test`
  - [x] `pdm run fe-test`
  - [x] `pdm run test tests/unit/application/test_editor_inline_completion_handler.py tests/unit/web/test_editor_inline_completion_api.py`
  - [x] `pdm run fe-test src/composables/editor/skriptoteketGhostText.spec.ts`
- [x] **Backend API path (app code, not harness)**:
  - [x] Login and call `POST /api/v1/editor/completions` (optionally with `X-Skriptoteket-Eval: 1`) using a real
    prefix/suffix captured from the editor.
  - [x] Confirm response is `200` and `completion` is non-empty for typical scenarios (even if
    `X-Skriptoteket-Eval-Outcome=truncated`).
  - [x] Confirm `completion` does **not** repeat the prefix tail at the cursor boundary (example failure:
    `def run_tooldef run_tool(...)`).
- [x] **Docker logs (source of truth)**:
  - [x] Confirm each request logs `ai_inline_completion_request` and then either:
    - [x] `ai_inline_completion_normalized` with `normalized_chars>0`, OR
    - [x] `ai_inline_completion_truncated` followed by `ai_inline_completion_normalized` (non-empty best-effort).
  - [x] Confirm `inline_completion_payload_shape` shows:
    - [x] `prompt_format="delimited"` for GPT‑5 family models
    - [x] `prompt_format="fim"` for local FIM completions
- [x] **End-to-end UX**:
  - [x] Ghost text appears in the Script Editor for `tool.py` while typing (not only after explicit actions).
  - [ ] (Optional) Run Playwright: `pdm run ui-editor-smoke` (requires escalated permissions).

### Validation notes

- Local (FIM, Vite `:5173` → backend `:8010`): `pdm run python -m scripts.diagnose_ghost_text --base-url http://127.0.0.1:5173 --tool-slug html-to-pdf-preview --cursor-anchor "if not html_sources:" --cursor-anchor-mode line --cursor-text "        return {" --cursor-delete-next-lines 7`
  → ghost text present; `cursor_overlap_chars=0` in `.artifacts/diagnose-ghost-text/result.json`. Log: `.artifacts/inline-completion-verify-local.log` correlation `d8d8efab-e169-4657-b35f-9b3c82a7d299` shows `prompt_format="fim"` and `ai_inline_completion_normalized` (`normalized_chars=325`, `prefix_overlap_chars=1`).
- GPT‑5 (Vite `:5174` → backend `:8011`): `pdm run python -m scripts.diagnose_ghost_text --base-url http://127.0.0.1:5174 --tool-slug html-to-pdf-preview --cursor-anchor "return _handle_preview(input_files=" --cursor-anchor-mode inline --cursor-text "" --cursor-delete-line-tail`
  → ghost text `input_files)` with `cursor_overlap_chars=0`. Log: `.artifacts/inline-completion-verify-gpt5.log` correlation `aff69a9e-de1b-4d32-86ca-259914328da6` shows `prompt_format="delimited"` and `ai_inline_completion_normalized` (`normalized_chars=12`, `prefix_overlap_chars=28`).
- UI + network capture via `pdm run python -m scripts.diagnose_ghost_text --base-url http://127.0.0.1:8001`
  (Playwright, real `/api/v1/editor/completions`); captured prefix `def run_tool`, completion starts with `(` and
  `cursor_overlap_chars=0` in `.artifacts/diagnose-ghost-text/result.json`.
- Tee'd backend log via uvicorn `:8002` with `LLM_COMPLETION_SYSTEM_PROMPT_MAX_TOKENS=2048` +
  Vite `:5173` → backend `:8002` in `.artifacts/inline-completion-verify-local.log`; log shows
  `inline_completion_payload_shape` `prompt_format="fim"` and `ai_inline_completion_request` with
  `system_prompt_tokens=1075`, `prefix_tokens=2016`, `suffix_tokens=512`, `prompt_tokens_total=3603`
  (correlation id `46a593de-db93-412e-952b-2bc065980e7f`), plus `ai_inline_completion_truncated` →
  `ai_inline_completion_normalized` (`provider_ms ~8–9s`).
- GPT‑5 (Vite `:5174` → backend `:8003`): `pdm run python -m scripts.diagnose_ghost_text --base-url http://127.0.0.1:5174 --tool-slug html-to-pdf-preview --cursor-anchor "if not html_sources:" --cursor-anchor-mode line --cursor-text "        return {" --cursor-delete-next-lines 7`
  → ghost text present; `cursor_overlap_chars=0` in `.artifacts/diagnose-ghost-text/result.json`. Log:
  `.artifacts/inline-completion-verify-gpt5.log` correlation `79bbf574-96d5-4020-af0d-f9ac36b3af5a` shows
  `prompt_format="delimited"` and `ai_inline_completion_request` with `system_prompt_tokens=875`,
  `prefix_tokens=1904`, `suffix_tokens=512`, `prompt_tokens_total=3291`.
- Inline-hole diagnostic (long script, anchor mid-file) used new flags:
  - Local: `pdm run python -m scripts.diagnose_ghost_text --base-url http://127.0.0.1:8002 --tool-slug html-to-pdf-preview --cursor-anchor "render_options: dict[str, object] = " --cursor-anchor-mode inline --cursor-text "{" --cursor-delete-line-tail`
    → `suffix_tokens=512`, but normalized completion dropped as contiguous echo (correlation id `f7beb17a-1e9a-46ed-8e8e-c88beeb70645`, `provider_ms ~6.8s`).
  - GPT‑5: same command with provider preference set to `external` → `prompt_format="delimited"`, `suffix_tokens=512`,
    normalized completion dropped as contiguous echo (correlation id `a14dc765-61f6-496d-b797-e6b379021709`,
    `provider_ms ~4.2s`). See `.artifacts/inline-completion-verify.log` + captures under
    `/tmp/skriptoteket/artifacts/llm-captures/inline_completion_response/`.
- Inline-hole diagnostic (obvious completion, long script):
  - Local: `pdm run python -m scripts.diagnose_ghost_text --base-url http://127.0.0.1:8005 --tool-slug html-to-pdf-preview --cursor-anchor "return _handle_preview(input_files=" --cursor-anchor-mode inline --cursor-text "" --cursor-delete-line-tail`
    → completion `input_files=input_files,\n)` with ghost text present; `prompt_format="fim"` and `normalized_chars=30`
    (correlation id `aa95da5b-c4de-4980-8361-b2487a75dc37`, `provider_ms ~1.1s`).
  - GPT‑5: same command with provider preference `external` → completion `input_files)` with ghost text present;
    `prompt_format="delimited"`, `normalized_chars=12` (correlation id `d4f15f1b-b903-4f9b-a478-3557f90efeb8`,
    `provider_ms ~1.5s`).
- Inline-hole diagnostics (targeted anchors, long script, base-url `http://127.0.0.1:8000` local + `http://127.0.0.1:5173` GPT proxy):
  - `render_options: dict[str, object] = {` → Local returned unrelated block; GPT‑5 returned unrelated block (cache/weasyprint).
  - `if not html_sources:` → Local returned unrelated block; GPT‑5 returned empty (likely contiguous echo dropped).
  - `_notice(level, f"{ok_count} PDF skapades` → Local returned unrelated block; GPT‑5 returned empty.

## Test plan

- Unit tests for normalization:
  - Cursor-boundary overlap removal (prefix tail duplicated at completion start).
  - 2-line contiguous echo drop.
  - Line-level de-dup with >=12-char threshold.
  - Fenced/quoted output.
  - Empty after normalization.
- Harness validation:
  - Run local FIM baseline at 64 tokens.
  - Run GPT-5-nano delimiter at 64 tokens.

## Rollback plan

- Revert the truncation-handling change (resume hard-discard on `finish_reason=length|incomplete`) and restore
  the prior token caps.
