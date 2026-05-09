# 2026-05-09 PR-0308 Smart Settings Preference Continuity

## Summary

Implemented `PR-0308` under `ST-29-11` to remediate the over-broad `PR-0306`
Smart default. Authenticated Klassrumskartan Smart preferences are now
profile-owned and cross-browser persisted through
`/api/v1/profile/classroom-planner-settings`. New authenticated drafts seed
Smart/history/seating-influence from nullable profile preferences. First-time
authenticated drafts keep `Smart placering` and `Historik` on but keep
`Tillämpa sittschema` off. Public guest drafts remember explicit Smart choices
only in browser storage. A follow-up review fix added an ordered frontend
preference lane so new draft creation waits for pending authenticated profile
preference writes and cannot seed from stale backend profile state.

## Key Files

- `src/skriptoteket/domain/identity/models.py`
- `src/skriptoteket/application/identity/handlers/update_classroom_planner_settings.py`
- `src/skriptoteket/application/curated_apps/classroom_planner/draft_smart_preferences.py`
- `src/skriptoteket/web/api/v1/apps_classroom_planner_preferences.py`
- `frontend/apps/skriptoteket/src/views/apps/classroomPlannerSmartPreferences.ts`
- `migrations/versions/b6c9f2a1d4e8_add_classroom_planner_smart_profile_preferences.py`
- `docs/backlog/prs/pr-0308-st-29-11-smart-settings-preference-continuity-and-seating-influence-default.md`

## Verification

- `pdm run fe-gen-api-types`
- `pdm run pytest tests/unit/application/apps/classroom_planner/test_draft_lifecycle.py tests/unit/web/apps/classroom_planner/test_api.py tests/unit/application/identity/test_update_ai_settings_handler.py`
- `pdm run pytest tests/unit/application/identity/test_update_classroom_planner_settings_handler.py`
- `pdm run fe-test --run src/views/apps/useClassroomState.spec.ts src/views/apps/classroomPlannerSmartPreferences.spec.ts src/views/apps/classroomPlannerSmartRuleActions.spec.ts src/views/apps/classroomPlannerGuestDraftWorkspace.spec.ts`
- `pdm run pytest -m docker 'tests/integration/test_migration_revision_coverage_idempotent.py::test_uncovered_migration_revision_is_idempotent[b6c9f2a1d4e8]'`
- `pdm run lint`
- `pdm run typecheck`
- `pdm run fe-lint`
- `pdm run fe-type-check`
- `pdm run fe-build`
- `pdm run docs-validate`
- `pdm run handoff-validate`
- `pdm run alembic heads`
- `git diff --check`
