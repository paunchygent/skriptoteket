---
type: pr
id: PR-0253
title: "ST-28-03 local auth authority retirement and contract regeneration"
status: done
owners: "agents"
created: 2026-04-10
updated: 2026-04-12
stories:
  - "ST-28-03"
tags: ["auth", "backend", "frontend", "contracts"]
links:
  - "REV-PR-0253"
  - "REF-hule-education-product-identity-realms-and-skriptoteket-standalone-identity"
acceptance_criteria:
  - "Given `REV-PR-0253` is the retained review gate for this hard-break task, when implementation starts, then the review is approved, its required constraints are encoded in this task, and docs validation has passed."
  - "Given Skriptoteket has cut over to the HuleEdu-owned browser-session contract, when local browser-auth surfaces are audited, then routes, models, handlers, and frontend assumptions that only exist to own browser auth locally are removed."
  - "Given shared auth endpoints are now external provider contract surfaces, when client contracts and generated types are refreshed, then Skriptoteket no longer treats local `/api/v1/auth/me` as the browser bootstrap source."
  - "Given `PR-0255` made app continuation HuleEdu-context-derived, when this PR retires local auth authority, then remaining local-session-backed `require_user_api`, `require_contributor_api`, `require_admin_api`, `require_superuser_api`, `require_session_api`, and `require_csrf_token` consumers are rewired from the route inventory to canonical HuleEdu-derived app dependencies or explicitly retained behind a documented non-browser allowlist."
  - "Given the browser must never mint downstream identity context, when authenticated app APIs are called, then the task has an explicit browser API edge contract: either the same-origin `/api` deployment/local proxy is the formal gateway path that injects signed context, or the SPA uses a configured HuleEdu Gateway app API base URL. Frontend tests prove no `X-Huledu-Identity-*` headers are constructed in browser code."
  - "Given the current signed HuleEdu context does not contain trusted email/email-verification provisioning claims, when a HuleEdu-authenticated subject has no Skriptoteket projection, then no local user is fabricated from `sub`; protected APIs fail closed and the SPA reaches a deliberate not-provisioned or local-provisioning-required state."
  - "Given local CSRF tokens belonged to local browser sessions, when local sessions are retired, then mutating browser app routes are protected by signed HuleEdu gateway context through `require_app_*_api` dependencies; stale `X-CSRF-Token` values do not authorize anything."
  - "Given public auth ceremony routes currently point at local forms, when this task removes local browser-auth authority, then `/auth/login`, `/register`, `/forgot-password`, `/reset-password`, `/verify-email`, and verification-resend behavior are mapped to frozen Hule Education-owned browser ceremony targets or deliberate retired-state UX with old-link behavior covered by tests."
  - "Given the repository exposes supported smoke/proof commands, when local auth endpoints are removed, then active script command surfaces are updated to HuleEdu/shared-session proof style or explicitly retired; supported commands do not call local `/api/v1/auth/login` or `/api/v1/auth/csrf`."
  - "Given the `sessions` table and session model become obsolete browser-auth state, when they are dropped or refactored, then the Alembic migration, schema assertions, observability metric removal, downgrade/data-loss posture, and `ToolSessionRepositoryProtocol` exclusion are documented and tested."
  - "Given the repository forbids hidden compatibility bridges, when this PR is reviewed, then remaining auth code is either internal authorization, explicit app-local domain behavior, or documented consumer code for the HuleEdu session contract."
---

## Problem

The cutover is not complete if old local browser-auth ownership remains in the codebase as a
fallback path.

After `PR-0255`, `GET /api/v1/profile/app-continuation` no longer depends on the
local-session-backed `require_user_api` path. Other protected app APIs still do. That includes
profile mutations, editor/admin APIs, my-tools/favorites APIs, curated-app authenticated APIs, and
the role-specific wrappers (`require_contributor_api`, `require_admin_api`,
`require_superuser_api`) that delegate to `require_user_api`.

## Goal

Retire Skriptoteket-local browser auth authority after `PR-0251` and `PR-0252` prove the consumer
path, then regenerate or realign client contracts around the shared session model without leaving a
dead onboarding path, a direct-browser transport gap, a soft CSRF bypass, or broken supported proof
scripts.

## Non-goals

- Removing internal service authorization checks that still protect app data.
- Removing account-domain concepts that Skriptoteket still legitimately owns.
- Implementing missing HuleEdu provider registration or password-lifecycle endpoints in this repo.
- Letting browser code construct downstream `X-Huledu-Identity-*` headers.
- Preserving local browser-auth endpoints for legacy scripts or old links.
- Collapsing Skriptoteket standalone product identity into a HuleEdu school-registration identity.

## Retained Review Gate

`REV-PR-0253` is the retained review record for this task. It was approved for implementation
planning after docs-quality closeout, moved to `changes_requested` during implementation review,
and returned to `approved` on 2026-04-12 after reviewer-owned remediation re-check.

Implementation preserved the approved constraints below, addressed the retained findings without
reintroducing a local auth compatibility bridge, and passed the 2026-04-12 retained
`REV-PR-0253` implementation re-review. If future code discovery invalidates the browser edge,
provisioning, ceremony, CSRF, script, session, or proof gates, route the change back through the
retained review record.

`ADR-0076` remains `proposed`; this task may proceed only by explicitly citing the approved
`REV-EPIC-28` direction as the governing backlog approval for the implementation lane, or by
separately moving `ADR-0076` through the repo review workflow before code work.

## Product Identity Realm Direction

`REF-hule-education-product-identity-realms-and-skriptoteket-standalone-identity` is now attached
to this task as a required architecture correction. `PR-0253` may retire Skriptoteket-local
browser-session authority, but it must not imply that Skriptoteket standalone identity disappears or
that all users must complete a HuleEdu school-registration process.

The temporary direction for this PR is:

- Hule Education owns the browser gateway/session/CSRF/login ceremony.
- Hule Education Identity should support product identity realms, including a Skriptoteket
  standalone realm.
- Skriptoteket continues to own local projection, profile, RBAC, AI preferences, and app
  authorization.
- `AuthProvider.LOCAL` and existing Skriptoteket-local identity data remain valid product-domain
  concepts; this PR removes browser-session authority, not standalone Skriptoteket identity.
- Skriptoteket-local browser API registration/password/verification routes are removed. Standalone
  Skriptoteket registration/password/verification semantics should move to a Hule
  Education-hosted Skriptoteket realm ceremony, not back to local browser-auth API routes.
- The exact realm vocabulary, signed context schema, account-linking behavior, and gateway ceremony
  URL are now routed to `ADR-0083` / `ST-28-06` through `ST-28-09` before `PR-0254` treats
  cross-app auth proof as final.

## Required Inventories And Matrices

Before code changes, add the following working artifacts to the task implementation notes,
retained review response, or a governed follow-up doc:

| Artifact | Required columns / fields | Blocks |
|----------|---------------------------|--------|
| Route inventory | route file, method/path, current guard, target guard, browser-facing, mutating, public/guest-adjacent, proof owner, allowlist rationale if retained | Guard codemods and CSRF removal |
| Browser API edge contract | selected edge (`api.hule.education` app API base URL or formal same-origin gateway/proxy `/api`), local-dev behavior, production behavior, identity-context injector owner, proof route(s), frontend env/config owner | Backend signed-context enforcement |
| Auth ceremony target matrix | old route/action, target HuleEdu URL/action or retired UX, owner, expected status/error behavior, old-link handling, test owner | Frontend route deletion/redirects |
| Provisioning policy | source of trusted provisioning claims or non-browser provisioning path, missing-projection backend behavior, missing-projection UX, follow-up owner if HuleEdu must add claims | Local register/password deletion |
| Supported script allowlist | active `pyproject.toml` command, helper module, auth dependency, keep/update/retire decision, proof command | Script helper cleanup |
| Session cleanup checklist | handler/model/repository/DI/migration/metric/test/doc item, owner, delete/refactor decision, downgrade/data-loss posture | Session table drop |

## Implementation Plan

1. **Keep the retained review response current.** Preserve the approved `REV-PR-0253` constraints
   while adding the route/edge/ceremony/provisioning/session decisions and docs-validation evidence
   during implementation.
2. **Freeze the browser API edge contract.** Choose exactly one authenticated app API transport:
   a configured HuleEdu Gateway app API base URL, or a formal same-origin `/api` gateway/proxy that
   injects signed downstream context. Browser code must never set `X-Huledu-Identity-*`.
3. **Build the route inventory before import changes.** Classify every `require_user_api`,
   `require_contributor_api`, `require_admin_api`, `require_superuser_api`, `require_session_api`,
   and `require_csrf_token` consumer before rewiring. Include `/api/v1/me`, editor, curated apps,
   vault, suggestions, admin, and `web/routes/interactive_tools.py`.
4. **Define the canonical app-auth dependency surface.** Add or finalize
   `require_app_user_projection_api()`, `require_app_user_api()`, role wrappers, and
   `require_app_ai_preferences()` so handlers can keep app-local user/profile semantics while
   depending on signed HuleEdu gateway context.
5. **Replace CSRF wording with trust-boundary enforcement.** Mutating app routes should require the
   canonical signed-context dependencies, not local-session CSRF comparison. Update
   `.agents/rules/040-fastapi-blueprint.md` so future work does not reintroduce
   `require_csrf_token` for browser app writes.
6. **Settle provisioning before deleting local registration/password paths.** Either record a
   HuleEdu provider follow-up for signed provisioning claims or keep a non-browser
   admin/import/local-user provisioning path. Missing projection must fail closed and never create a
   local user from `sub` alone.
7. **Replace the frontend auth ceremony explicitly.** Replace `auth.login()` with a Hule
   Education inloggning handoff adapter, make logout call `sharedAuthUrl("/v1/auth/logout")`, and
   remove or redirect register/forgot/reset/verify/resend surfaces according to the ceremony target
   matrix.
8. **Migrate route cohorts from the inventory.** Rewire browser-facing protected routes to the new
   app dependencies; retain only explicit internal/non-browser authorization paths with rationale.
   Add a static test that fails on old guard imports outside the allowlist.
9. **Delete/refactor session infrastructure only after references are gone.** Cover login/logout
   handlers, current-user provider, reset-password session revocation, AI session syncing,
   active-session metric, `SessionModel`, repository/DI binding, migration imports/schema
   assertions, and the sessions table. Keep `ToolSessionRepositoryProtocol` untouched.
10. **Regenerate and harden contracts.** Regenerate OpenAPI/frontend types and add broad no-zombie
    tests proving local browser-auth paths and schemas are absent:
    login/logout/me/csrf/register/register-validate/resend-verification/verify-email/
    forgot-password/reset-password, plus `Login*`, `MeResponse`, and `CsrfResponse`. Hand-type
    `SharedCsrfResponse` in `sharedAuth.ts` instead of depending on Skriptoteket OpenAPI.
11. **Update supported scripts.** Convert active proof/smoke helpers to HuleEdu/shared-session
    proof style, retire or archive historical PR scripts that still post to local login/CSRF, and
    add a static grep test for active command surfaces.
12. **Run a live PR-0253 proof.** The live proof must exercise a gateway/proxy-signed read and
    write path, direct missing-context rejection, missing-projection failure, and the frontend auth
    ceremony outcome for at least the canonical protected route.

## Test Plan

- Run affected backend route/dependency tests for signed context success and fail-closed cases.
- Run tests proving direct missing signed context returns `401` even if `X-CSRF-Token` is present;
  valid signed context succeeds with no `skriptoteket_session`; stale local CSRF grants nothing.
- Run tests proving missing HuleEdu projection creates no local user, protected APIs fail closed,
  and the frontend reaches the deliberate not-provisioned/local-provisioning-required state.
- Run static backend tests forbidding old local-auth guard imports outside the explicit allowlist.
- Run OpenAPI/no-zombie contract tests for removed local auth paths and schemas.
- Run active-script static grep tests for supported `pyproject.toml` command surfaces.
- Run affected frontend auth/client/router/component tests, including:
  - no browser code calls `/api/v1/auth/login`, `/logout`, `/register`, `/forgot-password`,
    `/reset-password`, `/verify-email`, or `/resend-verification`
  - login anchors do not target `/v1/auth/login` unless that path is explicitly proven
    browser-navigable by the Hule Education Gateway/Identity contract
  - no browser code sets `X-Huledu-Identity-*`
  - each public auth route reaches the frozen Hule Education inloggning handoff or retired-state UX
- Run affected migration/schema assertion tests for the sessions-table removal.
- Run `pdm run fe-gen-api-types` or the repo-sanctioned generated-contract command.
- Run `pdm run fe-type-check`.
- Run `pdm run typecheck`.
- Run `pdm run lint`.
- Run `pdm run db-upgrade`.
- Run `pdm run docs-validate`.
- Run `git diff --check`.
- Run the new live `PR-0253` proof command and record it in `.agents/handoff.md`.

## Implementation Notes (as of 2026-04-11)

`PR-0253` completed a hard retirement of Skriptoteket-local browser auth authority. The old
`/api/v1/auth/*` router is deleted rather than retained as an import-compatible retired module, and
the retained implementation review approved the remediation evidence on 2026-04-12.

### Implementation Review Status

`REV-PR-0253` remediation evidence addresses the retained implementation findings:

- zombie browser-session protocol/model/config/fixture surfaces were removed or rehomed behind
  non-browser owners
- missing-projection frontend UX now preserves the app-continuation reason and routes to a
  deliberate provisioning-required state
- the live proof now exercises a browser protected route through a test gateway injector that adds
  signed app context outside browser code
- current docs/rules/runbooks no longer advertise removed smoke commands
- product identity realm separation is now explicitly retained so local browser-session retirement
  does not erase standalone Skriptoteket identity
- the frontend login anchor now uses a dedicated browser ceremony helper instead of the shared auth
  API login endpoint; copy says `inloggning`/Skriptoteket access rather than HuleEdu-only login

The reviewer-owned checklist in `REV-PR-0253` is closed and the retained review is approved.

### Route Inventory Outcome

| Cohort | Route files / method-path scope | Previous guard | Target guard | Browser-facing | Mutating | Proof owner |
|--------|--------------------------------|----------------|--------------|----------------|----------|-------------|
| Current user/profile | `api/v1/me.py`, `api/v1/profile.py` (`GET`, `PATCH`) | `require_user_api`, local CSRF for writes | `require_app_user_api`, `require_app_user_projection_api` | yes | profile writes | unit + live PR-0253 proof |
| Catalog/tool usage | `api/v1/catalog.py`, `api/v1/tools.py`, `api/v1/favorites.py`, `api/v1/my_runs.py`, `api/v1/vault.py` | `require_user_api`, local CSRF for writes | `require_app_user_api` | yes | mixed | static old-guard ban |
| Contributor/editor | `api/v1/editor/**` (`boot`, `chat`, `completions`, `drafts`, `edit_ops`, `locks`, `runs`, `sandbox*`, `schema_validation`, `workflow`) | `require_contributor_api`, role wrappers, local CSRF for writes | `require_app_contributor_api`, `require_app_admin_api`, `require_app_superuser_api`, `require_app_ai_preferences` | yes | mixed | static old-guard ban + signed-context dependency tests |
| Admin/user management | `api/v1/admin_tools.py`, `api/v1/admin_users.py`, editor taxonomy/metadata/maintainers/workflow admin paths | `require_admin_api`, `require_superuser_api`, local CSRF for writes | `require_app_admin_api`, `require_app_superuser_api` | yes | mixed | static old-guard ban |
| Curated apps | `api/v1/apps*.py`, classroom planner modules, Reagent Prep Chef, Conversion Hub, Flunk Out Frenzy | `require_user_api`, local CSRF for writes | `require_app_user_api` | yes | mixed | static old-guard ban |
| HTML interactive tools | `web/routes/interactive_tools.py` | `require_user_api`, local CSRF for writes | `require_app_user_api` | yes | mixed | static old-guard ban |

There is no retained browser-route allowlist for the retired local guard family. The static
contract test fails on `require_user_api`, `require_contributor_api`, `require_admin_api`,
`require_superuser_api`, `require_session_api`, `require_csrf_token`, or the deleted
`skriptoteket.web.auth.api_dependencies` import under browser API/route modules.

### Browser API Edge Contract

Skriptoteket keeps relative `/api` browser calls. The deployment/local edge contract is that the
same-origin `/api` path is a trusted gateway/proxy path that injects signed HuleEdu downstream
identity context before requests reach Skriptoteket. Browser code must never construct
`X-Huledu-Identity-*` headers.

Local proof uses Vite's `/api` proxy pinned to `http://127.0.0.1:8000` and signed test headers
owned by the proof harness to simulate the trusted gateway injector. The browser-route proof
asserts that incoming browser requests did not set internal identity headers before the proof
injector forwards signed context, and the SPA source/static tests assert no browser code emits
internal identity headers.

Docker-first live testing after this switch belongs to `PR-0254` after `ADR-0083` and the
realm-aware login/projection stories are accepted: run the containerized Skriptoteket stack against
the HuleEdu shared edge/gateway proof instead of reintroducing local password-form smoke scripts.
`PR-0253` keeps only the targeted local real-backend/Vite proof for the signed downstream contract.

### Ceremony Target Matrix

| Public route/action | Target | Owner | Old-link behavior | Proof |
|---------------------|--------|-------|-------------------|-------|
| `/auth/login` | Browser-navigable Hule Education inloggning ceremony from `VITE_HULEEDU_AUTH_ENTRY_URL`, defaulting to `https://api.hule.education/auth/login?app=skriptoteket&next=...` | Hule Education Gateway / Identity | preserved `next` becomes absolute return URL; anchors must not target POST-only `/v1/auth/login` unless that path is explicitly proven browser-navigable | `AuthLoginPanel.spec.ts`, `sharedAuth.spec.ts`, live PR-0253 proof |
| logout action | HuleEdu `/v1/auth/logout` | HuleEdu Gateway | local state clears on `204`/`401` | `auth.spec.ts` |
| `/register` | retired/local-provisioning-required UX until Hule Education-hosted Skriptoteket realm registration is designed | Skriptoteket product + Hule Education Identity follow-up | no local submit; does not imply Skriptoteket standalone identity is removed | route/component tests + static no local auth calls |
| `/forgot-password` | retired/local-provisioning-required UX | Skriptoteket | no local reset request | route/component tests + static no local auth calls |
| `/reset-password` | retired/local-provisioning-required UX | Skriptoteket | no token reset submit | route/component tests + static no local auth calls |
| `/verify-email` / resend | retired/local-provisioning-required UX | Skriptoteket | no local verify/resend submit | route/component tests + static no local auth calls |

### Provisioning And RBAC

Missing HuleEdu projections fail closed. Skriptoteket does not fabricate local users from `sub`
because the signed context still lacks trusted provisioning email/email-verification claims.
Non-browser admin/import/local-user provisioning remains the explicit path for creating
Skriptoteket projections until Hule Education owns signed provisioning claims for the chosen
product identity realm. `AuthProvider.LOCAL` and local identity data stay in place for
Skriptoteket product identity; they are not browser-session authority.

RBAC remains Skriptoteket-local: signed HuleEdu context proves the browser identity/session, then
`HuleEduAppProjectionResolver` resolves the existing local `User` by `(auth_provider, external_id)`.
All app role wrappers authorize against `User.role` via local role guards. HuleEdu provider roles
and grants are context metadata; they do not overwrite Skriptoteket admin/contributor/superuser
authorization.

### Session, Contract, And Script Cleanup

- Deleted the local browser auth router/dependencies and removed it from `web/router.py`.
- Removed local login/logout/current-user/session repository/model/DI bindings.
- Removed session-row AI preference syncing and the active-session metric.
- Dropped the `sessions` table through Alembic migration `c1d2e3f4a5b6`; downgrade recreates an
  empty legacy shape for recovery and documents that browser session data is intentionally not
  preserved.
- Kept `ToolSessionRepositoryProtocol` and `tool_sessions` untouched.
- Regenerated OpenAPI/frontend types and added no-zombie contract tests for retired local
  browser-auth paths/schemas.
- Removed supported `ui-smoke`, `ui-editor-smoke`, and `ui-runtime-smoke` command surfaces that
  drove the deleted local password form; active PR proof commands use HuleEdu/shared-session helpers.

### Verification Evidence

- `pdm run pytest tests/unit/web/test_profile_app_continuation_api.py tests/unit/web/test_pr_0253_auth_retirement_contracts.py tests/unit/application/identity/test_update_ai_settings_handler.py tests/unit/application/identity/test_reset_password_handler.py -q`
- `pdm run fe-test -- --run src/components/auth/AuthLoginPanel.spec.ts src/api/sharedAuth.spec.ts src/stores/auth.spec.ts src/stores/authBootstrap.spec.ts src/router/index.spec.ts src/views/AuthLoginView.spec.ts src/App.spec.ts`
- `pdm run fe-type-check`
- `pdm run typecheck`
- `pdm run db-upgrade`
- `pdm run pytest -q tests/integration/test_migration_c1d2e3f4a5b6_idempotent.py -m docker --override-ini addopts=''`
- `pdm run python -m scripts.check_migration_test_coverage`
- `pdm run python -m py_compile scripts/_playwright_huleedu_auth.py scripts/playwright_pr_0253_auth_retirement.py scripts/playwright_pr_0252_auth_return_to_origin.py scripts/playwright_pr_0255_auth_bootstrap.py`
- `ARTIFACTS_ROOT=.artifacts/local-tool-artifacts pdm run pr-0253-auth-retirement --start-backend --start-vite`
  (signed read/write `200`, stale-CSRF missing-context `401`, missing projection `401`,
  `/auth/login` inloggning ceremony handoff, browser gateway-injected `/editor`, and
  provisioning-required UX)
- `pdm run docs-validate`
- `pdm run lint`
- `git diff --check`

Implementation review failures retained in `REV-PR-0253`:

- `pdm run pytest -q tests/unit/web/test_me_api_routes.py` now passes as part of the targeted
  retained-remediation test set.
- `pdm run pytest -q tests/unit/web/test_editor_chat_api.py` now passes as part of the targeted
  retained-remediation test set.
- `pdm run pytest -q tests/unit/web/apps/classroom_planner/test_guest_upgrade_api.py` now passes as
  part of the targeted retained-remediation test set.
- `pdm run pytest -q tests/unit/web/test_observability_routes.py` now passes as part of the
  targeted retained-remediation test set.

Additional retained-remediation evidence:

- `pdm run pytest tests/unit/web -q` (pass; 276 tests).
- `pdm run pytest -q tests/unit/web/test_pr_0253_auth_retirement_contracts.py tests/unit/web/test_profile_app_continuation_api.py tests/unit/web/test_me_api_routes.py tests/unit/web/test_editor_chat_api.py tests/unit/web/apps/classroom_planner/test_guest_upgrade_api.py tests/unit/web/test_observability_routes.py` (pass; 44 tests).
- `pdm run fe-test -- --run src/stores/auth.spec.ts src/router/index.spec.ts src/views/AuthProvisioningRequiredView.spec.ts src/components/auth/AuthLoginPanel.spec.ts src/api/sharedAuth.spec.ts src/api/client.spec.ts src/App.spec.ts` (pass; 71 tests).
- `pdm run fe-type-check` (pass).
- `pdm run typecheck` (pass).
- `pdm run db-upgrade` (pass; database already at the PR-0253 migration head).
- `pdm run docs-validate` (pass).
- `pdm run lint` (pass).
- `git diff --check` (pass).

Reviewer-owned closeout evidence:

- `pdm run pytest -q tests/unit/web/test_pr_0253_auth_retirement_contracts.py` (pass; 7 tests).
- `pdm run docs-validate` (pass).
- `pdm run fe-type-check` (pass).
- `pdm run typecheck` (pass).
- `pdm run pytest -q tests/unit/web/test_profile_app_continuation_api.py tests/unit/web/test_me_api_routes.py tests/unit/web/test_editor_chat_api.py tests/unit/web/apps/classroom_planner/test_guest_upgrade_api.py tests/unit/web/test_observability_routes.py` (pass; 38 tests).
- `pdm run fe-test -- --run src/stores/auth.spec.ts src/router/index.spec.ts src/views/AuthProvisioningRequiredView.spec.ts src/components/auth/AuthLoginPanel.spec.ts src/api/sharedAuth.spec.ts src/api/client.spec.ts src/App.spec.ts` (pass; 74 tests).
- `ARTIFACTS_ROOT=.artifacts/local-tool-artifacts pdm run pr-0253-auth-retirement --start-backend --start-vite` (pass; signed read/write `200`, stale-CSRF missing-context `401`, missing projection `401`, `/auth/login` ceremony handoff, browser gateway-injected `/editor`, and provisioning-required UX).
- `pdm run lint` (pass).
- `git diff --check` (pass).

## Rollback Plan

This is an intentional hard break, not a compatibility bridge.

If the browser API edge, provisioning policy, or public ceremony targets cannot be made concrete,
stop before deleting local browser-auth surfaces and route the gap to the named HuleEdu provider or
deployment follow-up. After the sessions-table migration lands, rollback requires either the
documented downgrade that recreates the empty table shape or an explicit one-way data-loss note in
the migration and retained review response.
