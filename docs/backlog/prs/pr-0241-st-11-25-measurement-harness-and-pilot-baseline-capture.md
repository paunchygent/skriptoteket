---
type: pr
id: PR-0241
title: "ST-11-25: measurement harness and pilot baseline capture"
status: ready
owners: "agents"
created: 2026-04-08
updated: 2026-04-08
stories:
  - "ST-11-25"
tags: ["frontend", "performance", "playwright", "lighthouse", "bundles", "docs"]
dependencies:
  - "ST-11-25"
  - "REV-ST-11-25"
  - "ST-11-03"
  - "ST-11-05"
acceptance_criteria:
  - "Given Skriptoteket needs a repeatable audit lane, when this slice ships, then the repo exposes one documented command surface for production-style frontend performance capture instead of relying on ad hoc DevTools-only workflows."
  - "Given the team wants standard tooling over bespoke measurement code, when this slice ships, then Lighthouse CI is the canonical lab-audit runner, Playwright remains the canonical browser/navigation harness for authenticated route inventory, and bundle ownership is inspected through a standard Vite/Rollup visualizer plugin."
  - "Given the full route matrix is larger than one slice, when this slice ships, then it captures pilot baseline artifacts for a bounded seed set of representative routes without claiming the whole story is complete."
  - "Given later cleanup work depends on trustworthy evidence, when this slice ships, then the generated artifacts distinguish request inventory, transferred bytes, duplicate requests, and chunk ownership rather than collapsing everything into one score."
  - "Given field telemetry may be useful later, when dependency choices are recorded, then `web-vitals` is documented as optional follow-on instrumentation and is not added unless the slice explicitly starts collecting real-user metrics."
---

## Problem

`ST-11-25` now defines what the route-load audit should measure, but the repo still lacks the
first concrete implementation slice:

- there is no canonical command lane for SPA performance capture
- there is no standard artifact layout for route request inventories, bundle reports, and
  Lighthouse/LHCI output
- there is no agreed dependency posture for performance tooling, so the implementation could drift
  into a one-off script pile or duplicate browser stacks

If the first slice is too broad, it will turn into an unbounded “measure everything” effort. If it
is too bespoke, the team will spend time building collectors instead of learning from the routes.

## Goal

Create the first bounded implementation slice for `ST-11-25`:

- establish the standard measurement toolchain
- add one documented command surface
- capture pilot baseline artifacts for a small representative route seed set
- prove the artifact format is useful enough to drive later cleanup slices

## Architecture and placement constraints

This slice must follow the repo’s existing structure rather than creating a new “performance
subsystem” in the wrong place.

### Placement rules

- frontend app-local performance configuration belongs in `frontend/apps/skriptoteket/`
  - example: `lighthouserc.json`
  - example: app-local `package.json` scripts
- browser automation entrypoints belong in `scripts/`
  - example: `scripts/playwright_route_perf_inventory.py`
- shared Playwright helpers belong in underscored modules under `scripts/`
  - example: `scripts/_playwright_perf.py`
- repo operator wrappers belong in `pyproject.toml`
  - example: `fe-perf-lhci`, `fe-perf-bundle`, `ui-perf-inventory`
- operator documentation belongs in versioned docs
  - example: `docs/runbooks/runbook-frontend-performance-baseline.md`
- generated outputs belong under `.artifacts/frontend-performance/`

### Explicit non-placement rules

- do not add route-audit logic inside Vue views or route components
- do not add bundle-analysis code under `src/skriptoteket/` backend packages
- do not introduce a generic repo-root `scripts/perf/` tree unless the helper is truly shared across
  multiple apps
- do not hide large amounts of logic in `vite.config.ts`; keep config wiring thin and move any
  non-trivial Node-side logic into a small app-local script if needed

### Modularization rules

- keep each new file under the repo’s normal size budget; treat `400–500` LOC as a hard ceiling
- keep the Playwright entrypoint thin:
  - argument parsing
  - browser/context lifecycle
  - route loop orchestration
  - artifact write delegation
- move request normalization, duplicate detection, and summary derivation into
  `scripts/_playwright_perf.py`
- keep LHCI config declarative in `lighthouserc.json`; do not embed large audit policy logic in
  ad hoc wrapper scripts
- keep bundle visualizer wiring as a narrow Vite/plugin seam; do not mix artifact post-processing
  into the core build config unless it stays minimal

### Future-proof placement

If a later slice adds real-user `web-vitals` instrumentation, place it in a dedicated frontend
module such as `frontend/apps/skriptoteket/src/observability/performance/` and keep components and
views as thin consumers. Do not wire measurement logic directly inside route views.

## Non-goals

- Auditing the full story route matrix in this first slice
- Fixing discovered route-load regressions in the same PR
- Adding permanent real-user monitoring or analytics in this slice
- Introducing a second browser automation stack if the existing Playwright lane is sufficient
- Hand-authoring custom bundle parsers or custom Lighthouse score calculators

## Recommended standard tooling

### Adopt in this slice

- `@lhci/cli`
  - Use as the canonical Lighthouse/Lab runner and future regression gate.
  - Preferred over handrolled wrappers because it already supports repeated runs, assertions, and
    budget-style checks.
- `rollup-plugin-visualizer`
  - Use to generate bundle/chunk ownership reports from the existing Vite build.
  - Preferred over custom parsing of Vite manifest output.
- existing repo Playwright Python lane
  - Reuse the current Playwright stack and helper modules for authenticated route navigation,
    login bootstrap, and request/response inventory capture.
  - Do not add Puppeteer in this first slice unless review explicitly decides that automated
    authenticated Lighthouse flows are worth a second browser harness.

### Explicitly optional, not required in this slice

- `web-vitals`
  - Useful later if the team wants lightweight real-user metric capture.
  - Prefer the standard build by default; use `web-vitals/attribution` only if the follow-up slice
    actually needs element-level diagnostic attribution in production-like traffic.
  - Keep it out of this first slice unless the PR explicitly starts collecting field telemetry.

### Avoid in this slice

- `puppeteer`
  - Do not add a second browser automation stack just to run authenticated Lighthouse flows.
  - If a later slice truly needs Lighthouse user-flow automation for authenticated routes, review it
    as a separate dependency decision.
- custom bundle parsers
  - The visualizer plugin and Vite manifest already cover the bundle-ownership need more honestly
    than a bespoke parser.
- custom “one score” performance scripts
  - Keep raw tool outputs and route summaries legible instead of inventing a repo-specific scoring
    abstraction too early.

## Pilot route seed set

Keep this first slice intentionally narrow. Capture baseline artifacts for:

| Route | User state | Why this route is in the pilot |
|------|------|------|
| `/` | signed out | cheapest shell and public baseline |
| `/browse` | signed in | catalog data-loading and filter payload baseline |
| `/admin/tools/:toolId` | contributor/admin | heavy editor/admin route and chunk boundary baseline |

The rest of the story route matrix should remain follow-up work.

## Implementation plan

1. Add the standard perf-audit dependencies in the frontend workspace with clear ownership:
   - `@lhci/cli`
   - `rollup-plugin-visualizer`
2. Add a small, documented command surface for the audit lane.
   - Prefer repo-approved wrappers or scripts over raw one-off shell commands.
   - Keep commands explicit about output under `.artifacts/`.
3. Add LHCI configuration for local production-style runs against the built SPA.
   - Start with the public route baseline.
   - If authenticated Lighthouse automation proves awkward, keep Lighthouse CI focused on the
     routes it can run cleanly in this slice and let Playwright own authenticated request inventory.
4. Add a Playwright-based route inventory script that reuses existing auth/bootstrap helpers and
   captures per-route request/response evidence for the pilot routes.
   - Record request URL, method, status, initiator classification, response size when available,
     and duplication counts.
   - Keep the output as JSON and compact human-readable summaries under `.artifacts/`.
5. Add bundle/chunk reporting off the normal Vite production build using the visualizer plugin.
6. Write one small reference or README fragment for how to run the lane and how to read the pilot
   artifacts.
7. Record the exact commands and artifact paths in `.agents/handoff.md`.

## Concrete command surface

The implementation should use the existing split between `pdm` repo wrappers and app-local
`package.json` scripts.

### `frontend/apps/skriptoteket/package.json`

Add these app-local scripts:

- `perf:lhci`
  - `lhci autorun --config=./lighthouserc.json`
- `perf:bundle`
  - `VITE_BUNDLE_VISUALIZER=1 vite build`

Keep `build` unchanged. `perf:bundle` should be a variant of the normal production build, not a
second build system.

### `pyproject.toml`

Add these repo-facing wrappers:

- `fe-perf-lhci`
  - working dir: `frontend`
  - command: `pnpm --filter @skriptoteket/spa perf:lhci`
- `fe-perf-bundle`
  - working dir: `frontend`
  - command: `pnpm --filter @skriptoteket/spa perf:bundle`
- `ui-perf-inventory`
  - command: `python -m scripts.playwright_route_perf_inventory`

Do not add one giant “do everything” composite script yet. The first slice should keep each lane
individually runnable and debuggable.

### Canonical operator sequence for the pilot

The implementation should document this exact happy-path flow:

1. `pdm run fe-build`
2. `pdm run fe-perf-bundle`
3. `pdm run ui-perf-inventory --base-url http://127.0.0.1:8000`
4. `pdm run fe-perf-lhci`

If the local operator wants to inspect the HMR lane for debugging, that remains separate and should
not replace the production-style baseline sequence above.

## Proposed file layout

Use the following concrete file/layout plan.

### Frontend app files

- `frontend/apps/skriptoteket/package.json`
  - add `perf:lhci` and `perf:bundle`
- `frontend/apps/skriptoteket/lighthouserc.json`
  - app-scoped LHCI config
  - start with the public pilot route only
- `frontend/apps/skriptoteket/vite.config.ts`
  - conditionally enable `rollup-plugin-visualizer` when `VITE_BUNDLE_VISUALIZER=1`
  - write the visualizer output into the repo’s `.artifacts/` tree, not inside the app folder

### Repo Playwright files

- `scripts/playwright_route_perf_inventory.py`
  - main entrypoint for authenticated/public route inventory
  - reuse `scripts._playwright_config.get_config()`
  - reuse `scripts._playwright_auth.login_to_browse(...)`
  - reuse `scripts._playwright_browser.launch_chromium(...)`
- `scripts/_playwright_perf.py`
  - small helper module for:
    - route matrix definitions
    - request normalization
    - duplication detection
    - artifact writing

Keep the entrypoint script as the proof surface and the underscored module as the shared helper
surface, following the repo’s current Playwright taxonomy.

### Docs file

- `docs/runbooks/runbook-frontend-performance-baseline.md`
  - short operator runbook for:
    - required local runtime
    - pilot commands
    - artifact locations
    - how to interpret route summaries

## Artifact directory layout

Write all outputs under one root:

- `.artifacts/frontend-performance/`

Inside it, use this concrete structure:

- `.artifacts/frontend-performance/lhci/`
  - raw LHCI output and HTML reports
- `.artifacts/frontend-performance/bundle/`
  - visualizer HTML and any machine-readable bundle stats emitted by the plugin
- `.artifacts/frontend-performance/routes/summary.json`
  - top-level pilot route summary
- `.artifacts/frontend-performance/routes/public-home.json`
- `.artifacts/frontend-performance/routes/browse-authenticated.json`
- `.artifacts/frontend-performance/routes/admin-tool-editor.json`
  - per-route request ledgers and derived summaries

Do not scatter artifacts across unrelated script folders for this lane.

## Ownership map

To keep the implementation DRY and structurally honest, use this ownership split:

- `frontend/apps/skriptoteket/package.json`
  - owns app-local Node command aliases only
- `frontend/apps/skriptoteket/lighthouserc.json`
  - owns LHCI route targets, assertions, and output shape
- `frontend/apps/skriptoteket/vite.config.ts`
  - owns the visualizer plugin hook only
- `scripts/playwright_route_perf_inventory.py`
  - owns route execution and artifact session orchestration
- `scripts/_playwright_perf.py`
  - owns route descriptors, request-ledger shaping, duplicate classification, and summary building
- `pyproject.toml`
  - owns repo-facing wrapper commands only
- `docs/runbooks/runbook-frontend-performance-baseline.md`
  - owns operator instructions and artifact-reading guidance

No single file in this slice should simultaneously own command wiring, browser orchestration,
request classification, and docs.

## Artifact contract

This slice should produce, at minimum:

- Lighthouse/LHCI report output for the public pilot route
- Playwright request inventory JSON for all pilot routes
- a compact per-route summary showing:
  - request count
  - duplicate request count
  - total transferred bytes
  - JS/CSS/API byte breakdown where measurable
  - candidate `over-fetch`, `over-load`, and `over-chat` findings
- bundle visualizer output for the corresponding production build

### Request-ledger shape

The Playwright ledger should stay simple and implementation-friendly. Each request record should try
to capture:

- route id
- URL
- method
- resource type when available
- status
- response content type
- transferred size when available from Playwright response headers or body length heuristics
- whether the request is classified as:
  - `required-shared-bootstrap`
  - `required-route-owned`
  - `suspicious-duplicate`
  - `suspicious-cross-route`
  - `deferable-or-avoidable`

Derived per-route summaries should include duplicate counts and grouped byte totals, but the raw
ledger should remain inspectable JSON.

## Test plan

- `pdm run docs-validate`
- `pdm run fe-build`
- `pdm run fe-perf-bundle`
- `pdm run ui-perf-inventory --base-url http://127.0.0.1:8000`
- `pdm run fe-perf-lhci`
- verify bundle visualizer output is generated from the same production build surface
- perform one live spot-check that the authenticated pilot route proof still uses the canonical
  local login/bootstrap lane and records the exact artifact paths in `.agents/handoff.md`

## Rollback plan

- Remove the audit dependencies, wrapper commands, and artifact-generation scripts together if the
  first measurement lane proves too noisy or mismatched to the story.
- Keep the story and review docs; this PR only defines and proves the first implementation slice.
- Do not keep partial custom collectors if the standard toolchain is rejected.

## References

- Story parent: [ST-11-25](../stories/story-11-25-spa-route-load-performance-and-network-isolation-audit.md)
- Epic parent: [EPIC-11](../epics/epic-11-full-vue-spa-migration.md)
- Review gate:
  [REV-ST-11-25](../reviews/review-st-11-25-spa-route-load-performance-and-network-isolation-audit.md)
- SPA hosting baseline: [ST-11-03](../stories/story-11-03-spa-hosting-fastapi-integration.md)
- Auth/bootstrap baseline: [ST-11-05](../stories/story-11-05-auth-flow-and-route-guards.md)

## Tooling notes

These recommendations are grounded in the current official tooling docs:

- Lighthouse overview:
  [developer.chrome.com/docs/lighthouse/overview](https://developer.chrome.com/docs/lighthouse/overview)
- Lighthouse CI:
  [github.com/GoogleChrome/lighthouse-ci](https://github.com/GoogleChrome/lighthouse-ci)
- web-vitals:
  [github.com/GoogleChrome/web-vitals](https://github.com/GoogleChrome/web-vitals)
- Playwright page/network events:
  [playwright.dev/docs/api/class-page](https://playwright.dev/docs/api/class-page)
- Rollup plugin visualizer:
  [github.com/btd/rollup-plugin-visualizer](https://github.com/btd/rollup-plugin-visualizer)
