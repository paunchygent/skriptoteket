---
type: pr
id: PR-0244
title: "ST-11-25: pilot route inventory and trace baselines"
status: ready
owners: "agents"
created: 2026-04-08
updated: 2026-04-08
stories:
  - "ST-11-25"
tags: ["frontend", "performance", "playwright", "audit", "docs"]
dependencies:
  - "ST-11-25"
  - "REV-ST-11-25"
  - "PR-0241"
  - "PR-0243"
  - "ST-11-05"
acceptance_criteria:
  - "Given the pilot routes need trustworthy evidence, when this slice ships, then the repo contains a Playwright route-inventory entrypoint and a small helper module under `scripts/playwright/` that capture request ledgers, duplicate detection, and per-route summaries for the pilot route set."
  - "Given the editor route must be deterministic, when this slice ships, then the admin editor pilot route is measured through one explicit script-bank fixture (`demo-settings-test`) instead of whichever tool happens to exist."
  - "Given the parent story requires per-route trace notes, when this slice ships, then every audited pilot route produces both a request ledger and one short trace-note artifact covering LCP candidates, long-task / INP-sensitive work, and visible CLS contributors."
  - "Given Playwright artifacts must follow repo rules, when this slice ships, then the raw script outputs live under `.artifacts/playwright-route-perf-inventory/` and any shared perf index only references that directory rather than replacing it."
  - "Given this is still a pilot slice, when it ships, then it covers only the bounded pilot routes (`/`, signed-in `/browse`, seeded `/admin/tools/:toolId`) and does not claim the whole story route matrix is complete."
---

## Problem

After the tree normalization and toolchain wiring slices, the repo still needs the actual pilot
route evidence lane. That lane should be focused on authenticated/public route inventory and
per-route trace notes, not mixed with the earlier placement or dependency work.

## Goal

Add the pilot route-inventory and trace-baseline lane only.

## Non-goals

- Moving Playwright files around in this slice
- Adding LHCI or bundle-visualizer dependencies in this slice
- Expanding beyond the bounded pilot routes
- Fixing discovered performance issues in this slice

## Pilot route seed set

| Route | User state | Notes |
|------|------|------|
| `/` | signed out | public baseline |
| `/browse` | signed in | authenticated catalog baseline |
| `/admin/tools/:toolId` | contributor/admin | seeded `demo-settings-test` fixture only |

## Deterministic editor fixture

Use one canonical script-bank fixture:

- slug: `demo-settings-test`
- seed command:
  - `pdm run seed-script-bank --slug demo-settings-test --profile dev`

The route-inventory script must resolve the tool id by slug and fail clearly if the slug is absent.

## Implementation plan

1. Add `scripts/playwright/route_perf_inventory.py`.
2. Add `scripts/playwright/_perf.py`.
3. Reuse existing shared helpers from the normalized tree:
   - `scripts.playwright._config`
   - `scripts.playwright._auth`
   - `scripts.playwright._browser`
4. Add the repo wrapper:
   - `ui-perf-inventory`
5. Capture per-route request ledgers, duplicate classification, and byte summaries.
6. Capture one raw Chromium performance trace artifact per pilot route.
7. Emit one short route note per pilot route.
8. Record exact artifact paths in `.agents/handoff.md`.

## Concrete command surface

### `pyproject.toml`

- `ui-perf-inventory`
  - command: `python -m scripts.playwright.route_perf_inventory`

### Canonical operator sequence for this slice

1. `pdm run seed-script-bank --slug demo-settings-test --profile dev`
2. `pdm run ui-perf-inventory --base-url http://127.0.0.1:8000`

## Proposed file layout

- `scripts/playwright/route_perf_inventory.py`
  - thin entrypoint:
    - args
    - route loop orchestration
    - browser/context lifecycle
    - artifact session coordination
- `scripts/playwright/_perf.py`
  - helper logic:
    - route descriptors
    - request normalization
    - duplicate detection
    - trace-note shaping
    - artifact writing

## Artifact directory layout

Raw script outputs must live under:

- `.artifacts/playwright-route-perf-inventory/`

Use this shape:

- `.artifacts/playwright-route-perf-inventory/summary.json`
- `.artifacts/playwright-route-perf-inventory/routes/public-home.json`
- `.artifacts/playwright-route-perf-inventory/routes/browse-authenticated.json`
- `.artifacts/playwright-route-perf-inventory/routes/admin-tool-editor.json`
- `.artifacts/playwright-route-perf-inventory/traces/public-home.trace.json`
- `.artifacts/playwright-route-perf-inventory/traces/browse-authenticated.trace.json`
- `.artifacts/playwright-route-perf-inventory/traces/admin-tool-editor.trace.json`
- `.artifacts/playwright-route-perf-inventory/notes/public-home.md`
- `.artifacts/playwright-route-perf-inventory/notes/browse-authenticated.md`
- `.artifacts/playwright-route-perf-inventory/notes/admin-tool-editor.md`

## Artifact contract

This slice should produce, at minimum:

- request-ledger JSON for all pilot routes
- one raw Chromium trace artifact per pilot route
- one short route note per pilot route covering:
  - LCP candidates
  - long-task / INP-sensitive work
  - visible CLS contributors
- one compact top-level summary aggregating:
  - request count
  - duplicate request count
  - total transferred bytes
  - JS/CSS/API byte breakdown where measurable
  - candidate `over-fetch`, `over-load`, and `over-chat` findings

## Test plan

- `pdm run docs-validate`
- `pdm run seed-script-bank --slug demo-settings-test --profile dev`
- `pdm run ui-perf-inventory --base-url http://127.0.0.1:8000`
- verify the editor route resolves from the seeded slug, not the first available tool
- verify each pilot route has both a request ledger and a trace note artifact
- verify the raw script outputs live under `.artifacts/playwright-route-perf-inventory/`

## Rollback plan

- Remove the route-inventory entrypoint, helper module, wrapper command, and artifact references
  together if the pilot evidence lane proves too noisy or structurally wrong.

## References

- Story parent: [ST-11-25](../stories/story-11-25-spa-route-load-performance-and-network-isolation-audit.md)
- Review gate:
  [REV-ST-11-25](../reviews/review-st-11-25-spa-route-load-performance-and-network-isolation-audit.md)
- Browser automation rule:
  [075-browser-automation](../../../.agents/rules/075-browser-automation.md)
