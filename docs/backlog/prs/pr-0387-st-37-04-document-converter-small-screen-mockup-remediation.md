---
type: pr
id: PR-0387
title: "ST-37-04 Document Converter small-screen mockup remediation"
status: done
owners: "agents"
created: 2026-06-25
updated: 2026-06-25
stories:
  - "ST-37-04"
tags:
  - frontend
  - mockup
  - design-system
  - remediation
dependencies:
  - "PR-0383"
acceptance_criteria:
  - "Given curated apps are desktop-first instruments, when the Document Converter HTML/CSS mockup is viewed on phone width, then it presents a deliberate reduced port rather than stacking the full desktop workbench."
  - "Given secondary project inventory is not the primary phone task, when the phone mockup renders, then mode/project inventory is summarized or deferred behind compact affordances while preview and core output actions stay reachable."
  - "Given the PR-0383 outcome-first rule, when the reduced phone layout is created, then it still exposes only operator input/output choices and does not introduce renderer, producer, path, id, advanced, or implementation-detail controls."
  - "Given PR-0383 established token fidelity, when the remediation closes, then the static mockup uses imported design tokens rather than hard-coded surface colors and still reserves navy fill for selected selector-rail state only."
  - "Given this is a mockup approval package, when the remediation closes, then no production Vue route, `/apps/document-converter` activation, final Swedish copy, backend contract change, or API type change is introduced."
---

# PR-0387: ST-37-04 Document Converter Small-Screen Mockup Remediation

## Problem

The first frontend review of the `PR-0383` HTML/CSS mockup found that the
phone breakpoint linearizes the entire desktop workbench into one vertical
stack. That violates the curated-app small-screen policy: dense teacher tools
may have reduced phone ports, but the phone view must not be a compressed
desktop rail with every secondary control dumped in order.

The same review also found one hard-coded topbar surface color in the static
mockup, which weakens the token-driven handoff contract for `PR-0384`.

## Research Basis

- `integrated-frontend-stack/references/dense-workspaces.md`: dense curated
  apps are instruments; mobile is a reduced port, not the source layout.
- `integrated-frontend-stack/references/layout-geometry.md`: CSS owns
  breakpoint geometry, scroll ownership, containment, and panel/drawer layout.
- `.codex/rules/045-huleedu-design-system.md`: operational density,
  desktop-first curated-app composition, token-first styling, and reduced
  mobile ports are governed design-system behavior.
- `docs/mockups/st-29-small-screen-workspace-redesign/README.md`: approved
  local precedent for replacing cramped small-screen workspace rails with
  compact mode affordances and mode-specific reduced layouts.
- `PR-0383` frontend review by subagent `Zeno`: changes requested because the
  phone mockup stacked rail, controls, preview, and actions instead of defining
  an approved small-screen contract.

## Goal

Remediate the route-inactive static HTML/CSS mockup so `PR-0383` can approve a
truthful small-screen contract before `PR-0384` implements production Vue.

The corrected phone view should keep the stable shell and preview-centered
workflow, summarize or defer secondary project inventory, keep core output and
preview actions reachable, and avoid introducing any main-page control that
compensates for missing application logic.

## Non-goals

- No production Vue route or component changes.
- No `/apps/document-converter` activation.
- No backend, API, OpenAPI, generated frontend type, or storage changes.
- No final Swedish copy approval.
- No advanced settings overlay.
- No template marketplace, durable history, or file manager implementation.

## Implementation Plan

1. Update the static HTML/CSS mockup only:
   - preserve the desktop Project Workbench geometry;
   - add a phone-specific reduced port;
   - summarize/defer project inventory and readiness details on phone;
   - keep preview, paper size, output mode, render, download, save, and discard
     reachable without surfacing internal conversion controls;
   - replace hard-coded surface color with token-derived styling.
2. Update the `PR-0383` mockup README and backlog notes with the approved
   small-screen contract.
3. Refresh desktop and mobile screenshot proof under
   `.artifacts/pr-0383-html-css-mockup-proof/`.
4. Run a fixed reviewer pass and retain review evidence before closing.

## Progress

- The static mockup now adds a phone-only workspace summary shell while leaving
  the desktop Project Workbench structure intact.
- The phone breakpoint now hides the full desktop rail, moves preview ahead of
  outcome controls, and keeps render/download/save/discard reachable.
- The topbar surface now uses token-derived styling instead of a hard-coded
  `rgba(...)` value.

## Red-First Proof Plan

- Review-red evidence: Zeno's frontend review found `changes_requested` because
  the earlier phone mockup stacked the full desktop workbench instead of
  presenting a reduced phone port. The preserved red artifact for this session
  is `.artifacts/pr-0383-html-css-mockup-proof/mobile-390-full-before-pr0387.png`.
- Token-red evidence: the pre-remediation stylesheet used a literal
  `rgba(...)` topbar surface. The preserved red desktop artifact for this
  session is `.artifacts/pr-0383-html-css-mockup-proof/desktop-1680x980-before-pr0387.png`.

## Green Proof Plan

- Desktop and mobile screenshot proof:
  - `pdm run playwright screenshot --viewport-size=1680,980 ...`
  - `pdm run playwright screenshot --full-page --viewport-size=390,920 ...`
- Static audits:
  - no literal colors anywhere in the scoped HTML/CSS bundle;
  - no `Letter` or toy document-shape controls;
  - no default-page implementation controls for producer, paths, ids,
    orientation, margins, print CSS, embedding, page breaks, advanced settings,
    durable history, or raw filesystem authority;
  - only selected selector-rail state may use navy fill.
- `pdm run docs-validate`
- `pdm run handoff-validate` only if `.codex/handoff.md` changes
- `git diff --check`

## Verification Notes

- Screenshot proof regenerated:
  - `.artifacts/pr-0383-html-css-mockup-proof/desktop-1680x980.png`
  - `.artifacts/pr-0383-html-css-mockup-proof/mobile-390-full.png`
- Preserved red comparison artifacts:
  - `.artifacts/pr-0383-html-css-mockup-proof/desktop-1680x980-before-pr0387.png`
  - `.artifacts/pr-0383-html-css-mockup-proof/mobile-390-full-before-pr0387.png`
- Static audits passed:
  - `rg -n "#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})\\b|rgba?\\(" docs/mockups/pr-0383-document-converter-mockup-and-copy-approval/html-css-mockup/index.html docs/mockups/pr-0383-document-converter-mockup-and-copy-approval/html-css-mockup/styles.css docs/mockups/pr-0383-document-converter-mockup-and-copy-approval/html-css-mockup/preview.css docs/mockups/pr-0383-document-converter-mockup-and-copy-approval/html-css-mockup/icons.css` returned no matches after replacing `.pdf-page` `#fff` with `var(--huleedu-paper)`.
  - `rg -n -i "\\bletter\\b|document[- ]shape|orientation|margin|page[- ]break|embedding|producer|preview id|artifact id|advanced settings|history|filesystem|path" index.html` returned no matches.
  - `rg -n "background:\\s*var\\(--huleedu-navy\\)" styles.css` returned only the selected `.rail-choice-active` state.
- Validation passed:
  - `pdm run docs-validate`
  - `git diff --check`
- `pdm run handoff-validate` was not rerun because `.codex/handoff.md` was unchanged.

## Overseer Contract

Implementation must run through the overseer loop:

1. Implementation specialist applies the static mockup/docs remediation and
   reports exact changed files plus red/green proof.
2. Fixed reviewer writes or updates retained review evidence under
   `docs/backlog/reviews/` and returns `approved` or `changes_requested`.
3. If changes are requested, the same implementation specialist receives the
   review and repairs the accepted findings.
4. The slice closes only after the retained review is accepted and the required
   validation gates pass.

Current-session execution note: the overseer loop used separate subagents for
implementation and review. `Nash` implemented the static mockup remediation;
`Franklin` remained the fixed reviewer, wrote `REV-PR-0387`, requested one
repair pass, then approved the retained review after the repair.

## Stop Conditions

- Stop if the remediation requires production route-visible UI.
- Stop if the small-screen solution needs final Swedish copy approval.
- Stop if the phone view introduces application-logic settings as user-facing
  controls.
- Stop if token fidelity conflicts with `.codex/rules/045-huleedu-design-system.md`.
- Stop if the implementation would modify backend/API contracts or generated
  frontend types.

## Rollback Plan

Revert the `PR-0387` static mockup and docs changes. Keep `PR-0382`,
`PR-0383`, and the backend paper-size tests unchanged unless a later review
finds a separate contract defect.
