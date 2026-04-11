---
type: pr
id: PR-0250
title: "ST-28-05 HuleEdu provider conformance ingest and cutover readiness"
status: done
owners: "agents"
created: 2026-04-10
updated: 2026-04-11
stories:
  - "ST-28-05"
tags: ["auth", "huleedu", "docs", "cutover"]
acceptance_criteria:
  - "Given HuleEdu has accepted ADR-0039 and live-proven the shared browser-session authority, when this PR completes, then EPIC-28 records the provider dependency as ready for Skriptoteket implementation rather than as an unresolved upstream blocker."
  - "Given ownership must stay split by repository, when this PR completes, then Skriptoteket owns only consumer migration work while HuleEdu remains responsible for provider conformance, additive session fields, and the handoff pack."
  - "Given any contract gaps discovered by Skriptoteket must route cleanly, when this PR completes, then the backlog names the HuleEdu follow-up target and the Skriptoteket implementation PRs that consume it."
---

## Problem

`EPIC-28` was approved while the HuleEdu shared browser-session authority was still an upstream
runtime blocker. HuleEdu has now accepted ADR-0039 and smoke-proven the provider path, so the
Skriptoteket backlog needs one small readiness intake before implementation starts.

Without this intake, the implementation PRs risk mixing HuleEdu provider obligations with
Skriptoteket consumer work.

## Goal

Record the current HuleEdu provider state and unblocking assumptions in Skriptoteket's local
backlog.

The expected HuleEdu handoff anchors are:

- `docs/decisions/0039-huleedu-owned-browser-session-authority-and-saas-bootstrap-contract.md`
- `docs/backlog/programmes/programme-shared-auth-consumer-cutover-hub.md`
- `docs/backlog/stories/story-01-03-shared-browser-session-provider-conformance-and-consumer-handoff.md`
- `docs/backlog/tasks/task-0308-publish-shared-auth-consumer-conformance-pack-and-skriptoteket-handoff.md`

## Rereview Verdict (2026-04-11)

**Verdict: approved for Skriptoteket consumer implementation.**

The HuleEdu provider gate is now closed for `PR-0251`. After the HuleEdu remediation and
production redeploy to `432b25ed`, Skriptoteket has no remaining provider-side blocker for
starting the consumer cutover against the shared browser-session contract.

The rereview compared ADR-0039, the shared-auth programme hub, `ST-01-03`, `TASK-0308`, and the
retained conformance reference against `EPIC-28` / `ADR-0076`. The actual provider contract now
matches the required ownership and transport direction:

- API Gateway exposes the browser-facing `/v1/auth/login`, `/v1/auth/logout`,
  `/v1/auth/refresh`, `/v1/auth/session`, `/v1/auth/csrf`, and
  `/v1/auth/websocket-ticket` surfaces.
- Identity Service owns the canonical browser session document and issues
  refresh-backed `huleedu_session` cookies, readable `huleedu_csrf` cookies, and
  `X-CSRF-Token` double-submit validation.
- Production cookie policy defaults to `.hule.education`, `SameSite=Lax`, and
  secure cookies outside local/test runtime.
- The implemented `GET /v1/auth/session` payload includes `authenticated`,
  `user`, `profile`, `context`, `policy`, `session`, and `app_flags`.
- Websocket admission is session-derived through `GET /v1/auth/websocket-ticket`,
  with `ws.hule.education` as the public websocket host.
- Gateway-to-service identity propagation is documented through signed
  `InternalIdentityContextV1` headers rather than raw browser cookies.
- `TASK-0308` is `done` and publishes the retained
  `REF-shared-browser-session-consumer-conformance-v1` handoff pack.
- Production API Gateway credentialed CORS and WebSocket origin admission now include
  `https://skriptoteket.hule.education` alongside `https://hule.education`.
- Public Hemma proof is green: the auth readiness probe passed with `huleedu_session` /
  `huleedu_csrf`, and the WebSocket readiness probe accepted
  `https://skriptoteket.hule.education` with HTTP `101 Switching Protocols`.

That satisfies the non-negotiable ownership and transport direction in
`ADR-0076` / `EPIC-28`: Skriptoteket should not create a bearer-token bridge,
should not call HuleEdu Identity directly from the browser, and should consume
the Gateway-owned browser session contract.

## Closed Provider Gaps

1. **Production browser-origin admission is proven.**
   HuleEdu `TASK-0308` now records public proof for `https://skriptoteket.hule.education` on both
   `https://api.hule.education` credentialed browser traffic and `wss://ws.hule.education/ws`
   WebSocket admission.

2. **Consumer conformance handoff is published.**
   HuleEdu `TASK-0308` is `done`, `ST-01-03` is the provider story anchor, and the shared-auth
   programme hub records the green public proof. Skriptoteket should consume the retained
   conformance reference instead of inventing a local contract.

3. **Shared session policy is no longer too thin for first implementation.**
   The provider session policy now carries `roles`, `grants`, and `feature_flags`, and the
   conformance pack explicitly forbids consumers from dropping grants or feature flags. Skriptoteket
   still owns local role/profile/AI-policy interpretation, but that is a `PR-0251` consumer mapping
   concern rather than a provider readiness blocker.

## Consumer Guardrails For PR-0251

`PR-0251` may now start, with these constraints:

- Consume `REF-shared-browser-session-consumer-conformance-v1` as the provider contract.
- Preserve Skriptoteket-local authorization, profile preferences, and AI policy semantics without
  reinstating local browser auth authority.
- Treat any missing app-specific bootstrap fields as either Skriptoteket-owned app bootstrap data or
  a new HuleEdu provider follow-up; do not smuggle them through bearer storage, local auth mirrors,
  or direct Identity calls.
- Keep the browser on the hard `huledu_session` / `huledu_csrf` / `X-CSRF-Token` contract.

## Non-goals

- Implementing frontend or backend auth cutover code.
- Reopening ADR-0076 unless the HuleEdu handoff exposes a real contract mismatch.
- Moving HuleEdu-owned provider conformance work into this repository.

## Implementation Plan

1. Update `EPIC-28` dependency language from unresolved upstream blocker to provider-ready,
   consumer-implementation-ready state.
2. Update `ST-28-05` with the HuleEdu provider handoff anchors and explicit ownership split.
3. Keep `ST-28-01` through `ST-28-04` as the implementation story spine.
4. Ensure `docs/index.md` links this readiness PR and the follow-on implementation PRs.

## Test Plan

- Run `pdm run docs-validate`.

## Rollback Plan

Revert the docs changes and return `EPIC-28` to the previous upstream-blocked wording if the
HuleEdu handoff is withdrawn or fails the provider conformance check.
