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
- Current lane: `ST-28-08` / `PR-0257` is done; standalone lifecycle URLs now hand off to HuleEdu Gateway ceremonies.
- Production: Full Vue SPA.
- Dirty worktree before this lane included docs from `ST-28-06` / `ST-28-07`; preserve unrelated user changes if any appear.
## Status
- `REV-EPIC-28` is approved. `ADR-0076`, `EPIC-28`, and `ST-28-01` through `ST-28-05` remain the governing Skriptoteket auth-cutover spine.
- `ST-32-10` / `PR-0242` is the owner of the dedicated `/auth/login` route contract. `ST-28-02` consumes that route contract under the HuleEdu-owned session model.
- HuleEdu has accepted ADR-0039, completed `TASK-0308`, and publicly proved the shared browser-session authority after prod redeploy to `432b25ed`: auth readiness passed with `huleedu_session` / `huleedu_csrf`, and WebSocket origin admission accepted `https://skriptoteket.hule.education` with HTTP `101`.
- `PR-0250` / `ST-28-05` are done. Readiness verdict: no remaining provider-side blocker for Skriptoteket consumer implementation; `PR-0251` may start from the retained HuleEdu shared browser-session conformance contract.
- `PR-0251` first frontend slice is implemented: `frontend/apps/skriptoteket/src/api/sharedAuth.ts` owns HuleEdu session/CSRF URLs and maps shared session policy, `useAuthStore.bootstrap()` no longer calls `/api/v1/auth/me`, and unsafe API writes fetch shared CSRF without bearer headers.
- `REV-PR-0251` now approves the retained implementation re-review after `PR-0255`; the app-local continuation remediation is review-clean.
- `PR-0255` is done after implementation review fixes: app continuation verifies signed HuleEdu `InternalIdentityContextV1` headers, resolves existing local HuleEdu projections by `(auth_provider, external_id)`, returns `local_user` + `profile`, and keeps user auto-provisioning blocked until HuleEdu provides signed email claims.
- `PR-0253` / `ST-28-03` is done. `REV-PR-0253` approved the retained implementation re-review on 2026-04-12 after checking removed zombie browser-session protocol/model/config/fixture surfaces, provisioning-required UX for authenticated HuleEdu subjects without local projections, strengthened live browser `/api` edge proof with a test gateway injector, and docs/rules updated away from removed local password-form smoke commands.
- Product identity realm correction is recorded in `docs/reference/ref-hule-education-product-identity-realms-and-skriptoteket-standalone-identity.md` and frozen by `ADR-0083` / `REV-ST-28-06`: Hule Education owns the shared browser edge/session ceremony, but Skriptoteket standalone identity remains a product realm.
- `PR-0253` follow-up boundary refinement is implemented: login anchors use a dedicated browser ceremony helper (`VITE_HULEEDU_AUTH_ENTRY_URL`) instead of `/v1/auth/login`, user-facing copy says `inloggning`/Skriptoteket access, and docs preserve `AuthProvider.LOCAL` / local identity data as product-domain concepts rather than browser-session authority.
- `ST-28-06` / `REV-ST-28-06` are done: `ADR-0083` is accepted and freezes the product identity realm contract. First accepted realms are `skriptoteket_standalone` and `huleedu_school`; browser login must use a Hule Education-hosted `app=skriptoteket` ceremony; final proof requires realm-aware signed context and projection keyed by `(product_identity_realm, realm_subject_id)`; local RBAC remains `User.role`-driven.
- `ST-28-07` / `PR-0256` are done after review remediation. HuleEdu `TASK-0313` / `TASK-0314` cleared the provider blocker; Skriptoteket now sends `/auth/login` to HuleEdu `GET /auth/login` with `app=skriptoteket`, default `product_identity_realm=skriptoteket_standalone`, `return_to=/auth/callback`, and safe route-level `next`; `/auth/callback` preserves query/hash continuation; helper-level `next` drops hostile/loop values; app continuation requires `active_app=skriptoteket`, supported realm, and `realm_subject_id` before existing subject-key projection lookup.
- `ST-28-08` / `PR-0257` is done after HuleEdu `TASK-0318` closed the provider gate: `/register`, `/forgot-password`, `/reset-password`, and `/verify-email` render HuleEdu Gateway handoff links for `app=skriptoteket`, `product_identity_realm=skriptoteket_standalone`, `return_to=/auth/callback`, safe `next`, and reset/verification `token`; no local form, local browser-auth API, or direct lifecycle POST API is introduced.
- Skriptoteket should not create a second integration epic. Implementation now lives as PR-sized tasks under existing `EPIC-28`:
  - `PR-0250` ingests HuleEdu provider conformance and records cutover readiness.
  - `PR-0251` cuts the SPA auth store/API client over to `GET https://api.hule.education/v1/auth/session` plus CSRF.
  - `PR-0255` remediates `REV-PR-0251` implementation findings before `PR-0251` close-out; retained `REV-PR-0251` re-review is approved.
  - `PR-0252` preserves `/auth/login?next=...` interruption and return-to-origin behavior on the shared session.
  - `PR-0253` removes obsolete Skriptoteket-local browser auth ownership and regenerates/realigns contracts; retained implementation review is approved.
  - `PR-0256` implements `ST-28-07` and is approved after HuleEdu provider proof.
  - `PR-0257` implements `ST-28-08` consumer lifecycle handoffs after HuleEdu `TASK-0318`.
  - `PR-0254` adds the realm-aware cross-app Playwright smoke and operator runbook proof after `ST-28-07` through `ST-28-09`.
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
- `pdm run docs-validate` (pass on 2026-04-12 after `ST-28-06` / `ADR-0083` contract freeze).
- `git diff --check` (pass on 2026-04-12 after `ST-28-06` / `ADR-0083` contract freeze).
- `pdm run docs-validate` (pass on 2026-04-12 after `PR-0256` provider-contract blocker review).
- `git diff --check` (pass on 2026-04-12 after `PR-0256` provider-contract blocker review).
- `pdm run fe-test -- --run src/api/sharedAuth.spec.ts src/components/auth/AuthLoginPanel.spec.ts src/views/AuthLoginView.spec.ts src/composables/auth/authEntryNavigation.spec.ts src/router/index.spec.ts` (pass on 2026-04-12 after `PR-0256`; 35 tests).
- `pdm run test tests/unit/web/test_profile_app_continuation_api.py` (pass on 2026-04-12 after `PR-0256`; 26 tests).
- `pdm run python -m py_compile scripts/playwright_pr_0256_auth_ceremony.py` (pass on 2026-04-12 after `PR-0256` proof script).
- `docker compose up -d db` (db already running on 2026-04-12 before `PR-0256` live proof).
- `pdm run fe-type-check` (pass on 2026-04-12 after `PR-0256`).
- `pdm run typecheck` (pass on 2026-04-12 after `PR-0256`).
- `pdm run fe-lint` (pass on 2026-04-12 after `PR-0256`).
- `pdm run python -m scripts.playwright_pr_0256_auth_ceremony --start-backend --start-vite` (pass on 2026-04-12; verified provider-approved ceremony href and `/auth/callback` resumed `/editor`).
- `pdm run lint` (pass on 2026-04-12 after `PR-0256`).
- `pdm run docs-validate` (pass on 2026-04-12 after `PR-0256`).
- `git diff --check` (pass on 2026-04-12 after `PR-0256`).
- `pdm run fe-test -- --run src/api/sharedAuth.spec.ts src/components/auth/AuthLoginPanel.spec.ts src/views/AuthLoginView.spec.ts src/composables/auth/authEntryNavigation.spec.ts src/router/index.spec.ts` (pass on 2026-04-12 after `PR-0256` review remediation; 40 tests).
- `pdm run test tests/unit/web/test_profile_app_continuation_api.py` (pass on 2026-04-12 after `PR-0256` review remediation; 31 tests).
- `pdm run python -m py_compile scripts/playwright_pr_0256_auth_ceremony.py` (pass on 2026-04-12 after `PR-0256` review remediation).
- `pdm run fe-type-check` (pass on 2026-04-12 after `PR-0256` review remediation).
- `pdm run typecheck` (pass on 2026-04-12 after `PR-0256` review remediation).
- `pdm run fe-lint` (pass on 2026-04-12 after `PR-0256` review remediation).
- `pdm run python -m scripts.playwright_pr_0256_auth_ceremony --start-backend --start-vite` (pass on 2026-04-12 after review remediation; verified ceremony href and callback resumed `/editor?draft=head#debug`).
- `pdm run lint` (pass on 2026-04-12 after `PR-0256` review remediation).
- `pdm run docs-validate` (pass on 2026-04-12 after `PR-0256` review remediation).
- `git diff --check` (pass on 2026-04-12 after `PR-0256` review remediation).
- `pdm run fe-test -- --run src/api/sharedAuth.spec.ts src/views/AuthLifecycleHandoffView.spec.ts src/components/auth/AuthLoginPanel.spec.ts src/router/routes.spec.ts` (pass on 2026-04-12 after `PR-0257`; 25 tests).
- `pdm run pytest -q tests/unit/web/test_pr_0253_auth_retirement_contracts.py` (pass on 2026-04-12 after `PR-0257`; 7 tests).
- `pdm run python -m py_compile scripts/playwright_pr_0257_auth_lifecycle.py` and `pdm run python -m scripts.playwright_pr_0257_auth_lifecycle --start-vite` (pass on 2026-04-12; lifecycle handoff URLs render through Vite).
- `pdm run fe-type-check`, `pdm run fe-lint`, `pdm run typecheck`, and `pdm run lint` (pass on 2026-04-12 after `PR-0257`).
- `pdm run docs-validate` and `git diff --check` (pass on 2026-04-12 after `PR-0257` docs closeout).
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
pdm run python -m scripts.playwright_pr_0256_auth_ceremony --start-backend --start-vite
pdm run python -m scripts.playwright_pr_0257_auth_lifecycle --start-vite
```
## Known Issues / Risks
- Canonical Docker-first live testing after the auth switch belongs to `PR-0254` after `ADR-0083` / realm stories; do not resurrect local password-form smoke scripts for that lane.
- Product identity realm concern is now closed through `ADR-0083` / `REV-ST-28-06`: do not treat local browser-session retirement as removal of standalone Skriptoteket identity.
- `ST-28-09` still owns realm-aware projection provisioning; lifecycle completion does not create a Skriptoteket projection by itself.
- `PR-0254` owns Docker-first cross-app auth proof after the `ADR-0083` realm/login/projection path; do not resurrect removed local password-form smoke commands for that lane.
## Next Steps
- Start `ST-28-09`: migrate projection lookup/provisioning toward `(product_identity_realm, realm_subject_id)` after consuming the lifecycle output contract.
- Keep `PR-0254` as the final Docker/operator cross-app proof after `ST-28-09`.
