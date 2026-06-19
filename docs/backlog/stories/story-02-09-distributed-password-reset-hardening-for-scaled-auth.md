---
type: story
id: ST-02-09
title: "Distributed password-reset hardening for scaled auth"
status: canceled
owners: "agents"
created: 2026-03-30
updated: 2026-06-18
epic: "EPIC-02"
acceptance_criteria:
  - "Given Skriptoteket runs with multiple web processes or instances, when repeated `forgot-password` requests for the same normalized email hit different instances inside the cooldown window, then the public response remains the same generic `202 Accepted` contract and only the shared cooldown owner decides whether a new reset token may be issued."
  - "Given concurrent eligible reset requests race for the same local account, when token issuance reaches persistence, then the system enforces at the database level that at most one active password-reset token exists for a user at a time and any superseded token becomes unusable."
  - "Given operators plan horizontal scaling, multi-worker uvicorn, or load-balanced production rollout for auth traffic, when rollout readiness is reviewed, then this hardening story is complete and documented as a prerequisite rather than relying on a process-local in-memory throttle."
dependencies: ["ST-02-07"]
ui_impact: "No intended UX change; preserves the existing anonymous forgot-password and reset-password behavior while making it safe across multiple auth-serving instances."
data_impact: "Adds shared coordination for forgot-password cooldowns and schema-level enforcement of the one-active-reset-token invariant."
---

## Context

`ST-02-07` intentionally shipped password reset for the current single-instance deployment shape, but its
anonymous request cooldown is still an app-scoped in-memory service. That is acceptable today and keeps
the slice small, yet it is not a safe long-term contract for horizontal scaling, multi-worker uvicorn, or
load-balanced production auth traffic.

This follow-up hardens the password-reset flow so the public anonymous contract remains truthful even when
multiple auth-serving processes race or receive traffic unevenly.

## Implementation notes

### Shared cooldown ownership

- Replace the process-local forgot-password cooldown with a shared coordination store.
- Preferred implementation direction:
  - use PostgreSQL-backed coordination if no broader Redis dependency is being introduced for auth/runtime
  - use Redis only if the repo already has an approved cross-instance coordination need that justifies it
- Keep the current public API contract unchanged:
  - `POST /api/v1/auth/forgot-password` still returns the same generic `202 Accepted` body for eligible,
    throttled, unknown, inactive, unverified, and federated identities

### Database-enforced active-token invariant

- Move the one-active-reset-token rule from handler-only behavior to an explicit database invariant.
- The persistence layer must prevent two active reset tokens from existing for the same user even under
  concurrent requests from different instances.
- Keep tokens hashed at rest and preserve the current token invalidation semantics from `ST-02-07`.

### Rollout guard

- Treat this story as a prerequisite for:
  - horizontal scaling of the `web` service
  - multi-worker uvicorn or equivalent multi-process app serving for auth traffic
  - any load-balanced production rollout where forgot-password traffic can land on different instances

## Verification

- Repository/service tests proving the shared cooldown works across distinct app instances or independently
  constructed handler/service objects.
- Concurrency/integration tests proving the one-active-token invariant still holds under racing reset
  requests.
- Migration/schema assertions for the database invariant.
- Docs/runbook verification that any future scaling plan references this prerequisite explicitly.

## Supersession Note (2026-06-18)

Canceled during `PR-0359` as browser-auth lifecycle work superseded by
`ST-28-08` / `PR-0257`. The product no longer treats Skriptoteket-local browser
forgot/reset flows as the forward lane. Existing backend token/cooldown code
remains in the repo and must be retired only through a separate owned backend
or ops decision.
