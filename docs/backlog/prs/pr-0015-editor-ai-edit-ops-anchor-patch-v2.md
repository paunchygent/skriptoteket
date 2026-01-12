---
type: pr
id: PR-0015
title: "Editor AI: anchor/patch-based edit ops v2 (ST-08-24)"
status: done
owners: "agents"
created: 2026-01-10
updated: 2026-01-11
stories:
  - "ST-08-24"
tags: ["backend", "frontend", "editor", "ai", "diff"]
acceptance_criteria:
  - "Edit-ops supports patch/anchor targets per ADR-0051 and rejects ambiguous or invalid ops safely."
  - "Diff preview and apply use the same patch/anchor application helper and remain atomic/undoable."
  - "OpenAPI + generated frontend types reflect the v2 op shapes."
---

## Problem

Cursor/selection-only ops lead to surprising inserts (often at the top of the file) when the user has not explicitly
placed a cursor or selection. This does not match expected coding-assistant behavior.

## Goal

Add a v2 edit-ops protocol that supports anchor/patch-based targeting and a strict, deterministic apply pipeline for
preview + apply. Maintain existing v1 behavior for explicit selection/cursor edits.

## Non-goals

- No semantic refactor engine or multi-range operations.
- No new editor UI surfaces beyond updating the existing diff preview/apply flow.
- No new persistence tables.

## Related work

- Follow-up hardening: `docs/backlog/prs/pr-0016-editor-ai-edit-ops-v2-hardening.md`

## Implementation plan

1) **Contracts + OpenAPI**
   - Extend edit-ops schema to add `patch` ops and `anchor` targets.
   - Define anchor payload fields and validation rules in API models + protocols.
   - Regenerate `frontend/apps/skriptoteket/src/api/openapi.d.ts`.

2) **Prompt + parsing**
   - Add a new chat-ops prompt template (v2) that instructs patch/anchor outputs when no selection/cursor is present.
   - Update the handler to validate patch/anchor outputs and safe-fail on invalid payloads.

3) **Frontend apply pipeline**
   - Extend `applyEditOpsToVirtualFiles` to apply patch/anchor ops deterministically.
   - Use strict patch application (all hunks must match) and explicit anchor matching (single match only).
   - Keep atomic apply + undo behavior from ST-08-22.

4) **Preview + UX guardrails**
   - Preview uses the same apply helper as apply.
   - If patch/anchor application fails, surface a clear error and offer Regenerate.

5) **Tests**
   - Unit tests for patch/anchor application helper (success, mismatch, ambiguity).
   - Update edit-ops handler tests for patch/anchor validation and safe-fail behavior.

## Test plan

- `pdm run pytest tests/unit/application/test_editor_edit_ops_handler.py -q`
- `pdm run fe-test` (focus on `editOps.spec.ts`)
- Manual: request edit without selection/cursor → preview → apply → undo.

## Rollback plan

Revert the PR. No migrations or data changes are introduced.
