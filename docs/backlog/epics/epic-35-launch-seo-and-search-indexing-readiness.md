---
type: epic
id: EPIC-35
title: "Launch SEO and search indexing readiness"
status: proposed
owners: "agents"
created: 2026-04-08
updated: 2026-04-08
outcome: "Skriptoteket can launch on one explicit canonical public host with valid crawler-facing files, honest HTTP status semantics, route-level metadata for the current public entry pages, and an operator-ready search verification workflow so search engines can discover and index the intended public surfaces without domain ambiguity or soft-404 drift."
dependencies:
  - "ADR-0027"
  - "ADR-0028"
  - "EPIC-32"
  - "ST-32-07"
  - "ST-32-08"
  - "ST-32-09"
  - "REF-launch-seo-and-search-indexing-readiness-2026-04-08"
---

## Scope

- Freeze the canonical public Skriptoteket host for launch instead of leaving
  `skriptoteket.hule.education`, `hule.education`, and potential `www`
  variants in ambiguous competition.
- Convert crawler-critical paths such as `/robots.txt` and `/sitemap.xml` into
  real edge-owned responses with correct content type, body, and status code.
- Repair public-route and unmatched-route HTTP semantics so search engines do
  not receive the SPA shell as a misleading `200 OK` response for malformed or
  non-existent URLs.
- Add minimum viable indexing metadata for the current public entry surfaces:
  `/` and `/public/apps/classroom.group-seating-studio`.
- Define an explicit indexing policy for public, authenticated, and unmatched
  route families rather than relying on one generic SPA shell.
- Document and execute the search-operator lane: Search Console / Bing
  verification, sitemap submission, launch-day checks, and post-deploy
  revalidation.

## Out of Scope

- A broad marketing-site rewrite or a copywriting campaign beyond the minimum
  metadata and launch-surface discoverability required for indexing.
- Opening authenticated or private teacher surfaces to public search indexing.
- SEO expansion for every route in the SPA when the current launch-visible
  surface is still intentionally narrow.
- Full SSR or prerender adoption across the whole SPA by default; that remains
  a follow-up choice after the minimum crawlability lane is honest and stable.
- Search ranking promises. This epic only aims to make the public surface
  crawlable, coherent, and operator-verifiable.

## Risks

- If the canonical host is not decided early, link equity and search-console
  ownership can split across the apex and subdomain surfaces.
- If crawler-facing files still fall through to the SPA shell, search engines
  may delay indexing or classify key URLs as low quality or soft 404s.
- If unmatched URLs stay `200 OK` at the backend edge, route recovery in the
  client will mask indexability defects instead of fixing them.
- If route-level metadata stays generic, public pages may index with weak or
  misleading snippets even after crawlability is repaired.
- If search verification is treated as “someone will do it later,” launch-day
  status will remain ambiguous even after the technical fixes ship.

## Story Stack

- [ST-35-01: Canonical public host and edge indexability decision package](../stories/story-35-01-canonical-public-host-and-edge-indexability-decision-package.md)
- [ST-35-02: Crawler surfaces and honest HTTP status semantics](../stories/story-35-02-crawler-surfaces-and-honest-http-status-semantics.md)
- [ST-35-03: Public-route metadata, canonical, and indexing policy](../stories/story-35-03-public-route-metadata-canonical-and-indexing-policy.md)
- [ST-35-04: Search Console, Bing, and launch-day SEO operations](../stories/story-35-04-search-console-bing-and-launch-day-seo-operations.md)

## Decision Trees

### 1. Canonical host

| Decision point | Path A | Path B | Current recommendation |
|---|---|---|---|
| Is Skriptoteket moving to `https://hule.education` before launch? | Migrate fully to the apex only if DNS, TLS, redirects, app config, and search-console ownership switch together in one cutover | Keep `https://skriptoteket.hule.education` as the only canonical Skriptoteket host and keep the apex non-competing until it becomes a real product surface | Path B |
| Do we need a `www` variant for launch? | Add DNS, TLS coverage, and a permanent redirect to the canonical host | Leave `www` out of scope for launch and avoid introducing another public variant | Path B |

### 2. Crawl contract

| Route class | HTTP contract | Search contract | Current recommendation |
|---|---|---|---|
| Public landing and public curated-app entry pages | `200 OK` with real metadata and self-canonical URL | Indexable and listed in the sitemap | Required now |
| Authenticated or private teacher surfaces | Product-driven response semantics only | Excluded from sitemap and explicitly non-indexable where appropriate | Required now |
| Malformed or non-existent URLs | Honest `404` or `410`, not SPA-shell `200` | Not indexable | Required now |

### 3. Rendering depth

| Need | Implementation lane | When |
|---|---|---|
| Minimum viable launch indexing | Real crawler files, honest status semantics, and route-level head metadata | Now |
| Stronger organic discoverability later | Public-page prerender or SSR plus structured data and broader crawlable surface expansion | After the minimum lane is stable |

## Notes

- [REF-launch-seo-and-search-indexing-readiness-2026-04-08](../../reference/ref-launch-seo-and-search-indexing-readiness-2026-04-08.md)
  is the canonical evidence and analysis record for this epic.
- Story ordering matters. `ST-35-01` should freeze the host policy before the
  crawler, metadata, and search-ops stories harden around it.
- `ST-35-02` is the launch-critical technical truth gate. If `/robots.txt`,
  `/sitemap.xml`, and unmatched URLs are still wrong at the backend edge, the
  rest of the lane is only partial polish.
- This epic requires review approval before implementation begins.
