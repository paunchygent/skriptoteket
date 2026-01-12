---
type: pr
id: PR-0017
title: "AI provider: GPT-5 config support + remove legacy edit suggestions"
status: done
owners: "agents"
created: 2026-01-11
updated: 2026-01-11
stories:
  - "ST-08-25"
tags: ["backend", "frontend", "ai", "cleanup"]
acceptance_criteria:
  - "Legacy edit suggestion endpoint and dead UI/client code are removed (`/api/v1/editor/edits`, `EditorEditSuggestionPanel.vue`, `useEditorEditSuggestions`)."
  - "GPT-5-family requests support `reasoning_effort` and use `max_completion_tokens` for `gpt-5.2` and `gpt-5-nano`, without sending `temperature`/`max_tokens`."
  - "OpenAPI schema and generated TS types no longer include the removed endpoint/types."
---

## Problem

We have an unused legacy edit-suggestion UI/API path that adds confusion alongside the chat-first edit-ops flow.
We also need correct GPT-5 request shaping (`reasoning_effort`, `max_completion_tokens`) for tiered OpenAI models.

## Goal

- Remove the legacy edit suggestions endpoint and dead frontend code.
- Make GPT-5 model requests correct and configurable.

## Non-goals

- Provider failover / load shedding between llama.cpp and OpenAI (planned follow-up).
- UX changes to the chat drawer or edit-ops flow.

## Follow-up cleanup plan (non-runtime references)

The endpoint `/api/v1/editor/edits` is removed from runtime code + OpenAPI, but some historical scripts/docs still
mention it. Plan a small follow-up PR to avoid confusion:

1. Scripts:
   - Delete or update obsolete Playwright + prompt-eval harness bits that still target `/api/v1/editor/edits`:
     - `scripts/playwright_st_08_16_ai_edit_suggestions_e2e.py`
     - `scripts/ai_prompt_eval/fixture_bank.py` (remove `EditSuggestionFixture` if unused)
     - `scripts/ai_prompt_eval/run_live_backend.py` (remove `/edits` path)
2. Docs/stakeholder artifacts:
   - Update docs that describe the legacy endpoint to either:
     - remove the mention, or
     - explicitly mark it as removed and point to chat-ops (`/api/v1/editor/edit-ops`) instead.
     Candidates (from `rg "/api/v1/editor/edits"`):
     - `docs/reference/ref-tool-editor-framework-codemap.md`
     - `docs/reference/reports/ref-ai-edit-suggestions-kb-context-budget-blocker.md`
     - `stakeholders/tooleditor_flow.html`
3. Acceptance check:
   - `rg -n "/api/v1/editor/edits" scripts docs stakeholders` should only match explicitly historical notes (if any),
     and no runnable script should call the removed endpoint.

## Implementation plan

1. Backend: remove `/api/v1/editor/edits` endpoint + handler/provider/config surface.
2. Frontend: remove unused edit suggestion panel + composable + tests.
3. Provider: add per-profile `*_REASONING_EFFORT` settings and pass them; ensure GPT-5-family uses
   `max_completion_tokens` and omits unsupported sampling params.
4. Regenerate OpenAPI schema + TypeScript types.
5. Update ADR note(s) to clarify the removal and avoid future confusion.

## Test plan

- `pdm run pytest tests/unit -q`
- `pdm run fe-test`
- `pdm run fe-gen-api-types`

## Rollback plan

- Revert this PR; no data migrations are involved.
