---
type: review
id: REV-PR-0365
title: "Review: PR-0365 authenticated shell navigation realignment"
status: changes_requested
owners: "agents"
created: 2026-06-19
updated: 2026-06-19
reviewer: "codex-independent-reviewer"
prs:
  - PR-0365
links:
  - ST-37-03
  - EPIC-37
  - PR-0361
  - PR-0362
  - PR-0363
  - PR-0364
  - REV-PR-0364
  - REF-service-shell-ux-realignment-plan-v1
  - REF-app-presentation-decomposition-and-naming-plan-v1
  - REF-review-workflow
---

## TL;DR

Pre-implementation authority was approved, but the post-implementation review is
`changes_requested`. The shipped sidebar code and focused tests line up with the
governed navigation order, yet the slice still lacks the required truthful
protected browser proof through the HuleEdu browser-session ceremony for the
authenticated sidebar and mobile drawer.

## Problem Statement

This review checks whether `PR-0365` is a truthful, discoverable, and
implementation-ready authority package for authenticated shell navigation
realignment before any production Vue work begins.

## Proposed Solution

Approve only if the review target is surfaced through the normal docs doorway,
its dependency chain truthfully reflects the completed `PR-0364` slice it builds
on, and its frontend proof plan still covers the route-visible shell behaviors
it claims to protect.

## Artifacts to Review

| File | Focus | Time |
|------|-------|------|
| `docs/backlog/prs/pr-0365-st-37-03-authenticated-shell-navigation-realignment.md` | Scope, acceptance criteria, review gate, and proof plan | 15 min |
| `docs/backlog/stories/story-37-03-service-shell-and-dashboard-ux-realignment.md` | Parent story state and dependency truth | 8 min |
| `docs/backlog/epics/epic-37-backlog-product-direction-inventory-and-app-surface-realignment.md` | Epic implementation summary consistency | 8 min |
| `docs/index.md` | Durable docs discoverability | 5 min |
| `docs/reference/ref-service-shell-ux-realignment-plan-v1.md` | Governing shell sequence and proof expectations | 10 min |
| `docs/reference/ref-app-presentation-decomposition-and-naming-plan-v1.md` | Lane naming and route-visible stop conditions | 8 min |
| `docs/backlog/reviews/review-pr-0364-authenticated-home-work-apps-surface.md` | Dependency close-out status | 5 min |

**Total estimated time:** ~59 minutes

## Key Decisions

| Decision | Rationale | Approve? |
|----------|-----------|----------|
| Lead authenticated navigation with `Klassrumskartan`, `Provhantering`, `Ljudtranskribering`, and contributor-only `Kodredigerare`, with no visible group labels. | Matches the approved product direction and keeps `Document Converter` out of runtime navigation until a truthful route exists. | [x] |
| Make `Föreslå verktyg` available to all signed-in users. | The user explicitly widened this surface beyond contributor-only gating. | [x] |
| Surface `PR-0365` through the normal docs doorway and truthful parent backlog chain before implementation. | This repo requires `docs/index.md` plus parent backlog records to remain the discoverable authority. | [x] |
| Keep the route-visible proof plan aligned with sidebar ordering and shell-level focus/immersive/breakpoint behavior. | Test truthfulness matters because the slice claims protection for more than one component boundary. | [x] |

## Review Checklist

- [x] The PR scope stays on authenticated shell navigation and does not invent new routes or a fake `Dokumentkonvertering` entry.
- [x] The acceptance criteria reflect the approved app-lane order, no-label rule, and widened `Föreslå verktyg` access.
- [x] The docs doorway and parent backlog chain truthfully surface the next implementation slice and its completed dependency.
- [x] The proof plan stays aligned with the route-visible behaviors named in the governing plan and acceptance criteria.

## Review Feedback

**Reviewer:** `codex-independent-reviewer`
**Date:** `2026-06-19`
**Verdict:** `changes_requested`

### Findings

No findings.

Re-review pass notes:

- [docs/index.md](/Users/olofs_mba/Documents/Repos/CascadeProjects/windsurf-project/docs/index.md:89) now exposes both `PR-0365` and `REV-PR-0365` in the `EPIC-37` cluster.
- [story-37-03-service-shell-and-dashboard-ux-realignment.md](/Users/olofs_mba/Documents/Repos/CascadeProjects/windsurf-project/docs/backlog/stories/story-37-03-service-shell-and-dashboard-ux-realignment.md:36) now marks `PR-0364` done and describes `PR-0365` as the remaining open shell slice.
- [epic-37-backlog-product-direction-inventory-and-app-surface-realignment.md](/Users/olofs_mba/Documents/Repos/CascadeProjects/windsurf-project/docs/backlog/epics/epic-37-backlog-product-direction-inventory-and-app-surface-realignment.md:132) now records `PR-0364` done/approved and keeps the epic summary consistent with the current slice sequence.
- [pr-0365-st-37-03-authenticated-shell-navigation-realignment.md](/Users/olofs_mba/Documents/Repos/CascadeProjects/windsurf-project/docs/backlog/prs/pr-0365-st-37-03-authenticated-shell-navigation-realignment.md:108) now restores the focused red/green lane to `AuthSidebar.spec.ts`, `AuthLayout.spec.ts`, and `App.spec.ts`, which matches the route-visible shell proof burden.

### Required Changes

None.

### Suggestions (Optional)

None.

### Decision Approvals

- [x] Approve the app-first navigation order and no-label rule
- [x] Approve widening `Föreslå verktyg` to all signed-in users
- [x] Approve the docs doorway and parent backlog chain as implementation-ready authority
- [x] Approve the current proof plan as sufficiently truthful for the claimed shell behaviors

### Validation Reviewed

- Reviewer inspected the working-tree docs diffs for the scoped authority package with `git diff -- ...`.
- User-reported blocker-fix gates were reviewed: `pdm run docs-validate` and `git diff --check`.
- Repo validation after recording this retained review is listed below in `## Changes Made`.

### Post-Implementation Review Pass - 2026-06-19

Decision: `changes_requested`.

#### Scope Reviewed

- Governing docs and retained records:
  `AGENTS.md`,
  `docs/backlog/prs/pr-0365-st-37-03-authenticated-shell-navigation-realignment.md`,
  `docs/backlog/stories/story-37-03-service-shell-and-dashboard-ux-realignment.md`,
  `docs/backlog/epics/epic-37-backlog-product-direction-inventory-and-app-surface-realignment.md`,
  `docs/index.md`,
  `.codex/handoff.md`,
  and the prior retained review state in `REV-PR-0365`.
- Runtime patch:
  `frontend/apps/skriptoteket/src/components/layout/AuthSidebar.vue` and
  `frontend/apps/skriptoteket/src/components/layout/AuthSidebar.spec.ts`.
- Supporting proof lane:
  `frontend/apps/skriptoteket/src/components/layout/AuthLayout.spec.ts`,
  `frontend/apps/skriptoteket/src/App.spec.ts`,
  the focused Vitest rerun, and the handoff-recorded shared-auth evidence.

#### Findings

1. Severity: `blocker`
   File reference: `.codex/handoff.md:109`, `docs/backlog/prs/pr-0365-st-37-03-authenticated-shell-navigation-realignment.md:142`
   What is wrong: the required live authenticated browser proof for the changed
   sidebar/mobile-drawer shell is still missing. The retained handoff and PR
   doc both explicitly say the protected proof remains blocked because the
   available browser surface could not complete the HuleEdu login ceremony
   truthfully.
   Why it matters: `PR-0365` changes a protected route-visible shell surface,
   and both the repo policy and the PR acceptance criteria require browser proof
   through the sanctioned HuleEdu ceremony. Without that proof, we have not
   actually validated the post-login sidebar order, contributor-only editor
   gating, mobile drawer behavior, or potential overlap/clipping on the real
   authenticated surface.
   Concrete fix: rerun the proof through a sanctioned interactive auth lane that
   can actually complete the HuleEdu ceremony against the Docker/Gateway stack,
   then retain authenticated desktop-sidebar and mobile-drawer captures and
   update the PR doc plus handoff with the exact commands, URLs, and artifact
   paths.
   Proof requirement: pass the shared-auth preflight/check lane, then complete
   retained authenticated proof for `/` or another shell-bearing protected route
   using the sanctioned HuleEdu browser-session flow, with exact evidence
   recorded alongside the existing focused test commands.

No additional code or test-truthfulness findings were found in the scoped
implementation patch:

- `frontend/apps/skriptoteket/src/components/layout/AuthSidebar.vue:55`
  leads with the governed app-lane links and keeps `Dokumentkonvertering` out
  of persistent navigation.
- `frontend/apps/skriptoteket/src/components/layout/AuthSidebar.vue:81`
  promotes `Föreslå verktyg` into the standard signed-in links for all users.
- `frontend/apps/skriptoteket/src/components/layout/AuthSidebar.spec.ts:62`
  truthfully checks the first app-lane entries, proposal visibility, no-label
  rule, and absence of `Mina körningar`.
- Reviewer-ran focused Vitest rerun passed with 17 tests across
  `AuthSidebar.spec.ts`, `AuthLayout.spec.ts`, `App.spec.ts`,
  `LandingLayout.spec.ts`, and `HomeView.spec.ts`.

#### Validation Commands And Outcomes

Reviewer-ran checks:

```bash
pdm run fe-test -- --run src/components/layout/AuthSidebar.spec.ts src/components/layout/AuthLayout.spec.ts src/App.spec.ts src/components/layout/LandingLayout.spec.ts src/views/HomeView.spec.ts
```

Results:

- Focused Vitest rerun: passed with 17 tests.

Additional evidence reviewed:

- Worker-reported gates:
  `pdm run fe-type-check`
  `pdm run fe-lint`
  `pdm run docs-validate`
  `pdm run handoff-validate`
  `git diff --check`
- The reviewer started a local `pdm run fe-type-check` rerun but interrupted it
  after it produced no completion output during the review window, so I am
  relying on the retained reported pass for that gate.

Residual risk is blocking, not optional: until the authenticated browser proof
exists, this slice cannot be approved.

## Changes Made

| Change | Artifact | Description |
|--------|----------|-------------|
| 1 | `REV-PR-0365` | Created the retained pre-implementation review record and requested changes on docs discoverability, parent authority truth, and proof-plan alignment. |
| 2 | `REV-PR-0365` | Re-reviewed the blocker fixes, found no remaining docs-authority gaps in scope, and updated the retained decision to `approved`. |
| 3 | `REV-PR-0365` | Performed the post-implementation ruthless review, confirmed the runtime patch and focused tests are aligned, and moved the retained decision back to `changes_requested` because protected authenticated browser proof is still missing. |
