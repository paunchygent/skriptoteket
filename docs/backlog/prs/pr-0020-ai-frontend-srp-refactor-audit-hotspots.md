---
type: pr
id: PR-0020
title: "AI frontend: SRP refactor audit follow-ups (editor AI hotspots)"
status: ready
owners: "agents"
created: 2026-01-11
updated: 2026-01-11
stories:
  - "ST-08-14"
  - "ST-08-20"
  - "ST-08-21"
  - "ST-08-22"
  - "ST-08-23"
  - "ST-08-24"
  - "ST-08-25"
  - "ST-08-26"
  - "ST-08-27"
tags: ["frontend", "ai", "refactor", "srp", "testing"]
links: ["EPIC-08"]
acceptance_criteria:
  - "Editor AI UI + composables follow SRP boundaries: API calls/helpers/state are separated and easier to test."
  - "No Vue SFC touched in this PR exceeds 500 LoC (per `.agent/rules/045-huleedu-design-system.md`)."
  - "AI edit-ops composable is split into smaller modules/composables (request/preview/apply/undo helpers + API client), without behavior changes."
  - "AI chat composable is split into smaller modules (SSE streaming client + reducer/state + API helpers), without behavior changes."
  - "AI-related test files stay <400–500 LoC (per `.agent/rules/070-testing-standards.md`)."
  - "`pdm run fe-test` passes (and `pdm run fe-lint`/`pdm run fe-type-check` if configured)."
---

## Problem

The SPA’s editor AI implementation grew quickly during the AI sprint. Some files now act as “god modules” that mix
UI state, API calls, parsing, and orchestration. This increases coupling and makes correctness-sensitive AI flows
harder to refactor safely.

## Goal

- Enforce SRP boundaries in editor AI hotspots (chat + edit-ops + inline completion integration points).
- Keep views UI-only and push logic down into cohesive composables/modules.
- Reduce file sizes to match repo rules and improve testability (mock at module boundaries).
- Preserve runtime behavior (refactor only).

## Non-goals

- UX redesign of chat/edit-ops/ghost-text (beyond mechanical component extraction if needed).
- Changing backend contracts, prompt formats, budgets, routing, or thread semantics.
- Adding new AI capabilities or providers.

## SRP audit (frontend AI sprint hotspots)

- `frontend/apps/skriptoteket/src/views/admin/ScriptEditorView.vue` (~848 LoC): high prop drilling + orchestration across editor, chat, edit-ops, workflow, persistence; candidate extraction into focused subcomponents + view-model composables.
- `frontend/apps/skriptoteket/src/components/editor/EditorWorkspacePanel.vue` (~560 LoC): large SFC with extensive prop/event surface; candidate move prop/event types + derived helpers to adjacent TS module(s) and split template into subcomponents.
- `frontend/apps/skriptoteket/src/composables/editor/useEditorEditOps.ts` (~744 LoC): mixes selection/cursor capture, API calls, preview diff derivation, apply/undo/redo snapshotting, timers/listeners, and UI state model; candidate split into API client + pure helpers + state machine/composable.
- `frontend/apps/skriptoteket/src/composables/editor/useEditorEditOps.spec.ts` (~576 LoC): exceeds test size guidance; candidate split by behavior area (request/preview/apply/undo) with shared fixtures.
- `frontend/apps/skriptoteket/src/composables/editor/useEditorChat.ts` (~403 LoC): mixes history loading, SSE streaming, event parsing, and local message state; candidate split into SSE client + event reducer + API helpers.
- `frontend/apps/skriptoteket/src/components/editor/ChatDrawer.vue` (~474 LoC): UI plus input orchestration + remote-fallback opt-in toggle; candidate extract input composer / message list (optional) if it needs to grow.

## Implementation plan

1. Introduce a small “editor AI API” module boundary for typed requests:
   - `editorChatApi.ts` (history/clear + `postChatStream(...)` helper).
   - `editorEditOpsApi.ts` (request/preview/apply endpoints).
   This keeps network details out of composables and enables `vi.mock` at the boundary.
2. Refactor `useEditorChat.ts`:
   - Extract SSE parsing/stream loop into a `EditorChatStreamClient` helper that emits typed events.
   - Extract message/notice/disabled/error state updates into a reducer-like helper for determinism in tests.
3. Refactor `useEditorEditOps.ts`:
   - Extract pure helpers (fingerprints, selection/cursor resolution, target file ordering, diff items).
   - Extract “proposal lifecycle” logic (request → preview → apply → snapshot) into smaller composables/modules.
   - Keep `useEditorEditOps(...)` as a thin facade to avoid churn in component callers.
4. Reduce Vue SFC size for editor AI surfaces:
   - Move large prop/event types for `EditorWorkspacePanel.vue` into `EditorWorkspacePanel.types.ts` (or similar).
   - If needed, split `ScriptEditorView.vue` into subcomponents that each have a focused prop surface (e.g., workspace panel wiring vs workflow modal).
5. Split `useEditorEditOps.spec.ts` into smaller specs aligned with the extracted modules and keep each file <400–500 LoC.

## Test plan

- `pdm run fe-test`
- If configured: `pdm run fe-lint` and `pdm run fe-type-check`
- Quick manual smoke (no backend changes required):
  - Open `http://127.0.0.1:5173/admin/tools/<tool_id>`
  - Verify chat still streams and edit-ops still previews/applies/undo-redo as before.

## Rollback plan

- Revert the PR; this is a refactor-only change with no data migrations.
