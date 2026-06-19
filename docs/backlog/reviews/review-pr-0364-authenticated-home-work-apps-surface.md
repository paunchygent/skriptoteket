---
type: review
id: REV-PR-0364
title: "Review: PR-0364 authenticated home work-apps surface"
status: pending
owners: "agents"
created: 2026-06-19
updated: 2026-06-19
reviewer: "codex-independent-reviewer"
prs:
  - PR-0364
links:
  - ST-37-03
  - EPIC-37
  - PR-0361
  - PR-0362
  - PR-0363
  - REV-PR-0363
  - MOCK-pr-0364-authenticated-home-work-apps-surface
  - REF-service-shell-ux-realignment-plan-v1
  - REF-current-product-lanes-and-sir-convert-boundary-v1
  - REF-app-presentation-decomposition-and-naming-plan-v1
---

# Review: PR-0364 Authenticated Home Work-Apps Surface

## TL;DR

Pending review after user approval of the C2 mockup. This review should decide
whether `PR-0364` is sufficiently bounded and implementation-ready as the next
`ST-37-03` route-visible slice: make authenticated `/` app-first, promote
`Kodredigerare` to the primary app shelf, remove run/latest/recent vanity
chrome, avoid nested cards, and stop rather than fake the Document Converter
route.

## Problem Statement

The signed-in home still presents Skriptoteket primarily as favorites, recent
tools, catalog/run/editor/admin actions, and a generic dashboard grid. After
`PR-0363`, the home can link directly to Exam Converter and Audio Transcription
without route decomposition, and the approved C2 mockup defines the app-first
target hierarchy.

## Proposed Solution

Review the amended `PR-0364` contract against the approved C2 mockup. The
deleted PR-0364 card-grid and service-foyer mockups must not be treated as
evidence. The proposal should keep runtime work bounded to authenticated home
composition unless `PR-0365` is explicitly absorbed, add direct entries for
`Klassrumskartan`, `Exam Converter`, `Audio Transcription`, and
`Kodredigerare`, include `Document Converter` only with a truthful reviewed
route target, remove `Mina körningar`/latest/recent home chrome, preserve flat
secondary file/catalog/contribution affordances, and require focused Vitest
plus Docker-backed HuleEdu browser-session proof.

## Artifacts To Review

| File | Focus | Time |
|------|-------|------|
| `docs/mockups/pr-0364-authenticated-home-work-apps-surface/README.md` | Approved C2 design direction, accepted/rejected patterns | 8 min |
| `docs/mockups/pr-0364-authenticated-home-work-apps-surface/index.html` | Concrete HTML/CSS mockup hierarchy and forbidden nested-card/open-link patterns | 10 min |
| `docs/backlog/prs/pr-0364-st-37-03-authenticated-home-work-apps-surface.md` | Scope, decisions, options, red/green plan, and proof gates | 20 min |
| `docs/backlog/stories/story-37-03-service-shell-and-dashboard-ux-realignment.md` | Parent story expectations and sequencing | 5 min |
| `docs/reference/ref-service-shell-ux-realignment-plan-v1.md` | Home-before-navigation sequence authority | 8 min |
| `docs/reference/ref-current-product-lanes-and-sir-convert-boundary-v1.md` | Current product lane and Document Converter truth boundary | 8 min |
| `docs/reference/ref-app-presentation-decomposition-and-naming-plan-v1.md` | App presentation and route/registry stop conditions | 8 min |
| `frontend/apps/skriptoteket/src/views/HomeView.vue` | Current signed-in dashboard ordering and preservation surface | 10 min |
| `frontend/apps/skriptoteket/src/views/HomeView.spec.ts` | Existing signed-out coverage and expected red test seam | 5 min |

**Total estimated time:** ~70 minutes.

## Key Decisions

| Decision | Rationale | Approve? |
|----------|-----------|----------|
| Put work-app lanes before old dashboard/platform sections on authenticated `/`. | This is the smallest route-visible step that centers the current product proposition without changing sidebar navigation yet. | [ ] |
| Use current truthful route targets for the three runnable lanes. | `PR-0363` made Exam and Transcript directly linkable while preserving app-id compatibility. | [ ] |
| Promote `Kodredigerare` into the app shelf. | The user explicitly rejected treating the editor as a form or nested secondary action. | [ ] |
| Include `Document Converter` only with a truthful route stop condition. | The approved mockup includes the lane, but linking it to Exam/Transcript or catalog would be false. | [ ] |
| Remove `Mina körningar`/latest/recent home chrome. | The user explicitly retired this dashboard path from the active home direction. | [ ] |
| Preserve useful secondary surfaces without nested cards. | Files/catalog/contribution remain useful but must be flat ledger affordances below the app shelf. | [ ] |
| Require Docker-backed HuleEdu browser-session proof. | Authenticated route-visible proof must use Gateway with Docker `skriptoteket_web`, not host Uvicorn. | [ ] |
| Treat the approved C2 mockup as the design authority. | The user approved the latest C2 suggestion and requested a real HTML/CSS mockup before code. | [ ] |

## Review Checklist

- [ ] Scope is limited to authenticated home composition unless `PR-0365` is
  explicitly absorbed for sidebar/mobile navigation.
- [ ] Route targets are exact and do not require route-table or app-id changes.
- [ ] Document Converter handling cannot mislead teachers into Exam/Transcript,
  catalog, or the current compatibility host.
- [ ] `Kodredigerare` is treated as an app shelf entry.
- [ ] `Mina körningar`, latest-used apps, and recent-used vanity rows are
  absent from authenticated home.
- [ ] Secondary surfaces are flat ledgers or equivalent un-nested structures.
- [ ] Existing useful files/catalog/contribution/admin capabilities remain
  available below or outside the app shelf.
- [ ] Red-first test and live proof plan would catch the real product failure:
  signed-in home still being generic-dashboard-first.
- [ ] Stop conditions cover route/registry/backend/Sir Convert/HuleEdu/QTI/DOCX
  drift and the Docker service proof lane.
- [ ] The approved C2 HTML/CSS mockup is the only mockup target; the deleted
  card-grid and service-foyer attempts are not treated as targets.

## Review Feedback

**Reviewer:** `codex-independent-reviewer`
**Date:** `2026-06-19`
**Verdict:** `pending`

### Required Changes

Pending review.

### Suggestions (Optional)

Pending review.

### Decision Approvals

- [ ] Approved C2 authenticated home work-app hierarchy
- [ ] Exact current lane route targets
- [ ] `Kodredigerare` as primary app
- [ ] Document Converter truthful-route stop condition
- [ ] `Mina körningar`/latest/recent home chrome removed
- [ ] Flat secondary ledgers instead of nested cards
- [ ] Docker-backed authenticated browser proof lane
- [ ] Approved mockup retained under `docs/mockups/`

## Changes Made

| Change | Artifact | Description |
|--------|----------|-------------|
| 1 | `REV-PR-0364` | Added the retained planning review packet for the authenticated home work-app surface |
| 2 | `MOCK-pr-0364-authenticated-home-work-apps-surface` | Added the approved C2 HTML/CSS mockup as review evidence |
