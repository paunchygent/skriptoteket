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
- Current lane: `PR-0253` / `ST-28-03` is done after `REV-PR-0253` retained implementation re-review approved the remediation evidence.
- Production: Full Vue SPA.
- Dirty worktree before this lane: `frontend/apps/skriptoteket/src/views/HomeView.vue` and `frontend/apps/skriptoteket/src/views/HomeView.spec.ts`; do not overwrite them unless the lane explicitly takes ownership.
## Status
- `REV-EPIC-28` is approved. `ADR-0076`, `EPIC-28`, and `ST-28-01` through `ST-28-05` remain the governing Skriptoteket auth-cutover spine.
- `ST-32-10` / `PR-0242` is the owner of the dedicated `/auth/login` route contract. `ST-28-02` consumes that route contract under the HuleEdu-owned session model.
- HuleEdu has accepted ADR-0039, completed `TASK-0308`, and publicly proved the shared browser-session authority after prod redeploy to `432b25ed`: auth readiness passed with `huleedu_session` / `huleedu_csrf`, and WebSocket origin admission accepted `https://skriptoteket.hule.education` with HTTP `101`.
- `PR-0250` / `ST-28-05` are done. Readiness verdict: no remaining provider-side blocker for Skriptoteket consumer implementation; `PR-0251` may start from the retained HuleEdu shared browser-session conformance contract.
- `PR-0251` first frontend slice is implemented: `frontend/apps/skriptoteket/src/api/sharedAuth.ts` owns HuleEdu session/CSRF URLs and maps shared session policy, `useAuthStore.bootstrap()` no longer calls `/api/v1/auth/me`, and unsafe API writes fetch shared CSRF without bearer headers.
- `REV-PR-0251` now approves the retained implementation re-review after `PR-0255`; the app-local continuation remediation is review-clean.
- `PR-0255` is done after implementation review fixes: app continuation verifies signed HuleEdu `InternalIdentityContextV1` headers with required `org_id`, `tenant_id`, `roles`, and `grants`, resolves existing local HuleEdu projections by `(auth_provider, external_id)`, returns `local_user` + `profile`, and keeps user auto-provisioning blocked until HuleEdu provides signed email claims.
- `PR-0253` / `ST-28-03` is done. `REV-PR-0253` approved the retained implementation re-review on 2026-04-12 after checking removed zombie browser-session protocol/model/config/fixture surfaces, provisioning-required UX for authenticated HuleEdu subjects without local projections, strengthened live browser `/api` edge proof with a test gateway injector, and docs/rules updated away from removed local password-form smoke commands.
- Product identity realm correction is now recorded in `docs/reference/ref-hule-education-product-identity-realms-and-skriptoteket-standalone-identity.md`: Hule Education owns the shared browser edge/session ceremony, but Skriptoteket standalone identity must remain a product realm with explicit ADR/story follow-up.
- `PR-0253` follow-up boundary refinement is implemented: login anchors use a dedicated browser ceremony helper (`VITE_HULEEDU_AUTH_ENTRY_URL`) instead of `/v1/auth/login`, user-facing copy says `inloggning`/Skriptoteket access, and docs preserve `AuthProvider.LOCAL` / local identity data as product-domain concepts rather than browser-session authority.
- Post-`PR-0253` login planning is scaffolded: `ADR-0083` plus `ST-28-06` through `ST-28-10`. `PR-0255` stays complete as foundation; `ST-28-04` / `PR-0254` is now blocked behind `ADR-0083`, login ceremony, standalone lifecycle, and realm-aware projection, then becomes the final realm-aware cross-app proof.
- Reviewer advice acted on: `frontend/apps/skriptoteket/src/stores/ai.ts` now fails closed while `auth.aiPolicy` is missing, and `frontend/apps/skriptoteket/src/stores/ai.spec.ts` freezes that missing app-local AI bootstrap does not allow remote providers.
- `PR-0251` continuation slice is implemented: `GET /api/v1/profile/app-continuation` returns runtime `ai_policy` plus profile AI preferences, `useAuthStore.bootstrap()` performs HuleEdu session first and app-local continuation second, and editor AI chat/completions/edit-ops no longer read AI preferences from local `Session` fields.
- `PR-0252` is implemented: direct protected entry, app-local `401` recovery, and top-level `/auth/login?next=...` return preserve the dedicated auth-entry contract on the HuleEdu-owned session model. Live proof uses the real backend app-continuation route, signed HuleEdu request context, DB projection, and Vite `/api` proxy. Shared proof helpers now live in `scripts/_playwright_huleedu_auth.py`.
- Independent `skriptoteket_reviewer` pass for `PR-0252` approved the implementation with no actionable findings. Residual note: the live proof covers canonical `/editor`; richer query/hash destinations are covered by focused Vitest.
- `PR-0253` preserved local RBAC by resolving signed HuleEdu subjects to existing Skriptoteket `User` projections and enforcing local `User.role`; HuleEdu roles/grants remain context metadata, not Skriptoteket admin/contributor/superuser assignment.
- Post-`PR-0253` auth observability rule: do not recreate `skriptoteket_active_sessions` from local state. Future gauges/counters should measure HuleEdu signed-context verification/projection outcomes or local RBAC inventory such as `skriptoteket_users_by_role` when explicitly enabled.
- Skriptoteket should not create a second integration epic. Implementation now lives as PR-sized tasks under existing `EPIC-28`:
  - `PR-0250` ingests HuleEdu provider conformance and records cutover readiness.
  - `PR-0251` cuts the SPA auth store/API client over to `GET https://api.hule.education/v1/auth/session` plus CSRF.
  - `PR-0255` remediates `REV-PR-0251` implementation findings before `PR-0251` close-out; retained `REV-PR-0251` re-review is approved.
  - `PR-0252` preserves `/auth/login?next=...` interruption and return-to-origin behavior on the shared session.
  - `PR-0253` removes obsolete Skriptoteket-local browser auth ownership and regenerates/realigns contracts; retained implementation review is approved.
  - `PR-0254` adds the realm-aware cross-app Playwright smoke and operator runbook proof after `ADR-0083` / `ST-28-07` through `ST-28-09`.
- `EPIC-35` remains downstream of the shared launch topology and should consume the same `api.hule.education` / `skriptoteket.hule.education` assumptions, not recreate them.
## Verification
- `pdm run docs-validate` (pass on 2026-04-11 after `PR-0250` rereview close-out).
- `pdm run docs-validate` (pass on 2026-04-11 after `PR-0251` progress/verification update).
- `pdm run fe-test -- --run src/api/sharedAuth.spec.ts src/stores/auth.spec.ts src/api/client.spec.ts` (pass on 2026-04-11; 55 tests).
- `pdm run fe-type-check` (pass on 2026-04-11).
- `pdm run fe-lint` (pass on 2026-04-11).
- `pdm run docs-validate` (pass on 2026-04-11 after adding `ADR-0082` / `REV-PR-0251` docs gate).
- `pdm run docs-validate` (pass on 2026-04-11 after approving `REV-PR-0251` and accepting `ADR-0082`).
- `pdm run fe-test -- --run src/stores/ai.spec.ts src/stores/auth.spec.ts src/api/sharedAuth.spec.ts src/api/client.spec.ts` (pass on 2026-04-11; 57 tests).
- `pdm run fe-type-check` (pass on 2026-04-11 after AI fail-closed guard).
- `pdm run fe-lint` (pass on 2026-04-11 after AI fail-closed guard).
- `pdm run docs-validate` (pass on 2026-04-11 after recording AI fail-closed review follow-up).
- `pdm run pytest -q tests/unit/web/test_profile_app_continuation_api.py tests/unit/web/test_editor_inline_completion_api.py` (pass on 2026-04-11; 12 tests).
- `pdm run fe-test -- --run src/stores/auth.spec.ts src/stores/ai.spec.ts src/api/sharedAuth.spec.ts src/api/client.spec.ts` (pass on 2026-04-11; 58 tests).
- `pdm run typecheck` (pass on 2026-04-11 after continuation endpoint).
- `pdm run fe-type-check` (pass on 2026-04-11 after continuation endpoint).
- `pdm run fe-lint` (pass on 2026-04-11 after continuation endpoint).
- `pdm run lint` (pass on 2026-04-11 after continuation endpoint).
- `pdm run docs-validate` (pass on 2026-04-11 after continuation endpoint docs update).
- `pdm run docs-validate` (pass on 2026-04-11 after retained `REV-PR-0251` implementation review update).
- `pdm run docs-validate` (pass on 2026-04-11 after adding `PR-0255` remediation task).
- `pdm run docs-validate` (pass on 2026-04-11 after `REV-PR-0255` re-review update).
- `pdm run docs-validate` (pass on 2026-04-11 after revising `PR-0255` for `REV-PR-0255` clarification requests).
- `pdm run docs-validate` (pass on 2026-04-11 after approving revised `PR-0255` in `REV-PR-0255`).
- `pdm run pytest -q tests/unit/web/test_profile_app_continuation_api.py tests/unit/web/test_editor_inline_completion_api.py` (pass on 2026-04-11 after `PR-0255` review fixes; 31 tests).
- `pdm run fe-test -- --run src/api/sharedAuth.spec.ts src/stores/auth.spec.ts src/stores/ai.spec.ts src/api/client.spec.ts` (pass on 2026-04-11 after `PR-0255`; 58 tests).
- `pdm run pytest -q tests/unit/web/test_profile_app_continuation_api.py` (pass on 2026-04-11 after required signed payload remediation; 22 tests).
- `pdm run fe-test -- --run src/api/sharedAuth.spec.ts src/stores/auth.spec.ts src/api/client.spec.ts` (pass on 2026-04-11 after auth-store SRP split; 56 tests).
- `docker compose up -d db` and `pdm run db-upgrade` (pass on 2026-04-11 before real backend Playwright proof).
- `pdm run pr-0255-auth-bootstrap --start-backend --start-vite` (pass on 2026-04-11; real `pdm run dev` backend verified signed context `200`, missing context `401`, SPA `/editor` opened after real continuation route through Vite `/api` proxy).
- `pdm run fe-type-check` (pass on 2026-04-11 after auth-store SRP split).
- `pdm run fe-lint` (pass on 2026-04-11 after auth-store SRP split).
- `pdm run typecheck` (pass on 2026-04-11 after `PR-0255` review fixes).
- `pdm run docs-validate` (pass on 2026-04-11 after `PR-0255` review fixes).
- `pdm run lint` (pass on 2026-04-11 after `PR-0255` review fixes).
- `pdm run typecheck` (pass on 2026-04-11 after `PR-0255`).
- `pdm run fe-type-check` (pass on 2026-04-11 after `PR-0255`).
- `pdm run fe-lint` (pass on 2026-04-11 after `PR-0255`).
- `pdm run docs-validate` (pass on 2026-04-11 after `PR-0255` implementation docs).
- `pdm run lint` (pass on 2026-04-11 after `PR-0255`).
- `pdm run pytest -q tests/unit/web/test_profile_app_continuation_api.py` (pass on 2026-04-11 during retained `REV-PR-0251` re-review; 22 tests).
- `git diff --check` (pass on 2026-04-11 during retained `REV-PR-0251` re-review).
- `lsof -nP -iTCP:8000 -sTCP:LISTEN` and `lsof -nP -iTCP:5173 -sTCP:LISTEN` (no listeners on 2026-04-11 during retained `REV-PR-0251` re-review).
- `pdm run docs-validate` (pass on 2026-04-11 after retained `REV-PR-0251` approval docs update).
- Previous retained proof for `/auth/login` lives in `ST-32-10` / `PR-0242` docs and the prior handoff compaction history in `docs/reference/ref-development-changelog.md`.
- `pdm run fe-test -- --run src/router/index.spec.ts src/components/auth/AuthLoginPanel.spec.ts src/views/AuthLoginView.spec.ts src/composables/auth/authEntryNavigation.spec.ts src/App.spec.ts` (pass on 2026-04-11 after `PR-0252`; 26 tests).
- `pdm run fe-test -- --run src/api/sharedAuth.spec.ts src/stores/auth.spec.ts src/api/client.spec.ts` (pass on 2026-04-11 after `PR-0252`; 56 tests).
- `pdm run python -m py_compile scripts/_playwright_huleedu_auth.py scripts/playwright_pr_0252_auth_return_to_origin.py scripts/playwright_pr_0255_auth_bootstrap.py` (pass on 2026-04-11 after `PR-0252` proof helper extraction).
- `pdm run fe-type-check` (pass on 2026-04-11 after `PR-0252`).
- `pdm run db-upgrade` (pass on 2026-04-11 before `PR-0252` live proof).
- `ARTIFACTS_ROOT=.artifacts/local-tool-artifacts pdm run pr-0252-auth-return --start-backend --start-vite` (pass on 2026-04-11; direct `/editor` -> `/auth/login?next=/editor`, app-local `401` recovery preserved `next`, authenticated return resumed `/editor`; artifacts in `.artifacts/playwright-pr-0252-auth-return-to-origin/`).
- `lsof -nP -iTCP:8000 -sTCP:LISTEN` and `lsof -nP -iTCP:5173 -sTCP:LISTEN` (no listeners after `PR-0252` live proof on 2026-04-11).
- `pdm run typecheck` (pass on 2026-04-11 after `PR-0252`).
- `pdm run docs-validate` (pass on 2026-04-11 after retaining `REV-PR-0253` and revising `PR-0253`).
- `pdm run docs-validate` (pass on 2026-04-11 after approving `REV-PR-0253` through docs-quality closeout).
- `pdm run pytest tests/unit/web/test_profile_app_continuation_api.py tests/unit/web/test_pr_0253_auth_retirement_contracts.py tests/unit/application/identity/test_update_ai_settings_handler.py tests/unit/application/identity/test_reset_password_handler.py -q` (pass on 2026-04-11 after `PR-0253`; 38 tests).
- `pdm run fe-test -- --run src/components/auth/AuthLoginPanel.spec.ts src/api/sharedAuth.spec.ts src/stores/auth.spec.ts src/stores/authBootstrap.spec.ts src/router/index.spec.ts src/views/AuthLoginView.spec.ts src/App.spec.ts` (pass on 2026-04-11 after `PR-0253`; 48 tests).
- `pdm run fe-type-check` (pass on 2026-04-11 after `PR-0253`).
- `pdm run typecheck` (pass on 2026-04-11 after `PR-0253`).
- `pdm run db-upgrade` (pass on 2026-04-11; applied `c1d2e3f4a5b6`).
- `pdm run pytest -q tests/integration/test_migration_c1d2e3f4a5b6_idempotent.py -m docker --override-ini addopts=''` (pass on 2026-04-11; sessions drop/downgrade proof).
- `pdm run python -m scripts.check_migration_test_coverage` (pass on 2026-04-11; head=`c1d2e3f4a5b6`).
- `pdm run python -m py_compile scripts/_playwright_huleedu_auth.py scripts/playwright_pr_0253_auth_retirement.py scripts/playwright_pr_0252_auth_return_to_origin.py scripts/playwright_pr_0255_auth_bootstrap.py` (pass on 2026-04-11).
- `ARTIFACTS_ROOT=.artifacts/local-tool-artifacts pdm run pr-0253-auth-retirement --start-backend --start-vite` (pass on 2026-04-11 after remediation; signed read/write `200`, stale-CSRF missing-context `401`, missing projection `401`, `/auth/login` ceremony handoff, browser gateway-injected `/editor`, and provisioning-required UX).
- `pdm run docs-validate` (pass on 2026-04-11 after `PR-0253` implementation docs).
- `pdm run lint` (pass on 2026-04-11 after `PR-0253`).
- `git diff --check` (pass on 2026-04-11 after `PR-0253`).
- `pdm run pytest tests/unit/web -q` (pass on 2026-04-11 after `REV-PR-0253` remediation; 276 tests).
- `pdm run pytest -q tests/unit/web/test_pr_0253_auth_retirement_contracts.py tests/unit/web/test_profile_app_continuation_api.py tests/unit/web/test_me_api_routes.py tests/unit/web/test_editor_chat_api.py tests/unit/web/apps/classroom_planner/test_guest_upgrade_api.py tests/unit/web/test_observability_routes.py` (pass on 2026-04-11 after `REV-PR-0253` remediation; 44 tests).
- `pdm run fe-test -- --run src/stores/auth.spec.ts src/router/index.spec.ts src/views/AuthProvisioningRequiredView.spec.ts src/components/auth/AuthLoginPanel.spec.ts src/api/sharedAuth.spec.ts src/api/client.spec.ts src/App.spec.ts` (pass on 2026-04-11 after `REV-PR-0253` remediation; 71 tests).
- `pdm run python -m py_compile scripts/_playwright_huleedu_auth.py scripts/playwright_pr_0253_auth_retirement.py scripts/playwright_pr_0252_auth_return_to_origin.py scripts/playwright_pr_0255_auth_bootstrap.py` (pass on 2026-04-11 after `REV-PR-0253` remediation).
- `pdm run fe-type-check` (pass on 2026-04-11 after `REV-PR-0253` remediation).
- `pdm run typecheck` (pass on 2026-04-11 after `REV-PR-0253` remediation).
- `pdm run db-upgrade` (pass on 2026-04-11 after `REV-PR-0253` remediation; database already at the PR-0253 migration head).
- `pdm run docs-validate` (pass on 2026-04-11 after `REV-PR-0253` remediation closeout).
- `pdm run lint` (pass on 2026-04-11 after `REV-PR-0253` remediation closeout).
- `git diff --check` (pass on 2026-04-11 after `REV-PR-0253` remediation closeout).
- `pdm run docs-validate` (pass on 2026-04-11 after correcting `REV-PR-0253` reviewer-owned acceptance gate status).
- `pdm run docs-validate` (pass on 2026-04-11 after adding product identity realm reference and links).
- `pdm run docs-validate` (pass on 2026-04-11 after persisting `REV-PR-0253` implementation review as `changes_requested`).
- `pdm run docs-validate` (pass on 2026-04-11 after aligning `PR-0253`, `ST-28-03`, and `EPIC-28` with the `REV-PR-0253` implementation verdict).
- `pdm run docs-validate` (pass on 2026-04-11 after adding the `REV-PR-0253` reviewer-owned remediation checklist).
- `pdm run fe-test -- --run src/api/sharedAuth.spec.ts src/components/auth/AuthLoginPanel.spec.ts src/views/AuthProvisioningRequiredView.spec.ts src/stores/auth.spec.ts` (pass on 2026-04-11 after splitting auth ceremony URL from shared auth API URL; 37 tests).
- `pdm run pytest -q tests/unit/web/test_pr_0253_auth_retirement_contracts.py` (pass on 2026-04-11 after widening the SPA `/v1/auth/login` no-link guard; 7 tests).
- `pdm run fe-type-check` (pass on 2026-04-11 after auth ceremony helper/copy update).
- `pdm run python -m py_compile scripts/playwright_pr_0253_auth_retirement.py` (pass on 2026-04-11 after proof copy/selector update).
- `pdm run docs-validate` (pass on 2026-04-11 after PR-0253 product-identity boundary refinement).
- `pdm run lint` (pass on 2026-04-11 after PR-0253 product-identity boundary refinement).
- `git diff --check` (pass on 2026-04-11 after PR-0253 product-identity boundary refinement).
- Playwright MCP live check on `http://127.0.0.1:5173/auth/login?next=/editor` with shared-session route mocked anonymous: rendered `Fortsätt till inloggning`, no local form, href `https://api.hule.education/auth/login?app=skriptoteket&next=http%3A%2F%2F127.0.0.1%3A5173%2Feditor`.
- `pdm run docs-validate` (pass on 2026-04-11 after scaffolding `ADR-0083`, `ST-28-06` through `ST-28-10`, and adapting `ST-28-04` / `PR-0254`).
- `git diff --check` (pass on 2026-04-11 after scaffolding `ADR-0083`, `ST-28-06` through `ST-28-10`, and adapting `ST-28-04` / `PR-0254`).
- `pdm run pytest -q tests/unit/web/test_pr_0253_auth_retirement_contracts.py` (pass on 2026-04-12 during retained `REV-PR-0253` re-review; 7 tests).
- `pdm run docs-validate` (pass on 2026-04-12 during retained `REV-PR-0253` re-review).
- `pdm run fe-type-check` (pass on 2026-04-12 during retained `REV-PR-0253` re-review).
- `pdm run typecheck` (pass on 2026-04-12 during retained `REV-PR-0253` re-review).
- `pdm run pytest -q tests/unit/web/test_profile_app_continuation_api.py tests/unit/web/test_me_api_routes.py tests/unit/web/test_editor_chat_api.py tests/unit/web/apps/classroom_planner/test_guest_upgrade_api.py tests/unit/web/test_observability_routes.py` (pass on 2026-04-12 during retained `REV-PR-0253` re-review; 38 tests).
- `pdm run fe-test -- --run src/stores/auth.spec.ts src/router/index.spec.ts src/views/AuthProvisioningRequiredView.spec.ts src/components/auth/AuthLoginPanel.spec.ts src/api/sharedAuth.spec.ts src/api/client.spec.ts src/App.spec.ts` (pass on 2026-04-12 during retained `REV-PR-0253` re-review; 74 tests).
- `ARTIFACTS_ROOT=.artifacts/local-tool-artifacts pdm run pr-0253-auth-retirement --start-backend --start-vite` (pass on 2026-04-12 during retained `REV-PR-0253` re-review; signed read/write `200`, stale-CSRF missing-context `401`, missing projection `401`, `/auth/login` ceremony handoff, browser gateway-injected `/editor`, and provisioning-required UX).
- `pdm run lint` (pass on 2026-04-12 during retained `REV-PR-0253` re-review).
- `git diff --check` (pass on 2026-04-12 during retained `REV-PR-0253` re-review).
## How to Run
```bash
pdm run docs-validate
pdm run typecheck
pdm run lint
pdm run fe-type-check
pdm run fe-test -- --run src/stores/ai.spec.ts src/stores/auth.spec.ts src/api/sharedAuth.spec.ts src/api/client.spec.ts
pdm run pytest -q tests/unit/web/test_profile_app_continuation_api.py tests/unit/web/test_editor_inline_completion_api.py
pdm run pr-0253-auth-retirement --start-backend --start-vite
pdm run pr-0252-auth-return --start-backend --start-vite
pdm run pr-0255-auth-bootstrap --start-backend --start-vite
pdm run fe-test -- --run src/router/index.spec.ts src/components/auth/AuthLoginPanel.spec.ts src/views/AuthLoginView.spec.ts src/composables/auth/authEntryNavigation.spec.ts src/App.spec.ts
```
## Known Issues / Risks
- `PR-0251` must preserve Skriptoteket-local role, profile, AI policy, and app authorization semantics without reinstating local browser auth authority, bearer storage, or direct HuleEdu Identity calls.
- `REV-PR-0251` retained re-review is approved; `PR-0254` remains for Docker-first realm-aware cross-app proof after the new identity-realm path.
- Canonical Docker-first live testing after the auth switch belongs to `PR-0254` after `ADR-0083` / realm stories; do not resurrect local password-form smoke scripts for that lane.
- `HomeView.vue` / `HomeView.spec.ts` had pre-existing local changes before this docs lane; keep them separate from EPIC-28 scaffolding.
- Public guest mode remains browser-owned and route-sensitive; clear local public guest storage before treating a stale guest state as an auth-cutover regression.
- `REV-PR-0253` is approved; `PR-0253` / `ST-28-03` are done.
- `REV-PR-0253` now has an additional product identity realm concern: do not treat local browser-session retirement as removal of standalone Skriptoteket identity.
- `PR-0254` owns Docker-first cross-app auth proof after the `ADR-0083` realm/login/projection path; do not resurrect removed local password-form smoke commands for that lane.
## Next Steps
- Review and approve `ADR-0083`, then plan implementation PRs for `ST-28-07` through `ST-28-09` before taking `PR-0254`.
- Start the agreed next auth lane from `ST-28-06` / `ADR-0083`; keep `PR-0254` blocked until the realm-aware login/projection path is implemented.
