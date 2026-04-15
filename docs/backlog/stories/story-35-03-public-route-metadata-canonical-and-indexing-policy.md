---
type: story
id: ST-35-03
title: "Public-route metadata, canonical, and indexing policy"
status: done
owners: "agents"
created: 2026-04-08
updated: 2026-04-15
epic: "EPIC-35"
dependencies:
  - "ST-35-01"
  - "ST-35-02"
  - "ST-32-07"
  - "ST-32-08"
  - "REF-launch-seo-and-search-indexing-readiness-2026-04-08"
acceptance_criteria:
  - "Given `/` and `/public/apps/classroom.group-seating-studio` are the current public entry points, when this story ships, then each route exposes a unique title, meta description, canonical URL, robots policy, and share metadata in the backend-served initial HTML."
  - "Given Skriptoteket is a mixed public/private SPA, when this story ships, then the indexing policy is explicit per route family instead of relying on one generic HTML shell for every page."
  - "Given authenticated and private teacher routes should not become search results, when this story ships, then those routes are excluded from sitemap coverage and receive the appropriate indexing policy."
  - "Given client-only head management is not a sufficient launch proof, when this story ships, then backend initial-HTML tests and a browser hydration check prove the runtime head still matches the static launch-visible contract."
ui_impact: "Yes (public page titles/snippets/share cards and route-level indexing semantics)"
data_impact: "No"
---

## Context

The current SPA shell still exposes the same generic `Skriptoteket` title on both the home page and
the public Klassrumskartan host, and the launch assessment found no route-level meta description,
canonical tag, or robots policy on those pages.

That is enough for a developer-friendly SPA but not enough for a launch-facing public surface that
needs predictable snippets, canonicalization, and indexing behavior.

## Notes

- Keep this story grounded in the actual launch surface. The current public pages are few, and that
  is fine.
- Do not let this story balloon into a whole-site marketing copy rewrite.
- If prerender is adopted later, the current route-level metadata decisions should still remain the
  canonical content contract.
- The current public copy and CTA hierarchy from `ST-32-07` / `ST-32-08` should remain the product
  source while this story adds search-facing metadata discipline.
- The launch-visible contract is static backend-served initial HTML for the approved public URLs,
  implemented either by build-time prerender or edge/head injection. A Vue-only head manager may
  keep hydration in sync, but it cannot be the only proof for launch metadata.

## Metadata Delivery Contract

| Route | Initial HTML head contract | Runtime hydration contract | Search/share contract |
|---|---|---|---|
| `/` | Unique title, meta description, self-canonical `https://skriptoteket.hule.education/`, `index,follow` robots policy, Open Graph URL/title/description/type, and equivalent share-card metadata | Vue runtime leaves the same values in place after hydration | Indexable, listed in sitemap |
| `/public/apps/classroom.group-seating-studio` | Unique Klassrumskartan title and description, self-canonical `https://skriptoteket.hule.education/public/apps/classroom.group-seating-studio`, `index,follow` robots policy, Open Graph URL/title/description/type, and equivalent share-card metadata | Vue runtime leaves the same values in place after hydration | Indexable, listed in sitemap |
| Auth entry and lifecycle routes | `noindex,follow` in initial HTML when served by the fallback | Vue runtime may update visible page titles but must not make these routes indexable | Excluded from sitemap |
| Authenticated/private app routes | `noindex,follow` in initial HTML when served by the fallback | Vue runtime may update visible page titles but must not make these routes indexable | Excluded from sitemap |
| Malformed public-app and unknown routes | `noindex,follow` or `noindex,nofollow` with the honest `404` or `410` status from `ST-35-02` | Recovery UX may render client-side, but the status/indexing contract is server-owned | Excluded from sitemap |

## Proof Requirements

- Add backend tests that fetch `/` and `/public/apps/classroom.group-seating-studio` and inspect
  the returned initial HTML for title, description, canonical URL, robots policy, and share tags.
- Add backend tests that prove representative auth/private/malformed routes are not exposed as
  indexable initial HTML.
- Add a browser check for both approved public URLs proving the hydrated document head still
  matches the backend-served metadata contract.
- Keep full SSR or whole-SPA prerendering out of scope unless the implementation cannot satisfy
  the initial-HTML contract with a smaller edge/head-injection lane.

## Implementation Summary (as of 2026-04-15)

- Shipped via `PR-0268`.
- The backend SPA fallback now injects route-specific launch metadata into the initial HTML for `/`
  and `/public/apps/classroom.group-seating-studio`, including title, description, canonical URL,
  robots policy, Open Graph tags, and share-card metadata.
- Auth and private SPA fallback routes receive explicit `noindex,follow` metadata and remain
  excluded from the sitemap.
- Malformed public-app paths and unknown routes keep honest `404` status semantics with
  `noindex,nofollow` metadata.
- `scripts/playwright_pr_0268_spa_metadata_hydration.py` proves the two public route heads still
  match after Vue hydration.

## References

- Epic parent:
  [EPIC-35](../epics/epic-35-launch-seo-and-search-indexing-readiness.md)
- Evidence and analysis:
  [REF-launch-seo-and-search-indexing-readiness-2026-04-08](../../reference/ref-launch-seo-and-search-indexing-readiness-2026-04-08.md)
- Current SPA shell:
  [frontend/apps/skriptoteket/index.html](../../../frontend/apps/skriptoteket/index.html)
- Current public landing:
  [HomeView.vue](../../../frontend/apps/skriptoteket/src/views/HomeView.vue)
