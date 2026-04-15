---
type: pr
id: PR-0268
title: "ST-35-03 public route initial HTML metadata"
status: done
owners: "agents"
created: 2026-04-15
updated: 2026-04-15
stories:
  - "ST-35-03"
tags: ["backend", "seo", "spa"]
acceptance_criteria:
  - "Backend-served initial HTML for `/` and `/public/apps/classroom.group-seating-studio` contains unique titles, descriptions, canonical URLs, robots policy, Open Graph tags, and share-card metadata."
  - "Authenticated and private SPA route families served by the fallback receive explicit non-indexable robots metadata and stay out of the sitemap."
  - "Malformed public-app routes and unknown routes keep honest 404 status semantics and receive non-indexable robots metadata."
  - "A browser hydration proof confirms the runtime document head still matches the launch-visible metadata contract for both public URLs."
---

## Problem

`ST-35-01` and `ST-35-02` made the crawler files and direct URL status semantics honest, but the
SPA shell still needs backend-visible route metadata for the two approved public launch URLs.

## Goal

Serve route-specific head metadata from the backend fallback so crawlers and social link unfurlers
see the correct title, description, canonical URL, robots policy, and share tags before JavaScript
hydration.

## Non-goals

- Do not add whole-SPA SSR or prerendering.
- Do not open authenticated or private teacher routes to indexing.
- Do not expand the launch sitemap beyond the approved public route allowlist.

## Implementation plan

- Add a focused web helper that renders and injects route metadata into the built SPA shell.
- Update the SPA fallback to return injected HTML instead of the generic static shell.
- Return a minimal backend-owned 404 HTML response with `noindex,nofollow` for malformed and
  unknown routes.
- Extend route tests for public, private, and 404 indexing policy.

## Test plan

- Run focused backend route tests for the crawler and fallback contract.
- Run a browser hydration check against a temporary local ASGI server for both public URLs.
- Run docs validation, typecheck, lint, and whitespace checks before closeout.

## Rollback plan

Revert this slice to the `PR-0267` fallback behavior, keeping `robots.txt`, `sitemap.xml`, and the
honest route allowlist intact.

## Implementation Summary (as of 2026-04-15)

- Added backend-owned SPA head metadata injection for `/` and
  `/public/apps/classroom.group-seating-studio`.
- Added explicit `noindex,follow` metadata for private/authenticated fallback routes.
- Added backend-owned `404` HTML with `noindex,nofollow` for malformed public-app and unknown
  routes.
- Added a targeted Playwright hydration proof for both public launch URLs.
