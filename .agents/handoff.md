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
- Date: 2026-04-11
- Branch: `main` + local changes
- Current lane: `PR-0252` auth entry return-to-origin is implemented and independent-review approved.
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
- `PR-0253` now explicitly owns retiring or rewiring the remaining local-session-backed `require_user_api` / role-wrapper consumers after `PR-0251` and `PR-0252`; `PR-0255` only moved `/api/v1/profile/app-continuation`.
- Reviewer advice acted on: `frontend/apps/skriptoteket/src/stores/ai.ts` now fails closed while `auth.aiPolicy` is missing, and `frontend/apps/skriptoteket/src/stores/ai.spec.ts` freezes that missing app-local AI bootstrap does not allow remote providers.
- `PR-0251` continuation slice is implemented: `GET /api/v1/profile/app-continuation` returns runtime `ai_policy` plus profile AI preferences, `useAuthStore.bootstrap()` performs HuleEdu session first and app-local continuation second, and editor AI chat/completions/edit-ops no longer read AI preferences from local `Session` fields.
- `PR-0252` is implemented: direct protected entry, app-local `401` recovery, and top-level `/auth/login?next=...` return preserve the dedicated auth-entry contract on the HuleEdu-owned session model. Live proof uses the real backend app-continuation route, signed HuleEdu request context, DB projection, and Vite `/api` proxy. Shared proof helpers now live in `scripts/_playwright_huleedu_auth.py`.
- Independent `skriptoteket_reviewer` pass for `PR-0252` approved the implementation with no actionable findings. Residual note: the live proof covers canonical `/editor`; richer query/hash destinations are covered by focused Vitest.
- `REV-PR-0253` is approved after docs-quality closeout. `PR-0253` requires the retained review/doc gate, route inventory, browser API edge contract, public auth ceremony matrix, provisioning policy, CSRF signed-context proof, session migration/data policy, no-zombie contracts, supported script cleanup, and a live gateway/proxy-signed proof before implementation deletion work.
- Skriptoteket should not create a second integration epic. Implementation now lives as PR-sized tasks under existing `EPIC-28`:
  - `PR-0250` ingests HuleEdu provider conformance and records cutover readiness.
  - `PR-0251` cuts the SPA auth store/API client over to `GET https://api.hule.education/v1/auth/session` plus CSRF.
  - `PR-0255` remediates `REV-PR-0251` implementation findings before `PR-0251` close-out; retained `REV-PR-0251` re-review is approved.
  - `PR-0252` preserves `/auth/login?next=...` interruption and return-to-origin behavior on the shared session.
  - `PR-0253` removes obsolete Skriptoteket-local browser auth ownership and regenerates/realigns contracts.
  - `PR-0254` adds the cross-app Playwright smoke and operator runbook proof.
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
## How to Run
```bash
pdm run docs-validate
pdm run typecheck
pdm run lint
pdm run fe-type-check
pdm run fe-test -- --run src/stores/ai.spec.ts src/stores/auth.spec.ts src/api/sharedAuth.spec.ts src/api/client.spec.ts
pdm run pytest -q tests/unit/web/test_profile_app_continuation_api.py tests/unit/web/test_editor_inline_completion_api.py
pdm run pr-0252-auth-return --start-backend --start-vite
pdm run pr-0255-auth-bootstrap --start-backend --start-vite
pdm run fe-test -- --run src/router/index.spec.ts src/components/auth/AuthLoginPanel.spec.ts src/views/AuthLoginView.spec.ts src/views/ForgotPasswordView.spec.ts src/views/ResetPasswordView.spec.ts src/views/RegisterView.spec.ts src/views/VerifyEmailView.spec.ts src/composables/auth/authEntryNavigation.spec.ts src/App.spec.ts
```
## Known Issues / Risks
- `PR-0251` must preserve Skriptoteket-local role, profile, AI policy, and app authorization semantics without reinstating local browser auth authority, bearer storage, or direct HuleEdu Identity calls.
- `REV-PR-0251` retained re-review is approved; `PR-0253` / `PR-0254` remain for local-auth retirement and cross-app proof.
- Login/logout ceremony cleanup beyond return-to-origin proof stays with `PR-0253`; approved `REV-PR-0253` requires exact HuleEdu handoff or retired-state targets before local routes are deleted.
- `PR-0253` must settle browser API transport, missing-projection provisioning, CSRF signed-context enforcement, active script migration, and sessions-table data policy before deleting local browser-auth authority.
- `HomeView.vue` / `HomeView.spec.ts` had pre-existing local changes before this docs lane; keep them separate from EPIC-28 scaffolding.
- Public guest mode remains browser-owned and route-sensitive; clear local public guest storage before treating a stale guest state as an auth-cutover regression.
## Next Steps
- Continue with `PR-0253` -> `PR-0254` in order.
