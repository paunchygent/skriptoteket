# Session Handoff
Keep this file updated so the next session can pick up work quickly.

## Editing Rules (do not break structure)

- Keep the headings and section order exactly as-is; only fill in content.
- Use short bullets; include key file paths (e.g., `src/...`, `docs/...`) and exact commands.
- Do not paste large code blocks; link to files instead.
- Never include secrets/tokens/passwords or personal data.
- Keep this file under 200 lines; move history to `.agents/readme-first.md` + `docs/`.

## Snapshot

- Date: 2026-03-22
- Branch: `main` + local changes
- Current sprint: Sprint 24
- Production: Full Vue SPA
- Completed: `ST-24-01`, `ST-24-05`, `ST-24-02`, `PR-0090`, and `PR-0091` (Klassrumskartan grouping workspace fundamentals).

## Status

- PR-0090 is DONE. Implemented bounded undo/redo history (10 steps) inside the active grouping draft.
- PR-0091 is DONE. Grouping now has its own `Slumpa`, an explicit blank `Nytt grupputkast`, and larger group cards render without clipping.
- PR-0091 follow-up fixes are DONE. Group-card up/down controls now update meaningful persisted ordering, and the shared grouping API serializer no longer depends on a private helper leak.
- Backend lifecycle: added `CreateGroupingDraftHandler` plus `POST /api/v1/apps/classroom.group-seating-studio/drafts/grouping/new` so blank grouping drafts supersede the previous active grouping draft cleanly instead of overloading `resolve`.
- Frontend store: `useClassroomState.ts` now exposes `startNewGroupingDraft()` and `randomizeGroups()`, with pure grouping-randomize logic kept in `classroomPlannerStoreMutations.ts`.
- Frontend UI: grouping controls live in `GroupBoard.vue`; `PlannerWorkspaceShell.vue` forwards explicit new-draft requests; `GroupCard.vue` now wraps student cards cleanly for larger groups.
- Group ordering: `moveGroup()` now preserves user-visible reorder intent instead of re-sorting by stale `sort_order`, so group-card up/down controls are safe to reuse during later PDF/XLSX export work.
- Group naming: default names are now positional labels backed by `name_is_custom`. Untouched defaults renumber automatically on reorder/delete, while teacher-entered custom names stay fixed.
- Live smoke: `scripts/playwright_classroom_planner_smoke.py` now verifies grouping rename + `Slumpa` + blank `Nytt grupputkast` before continuing through seating, overview return, and landing exit/discard.
- Live smoke also verifies grouping reorder in the browser: custom names stay fixed, default names remain positional, and `Ordning` badges stay meaningful after reordering.
- PR-0092 is now tightened at the planning level:
  - undo/redo stays grouping-only
  - pending autosave should flush before undo/redo
  - the existing compact autosave badge stays; no broad top-panel redesign
  - `Nytt grupputkast` remains a draft-lifecycle boundary outside undo/redo
- Next: implement PR-0092 with the narrowed scope above.

## Previous Sessions

## Verification

- 2026-03-22: `pdm run pytest tests/unit/application/apps/classroom_planner/test_draft_lifecycle.py -q`; `pdm run pytest tests/unit/web/apps/classroom_planner/test_api.py -q`; `pdm run pytest tests/unit/infrastructure/repositories/test_classroom_planner_history_unit.py -q` (ALL PASSED).
- 2026-03-22: `pdm run alembic upgrade head` (PASSED).
- 2026-03-22: `pdm run ruff check src/skriptoteket/web/api/v1/apps_classroom_planner.py src/skriptoteket/infrastructure/repositories/classroom_planner.py src/skriptoteket/domain/curated_apps/classroom_planner/models.py src/skriptoteket/application/curated_apps/classroom_planner/handlers/drafts.py` (PASSED).
- 2026-03-22: `PYTHONPATH=src pdm run python -c 'from skriptoteket.di.curated_apps import CuratedAppsProvider; print("di-import-ok")'` (PASSED).
- 2026-03-22: `pdm run pytest tests/unit/application/apps/classroom_planner/test_draft_lifecycle.py tests/unit/infrastructure/repositories/test_classroom_planner_review_fixes.py tests/unit/web/apps/classroom_planner/test_api.py -q` (31 PASSED).
- 2026-03-22: `pdm run ruff check src/skriptoteket/application/curated_apps/classroom_planner/handlers/drafts.py src/skriptoteket/infrastructure/repositories/classroom_planner.py tests/unit/application/apps/classroom_planner/test_draft_lifecycle.py tests/unit/infrastructure/repositories/test_classroom_planner_review_fixes.py` (PASSED).
- 2026-03-22: `pdm run mypy src/skriptoteket/application/curated_apps/classroom_planner/handlers/drafts.py src/skriptoteket/infrastructure/repositories/classroom_planner.py` (PASSED).
- 2026-03-22: `pdm run pytest -m 'integration and docker' tests/integration/database/test_classroom_planner_migration.py -q` (PASSED).
- 2026-03-22: `pdm run pytest tests/unit/application/apps/classroom_planner/test_draft_lifecycle.py tests/unit/web/apps/classroom_planner/test_api.py -q` (29 PASSED).
- 2026-03-22: `pnpm -C frontend --filter @skriptoteket/spa exec vitest run src/views/apps/useClassroomState.spec.ts src/views/apps/components/GroupBoard.spec.ts src/views/apps/components/PlannerWorkspaceShell.spec.ts src/views/apps/ClassroomPlannerView.spec.ts` (27 PASSED).
- 2026-03-22: `pdm run ruff check src/skriptoteket/application/curated_apps/classroom_planner/handlers/planner_context.py src/skriptoteket/application/curated_apps/classroom_planner/handlers/workspace_builders.py src/skriptoteket/application/curated_apps/classroom_planner/handlers/grouping_drafts.py src/skriptoteket/application/curated_apps/classroom_planner/handlers/drafts.py src/skriptoteket/application/curated_apps/classroom_planner/__init__.py src/skriptoteket/di/curated_apps.py src/skriptoteket/web/api/v1/apps_classroom_planner_grouping.py src/skriptoteket/web/router.py tests/unit/application/apps/classroom_planner/test_draft_lifecycle.py tests/unit/web/apps/classroom_planner/test_api.py` (PASSED).
- 2026-03-22: `pdm run mypy src/skriptoteket/application/curated_apps/classroom_planner/handlers/planner_context.py src/skriptoteket/application/curated_apps/classroom_planner/handlers/workspace_builders.py src/skriptoteket/application/curated_apps/classroom_planner/handlers/grouping_drafts.py src/skriptoteket/application/curated_apps/classroom_planner/handlers/drafts.py src/skriptoteket/infrastructure/repositories/classroom_planner.py src/skriptoteket/web/api/v1/apps_classroom_planner_grouping.py` (PASSED).
- 2026-03-22: `pnpm -C frontend --filter @skriptoteket/spa exec eslint src/views/apps/ClassroomPlannerView.vue src/views/apps/classroomPlannerStoreMutations.ts src/views/apps/classroomPlannerTypes.ts src/views/apps/useClassroomState.ts src/views/apps/ClassroomPlannerView.spec.ts src/views/apps/components/GroupBoard.vue src/views/apps/components/GroupBoard.spec.ts src/views/apps/components/GroupCard.vue src/views/apps/components/PlannerWorkspaceShell.vue src/views/apps/components/PlannerWorkspaceShell.spec.ts` (PASSED).
- 2026-03-22: `pnpm -C frontend --filter @skriptoteket/spa exec vue-tsc --noEmit` (PASSED).
- 2026-03-22: `pnpm -C frontend --filter @skriptoteket/spa build` (PASSED).
- 2026-03-22: `pdm run ruff check scripts/playwright_classroom_planner_smoke.py` (PASSED).
- 2026-03-22: `pdm run python -m scripts.playwright_classroom_planner_smoke --base-url http://127.0.0.1:5173` (PASSED; artifact in `.artifacts/classroom-planner-smoke/classroom-planner-smoke.png`).
- 2026-03-22: `pnpm -C frontend --filter @skriptoteket/spa exec vitest run src/views/apps/components/GroupCard.spec.ts src/views/apps/components/GroupBoard.spec.ts src/views/apps/components/PlannerWorkspaceShell.spec.ts src/views/apps/ClassroomPlannerView.spec.ts src/views/apps/useClassroomState.spec.ts` (30 PASSED).
- 2026-03-22: `pdm run pytest tests/unit/application/apps/classroom_planner/test_draft_lifecycle.py tests/unit/web/apps/classroom_planner/test_api.py -q` (29 PASSED).
- 2026-03-22: `pdm run ruff check src/skriptoteket/web/api/v1/apps_classroom_planner_draft_contracts.py src/skriptoteket/web/api/v1/apps_classroom_planner.py src/skriptoteket/web/api/v1/apps_classroom_planner_grouping.py` (PASSED).
- 2026-03-22: `pdm run mypy src/skriptoteket/web/api/v1/apps_classroom_planner_draft_contracts.py src/skriptoteket/web/api/v1/apps_classroom_planner.py src/skriptoteket/web/api/v1/apps_classroom_planner_grouping.py` (PASSED).
- 2026-03-22: `pnpm -C frontend --filter @skriptoteket/spa exec eslint src/views/apps/classroomPlannerStoreMutations.ts src/views/apps/useClassroomState.ts src/views/apps/useClassroomState.spec.ts src/views/apps/components/GroupBoard.spec.ts src/views/apps/components/GroupCard.vue src/views/apps/components/GroupCard.spec.ts` (PASSED).
- 2026-03-22: `pnpm -C frontend --filter @skriptoteket/spa exec vue-tsc --noEmit` (PASSED).
- 2026-03-22: `pnpm -C frontend --filter @skriptoteket/spa build` (PASSED).
- 2026-03-22: `pdm run docs-validate` (PASSED).
- 2026-03-22: `pdm run python -m scripts.playwright_classroom_planner_smoke --base-url http://127.0.0.1:5173` (PASSED after adding reorder assertions; artifact in `.artifacts/classroom-planner-smoke/classroom-planner-smoke.png`).
- 2026-03-22: `pdm run db-upgrade` (PASSED; required locally after adding the `name_is_custom` draft-group migration).
- 2026-03-22: `pnpm -C frontend --filter @skriptoteket/spa exec vitest run src/views/apps/useClassroomState.spec.ts src/views/apps/components/GroupCard.spec.ts src/views/apps/components/GroupBoard.spec.ts src/views/apps/components/RoomCanvas.spec.ts src/views/apps/components/PlannerWorkspaceShell.spec.ts src/views/apps/ClassroomPlannerView.spec.ts` (34 PASSED).
- 2026-03-22: `pdm run pytest tests/unit/application/apps/classroom_planner/test_draft_lifecycle.py tests/unit/web/apps/classroom_planner/test_api.py tests/unit/infrastructure/repositories/test_classroom_planner_review_fixes.py -q` (33 PASSED).
- 2026-03-22: `pdm run pytest -m 'integration and docker' tests/integration/database/test_classroom_planner_migration.py -q` (PASSED).
- 2026-03-22: `pdm run ruff check migrations/versions/71e8b6f24c1a_add_group_name_custom_flag.py src/skriptoteket/domain/curated_apps/classroom_planner/models.py src/skriptoteket/application/curated_apps/classroom_planner/handlers/workspace_builders.py src/skriptoteket/infrastructure/db/models/classroom_planner_plan_draft.py src/skriptoteket/infrastructure/repositories/classroom_planner.py src/skriptoteket/web/api/v1/apps_classroom_planner.py tests/unit/infrastructure/repositories/test_classroom_planner_review_fixes.py scripts/playwright_classroom_planner_smoke.py` (PASSED).
- 2026-03-22: `pdm run mypy src/skriptoteket/domain/curated_apps/classroom_planner/models.py src/skriptoteket/application/curated_apps/classroom_planner/handlers/workspace_builders.py src/skriptoteket/infrastructure/repositories/classroom_planner.py src/skriptoteket/web/api/v1/apps_classroom_planner.py` (PASSED).
- 2026-03-22: `pnpm -C frontend --filter @skriptoteket/spa exec eslint src/views/apps/classroomPlannerTypes.ts src/views/apps/classroomPlannerStoreMutations.ts src/views/apps/useClassroomState.ts src/views/apps/useClassroomState.spec.ts src/views/apps/components/GroupBoard.spec.ts src/views/apps/components/GroupCard.vue src/views/apps/components/GroupCard.spec.ts src/views/apps/components/RoomCanvas.spec.ts` (PASSED).
- 2026-03-22: `pnpm -C frontend --filter @skriptoteket/spa exec vue-tsc --noEmit` (PASSED).
- 2026-03-22: `pnpm -C frontend --filter @skriptoteket/spa build` (PASSED).
- 2026-03-22: `pdm run python -m scripts.playwright_classroom_planner_smoke --base-url http://127.0.0.1:5173` (PASSED after adding default/custom naming assertions; artifact in `.artifacts/classroom-planner-smoke/classroom-planner-smoke.png`).

## How to Run

```bash
# Setup
docker compose up -d db && pdm run db-upgrade

# Development (backend + SPA)
ARTIFACTS_ROOT=/tmp/skriptoteket/artifacts pdm run dev-local

# Focused verification
pdm run pytest tests/unit/web/apps/classroom_planner/test_api.py -q
pnpm -C frontend --filter @skriptoteket/spa exec vitest run src/views/apps/useClassroomState.spec.ts src/views/apps/components/GroupBoard.spec.ts src/views/apps/components/PlannerWorkspaceShell.spec.ts src/views/apps/ClassroomPlannerView.spec.ts
```

## Known Issues / Risks

- Integration tests for repository history were moved to unit tests due to environmental loop mismatch issues in the test runner; the repository logic itself is thoroughly covered by `test_classroom_planner_history_unit.py`.
- Seating drafts do not yet push to history (intentional scope constraint for PR-0090); they will inherit the same model in ST-24-04.

## Next Steps

- Start `PR-0092` for `ST-24-03`: add grouping undo/redo controls and compact autosave feedback on top of the shipped draft-history contract and grouping fundamentals.
