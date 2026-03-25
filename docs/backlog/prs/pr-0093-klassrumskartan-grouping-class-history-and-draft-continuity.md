---
type: pr
id: PR-0093
title: "Klassrumskartan: grouping class history and draft continuity"
status: done
owners: "agents"
created: 2026-03-22
updated: 2026-03-25
stories:
  - "ST-24-03"
tags: ["frontend", "backend", "integration"]
acceptance_criteria:
  - "Creating a new grouping draft starts blank and demotes the previous active grouping draft to secondary class history automatically."
  - "Resuming the current grouping draft stays distinct from reopening an older superseded grouping draft."
  - "Any class-level grouping history remains clearly secondary to the active draft and its in-workspace undo/redo history."
  - "On desktop/laptop-sized viewports, grouping history opens as an overlay drawer rather than pushing the active workspace down."
  - "The segmented toggle remains the only way to enter `Översikt`, `Grupper`, and `Sittplatser`; the overview does not duplicate those entry actions."
  - "The grouping history trigger lives in the grouping action row so the continuity drawer feels native to that mode instead of being anchored in the overview."
  - "Smaller viewport behavior is treated as an adaptation of the desktop workflow rather than the source of the primary interaction model."
  - "Older historical grouping drafts can be deleted from the drawer through a secondary trash-can action with confirmation, without introducing active-draft delete controls into the main workspace."
  - "Live browser verification covers grouping draft creation, grouping randomize/manual edits, undo/redo, leaving and resuming the draft, and opening an older grouping draft from secondary history."
---

## Problem

`ST-24-03` still needs one more lifecycle polish layer after grouping fundamentals and undo/redo:

- new grouping drafts must start cleanly
- previous active grouping drafts must demote to secondary class history automatically
- class-level history must not compete with the active draft or with in-workspace undo/redo

Without this distinction, the app risks showing too many "histories" at once and becoming muddy
again.

## Goal

Finish the grouping draft workflow as a clear document-like model:

- one active grouping draft
- bounded in-workspace undo/redo for recent steps
- secondary class-level history for earlier superseded drafts

## Non-goals

- Durable export/file-vault artifact projection.
- Seating draft continuity.
- Broad archival/version-management UX.

## Checklist

- [ ] Keep `Nytt grupputkast` blank and explicit.
- [ ] Demote the previous active grouping draft to secondary class history automatically.
- [ ] Keep active-draft resume distinct from reopening an older superseded draft.
- [ ] Keep class-level grouping history secondary to the active workspace.
- [ ] Keep grouping history inside an overlay drawer on full-sized viewports instead of a push-down panel.
- [ ] Present the current active grouping draft separately from older superseded drafts inside the continuity surface.
- [ ] Let older historical grouping drafts be deleted from the drawer through a secondary trash-can action and confirmation flow.
- [ ] Extend live browser checks for grouping draft continuity and class history behavior.

## Implementation plan

- Reuse the class-first workspace and grouping drawer patterns from `ST-24-02`, but keep prior
  grouping drafts visually secondary to the active draft.
- Distinguish clearly between:
  - current active grouping draft
  - earlier superseded grouping drafts
  - in-workspace undo/redo history
- Keep the continuity UI desktop-first:
  - use a fixed overlay drawer on full-sized viewports
  - do not push the active workspace down when history opens
  - treat tablet/phone layouts as ports of the desktop workflow rather than the source of the
    canonical layout
- Keep the overview quiet:
  - the segmented toggle remains the only mode switch
  - overview content stays class-focused instead of duplicating grouping/seating launch actions
- Ensure creating a new grouping draft does not silently copy the current one.
- Keep reopening earlier grouping drafts simple and class-scoped without turning them into
  teacher-facing "saved files".
- Keep the active draft visually distinct from the historical draft list, for example through a
  compact "Aktuellt utkast" section above the secondary history entries.

## Concrete implementation checklist

### 1. Extend the class-workspace grouping history surface

Targets:

- `frontend/apps/skriptoteket/src/views/apps/components/PlannerHistoryDrawer.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerClassWorkspace.vue`

Required behavior:

- The grouping history drawer remains a fixed right-side overlay on desktop/laptop-sized viewports.
- Opening the grouping history drawer must not push the main workspace down or replace the active
  task surface.
- The drawer should distinguish:
  - current active grouping draft
  - older superseded grouping drafts
- The active grouping draft should appear as a compact separate section rather than as just another
  item in the historical list.

### 2. Make historical grouping drafts actionable

Targets:

- `frontend/apps/skriptoteket/src/views/apps/components/PlannerHistoryDrawer.vue`
- `frontend/apps/skriptoteket/src/views/apps/ClassroomPlannerView.vue`
- `frontend/apps/skriptoteket/src/views/apps/useClassroomState.ts`
- backend contract only if current draft-load endpoints are insufficient

Required behavior:

- Grouping history entries can be opened from the drawer.
- Opening a historical grouping draft quietly makes it the active grouping draft for the class.
- The previously active grouping draft is demoted to secondary class history automatically.
- Seating history stays unchanged in this PR unless a minimal shared refactor is required.

### 2a. Add historical draft deletion to the drawer

Targets:

- `frontend/apps/skriptoteket/src/views/apps/components/PlannerHistoryDrawer.vue`
- `frontend/apps/skriptoteket/src/views/apps/ClassroomPlannerView.vue`
- `frontend/apps/skriptoteket/src/views/apps/useClassroomState.ts`
- backend contract only if the current abandon/delete path needs a historical-draft-specific entry point

Required behavior:

- Only historical grouping drafts expose delete controls in this PR.
- Delete is a secondary action, for example a trash-can affordance on the historical item row.
- Delete always requires confirmation.
- Deleting a historical grouping draft removes it from the drawer list without affecting the current active grouping draft.
- The active grouping draft must not gain a delete/trash affordance in the main workspace through this PR.

### 3. Preserve clean resume semantics

Targets:

- `frontend/apps/skriptoteket/src/views/apps/ClassroomPlannerView.vue`
- `frontend/apps/skriptoteket/src/views/apps/useClassroomState.ts`

Required behavior:

- Opening `Grupper` for a class resumes the current active grouping draft directly.
- The teacher does not have to choose from history before continuing current work.
- Opening an older grouping draft from the drawer is a distinct, uncommon recovery action.

### 4. Keep history visually secondary and compact

Targets:

- `frontend/apps/skriptoteket/src/views/apps/components/PlannerHistoryDrawer.vue`
- `frontend/apps/skriptoteket/src/views/apps/classroomPlannerTypes.ts`

Required behavior:

- Historical grouping items stay concise and scannable.
- Each historical item should show only enough metadata to identify it, such as:
  - updated timestamp
  - optional classroom-context label
  - compact draft metadata when useful
- Avoid large preview cards, broad dashboard chrome, or UI that competes with the active
  workspace.

### 5. Keep undo/redo distinct from class history

Targets:

- `frontend/apps/skriptoteket/src/views/apps/useClassroomState.ts`
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerHistoryDrawer.vue`
- backend contract only if needed

Required behavior:

- In-draft undo/redo remains local to the currently active grouping draft.
- The continuity drawer must not surface undo/redo steps as separate class-history items.
- Opening an older grouping draft changes which draft is active; it does not merge or replay
  undo/redo history across drafts.

### 6. Add focused tests and browser verification

Targets:

- `frontend/apps/skriptoteket/src/views/apps/components/PlannerHistoryDrawer.spec.ts` if needed
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerClassWorkspace.spec.ts` if needed
- `frontend/apps/skriptoteket/src/views/apps/ClassroomPlannerView.spec.ts`
- `frontend/apps/skriptoteket/src/views/apps/useClassroomState.spec.ts`
- `tests/unit/application/apps/classroom_planner/test_draft_lifecycle.py`
- `tests/unit/web/apps/classroom_planner/test_api.py`
- `scripts/playwright_classroom_planner_smoke.py`

Required coverage:

- creating a new grouping draft demotes the previous one to secondary history
- opening `Grupper` resumes the active grouping draft directly
- opening an older grouping draft from history makes it active
- deleting an older historical grouping draft removes it after confirmation without disturbing the active draft
- the active draft remains visually primary
- the history drawer stays overlay-based on desktop-sized viewport verification

## Verification commands

Before implementation:

```bash
pdm run pytest tests/unit/application/apps/classroom_planner/test_draft_lifecycle.py tests/unit/web/apps/classroom_planner/test_api.py -q
pnpm -C frontend --filter @skriptoteket/spa exec vitest run src/views/apps/useClassroomState.spec.ts src/views/apps/components/GroupBoard.spec.ts src/views/apps/components/PlannerWorkspaceShell.spec.ts src/views/apps/ClassroomPlannerView.spec.ts
```

After implementation:

```bash
pdm run pytest tests/unit/application/apps/classroom_planner/test_draft_lifecycle.py tests/unit/web/apps/classroom_planner/test_api.py -q
pdm run ruff check src/skriptoteket/application/curated_apps/classroom_planner/handlers/drafts.py src/skriptoteket/infrastructure/repositories/classroom_planner.py src/skriptoteket/web/api/v1/apps_classroom_planner.py tests/unit/application/apps/classroom_planner/test_draft_lifecycle.py tests/unit/web/apps/classroom_planner/test_api.py
pdm run mypy src/skriptoteket/application/curated_apps/classroom_planner/handlers/drafts.py src/skriptoteket/infrastructure/repositories/classroom_planner.py src/skriptoteket/web/api/v1/apps_classroom_planner.py

pnpm -C frontend --filter @skriptoteket/spa exec vitest run src/views/apps/useClassroomState.spec.ts src/views/apps/components/PlannerHistoryDrawer.spec.ts src/views/apps/components/PlannerClassWorkspace.spec.ts src/views/apps/ClassroomPlannerView.spec.ts
pnpm -C frontend --filter @skriptoteket/spa exec eslint src/views/apps/useClassroomState.ts src/views/apps/classroomPlannerTypes.ts src/views/apps/components/PlannerHistoryDrawer.vue src/views/apps/components/PlannerClassWorkspace.vue src/views/apps/ClassroomPlannerView.vue
pnpm -C frontend --filter @skriptoteket/spa exec vue-tsc --noEmit
pnpm -C frontend --filter @skriptoteket/spa build

pdm run docs-validate
pdm run python -m scripts.playwright_classroom_planner_smoke --base-url http://127.0.0.1:5173
```

## Test plan

- Backend/integration:
  - creating a new grouping draft supersedes the previous active grouping draft
  - reopening an older grouping draft restores it as the active draft for that class
- Frontend/manual:
  - active draft remains primary
  - older drafts stay secondary
- Live/browser:
  - use the app-specific Playwright baseline to create/open grouping, make several edits, use
    undo/redo, create a blank new draft, and reopen the previous grouping draft from secondary
    class history

## Rollback plan

- Revert the class-history continuity changes if they make grouping history louder than the active
  workspace, while keeping grouping fundamentals and undo/redo intact.

## Follow-up direction

- `ST-24-04` can mirror the same draft-history and draft-continuity model for seating.
