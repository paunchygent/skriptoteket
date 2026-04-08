---
type: story
id: ST-35-02
title: "Crawler surfaces and honest HTTP status semantics"
status: ready
owners: "agents"
created: 2026-04-08
updated: 2026-04-08
epic: "EPIC-35"
dependencies:
  - "ST-35-01"
  - "ADR-0028"
  - "ST-32-09"
  - "REF-launch-seo-and-search-indexing-readiness-2026-04-08"
acceptance_criteria:
  - "Given search engines request `/robots.txt` and `/sitemap.xml` directly, when this story ships, then those URLs return real crawler files with correct content type and status code rather than the SPA shell."
  - "Given the current public crawl surface is intentionally narrow, when the sitemap contract ships, then it lists only approved canonical public URLs and excludes authenticated or placeholder surfaces."
  - "Given malformed and non-existent URLs currently risk soft-404 behavior, when this story ships, then unmatched public URLs return honest backend `404` or `410` responses instead of a generic SPA `200 OK` shell."
  - "Given the SPA still needs deep-link support for valid public routes, when this story ships, then canonical public routes continue to deep-link correctly while crawler-critical exclusions and not-found semantics are enforced server-side."
ui_impact: "No"
data_impact: "No"
---

## Context

The live April 8, 2026 crawl checks showed three launch-critical edge defects:

- `https://skriptoteket.hule.education/robots.txt` returned the SPA HTML shell with `200 OK`
- `https://skriptoteket.hule.education/sitemap.xml` returned the SPA HTML shell with `200 OK`
- arbitrary non-existent paths also returned the SPA HTML shell with `200 OK`

That means the current backend fallback contract is still honest for app routing but not honest for
crawlers.

## Notes

- This is the story that turns “SEO is alive” from a hope into a technically true statement.
- The fix belongs at the backend edge and static-file layer, not only in Vue route recovery.
- Keep the public route contract narrow and explicit. Do not let the sitemap imply that private
  teacher pages are meant to index.
- `ST-32-09` fixed the client-side recovery experience. This story is the server-side truth gate
  for search engines and direct URL fetches.

## References

- Epic parent:
  [EPIC-35](../epics/epic-35-launch-seo-and-search-indexing-readiness.md)
- Evidence and analysis:
  [REF-launch-seo-and-search-indexing-readiness-2026-04-08](../../reference/ref-launch-seo-and-search-indexing-readiness-2026-04-08.md)
- SPA fallback contract:
  [spa_fallback.py](../../../src/skriptoteket/web/routes/spa_fallback.py)
- Public-route recovery baseline:
  [ST-32-09](story-32-09-canonical-public-route-recovery-and-spa-unmatched-state.md)
