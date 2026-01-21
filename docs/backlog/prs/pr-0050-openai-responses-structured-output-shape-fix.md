---
type: pr
id: PR-0050
title: "AI: fix OpenAI Responses structured output payload shape + add editor AI pipeline runbook"
status: done
owners: "agents"
created: 2026-01-21
updated: 2026-01-21
stories:
  - "ST-08-31"
tags: ["backend", "ai", "openai", "docs"]
acceptance_criteria:
  - "Chat-ops using OpenAI Responses API includes a valid `text.format` with required `name` and `schema` fields."
  - "Assistant history in Responses requests is encoded as `output_text` (not `input_text`)."
  - "Runbook documents Responses vs Chat Completions structured output shapes and message content item types."
  - "A dedicated runbook exists for the editor AI pipeline (completion/chat/edit-ops) and is indexed in docs."
  - "Unit tests cover Responses payload shaping and prevent regressions."
---

## Problem

Our chat-ops fallback path (OpenAI Responses API) can fail with a hard 400 when we send structured
output configuration in the wrong shape, producing captures like:

- `missing_required_parameter: text.format.name`

This results in `invalid_ops` (no ops returned) which then breaks edit-ops regeneration.

Root cause: we accidentally reused the Chat Completions `response_format` JSON schema shape inside
the Responses `text.format` field.

## Goal

- Ensure all Requests to `/v1/responses` include valid `text.format` when structured output is used.
- Keep Responses vs Chat Completions types clearly separated and documented in code (with canonical
  doc references) to avoid repeat mixups.
- Add onboarding runbook(s) for quick debugging of completion/chat/edit-ops failures via correlation IDs.

## Non-goals

- Changing prompts or UX behavior.
- Migrating local llama-server (Chat Completions-compatible) payloads.
- Rewriting edit-ops diff normalization/apply logic.

## Implementation plan

1. **Types: separate Responses vs Chat Completions**
   - Define explicit Responses structured output types (distinct from Chat `response_format`).
   - Add docstrings linking canonical API docs.

2. **Constants: split Chat vs Responses shapes (Option B)**
   - Define explicit constants for each API:
     - Chat Completions: `*_CHAT_RESPONSE_FORMAT` (for `response_format`)
     - Responses API: `*_RESPONSES_TEXT_FORMAT` (for `text.format`)
   - Do not reuse the same dict for both endpoints.

3. **Payload shaping: validate before sending (fail fast)**
   - Ensure `/v1/responses` payload builder only accepts the Responses `text.format` shape
     (`{"type":"json_schema","name":...,"schema":...}`).
   - Reject Chat `response_format` shapes when passed into Responses payloads (raise a clear in-process error)
     to avoid hard 400s from OpenAI.

4. **Tests**
   - Assert `text.format.name` and `text.format.schema` are present for Responses payloads.
   - Ensure chat-ops provider uses `text.format` (not `response_format`) for OpenAI.

5. **Docs**
   - Update `RUN-openai-responses-api` with a “Structured Output: Chat vs Responses” section.
   - Add `RUN-editor-ai-pipeline` runbook for onboarding + debugging (code pointers + capture workflow).
   - Add new runbook to `docs/index.md`.

## Review checklist

- [x] `text.format.name` is present in Responses payloads (no more 400 missing required parameter)
- [x] Responses message history uses `output_text` for assistant turns
- [x] No behavioral changes in local llama-server paths
- [x] New runbooks are accurate and linked from `docs/index.md`
- [x] Unit tests pass
- [x] Lint + docs contract validation pass

## Test plan

- `pdm run pytest -q tests/unit/infrastructure/llm/test_openai_payloads.py tests/unit/infrastructure/llm/test_openai_chat_ops_provider_grammar.py`
- `pdm run lint`
- `pdm run docs-validate`

Optional manual verification (dev):

- Trigger edit-ops with OpenAI base URL and confirm ops are returned (no `invalid_ops` captures).
- Verify correlation-ID captures for chat-ops no longer contain `text.format.name` 400s.

## Rollback plan

- Revert the Responses payload normalization (and keep the older behavior) to restore previous payloads.
- If needed, temporarily disable structured output for Responses (remove `text.format`) while keeping the
  Responses endpoint wiring intact.
