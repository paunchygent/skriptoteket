---
type: story
id: ST-SKRIPT-09-07
title: Public-edge app/runtime hardening
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
status: active
readiness_review:
  record: inline
  status: not_started
closeout_review:
  record: inline
  status: not_started
epic: EPIC-SKRIPT-09
acceptance_criteria:
- Given Skriptoteket starts with `ENVIRONMENT=production`, when an unauthenticated
  caller requests `/docs`, `/redoc`, or `/openapi.json`, then the routes fail closed
  and no interactive API surface is exposed.
- Given Skriptoteket starts with `ENVIRONMENT=production`, when an unauthenticated
  caller requests `/healthz`, then the response is limited to a public-safe status
  payload and omits service version, environment, and dependency details.
- Given Skriptoteket starts with identity metrics disabled, when `/metrics` is requested,
  then the response omits `skriptoteket_active_sessions` and `skriptoteket_users_by_role`
  while keeping operational metrics intact.
- Given login-event audit logging runs behind the public edge, when an untrusted direct
  peer sends `X-Forwarded-For` or `X-Real-IP`, then the stored client IP is derived
  from the direct peer and not the caller-supplied forwarding header.
- Given Docker-based local development proxies requests with the backend alias host,
  when a bootstrap superuser logs in through the frontend dev server, then the request
  succeeds and the non-production host allowance does not widen production `ALLOWED_HOSTS`.
retired_ids:
- ST-09-07
---

## Context


The March 29, 2026 UTC authorized red-team pass confirmed that Skriptoteket's
repo-side public-edge hardening was only partially landed in production shape.
The already-landed app patch covered docs/OpenAPI disablement, trusted-host
middleware, and browser hardening headers, but the follow-up still needed to
close three app/runtime gaps:

- public `/healthz` exposed production metadata and dependency state
- public `/metrics` leaked identity/session gauges
- login-event IP capture trusted caller-controlled forwarding headers

This story tracks the application/runtime slice that is now implemented locally
and verified, but still needs the normal merge/deploy close-out before it can
be called fully shipped.

## Epic Contract Slice

No separate epic contract slice is stated in the source.

## ADR Coverage

No separate adr coverage is stated in the source.

## Contract Inputs

No separate contract inputs is stated in the source.

## Live Verification Plan

No separate live verification plan is stated in the source.

## Non-Goals

No separate non-goals is stated in the source.

## Notes


- Keep the production trust boundary fail-closed by default:
  - production `ALLOWED_HOSTS` must stay explicit
  - production `TRUSTED_PROXY_CIDRS` must stay empty until ops sets the exact
    nginx-proxy bridge IP/CIDR
- Preserve the Docker-based local dev path explicitly via a non-production-only
  host allowance for `skriptoteket_web`
- Do not expand this story into nginx/DNS/reserved-host work; that belongs in
  the separate Hemma edge follow-up story

## Decision And Assumption Ledger

| source | semantic | carried_forward | Source material is retained in the sections above. | source |

## Plan Document Review

No review evidence is recorded in this migration candidate; the frontmatter gate remains authoritative.

## Story Closeout Review

No review evidence is recorded in this migration candidate; the frontmatter gate remains authoritative.
