---
type: pr
id: PR-0034
title: "Editor AI: patch_lines encoding for edit-ops patch ops (parse_failed fix)"
status: done
owners: "agents"
created: 2026-01-16
updated: 2026-01-16
stories:
  - "ST-08-29"
tags: ["backend", "frontend", "editor", "ai", "protocol"]
acceptance_criteria:
  - "`POST /api/v1/editor/edit-ops` returns patch ops encoded as `patch_lines` (no `patch` string field) and backend parsing no longer fails due to literal newlines inside JSON strings."
  - "`POST /api/v1/editor/edit-ops/preview` and `/apply` accept `patch_lines` patch ops and preserve existing diff apply behavior (same bounded fuzz ladder, same error mapping)."
  - "Backend parser remains resilient when model output is wrapped in code fences and patch content includes backticks (no early fence termination)."
  - "OpenAPI + generated frontend types reflect the new patch op shape."
  - "Verification: `pdm run test`, `pdm run fe-type-check`, and `pdm run fe-test`."
---

## Problem

Edit-ops `parse_failed` happens when the model emits invalid JSON: a patch op encodes the unified diff as a single JSON
string (`patch`) but includes literal newlines inside that string. JSON parsers reject this as an invalid control
character, and the backend can’t recover any ops.

## Goal

- Switch patch op encoding to `patch_lines: string[]` so no JSON string ever needs embedded literal newlines.
- Preserve all existing diff sanitization and apply semantics (preview/apply and bounded fuzz behavior unchanged).
- Update OpenAPI + frontend types so the SPA can roundtrip ops through preview/apply.

## Non-goals

- Compatibility shims (no dual support for `patch` + `patch_lines`).
- Changes to the diff apply algorithm beyond joining `patch_lines` into a unified-diff string.
- Provider/model tuning beyond updating the system prompt schema.

## Implementation plan

1. Update the edit-ops system prompt (`editor_chat_ops_v1`) to require `patch_lines` and forbid `patch`.
2. Update the patch op schema in backend protocols + API models:
   - `EditOpsPatchOp.patch` → `EditOpsPatchOp.patch_lines`
   - `EditorEditOpsPatchOp.patch` → `EditorEditOpsPatchOp.patch_lines`
3. Reconstruct the unified diff string from `patch_lines` at the preview/apply boundary (before calling the diff applier).
4. Harden fenced-block extraction to avoid truncation when patch content contains ``` inside JSON strings.
5. Regenerate OpenAPI types and update any frontend code that assumes `patch`.
6. Update unit tests to use `patch_lines` everywhere.

Files touched:

- `docs/adr/adr-0051-chat-first-ai-editing.md`
- `docs/backlog/epics/epic-08-contextual-help-and-onboarding.md`
- `docs/backlog/prs/pr-0034-editor-ai-edit-ops-patch-lines-encoding.md`
- `docs/backlog/stories/story-08-29-ai-edit-ops-patch-lines-encoding.md`
- `docs/index.md`
- `src/skriptoteket/application/editor/system_prompts/editor_chat_ops_v1.txt`
- `src/skriptoteket/application/editor/edit_ops_payload_parser.py`
- `src/skriptoteket/application/editor/edit_ops_preview_handler.py`
- `src/skriptoteket/protocols/llm.py`
- `src/skriptoteket/web/api/v1/editor/models.py`
- `frontend/apps/skriptoteket/openapi.json` (generated)
- `frontend/apps/skriptoteket/src/api/openapi.d.ts` (generated)
- `tests/unit/application/test_editor_edit_ops_handler.py`
- `tests/unit/application/test_editor_edit_ops_preview_handler.py`
- `tests/unit/application/test_editor_edit_ops_preview_capture_on_error.py`

## Test plan

- Backend: `pdm run test`
- Frontend: `pdm run fe-type-check` and `pdm run fe-test`
- Manual: request edit-ops → preview → apply in the tool editor and confirm no `parse_failed` (record in `.agent/handoff.md`).

## Rollback plan

- Revert this PR and redeploy backend + SPA together.
