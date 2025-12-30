---
type: story
id: ST-06-15
title: "Frontend critical test coverage gaps (SPA)"
status: done
owners: "agents"
created: 2025-12-29
epic: "EPIC-06"
acceptance_criteria:
  - "Router guard/auth redirect logic is covered by Vitest tests"
  - "Tool run orchestration (submit + polling + actions) is covered by Vitest tests"
  - "Editor save + workflow actions have Vitest coverage for success + error paths"
  - "Draft lock + settings flows have Vitest coverage for conflicts + error handling"
  - "Coverage status is tracked and updated in REF-frontend-test-gaps-2025-12-29"
---

## Context

The SPA has limited Vitest coverage outside stores and helpers. This story tracks the critical
frontend test gaps and implements coverage for the highest-risk flows first.

Reference list: `docs/reference/ref-frontend-test-gaps-2025-12-29.md`.

## Critical checklist (update as completed)

- [x] Router guards + auth redirects (`frontend/apps/skriptoteket/src/router/index.ts`)
- [x] Tool run flow (`frontend/apps/skriptoteket/src/composables/tools/useToolRun.ts`)
- [x] Editor save + workflow actions (`frontend/apps/skriptoteket/src/composables/editor/useScriptEditor.ts`, `frontend/apps/skriptoteket/src/composables/editor/useEditorWorkflowActions.ts`)
- [x] Draft lock acquisition + heartbeat (`frontend/apps/skriptoteket/src/composables/editor/useDraftLock.ts`)
- [x] Tool settings flows (`frontend/apps/skriptoteket/src/composables/tools/useToolSettings.ts`, `frontend/apps/skriptoteket/src/composables/editor/useToolVersionSettings.ts`, `frontend/apps/skriptoteket/src/composables/editor/useSandboxSettings.ts`)

## Notes

- Keep tests focused on composables/helpers with mocked API boundaries (`vi.mock`).
- Prefer unit/integration style tests in Vitest; no Playwright for these flows.
