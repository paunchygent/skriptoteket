---
type: story
id: ST-08-29
title: "AI edit ops: patch_lines encoding for patch ops (avoid parse_failed)"
status: done
owners: "agents"
created: 2026-01-16
updated: 2026-01-16
epic: "EPIC-08"
acceptance_criteria:
  - "Given `POST /api/v1/editor/edit-ops` succeeds upstream, when the model returns patch ops, then the backend parses the response into ops without relying on JSON-escaped newlines inside a single `patch` string (uses `patch_lines`)."
  - "Given a patch op contains diff lines that include backticks (e.g. a Python string containing ```text fences), when the model response is parsed, then fenced extraction does not truncate the JSON payload."
  - "Given the frontend receives patch ops from `POST /api/v1/editor/edit-ops`, when it calls `POST /api/v1/editor/edit-ops/preview` and `/apply`, then the patch is reconstructed from `patch_lines` and preview/apply behavior remains unchanged."
  - "Given the model returns an invalid payload (missing required fields or wrong patch encoding), when the backend processes the response, then it safe-fails with `ops=[]` and a user-actionable assistant_message (no crashes)."
ui_impact: "Yes (edit-ops preview/apply request/response schema changes)"
data_impact: "No (protocol change only)"
---

## Context

Real-world edit-ops failures show `parse_failed` outcomes where the model emits a JSON `"patch"` string containing literal
newlines (invalid JSON), which prevents the backend from parsing any ops (`ops_count=0`).

To remove this failure mode without adding compatibility shims, patch ops switch to a `patch_lines: string[]` encoding.
Each unified-diff line becomes a separate JSON string element, eliminating the need for the model to escape newlines.

## Notes

- No compatibility/migration period: the patch op encoding changes as a breaking schema update; deployments must ship
  backend + SPA together.
- Backend continues to normalize/sanitize diffs and apply them using the existing bounded fuzz ladder.

## Implementation (done)

- Prompt: `patch_lines` required for patch ops (`src/skriptoteket/application/editor/system_prompts/editor_chat_ops_v1.txt`).
- Protocol + API schema: patch ops use `patch_lines` (`src/skriptoteket/protocols/llm.py`,
  `src/skriptoteket/web/api/v1/editor/models.py`).
- Preview/apply: reconstruct unified diff from `patch_lines` before apply (`src/skriptoteket/application/editor/edit_ops_preview_handler.py`).
- Parser hardening: fenced extraction is line-anchored to avoid truncation when patch content contains ``` (`src/skriptoteket/application/editor/edit_ops_payload_parser.py`).
- Frontend OpenAPI types regenerated (`frontend/apps/skriptoteket/openapi.json`,
  `frontend/apps/skriptoteket/src/api/openapi.d.ts`).

Verification:

- `pdm run test`
- `pdm run fe-gen-api-types`
- `pdm run fe-type-check`
- `pdm run fe-test`
- Manual: `POST /api/v1/editor/edit-ops` returned a patch op with `patch_lines` (no parse_failed).
