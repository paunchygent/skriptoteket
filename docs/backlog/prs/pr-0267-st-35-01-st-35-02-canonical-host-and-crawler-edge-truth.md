---
type: pr
id: PR-0267
title: "ST-35-01/ST-35-02 canonical host and crawler edge truth"
status: done
owners: "agents"
created: 2026-04-15
updated: 2026-04-15
stories:
  - "ST-35-01"
  - "ST-35-02"
tags: ["backend", "seo", "routing", "docs-as-code"]
acceptance_criteria:
  - "Given the launch host policy is approved, when crawler files are generated, then canonical URLs use `https://skriptoteket.hule.education` unless explicitly overridden by deploy configuration."
  - "Given crawlers request `/robots.txt`, when the route is fetched, then it returns `200 OK`, `text/plain`, and a real robots body with the canonical sitemap URL."
  - "Given crawlers request `/sitemap.xml`, when the route is fetched, then it returns `200 OK`, XML content, and only the approved launch-indexable public URLs."
  - "Given malformed public app URLs and unknown paths should not become soft 404s, when those paths are fetched, then the backend returns an honest `404` instead of the generic SPA shell."
  - "Given valid SPA deep links still need browser routing, when auth, private app, and approved public entry paths are fetched, then the backend still returns the SPA entry response."
---

## Problem

The approved `REV-EPIC-35` package identified a launch blocker: crawler-critical URLs and unknown
paths still fall through to the same SPA `200 OK` shell. That makes `/robots.txt`,
`/sitemap.xml`, and missing URLs indistinguishable to direct fetches and search crawlers.

## Goal

Freeze the first implementation slice around the canonical Skriptoteket app host and repair the
backend-owned crawler/status contract:

- canonical public app host: `https://skriptoteket.hule.education`
- crawler files are backend-owned, explicit, and not SPA fallback content
- sitemap includes only `/` and `/public/apps/classroom.group-seating-studio`
- malformed public app paths and unknown paths return honest `404`
- valid SPA deep-link families keep returning the SPA entry response

## Non-goals

- Do not implement `ST-35-03` route-specific metadata or head injection in this slice.
- Do not add Search Console or Bing account verification; that remains `ST-35-04`.
- Do not broaden the public sitemap beyond the two approved launch URLs.
- Do not introduce SSR or full-SPA prerendering.

## Implementation plan

1. Add a deploy-overridable `PUBLIC_APP_BASE_URL` setting with the approved canonical default.
2. Add explicit `/robots.txt` and `/sitemap.xml` routes before the SPA catch-all.
3. Replace the open-ended fallback predicate with an explicit route-family allowlist.
4. Return honest `404` responses for malformed public app paths and unknown paths.
5. Add focused backend tests for crawler files and the route-family matrix.
6. Run a live curl checklist against the backend route surface and record it in handoff.

## Test plan

- `pdm run pytest -q tests/unit/web/test_spa_fallback.py`
- `pdm run docs-validate`
- `git diff --check`
- Live curl checklist:
  `/`, `/public/apps/classroom.group-seating-studio`, `/robots.txt`, `/sitemap.xml`,
  `/public/apps`, `/public/apps/unknown-app`, and `/this-route-should-not-exist`

## Rollback plan

Remove the crawler routes and fallback route-family allowlist, restore the previous broad SPA
fallback predicate, remove the tests and setting, and rerun the focused backend/docs checks.

## Implementation Summary

- Added `PUBLIC_APP_BASE_URL` as the deploy-overridable canonical public app host setting.
- Added explicit `/robots.txt` and `/sitemap.xml` backend routes.
- Narrowed SPA fallback to approved route families instead of serving every unknown path.
- Added focused route tests for crawler files, valid SPA routes, malformed public app paths, and
  unknown routes.
