---
type: pr
id: PR-0255
title: "ST-28-01 PR-0251 remediation: HuleEdu context and local authorization projection"
status: done
owners: "agents"
created: 2026-04-11
updated: 2026-04-11
stories:
  - "ST-28-01"
adrs:
  - "ADR-0076"
  - "ADR-0082"
links:
  - "REV-PR-0255"
  - "REV-PR-0251"
  - "PR-0251"
tags: ["auth", "backend", "frontend", "review-remediation"]
acceptance_criteria:
  - "Given HuleEdu Gateway forwards `InternalIdentityContextV1` using `X-Huledu-Identity-Context-Version`, `X-Huledu-Identity-Context`, `X-Huledu-Identity-Key-Id`, and `X-Huledu-Identity-Signature`, when `GET /api/v1/profile/app-continuation` is called without a Skriptoteket session cookie for an existing local projection, then Skriptoteket verifies issuer, audience, key id, RS256 signature, payload version, required fields, TTL, clock skew, and returns `200`."
  - "Given the app-local continuation request has missing, malformed, unsigned, unknown-key, wrong-audience, wrong-issuer, expired, future-issued, or overlong-lifetime HuleEdu identity context, when the endpoint is called, then it returns `401` and does not fall back to `settings.SESSION_COOKIE_NAME`, `SessionRepositoryProtocol`, `/api/v1/auth/me`, bearer storage, unsigned identity headers, or a local browser-auth bridge."
  - "Given the verified HuleEdu subject has an existing Skriptoteket projection at `(auth_provider=huleedu, external_id=<context.sub>)`, when app continuation succeeds, then the response carries `local_user` equivalent to the local `User` contract plus the matching `profile`, `ai_policy`, `allow_remote_fallback`, and `inline_completion_provider`."
  - "Given HuleEdu `user.user_id` differs from the Skriptoteket-local `local_user.id`, when the SPA bootstrap completes, then `auth.user.id` is the Skriptoteket-local UUID used by app APIs and ownership comparisons, while shared `policy.grants` and `policy.feature_flags` remain preserved as shared-session metadata."
  - "Given HuleEdu shared-session `policy.roles` is absent, foreign, or tenant-scoped, when the SPA bootstrap completes, then Skriptoteket role-aware getters use `local_user.role` from app continuation rather than inferring authorization from HuleEdu provider roles."
  - "Given this remediation changes an API route and SPA bootstrap path, when implementation is complete, then focused backend/frontend tests, type/lint/docs gates, and a live continuation/bootstrap check are recorded in `PR-0255`, `REV-PR-0251`, and `.agents/handoff.md`."
---

## Problem

`REV-PR-0251` changed the implementation verdict for `PR-0251` to `changes_requested`.
The architectural decision in `ADR-0082` remains approved, but the current code still violates two
required cutover boundaries.

`REV-PR-0255` re-reviewed this remediation response and approved the revised implementation
contract: the app-local projection carries Skriptoteket-local user identity, not only role, and the
HuleEdu gateway identity verification contract is concrete enough to implement fail-closed.

This revision consumes the named HuleEdu provider artifacts from `PR-0250`:

- `REF-shared-browser-session-consumer-conformance-v1`
- `REF-internal-identity-context-v1-contract`
- HuleEdu shared library helpers for `InternalIdentityContextV1`

The current HuleEdu `InternalIdentityContextV1` payload does not carry email or email verification
claims. Therefore this remediation must not fabricate new local users from `sub` alone. `PR-0255`
should resolve an existing local projection by `(auth_provider=huleedu, external_id=<sub>)`; any
first-login provisioning flow requires a signed provider contract that carries enough identity
profile data and should be recorded as a provider follow-up if needed.

First, `GET /api/v1/profile/app-continuation` currently depends on `require_user_api`, which
resolves the actor through the old Skriptoteket session-cookie path:

- `settings.SESSION_COOKIE_NAME`
- `get_session_id()`
- `CurrentUserProviderProtocol.get_current_user(session_id=...)`
- local `SessionRepositoryProtocol`-backed browser session rows

That means a real HuleEdu-authenticated browser can successfully load
`GET https://api.hule.education/v1/auth/session` and still receive `401` from the app-local
continuation endpoint unless the old Skriptoteket session cookie also exists. This keeps a hidden
local browser-auth dependency alive.

Second, the SPA currently derives `user.role` from HuleEdu shared-session `policy.roles`.
Skriptoteket roles are local authorization, not HuleEdu browser-session authority. Inferring local
RBAC from provider roles can silently downgrade existing contributors/admins or accidentally
elevate users when unrelated HuleEdu roles happen to reuse Skriptoteket role names.

The existing continuation tests prove response shape, but they do not prove the HuleEdu-only
request path because the current user provider stub returns a user even when no local session id was
provided.

## Goal

Remediate the retained `PR-0251` implementation review by making the app-local continuation truly
HuleEdu-context-derived while keeping Skriptoteket-local authorization explicit.

The desired shape is:

1. HuleEdu remains the only browser auth bootstrap through `GET /v1/auth/session`.
2. HuleEdu Gateway forwards signed internal identity context to Skriptoteket.
3. Skriptoteket verifies that context behind protocol-first DI.
4. Skriptoteket resolves the local user/profile projection by HuleEdu subject. Idempotent
   provisioning is allowed only if a signed provider contract supplies the required local-user
   creation fields; the current `InternalIdentityContextV1` contract does not.
5. The app-local continuation returns Skriptoteket-owned bootstrap state, including `local_user`,
   matching `profile`, AI policy, and profile AI preferences.
6. The SPA uses HuleEdu session data for browser identity/shared metadata and uses the
   app-local continuation for Skriptoteket-local user id, role, profile identity, and app
   authorization.

## Non-goals

- Implementing or redesigning login/logout ceremony. That remains with `PR-0252` / `PR-0253`
  unless it directly blocks this remediation.
- Changing `/auth/login` return-to-origin behavior. That remains `PR-0252`.
- Deleting all old local browser-auth routes and generated contract remnants. That remains
  `PR-0253` after this consumer path is review-clean.
- Adding browser bearer auth, frontend token storage, direct browser calls to HuleEdu Identity, or
  a Skriptoteket-local auth bridge.
- Replacing the broader cross-app smoke proof owned by `PR-0254`.

## Suggested Solution

### Backend

Add a protocol-first HuleEdu request-context seam for downstream app requests.

The verifier contract is no longer open-ended. `PR-0255` consumes HuleEdu
`InternalIdentityContextV1` exactly as defined by `REF-shared-browser-session-consumer-conformance-v1`
and `REF-internal-identity-context-v1-contract`.

Required transport headers:

- `X-Huledu-Identity-Context-Version`
- `X-Huledu-Identity-Context`
- `X-Huledu-Identity-Key-Id`
- `X-Huledu-Identity-Signature`
- `X-Correlation-ID` for traceability

Required payload fields after decoding the base64url canonical JSON context:

- `context_version`
- `iss`
- `aud`
- `sub`
- `session_id`
- `org_id`
- `tenant_id`
- `roles`
- `grants`
- `policy_version`
- `iat`
- `exp`
- `jti`
- optional `active_context`
- optional `feature_flags`
- optional `source_app`

Verification requirements:

- `X-Huledu-Identity-Key-Id` must be present, non-blank, and recognized in trusted public keys.
- `X-Huledu-Identity-Signature` must use the `rs256=` prefix and verify as a detached RS256
  signature over the exact encoded `X-Huledu-Identity-Context` value.
- `context_version` must be `1`.
- `iss` must equal `api_gateway_service` unless an explicitly configured accepted issuer replaces
  the HuleEdu default.
- `aud` must equal this service's configured audience. The default expected audience is
  `settings.SERVICE_NAME`, currently `skriptoteket`, unless
  `HULEEDU_INTERNAL_IDENTITY_AUDIENCE` overrides it.
- Required strings (`iss`, `aud`, `sub`, `session_id`, `policy_version`, `jti`) must be non-blank
  after trimming.
- `exp` must not precede `iat`.
- Signed context lifetime must not exceed `HULEEDU_INTERNAL_IDENTITY_TTL_SECONDS`; current HuleEdu
  default is 60 seconds.
- `iat` and `exp` must respect `HULEEDU_INTERNAL_IDENTITY_ALLOWED_CLOCK_SKEW_SECONDS`; current
  HuleEdu default is 5 seconds.
- Verification must fail closed for missing headers, unsupported version, unknown key id, invalid
  signature, invalid payload, wrong issuer/audience, future-issued context, expired context, or
  overlong lifetime.
- Legacy unsigned identity headers such as `X-User-ID`, `X-Org-ID`, and `X-Identity-Encoding` must
  not be accepted for the migrated app-continuation route.

Suggested code boundaries:

- a typed internal identity context model for the signed HuleEdu gateway payload
- a web-layer resolver/verifier that reads the gateway-forwarded context from request headers
- a protocol for resolving the local Skriptoteket projection from verified HuleEdu context
- a dependency such as `require_huleedu_app_user_projection` for app-local continuation routes
- settings for trusted HuleEdu public keys and expected audience/issuer, using the HuleEdu setting
  names where practical:
  - `HULEEDU_INTERNAL_IDENTITY_PUBLIC_KEY`
  - `HULEEDU_INTERNAL_IDENTITY_PUBLIC_KEY_PATH`
  - `HULEEDU_INTERNAL_IDENTITY_TRUSTED_PUBLIC_KEYS_JSON`
  - `HULEEDU_INTERNAL_IDENTITY_AUDIENCE`
  - `HULEEDU_INTERNAL_IDENTITY_ISSUER`
  - `HULEEDU_INTERNAL_IDENTITY_TTL_SECONDS`
  - `HULEEDU_INTERNAL_IDENTITY_ALLOWED_CLOCK_SKEW_SECONDS`

The continuation endpoint should stop depending on `require_user_api` for this route. It should not
read `settings.SESSION_COOKIE_NAME`, local session ids, or local session rows.

Projection behavior should be explicit and testable:

- add a repository protocol method for lookup by `(auth_provider, external_id)`, backed by the
  existing `uq_users_auth_provider_external_id` database invariant
- look up existing Skriptoteket users with `auth_provider=huleedu` and
  `external_id=<InternalIdentityContextV1.sub>`
- preserve existing local `role` and profile AI preferences
- create a safe default local profile only for an already resolved local user that has no profile
- do not auto-create a local user from `sub` alone because the current signed context does not carry
  email or email-verification claims
- if no local user projection exists, fail closed with an explicit app-local projection error and
  record the missing provisioning contract rather than fabricating a user id or email
- never derive Skriptoteket admin/contributor/superuser authorization from generic HuleEdu roles

Freeze the continuation response shape so it carries the local projection the SPA needs:

```json
{
  "local_user": {
    "id": "<skriptoteket-local-user-uuid>",
    "email": "teacher@example.test",
    "role": "contributor",
    "auth_provider": "huleedu",
    "external_id": "<huleedu-context-sub>",
    "is_active": true,
    "email_verified": true
  },
  "profile": {
    "user_id": "<skriptoteket-local-user-uuid>",
    "first_name": null,
    "last_name": null,
    "display_name": "Teacher",
    "locale": "sv-SE",
    "allow_remote_fallback": true,
    "inline_completion_provider": "external"
  },
  "ai_policy": {
    "remote_providers_enabled": true,
    "completion_external_available": true,
    "completion_local_available": true
  },
  "allow_remote_fallback": true,
  "inline_completion_provider": "external"
}
```

The exact Pydantic response can reuse existing `User`, `UserProfile`, and `AiPolicyResponse`
models, but the field must be named `local_user` or `app_user`; do not call it a HuleEdu session
`user`.

### Frontend

Stop using HuleEdu shared-session `policy.roles` as the local RBAC source.

Suggested frontend behavior:

- keep `policy.grants` and `policy.feature_flags` from the HuleEdu shared session as shared-session
  metadata
- treat shared-session `policy.roles` as provider metadata unless a future contract explicitly
  scopes roles to Skriptoteket authorization
- treat the HuleEdu shared-session `user.user_id` as provider subject metadata, not the local app
  user id
- hydrate `auth.user` from app-continuation `local_user` so `auth.user.id` remains the
  Skriptoteket-local UUID used by existing app APIs, ownership comparisons, editor state, profile
  linkage, and user-specific UI
- hydrate `auth.profile` from the matching app-continuation `profile`, with
  `profile.user_id === auth.user.id`
- avoid exposing local RBAC as ready until app continuation has loaded the local projection
- keep remote AI failed closed while app-local continuation is missing or failed
- keep bootstrap free of `/api/v1/auth/me`, bearer storage, and local auth fallback paths

### Tests

Add reviewer-requested proofs at the contract boundaries:

- backend positive: valid HuleEdu gateway identity context and no Skriptoteket session cookie returns
  `200` from `GET /api/v1/profile/app-continuation` for an existing
  `(auth_provider=huleedu, external_id=<sub>)` local user
- backend positive: projection lookup resolves the existing local user by
  `(auth_provider=huleedu, external_id=<sub>)` rather than by email or session id
- backend negative: missing context, unsupported version, missing key id, unknown key id, invalid
  signature, malformed payload, wrong issuer, wrong audience, expired context, future-issued
  context, and overlong lifetime each return `401`
- backend negative: valid HuleEdu context with no local projection fails closed without creating a
  placeholder user from `sub`
- backend regression: app continuation does not call local session-cookie/session-repository
  dependencies
- frontend positive: HuleEdu session has no Skriptoteket role names but app continuation supplies
  `contributor`, and `hasAtLeastRole("contributor")` is true
- frontend positive: HuleEdu `user.user_id` differs from app-continuation `local_user.id`; after
  bootstrap, `auth.user.id` equals the local UUID and `auth.profile.user_id` matches it
- frontend negative: foreign HuleEdu roles do not elevate local authorization
- frontend regression: bootstrap still does not call `/api/v1/auth/me` or use browser bearer storage

## Implementation Summary (2026-04-11)

Implemented the approved remediation:

- Added a typed `InternalIdentityContextV1` contract and verifier for the concrete HuleEdu
  `X-Huledu-Identity-*` header set, including key id lookup, detached RS256 verification, issuer,
  audience, payload version, TTL, clock skew, and fail-closed error cases.
- Added HuleEdu app-projection resolution by `(auth_provider=huleedu, external_id=<context.sub>)`
  through protocol-first DI. Missing local projection returns `401`; missing profile creates a safe
  default profile only after the local user projection exists.
- Moved `GET /api/v1/profile/app-continuation` off `require_user_api` and onto
  `require_huleedu_app_user_projection`, so this route no longer reads
  `settings.SESSION_COOKIE_NAME`, local session ids, or local session rows.
- Extended the continuation response to include `local_user`, matching `profile`, `ai_policy`,
  `allow_remote_fallback`, and `inline_completion_provider`; regenerated OpenAPI and frontend
  types.
- Updated the SPA bootstrap so `auth.user` and local RBAC come from app continuation, while HuleEdu
  `policy.grants` and `policy.feature_flags` remain shared-session metadata. HuleEdu
  `policy.roles` no longer elevates or downgrades Skriptoteket-local authorization.
- Added `pdm run pr-0255-auth-bootstrap --start-backend --start-vite` as the repo-standard
  Playwright proof. It starts the real dev backend, seeds a HuleEdu-linked local user in the real
  database, verifies the continuation route over HTTP (`200` for valid signed context, `401` when
  missing), and proves the SPA opens `/editor` after its app-continuation request hits the real
  backend route through the Vite `/api` proxy.

## Implementation Plan

1. Read `REV-PR-0251`, `ADR-0082`, `ADR-0076`, `PR-0250`, and the current `PR-0251` diff before
   editing.
2. Implement the `InternalIdentityContextV1` verifier using the concrete header, payload,
   signature, issuer, audience, TTL, and clock-skew rules in this PR. Reuse or closely mirror the
   HuleEdu shared helper semantics; do not accept unsigned legacy identity headers.
3. Add a local projection resolver protocol and repository lookup by `(auth_provider, external_id)`.
   The first implementation should resolve existing HuleEdu-linked local users and create missing
   profiles for resolved users only; local user auto-provisioning remains blocked until a signed
   email/email-verification provider contract exists.
4. Move `GET /api/v1/profile/app-continuation` from `require_user_api` to the new HuleEdu-derived
   app projection dependency.
5. Extend the continuation response contract to include `local_user`, `profile`, `ai_policy`,
   `allow_remote_fallback`, and `inline_completion_provider`, then regenerate OpenAPI TypeScript
   types.
6. Update `useAuthStore.bootstrap()` and shared auth mapping so `auth.user` and local RBAC come from
   app continuation, not HuleEdu provider roles or HuleEdu provider subject id.
7. Add the focused backend and frontend regression tests listed above.
8. Add a live route/bootstrap probe and record the exact command and result.
9. Update `PR-0251`, `REV-PR-0251`, linked story/epic/handoff docs with remediation outcome and
   verification evidence.

## Test Plan

- `pdm run pytest -q tests/unit/web/test_profile_app_continuation_api.py`
- `pdm run fe-test -- --run src/api/sharedAuth.spec.ts src/stores/auth.spec.ts src/stores/ai.spec.ts src/api/client.spec.ts`
- `pdm run typecheck`
- `pdm run fe-type-check`
- `pdm run fe-lint`
- `pdm run lint`
- `pdm run pr-0255-auth-bootstrap --start-backend --start-vite`
- `pdm run docs-validate`

Verification evidence captured on 2026-04-11:

- `pdm run pytest -q tests/unit/web/test_profile_app_continuation_api.py` passed with 22
  tests after tightening required signed payload fields.
- `pdm run pytest -q tests/unit/web/test_profile_app_continuation_api.py tests/unit/web/test_editor_inline_completion_api.py` passed with 31 tests.
- `pdm run fe-test -- --run src/api/sharedAuth.spec.ts src/stores/auth.spec.ts src/stores/ai.spec.ts src/api/client.spec.ts` passed with 58 tests.
- `pdm run fe-test -- --run src/api/sharedAuth.spec.ts src/stores/auth.spec.ts src/api/client.spec.ts` passed with 56 tests after the auth-store SRP split.
- `pdm run typecheck` passed after the implementation review fixes.
- `pdm run fe-type-check` passed after the auth-store SRP split.
- `pdm run fe-lint` passed after the auth-store SRP split.
- `pdm run pr-0255-auth-bootstrap --start-backend --start-vite` passed: the script started the
  real `pdm run dev` backend with the verifier public key, seeded a HuleEdu-linked local user in
  the real database, verified real `GET /api/v1/profile/app-continuation` responses of `200` for
  signed context and `401` for missing context, then let the SPA hit the real continuation route
  through the Vite `/api` proxy with signed gateway headers.
- `pdm run docs-validate` passed after the implementation review fixes.
- `pdm run lint` passed after the implementation review fixes.

Implementation review follow-up captured on 2026-04-11:

- `InternalIdentityContextV1` now requires `org_id`, `tenant_id`, `roles`, and `grants`; missing
  required fields and blank required string/list entries fail closed as invalid signed payloads.
- `frontend/apps/skriptoteket/src/stores/auth.ts` was split under the module size budget; HuleEdu
  shared-session, app-continuation, and CSRF network orchestration now lives in
  `frontend/apps/skriptoteket/src/stores/authBootstrap.ts`, while HTTP timeout/error parsing lives
  in `frontend/apps/skriptoteket/src/api/authHttp.ts`.
- The PR-0255 Playwright proof no longer records a mocked app-continuation response as live
  evidence.

## Rollback Plan

If the HuleEdu request-context resolver cannot be implemented safely against the named
`InternalIdentityContextV1` contract, leave `PR-0251` blocked, revert the partial remediation
changes, and record the exact missing HuleEdu gateway contract as a provider follow-up. If first
login provisioning is required but the signed context still lacks email/email-verification claims,
block provisioning rather than fabricating local users. Do not close `PR-0251` by restoring local
session-cookie continuation, `/api/v1/auth/me`, bearer storage, unsigned identity headers, or a
local browser-auth bridge.
