---
name: skriptoteket-frontend-specialist
description: Skriptoteket frontend development inside the Skriptoteket monolith (FastAPI + Jinja templates + static assets) using the HuleEdu-aligned stack (Vue 3.5.x + Vite + TypeScript, Pinia, Vue Router, Tailwind CSS v4 tokens/@theme, HuleEdu design tokens, pnpm). Use for working in the `frontend/` pnpm workspace, wiring Vite builds/manifest into the backend, implementing SPA features (auth, routing, state, API clients), and keeping the UI/auth model compatible with future HuleEdu teacher login integration (same entry point, no separate login).
---

# Skriptoteket Frontend Specialist

## Defaults

- Prefer a single SPA paradigm for product pages; avoid re-introducing template/HTMX UI unless maintaining legacy surfaces.
- Use Vue 3.5 Composition API with `<script setup lang="ts">`.
- Keep the frontend HuleEdu-aligned so it can be integrated into HuleEdu later (shared design tokens and compatible auth model).
- Keep integration costs low: avoid hardcoded base paths, isolate auth transport (cookie vs bearer), and prefer token-driven styling over bespoke CSS.
- Lock styling down with a tokens-first setup: `tokens.css` (canonical `--huleedu-*`) + `tailwind-theme.css` (Tailwind bridge via `@theme inline`).
- Admin editor features: extract logic into `frontend/apps/skriptoteket/src/composables/editor/` and keep views UI-only.

## Repo map (Skriptoteket monolith)

- Backend (FastAPI + templates + static): `src/skriptoteket/web/`
  - Templates: `src/skriptoteket/web/templates/`
  - Static assets: `src/skriptoteket/web/static/`
  - Vite manifest + built SPA assets: `src/skriptoteket/web/static/spa/`
- Frontend workspace (pnpm): `frontend/`
  - SPA app: `frontend/apps/skriptoteket/`
  - (Legacy) islands: `frontend/islands/`

## Workflow

1. Work from the repo root:
   - Backend dev: `pdm run dev`
   - Frontend install: `pdm run fe-install`
   - SPA dev server: `pdm run fe-dev`
2. If backend templates must load assets from Vite dev server, set `VITE_DEV_SERVER_URL` (see `references/vite-hosting.md`).
3. Implement in this order:
   - OpenAPI models (backend) -> regenerate TypeScript types (see `references/data-api.md`)
   - API client calls in SPA
   - Pinia stores for shared state, views/components for UI
4. Keep styling token-driven and HuleEdu-compatible (see `references/styling-tokens.md`).
5. Keep auth integration "pluggable" so HuleEdu SSO can be added without rewriting the SPA (see `references/auth-integration.md`).

## Patterns

### Pinia state

- Define stores with `defineStore(...)`; keep state/actions cohesive and typed.
- Avoid destructuring the store object; use `storeToRefs(store)` when you need refs.
- Centralize auth/session state in one store and let router guards depend on it.

### Routing + hosting

- Use history mode routing with server-side fallback (backend serves `index.html` for non-API routes).
- Avoid hardcoding absolute paths; keep router base aligned with Vite `base`.

### API contracts

- Treat OpenAPI as the source of truth and generate TypeScript types via `openapi-typescript`.
- Keep response/error envelopes consistent; handle 401/403 centrally.

### Auth (integration-ready)

- Current Skriptoteket reality: cookie-session auth + CSRF for mutating requests.
- Future HuleEdu integration: identity federation without shared authorization (keep Skriptoteket roles local).
- In the SPA, isolate auth transport details behind a small adapter (cookie vs bearer) so the UI can run in both modes.

## HuleEdu compatibility checklist

- Versions: Vue 3.5.x / Pinia 3.x / Vue Router 4.6.x / Vite 6.x (match HuleEdu minor lines).
- Paths: use `import.meta.env.BASE_URL` + relative URLs so the SPA can be hosted under a subpath.
- Auth: handle 401 centrally; do not assume a separate Skriptoteket login UI exists in "integrated" mode.
- Styling: use HuleEdu tokens as the contract; avoid hard-coded colors/fonts.

## Context7 lookups

Use Context7 when you need exact API details or version-specific behavior:

- Vue 3 docs: `/vuejs/docs` (Composition API, `<script setup>`)
- Pinia docs: `/vuejs/pinia` (setup stores, TypeScript, best practices)
- Vue Router docs: `/vuejs/vue-router` (route meta, guards)
- Vite v6 docs: `/websites/v6_vite_dev` (config, proxy, dev server)
- Tailwind v4 docs: `/websites/tailwindcss` (theme variables, `@theme`, `@reference`)
- Vitest v4 docs: `/vitest-dev/vitest/v4.0.7` (mocking, `vi.mock`, `vi.mocked`)

## References

- Stack + commands: `references/stack.md`
- Vite hosting + manifest: `references/vite-hosting.md`
- Styling + tokens: `references/styling-tokens.md`
- Data/API + OpenAPI types: `references/data-api.md`
- Auth + HuleEdu integration readiness: `references/auth-integration.md`
- Testing: `references/testing.md`
