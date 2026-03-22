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
- Completed: `ST-24-01`, `ST-24-05`, `ST-24-02`, and `PR-0090` (Klassrumskartan grouping draft history contract).

## Status

- PR-0090 is DONE. Implemented bounded undo/redo history (10 steps) inside the active grouping draft.
- Backend contract: `GroupingHistoryStatus` domain model, `history_stack` (JSONB) and `undo_index` (Int) in DB.
- Repository: `PostgreSQLPlanDraftRepository` now handles history-aware `save_workspace`, `undo`, and `redo`.
- Review fixes: undo/redo now reject foreign and non-grouping drafts before any repository mutation.
- Review fixes: grouping snapshots are canonicalized so reordered-but-identical assignments/notes do not burn history steps.
- Review fixes: the roomless-seating migration downgrade now backfills a valid room template before restoring the old seating constraint, so the Slice 2 migration chain is idempotent again.
- API: Exposed `POST /api/v1/apps/classroom.group-seating-studio/drafts/{draft_id}/undo` and `/redo`.
- Infrastructure: Enabled `AsyncAttrs` on `Base` model for safe async relation access in repository methods.
- Next: PR-0091 will implement the live grouping workspace fundamentals that consume this history contract.

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

## How to Run

```bash
# Setup
docker compose up -d db && pdm run db-upgrade

# Development (backend + SPA)
ARTIFACTS_ROOT=/tmp/skriptoteket/artifacts pdm run dev-local

# Focused verification
pdm run pytest tests/unit/web/apps/classroom_planner/test_api.py -q
pdm run pytest tests/unit/infrastructure/repositories/test_classroom_planner_history_unit.py -q
```

## Known Issues / Risks

- Integration tests for repository history were moved to unit tests due to environmental loop mismatch issues in the test runner; the repository logic itself is thoroughly covered by `test_classroom_planner_history_unit.py`.
- Seating drafts do not yet push to history (intentional scope constraint for PR-0090); they will inherit the same model in ST-24-04.

## Next Steps

- Start `PR-0091` for `ST-24-03`: implement the grouping workspace fundamentals, randomizer, and manual group management on top of the draft-history contract.
- Wire frontend undo/redo UI in `PR-0092`.
