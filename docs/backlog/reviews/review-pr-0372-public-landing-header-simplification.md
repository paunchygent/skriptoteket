---
type: review
id: REV-PR-0372
title: "Review: PR-0372 public landing header simplification"
status: approved
owners: "agents"
created: 2026-06-19
updated: 2026-06-19
reviewer: "codex-independent-reviewer"
prs:
  - PR-0372
links:
  - ST-37-04
  - EPIC-37
  - PR-0370
  - PR-0371
  - REV-PR-0371
  - REF-public-landing-copy-lock
  - REF-review-workflow
---

## TL;DR

Approved. The prior docs-authority blocker is resolved, the runtime patch stays
within scope, the focused landing tests are truthful, and the retained desktop
and mobile screenshots show the simplified public header contract on the live
page.

## Problem Statement

This review checks whether `PR-0372` is backed by a truthful docs-as-code spine
before any public landing header implementation begins.

## Proposed Solution

Approve only if the new public-header slice is not just locally well-written,
but also reflected accurately in the parent `ST-37-04` authority chain so the
repo does not advertise the wrong remaining work.

## Artifacts to Review

| File | Focus | Time |
|------|-------|------|
| `docs/backlog/prs/pr-0372-st-37-04-public-landing-header-simplification.md` | Scope, acceptance criteria, and proof plan | 12 min |
| `docs/backlog/stories/story-37-04-app-presentation-decomposition-and-naming-reset.md` | Parent story sequencing and notes | 8 min |
| `docs/reference/ref-public-landing-copy-lock.md` | Header copy lock and public CTA ownership | 8 min |
| `docs/index.md` | Durable docs discoverability | 5 min |
| `docs/backlog/epics/epic-37-backlog-product-direction-inventory-and-app-surface-realignment.md` | Parent epic implementation summary truth | 8 min |
| `docs/backlog/reviews/review-pr-0371-public-landing-authenticated-app-preview-implementation.md` | Immediate predecessor close-out status | 5 min |

**Total estimated time:** ~46 minutes

## Key Decisions

| Decision | Rationale | Approve? |
|----------|-----------|----------|
| Remove the signed-out header `Klassrumskartan` link because the hero owns that CTA. | Matches the approved landing hierarchy and avoids duplicate CTA competition. | [x] |
| Keep brand, `Logga in`, and `Hjälp` on one row on small screens, with `Logga in` and `Hjälp` using the same visual treatment. | This is the user-approved header simplification contract. | [x] |
| Keep the parent `EPIC-37` summary aligned with the current `ST-37-04` slice stack. | Parent docs must not contradict the story and docs doorway about what is done and what remains. | [x] |

## Review Checklist

- [x] The PR scope is bounded to the signed-out public landing header.
- [x] The acceptance criteria encode the approved CTA removal and mobile one-row action treatment.
- [x] The copy lock and story notes both support the intended header behavior.
- [x] The parent epic summary truthfully reflects the current `ST-37-04` slice stack.

## Review Feedback

**Reviewer:** `codex-independent-reviewer`
**Date:** `2026-06-19`
**Verdict:** `approved`

### Findings

No findings.

Re-review pass notes:

- [epic-37-backlog-product-direction-inventory-and-app-surface-realignment.md](/Users/olofs_mba/Documents/Repos/CascadeProjects/windsurf-project/docs/backlog/epics/epic-37-backlog-product-direction-inventory-and-app-surface-realignment.md:123) now records the public-landing follow-up slices `PR-0370` through `PR-0372` alongside the remaining `PR-0366` through `PR-0369` work.
- [story-37-04-app-presentation-decomposition-and-naming-reset.md](/Users/olofs_mba/Documents/Repos/CascadeProjects/windsurf-project/docs/backlog/stories/story-37-04-app-presentation-decomposition-and-naming-reset.md:38) and [docs/index.md](/Users/olofs_mba/Documents/Repos/CascadeProjects/windsurf-project/docs/index.md:95) now agree with the parent epic summary about the current `ST-37-04` slice stack.
- [pr-0372-st-37-04-public-landing-header-simplification.md](/Users/olofs_mba/Documents/Repos/CascadeProjects/windsurf-project/docs/backlog/prs/pr-0372-st-37-04-public-landing-header-simplification.md:15) remains scoped correctly to the approved public-header simplification decisions.

### Required Changes

None.

### Suggestions (Optional)

None.

### Decision Approvals

- [x] Approve removing the duplicate public header `Klassrumskartan` link
- [x] Approve the one-row small-screen header with matched `Logga in` / `Hjälp` treatment
- [x] Approve the current parent authority chain as implementation-ready

### Validation Reviewed

- Reviewer inspected the scoped working-tree docs with `git diff -- ...`.
- User-reported blocker-fix gates were reviewed: `pdm run docs-validate` and `git diff --check`.
- Repo validation after recording this retained review is listed below in `## Changes Made`.

### Post-Implementation Review Pass - 2026-06-19

Decision: `approved`.

#### Scope Reviewed

- Governing docs and retained records:
  `AGENTS.md`,
  `docs/backlog/prs/pr-0372-st-37-04-public-landing-header-simplification.md`,
  `docs/backlog/stories/story-37-04-app-presentation-decomposition-and-naming-reset.md`,
  `docs/backlog/epics/epic-37-backlog-product-direction-inventory-and-app-surface-realignment.md`,
  `docs/reference/ref-public-landing-copy-lock.md`,
  `docs/index.md`,
  `.codex/handoff.md`,
  and the prior retained review state in `REV-PR-0372`.
- Runtime patch:
  `frontend/apps/skriptoteket/src/components/layout/LandingLayout.vue` and
  `frontend/apps/skriptoteket/src/components/layout/LandingLayout.spec.ts`.
- Supporting proof surface:
  reviewer-ran focused Vitest, the retained public screenshots under
  `.artifacts/pr-0372-public-landing-header-simplification/`, and the reported
  green validation lane.

#### Findings

No findings.

The approved state is grounded in the scoped implementation and proof:

- `frontend/apps/skriptoteket/src/components/layout/LandingLayout.vue:33`
  removes the public `Klassrumskartan` header link and keeps the brand plus
  `Logga in` / `Hjälp` actions only.
- `frontend/apps/skriptoteket/src/components/layout/LandingLayout.vue:154`
  restyles the embedded help button to match the login link treatment without
  introducing a hamburger or extra nav surface.
- `frontend/apps/skriptoteket/src/components/layout/LandingLayout.spec.ts:40`
  truthfully checks that the header no longer renders `Klassrumskartan`, still
  exposes `Logga in` and `Hjälp`, and preserves the shared HuleEdu continuation
  URL.
- Reviewer inspection of
  `.artifacts/pr-0372-public-landing-header-simplification/public-landing-desktop.png`
  and
  `.artifacts/pr-0372-public-landing-header-simplification/public-landing-mobile.png`
  confirms the public header contains only the brand, `Logga in`, and `Hjälp`,
  and that the small-screen top row remains intact.

#### Validation Commands And Outcomes

Reviewer-ran checks:

```bash
pdm run fe-test -- --run src/components/layout/AuthSidebar.spec.ts src/components/layout/AuthLayout.spec.ts src/App.spec.ts src/components/layout/LandingLayout.spec.ts src/views/HomeView.spec.ts
```

Results:

- Focused Vitest rerun: passed with 17 tests, including the two scoped
  `LandingLayout` tests.

Additional evidence reviewed:

- Worker-reported gates:
  `pdm run fe-type-check`
  `pdm run fe-lint`
  `pdm run docs-validate`
  `pdm run handoff-validate`
  `git diff --check`
- Retained live public-route screenshots:
  `.artifacts/pr-0372-public-landing-header-simplification/public-landing-desktop.png`
  and
  `.artifacts/pr-0372-public-landing-header-simplification/public-landing-mobile.png`

Residual risk, not a blocker: I relied on the reported `fe-type-check` and
`fe-lint` passes rather than rerunning both to completion myself during this
review pass.

## Changes Made

| Change | Artifact | Description |
|--------|----------|-------------|
| 1 | `REV-PR-0372` | Created the retained pre-implementation review record and requested changes on the stale parent epic authority chain. |
| 2 | `REV-PR-0372` | Re-reviewed the parent-spine fix, found no remaining docs-authority blockers in scope, and updated the retained decision to `approved`. |
| 3 | `REV-PR-0372` | Performed the post-implementation ruthless review, verified the runtime header change against focused tests and retained public proof, and kept the retained decision at `approved`. |
