---
type: story
id: ST-11-25
title: "SPA route-load performance and network-isolation audit"
status: ready
owners: "agents"
created: 2026-04-08
updated: 2026-04-08
epic: "EPIC-11"
dependencies:
  ["ADR-0027", "ADR-0028", "ADR-0030", "ST-11-03", "ST-11-05", "ST-11-21"]
acceptance_criteria:
  - "Given Skriptoteket now runs as one Vue/Vite SPA, when this story is executed, then the team captures a production-style baseline for a representative route matrix instead of relying on Vite/HMR timings or anecdotal spot checks."
  - "Given route-load efficiency is the concern, when a route baseline is recorded, then the evidence explicitly separates shared bootstrap traffic from route-owned fetches and identifies duplicate API calls, non-route-owned chatter, large asset downloads, and unnecessary JavaScript eagerly loaded into that route."
  - "Given future cleanup work should be reviewable, when this story is completed, then each audited route has a consistent evidence package covering request inventory, transferred bytes, bundle/chunk ownership, and Core Web Vitals-oriented trace notes rather than a single aggregate score."
  - "Given the first implementation pass should avoid premature optimization, when follow-up work is planned, then the audit output groups findings into over-fetch, over-load, and over-chat buckets and sequences concrete remediation slices from measured waste rather than intuition."
  - "Given performance budgets can drift into guesswork, when this story is reviewed, then the retained package defines how initial route budgets will be derived from the first baseline rather than inventing arbitrary thresholds before the measurement lane exists."
ui_impact: "No direct UI change; defines the audit contract for future SPA route-load and network-efficiency work."
data_impact: "No schema change."
---

## Context

The SPA already uses route-level lazy loading and several focused composables,
but Skriptoteket does not yet have one canonical way to answer basic frontend
performance questions:

- which routes are clean versus noisy during first load
- whether authenticated shells are paying repeated bootstrap costs
- whether a route pulls in code, API data, or assets that belong to some other
  surface
- whether duplicated requests or avoidable client chatter are slipping in during
  navigation or initialization

Without a retained route-audit plan, performance cleanup tends to collapse into
one-off DevTools screenshots or generic Lighthouse scores that do not explain
what to fix next.

## Audit scope

This story is about the audit contract, not the cleanup implementation.

The route baseline should cover the minimum representative matrix below.

| Route | User state | Why it belongs in the baseline |
|------|------|------|
| `/` | signed out | public landing baseline and cheapest shell |
| `/` | signed in | auth-adaptive dashboard fan-out baseline |
| `/browse` | signed in | catalog listing + filter query behavior |
| `/public/apps/classroom.group-seating-studio` | public | heavy public curated-app bootstrap |
| `/apps/classroom.group-seating-studio` | signed in | authenticated curated-app host baseline |
| `/tools/:slug/run` | signed in | tool-runtime shell + form/bootstrap behavior |
| `/admin/tools/:toolId` | contributor/admin | heavy editor/admin route and chunk boundary check |

If a reviewer wants one extra route after the baseline is working, the next most
valuable candidate is `/my-runs`.

## Measurement contract

### Runtime lane

- Capture baseline numbers against the production-style built SPA, not Vite HMR.
- Use the local dev stack only for debugging and route investigation.
- Reuse the existing bootstrap superuser for authenticated routes.

### Evidence package per route

Each audited route should produce one compact baseline record containing:

- initial document + static asset request inventory
- API request inventory during first meaningful render
- total transferred bytes
- bytes grouped by HTML, JS, CSS, images/fonts, and API payloads
- duplicate request detection
- route-owned versus shared-bootstrap request classification
- bundle/chunk notes explaining which JS arrived for that route
- trace notes for LCP, INP-sensitive long tasks, and CLS contributors

### Noise classification

Every finding should land in one of these buckets:

- `over-fetch`: the route requests more server data than it needs
- `over-load`: the route downloads too much code or too many assets
- `over-chat`: the route emits duplicate, repeated, or low-value requests

The audit should also mark whether a request is:

- `required-shared-bootstrap`
- `required-route-owned`
- `suspicious-duplicate`
- `suspicious-cross-route`
- `deferable-or-avoidable`

## Reviewable rubric

The baseline should not reduce a route to one score. Review should instead ask:

1. Is the route functionally isolated, or is it loading code/data owned by
   another route?
2. Are repeated or duplicate requests visible during initial render?
3. Are authenticated routes paying predictable shared bootstrap cost once, or
   re-paying it in avoidable ways?
4. Does the route ship more JavaScript or API data than the visible UI justifies?
5. Can the evidence support a narrow remediation slice without guesswork?

The first audit pass should record measured numbers and qualitative findings.
Only after that baseline exists should the team freeze route budgets and
enforcement thresholds.

## Planned implementation slices

- Slice 1: add the measurement harness and baseline capture workflow
- Slice 2: inventory and classify the first route-matrix results
- Slice 3: fix the highest-value over-fetch and over-chat findings
- Slice 4: tighten chunking, lazy-load boundaries, and route budgets

### Planned PR slices

- [PR-0241: ST-11-25 Playwright tree normalization under scripts/playwright](../prs/pr-0241-st-11-25-playwright-tree-normalization.md)
- [PR-0243: ST-11-25 LHCI and bundle-visualizer toolchain wiring](../prs/pr-0243-st-11-25-lhci-and-bundle-visualizer-toolchain.md)
- [PR-0244: ST-11-25 pilot route inventory and trace baselines](../prs/pr-0244-st-11-25-pilot-route-inventory-and-trace-baselines.md)

## Verification expectation

- `pdm run docs-validate`
- reviewer approval on the retained story review record before implementation
- when implementation eventually begins, record the exact measurement commands,
  artifacts, and live verification notes in `.codex/handoff.md`

## References

- Epic parent: [EPIC-11](../epics/epic-11-full-vue-spa-migration.md)
- SPA hosting and route fallback: [ST-11-03](story-11-03-spa-hosting-fastapi-integration.md)
- Auth bootstrap and route guards: [ST-11-05](story-11-05-auth-flow-and-route-guards.md)
- Unified landing shell baseline: [ST-11-21](story-11-21-unified-landing-page.md)
- Frontend transition reference:
  [REF-frontend-transition-continuity-v1](../../reference/ref-frontend-transition-continuity-v1.md)
