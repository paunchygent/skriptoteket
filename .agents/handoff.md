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
- Completed: ST-23-02 (Roster/Template Persistence) for Klassrumskartan.

## Current Session (2026-03-20)

- Klassrumskartan (Group Seating Studio) Relational Persistence (Slice 1).
  - Implemented `Roster` and `RoomTemplate` SQLAlchemy models in `src/skriptoteket/infrastructure/db/models/`.
  - Created and applied Alembic migration `57a6ea32ef0a` for new tables.
  - Implemented `PostgreSQLRosterRepository` and `PostgreSQLRoomTemplateRepository` in `src/skriptoteket/infrastructure/repositories/classroom_planner.py`.
  - Added CRUD application services in `src/skriptoteket/application/apps/classroom_planner/services.py`.
  - Added CRUD API endpoints in `src/skriptoteket/web/api/v1/apps_classroom_planner.py`.
  - Updated `ClassroomPlannerView.vue` with a 3-step selection gate (Lesson Mode, Roster, Room).
  - Added a REQUIRED database migration idempotency test using Testcontainers in `tests/integration/database/test_classroom_planner_migration.py`.

## Previous Sessions

- Klassrumskartan (Group Seating Studio) Backend Skeleton (ST-23-01).
  - Bootstrap endpoint provisioning lesson modes and feature flags.
- Klassrumskartan (Group Seating Studio) Planning (Slice 1).
  - `docs/adr/adr-0069-group-seating-studio-domain-model.md`
  - `docs/backlog/epics/epic-23-group-seating-studio.md`
- Older history: see `.agents/readme-first.md` + `docs/`.

## Verification

- 2026-03-20: `pdm run pytest tests/integration/database/test_classroom_planner_migration.py` (PASSED, verified upgrade/downgrade/upgrade idempotency).
- 2026-03-20: `pdm run pytest tests/unit/application/apps/classroom_planner tests/unit/web/apps/classroom_planner` (PASSED 100%).
- 2026-03-20: Live `curl` check: created test roster and room template, verified they persist and are listable.
- 2026-03-20: `pdm run lint` and `pdm run docs-validate` PASSED.

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
```

## Known Issues / Risks

- Mutually dependent foreign keys between `tools` and `tool_versions` cause a warning during Alembic autogeneration (SAWarning: Cannot correctly sort tables).
- Migration idempotency tests require a running Docker daemon.

## Next Steps

- ST-23-03: Implement the Group Assignment Board (UI) where students can be dragged into groups.
- ST-23-04: Implement the Seat Assignment Canvas (UI) for spatial placement.
