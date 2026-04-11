---
type: adr
id: ADR-0082
title: "App-local bootstrap continuation on HuleEdu-owned session"
status: accepted
owners: "agents"
deciders: ["user-lead"]
created: 2026-04-11
updated: 2026-04-11
links:
  [
    "ADR-0076",
    "EPIC-28",
    "ST-28-01",
    "PR-0251",
    "PR-0253",
    "REV-PR-0251",
  ]
---

## Context

`ADR-0076` moves browser auth authority to HuleEdu:

- HuleEdu Identity owns the canonical browser session.
- HuleEdu Gateway is the browser auth/API edge.
- Skriptoteket consumes `GET https://api.hule.education/v1/auth/session` and
  `GET https://api.hule.education/v1/auth/csrf`.
- Skriptoteket must not keep a local browser auth bridge or `/api/v1/auth/me`
  compatibility path.

`PR-0251` has already cut the first frontend slice over to the shared HuleEdu
session and CSRF contract. The remaining issue is that the old local bootstrap
also carried Skriptoteket-owned app state:

- `ai_policy`
- `profile.allow_remote_fallback`
- `profile.inline_completion_provider`

Those fields are not browser-auth authority. They are Skriptoteket app policy,
profile preference, and AI consent state. Treating them as HuleEdu-owned session
fields would blur product ownership. Reintroducing local `/api/v1/auth/me` or
mirroring local session rows would blur auth ownership.

The decision needed for `PR-0251` is therefore a narrow continuation boundary:
after HuleEdu proves the browser subject, how does Skriptoteket hydrate
app-local state without becoming a second browser auth authority?

## Decision

### 1. HuleEdu session remains the only browser auth bootstrap

The canonical browser auth bootstrap remains:

```text
GET https://api.hule.education/v1/auth/session
```

Skriptoteket must not restore `/api/v1/auth/me` as a browser bootstrap source,
fallback path, or compatibility bridge.

The shared HuleEdu session response may carry identity, display profile,
session transport, grants, roles, feature flags, and other HuleEdu-owned
session state. It does not need to own Skriptoteket-specific AI consent or app
preference fields.

### 2. Skriptoteket owns a separate app-local bootstrap continuation

Skriptoteket may expose a separate authenticated app bootstrap continuation
endpoint for Skriptoteket-owned state.

That endpoint must answer only app-local questions, such as:

- what AI policy applies in this Skriptoteket runtime
- what AI preferences this local Skriptoteket profile has stored
- which app-local defaults or capability flags are needed after auth bootstrap

It must not answer "who is logged in?" as a browser auth authority. HuleEdu
answers that through the shared session contract.

### 3. App-local continuation is request-context derived

The continuation endpoint must derive its user from the HuleEdu-owned browser
session authority, not from a Skriptoteket browser session row.

The intended backend shape is:

1. HuleEdu Gateway validates the browser session and CSRF contract.
2. Gateway forwards a signed internal identity context to Skriptoteket.
3. Skriptoteket verifies that context behind protocol-first DI.
4. Skriptoteket resolves or idempotently provisions the local user/profile
   projection.
5. Skriptoteket returns app-local bootstrap state for that resolved local user.

The application layer should continue depending on protocols and local domain
models. The web layer owns request extraction and context verification.

### 4. AI policy is runtime policy, not identity policy

`ai_policy` is derived from Skriptoteket runtime configuration and provider
availability.

It should move out of local browser-auth route ownership and into a small
app/AI policy service or response builder that can be reused by app bootstrap,
profile responses, and tests.

### 5. AI preferences live on Skriptoteket `UserProfile`

The following remain Skriptoteket-local profile preferences:

- `allow_remote_fallback`
- `inline_completion_provider`

They must be read from and persisted to `UserProfile`, not copied into a local
browser session mirror for the HuleEdu cutover.

Profile/AI preference updates may continue through a Skriptoteket app endpoint,
but the response should refresh app-local state rather than mutate or replace
the HuleEdu session document.

### 6. Editor AI routes consume app-local AI preferences

Editor AI routes that need remote fallback or inline completion provider
preferences should receive those values through a request-scoped app preference
dependency.

They should not depend on `Session.allow_remote_fallback` or
`Session.inline_completion_provider` once HuleEdu owns browser session
authority.

### 7. Missing app bootstrap fails closed for remote AI

If the frontend has a HuleEdu authenticated session but has not yet loaded
Skriptoteket app-local AI policy, remote-AI affordances should fail closed:

- remote providers are not assumed enabled
- external completions are not assumed available
- user consent is not assumed granted

This preserves the remote-provider consent guardrail while the app continuation
loads or reports an error.

## Rejected Options

### Restore `/api/v1/auth/me` with fewer fields

Rejected. Even a narrowed `/auth/me` route would keep the browser on a local
auth-shaped bootstrap path and would violate the hard-break direction in
`ADR-0076`.

### Add Skriptoteket local session rows as a mirror

Rejected. Creating or syncing local session rows only to carry AI preferences
would recreate a hidden browser auth bridge. AI preferences belong to profile
state, not session authority.

### Put Skriptoteket AI consent into the HuleEdu session document

Rejected as the first implementation shape. HuleEdu owns identity/session
authority; Skriptoteket owns app-specific AI consent and provider policy. If a
future shared app-capability envelope is needed, it should be additive and
explicit, not required for this cutover.

### Browser bearer storage or direct Identity calls

Rejected by `ADR-0076`. This ADR does not reopen that decision.

## Consequences

- `PR-0251` should implement a two-phase frontend bootstrap:
  HuleEdu session first, Skriptoteket app continuation second.
- `PR-0251` should not close until the app-local AI/profile continuation is
  implemented or explicitly split behind this ADR.
- `PR-0253` can delete local browser auth/session ownership with less ambiguity,
  because app-local AI/profile state has its own non-auth boundary.
- Backend work will need a request-context resolver for HuleEdu-proven users
  before local `require_session_api` dependencies can disappear from editor AI
  routes.
- Tests should assert that authenticated app bootstrap does not call
  `/api/v1/auth/me`, does not use bearer storage, and treats missing app AI
  bootstrap as remote-AI disabled until loaded.
