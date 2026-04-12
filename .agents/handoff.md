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
- Current lane: `ST-28-04` / `PR-0254` ready next after `PR-0258` remediation.
- Production: Full Vue SPA.
- Handoff compaction moved previous auth-cutover history into `docs/reference/ref-development-changelog.md`.
## Status
- `ST-28-06`, `ST-28-07`, `ST-28-08`, and `ST-28-09` are done under `EPIC-28`.
- `ST-28-04` / `PR-0254` is ready as the final realm-aware Docker/operator proof lane.
- `PR-0258` replaces the temporary `(auth_provider, external_id)` bridge with
  `identity_projections(product_identity_realm, realm_subject_id)` and removes `users.external_id`.
- Migration `e7b3a9c4d1f2` creates `identity_projections` and `identity_projection_events`,
  preflights/backfills old HuleEdu rows into `huleedu_school`, and fails ambiguous provider-subject
  data before dropping the legacy field.
- App continuation now requires signed `active_app=skriptoteket`, accepted realm, and
  `realm_subject_id`; invalid product context remains a generic auth ceremony/context error.
- First-login provisioning requires signed `email` and strict `email_verified=true`; newly
  provisioned Skriptoteket users default to local role `user`.
- Matching email without an explicit link fails closed into linking/provisioning-required UX; local
  contributor/admin/superuser remain app-local promotions.
- Runtime `identity_projection_events` now include request correlation ids when available.
- First-login user/projection creation uses no-conflict repository inserts and DB-backed recovery
  tests for same-subject, same-email, and projection unique-conflict races.
- Public "Logga in" actions open the HuleEdu login ceremony directly; `/auth/login?next=...`
  remains only as an auto-handoff/fallback route.
## Verification
- `pdm run pytest -q tests/unit/web/test_profile_app_continuation_api.py tests/unit/web/test_profile_app_continuation_context_api.py tests/unit/web/test_profile_app_continuation_dependencies_api.py` (pass; 34 tests).
- `pdm run pytest -q tests/integration/application/test_huleedu_app_projection_concurrency.py` (pass; 3 tests).
- `pdm run pytest -q tests/integration/test_migration_e7b3a9c4d1f2_idempotent.py -m docker --override-ini addopts=''` (pass; 4 tests).
- `pdm run python -m scripts.check_migration_test_coverage` (pass; 67 revisions covered).
- `pdm run fe-gen-api-types` (pass).
- `pdm run fe-test -- --run src/router/index.spec.ts src/views/AuthLoginView.spec.ts src/components/auth/AuthLoginPanel.spec.ts src/components/layout/LandingLayout.spec.ts src/views/HomeView.spec.ts src/views/apps/ClassroomPlannerGuestOverviewView.spec.ts src/composables/auth/authEntryNavigation.spec.ts src/stores/auth.spec.ts` (pass; 66 tests).
- `pdm run typecheck`, `pdm run lint`, `pdm run fe-type-check`, and `pdm run fe-lint` (pass).
- `ARTIFACTS_ROOT=.artifacts/local-tool-artifacts pdm run pr-0258-auth-projection --start-backend --start-vite --gateway-base-url http://127.0.0.1:8000` (pass; artifacts in `.artifacts/playwright-pr-0258-auth-projection/`, including `login-auto-handoff.png`).
- `pdm run docs-validate`, `git diff --check`, and `pdm run precommit-run` (pass).
## How to Run
```bash
pdm run docs-validate
pdm run lint
pdm run typecheck
pdm run fe-type-check
pdm run fe-lint
pdm run pytest -q tests/unit/web/test_profile_app_continuation_api.py tests/unit/web/test_profile_app_continuation_context_api.py tests/unit/web/test_profile_app_continuation_dependencies_api.py
pdm run pytest -q tests/integration/application/test_huleedu_app_projection_concurrency.py
pdm run pytest -q tests/integration/test_migration_e7b3a9c4d1f2_idempotent.py -m docker --override-ini addopts=''
ARTIFACTS_ROOT=.artifacts/local-tool-artifacts pdm run pr-0258-auth-projection --start-backend --start-vite --gateway-base-url http://127.0.0.1:8000
```
## Known Issues / Risks
- `PR-0254` still owns the final Docker/operator cross-app proof after this remediated realm-aware
  projection slice; do not treat `PR-0258` as the final cross-app certification.
- Local full-auth ceremony livetests require a local or non-production HuleEdu Gateway whose
  allowed return origins include the exact dev origin, such as `http://localhost:5173` or
  `http://127.0.0.1:5173`.
- Do not reintroduce app-local browser auth or direct browser-to-Identity calls.
## Next Steps
- Start `PR-0254` as the final realm-aware cross-app Docker/operator proof.
- Follow with `ST-28-10` auth outcome observability for gateway/session, realm, projection, and
  local RBAC outcomes.
