---
type: story
id: ST-35-03
title: "Public-route metadata, canonical, and indexing policy"
status: ready
owners: "agents"
created: 2026-04-08
updated: 2026-04-08
epic: "EPIC-35"
dependencies:
  - "ST-35-01"
  - "ST-35-02"
  - "ST-32-07"
  - "ST-32-08"
  - "REF-launch-seo-and-search-indexing-readiness-2026-04-08"
acceptance_criteria:
  - "Given `/` and `/public/apps/classroom.group-seating-studio` are the current public entry points, when this story ships, then each route exposes a unique title, meta description, canonical URL, and share metadata aligned with the chosen canonical host."
  - "Given Skriptoteket is a mixed public/private SPA, when this story ships, then the indexing policy is explicit per route family instead of relying on one generic HTML shell for every page."
  - "Given authenticated and private teacher routes should not become search results, when this story ships, then those routes are excluded from sitemap coverage and receive the appropriate indexing policy."
  - "Given full SSR or prerender may not be required for launch, when this story is reviewed, then it records whether route-level head management alone is sufficient for the current launch goals or whether public-page prerender becomes a required follow-on."
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

## References

- Epic parent:
  [EPIC-35](../epics/epic-35-launch-seo-and-search-indexing-readiness.md)
- Evidence and analysis:
  [REF-launch-seo-and-search-indexing-readiness-2026-04-08](../../reference/ref-launch-seo-and-search-indexing-readiness-2026-04-08.md)
- Current SPA shell:
  [frontend/apps/skriptoteket/index.html](../../../frontend/apps/skriptoteket/index.html)
- Current public landing:
  [HomeView.vue](../../../frontend/apps/skriptoteket/src/views/HomeView.vue)
