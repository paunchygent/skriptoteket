---
type: story
id: ST-09-07
title: "Public-edge app/runtime hardening"
status: in_progress
owners: "agents"
created: 2026-03-30
updated: 2026-03-30
epic: "EPIC-09"
dependencies: ["ADR-0021", "ADR-0019", "ADR-0049", "ADR-0053", "ST-07-07"]
acceptance_criteria:
  - "Given Skriptoteket starts with `ENVIRONMENT=production`, when an unauthenticated caller requests `/docs`, `/redoc`, or `/openapi.json`, then the routes fail closed and no interactive API surface is exposed."
  - "Given Skriptoteket starts with `ENVIRONMENT=production`, when an unauthenticated caller requests `/healthz`, then the response is limited to a public-safe status payload and omits service version, environment, and dependency details."
  - "Given Skriptoteket starts with identity metrics disabled, when `/metrics` is requested, then the response omits `skriptoteket_active_sessions` and `skriptoteket_users_by_role` while keeping operational metrics intact."
  - "Given login-event audit logging runs behind the public edge, when an untrusted direct peer sends `X-Forwarded-For` or `X-Real-IP`, then the stored client IP is derived from the direct peer and not the caller-supplied forwarding header."
  - "Given Docker-based local development proxies requests with the backend alias host, when a bootstrap superuser logs in through the frontend dev server, then the request succeeds and the non-production host allowance does not widen production `ALLOWED_HOSTS`."
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

## Notes

- Keep the production trust boundary fail-closed by default:
  - production `ALLOWED_HOSTS` must stay explicit
  - production `TRUSTED_PROXY_CIDRS` must stay empty until ops sets the exact
    nginx-proxy bridge IP/CIDR
- Preserve the Docker-based local dev path explicitly via a non-production-only
  host allowance for `skriptoteket_web`
- Do not expand this story into nginx/DNS/reserved-host work; that belongs in
  the separate Hemma edge follow-up story
