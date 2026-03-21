# Session Handoff

Keep this file updated so the next session can pick up work quickly.

## Editing Rules (do not break structure)

- Keep the headings and section order exactly as-is; only fill in content.
- Use short bullets; include key file paths (e.g., `src/...`, `docs/...`) and exact commands.
- Do not paste large code blocks; link to files instead.
- Never include secrets/tokens/passwords or personal data.
- Keep this file under 200 lines; move history to `.agents/readme-first.md` + `docs/`.

## Snapshot

- Date: 2026-03-20
- Branch: `main` + local changes
- Current sprint: N/A (no sprints)
- Production: Full Vue SPA
- Completed: EPIC-23 closure work + core EPIC-24 Slice 2 implementation for Klassrumskartan (workspace hydrate, draft groups, metadata/constraints, suggestion/randomize/finalize APIs, richer planner UI, class/classroom CRUD edits, live-verified randomizer/snapshot flow).

## Current Session (2026-03-20)

- Klassrumskartan Slice 2 backend:
  - Added draft-scoped groups, student metadata, pair constraints, planning profile, suggestion metadata, and arrangement snapshots.
  - Added validation, suggestions, suggestion apply, randomize (`Slumpa`), finalize, and snapshot read endpoints in `src/skriptoteket/web/api/v1/apps_classroom_planner.py`.
  - Added migration `migrations/versions/8a1d4c7b32ef_classroom_planner_slice_2_workspace_and_.py`.
  - Fixed `save_workspace()` child-row replacement in `src/skriptoteket/infrastructure/repositories/classroom_planner.py` so randomize/apply no longer violate `uq_cp_draft_group_id` on existing drafts.
- Klassrumskartan Slice 2 frontend:
  - Rebuilt `frontend/apps/skriptoteket/src/views/apps/useClassroomState.ts` around the hydrated workspace contract.
  - Added responsive selection/workspace split via `PlannerSelectionGate.vue` and `PlannerWorkspaceShell.vue`.
  - Added teacher metadata drawer, suggestion panel, randomizer controls, conflict reload UX, and improved classroom canvas with fixtures.
  - Upgraded roster/classroom modals to create/edit/delete and added fixture placement for whiteboard, teacher desk, windows, and door.
  - Fixed invalid nested-button markup in `frontend/apps/skriptoteket/src/views/apps/components/GroupCard.vue`.
- Docs:
  - Added `docs/adr/adr-0070-group-seating-studio-slice-2-engine-and-snapshots.md`.
  - Added `docs/backlog/epics/epic-24-group-seating-studio-slice-2.md`.
  - Rewrote `docs/backlog/reviews/review-epic-24-group-seating-studio-slice-2-planning.md`.
  - Updated `docs/backlog/epics/epic-23-group-seating-studio.md` and `docs/index.md`.

## Previous Sessions

- Earlier Slice 1 history remains in `.agents/readme-first.md` and the EPIC-23 docs/review trail.

## Verification

- 2026-03-20: `pnpm -C frontend --filter @skriptoteket/spa exec vitest run src/views/apps/useClassroomState.spec.ts` (PASSED).
- 2026-03-20: `pnpm -C frontend --filter @skriptoteket/spa exec vue-tsc --noEmit` (PASSED).
- 2026-03-20: `pnpm -C frontend --filter @skriptoteket/spa build` (PASSED).
- 2026-03-20: `python -m py_compile src/skriptoteket/web/api/v1/apps_classroom_planner.py src/skriptoteket/application/curated_apps/classroom_planner/handlers/planning.py src/skriptoteket/infrastructure/repositories/classroom_planner.py` (PASSED).
- 2026-03-20: `pdm run pytest tests/unit/web/apps/classroom_planner/test_api.py -q` (PASSED).
- 2026-03-20: `pdm run pytest tests/unit/application/apps/classroom_planner/test_services.py -q` (PASSED).
- 2026-03-20: `pdm run pytest tests/integration/database/test_classroom_planner_migration.py -q -m 'integration and docker'` (PASSED).
- 2026-03-20: `ARTIFACTS_ROOT=/tmp/skriptoteket/artifacts pdm run dev-local` + Playwright/request smoke (PASSED): created roster/template with fixtures, opened `/apps/classroom.group-seating-studio`, selected lesson mode/assets, ran `Slumpa`, opened student metadata, fetched/applied suggestions, finalized snapshot.
- 2026-03-20: `ARTIFACTS_ROOT=/tmp/skriptoteket/artifacts pdm run dev-local` + edit-surface smoke (PASSED): opened `Redigera klasslista` and `Redigera klassrum` from the selection gate.

## How to Run

```bash
# Setup
docker compose up -d db && pdm run db-upgrade

# Development (backend + SPA)
ARTIFACTS_ROOT=/tmp/skriptoteket/artifacts pdm run dev-local

# Focused verification
pnpm -C frontend --filter @skriptoteket/spa exec vue-tsc --noEmit
pnpm -C frontend --filter @skriptoteket/spa build
pdm run pytest tests/unit/web/apps/classroom_planner/test_api.py -q
pdm run pytest tests/unit/application/apps/classroom_planner/test_services.py -q
pdm run pytest tests/integration/database/test_classroom_planner_migration.py -q -m 'integration and docker'
```

## Known Issues / Risks

- Broader repo-wide lint/typecheck/test suites have not been rerun after this Slice 2 landing.
- The ad hoc live smoke created several dev-only roster/template rows in the local database; they are harmless but noisy.

## Next Steps

- Run broader quality gates (`pdm run lint`, `pdm run typecheck`, `pdm run test`, `pdm run fe-test`) once the live check is complete.
- Optionally add a cleanup/admin story for removing temporary local dev planner assets if the seed noise becomes distracting.
