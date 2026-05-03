---
type: reference
id: REF-launch-seo-and-search-indexing-readiness-2026-04-08
title: "Reference: Launch SEO and search indexing readiness assessment (2026-04-08)"
status: active
owners: "agents"
created: 2026-04-08
updated: 2026-05-02
topic: "launch-seo-and-search-indexing"
links:
  - EPIC-35
  - REV-EPIC-35
---

## Overview

This reference captures the information gained during the April 8, 2026 launch-readiness assessment
for Skriptoteket SEO and search indexing.

The goal was not to guess about “SEO best practices” in the abstract. The goal was to answer three
practical launch questions against the current live system and repo state:

1. what the public edge actually serves today
2. what technical blockers currently prevent clean indexing
3. what path forward is proportionate for launch rather than idealized future marketing work

This document is the evidence and analysis base for
[EPIC-35](../backlog/epics/epic-35-launch-seo-and-search-indexing-readiness.md) and
[REV-EPIC-35](../backlog/reviews/review-epic-35-launch-seo-and-search-indexing-readiness.md).

The broader cross-repo topology is now governed separately by
[REF-huleedu-launch-surface-and-shared-auth-topology-2026-04-08](./ref-huleedu-launch-surface-and-shared-auth-topology-2026-04-08.md).
This reference should now be read as the downstream Skriptoteket SEO assessment that consumes that
topology.

Planning note after the initial assessment:

- the intended platform shape is now explicitly:
  - `hule.education` = HuleEdu landing entrypoint
  - `api.hule.education` = HuleEdu Identity/Gateway browser auth and API edge
  - `skriptoteket.hule.education` = canonical public Skriptoteket app host
- this means the apex should no longer be treated as “available Skriptoteket canonical host”
  inside the launch SEO lane

## Information Gained

### Historical Live Edge Findings on 2026-04-08

| Surface | Observation | Why it matters |
|---|---|---|
| `skriptoteket.hule.education` DNS | Resolves to `83.252.61.217` | The subdomain is publicly routable right now |
| `hule.education` DNS | Resolves to `83.252.61.217` | The apex is also public, so canonical-host ambiguity is real rather than hypothetical |
| `www.hule.education` DNS | Did not resolve during the check | `www` is not a launch-ready alias today |
| `https://skriptoteket.hule.education` TLS | Valid Let's Encrypt `R12` certificate, `CN=skriptoteket.hule.education`, valid from March 7, 2026 to June 5, 2026 | The live app host already has valid HTTPS |
| `https://hule.education` TLS | Valid Let's Encrypt certificate covering `hule.education`, `api.hule.education`, and `ws.hule.education`, valid from March 29, 2026 to June 27, 2026 | The apex and shared HuleEdu hosts are also active and could compete if not handled deliberately |
| `http://skriptoteket.hule.education/` | `301` redirect to `https://skriptoteket.hule.education/` | Basic HTTP-to-HTTPS enforcement is already present |
| `https://skriptoteket.hule.education/` | `200 OK` and serves the SPA HTML shell | The site is publicly reachable, but the shell alone is not enough for crawler clarity |
| `https://skriptoteket.hule.education/robots.txt` | Returned the SPA HTML shell with `200 OK` | This is a launch blocker for crawl semantics |
| `https://skriptoteket.hule.education/sitemap.xml` | Returned the SPA HTML shell with `200 OK` | This is a launch blocker for crawler discovery |
| `https://skriptoteket.hule.education/this-route-should-not-exist` | Returned the SPA HTML shell with `200 OK` | This is soft-404 behavior at the backend edge |
| `https://skriptoteket.hule.education/public/apps/classroom.group-seating-studio` | Reachable and client-renders the public app host | The public curated-app entry exists and is a real candidate for indexing |
| `https://hule.education/` | Returned a HuleEdu reserved-host response with `200 OK` | The apex was live but not the Skriptoteket product host |

As of the 2026-05-02 Hemma readiness proof, the old reserved-host placeholder
expectation is stale: HuleEdu runtime services own `hule.education` and
`api.hule.education`, while `skriptoteket.hule.education` remains the
Skriptoteket app host.

### Repo findings on 2026-04-08

| Area | Observation | Evidence |
|---|---|---|
| Production host wiring | Production is currently anchored to `skriptoteket.hule.education` through `ALLOWED_HOSTS`, `EMAIL_VERIFICATION_BASE_URL`, `SIR_CONVERT_A_LOT_V2_CALLBACK_BASE_URL`, `VIRTUAL_HOST`, and `LETSENCRYPT_HOST` | [compose.prod.yaml](../../compose.prod.yaml) |
| HTML shell metadata | The SPA shell has only a generic `<title>Skriptoteket</title>` plus favicon and font links; there is no meta description, canonical tag, robots tag, OG metadata, or structured data | [frontend/apps/skriptoteket/index.html](../../frontend/apps/skriptoteket/index.html) |
| Public landing product surface | The signed-out home page already positions `Klassrumskartan` as the primary public CTA and links to `/public/apps/classroom.group-seating-studio` | [HomeView.vue](../../frontend/apps/skriptoteket/src/views/HomeView.vue) |
| Public route inventory | The current public, index-candidate routes are effectively `/` and `/public/apps/:appId`; the SPA also has explicit client-side recovery routes for malformed public URLs and generic unmatched URLs | [routes.ts](../../frontend/apps/skriptoteket/src/router/routes.ts) |
| Backend fallback behavior | The FastAPI SPA fallback excludes API, static, and observability paths, but it does not exclude `/robots.txt`, `/sitemap.xml`, or arbitrary unmatched public paths; it returns the SPA HTML file for everything else | [spa_fallback.py](../../src/skriptoteket/web/routes/spa_fallback.py) |
| Client-side not-found handling | The SPA now renders a human-friendly recovery view for unmatched routes, but that is a client UX improvement, not a crawler-safe HTTP status contract | [RouteRecoveryView.vue](../../frontend/apps/skriptoteket/src/views/RouteRecoveryView.vue) |

### Live edge re-check on 2026-04-15

The retained `REV-EPIC-35` review re-checked the same public edge before approval. `/`,
`/robots.txt`, `/sitemap.xml`, and an arbitrary missing path still returned the same HTML shell
with `200 OK` and `content-type: text/html; charset=utf-8`.

That re-check keeps the April 8 findings current: the package must still repair crawler files,
unmatched-route status semantics, and launch-visible initial HTML metadata before the epic can be
approved for implementation.

### Official crawler guidance checked on 2026-04-15

The implementation stories should keep their proof requirements aligned with current official
guidance rather than relying on memory:

- Google documents that `2xx` content may be considered for indexing and that soft-404-like
  content can still be reported when a successful response body looks like an error page.
- Google documents that `4xx` responses are treated as missing content for Search indexing.
- Google Search Console ownership verification is account-bound and supports methods such as DNS,
  HTML file upload, and homepage meta tags depending on the property shape.
- Google's robots and sitemap guidance require crawler files to be real fetchable resources, not
  arbitrary SPA HTML fallback content.
- Bing Webmaster Tools verification and sitemap/URL-inspection work is likewise account-bound and
  must be performed by an operator with access to the relevant site/property.

Reference links used for the April 15 update:

- Google Search Central: `https://developers.google.com/search/docs/crawling-indexing/http-network-errors`
- Google Search Central: `https://developers.google.com/search/docs/crawling-indexing/javascript/javascript-seo-basics`
- Google Search Central: `https://developers.google.com/search/docs/crawling-indexing/robots/intro`
- Google Search Central: `https://developers.google.com/search/docs/crawling-indexing/sitemaps/build-sitemap`
- Google Search Console Help: `https://support.google.com/webmasters/answer/9008080`
- Bing Webmaster Blog: `https://blogs.bing.com/webmaster/August-2024/Bing-Webmaster-Tools-or-Google-Search-Console-A-Comparison`

## Analysis

### Recommended canonical host topology for launch

The current recommended launch topology is:

- `https://hule.education` = HuleEdu landing page
- `https://api.hule.education` = HuleEdu browser auth/API gateway
- `https://skriptoteket.hule.education` = canonical public Skriptoteket app host

Rationale:

- `skriptoteket.hule.education` already serves the real Skriptoteket product
- production compose and environment defaults already point Skriptoteket there
- `ADR-0076` and `EPIC-28` already set the intended future auth shape to
  HuleEdu-owned Gateway/Identity at `api.hule.education`
- the apex `https://hule.education` is better modeled as the HuleEdu entrypoint
  than as a temporary Skriptoteket host

The consequence for `EPIC-35` is:

- do not harden Skriptoteket SEO around the apex as if it were a vacant app host
- do keep Skriptoteket search-facing work clean and canonical on
  `https://skriptoteket.hule.education`
- do align landing-page and auth-entry assumptions with the upstream HuleEdu
  landing and gateway rollout

### Top launch blockers

| Severity | Blocker | Why it blocks a clean launch |
|---|---|---|
| P0 | `robots.txt` returns SPA HTML with `200 OK` | Crawlers are not receiving a real crawl policy file |
| P0 | `sitemap.xml` returns SPA HTML with `200 OK` | Search engines are not receiving a real sitemap |
| P0 | Unknown URLs return SPA HTML with `200 OK` | The site currently emits soft-404-like behavior at the edge |
| P1 | No route-level meta description, canonical tags, or share metadata on current public pages | Even if crawled, the public pages are weakly described and weakly canonicalized |
| P1 | Canonical host topology is still implicit rather than frozen in backlog and ops docs | Search-console ownership, redirects, and metadata can drift if the HuleEdu apex, gateway, and Skriptoteket host are not treated as one intentional system |
| P1 | No verified search-operator workflow was available during the assessment | The technical lane can ship without proving that search engines were actually told about it |
| P1 | HuleEdu landing/gateway rollout is still upstream work | If the apex and shared API edge arrive late, launch-day redirects and auth flows can churn unless the SEO lane stays explicitly compatible with them |
| P2 | Public crawlable surface is still intentionally small | Indexing can be healthy, but discoverability will still be narrow until more public content exists |

### What is not currently blocking launch

| Item | Assessment | Why |
|---|---|---|
| HTTPS on the live app host | Not a blocker | `skriptoteket.hule.education` already has a valid certificate and HTTP-to-HTTPS redirect |
| Public landing CTA hierarchy | Not a blocker | The public landing already has a clear public path into Klassrumskartan |
| Full-site SSR | Not a launch blocker by default | The minimum viable launch lane can be honest and indexable without committing to a larger rendering migration immediately |

### Recommended execution order

| Order | Backlog item | Reason |
|---|---|---|
| 1 | `ST-35-01` | Freeze the canonical host topology before building SEO machinery around the wrong URL or the wrong product boundary |
| 2 | `ST-35-02` | Fix crawler truth at the edge before polishing snippets |
| 3 | `ST-35-03` | Add route-level metadata and indexing policy on the now-honest public surface |
| 4 | `ST-35-04` | Verify, submit, and document the operator workflow so launch status is measurable |

Parallel upstream lane:

- `EPIC-28` should advance the HuleEdu-owned session contract and auth-entry
  handoff so Skriptoteket does not overfit to app-local auth assumptions
- HuleEdu owns the apex landing and `api.hule.education` gateway/identity
  surfaces; Skriptoteket must continue treating them as non-Skriptoteket
  canonical hosts

## Decision Trees

### 1. Canonical host decision

| Question | If yes | If no | Recommended current branch |
|---|---|---|---|
| Is the apex `https://hule.education` becoming the HuleEdu landing page before launch? | Keep the apex HuleEdu-owned, link outward to `https://skriptoteket.hule.education`, and avoid treating the apex as a Skriptoteket canonical host | Keep the apex HuleEdu-owned and non-competing until the HuleEdu landing page is ready | Yes |
| Do we need `www.hule.education` for launch? | Add DNS, TLS coverage, and a permanent redirect to the canonical host | Keep `www` out of scope and avoid introducing another public variant | No |

### 2. Crawlability decision

| Route type | HTTP rule | Search rule | Recommended current branch |
|---|---|---|---|
| Current public entry pages | `200 OK` with route-specific metadata | Include in sitemap and allow indexing | Yes |
| Authenticated teacher surfaces | Product-driven responses only | Exclude from sitemap and do not expose as public search targets | Yes |
| Malformed or non-existent paths | `404` or `410` | Never allow a SPA-shell `200` fallback to act as the search contract | Yes |

### 3. Rendering-depth decision

| Need | Path | Recommended current branch |
|---|---|---|
| Make SEO alive for launch | Fix crawler files, status semantics, and route-level head metadata | This is the required launch lane |
| Push toward richer organic discovery later | Add public-page prerender or SSR and structured data after the crawl contract is stable | Follow-on lane |

## Known Unknowns

- This assessment could not verify existing Google Search Console or Bing Webmaster ownership because
  that requires account access not available in the repo or public edge checks.
- Public search-engine queries alone cannot prove whether a URL is fully deindexed, just undiscovered,
  or newly submitted. The operator workflow in `ST-35-04` is still needed.
- This assessment still cannot prove delivery timing for the HuleEdu landing
  page, identity service, or API gateway. Those remain upstream execution risks.
- If the HuleEdu platform direction changes again, the host-topology
  recommendation here should be revised explicitly rather than diluted in
  implementation.
