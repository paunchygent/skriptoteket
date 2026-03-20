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
- Completed: ST-23-01, ST-23-02, ST-23-03, ST-23-04, ST-23-05, ST-23-06 (Epic 23 Slice 1 Fully Complete).

## Current Session (2026-03-20)

- Klassrumskartan (Group Seating Studio) UI Implementation & Draft Persistence (Slice 1).
  - Built `GroupBoard.vue` and `GroupCard.vue` for assigning students to groups via drag-and-drop.
  - Built `RoomCanvas.vue` and `SeatNode.vue` for spatial seat assignments.
  - Implemented normalized Pinia state in `useClassroomState.ts` with strict reducers.
  - Implemented `PlanDraft` persistence layer (SQLAlchemy model, repository, service methods, and API endpoints).
  - Added debounced autosave (`_triggerAutosave`) directly into the strict state reducers, ensuring durable draft continuation (ST-23-06).
  - Addressed review feedback from ST-23-01/02 (ownership auth checks, expanded service unit tests, fixed DTO naming).
  - Resolved `dishka` deprecation warnings by migrating to `starlette-dishka` and creating a compatibility layer.

## Previous Sessions

- Klassrumskartan (Group Seating Studio) Relational Persistence (Slice 1).
  - Implemented `Roster` and `RoomTemplate` SQLAlchemy models.
  - Created and applied Alembic migration `57a6ea32ef0a` for new tables.
  - Added CRUD API endpoints in `src/skriptoteket/web/api/v1/apps_classroom_planner.py`.
- Older history: see `.agents/readme-first.md` + `docs/`.

## Verification

- 2026-03-20: `pdm run fe-test` (PASSED: all 256 frontend unit tests pass, verifying the Pinia store reducers).
- 2026-03-20: `pdm run pytest tests/unit/application/apps/classroom_planner` (PASSED: verified expanded test coverage and ownership auth checks).
- 2026-03-20: `pdm run lint` and `pdm run typecheck` (PASSED).

## How to Run

```bash
# Setup
docker compose up -d db && pdm run db-upgrade

# Development (backend + SPA)
ARTIFACTS_ROOT=/tmp/skriptoteket/artifacts pdm run dev-local

# Quality gates
pdm run lint
pdm run typecheck
pdm run test
pdm run fe-test
```

## Known Issues / Risks

- Mutually dependent foreign keys between `tools` and `tool_versions` cause a warning during Alembic autogeneration (SAWarning: Cannot correctly sort tables).
- Migration idempotency tests require a running Docker daemon.

## Next Steps

- ST-23-06: PlanDraft persistence and autosave (saving the workspace state to the database).
