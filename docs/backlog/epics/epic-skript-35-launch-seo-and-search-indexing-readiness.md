---
type: epic
id: EPIC-SKRIPT-35
title: Launch SEO and search indexing readiness
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
outcome: 'Skriptoteket can launch under the intended HuleEdu domain topology: `hule.education`
  serves the HuleEdu landing layer, `api.hule.education` becomes the shared browser
  auth/API edge, `skriptoteket.hule.education` remains the canonical public Skriptoteket
  app host for its crawlable surfaces, and the current public pages gain valid crawler-facing
  files, honest HTTP status semantics, route-level metadata, and operator-ready search
  verification.'
retired_ids:
- EPIC-35
dependencies:
- ADR-SKRIPT-0027
- ADR-SKRIPT-0028
- ADR-SKRIPT-0076
- REF-SKRIPT-GENERAL-reference-huleedu-launch-surface-and-shared-auth-topology-2026-04-08
- REF-SKRIPT-RESEARCH-reference-launch-seo-and-search-indexing-readiness-assessment-2026-04-08
---

## Scope
- Consume the frozen launch topology from `ST-28-05` instead of treating
  `skriptoteket.hule.education`, `hule.education`, `api.hule.education`, and
  potential `www` variants as an SEO-owned decision space.
- Treat `hule.education` as the HuleEdu entrypoint and `api.hule.education` as
  the shared browser auth/API edge while keeping `skriptoteket.hule.education`
  as the canonical public Skriptoteket app host.
- Convert crawler-critical paths such as `/robots.txt` and `/sitemap.xml` into
  real edge-owned responses with correct content type, body, and status code.
- Repair public-route and unmatched-route HTTP semantics so search engines do
  not receive the SPA shell as a misleading `200 OK` response for malformed or
  non-existent URLs.
- Add minimum viable indexing metadata for the current public entry surfaces:
  `/` and `/public/apps/classroom.group-seating-studio`.
- Define an explicit indexing policy for public, authenticated, and unmatched
  route families rather than relying on one generic SPA shell.
- Keep the launch SEO lane aligned with the HuleEdu-owned session direction in
  `EPIC-28` and `ADR-0076` instead of hardening around app-local auth
  assumptions or apex-domain drift.
- Document and execute the search-operator lane: Search Console / Bing
  verification, sitemap submission, launch-day checks, and post-deploy
  revalidation.
### Out of Scope
- A broad marketing-site rewrite or a copywriting campaign beyond the minimum
  metadata and launch-surface discoverability required for indexing.
- Opening authenticated or private teacher surfaces to public search indexing.
- SEO expansion for every route in the SPA when the current launch-visible
  surface is still intentionally narrow.
- Full SSR or prerender adoption across the whole SPA by default; that remains
  a follow-up choice after the minimum crawlability lane is honest and stable.
- Search ranking promises. This epic only aims to make the public surface
  crawlable, coherent, and operator-verifiable.
- Implementing the HuleEdu identity service, API gateway, or apex landing page
  itself inside the Skriptoteket repo. Those are upstream platform work, but
  this epic must stay compatible with them.

## Epic Contract
The source record did not define a separate section for this package heading.

## ADR Coverage
### Decision Trees
### 1. Canonical host

| Decision point | Path A | Path B | Current recommendation |
|---|---|---|---|
| Does `https://hule.education` become the HuleEdu landing page before launch? | Keep the apex as HuleEdu-owned, link to `https://skriptoteket.hule.education`, and keep Skriptoteket's own canonical app URLs on the subdomain | Keep the apex HuleEdu-owned and non-competing until the HuleEdu landing page is ready; do not promote the apex into the Skriptoteket app host | Path A |
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

## Contract Inputs
The source record did not define a separate section for this package heading.

## Stories
### Story Stack
- [ST-35-01: Canonical public host and edge indexability decision package](../stories/story-35-01-canonical-public-host-and-edge-indexability-decision-package.md)
- [ST-35-02: Crawler surfaces and honest HTTP status semantics](../stories/story-35-02-crawler-surfaces-and-honest-http-status-semantics.md)
- [ST-35-03: Public-route metadata, canonical, and indexing policy](../stories/story-35-03-public-route-metadata-canonical-and-indexing-policy.md)
- [ST-35-04: Search Console, Bing, and launch-day SEO operations](../stories/story-35-04-search-console-bing-and-launch-day-seo-operations.md)

## Epic Verification Plan
The source record did not define a separate section for this package heading.

## Exceptions And Follow-Ups
The source record did not define a separate section for this package heading.

## Risks
- If the canonical host is not decided early, link equity and search-console
  ownership can split across the HuleEdu apex, shared API edge, and Skriptoteket
  subdomain surfaces.
- If crawler-facing files still fall through to the SPA shell, search engines
  may delay indexing or classify key URLs as low quality or soft 404s.
- If unmatched URLs stay `200 OK` at the backend edge, route recovery in the
  client will mask indexability defects instead of fixing them.
- If route-level metadata stays generic, public pages may index with weak or
  misleading snippets even after crawlability is repaired.
- If search verification is treated as “someone will do it later,” launch-day
  status will remain ambiguous even after the technical fixes ship.
- If the apex and gateway are built after Skriptoteket hardens around the wrong
  host assumptions, launch-day SEO work can create avoidable redirect and auth
  churn.

## Notes
- [REF-launch-seo-and-search-indexing-readiness-2026-04-08](../../reference/ref-launch-seo-and-search-indexing-readiness-2026-04-08.md)
  is the canonical evidence and analysis record for this epic.
- [REF-huleedu-launch-surface-and-shared-auth-topology-2026-04-08](../../reference/ref-huleedu-launch-surface-and-shared-auth-topology-2026-04-08.md)
  now governs the upstream launch topology that this epic consumes.
- The current intended platform shape is: `hule.education` = HuleEdu landing,
  `api.hule.education` = HuleEdu gateway/session edge, `skriptoteket.hule.education`
  = canonical public Skriptoteket app host.
- Story ordering matters. `ST-35-01` should freeze the Skriptoteket-side host
  and edge behavior under that upstream topology before the
  crawler, metadata, and search-ops stories harden around it.
- `ST-35-02` is the launch-critical technical truth gate. If `/robots.txt`,
  `/sitemap.xml`, and unmatched URLs are still wrong at the backend edge, the
  rest of the lane is only partial polish.
- The April 15 `REV-EPIC-35` requested changes were addressed in the story package by making the
  metadata delivery contract backend-visible, adding a route-family matrix for honest status
  semantics, and assigning the account-bound search-operator proof to a human operator lane.
- `REV-EPIC-35` was approved on 2026-04-15. Implementation can now start with the ordered
  `ST-35-01` / `ST-35-02` slices, while production remains known-bad for crawler files and unknown
  route status semantics until those slices ship.
### Implementation Summary (as of 2026-04-15)
- `ST-35-01` shipped via `PR-0267`: the Skriptoteket canonical public app host is now captured in
  `PUBLIC_APP_BASE_URL`, defaulting to `https://skriptoteket.hule.education`.
- `ST-35-02` shipped via `PR-0267`: `/robots.txt` and `/sitemap.xml` are backend-owned crawler
  files, the sitemap lists only approved public launch URLs, and malformed/unknown routes return
  honest `404` responses instead of a generic SPA `200 OK` shell.
- `ST-35-03` shipped via `PR-0268`: the backend SPA fallback now injects public-route title,
  description, canonical, robots, Open Graph, and share-card metadata into initial HTML, keeps
  private fallback routes non-indexable, and returns non-indexable `404` HTML for malformed or
  unknown routes.
- `ST-35-04` agent-owned prep shipped via `PR-0269`: the launch search operations runbook now
  covers DNS/TLS/redirect/crawler checks, Google Search Console, Bing Webmaster Tools, sitemap
  submission, URL inspection, redacted evidence, and host-migration reruns. The story remains
  blocked on a product owner or deployment operator with account access completing the external
  console verification steps.

## Decision And Assumption Ledger
The source record did not define a separate section for this package heading.

## Plan Document Review
The source record did not define a separate section for this package heading.

## Epic Closeout Review
The source record did not define a separate section for this package heading.
