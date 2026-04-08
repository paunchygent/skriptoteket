---
type: pr
id: PR-0243
title: "ST-11-25: LHCI and bundle-visualizer toolchain wiring"
status: ready
owners: "agents"
created: 2026-04-08
updated: 2026-04-08
stories:
  - "ST-11-25"
tags: ["frontend", "performance", "lighthouse", "bundles", "docs"]
dependencies:
  - "ST-11-25"
  - "REV-ST-11-25"
  - "PR-0241"
  - "ST-11-03"
acceptance_criteria:
  - "Given Skriptoteket needs a standard lab-audit lane, when this slice ships, then `@lhci/cli` is wired as the canonical LHCI runner and `rollup-plugin-visualizer` is wired as the canonical bundle-ownership reporter."
  - "Given the repo should avoid handrolled measurement code, when this slice ships, then the frontend app exposes narrow app-local scripts and the repo exposes narrow `pdm` wrappers instead of a custom performance framework."
  - "Given the LHCI lane must be executable from a clean local checkout, when this slice ships, then `lighthouserc.json` explicitly defines the collect URL, server bootstrap command, ready pattern, run count, and filesystem output path."
  - "Given this slice is toolchain-only, when it ships, then it proves `fe-perf-bundle` and `fe-perf-lhci` work for the public route baseline without also introducing authenticated route-inventory logic."
  - "Given field telemetry is not part of this first wiring pass, when dependency guidance is documented, then `web-vitals` remains optional follow-on work and is not added in this slice."
---

## Problem

The repo has no standard lab-audit lane yet. Without a focused wiring slice, later implementation
could mix configuration, bundle inspection, and browser inventory logic into one hard-to-review PR.

## Goal

Add only the standard measurement toolchain and its command surface:

- LHCI for lab audits
- Rollup/Vite visualizer for chunk ownership
- one runbook and wrapper surface that makes both lanes discoverable

## Non-goals

- Adding the Playwright route-performance inventory script in this slice
- Capturing authenticated route baselines in this slice
- Fixing discovered performance issues in this slice

## Implementation plan

1. Add frontend dependencies:
   - `@lhci/cli`
   - `rollup-plugin-visualizer`
2. Add app-local scripts in `frontend/apps/skriptoteket/package.json`:
   - `perf:lhci`
   - `perf:bundle`
3. Add `frontend/apps/skriptoteket/lighthouserc.json`.
4. Add a minimal Vite/plugin hook in `frontend/apps/skriptoteket/vite.config.ts` gated by
   `VITE_BUNDLE_VISUALIZER=1`.
5. Add repo-facing wrappers in `pyproject.toml`:
   - `fe-perf-lhci`
   - `fe-perf-bundle`
6. Add `docs/runbooks/runbook-frontend-performance-baseline.md` with operator instructions.
7. Record the exact commands and artifact paths in `.agents/handoff.md`.

## Required LHCI config shape

`frontend/apps/skriptoteket/lighthouserc.json` must make the lane executable after `pdm run fe-build`.

Required fields:

- `ci.collect.url`
  - start with `http://127.0.0.1:8000/`
- `ci.collect.startServerCommand`
  - `pdm run serve`
- `ci.collect.startServerReadyPattern`
  - match the normal Uvicorn startup log
- `ci.collect.startServerReadyTimeout`
  - explicit, not implicit
- `ci.collect.numberOfRuns`
  - explicit pilot baseline run count
- `ci.upload.target`
  - `filesystem`
- `ci.upload.outputDir`
  - `.artifacts/frontend-performance/lhci/` (relative path resolved correctly from the app dir)

This slice should document clearly that LHCI owns its own serving step; the operator should not need
to guess whether a separate backend process must already be running.

## Concrete command surface

### `frontend/apps/skriptoteket/package.json`

- `perf:lhci`
  - `lhci autorun --config=./lighthouserc.json`
- `perf:bundle`
  - `VITE_BUNDLE_VISUALIZER=1 vite build`

### `pyproject.toml`

- `fe-perf-lhci`
  - working dir: `frontend`
  - command: `pnpm --filter @skriptoteket/spa perf:lhci`
- `fe-perf-bundle`
  - working dir: `frontend`
  - command: `pnpm --filter @skriptoteket/spa perf:bundle`

## Artifact directory layout

- `.artifacts/frontend-performance/lhci/`
  - raw LHCI output and HTML reports
- `.artifacts/frontend-performance/bundle/`
  - visualizer HTML and any machine-readable bundle stats emitted by the plugin

## Test plan

- `pdm run docs-validate`
- `pdm run fe-build`
- `pdm run fe-perf-bundle`
- `pdm run fe-perf-lhci`
- verify bundle visualizer output is generated from the same production build
- verify LHCI succeeds from a clean local checkout after `pdm run fe-build` without ad hoc serving
  setup

## Rollback plan

- Remove the added dependencies, wrappers, config file, and runbook together if the toolchain
  choice is rejected.

## References

- Story parent: [ST-11-25](../stories/story-11-25-spa-route-load-performance-and-network-isolation-audit.md)
- Review gate:
  [REV-ST-11-25](../reviews/review-st-11-25-spa-route-load-performance-and-network-isolation-audit.md)
- SPA hosting baseline: [ST-11-03](../stories/story-11-03-spa-hosting-fastapi-integration.md)
