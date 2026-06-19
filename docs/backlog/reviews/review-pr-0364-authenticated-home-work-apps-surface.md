---
type: review
id: REV-PR-0364
title: "Review: PR-0364 authenticated home work-apps surface"
status: approved
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

Approved. The scoped mockup patch stays inside the retained design lane, aligns
with the HuleEdu/Skriptoteket token and composition rules, keeps
`Kodredigerare` first-class, shows `Document Converter` without faking a
runtime route, and the supplied desktop/mobile renders remain coherent without
overlap or clipping.

## Problem Statement

The signed-in home still presents Skriptoteket primarily as favorites, recent
tools, catalog/run/editor/admin actions, and a generic dashboard grid. After
`PR-0363`, the home can link directly to Exam Converter and Audio Transcription
without route decomposition, and the approved C2 mockup defines the app-first
target hierarchy.

## Proposed Solution

Review the amended `PR-0364` contract against the approved C2 mockup and the
actual mockup patch only. The deleted PR-0364 card-grid and service-foyer
mockups are not evidence. Approval requires that the HTML/CSS preview remains a
truthful design mockup, keeps runtime work bounded to authenticated home
composition unless `PR-0365` is explicitly absorbed, adds direct entries only
for the already-truthful lanes, keeps `Document Converter` non-clickable until a
reviewed route exists, removes `Mina körningar`/latest/recent home chrome, and
preserves flat secondary file/catalog/contribution affordances.

## Artifacts To Review

| File | Focus | Time |
|------|-------|------|
| `docs/mockups/pr-0364-authenticated-home-work-apps-surface/README.md` | Approved C2 design direction, accepted/rejected patterns, Document Converter truth boundary | 8 min |
| `docs/mockups/pr-0364-authenticated-home-work-apps-surface/index.html` | Concrete HTML/CSS mockup hierarchy, token usage, truthful links, and forbidden nested-card/open-link patterns | 10 min |
| `docs/backlog/prs/pr-0364-st-37-03-authenticated-home-work-apps-surface.md` | Scope, decisions, options, red/green plan, and proof gates | 20 min |
| `.artifacts/pr-0364-authenticated-home-work-apps-surface/design-rule-alignment-desktop.png` | Desktop geometry, equal-height shelves, and absence of clipping/overlap | 5 min |
| `.artifacts/pr-0364-authenticated-home-work-apps-surface/design-rule-alignment-mobile.png` | Compact-width geometry, stacking coherence, and absence of clipping/overlap | 5 min |

**Total estimated time:** ~56 minutes.

## Key Decisions

| Decision | Rationale | Approve? |
|----------|-----------|----------|
| Put work-app lanes before old dashboard/platform sections on authenticated `/`. | This is the smallest route-visible step that centers the current product proposition without changing sidebar navigation yet. | [x] |
| Use current truthful route targets for the three runnable lanes. | `PR-0363` made Exam and Transcript directly linkable while preserving app-id compatibility. | [x] |
| Promote `Kodredigerare` into the app shelf. | The user explicitly rejected treating the editor as a form or nested secondary action. | [x] |
| Include `Document Converter` only with a truthful route stop condition. | The approved mockup includes the lane, but linking it to Exam/Transcript or catalog would be false. | [x] |
| Remove `Mina körningar`/latest/recent home chrome. | The user explicitly retired this dashboard path from the active home direction. | [x] |
| Preserve useful secondary surfaces without nested cards. | Files/catalog/contribution remain useful but must be flat ledger affordances below the app shelf. | [x] |
| Require Docker-backed HuleEdu browser-session proof. | Authenticated route-visible proof belongs to the implementation slice, not this static mockup review; the PR still keeps that gate. | [x] |
| Treat the approved C2 mockup as the design authority. | The user approved the latest C2 suggestion and requested a real HTML/CSS mockup before code. | [x] |

## Review Checklist

- [x] Scope is limited to authenticated home composition unless `PR-0365` is
  explicitly absorbed for sidebar/mobile navigation.
- [x] Route targets are exact and do not require route-table or app-id changes.
- [x] Document Converter handling cannot mislead teachers into Exam/Transcript,
  catalog, or the current compatibility host.
- [x] `Kodredigerare` is treated as an app shelf entry.
- [x] `Mina körningar`, latest-used apps, and recent-used vanity rows are
  absent from authenticated home.
- [x] Secondary surfaces are flat ledgers or equivalent un-nested structures.
- [x] Existing useful files/catalog/contribution/admin capabilities remain
  available below or outside the app shelf.
- [x] The implementation plan still requires red-first tests and live proof for
  the eventual runtime slice.
- [x] Stop conditions cover route/registry/backend/Sir Convert/HuleEdu/QTI/DOCX
  drift and the Docker service proof lane.
- [x] The approved C2 HTML/CSS mockup is the only mockup target; the deleted
  card-grid and service-foyer attempts are not treated as targets.

## Review Feedback

**Reviewer:** `codex-independent-reviewer`
**Date:** `2026-06-19`
**Verdict:** `approved`

### Current Review Pass - 2026-06-19

Decision: `approved`.

#### Scope Reviewed

- Governing docs: `AGENTS.md`, `.codex/rules/045-huleedu-design-system.md`,
  `PR-0364`, `REV-PR-0364`, the required design-skill references, and the
  scoped mockup README/HTML.
- Scoped worker patch only:
  `docs/mockups/pr-0364-authenticated-home-work-apps-surface/README.md` and
  `docs/mockups/pr-0364-authenticated-home-work-apps-surface/index.html`.
- Render evidence only:
  `.artifacts/pr-0364-authenticated-home-work-apps-surface/design-rule-alignment-desktop.png`
  and
  `.artifacts/pr-0364-authenticated-home-work-apps-surface/design-rule-alignment-mobile.png`.

#### Findings

No findings.

The approved state is grounded in the reviewed files and renders:

- `docs/mockups/pr-0364-authenticated-home-work-apps-surface/index.html:8`
  imports the canonical HuleEdu design tokens, and
  `index.html:10-26` maps local variables from those tokens rather than from a
  raw local palette.
- `index.html:80-85`, `index.html:160-164`, `index.html:317-327`, and
  `index.html:346-352` remove the all-caps/eyebrow treatment in favor of
  structure-first headings and sentence-case hierarchy.
- `index.html:166-181` and `index.html:297-327` define stable equal-height app
  shelves with border-led surfaces and no hard per-card shadows.
- `index.html:427-431` and `index.html:452-503` keep truthful runtime links for
  `Klassrumskartan`, `Exam Converter`, `Audio Transcription`, and
  `Kodredigerare`, while `Document Converter` remains visible but
  non-clickable.
- `index.html:505-519` keeps the lower continuation area as flat ledgers rather
  than nested cards.
- `README.md:30-48` and `README.md:52-59` now explicitly encode the approved
  direction, including the no-fake-Document-Converter-link rule and the banned
  `Mina körningar`/latest-used/nested-card patterns.
- The retained desktop and mobile renders show coherent layout, no overlap, no
  clipping, and the expected shelf/ledger hierarchy at both breakpoints.

Residual risk, not a blocker: this review covers only the static mockup lane.
The later runtime implementation still owes the governed red-first tests and
Docker-backed HuleEdu browser-session proof already specified in `PR-0364`.

#### Validation Commands And Outcomes

Reviewer-ran checks:

```bash
pdm run docs-validate
git diff --check
```

Results:

- `docs-validate`: passed.
- `git diff --check`: passed.

Worker evidence inspected without rerunning the render:

- `pdm run docs-validate`: reported passed before review-doc edits.
- `git diff --check`: reported passed before review-doc edits.
- Desktop render:
  `.artifacts/pr-0364-authenticated-home-work-apps-surface/design-rule-alignment-desktop.png`.
- Mobile render:
  `.artifacts/pr-0364-authenticated-home-work-apps-surface/design-rule-alignment-mobile.png`.

### Required Changes

None.

## Changes Made

| Change | Artifact | Description |
|--------|----------|-------------|
| 1 | `REV-PR-0364` | Retained the independent mockup review verdict as `approved` with scoped evidence, no findings, and validator results |
