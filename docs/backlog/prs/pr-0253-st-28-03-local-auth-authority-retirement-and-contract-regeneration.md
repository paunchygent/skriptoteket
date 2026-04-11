---
type: pr
id: PR-0253
title: "ST-28-03 local auth authority retirement and contract regeneration"
status: ready
owners: "agents"
created: 2026-04-10
updated: 2026-04-11
stories:
  - "ST-28-03"
tags: ["auth", "backend", "frontend", "contracts"]
links:
  - "REV-PR-0253"
acceptance_criteria:
  - "Given `REV-PR-0253` is the retained review gate for this hard-break task, when implementation starts, then the review is approved, its required constraints are encoded in this task, and docs validation has passed."
  - "Given Skriptoteket has cut over to the HuleEdu-owned browser-session contract, when local browser-auth surfaces are audited, then routes, models, handlers, and frontend assumptions that only exist to own browser auth locally are removed."
  - "Given shared auth endpoints are now external provider contract surfaces, when client contracts and generated types are refreshed, then Skriptoteket no longer treats local `/api/v1/auth/me` as the browser bootstrap source."
  - "Given `PR-0255` made app continuation HuleEdu-context-derived, when this PR retires local auth authority, then remaining local-session-backed `require_user_api`, `require_contributor_api`, `require_admin_api`, `require_superuser_api`, `require_session_api`, and `require_csrf_token` consumers are rewired from the route inventory to canonical HuleEdu-derived app dependencies or explicitly retained behind a documented non-browser allowlist."
  - "Given the browser must never mint downstream identity context, when authenticated app APIs are called, then the task has an explicit browser API edge contract: either the same-origin `/api` deployment/local proxy is the formal gateway path that injects signed context, or the SPA uses a configured HuleEdu Gateway app API base URL. Frontend tests prove no `X-Huledu-Identity-*` headers are constructed in browser code."
  - "Given the current signed HuleEdu context does not contain trusted email/email-verification provisioning claims, when a HuleEdu-authenticated subject has no Skriptoteket projection, then no local user is fabricated from `sub`; protected APIs fail closed and the SPA reaches a deliberate not-provisioned or local-provisioning-required state."
  - "Given local CSRF tokens belonged to local browser sessions, when local sessions are retired, then mutating browser app routes are protected by signed HuleEdu gateway context through `require_app_*_api` dependencies; stale `X-CSRF-Token` values do not authorize anything."
  - "Given public auth ceremony routes currently point at local forms, when this task removes local browser-auth authority, then `/auth/login`, `/register`, `/forgot-password`, `/reset-password`, `/verify-email`, and verification-resend behavior are mapped to frozen HuleEdu-owned targets or deliberate retired-state UX with old-link behavior covered by tests."
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

## Retained Review Gate

`REV-PR-0253` is the retained review record for this task and is approved after docs-quality
closeout. Implementation must preserve the approved constraints below; if code discovery invalidates
the browser edge, provisioning, ceremony, CSRF, script, session, or proof gates, pause deletion and
route the change back through the retained review record.

`ADR-0076` remains `proposed`; this task may proceed only by explicitly citing the approved
`REV-EPIC-28` direction as the governing backlog approval for the implementation lane, or by
separately moving `ADR-0076` through the repo review workflow before code work.

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
7. **Replace the frontend auth ceremony explicitly.** Replace `auth.login()` with a HuleEdu handoff
   adapter, make logout call `sharedAuthUrl("/v1/auth/logout")`, and remove or redirect
   register/forgot/reset/verify/resend surfaces according to the ceremony target matrix.
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
  - no browser code sets `X-Huledu-Identity-*`
  - each public auth route reaches the frozen HuleEdu handoff or retired-state UX
- Run affected migration/schema assertion tests for the sessions-table removal.
- Run `pdm run fe-gen-api-types` or the repo-sanctioned generated-contract command.
- Run `pdm run fe-type-check`.
- Run `pdm run typecheck`.
- Run `pdm run lint`.
- Run `pdm run db-upgrade`.
- Run `pdm run docs-validate`.
- Run `git diff --check`.
- Run the new live `PR-0253` proof command and record it in `.agents/handoff.md`.

## Rollback Plan

This is an intentional hard break, not a compatibility bridge.

If the browser API edge, provisioning policy, or public ceremony targets cannot be made concrete,
stop before deleting local browser-auth surfaces and route the gap to the named HuleEdu provider or
deployment follow-up. After the sessions-table migration lands, rollback requires either the
documented downgrade that recreates the empty table shape or an explicit one-way data-loss note in
the migration and retained review response.
