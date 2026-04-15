---
type: story
id: ST-35-02
title: "Crawler surfaces and honest HTTP status semantics"
status: done
owners: "agents"
created: 2026-04-08
updated: 2026-04-15
epic: "EPIC-35"
dependencies:
  - "ST-35-01"
  - "ADR-0028"
  - "ST-32-09"
  - "REF-launch-seo-and-search-indexing-readiness-2026-04-08"
acceptance_criteria:
  - "Given search engines request `/robots.txt` and `/sitemap.xml` directly, when this story ships, then those URLs return real crawler files with correct content type and status code rather than the SPA shell."
  - "Given the current public crawl surface is intentionally narrow, when the sitemap contract ships, then it lists only approved canonical public URLs and excludes authenticated or placeholder surfaces."
  - "Given malformed and non-existent URLs currently risk soft-404 behavior, when this story ships, then the server-side route-family matrix below is implemented instead of relying on one generic SPA `200 OK` shell."
  - "Given the SPA still needs deep-link support for valid routes, when this story ships, then the backend preserves valid SPA entry families while returning `404` or `410` for malformed public-app URLs and unknown routes."
  - "Given crawler semantics are edge behavior, when this story ships, then parametrized backend tests and live curl checks cover status code, content type, and body class for every route family in the matrix."
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

## Server-Side Route Contract

| Route family | Examples | HTTP contract | Search contract |
|---|---|---|---|
| Crawler policy file | `/robots.txt` | `200 OK`, `text/plain`, real robots body with a sitemap pointer | Crawl policy is readable; do not use robots as the privacy boundary for private pages |
| Sitemap file | `/sitemap.xml` | `200 OK`, XML content type, valid URL set | Lists only approved canonical public URLs for the chosen Skriptoteket host |
| Launch-indexable public pages | `/`, `/public/apps/classroom.group-seating-studio` | `200 OK`, HTML body from the SPA entry with the `ST-35-03` static head contract | Indexable and included in sitemap |
| Non-indexable but valid public app pages | Future registry-backed `/public/apps/{appId}` not approved for launch indexing | `200 OK` only when the app id is registered as public; otherwise use malformed/unknown route behavior | Excluded from sitemap; `ST-35-03` must provide explicit `noindex` policy if this family exists |
| Auth entry and lifecycle pages | `/auth/login`, `/auth/callback`, `/register`, `/forgot-password`, `/reset-password`, `/verify-email` | Preserve SPA deep-link response so the HuleEdu ceremony and recovery flows still render | Excluded from sitemap; explicit `noindex` policy belongs to `ST-35-03` |
| Authenticated/private app pages | `/apps/classroom.group-seating-studio`, `/browse`, `/editor`, `/admin/tools`, `/my-runs`, `/vault` | Preserve SPA deep-link response so browser auth guards and RBAC recovery still render | Excluded from sitemap; explicit `noindex` policy belongs to `ST-35-03` |
| Malformed public-app routes | `/public/apps`, `/public/classroom.group-seating-studio`, `/public/apps/unknown-app` | `404 Not Found` or `410 Gone`; body may render a recovery page but must not be a generic `200 OK` app shell | Not indexable |
| Unknown routes | `/this-route-should-not-exist`, `/anything/not/owned` | `404 Not Found` or `410 Gone`; body must be distinguishable from the public landing shell | Not indexable |
| Backend-owned non-SPA paths | `/api/...`, `/static/...`, `/healthz`, `/metrics`, `/docs`, `/redoc`, `/openapi.json` | Existing owning router/static handler semantics; fallback must not convert misses into SPA `200 OK` | Not part of the public sitemap |

## Proof Requirements

- Add parametrized backend tests against the fallback/static route layer for all matrix rows that
  the backend owns.
- For `/robots.txt` and `/sitemap.xml`, assert status, content type, and that the body is not the
  SPA HTML shell.
- For launch public URLs, assert `200 OK` and the expected initial HTML body class from `ST-35-03`.
- For malformed public-app and unknown routes, assert `404` or `410` with a body that is not the
  public landing HTML shell.
- Add a live curl checklist for `/`, `/public/apps/classroom.group-seating-studio`,
  `/robots.txt`, `/sitemap.xml`, `/public/apps`, `/public/apps/unknown-app`, and a missing path.

## References

- Epic parent:
  [EPIC-35](../epics/epic-35-launch-seo-and-search-indexing-readiness.md)
- Evidence and analysis:
  [REF-launch-seo-and-search-indexing-readiness-2026-04-08](../../reference/ref-launch-seo-and-search-indexing-readiness-2026-04-08.md)
- SPA fallback contract:
  [spa_fallback.py](../../../src/skriptoteket/web/routes/spa_fallback.py)
- Public-route recovery baseline:
  [ST-32-09](story-32-09-canonical-public-route-recovery-and-spa-unmatched-state.md)

## Implementation Summary (as of 2026-04-15)

- `PR-0267` added backend-owned `/robots.txt` and `/sitemap.xml` responses.
- The sitemap allowlist is limited to `/` and `/public/apps/classroom.group-seating-studio`.
- The SPA fallback now preserves valid deep-link families and returns honest `404` responses for
  malformed public app paths and unknown routes.
- Focused backend tests cover status, content type, and SPA/non-SPA body class.
