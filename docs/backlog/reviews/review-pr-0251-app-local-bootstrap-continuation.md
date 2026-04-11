---
type: review
id: REV-PR-0251
title: "Review: PR-0251 app-local bootstrap continuation"
status: approved
owners: "agents"
created: 2026-04-11
updated: 2026-04-11
reviewer: "lead-developer"
prs:
  - PR-0251
adrs:
  - ADR-0082
links:
  - EPIC-28
  - ST-28-01
  - PR-0253
---

## TL;DR

`PR-0251` carried one retained decision before the next implementation slice:
Skriptoteket should hydrate app-local AI policy and profile preferences after
the HuleEdu shared session bootstrap without restoring `/api/v1/auth/me`, local
browser sessions, bearer storage, or an app-local auth bridge.

Implementation review update: the ADR direction remains approved, and the
retained implementation review is now **approved** after `PR-0255` remediated
the HuleEdu request-context boundary, local projection response, signed payload
contract, live proof, and auth-store module split.

## Problem Statement

The first `PR-0251` frontend slice now consumes the HuleEdu-owned browser
session and CSRF endpoints. The remaining fields from the old local bootstrap
are not HuleEdu browser-auth state:

- `ai_policy`
- `profile.allow_remote_fallback`
- `profile.inline_completion_provider`

Those fields are still required for existing editor AI behavior, remote-provider
consent, and profile UI parity. The implementation needs a clear boundary so it
does not smuggle local browser auth ownership back in while preserving
Skriptoteket app semantics.

## Proposed Solution

Approve `ADR-0082` as the governing direction for `PR-0251`:

- HuleEdu `GET /v1/auth/session` remains the only browser auth bootstrap.
- Skriptoteket exposes or uses a separate app-local continuation for app-owned
  state.
- The continuation derives the local user from HuleEdu-proven request context,
  not local browser sessions.
- AI policy is Skriptoteket runtime policy.
- AI preferences live on Skriptoteket `UserProfile`.
- Editor AI routes consume app-local AI preferences rather than
  `Session.allow_remote_fallback` / `Session.inline_completion_provider`.

## Artifacts to Review

| File | Focus | Time |
|------|-------|------|
| `docs/adr/adr-0082-app-local-bootstrap-continuation-on-huleedu-session.md` | Decision boundary and rejected options | 8 min |
| `docs/backlog/prs/pr-0251-st-28-01-session-bootstrap-api-client-cutover.md` | PR scope, acceptance criteria, and remaining work | 5 min |
| `docs/backlog/stories/story-28-01-frontend-auth-store-and-api-client-cutover-to-huleedu-session-contract.md` | Parent story expectations | 4 min |
| `frontend/apps/skriptoteket/src/stores/auth.ts` | Current frontend bootstrap orchestration | 4 min |
| `src/skriptoteket/web/api/v1/editor/completions.py` and sibling editor AI routes | Session-carried AI preference dependencies | 5 min |

**Total estimated time:** ~26 minutes

## Key Decisions

| Decision | Rationale | Approve? |
|----------|-----------|----------|
| Use a separate app-local continuation after HuleEdu session bootstrap | Preserves rich app state without making Skriptoteket a browser auth authority | [x] |
| Keep AI preferences on `UserProfile`, not local browser sessions | AI consent is app profile state, not session authority | [x] |
| Replace editor AI route dependency on local `Session` preference fields | Enables `PR-0253` to remove local browser session ownership cleanly | [x] |
| Fail closed for remote-AI affordances when app AI bootstrap is missing | Preserves remote-provider consent and safety guardrails | [x] |

## Review Checklist

- [x] `ADR-0082` stays compatible with `ADR-0076`
- [x] The continuation endpoint does not answer browser-auth identity questions
- [x] Local roles/profile/AI preference ownership remains in Skriptoteket
- [x] No local `/api/v1/auth/me` fallback, bearer storage, or session mirror is implied
- [x] Implementation consequences for `PR-0251` and `PR-0253` are explicit
- [x] Verification expectations include frontend bootstrap and AI preference behavior

## Review Feedback

**Reviewer:** `lead-developer`
**Date:** `2026-04-11`
**Verdict:** `approved`

### Required Changes

None for the retained decision package. `ADR-0082` is approved as the governing continuation
boundary for the remaining `PR-0251` work.

### Suggestions (Optional)

- During implementation, make the frontend AI store fail closed while `ai_policy` is missing rather
  than treating an unloaded app-local continuation as remote-provider consent.
- Keep the first implementation slice narrow: app bootstrap state, profile AI preferences, and
  editor AI preference dependencies only. Login/logout ceremony cleanup should remain with
  `PR-0252` / `PR-0253` unless the boundary is explicitly updated.

### Decision Approvals

- [x] Use a separate app-local continuation after HuleEdu session bootstrap
- [x] Keep AI preferences on `UserProfile`, not local browser sessions
- [x] Replace editor AI route dependency on local `Session` preference fields
- [x] Fail closed for remote-AI affordances when app AI bootstrap is missing

### Implementation Review (2026-04-11)

**Reviewer:** `lead-developer`
**Verdict:** `changes_requested`

#### Scope Reviewed

Public surfaces under review:

- `GET /api/v1/profile/app-continuation`
- `useAuthStore.bootstrap()` two-phase browser bootstrap
- shared HuleEdu session/CSRF URL adapter
- editor AI preference dependencies for chat, inline completions, and edit-ops
- OpenAPI TypeScript continuation response contract

Changed artifacts reviewed:

- `src/skriptoteket/web/api/v1/profile.py`
- `src/skriptoteket/web/api/v1/ai_policy.py`
- `src/skriptoteket/web/auth/ai_preferences.py`
- `src/skriptoteket/web/api/v1/editor/chat.py`
- `src/skriptoteket/web/api/v1/editor/completions.py`
- `src/skriptoteket/web/api/v1/editor/edit_ops.py`
- `frontend/apps/skriptoteket/src/api/sharedAuth.ts`
- `frontend/apps/skriptoteket/src/api/appContinuation.ts`
- `frontend/apps/skriptoteket/src/stores/auth.ts`
- `frontend/apps/skriptoteket/src/stores/ai.ts`
- focused backend/frontend tests listed in `PR-0251`

#### Findings

1. **blocker - continuation still depends on the local session-cookie auth path**

   File reference: `src/skriptoteket/web/api/v1/profile.py:104`

   `GET /api/v1/profile/app-continuation` uses `require_user_api`, which resolves
   `User` through `get_session_id()` and `CurrentUserProviderProtocol` with a
   Skriptoteket `SESSION_COOKIE_NAME` cookie. That contradicts `ADR-0082`, which
   requires the continuation endpoint to derive the user from HuleEdu-owned
   browser-session authority, not a Skriptoteket browser session row. In the new
   frontend flow, the browser can be authenticated through
   `GET https://api.hule.education/v1/auth/session` and still get `401` from the
   app-local continuation because no valid local Skriptoteket session cookie is
   involved.

   Why it matters: the claimed two-phase bootstrap cannot preserve app-local AI
   policy/profile preferences after the auth cutover without either keeping the
   old local auth bridge alive or failing every real HuleEdu-only session at the
   continuation step. The current unit test also masks this by using a stub
   `CurrentUserProviderProtocol` that returns a user even when no session id was
   supplied.

   Concrete fix: add a protocol-first HuleEdu request-context resolver for
   downstream app requests, backed by gateway-forwarded signed identity context,
   and make the continuation dependency resolve or idempotently provision the
   local Skriptoteket user/profile projection from that context. Do not route
   this endpoint through `get_session_id()` / local `SessionRepositoryProtocol`.
   If the gateway-context resolver is intentionally out of scope for `PR-0251`,
   split the continuation implementation out and keep this PR open rather than
   claiming the continuation contract is implemented.

   Proof requirement: add tests where an authenticated HuleEdu request context,
   without a Skriptoteket session cookie, returns `200` and profile preferences;
   add a negative test where missing/invalid gateway context returns `401`; keep
   the existing unauthenticated `401` test. Run:
   `pdm run pytest -q tests/unit/web/test_profile_app_continuation_api.py` and
   `pdm run typecheck`.

2. **high - local authorization role is inferred from HuleEdu policy roles**

   File reference: `frontend/apps/skriptoteket/src/api/sharedAuth.ts:92`

   `mapBrowserSessionToAuthSnapshot()` calls `resolveLocalRole()` on
   `payload.policy.roles` and stores that as the Skriptoteket `user.role`.
   The governing guardrails say authorization roles remain local to
   Skriptoteket, while HuleEdu owns browser session authority. The app-local
   continuation response currently returns AI policy and AI preferences only, so
   there is no implemented local projection that can preserve existing
   contributor/admin/superuser behavior when HuleEdu roles are absent,
   differently named, or tenant-scoped.

   Why it matters: role-aware getters and protected editor/admin affordances can
   silently downgrade a real contributor to `user`, or incorrectly elevate a
   user if HuleEdu policy roles happen to use Skriptoteket role names for a
   different purpose. This violates the `PR-0251` acceptance criterion that
   existing role and app-authorization getters remain behaviorally equivalent.

   Concrete fix: do not treat HuleEdu provider roles as the source of
   Skriptoteket authorization. Have the app-local continuation/local projection
   return the Skriptoteket-local role and app authorization fields, or expose a
   distinct typed mapping that can only consume explicitly Skriptoteket-scoped
   grants/roles from the gateway contract. Keep `policy.grants` and
   `feature_flags` as shared-session data, but make local role ownership
   explicit.

   Proof requirement: add frontend tests where the HuleEdu session has no
   Skriptoteket role names but the app-local continuation supplies a contributor
   role, and verify `hasAtLeastRole("contributor")` remains true; add a test
   that foreign HuleEdu roles do not elevate local authorization. Run:
   `pdm run fe-test -- --run src/api/sharedAuth.spec.ts src/stores/auth.spec.ts`
   and `pdm run fe-type-check`.

#### Decision

`changes_requested`

#### Verification

- `pdm run docs-validate` (pass on 2026-04-11 after retained implementation review update)

#### Required Follow-Ups

- Fix the user-resolution boundary for `GET /api/v1/profile/app-continuation`
  before closing `PR-0251`.
- Fix or explicitly split the local-role/app-authorization projection before
  claiming the rich bootstrap equivalence acceptance criterion is met.

### Remediation Implementation (2026-04-11)

`PR-0255` has now implemented the requested fixes that the retained `REV-PR-0251` re-review
approves below:

- `GET /api/v1/profile/app-continuation` no longer depends on `require_user_api`,
  `settings.SESSION_COOKIE_NAME`, local session ids, or `SessionRepositoryProtocol`.
- The route verifies HuleEdu `InternalIdentityContextV1` headers using the concrete
  `X-Huledu-Identity-*` transport, detached RS256 signature, issuer/audience, payload version,
  required fields, TTL, and clock-skew rules.
- The local projection resolves existing users by `(auth_provider=huleedu,
  external_id=<context.sub>)`, fails closed when missing, and creates only a safe default profile
  for an already resolved local user.
- The continuation response carries `local_user`, matching `profile`, `ai_policy`,
  `allow_remote_fallback`, and `inline_completion_provider`.
- The SPA now hydrates `auth.user` and local RBAC from app continuation; HuleEdu `policy.roles`
  remain provider metadata, while `policy.grants` and `policy.feature_flags` remain preserved as
  shared-session metadata.

Verification evidence:

- `pdm run pytest -q tests/unit/web/test_profile_app_continuation_api.py` passed with 22 tests
  after the required signed-payload field remediation.
- `pdm run pytest -q tests/unit/web/test_profile_app_continuation_api.py tests/unit/web/test_editor_inline_completion_api.py` passed with 31 tests.
- `pdm run fe-test -- --run src/api/sharedAuth.spec.ts src/stores/auth.spec.ts src/stores/ai.spec.ts src/api/client.spec.ts` passed with 58 tests.
- `pdm run fe-test -- --run src/api/sharedAuth.spec.ts src/stores/auth.spec.ts src/api/client.spec.ts` passed with 56 tests after splitting auth bootstrap transport helpers out of the store.
- `pdm run typecheck` passed after the implementation review fixes.
- `pdm run fe-type-check` passed after the auth-store SRP split.
- `pdm run fe-lint` passed after the auth-store SRP split.
- `pdm run pr-0255-auth-bootstrap --start-backend --start-vite` passed: the real `pdm run dev`
  backend verified signed HuleEdu context against a seeded HuleEdu-linked local user, returned
  `200` for valid context and `401` for missing context, and the SPA opened `/editor` after its
  app-continuation call hit the real backend route through the Vite `/api` proxy.
- `pdm run docs-validate` passed after the implementation review fixes.
- `pdm run lint` passed after the implementation review fixes.

Implementation review follow-up:

- `InternalIdentityContextV1` no longer accepts missing `org_id`, `tenant_id`, `roles`, or
  `grants`; the route tests now cover missing and blank required payload fields.
- `frontend/apps/skriptoteket/src/stores/auth.ts` is under the repo module-size budget after
  extracting HuleEdu bootstrap transport orchestration to `stores/authBootstrap.ts` and HTTP
  timeout/error parsing to `api/authHttp.ts`.
- The retained live proof is no longer the earlier temporary/stubbed route check; the Playwright
  command above exercises the real app factory, real DI graph, real DB repository lookup, and SPA
  continuation request path.

### Retained Re-review (2026-04-11)

**Reviewer:** `lead-developer`
**Verdict:** `approved`

#### Scope Re-reviewed

The re-review focused on the `PR-0255` remediation of the retained implementation blockers:

- signed `InternalIdentityContextV1` payload contract and verifier behavior
- `GET /api/v1/profile/app-continuation` HuleEdu request-context dependency
- app-local local-user/profile projection and frontend local RBAC hydration
- auth-store SRP/module-size split
- live route/bootstrap proof through the real backend and Vite `/api` proxy

#### Findings

None. The previous implementation findings are resolved:

- `GET /api/v1/profile/app-continuation` no longer depends on `require_user_api`, local session ids,
  `settings.SESSION_COOKIE_NAME`, or `SessionRepositoryProtocol`.
- The continuation response carries Skriptoteket-local `local_user`, matching `profile`, runtime
  `ai_policy`, and profile AI preferences.
- HuleEdu `policy.roles` stays provider metadata; local authorization comes from the app-local
  projection.
- `InternalIdentityContextV1` now requires `org_id`, `tenant_id`, `roles`, and `grants`, and rejects
  blank required strings or role/grant entries.
- `frontend/apps/skriptoteket/src/stores/auth.ts` is back under the module-size budget after
  bootstrap/network helpers moved to `stores/authBootstrap.ts` and `api/authHttp.ts`.
- `pdm run pr-0255-auth-bootstrap --start-backend --start-vite` now proves the real backend route,
  real DB projection lookup, and SPA continuation request path through Vite `/api`.

#### Verification

- `pdm run pytest -q tests/unit/web/test_profile_app_continuation_api.py` passed locally during
  re-review with 22 tests.
- `git diff --check` passed during re-review.
- Port checks confirmed no listener remained on `127.0.0.1:8000` or `127.0.0.1:5173` after the
  reported Playwright proof trail.

#### Decision

`approved`. `PR-0251` is review-clean for the app-local continuation remediation owned by
`PR-0255`; remaining login/logout ceremony and local-auth retirement work stays with `PR-0252` /
`PR-0253`, and cross-app/operator proof stays with `PR-0254`.

## Changes Made

| Change | Artifact | Description |
|--------|----------|-------------|
| 1 | `ADR-0082` | Drafted the app-local bootstrap continuation decision for `PR-0251` |
| 2 | `PR-0251` | Linked the proposed ADR and retained review gate |
| 3 | `REV-PR-0251` | Reviewed `ADR-0082` against `ADR-0076`, current frontend bootstrap state, and editor AI `Session` preference dependencies |
| 4 | `ADR-0082` | Accepted the app-local continuation boundary as the governing direction for the remaining `PR-0251` implementation |
| 5 | `REV-PR-0251` | Recorded the retained implementation review and requested changes for HuleEdu request-context resolution plus local role projection |
| 6 | `PR-0255` | Implemented the HuleEdu request-context continuation and local projection remediation |
| 7 | `REV-PR-0251` | Approved the retained implementation re-review after the `PR-0255` remediation fixes |
