---
type: pr
id: PR-0251
title: "ST-28-01 session bootstrap API client cutover"
status: done
owners: "agents"
created: 2026-04-10
updated: 2026-04-30
stories:
  - "ST-28-01"
adrs:
  - "ADR-0082"
tags: ["frontend", "auth", "api-client", "session"]
acceptance_criteria:
  - "Given the HuleEdu browser-session provider is ready, when the Skriptoteket SPA boots, then the auth store hydrates from `GET https://api.hule.education/v1/auth/session` instead of local `/api/v1/auth/me`."
  - "Given unsafe browser writes require CSRF, when the frontend sends a non-GET request, then it obtains the current token from `GET https://api.hule.education/v1/auth/csrf` and sends the required CSRF header with credentials."
  - "Given Skriptoteket depends on rich bootstrap state, when the shared session document hydrates the auth store, then existing role, profile, AI policy, and app-authorization getters remain behaviorally equivalent."
  - "Given the target is a hard browser-session cutover, when this PR is reviewed, then it contains no bearer-token storage, local auth bridge, or compatibility path back to `/api/v1/auth/me`."
---

## Problem

Skriptoteket already uses the stronger browser model that the shared HuleEdu contract should
preserve, but the frontend still points at local auth bootstrap and CSRF surfaces.

## Goal

Move the SPA auth store and API client to the HuleEdu-owned browser session and CSRF endpoints
while preserving current app semantics.

## Non-goals

- Removing Skriptoteket-local auth authority. That cleanup belongs to `PR-0253`.
- Changing the dedicated `/auth/login` route behavior. That belongs to `PR-0252`.
- Introducing bearer-browser auth.

## Implementation Plan

1. Audit `frontend/apps/skriptoteket/src/stores/auth.ts` and API client CSRF handling.
2. Introduce the shared HuleEdu session and CSRF endpoint configuration using the existing
   environment/configuration pattern.
3. Map the HuleEdu session document into the existing auth-store shape without downgrading current
   getters.
4. Add focused unit coverage for bootstrap success, anonymous bootstrap, CSRF refresh, and no
   bearer/local-storage regression.

## Progress (2026-04-11)

- Added `frontend/apps/skriptoteket/src/api/sharedAuth.ts` as the shared HuleEdu browser-session
  contract adapter.
- `useAuthStore.bootstrap()` now reads `GET https://api.hule.education/v1/auth/session` through the
  shared auth URL helper instead of local `/api/v1/auth/me`.
- `useAuthStore.ensureCsrfToken()` now reads `GET https://api.hule.education/v1/auth/csrf`.
- The auth store now preserves shared-session `policy.grants` and `policy.feature_flags` rather
  than dropping them during bootstrap.
- Focused tests cover default/override auth base URLs, HuleEdu session-to-auth snapshot mapping,
  anonymous session mapping, bootstrap, and unsafe API writes fetching shared CSRF without adding
  bearer `Authorization`.
- `REV-PR-0251` approved `ADR-0082` as the retained boundary for app-local AI/profile
  continuation after HuleEdu session bootstrap.
- The reviewer-requested frontend fail-closed guard is implemented: `useAiStore()` now treats a
  missing app-local `ai_policy` as remote providers disabled until the continuation loads, with
  focused coverage in `frontend/apps/skriptoteket/src/stores/ai.spec.ts`.
- Added the app-local continuation endpoint at `GET /api/v1/profile/app-continuation`, returning
  runtime `ai_policy` plus profile-owned `allow_remote_fallback` and
  `inline_completion_provider`.
- `useAuthStore.bootstrap()` now performs the intended two-phase bootstrap: HuleEdu shared session
  first, Skriptoteket app continuation second, with no `/api/v1/auth/me` fallback.
- Editor AI routes now resolve remote fallback and inline completion provider preferences from
  request-scoped profile state instead of `Session.allow_remote_fallback` /
  `Session.inline_completion_provider`.
- OpenAPI TypeScript contracts were regenerated after adding the continuation response.
- Retained implementation review initially requested changes for app-continuation user resolution
  and local authorization projection; `PR-0255` now remediates those findings.
- Remediation is captured in `PR-0255`: add HuleEdu request-context user/profile projection for
  app continuation and make the frontend local authorization source explicit before `PR-0251`
  close-out.
- `PR-0255` remediation is implemented and retained `REV-PR-0251` re-review is approved: app
  continuation verifies signed HuleEdu `InternalIdentityContextV1` headers, resolves existing local
  HuleEdu projections by `(auth_provider, external_id)`, returns `local_user` plus matching
  `profile`, and the SPA hydrates `auth.user.id` / local RBAC from that app projection rather than
  HuleEdu provider roles or provider subject id.

Closeout reconciliation (2026-04-30):

- `PR-0251` is now marked `done` because the shared-session bootstrap and
  app-local continuation remediation were review-clean after `PR-0255`.
- The login/logout ceremony cleanup that this PR intentionally deferred
  shipped through `PR-0252` and `PR-0253`.
- The cross-app/browser smoke proof then shipped through `PR-0254` and
  `PR-0263`, and the auth outcome observability closeout shipped through
  `PR-0264`.
- The old `in_progress` frontmatter was stale relative to the already-done
  `EPIC-28` authority.

## Test Plan

- Run focused auth store and API client tests.
- Run focused AI store tests for missing app-local `ai_policy` fail-closed behavior.
- Add focused app-continuation tests covering two-phase bootstrap, no `/api/v1/auth/me` fallback,
  and missing app-local AI bootstrap as remote-AI disabled until loaded. (Done.)
- Add or update focused editor AI route tests when the backend preference dependency moves off
  local `Session`. (Done for inline completions; chat/edit-ops use the same dependency.)
- Run focused backend route tests for the profile continuation and editor AI preference dependency.
- Run `pdm run fe-type-check`.
- Run `pdm run typecheck`.
- Run `pdm run lint`.
- Run `pdm run docs-validate`.

## Rollback Plan

Revert the endpoint/configuration changes and restore local bootstrap while keeping the docs task
open for a corrected provider contract.
