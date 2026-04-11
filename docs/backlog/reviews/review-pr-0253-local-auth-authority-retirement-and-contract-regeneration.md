---
type: review
id: REV-PR-0253
title: "Review: PR-0253 local auth authority retirement and contract regeneration"
status: approved
owners: "agents"
created: 2026-04-11
updated: 2026-04-11
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
---

## TL;DR

`PR-0253` is approved as the hard-break task that removes Skriptoteket-local browser-auth
authority. Retained re-review confirms the revised task closes the prior architectural gaps around
browser API edge, provisioning, CSRF trust boundary, frontend ceremony, session deletion policy,
supported scripts, and live proof; the later docs-quality cleanup aligned the review state,
checklists, and handoff with that decision.

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
   verify pages. Replace `auth.login()` with a HuleEdu handoff adapter, make `auth.logout()` call
   `sharedAuthUrl("/v1/auth/logout")`, and remove or redirect register/forgot/reset/verify/resend
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

## Changes Made

| Change | Artifact | Description |
|--------|----------|-------------|
| 1 | `REV-PR-0253` | Retained the initial review findings that shaped implementation approval |
| 2 | `PR-0253` | Required review gate, route inventory, browser API edge, ceremony matrix, provisioning policy, CSRF trust-boundary proof, session migration policy, no-zombie tests, supported scripts, and live proof |
| 3 | `REV-PR-0253` | Recorded retained re-review: architecture accepted, with temporary docs-quality cleanup remaining |
| 4 | `REV-PR-0253` / `PR-0253` | Closed docs-quality drift and approved the retained review for implementation planning |
