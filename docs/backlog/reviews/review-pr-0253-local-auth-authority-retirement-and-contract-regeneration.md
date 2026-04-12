---
type: review
id: REV-PR-0253
title: "Review: PR-0253 local auth authority retirement and contract regeneration"
status: approved
owners: "agents"
created: 2026-04-11
updated: 2026-04-12
reviewer: "lead-developer"
prs:
  - PR-0253
adrs:
  - ADR-0076
  - ADR-0082
links:
  - EPIC-28
  - ST-28-03
  - PR-0250
  - PR-0251
  - PR-0252
  - PR-0254
  - PR-0255
  - REF-hule-education-product-identity-realms-and-skriptoteket-standalone-identity
---

## TL;DR

`PR-0253` is approved after the 2026-04-12 retained implementation re-review. The hard-break task
removes Skriptoteket-local browser-auth authority, keeps app-local RBAC and projection semantics,
and proves the browser edge with a test gateway injector that adds signed HuleEdu context outside
browser code. The product identity realm correction remains attached: the task does not collapse
Skriptoteket standalone product identity into a HuleEdu-school-only identity future.

## Problem Statement

The current task can remove the old local browser-auth paths too early and leave three classes of
regression: HuleEdu-authenticated users without local projections can get stranded, direct browser
calls to Skriptoteket APIs can fail once signed gateway context is required, and stale local CSRF or
supported smoke scripts can imply a security or operator contract that no longer exists.

## Proposed Solution

Revise `PR-0253` into a gated implementation task. The implementation must first freeze the route
inventory, browser API edge, public auth ceremony targets, and provisioning/session data policy.
Only then should it codemod guards, delete local browser-auth surfaces, regenerate contracts, and
run the focused plus live proofs.

## Artifacts to Review

| File | Focus | Time |
|------|-------|------|
| `docs/backlog/prs/pr-0253-st-28-03-local-auth-authority-retirement-and-contract-regeneration.md` | Scope, gates, proof obligations | 20 min |
| `docs/adr/adr-0076-huleedu-owned-browser-session-authority-for-skriptoteket.md` | HuleEdu Gateway and signed downstream identity boundary | 8 min |
| `docs/adr/adr-0082-app-local-bootstrap-continuation-on-huleedu-session.md` | App-local continuation boundary | 5 min |
| `docs/backlog/prs/pr-0255-st-28-01-pr-0251-remediation-huleedu-context-and-local-authorization-projection.md` | Projection and signed-context constraints | 8 min |
| `docs/reference/ref-hule-education-product-identity-realms-and-skriptoteket-standalone-identity.md` | Product identity realm correction and follow-up ADR/story direction | 10 min |
| `frontend/apps/skriptoteket/src/api/client.ts` | Current browser API transport | 5 min |
| `frontend/apps/skriptoteket/src/stores/auth.ts` and `frontend/apps/skriptoteket/src/router/routes.ts` | Local ceremony calls/routes | 8 min |
| `src/skriptoteket/web/auth/api_dependencies.py` and `src/skriptoteket/application/identity/huleedu_app_projection.py` | Current guard surface and missing projection behavior | 8 min |
| `migrations/versions/0001_init.py` and `migrations/versions/0030_sessions_cache_ai_settings.py` | Session table lifecycle | 5 min |
| `pyproject.toml` and `scripts/_playwright_auth.py` | Supported script surfaces using local auth | 5 min |

**Total estimated time:** ~72 minutes

## Key Decisions

| Decision | Rationale | Approve? |
|----------|-----------|----------|
| Treat `PR-0253` as the hard break for local browser-auth authority | Keeps no-legacy-support posture and prevents hidden compatibility bridges | [x] |
| Require retained review approval before implementation | The slice removes auth, session, frontend, scripts, and DB surfaces with high blast radius | [x] |
| Freeze a browser API edge contract before route rewiring | Signed gateway context must be injected by a trusted edge, never by browser code | [x] |
| Keep provisioning separate from browser auth | Current HuleEdu signed context does not carry trusted email/email-verification claims | [x] |
| Replace local CSRF with signed-context route dependencies | CSRF tokens tied to local sessions cannot remain an authority after session retirement | [x] |
| Drop/refactor session infrastructure with explicit migration/data policy | The sessions table has schema and observability implications beyond route deletion | [x] |

## Review Checklist

- [x] Scope is bounded to `ST-28-03` / local auth authority retirement
- [x] Retained review gate is present before implementation
- [x] Route inventory and guard migration are concrete
- [x] Browser API edge and signed-context injector ownership are concrete
- [x] Provisioning and missing-projection behavior are deliberate
- [x] Public auth ceremony targets are frozen or deliberately retired
- [x] CSRF removal is replaced by a signed-context trust-boundary proof
- [x] Session migration includes schema, downgrade/data-loss, and metric proof
- [x] No-zombie contract and active-script tests cover old auth surfaces

## Review Feedback

### Implementation Review (2026-04-11)

**Reviewer:** `Codex ruthless-code-review`
**Verdict:** `changes_requested`

The hard-retirement direction is correct, but the implementation is not review-clean. The findings
below are retained so remediation work can update this same review record and close each item with
evidence.

#### Remediation Checklist

This checklist is owned by the main reviewer. Implementers may add evidence notes under
`## Changes Made`, but only the main reviewer should tick the boxes or move this review back to
`approved`.

- [x] Finding 1 closed: missing-projection frontend UX reaches a deliberate
  provisioning-required/local-access-required state instead of `/auth/login`.
  Evidence required: focused frontend tests plus PR-0253 browser proof exercising the missing
  projection state.
- [x] Finding 2 closed: retired browser-session protocols/models/config/fixtures are deleted or
  explicitly rehomed behind non-browser owners.
  Evidence required: widened no-zombie contract test and passing affected backend route tests.
- [x] Finding 3 closed: PR-0253 live proof exercises the documented browser `/api` edge rather
  than relying only on direct Playwright API signed headers.
  Evidence required: `pdm run pr-0253-auth-retirement --start-backend --start-vite` proves a
  protected SPA route, missing context rejection, stale-CSRF rejection, and missing-projection UX.
- [x] Finding 4 closed: current docs/rules/runbooks no longer advertise removed smoke commands.
  Evidence required: `pdm run docs-validate` and a widened static guard for retired command names.
- [x] Previously failing targeted backend tests pass:
  `tests/unit/web/test_me_api_routes.py`, `tests/unit/web/test_editor_chat_api.py`,
  `tests/unit/web/apps/classroom_planner/test_guest_upgrade_api.py`, and
  `tests/unit/web/test_observability_routes.py`.
- [x] Review closeout recorded: `## Changes Made` lists each remediation, verification evidence is
  current, `REV-PR-0253` returns to `approved`, and governed `PR-0253` / `ST-28-03` return to
  `done`.
- [x] Finding 5 closed: product identity realm separation is preserved in the PR-0253 closeout
  direction and routed to explicit ADR/story follow-up.
  Evidence required: the product identity realm reference is linked from `REV-PR-0253`, `PR-0253`,
  and `EPIC-28`; PR-0253 wording does not imply standalone Skriptoteket identity is removed; and
  the `ADR-0083` / `ST-28-06` through `ST-28-09` follow-up path is called out before PR-0254 treats
  cross-app proof as complete.

#### Required Changes

1. **high - missing-projection users loop back to login**

   File references:
   `frontend/apps/skriptoteket/src/router/index.ts:51`,
   `frontend/apps/skriptoteket/src/stores/auth.ts:192`,
   `frontend/apps/skriptoteket/src/stores/authBootstrap.ts:105`

   `PR-0253` requires an authenticated HuleEdu subject without a local Skriptoteket projection to
   reach a deliberate provisioning-required state. The current frontend collapses app-continuation
   `401` into `user = null`, then protected-route guards redirect the user to `/auth/login`. That
   hides the backend fail-closed `missing_huleedu_app_projection` result and can create an
   unhelpful login loop.

   Concrete remediation: preserve the app-continuation error status/details in `authBootstrap`,
   map `details.reason == "missing_huleedu_app_projection"` to a distinct auth-store state such as
   `provisioningRequired`, add a deliberate provisioning-required/needs-local-access route or view,
   and route authenticated-HuleEdu-but-unprojected users there instead of `/auth/login`.

   Proof requirement: add Vitest coverage for a direct protected route with an authenticated shared
   HuleEdu session and app-continuation `401`/`missing_huleedu_app_projection`, asserting the
   provisioning-required state. Extend the PR-0253 browser proof to exercise that UX through the
   SPA.

2. **high - retired browser-session protocol still defines the old contract**

   File references:
   `src/skriptoteket/protocols/identity.py:83`,
   `src/skriptoteket/domain/identity/models.py:121`,
   `src/skriptoteket/config.py:95`,
   `tests/fixtures/identity_fixtures.py:64`

   The sessions table/model/repository path was removed, but public identity protocols, domain
   models, config, and fixtures still expose browser-session concepts such as
   `SessionRepositoryProtocol`, current-user/login/logout/session abstractions,
   `skriptoteket_session`, and session fixtures. That keeps a compatibility-shaped contract alive
   and lets tests keep exercising the retired authority instead of the signed HuleEdu app guard.

   Concrete remediation: delete the browser-session model/protocol/config/fixtures outright, or
   move any genuinely retained local-account/provisioning concepts behind explicitly named
   non-browser owners. Migrate route tests to a shared signed-HuleEdu fixture that seeds a local
   projection and provides signed context headers through the same dependency seam used by
   `require_app_*`.

   Proof requirement: strengthen `test_pr_0253_auth_retirement_contracts.py` to scan all
   `src/skriptoteket`, relevant test fixtures, and current docs/rules for retired names such as
   `SessionRepositoryProtocol`, `CurrentUserProviderProtocol`, `LoginHandlerProtocol`,
   `LogoutHandlerProtocol`, `SESSION_COOKIE_NAME`, and `skriptoteket_session`, while explicitly
   preserving `ToolSessionRepositoryProtocol`.

3. **medium - live proof bypasses the documented browser API edge**

   File references:
   `scripts/playwright_pr_0253_auth_retirement.py:42`,
   `scripts/playwright_pr_0253_auth_retirement.py:101`,
   `frontend/apps/skriptoteket/vite.config.ts:38`

   The PR documents same-origin `/api` as the trusted gateway/proxy path, but the PR-0253 proof
   sends signed HuleEdu headers through Playwright's API client and the frontend check only verifies
   the `/auth/login` handoff link. The Vite `/api` proxy does not inject identity headers, so the
   current live proof does not prove that a browser-protected route can bootstrap under the chosen
   browser-edge contract.

   Concrete remediation: either add a test-only local edge injector for the PR-0253 proof, or use a
   Playwright route/proxy continuation like the PR-0252/PR-0255 browser proofs to navigate a
   protected route with signed app-continuation context. The proof must cover success for a seeded
   projection, missing signed context rejection, stale CSRF without signed context, and
   missing-projection UX.

   Proof requirement: run
   `ARTIFACTS_ROOT=.artifacts/local-tool-artifacts pdm run pr-0253-auth-retirement --start-backend --start-vite`
   after the browser-route proof asserts the protected-route and missing-projection states.

4. **medium - current runbooks point at removed smoke commands**

   File references:
   `.agents/rules/075-browser-automation.md:55`,
   `.agents/rules/070-testing-standards.md:63`,
   `docs/runbooks/runbook-testing.md:28`

   `PR-0253` removed `ui-smoke`, `ui-editor-smoke`, and `ui-runtime-smoke` from the active PDM
   command surface, but current agent rules and runbooks still tell future sessions to run them.
   That makes the docs spine actively misleading after the hard retirement.

   Concrete remediation: replace those references with the HuleEdu/shared-session proof commands
   that remain supported, or mark old local password-form smoke commands as historical only. Add a
   docs/rules static guard that fails on active references to retired command names.

   Proof requirement: run `pdm run docs-validate` and the widened retirement contract test after
   updating the current docs/rules/runbooks.

5. **high - standalone Skriptoteket product identity must not be erased**

   File references:
   `docs/adr/adr-0076-huleedu-owned-browser-session-authority-for-skriptoteket.md:45`,
   `docs/backlog/prs/pr-0253-st-28-03-local-auth-authority-retirement-and-contract-regeneration.md:69`,
   `frontend/apps/skriptoteket/src/api/sharedAuth.ts:74`

   The current hard-retirement language can be misread as "HuleEdu owns auth, therefore all
   Skriptoteket users must become HuleEdu school identities." That is not the intended product
   architecture. Hule Education should own the shared browser gateway/session ceremony, but
   Skriptoteket still needs a standalone product identity realm so users can register and log in to
   Skriptoteket without completing a HuleEdu school-registration process.

   Concrete remediation: preserve the distinction between Hule Education browser/session authority
   and product identity realms. Link
   `REF-hule-education-product-identity-realms-and-skriptoteket-standalone-identity` from this
   review, `PR-0253`, and `EPIC-28`; record that this is not solved inside PR-0253; and require a
   follow-up ADR plus one or more stories/PRs for the Hule Education Identity/Gateway login
   ceremony, standalone Skriptoteket realm, account linking, and signed context schema. The current
   planning scaffold names that path as `ADR-0083` and `ST-28-06` through `ST-28-09`, with
   `ST-28-04` / `PR-0254` moved behind them as final proof.

   Proof requirement: docs validation must pass after adding the reference and links. The retained
   reviewer should verify that `PR-0253` remains a browser-session-authority retirement, not a
   product-identity merger.

#### Verification Evidence From Review

The following targeted commands failed during the implementation review and should pass after the
remediation work:

- `pdm run pytest -q tests/unit/web/test_me_api_routes.py` failed with two route-level `500`
  responses caused by missing `HuleEduInternalIdentityVerifierProtocol` test DI.
- `pdm run pytest -q tests/unit/web/test_editor_chat_api.py` failed with two route-level `500`
  responses caused by the same missing signed-context verifier dependency.
- `pdm run pytest -q tests/unit/web/apps/classroom_planner/test_guest_upgrade_api.py` failed with
  six route-level `500` responses caused by the same retired session-test setup.
- `pdm run pytest -q tests/unit/web/test_observability_routes.py` failed because the test still
  expects the removed local active-session metric.

Review persistence check:

- `pdm run docs-validate` (pass on 2026-04-11 after recording this implementation review as
  `changes_requested` in `REV-PR-0253`).

#### Decision

`approved` after retained implementation re-review on 2026-04-12.

### Implementation Remediation Evidence (2026-04-11)

**Owner:** `implementer`
**Reviewer verdict:** approved on 2026-04-12

The four retained implementation findings have corresponding remediation evidence. The frontend now preserves the
`missing_huleedu_app_projection` app-continuation failure as a provisioning-required auth state and
routes authenticated HuleEdu users without a local projection to deliberate local-access UX.
Browser-session protocols, model/config symbols, and fixtures are removed rather than kept as
compatibility surfaces, with the no-zombie contract widened to source, fixtures, route tests, and
current docs/rules. The PR-0253 live proof now includes browser-route coverage for a seeded
projection and a missing projection through a test gateway injector that asserts the browser did
not mint internal `X-Huledu-Identity-*` headers. Current runbooks/rules now point at HuleEdu
shared-session proof commands instead of removed local password-form smokes.

Follow-up boundary cleanup preserves the new product identity direction: login anchors use a
separate browser ceremony helper (`VITE_HULEEDU_AUTH_ENTRY_URL`) instead of the POST-oriented auth
API path, user-facing copy says `inloggning`/Skriptoteket access rather than HuleEdu-only login,
and `AuthProvider.LOCAL` / local identity data are documented as retained product-domain concepts,
not local browser-session authority.

Verification evidence:

- `pdm run pytest tests/unit/web -q` (pass; 276 tests).
- `pdm run pytest -q tests/unit/web/test_pr_0253_auth_retirement_contracts.py tests/unit/web/test_profile_app_continuation_api.py tests/unit/web/test_me_api_routes.py tests/unit/web/test_editor_chat_api.py tests/unit/web/apps/classroom_planner/test_guest_upgrade_api.py tests/unit/web/test_observability_routes.py` (pass; 44 tests).
- `pdm run fe-test -- --run src/stores/auth.spec.ts src/router/index.spec.ts src/views/AuthProvisioningRequiredView.spec.ts src/components/auth/AuthLoginPanel.spec.ts src/api/sharedAuth.spec.ts src/api/client.spec.ts src/App.spec.ts` (pass; 71 tests).
- `pdm run python -m py_compile scripts/_playwright_huleedu_auth.py scripts/playwright_pr_0253_auth_retirement.py scripts/playwright_pr_0252_auth_return_to_origin.py scripts/playwright_pr_0255_auth_bootstrap.py` (pass).
- `ARTIFACTS_ROOT=.artifacts/local-tool-artifacts pdm run pr-0253-auth-retirement --start-backend --start-vite` (pass; signed read/write `200`, stale-CSRF missing-context `401`, missing projection `401`, inloggning ceremony handoff, browser gateway-injected `/editor`, and provisioning-required UX).
- `pdm run fe-type-check` (pass).
- `pdm run typecheck` (pass).
- `pdm run db-upgrade` (pass; database already at the PR-0253 migration head).
- `pdm run docs-validate` (pass).
- `pdm run lint` (pass).
- `git diff --check` (pass).

### Retained Implementation Re-review (2026-04-12)

**Reviewer:** `Codex ruthless-code-review`
**Verdict:** `approved`

The reviewer rechecked the remediation evidence and found no blocking or actionable findings.
The missing-projection UX reaches the provisioning-required state, the retired local browser-session
contracts are absent from active source and contract surfaces, the browser proof exercises the
signed gateway-injected `/api` edge and fail-closed cases, current docs/rules no longer advertise
removed smoke commands, and the product identity realm separation is preserved through the linked
reference plus `ADR-0083` / `ST-28-06` through `ST-28-10` follow-up path.

Verification evidence from this re-review:

- `pdm run pytest -q tests/unit/web/test_pr_0253_auth_retirement_contracts.py` (pass; 7 tests).
- `pdm run docs-validate` (pass).
- `pdm run fe-type-check` (pass).
- `pdm run typecheck` (pass).
- `pdm run pytest -q tests/unit/web/test_profile_app_continuation_api.py tests/unit/web/test_me_api_routes.py tests/unit/web/test_editor_chat_api.py tests/unit/web/apps/classroom_planner/test_guest_upgrade_api.py tests/unit/web/test_observability_routes.py` (pass; 38 tests).
- `pdm run fe-test -- --run src/stores/auth.spec.ts src/router/index.spec.ts src/views/AuthProvisioningRequiredView.spec.ts src/components/auth/AuthLoginPanel.spec.ts src/api/sharedAuth.spec.ts src/api/client.spec.ts src/App.spec.ts` (pass; 74 tests).
- `ARTIFACTS_ROOT=.artifacts/local-tool-artifacts pdm run pr-0253-auth-retirement --start-backend --start-vite` (pass; signed read/write `200`, stale-CSRF missing-context `401`, missing projection `401`, `/auth/login` ceremony handoff, browser gateway-injected `/editor`, and provisioning-required UX).
- `pdm run lint` (pass).
- `git diff --check` (pass).

### Product Identity Realm Direction (2026-04-11)

**Owner:** `user-lead architecture direction`
**Reviewer verdict:** approved on 2026-04-12

The retained review now links
`REF-hule-education-product-identity-realms-and-skriptoteket-standalone-identity`. This reference
clarifies that unity through the Hule Education Gateway/Identity browser edge does not mean
Skriptoteket standalone identity disappears. The current PR may retire local browser-session
authority, but it must preserve room for a Hule Education-hosted Skriptoteket identity realm,
including standalone login/registration/reset semantics, explicit account linking, and local
Skriptoteket RBAC.

This is not fully solved inside `PR-0253`. It is a required architecture direction for follow-up ADR
and story work coordinated with the Hule Education API Gateway and Identity service.

**Reviewer:** `lead-developer`
**Date:** `2026-04-11`
**Verdict:** `approved`

### Required Changes

Resolved. The list below preserves the initial review findings that shaped the approved task
revision.

1. **blocker - retained review/doc gate must be kept before implementation**

   File references:
   `docs/adr/adr-0076-huleedu-owned-browser-session-authority-for-skriptoteket.md:5`,
   `docs/backlog/prs/pr-0253-st-28-03-local-auth-authority-retirement-and-contract-regeneration.md:16`

   `ADR-0076` is still proposed while the task treats the decision as settled, and `PR-0253`
   explicitly requires review. Keep this `REV-PR-0253` record, record the feedback here, reconcile
   `ADR-0076` status or cite approved `REV-EPIC-28` as the governing backlog approval, update
   `.agents/handoff.md`, and run `pdm run docs-validate`.

2. **blocker - deleting local registration/password paths can strand HuleEdu users**

   File references:
   `docs/backlog/prs/pr-0255-st-28-01-pr-0251-remediation-huleedu-context-and-local-authorization-projection.md:44`,
   `src/skriptoteket/application/identity/huleedu_app_projection.py:63`

   The signed HuleEdu context currently lacks trusted email/email-verification claims, and the
   resolver fails closed when no projection exists. Before deleting local register/verify/reset,
   the task must choose either a provider follow-up for signed provisioning claims or a non-browser
   admin/import/local-user provisioning path. Tests must prove missing projection creates no local
   user, protected APIs fail closed, and the frontend reaches a deliberate not-provisioned or
   local-provisioning-required state.

3. **high - browser API transport is still implicit**

   File references:
   `docs/adr/adr-0076-huleedu-owned-browser-session-authority-for-skriptoteket.md:78`,
   `docs/adr/adr-0076-huleedu-owned-browser-session-authority-for-skriptoteket.md:98`,
   `frontend/apps/skriptoteket/src/api/client.ts:144`

   `ADR-0076` says HuleEdu Gateway is the browser auth/API origin and downstream services receive
   signed internal identity context, while the current SPA still calls relative Skriptoteket paths.
   Once backend routes require signed gateway context, direct `/api/v1/...` browser calls will fail
   unless a real gateway/proxy inserts the headers. Add a browser API edge contract cohort: choose
   a configured HuleEdu Gateway app API base URL or declare same-origin `/api` as the formal
   gateway/proxy path that injects signed context. Browser code must never construct
   `X-Huledu-Identity-*` headers. Proof must cover no browser-set internal identity headers,
   backend missing-context rejection, and a live gateway/proxy-signed read and write.

4. **high - CSRF removal needs signed-context proof, not just dependency deletion**

   File references:
   `src/skriptoteket/web/auth/api_dependencies.py:36`,
   `docs/adr/adr-0076-huleedu-owned-browser-session-authority-for-skriptoteket.md:49`,
   `docs/adr/adr-0076-huleedu-owned-browser-session-authority-for-skriptoteket.md:98`

   Local CSRF was coupled to local sessions. The task should require every protected browser write
   to depend on `require_app_*_api`, which verifies signed gateway context. Tests must prove missing
   signed context returns `401` even if `X-CSRF-Token` is present, valid signed context succeeds
   without `skriptoteket_session`, and stale local CSRF no longer grants anything. Also update
   `.agents/rules/040-fastapi-blueprint.md` so future agents do not reintroduce the old dependency.

5. **high - frontend auth ceremony replacement is under-scoped**

   File references:
   `frontend/apps/skriptoteket/src/stores/auth.ts:231`,
   `frontend/apps/skriptoteket/src/stores/auth.ts:278`,
   `frontend/apps/skriptoteket/src/stores/auth.ts:336`,
   `frontend/apps/skriptoteket/src/router/routes.ts:25`

   The live SPA still posts local login/register/logout and exposes local forgot/register/reset/
   verify pages. Replace `auth.login()` with a Hule Education inloggning handoff adapter, make
   `auth.logout()` call `sharedAuthUrl("/v1/auth/logout")`, and remove or redirect
   register/forgot/reset/verify/resend
   according to a frozen ceremony target matrix. Add frontend tests proving no browser code calls
   the old local `/api/v1/auth/*` endpoints and every public auth route reaches the intended
   handoff or retired-state UX.

6. **high - route migration needs a classification table before codemods**

   File reference:
   `src/skriptoteket/web/auth/api_dependencies.py:9`

   The old guards are consumed across dozens of route files. Add a route inventory table before
   code changes with file, method/path, current guard, target guard, browser-facing, mutating, and
   proof owner. Codemod only after classification, and add a static test that fails on imports of
   `require_user_api`, `require_contributor_api`, `require_admin_api`, `require_superuser_api`,
   `require_session_api`, or `require_csrf_token` outside an explicit allowlist.

7. **medium - new dependency API must be exact**

   File references:
   `src/skriptoteket/application/identity/huleedu_app_projection.py:26`,
   `src/skriptoteket/web/auth/ai_preferences.py:48`

   Define the canonical surface explicitly: `require_app_user_projection_api()`,
   `require_app_user_api()`, role wrappers, and `require_app_ai_preferences()` reading from
   projection/profile. This keeps handlers stable while preventing AI routes from quietly retaining
   local session auth.

8. **medium - public auth ceremony needs concrete target contracts**

   File references:
   `frontend/apps/skriptoteket/src/router/routes.ts:25`,
   `docs/backlog/prs/pr-0250-st-28-05-huleedu-provider-conformance-ingest-and-cutover-readiness.md`

   `PR-0250` freezes session/login/logout/refresh/csrf/websocket surfaces, but not clearly
   registration or password lifecycle. Add a ceremony target matrix for `/auth/login`, `/register`,
   `/forgot-password`, `/reset-password`, `/verify-email`, and verification resend. If a target is
   missing, choose a deliberate retired/local-provisioning-required page rather than a dangling
   redirect.

9. **medium - session cleanup is larger than deleting the repository**

   File references:
   `src/skriptoteket/application/auth/update_ai_settings.py:108`,
   `src/skriptoteket/application/auth/reset_password.py:96`,
   `src/skriptoteket/web/observability.py:78`

   Session behavior still appears in non-route flows: AI settings syncs session rows, password
   reset revokes sessions, and observability counts active sessions. Add a cleanup checklist for
   login/logout handlers, current-user provider, reset-password session revocation, AI session
   syncing, active-session metric, `SessionModel`, repository/DI binding, migration imports/schema
   assertions, and the sessions table. Keep `ToolSessionRepositoryProtocol` untouched.

10. **medium - dropping `sessions` needs migration/data-policy proof**

    File references:
    `migrations/versions/0001_init.py:46`,
    `migrations/versions/0030_sessions_cache_ai_settings.py:31`

    Add an Alembic migration requirement that drops indexes/FKs/table cleanly, updates migration
    schema assertions, and either provides a downgrade that recreates the empty table shape or
    documents intentional one-way data loss. Update observability docs/tests for removing
    `skriptoteket_active_sessions`. Proof must include `pdm run db-upgrade`, affected migration
    tests/schema assertions, and `pdm run docs-validate`.

11. **medium - no-zombie auth contract test should be broader**

    File references:
    `frontend/apps/skriptoteket/src/api/authBootstrap.ts:31`,
    `src/skriptoteket/web/api/v1/auth.py:129`,
    `src/skriptoteket/web/api/v1/auth.py:330`

    Assert OpenAPI absence for every local browser-auth path and schema:
    login/logout/me/csrf/register/register-validate/resend-verification/verify-email/
    forgot-password/reset-password and `Login*`, `MeResponse`, `CsrfResponse`. Hand-type
    `SharedCsrfResponse` in `sharedAuth.ts` instead of depending on Skriptoteket OpenAPI.

12. **medium - active scripts must not be silently broken**

    File references:
    `pyproject.toml:296`,
    `scripts/_playwright_auth.py:73`

    Define a supported script allowlist, update those helpers to HuleEdu/shared-session proof
    style, and retire or archive historical PR scripts that call `/api/v1/auth/login` or `/csrf`.
    Add a static grep test for active command surfaces.

### Suggestions (Optional)

- Keep the route inventory and ceremony matrix close to the implementation notes so reviewers can
  diff the intended migration against the actual route changes.
- Prefer one live PR-0253 proof script that starts backend/Vite and exercises the edge-signed path,
  rather than several historical proof scripts with overlapping setup.

### Decision Approvals

- [x] `PR-0253` is the hard-break task for local browser-auth authority retirement
- [x] Revised task shape closes the prior architectural gaps as implementation constraints
- [x] Retained review gate is satisfied
- [x] Browser API edge contract is frozen
- [x] Provisioning/missing-projection policy is frozen
- [x] Public auth ceremony matrix is frozen
- [x] Session migration/data-loss policy is frozen
- [x] No-zombie contracts and supported scripts are covered

### Retained Re-review (2026-04-11)

**Reviewer:** `lead-developer`
**Verdict:** `approved`

The revised `PR-0253` shape is architecturally acceptable. The prior findings for browser API
transport, provisioning, CSRF trust boundary, frontend ceremony replacement, session deletion
policy, supported script allowlist, no-zombie contracts, and live proof are now pinned down well
enough for an implementer.

#### Required Changes

None. The docs-quality closeout aligned frontmatter status, TL;DR, decision approvals, checklist
state, `PR-0253` retained-review gate wording, handoff status, and validation evidence with the
approved task shape. Do not reopen the architectural decision package unless new evidence appears.

### Verification

- `pdm run docs-validate` (pass on 2026-04-11 after retaining `REV-PR-0253` and revising
  `PR-0253`).
- `pdm run docs-validate` (pass on 2026-04-11 after approving `REV-PR-0253` through docs-quality
  closeout).
- `pdm run pytest -q tests/integration/test_migration_c1d2e3f4a5b6_idempotent.py -m docker
  --override-ini addopts=''` (pass on 2026-04-11 after implementation; proves sessions-table drop
  and downgrade shape).
- `ARTIFACTS_ROOT=.artifacts/local-tool-artifacts pdm run pr-0253-auth-retirement --start-backend
  --start-vite` (pass on 2026-04-11 after implementation; proves signed read/write, stale-CSRF
  missing-context `401`, missing projection `401`, and inloggning ceremony handoff).

## Changes Made

| Change | Artifact | Description |
|--------|----------|-------------|
| 1 | `REV-PR-0253` | Retained the initial review findings that shaped implementation approval |
| 2 | `PR-0253` | Required review gate, route inventory, browser API edge, ceremony matrix, provisioning policy, CSRF trust-boundary proof, session migration policy, no-zombie tests, supported scripts, and live proof |
| 3 | `REV-PR-0253` | Recorded retained re-review: architecture accepted, with temporary docs-quality cleanup remaining |
| 4 | `REV-PR-0253` / `PR-0253` | Closed docs-quality drift and approved the retained review for implementation planning |
| 5 | `REV-PR-0253` | Recorded retained implementation review as `changes_requested` with four required remediation findings and failing verification evidence |
| 6 | `REV-PR-0253` | Added reviewer-owned remediation checklist for tracking implementation review closeout |
| 7 | `REV-PR-0253` / `PR-0253` / `ST-28-03` | Submitted implementation remediation evidence and left reviewer-owned acceptance gates pending |
| 8 | `REV-PR-0253` / `PR-0253` / `EPIC-28` / `REF-hule-education-product-identity-realms-and-skriptoteket-standalone-identity` | Recorded the product identity realm correction so local browser-session retirement does not erase standalone Skriptoteket identity |
| 9 | `REV-PR-0253` / `PR-0253` / frontend auth entry | Split browser ceremony URLs from shared auth API endpoints and renamed HuleEdu-only login copy to `inloggning`/Skriptoteket access language |
| 10 | `REV-PR-0253` / `PR-0253` / `ST-28-03` / `EPIC-28` | Approved the retained implementation re-review, closed the reviewer checklist, and moved the governed PR/story to done |
