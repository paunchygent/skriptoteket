---
type: prd
id: PRD-spa-frontend-v0.1
title: "Frontend PRD v0.1: Full Vue/Vite SPA migration"
status: active
owners: "agents"
created: 2025-12-21
product: "script-hub"
version: "0.1"
links: ["ADR-0027", "ADR-0028", "ADR-0029", "ADR-0030", "REF-vue-spa-migration-roadmap"]
---

## Summary

Migrate Skriptoteket from a server-rendered Jinja2/HTMX frontend to a **single** Vue 3 / Vite SPA that covers **all**
user-facing and admin/contributor surfaces.

This is a deliberate “clean break” migration: once cutover happens, legacy templates, HTMX behaviors, and page routes are
removed.

## Goals

- One frontend paradigm (SPA) for the entire product surface.
- Preserve current role model and authorization semantics (users/contributors/admin/superuser).
- Preserve current security posture (server-side sessions, CSRF protection, no tool-provided UI JS).
- Maintain HuleEdu visual identity via design tokens and the brutalist component styling language.
- Prevent frontend/backend drift via OpenAPI as the source of truth and generated TypeScript types.

## Non-goals

- Offline mode or PWA support.
- A second admin SPA (admin remains part of the same SPA with route guards).
- Supporting both SSR and SPA long-term (cutover is a clean replacement).

## Success metrics (initial)

- Route parity: all current web routes have SPA equivalents and are reachable with the same auth requirements.
- E2E: Playwright covers critical flows (login, browse, run tool, admin/contributor editor).
- Operational: `pnpm build` produces hashed assets + manifest; FastAPI serves the SPA with history fallback.
- Deletion: Jinja2 templates and HTMX dependencies are removed from the runtime app after cutover.

## Scope (high level)

- Frontend: `frontend/` becomes a pnpm workspace with:
  - `apps/skriptoteket` (the SPA)
  - `packages/huleedu-ui` (Vue component library, pure CSS + design tokens)
- Backend: `/api/v1/*` added/expanded to back the SPA and documented via OpenAPI.
- Hosting: SPA is served by the FastAPI app (same-origin) to avoid CORS complexity.

## Dependencies

- ADR-0027 (full SPA adoption)
- ADR-0028 (SPA hosting + routing integration)
- ADR-0029 (pure CSS design system approach)
- ADR-0030 (OpenAPI + generated TypeScript)
