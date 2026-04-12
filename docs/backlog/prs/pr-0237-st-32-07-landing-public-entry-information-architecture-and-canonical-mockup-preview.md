---
type: pr
id: PR-0237
title: "ST-32-07: landing public-entry information architecture and canonical mockup preview"
status: done
owners: "agents"
created: 2026-04-07
updated: 2026-04-07
stories:
  - "ST-32-07"
tags: ["frontend", "ux", "landing-page", "public-access", "mockup", "planning"]
dependencies:
  - "EPIC-32"
  - "ST-11-21"
  - "ST-32-06"
acceptance_criteria:
  - "Given `ST-32-07` needs layout and CTA-hierarchy alignment before production code, when this slice lands, then the repo has one story-scoped mockup under `docs/mockups/` for the public landing discoverability flow."
  - "Given this slice is assigned to multiple lead web designers as a competitive mockup round, when they work in parallel, then each designer posts independent mockup files under `docs/mockups/st-32-07-public-landing-discoverability/` without editing or reacting to another designer's contribution unless explicitly directed to do so."
  - "Given the mockup round is competitive rather than collaborative, when the submissions are reviewed, then the strongest overall direction is promoted to the canonical blueprint for later implementation."
  - "Given the new landing direction must stay grounded in the actual Skriptoteket design language, when the mockup is authored, then the work explicitly references `.agents/rules/045-huleedu-design-system.md`, the `skriptoteket-frontend-specialist` skill, and the `brutalist-academic-ui` skill before any layout decisions are frozen."
  - "Given the mockup exists to align the first-screen landing direction, when it is opened, then it demonstrates the intended header link treatment, hero CTA hierarchy, and below-the-fold section order without mixing in malformed-route recovery or not-found guidance."
  - "Given header and hero both appear above the fold, when the mockup is reviewed, then the header-level `Klassrumskartan` affordance reads as quiet discoverability nav and the hero reads as the single primary action."
  - "Given the top header should stay calm, when the mockup is reviewed, then `Logga in` is not duplicated as a competing strong header action above the fold."
  - "Given the user must sign off every Swedish sentence later, when draft copy appears in the mockup, then it is clearly provisional and stays short, conversational, verb-led, non-technical, and free of sales language or internal terminology."
  - "Given the landing page should avoid generic card-stack aesthetics, when the mockup is authored, then it does not default to cards or nested cards and instead explores stronger structural layout devices first."
  - "Given this slice is for alignment only, when it ships, then no production frontend component, route, or backend behavior is changed."
---

## Problem

The repo has enough product direction to know that the public app should be easier to discover, but
it does not yet have a locked visual or information-architecture proposal for how that should work.

If we jump straight into production Vue code now, we risk burning time on layout churn and CTA
debates inside the live app instead of aligning first.

## Goal

Create one canonical story-scoped mockup that lets us align on public-entry hierarchy, section
order, and draft showcase language before production landing-page changes begin.

## Decision

`docs/mockups/st-32-07-public-landing-discoverability/designer-a.html` is the winning submission
for `PR-0237`. The canonical blueprint artifact for `ST-32-07` is the separate copy
`docs/mockups/st-32-07-public-landing-discoverability/index.html`, derived from the winning file
without modifying the original submission.

Why this direction won:

- it understands the page as a landing page first, not as an explained information-architecture exercise
- it keeps the header calmer and more confident
- it gives the hero one unmistakable first action
- it shows the product more directly with less explanatory support copy
- it keeps the authenticated-only preview reading as “later” instead of as a competing route
- it stays inside the Skriptoteket/HuleEdu brutalist-academic language without drifting into generic marketing design or overbuilt mockup chrome
- it feels edited: the hierarchy is clearer because it knows what to emphasize and what to leave out

Blueprint caveats to carry into `PR-0238` polish:

- any optional baseline overlay is a working aid only and must not appear in presentations, blueprint exports, or production interpretation
- a few monospace / uppercase micro-markers can be softened later, especially in smaller labels, captions, or utility-style navigation details, but that is polish rather than a directional problem

## Non-goals

- Editing `HomeView.vue`, `LandingLayout.vue`, or router code yet.
- Creating backend-driven marketing content or registry-driven landing cards in this slice.
- Finalizing shipped copy.
- Designing malformed-route recovery.

## Implementation plan

1. Review the current landing and design doctrine first:
   - `.agents/rules/045-huleedu-design-system.md`
   - `skriptoteket-frontend-specialist`
   - `brutalist-academic-ui`
2. Create a canonical mockup folder for this story under `docs/mockups/`.
3. Run this slice as a competitive mockup round:
   - each designer creates their own independent mockup files inside
     `docs/mockups/st-32-07-public-landing-discoverability/`
   - do not edit another designer's files
   - do not study or react to another designer's mockup unless explicitly told to do so
   - the best overall direction will later be promoted to blueprint
4. Add one self-contained preview file per designer that demonstrates:
   - header-level `Klassrumskartan` discoverability
   - hero CTA hierarchy with public app first
   - below-the-fold featured public app section
   - authenticated-value preview section
5. Keep the header affordance quiet and navigational while the hero remains the single strong
   primary action.
6. Keep the top header calm. Do not add a duplicated strong `Logga in` action there when the hero
   already carries the main CTA hierarchy.
7. Keep the visual language clearly within Skriptoteket/HuleEdu brutalist-academic patterns rather
   than inventing a separate glossy marketing style, and avoid card-first or nested-card layout
   proposals.

## Proposed module focus

- `docs/mockups/st-32-07-public-landing-discoverability/index.html`

## Mockup designer resources

Use these files as the practical source material for the mockup:

- Current signed-out landing view:
  `frontend/apps/skriptoteket/src/views/HomeView.vue`
- Shared signed-out shell/header:
  `frontend/apps/skriptoteket/src/components/layout/LandingLayout.vue`
- Root layout usage of the signed-out shell:
  `frontend/apps/skriptoteket/src/App.vue`
- Current public route shape:
  `frontend/apps/skriptoteket/src/router/routes.ts`
- Current landing behavior tests:
  `frontend/apps/skriptoteket/src/views/HomeView.spec.ts`
- Shared design rule:
  `.agents/rules/045-huleedu-design-system.md`
- Frontend implementation skill:
  `/Users/olofs_mba/Documents/Repos/skill-repository/skills/skriptoteket-frontend-specialist/SKILL.md`
- Brutalist/academic layout skill:
  `/Users/olofs_mba/Documents/Repos/skill-repository/skills/brutalist-academic-ui/SKILL.md`
- Canonical mockup precedent:
  `docs/backlog/prs/pr-0184-st-29-10-canonical-mockup-folder-and-first-run-preview.md`
- Canonical mockup location precedent:
  `docs/mockups/st-29-10-first-run-workspace-gating/index.html`

The mockup files for this slice should live under:

- `docs/mockups/st-32-07-public-landing-discoverability/`

Use designer-specific names so submissions can coexist, for example:

- `docs/mockups/st-32-07-public-landing-discoverability/designer-a.html`
- `docs/mockups/st-32-07-public-landing-discoverability/designer-b.html`
- `docs/mockups/st-32-07-public-landing-discoverability/designer-c.html`

## Test plan

- Open the mockup file locally in a browser and verify the full landing flow renders.
- `pdm run docs-validate`

## Rollback plan

- Remove the `ST-32-07` mockup folder if the story direction changes, while keeping the story and
  later production-slice docs intact.
