---
type: runbook
id: RUN-editor-ai-pipeline
title: "Runbook: Editor AI pipeline (completion/chat/edit-ops)"
status: active
owners: "agents"
created: 2026-01-21
updated: 2026-01-21
system: "skriptoteket"
---

Use this runbook when you need to understand, debug, or extend the editor AI features:

- Inline completions ("ghost text")
- Editor chat ("Kodassistenten")
- Edit-ops (patch-only diffs + preview/apply)

This document is intentionally code-pointer heavy for fast onboarding.

## Quick mental model

There are two big phases in the editor AI pipeline:

1. **Generate suggestion** (LLM call)
2. **Validate/apply safely** (deterministic server-side logic)

For edit-ops, phase (2) is the critical safety layer: we do not trust model line numbers or
perfect formatting.

## Endpoints and flows

### Inline completion (ghost text)

- Frontend triggers `POST /api/v1/editor/completions`
- Backend calls the configured LLM provider (Chat Completions or Responses)
- Backend returns a completion string plus normalization metadata

Key implementation files:

- Backend handler: `src/skriptoteket/application/editor/completion_handler.py`
- Web API: `src/skriptoteket/web/api/v1/editor/completions.py`
- Frontend composable: `frontend/apps/skriptoteket/src/composables/editor/skriptoteketGhostText.ts`
- Diagnose script (Playwright): `scripts/diagnose_ghost_text.py`

### Editor chat

- Frontend opens the assistant drawer and streams messages
- Backend streams deltas via SSE and persists turns/messages in tool session storage

Key implementation files:

- Chat providers: `src/skriptoteket/infrastructure/llm/openai/chat_stream_provider.py`
- Web API models: `src/skriptoteket/web/api/v1/editor/models.py`

### Edit-ops (patch-only)

- Frontend triggers `POST /api/v1/editor/edit-ops` to get patch ops
- Backend returns `ops[]` (patch-only unified diffs; targets virtual files)
- Frontend triggers `POST /api/v1/editor/edit-ops/preview` to apply ops to current virtual files
- If preview requires confirmation, frontend can call `POST /api/v1/editor/edit-ops/apply`

Key implementation files:

- LLM prompt/ops parsing: `src/skriptoteket/application/editor/system_prompts/editor_chat_ops_v1.txt`
- Preview/apply orchestration: `src/skriptoteket/application/editor/edit_ops_preview_handler.py`
- Unified diff normalization: `src/skriptoteket/infrastructure/editor/unified_diff/normalize.py`
- Unified diff apply/matching: `src/skriptoteket/infrastructure/editor/unified_diff/apply_patch.py`
- Diagnose script (Playwright): `scripts/diagnose_edit_ops.py`

## LLM routing: Responses vs Chat Completions (and local llama)

We use different upstream APIs depending on the configured base URL:

- **OpenAI base URL** → `/v1/responses` (Responses API)
- **Local llama server** → `/v1/chat/completions` (Chat Completions-compatible API, supports `grammar`)

Routing logic:

- `src/skriptoteket/infrastructure/llm/openai/common.py`:
  - `is_openai_api_base_url()`
  - `is_local_llama_server()`
- Providers:
  - `src/skriptoteket/infrastructure/llm/openai/inline_completion_provider.py`
  - `src/skriptoteket/infrastructure/llm/openai/chat_ops_provider.py`
  - `src/skriptoteket/infrastructure/llm/openai/chat_stream_provider.py`

Structured output + content item gotchas are documented in:

- `docs/runbooks/runbook-openai-responses-api.md`

## Captures, correlation IDs, and debugging

### Correlation IDs

Most editor API calls include an `X-Correlation-ID` header. When capture-on-error is enabled, the
backend writes LLM and preview/apply error captures under:

- `.artifacts/llm-captures/<kind>/<correlation-id>/capture.json`

Common kinds:

- `chat_ops_response` (LLM call for edit-ops ops generation)
- `edit_ops_preview_failure` (patch prepare/apply failures during preview)

### Fast inspection

- Find a correlation ID:

```bash
rg -n -S "<correlation-id>" .artifacts/llm-captures
```

- Summarize a capture:

```bash
jq '{captured_at, kind, payload: {provider, outcome, parse_ok, ops_count, error_kind, errors, upstream_error}}' \
  .artifacts/llm-captures/<kind>/<correlation-id>/capture.json
```

## Common failure modes (and where to look)

### 1) Responses API 400s (no ops / invalid ops)

Symptom: `chat_ops_response` has `outcome: invalid_ops` with `upstream_error` 400.

Common root causes:

- Wrong `text.format` schema shape for Responses (must include `name` at `text.format.name`)
- Wrong content item `type` for assistant history (`output_text` vs `input_text`)

See:

- `docs/runbooks/runbook-openai-responses-api.md`
- `src/skriptoteket/infrastructure/llm/openai/payloads.py`
- `src/skriptoteket/infrastructure/llm/openai/types.py`

### 2) Edit-ops patch preview failures ("Patchen kunde inte appliceras")

Symptom: `edit_ops_preview_failure` with `error_kind: patch_apply_failed`.

Common root causes:

- Patch context does not match the current file (file changed, or the model edited wrong region)
- Hunk header ranges are wrong (`@@ -old_start,...`) and the apply search window was too small

Relevant code:

- Deterministic header repairs: `src/skriptoteket/infrastructure/editor/unified_diff/normalize.py`
- Apply search/window: `src/skriptoteket/infrastructure/editor/unified_diff/apply_patch.py`
- Preview retry with wide search: `src/skriptoteket/application/editor/edit_ops_preview_handler.py`

## Repro scripts (Playwright)

These scripts create realistic “edit holes” in the CodeMirror editor and exercise the real UI +
API calls end-to-end. Artifacts are written under `.artifacts/`.

- Inline completion:

```bash
pdm run python -m scripts.diagnose_ghost_text --tool-slug <slug> --cursor-anchor "<...>" --cursor-delete-next-lines 7
```

- Edit-ops:

```bash
pdm run python -m scripts.diagnose_edit_ops --tool-slug <slug> --cursor-anchor "<...>" --cursor-delete-next-lines 7
```

## Rollback

- If a change breaks editor AI behaviors, first disable remote fallback and/or switch to the known-good
  local provider in `.env` while you investigate.
- For structured output issues, prefer reverting *only* the payload shaping logic for the affected API
  (Responses vs Chat Completions) rather than touching prompts or diff application logic.
