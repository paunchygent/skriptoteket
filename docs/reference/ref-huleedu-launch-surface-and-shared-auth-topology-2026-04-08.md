---
type: reference
id: REF-huleedu-launch-surface-and-shared-auth-topology-2026-04-08
title: "Reference: HuleEdu launch surface and shared auth topology (2026-04-08)"
status: active
owners: "agents"
created: 2026-04-08
updated: 2026-04-12
topic: "huleedu-launch-topology"
links:
  - EPIC-28
  - EPIC-35
  - REV-EPIC-28
  - REV-EPIC-35
---

## Overview

This reference records the current cross-repo launch topology decision that should govern both the
Skriptoteket auth cutover lane and the Skriptoteket SEO lane.

The main planning correction is simple:

- `hule.education` should be treated as the HuleEdu landing entrypoint
- `api.hule.education` should be treated as the HuleEdu Identity/Gateway browser auth and API edge
- `skriptoteket.hule.education` should be treated as the canonical public Skriptoteket app host

That means Skriptoteket should stop planning as if the apex is temporarily available for its own
app-host needs.

## Ownership Matrix

| Surface / concern | Primary owner | Why |
|---|---|---|
| `https://hule.education` landing page | HuleEdu | It is the product-family entrypoint, not a Skriptoteket-specific app shell |
| `https://api.hule.education` browser auth/API edge | HuleEdu | `ADR-0076` makes HuleEdu Gateway/Identity the sole browser auth authority |
| Browser session authority and CSRF contract | HuleEdu | Shared cross-app auth contract must not be owned locally by Skriptoteket |
| `/auth/login` interruption and return-to-origin handling inside Skriptoteket | Skriptoteket, aligned to HuleEdu contract | Skriptoteket keeps its redirect-preserving app UX while the auth ceremony can be HuleEdu-owned |
| `https://skriptoteket.hule.education` public app host | Skriptoteket | It is the real live product host today and the right place for app-specific crawlability work |
| `robots.txt`, `sitemap.xml`, canonical tags, and route-level metadata for Skriptoteket public pages | Skriptoteket | These are app-host concerns on the Skriptoteket surface |

## Current Reality vs Target

| Area | Current reality on 2026-04-08 | Target shape |
|---|---|---|
| `hule.education` | Placeholder host | Real HuleEdu landing page |
| `api.hule.education` | Reserved/placeholder-owned at the edge | Real HuleEdu API gateway and browser auth edge |
| `skriptoteket.hule.education` | Real live app host | Canonical public Skriptoteket app host |
| Skriptoteket browser auth authority | Still local in implementation terms | Consumes HuleEdu-owned session authority via `EPIC-28` |
| Skriptoteket launch SEO | Mixed with topology ambiguity if left unrefined | Narrowed to app-host crawlability under the frozen topology |

## Phased Critical Path

### Phase 1: Cross-repo topology and edge ownership

Decisions and rollout gates that must come first:

- HuleEdu landing page comes up on `https://hule.education`
- HuleEdu Identity/Gateway comes up on `https://api.hule.education`
- one shared browser session + CSRF contract is exposed there
- the public host topology is frozen in docs and deployment expectations

### Phase 2: Skriptoteket auth cutover

Downstream work in `EPIC-28`:

- Skriptoteket auth bootstrap moves to `https://api.hule.education`
- `/auth/login` handoff and return-to-origin behavior are preserved
- local browser auth ownership is removed
- cross-app smoke proof is recorded

### Phase 3: Skriptoteket app-host SEO hardening

Downstream work in `EPIC-35`:

- crawler files and honest status semantics on `skriptoteket.hule.education`
- route-level metadata and indexing policy for the current public pages
- sitemap submission and operator verification for the Skriptoteket app host

## Decision Tree

| Question | Decision |
|---|---|
| Should Skriptoteket take over the apex host for launch? | No |
| Should Skriptoteket wait to make its public URLs crawlable until the full HuleEdu platform is perfect? | No |
| Should Skriptoteket freeze its own app-host assumptions around the intended HuleEdu topology first? | Yes |
| Should `EPIC-28` own the cross-repo auth/topology dependency freeze and let `EPIC-35` consume it? | Yes |

## Planning Consequences

- `EPIC-28` needs one explicit planning gate for the cross-repo topology and shared-auth dependency
  freeze before the local cutover stories become implementation-critical.
- `EPIC-35` should narrow further and stop implying that it owns apex-host decisions.
- The most important near-term decisions are not sitemap polish or metadata copy. They are edge
  ownership, auth authority, and launch sequencing.

## Local Proof Analogue

Local proof should mirror ownership without copying production hosts:

- Skriptoteket Vite remains the app surface on `http://localhost:5173`.
- HuleEdu Gateway remains the browser auth/API authority on `http://localhost:8080`.
- HuleEdu login/lifecycle UI uses `http://localhost:5174` when co-running with Skriptoteket.
- The separate 127 proof keeps all browser-facing origins on 127:
  `http://127.0.0.1:5173`, `http://127.0.0.1:5174`, and
  `http://127.0.0.1:8080`.
- Local/non-production Gateway allowlists may include exact dev origins such as
  `http://localhost:5173` and `http://127.0.0.1:5173`.
- Protected Skriptoteket APIs remain `/api/...` in the browser; for local proof
  host-run Vite points `VITE_DEV_PROXY_TARGET` at the browser-visible Gateway
  base (`http://localhost:8080` or `http://127.0.0.1:8080`), while the normal
  Docker frontend service uses the container-internal target
  `http://huleedu_api_gateway_service:8080` on `hule-network`. Gateway forwards
  to `API_GATEWAY_SKRIPTOTEKET_BACKEND_URL=http://skriptoteket-web:8000`.
- Public Skriptoteket APIs remain public in local Docker proof:
  `VITE_DEV_BACKEND_PROXY_TARGET=http://skriptoteket_web:8000` keeps
  `/api/v1/public/...` and backend static assets off the HuleEdu Gateway.
- Public `https://api.hule.education` must continue rejecting loopback return origins.

This local lane is owned by HuleEdu `TASK-0325` and consumed by Skriptoteket `PR-0254`;
the auditable local proof is `pdm run pr-0254-auth-cutover`.
