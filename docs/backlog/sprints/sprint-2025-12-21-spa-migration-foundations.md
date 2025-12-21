---
type: sprint
id: SPR-2025-12-21
title: "Sprint 2025-12-21: SPA migration foundations"
status: active
owners: "agents"
created: 2025-12-21
starts: 2025-12-21
ends: 2026-01-04
objective: "Establish the full-SPA foundation: frontend workspace + SPA scaffold, pure-CSS UI library skeleton, FastAPI hosting plan, OpenAPI→TypeScript workflow, and an initial auth+routing shell."
prd: "PRD-spa-frontend-v0.1"
epics: ["EPIC-11"]
stories: ["ST-11-01", "ST-11-02", "ST-11-03", "ST-11-04", "ST-11-05"]
adrs: ["ADR-0027", "ADR-0028", "ADR-0029", "ADR-0030"]
---

## Objective

Establish the minimum viable “full SPA” foundation so further route-parity work can proceed as vertical slices.

## Scope (committed stories)

- [ST-11-01: Frontend workspace + SPA scaffold](../stories/story-11-01-frontend-workspace-and-spa-scaffold.md)
- [ST-11-02: UI library + design tokens (pure CSS)](../stories/story-11-02-ui-library-and-design-tokens.md)
- [ST-11-03: Serve SPA from FastAPI (manifest + history fallback)](../stories/story-11-03-spa-hosting-fastapi-integration.md)
- [ST-11-04: API v1 conventions + OpenAPI → TypeScript generation](../stories/story-11-04-api-v1-and-openapi-typescript.md)
- [ST-11-05: Auth flow + route guards](../stories/story-11-05-auth-flow-and-route-guards.md)

## Out of scope

- Route parity for all user/admin flows (starts next sprint once foundation is stable).
- Legacy SSR/HTMX coexistence polish (cutover is a clean break per ADR-0027).
- Playwright coverage for full parity flows (added later once core views exist).

## Decisions required (ADRs)

- ADR-0027: Full SPA as the frontend (accepted)
- ADR-0028: SPA hosting + routing integration (accepted)
- ADR-0029: Styling = pure CSS + design tokens (accepted)
- ADR-0030: OpenAPI as source + `openapi-typescript` (accepted)

## Risks / edge cases

- Auth/session edge cases (cookie + CSRF) causing confusing SPA failures.
- Accidental coupling to legacy island artifacts during the transition period.
- Dev workflow friction if Vite dev server/proxy is not stable early.

## Execution plan

1. Create the new pnpm workspace layout (`apps/` + `packages/`) and get a routed SPA shell running.
2. Add a minimal `@huleedu/ui` package with token imports and 1–2 primitives.
3. Define and wire an initial “OpenAPI → types” generation path (command + output location).
4. Implement the auth store + router guards for protected routes (login redirect + role gating).
5. Confirm the app can be served by FastAPI with history fallback (dev + prod build plan).

## Demo checklist

- `pnpm dev` shows the SPA shell and can navigate between placeholder routes.
- Auth guard blocks a protected route and navigates to `/login`.
- UI primitives render with token-driven styling (no Tailwind).

## Verification checklist

- `pdm run docs-validate`
- `pnpm -C frontend install`
- `pnpm -C frontend lint`
- `pnpm -C frontend typecheck`
- `pnpm -C frontend build`

## Notes / follow-ups

- Next sprint starts route-parity vertical slices (browse + run + admin/editor).
