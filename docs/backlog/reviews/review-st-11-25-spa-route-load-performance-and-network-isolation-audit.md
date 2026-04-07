---
type: review
id: REV-ST-11-25
title: "Review: ST-11-25 SPA route-load performance and network-isolation audit"
status: pending
owners: "agents"
created: 2026-04-08
updated: 2026-04-08
reviewer: "lead-developer"
stories:
  - ST-11-25
links:
  - EPIC-11
  - ADR-0027
  - ADR-0028
  - ADR-0030
---

## TL;DR

`ST-11-25` proposes a repo-native frontend performance audit plan for the Vue/Vite
SPA. The goal is not a generic Lighthouse-only scorecard. The package defines a
representative route matrix, a production-style measurement lane, and a
repeatable evidence format that can distinguish acceptable shared bootstrap cost
from route-specific waste such as duplicate API calls, cross-route chatter, and
unnecessary code or asset loads.

## Problem Statement

Skriptoteket currently has enough SPA surface area that route-load regressions
can hide in several places:

- authenticated bootstrap and CSRF setup
- dashboard fan-out fetches
- catalog/filter payloads
- curated-app host bootstrap
- heavy editor/admin route chunks

Without one agreed audit shape, performance analysis becomes informal and hard
to compare across routes. That makes it difficult to decide whether a route is
actually noisy, which requests are justified, and what the first cleanup slice
should be.

## Proposed Solution

Approve `ST-11-25` as the planning gate for a structured route-load audit:

1. measure a fixed representative route matrix
2. use the production-style built SPA for baseline numbers
3. record request inventory, payload size, chunk ownership, and Web Vitals trace
   notes per route
4. classify findings into `over-fetch`, `over-load`, and `over-chat`
5. derive route budgets only after the first measured baseline exists

## Artifacts to Review

| File | Focus | Time |
|------|-------|------|
| `docs/backlog/stories/story-11-25-spa-route-load-performance-and-network-isolation-audit.md` | Route matrix, evidence package, and scope boundaries | 8 min |
| `docs/backlog/epics/epic-11-full-vue-spa-migration.md` | Epic fit and post-cutover follow-up placement | 4 min |
| `frontend/apps/skriptoteket/src/router/routes.ts` | Representative route matrix coverage | 4 min |
| `frontend/apps/skriptoteket/src/stores/auth.ts` | Shared bootstrap/auth cost questions the audit must classify correctly | 4 min |
| `frontend/apps/skriptoteket/src/composables/home/useHomeDashboard.ts` | Dashboard fan-out baseline candidate | 4 min |
| `frontend/apps/skriptoteket/src/composables/useCatalogFilters.ts` | Catalog fetch/payload boundary candidate | 4 min |
| `frontend/apps/skriptoteket/src/views/useCuratedAppHost.ts` | Curated-app host bootstrap boundary candidate | 3 min |

**Total estimated time:** ~31 minutes

## Key Decisions

| Decision | Rationale | Approve? |
|----------|-----------|----------|
| Use a production-style built SPA as the baseline runtime | Avoids misleading HMR and dev-only overhead in reported numbers | [ ] |
| Audit a fixed representative route matrix instead of chasing the whole app at once | Keeps the first pass comparable and reviewable | [ ] |
| Separate shared bootstrap traffic from route-owned waste | Prevents correct auth/session costs from being mislabeled as route regressions | [ ] |
| Record evidence per route instead of relying on one global score | Makes cleanup slices concrete and bounded | [ ] |
| Derive budgets only after the baseline exists | Avoids arbitrary thresholds and premature optimization theater | [ ] |

## Review Checklist

- [ ] Scope is bounded to the audit contract rather than speculative implementation
- [ ] The route matrix is representative without being too broad for a first pass
- [ ] The evidence package is concrete enough to drive later remediation slices
- [ ] Shared bootstrap versus route-owned traffic is distinguished clearly
- [ ] Budget-setting is sequenced after measurement, not before it

## Review Feedback

**Reviewer:** `lead-developer`
**Date:** `2026-04-08`
**Verdict:** pending

### Required Changes

- Pending review.

### Suggestions (Optional)

- Pending review.

### Decision Approvals

- [ ] Use a production-style built SPA as the baseline runtime
- [ ] Audit a fixed representative route matrix instead of chasing the whole app at once
- [ ] Separate shared bootstrap traffic from route-owned waste
- [ ] Record evidence per route instead of relying on one global score
- [ ] Derive budgets only after the baseline exists

## Changes Made

| Change | Artifact | Description |
|--------|----------|-------------|
| 1 | `ST-11-25` | Created the retained story package for a frontend route-load and network-isolation audit. |
| 2 | `REV-ST-11-25` | Created the story review gate so the audit contract can be approved before implementation work begins. |
