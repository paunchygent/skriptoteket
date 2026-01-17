---
type: pr
id: PR-0035
title: "Editor AI: patch-only strict GBNF grammar for edit-ops (llama.cpp parse_failed hardening)"
status: done
owners: "agents"
created: 2026-01-16
updated: 2026-01-16
stories:
  - "ST-08-29"
tags: ["backend", "editor", "ai", "llama", "protocol"]
acceptance_criteria:
  - "Given the chat-ops provider is llama.cpp (`llama-server`), when the backend calls `/v1/chat/completions`, then it supplies a patch-only strict GBNF grammar so responses are syntactically valid JSON matching the edit-ops patch-only schema."
  - "Given the model emits unified diff hunk lines (e.g. `@@ ... @@`), when encoded in `patch_lines`, then JSON parsing no longer fails due to unquoted diff lines or code fences."
  - "Verification: `pdm run test`."
---

## Problem

Follow-up to PR-0034 (`patch_lines` encoding): we still observe `parse_failed` when the model emits malformed JSON (e.g.
an unquoted unified-diff hunk header line inside the `patch_lines` array, or leading code fences). This failure happens
before Pydantic validation, so the backend cannot recover any ops.

## Goal

- Constrain llama.cpp (`llama-server`) edit-ops responses at decode time so they are valid JSON matching the patch-only
  schema.
- Keep the change scoped to the edit-ops LLM parsing pipeline (no UI/protocol behavior changes beyond preventing invalid
  JSON).

## Non-goals

- Changing edit-ops op semantics (still patch-only).
- Adding a schema migration/dual support rollout.
- Applying grammars to non-llama providers (OpenAI).

## Implementation plan

1. Add a patch-only strict GBNF grammar that matches the edit-ops response schema.
2. Attach the grammar to llama.cpp chat-ops requests via the OpenAI-compatible `grammar` field (only when the upstream
   base URL uses the llama-server port).
3. Add unit tests that assert the chat-ops provider includes/omits the grammar correctly.
4. Update ADR-0051 to document constrained decoding for llama.cpp as part of the patch-only edit-ops workflow.

Files touched:

- `docs/adr/adr-0051-chat-first-ai-editing.md`
- `docs/backlog/prs/pr-0035-editor-ai-edit-ops-gbnf-patch-only-grammar.md`
- `src/skriptoteket/infrastructure/llm/openai/chat_ops_provider.py`
- `src/skriptoteket/infrastructure/llm/openai/common.py`
- `src/skriptoteket/infrastructure/llm/openai/grammars.py`
- `tests/unit/infrastructure/llm/test_openai_chat_ops_provider_grammar.py`

## Test plan

- `pdm run test`
- Manual: trigger `POST /api/v1/editor/edit-ops` on llama-server and confirm response content is a raw JSON object (no
  fences) and backend no longer returns “Jag kunde inte skapa ett giltigt ändringsförslag. Försök igen.”

## Rollback plan

- Revert this PR. The system falls back to prompt-only compliance and post-parse Pydantic validation.
