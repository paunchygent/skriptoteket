---
name: skriptoteket-frontend-specialist
description: Skriptoteket frontend development (FastAPI backend + full Vue/Vite SPA) using the HuleEdu-aligned stack (Vue 3.5.x + Vite + TypeScript, Pinia, Vue Router, Tailwind CSS v4 tokens/@theme, HuleEdu design tokens, pnpm). Use for working in the `frontend/` pnpm workspace, SPA hosting/history fallback, implementing SPA features (auth, routing, state, API clients), and keeping the UI/auth model compatible with future HuleEdu teacher login integration (same entry point, no separate login).
---

# Skriptoteket Frontend Specialist

## Defaults

- SPA-only: do not re-introduce template/HTMX UI (ADR-0027 clean-break cutover).
- Use Vue 3.5 Composition API with `<script setup lang="ts">`.
- Keep the frontend HuleEdu-aligned so it can be integrated into HuleEdu later (shared design tokens and compatible auth model).
- Keep integration costs low: avoid hardcoded base paths, isolate auth transport (cookie vs bearer), and prefer token-driven styling over bespoke CSS.
- Styling is tokens-first: `tokens.css` (canonical `--huleedu-*`) + `tailwind-theme.css` (Tailwind bridge via `@theme inline`).
- Single CSS entry point: `frontend/apps/skriptoteket/src/assets/main.css` (imports Tailwind + tokens + theme once).
- Before significant UI work in Klassrumskartan or other dense curated apps, read
  `docs/reference/ref-klassrumskartan-workspace-ui-doctrine-2026-03-28.md`.
- Use SPA primitives from `frontend/apps/skriptoteket/src/assets/main.css` to avoid drift:
  - Buttons: `.btn-primary`, `.btn-cta`, `.btn-ghost`
  - Panels (nested): `.panel-inset`, `.panel-inset-canvas`
  - Toasts: `.toast-*` (via `ToastHost`)
  - Inline messages: `.system-message*` (via `SystemMessage`)
  - Badges: `.status-pill`
- No stacked brutal shadows: only the outermost “card/panel” gets `shadow-brutal*`. Nested panels/fields inside a
  shadowed surface use `shadow-none` + thicker, uniform borders (`panel-inset*`, or `border-2 border-navy/20`).
- No Tailwind default palette leakage in product UI: avoid `bg-slate-*`, `text-gray-*`, etc. Prefer token-mapped utilities (`bg-canvas`, `text-navy`, `shadow-brutal-sm`) or CSS variables.
- Page/editor transitions: prefer opacity-only transitions (hard borders/shadows shimmer when translated).
- Dense workspace doctrine:
  - Treat multi-workspace apps as instruments, not stacked card pages.
  - One stable shell should own title, workspace mode, compact context, status, and exit.
  - The active board/map/canvas/inspector surface should dominate the layout.
  - Prefer compact action rows, icon-supported controls, and drawers/menus for secondary actions.
  - Avoid introducing new full-width helper/status panels when the workspace is already clear.
  - Design desktop/laptop composition first for workspace-heavy curated apps; mobile is a reduced port, not the source layout.
- Admin editor features: extract logic into `frontend/apps/skriptoteket/src/composables/editor/` and keep views UI-only.

## Repo map (Skriptoteket monolith)

- Backend (FastAPI + SPA hosting + APIs): `src/skriptoteket/web/`
  - Static assets: `src/skriptoteket/web/static/` (`/static/*`)
  - Built SPA assets: `src/skriptoteket/web/static/spa/` (served via history fallback)
- Frontend workspace (pnpm): `frontend/`
  - SPA app: `frontend/apps/skriptoteket/`

## Workflow

1. Work from the repo root:
   - Backend dev: `pdm run dev` (or `pdm run dev-logs` for log piping)
   - Frontend install: `pdm run fe-install`
   - SPA dev server: `pdm run fe-dev` (or `pdm run fe-dev-logs` for log piping)
   - Local combo (backend + SPA): `pdm run dev-local`
   - Container dev: `pdm run dev-start` (logs: `pdm run dev-containers-logs`, rebuild: `pdm run dev-rebuild`)
   - SPA tests: `pdm run fe-test` (Vitest), `pdm run fe-type-check`, `pdm run fe-lint`
2. Implement in this order:
   - OpenAPI models (backend) -> regenerate TypeScript types (`pdm run fe-gen-api-types`)
   - API client calls in SPA
   - Pinia stores for shared state, views/components for UI
3. Keep styling token-driven and HuleEdu-compatible (ADR-0032 + `@theme inline` bridge).
4. Keep auth integration "pluggable" so HuleEdu SSO can be added without rewriting the SPA (ADR-0006/ADR-0011 + current cookie/CSRF transport).

## UI doctrine for dense workspaces

- The design system is a base language, not permission to wrap every section in an equal-weight panel.
- Use prose sparingly inside planner-like workspaces; supporting copy should usually fit on one short line.
- Repeated operational actions should be icon-first or icon-supported. Text-only buttons are for rare or high-stakes actions.
- Define and reuse a canonical symbol set for repeated operations before adding more text buttons.
- Keep secondary context visibly subordinate:
  - history in drawers or menus
  - metadata in inspectors
  - setup context in compact strips or labeled controls
- Avoid dead space:
  - do not spend major vertical space on redundant titles, summaries, and helper text
  - do not make toolbars taller than the work they control
  - do not stack shell + action bar + status bar + summary bar before the main board/map/canvas unless each band is truly necessary
- Preserve location memory:
  - mode switch stays fixed
  - exit stays fixed
  - status stays fixed
  - task-specific tools stay near the task surface
- For Klassrumskartan specifically:
  - `Översikt` should feel neutral and class-first
  - `Grupper` should read as pool plus board
  - `Sittplatser` should read as pool plus room canvas
  - `Regler` should read as rail plus map plus inspector
  - mobile should be a simplified companion layout, not the same dense workspace collapsed vertically

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

### Layout + editor ergonomics

- Full-height editor routes:
  - Wrap route content in `route-stage` + `route-stage-item` (see `frontend/apps/skriptoteket/src/App.vue`).
  - Use `route-stage--editor` for editor routes so nested flex/grid children can use `min-h-0`.
  - In authenticated layout, use the editor variant (`auth-main-content--editor`) to avoid double scrollbars and let the
    editor manage its own scroll regions (see `frontend/apps/skriptoteket/src/components/layout/AuthLayout.vue`).
- Focus mode (width matters):
  - Persisted per user via `useLayoutStore` (`frontend/apps/skriptoteket/src/stores/layout.ts`).
  - Editor is the primary entry point for toggling; ensure the user is never “trapped” without an exit control.
- Drawers:
  - Reuse the existing right-side drawer surface for editor chat/history; don’t introduce a second sidebar.
  - Prefer `bg-canvas` + `border-navy` + `shadow-brutal-sm` for drawer frames (see `EditorWorkspacePanel.vue`).
- Dense toolbars:
  - Use the editor micro-typography pattern: `text-[10px] font-semibold uppercase tracking-wide text-navy/60`.
  - Use `.btn-ghost` with size/shadow overrides for 28px controls (see `EditorWorkspaceToolbar.vue`).

### Layout geometry ownership

- This is a frontend mandate, not a workspace-specific preference: **CSS owns layout geometry**.
- Layout geometry includes:
  - panel height, width, and position
  - sticky behavior
  - overflow ownership and scroll containment
  - breakpoint cutover
  - lane/column alignment
- If a surface drifts, fix CSS containment, track sizing, `min-h-0`, and overflow ownership first.
  Do not compensate with runtime geometry math.
- CSS is the only source of truth for layout shape:
  - shells, panes, rails, boards, canvases, inspectors, drawers, and sidebars get size/position/sticky/overflow behavior from CSS
  - use grid for structural composition and flex for one-dimensional alignment
- JS may select state, not geometry:
  - allowed: mode switches, semantic state, conditional mount/unmount, data flow, interaction logic
  - forbidden by default: persistent panel height, top offset, max-height, sticky thresholds, or breakpoint behavior
- Breakpoints are declarative:
  - define breakpoint cutovers once in shared CSS/layout tokens
  - do not re-encode the same breakpoint contract in runtime JS
- Overflow must have named owners:
  - for each axis, be able to name exactly which element scrolls
  - if multiple ancestors compete for the same vertical scroll path without a deliberate reason, the layout is invalid
- Sticky must resolve through CSS containment alone:
  - sticky rails/headers should work because the containing block and overflow chain are correct
  - do not repair sticky failures with JS position recomputation
- Measured layout is forbidden by default:
  - treat `window.innerHeight`, `getBoundingClientRect()`, `ResizeObserver`, or scroll listeners used for persistent surface sizing/alignment as a design smell unless an explicit exception is approved

### Geometry review red flags

- `window.innerHeight - rect.top` or similar viewport math to size persistent UI surfaces
- updating CSS variables from `getBoundingClientRect()` to keep panels visible/aligned
- scroll listeners whose job is panel alignment or sticky compensation
- `ResizeObserver` loops whose job is persistent surface sizing
- route-specific wrapper offsets or per-shell top math
- duplicating CSS breakpoint behavior in JS
- fixing nested-scroll bugs by adding another measured height layer

### Allowed JS domains

- data/state orchestration
- drag-and-drop and canvas interactions inside an already bounded workspace
- focus management and accessibility behavior
- virtualization inside a scroller whose size/overflow are already defined by CSS
- transient measurement/effects that do not define persistent panel geometry

### Exception path

- A JS layout exception is allowed only when all of these are true:
  - CSS cannot express the behavior cleanly and that reason is documented
  - the exception is explicit and localized, not hidden in normal component flow
  - it does not depend on page scroll position or wrapper-relative offsets
  - it does not duplicate CSS breakpoint logic
  - it does not redefine shell/overflow ownership
  - browser proof covers canonical widths and resize transitions

### Geometry review questions

- Who owns the height budget?
- Who owns vertical overflow?
- Would sticky still work if post-render JS measurement stopped?
- Are breakpoints defined once?
- Does any code author geometry from viewport or element measurements?
- Are there competing scroll owners on the same axis?

### Responsive strategy for curated apps

- Default assumption for workspace-heavy curated apps: desktop-first.
- Start by designing the canonical desktop layout for common laptop and desktop widths.
- Then define smaller-screen compositions intentionally:
  - reduce simultaneous panels
  - collapse secondary actions into drawers/menus
  - remove or defer non-essential operations when needed
- Do not preserve feature parity at the cost of a cramped, card-stacked desktop UI.

### Testing (Vitest)

- Config: `frontend/apps/skriptoteket/vitest.config.ts`
- Setup: `frontend/apps/skriptoteket/src/test/setup.ts`
- Tests: `frontend/apps/skriptoteket/src/**/*.spec.ts` (colocate with code)
- Commands: `pdm run fe-test` / `pdm run fe-test-watch` / `pdm run fe-test-coverage`
- Prefer testing pure helpers/composables and mocking HTTP via `vi.mock` rather than snapshot-heavy component tests.

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

- SPA adoption: `docs/adr/adr-0027-full-vue-vite-spa.md`
- SPA hosting + history fallback: `docs/adr/adr-0028-spa-hosting-and-history-fallback.md`
- OpenAPI + TS generation: `docs/adr/adr-0030-openapi-and-frontend-types.md`
- Tailwind v4 tokens bridge: `docs/adr/adr-0032-tailwind-4-theme-tokens.md`
- Workspace UI doctrine: `docs/reference/ref-klassrumskartan-workspace-ui-doctrine-2026-03-28.md`
- Concrete desktop-composition examples: `docs/backlog/stories/story-29-03-klassrumskartan-shared-desktop-workspace-composition-primitives.md`,
  `docs/backlog/stories/story-29-05-klassrumskartan-grouping-and-seating-desktop-workspace-overhaul.md`
- Testing runbook: `docs/runbooks/runbook-testing.md`
- SPA design system rules: `.agents/rules/045-huleedu-design-system.md`
- Testing standards: `.agents/rules/070-testing-standards.md`
