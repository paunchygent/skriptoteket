---
type: reference
id: REF-SKRIPT-PRD-frontend-prd-v0-1-full-vue-vite-spa-migration
title: 'Frontend PRD v0.1: Full Vue/Vite SPA migration'
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
status: active
reference_kind: prd
summary: 'Frontend PRD v0.1: Full Vue/Vite SPA migration'
---

## Product Outcome And Users

### Source: Summary

Migrate Skriptoteket from a server-rendered Jinja2/HTMX frontend to a **single** Vue 3 / Vite SPA that covers **all**
user-facing and admin/contributor surfaces.

This is a deliberate “clean break” migration: once cutover happens, legacy templates, HTMX behaviors, and page routes are
removed.

## Capability Direction

### Source: Success metrics (initial)

- Route parity: all current web routes have SPA equivalents and are reachable with the same auth requirements.
- E2E: Playwright covers critical flows (login, browse, run tool, admin/contributor editor).
- Operational: `pnpm build` produces hashed assets + manifest; FastAPI serves the SPA with history fallback.
- Deletion: Jinja2 templates and HTMX dependencies are removed from the runtime app after cutover.

### Source: Dependencies

- ADR-0027 (full SPA adoption)
- ADR-0028 (SPA hosting + routing integration)
- ADR-0030 (OpenAPI + generated TypeScript)
- ADR-0032 (Tailwind 4 with @theme design tokens; supersedes ADR-0029)

## Boundaries And Non-Goals

### Source: Non-goals

- Offline mode or PWA support.
- A second admin SPA (admin remains part of the same SPA with route guards).
- Supporting both SSR and SPA long-term (cutover is a clean replacement).

## Success Signals

The source does not provide a separate success signals section; no additional success signals is recorded.

## Governed Follow-Up

The source does not provide a separate governed follow-up section; no additional governed follow-up is recorded.

### Source: Goals

- One frontend paradigm (SPA) for the entire product surface.
- Preserve current role model and authorization semantics (users/contributors/admin/superuser).
- Preserve current security posture (server-side sessions, CSRF protection, no tool-provided UI JS).
- Maintain HuleEdu visual identity via design tokens and the brutalist component styling language.
- Prevent frontend/backend drift via OpenAPI as the source of truth and generated TypeScript types.

### Source: Scope (high level)

- Frontend: `frontend/` becomes a pnpm workspace with:
  - `apps/skriptoteket` (the SPA)
  - `packages/huleedu-ui` (Vue component library, Tailwind 4 + design tokens via @theme)
- Backend: `/api/v1/*` added/expanded to back the SPA and documented via OpenAPI.
- Hosting: SPA is served by the FastAPI app (same-origin) to avoid CORS complexity.
