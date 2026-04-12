# Session Handoff
Keep this file updated so the next session can pick up work quickly.
## Editing Rules (do not break structure)
- Keep the headings and section order exactly as-is; only fill in content.
- Use short bullets; include key file paths (e.g., `src/...`, `docs/...`) and exact commands.
- Do not paste large code blocks; link to files.
- Never include secrets/tokens/passwords or personal data.
- Keep this file under 200 lines.
- When compacting this file, move non-session-vital history into repo long-term memory at `docs/reference/ref-development-changelog.md` first.
## Snapshot
- Date: 2026-04-12
- Branch: `main` + local changes
- Current lane: `ST-28-09` / `PR-0258` implemented and locally validated.
- Production: Full Vue SPA.
- Handoff compaction moved previous auth-cutover history into `docs/reference/ref-development-changelog.md`.
## Status
- `ST-28-06`, `ST-28-07`, `ST-28-08`, and `ST-28-09` are done under `EPIC-28`.
- `ST-28-04` / `PR-0254` is ready as the final realm-aware Docker/operator cross-app proof.
- `PR-0258` replaces the temporary `(auth_provider, external_id)` bridge with
  `identity_projections(product_identity_realm, realm_subject_id)` and removes `users.external_id`.
- Migration `e7b3a9c4d1f2` creates `identity_projections` and `identity_projection_events`,
  preflights/backfills old HuleEdu rows into `huleedu_school`, and fails ambiguous provider-subject
  data before dropping the legacy field.
- App continuation now requires signed `active_app=skriptoteket`, accepted realm, and
  `realm_subject_id`; missing/unsupported context fails closed.
- First-login provisioning now requires signed `email` and strict `email_verified=true`; newly
  provisioned Skriptoteket users default to local role `user`.
- Matching email without an explicit link fails closed into linking/provisioning-required UX; local
  contributor/admin/superuser remain app-local promotions.
- Projection outcomes are audit-recorded in `identity_projection_events`.
- Frontend auth bootstrap maps `missing_huleedu_app_projection`, `identity_linking_required`, and
  `inactive_or_missing_local_user` to local access required UX without reviving local browser auth.
- `scripts/playwright_pr_0258_auth_projection.py` is the live proof for first-login provisioning,
  idempotent reuse, missing signed email, duplicate-email linking-required, and SPA bootstrap.
## Verification
- `pdm run pytest -q tests/unit/web/test_profile_app_continuation_api.py` (pass; 32 tests).
- `pdm run pytest -q tests/unit/web/test_me_api_routes.py tests/unit/web/test_favorites_api_routes.py tests/unit/web/test_tools_api_routes.py tests/unit/web/test_editor_chat_api.py tests/unit/web/test_editor_inline_completion_api.py tests/unit/web/test_editor_edit_ops_preview_apply_api.py tests/unit/web/test_apps_classroom_planner_imports.py tests/unit/web/apps/classroom_planner/test_smart_grouping_api.py tests/unit/web/apps/classroom_planner/test_smart_seating_api.py tests/unit/web/apps/classroom_planner/test_guest_upgrade_api.py tests/unit/web/reagent_prep_chef` (pass; 64 tests).
- `pdm run fe-gen-api-types` (pass).
- `pdm run fe-test -- --run src/stores/auth.spec.ts src/api/sharedAuth.spec.ts src/composables/editor/useEditorChat.spec.ts` (pass; 47 tests).
- `pdm run pytest -q tests/integration/test_migration_e7b3a9c4d1f2_idempotent.py -m docker --override-ini addopts=''` (pass; 4 tests).
- `pdm run pytest -q tests/integration/infrastructure/repositories/test_identity_projection_repository.py tests/integration/infrastructure/repositories/test_user_repository.py` (pass; 5 tests).
- `docker compose up -d db` and `pdm run db-upgrade` (pass; local DB applied `e7b3a9c4d1f2`).
- `ARTIFACTS_ROOT=.artifacts/local-tool-artifacts pdm run pr-0258-auth-projection --start-backend --start-vite --gateway-base-url http://127.0.0.1:8000` (pass; artifacts in `.artifacts/playwright-pr-0258-auth-projection/`).
- `pdm run format`, `pdm run lint-fix`, `pdm run lint`, `pdm run typecheck`, `pdm run fe-type-check`, and `pdm run fe-lint` passed during implementation.
## How to Run
```bash
pdm run docs-validate
pdm run lint
pdm run typecheck
pdm run fe-type-check
pdm run fe-lint
pdm run pytest -q tests/unit/web/test_profile_app_continuation_api.py
pdm run pytest -q tests/integration/test_migration_e7b3a9c4d1f2_idempotent.py -m docker --override-ini addopts=''
ARTIFACTS_ROOT=.artifacts/local-tool-artifacts pdm run pr-0258-auth-projection --start-backend --start-vite --gateway-base-url http://127.0.0.1:8000
```
## Known Issues / Risks
- `PR-0254` still owns the final Docker/operator cross-app proof after this realm-aware projection
  slice; do not treat `PR-0258` as the final cross-app certification.
- Local full-auth ceremony livetests require a local or non-production HuleEdu Gateway whose
  allowed return origins include the exact dev origin, such as `http://localhost:5173` or
  `http://127.0.0.1:5173`.
- Do not reintroduce app-local browser auth or direct browser-to-Identity calls.
## Next Steps
- Start `PR-0254` next as the realm-aware Docker/operator cross-app proof.
- Follow with `ST-28-10` auth outcome observability for gateway/session, realm, projection, and
  local RBAC outcomes.
