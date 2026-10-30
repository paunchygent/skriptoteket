---
type: task
id: TASK-SKRIPT-REP-0060
title: The top bar shows the Skriptoteket logo, larger than app titles, linking to the signed-in start page
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: '2026-10-30'
status: done
closeout_review:
  record: inline
  status: approved
  reviewer: orchestrator
  decided_at: '2026-10-30'
  approval_protocol: agent-overseer:approved-review-closeout
  approval_evidence: 'Light route, no review (D6). Merged 5b9cf6981 (466c839b7, d9e747c6c) and deployed to production; deploy log .artifacts/hemma-deploy-20261030-012826.log, healthz 200, web and worker healthy. The user checked the top-bar logo in production on phone and desktop on 2026-10-30 and answered ''Looks right''.'
task_kind: repository
acceptance_criteria:
  - The signed-in top bar and the login page render the shared logo (huleedu-integrated 0.1.38) as inline SVG coloured by the wordmark tokens, with the app label beside it in the top bar
  - The logo's visible height is larger than the page-title H1 role (24 px) at desktop, tablet and phone, the top bar stays 56 px, and the logo link is at least 44 px high
  - Clicking the top-bar logo goes to the home route, where sign-in lands when no other target was saved; only the linked logo shows a pointer cursor
  - The immersive dark top bar colours the logo through the wordmark tokens, with no CSS filter
  - The Klassrumskartan PDF exports show the 0.1.38 logo with navy and terracotta
backlog_document_profile: contract-derived
---

## Implementation Contract

The app shell rebuild (TASK-SKRIPT-40-04-02, `b71fd8524`, 2026-10-17) replaced the Skriptoteket logo in the
signed-in top bar with plain serif text, smaller than the app page titles. This task puts the shared logo back as
the home control, rendered inline so the design tokens colour it.

- Source: the shared design package 0.1.38 (TASK-SKILL-REP-0423) fixes the logo (one navy, trimmed right edge,
  compact paths) and writes its fills as `var(--huleedu-wordmark-primary, #082B4C)` and
  `var(--huleedu-wordmark-accent, #C94F32)`. This task adopts 0.1.38 through `design-system sync`; the synced
  `public/logo-horizontal.svg` stays the one logo file.
- Component: `BrandLogo.vue` renders that synced SVG inline (one source, no hand-copied paths), with an accessible
  name "Skriptoteket"; it sets no cursor. The top bar (`AuthTopBar.vue` `.topbar-brand`) and the login page use it.
- Size: logo height `var(--huleedu-space-10)` (40 px, about 35 px of visible ink) beats the page-title role
  (`.page-title`, `--huleedu-text-2xl`, 24 px) at every band; the top bar stays 56 px; the brand link is at least
  `--huleedu-action-control-height` (44 px) high.
- Link: `to="/"`; `resolveAuthLoginSuccessLocation` falls back to `home` (`/`) for every role.
- Immersive dark bar: the logo takes light colours by overriding the two wordmark tokens on the brand; the
  `brightness(0) invert(1)` filter goes.
- Klassrumskartan PDF exports: `classroom_planner/assets/logo-horizontal.svg` (a hand copy outside the sync map,
  rendered by WeasyPrint) takes the 0.1.38 file. If WeasyPrint does not apply the `var()` fallbacks, that copy
  keeps the 0.1.38 geometry with plain hex fills.
- Non-goals: the start-page greeting (44 px), the Flunk-Out Frenzy game titles and the signed-out recovery page
  stay larger than the logo; the favicon; HuleEdu's adoption of 0.1.38.

## Contract Inputs

- User decisions of 2026-10-30 (Hemma orchestrator session, AskUserQuestion): restore the logo; larger than app
  page titles only; link to the signed-in start page; inline with token colours; fix at the shared source; keep
  the outlined letterforms; no pointer cursor on the unlinked login logo.
- Junior findings on WIP `1007b2601` (branch `codex/task-skript-rep-0060`): page title 24 px at every band, top bar
  56 px, sign-in fallback `home`, the immersive filter, the 40 px link.
- TASK-SKILL-REP-0423 (skill-repository) for 0.1.38; `design-system-map.json`; the resource package contract's
  Consumer Adoption section.

## Core Vertical And Performance

One signed-in screen: the top bar shows the inline logo in token colours, taller than the app's page title, and a
click lands on the home route. The SVG is a few KB inline; no request is added. One junior unit after 0.1.38
exists, building on the WIP commit.

## Validation

- Vitest in `AuthLayout.actions.spec.ts`: the brand link renders the inline logo with the accessible name
  Skriptoteket, keeps the app label, targets `/`, and the login logo has no pointer cursor.
- One Klassrumskartan PDF export rendered locally, checked for the logo's navy and terracotta.
- The user's check in production on a phone and on desktop.

## Stop Conditions

- 0.1.38 is not released, or `design-system sync` brings changes beyond the logo and the wordmark tokens.
- The inline SVG cannot be rendered from the synced file without copying its paths into a component.

## Decided Contract Terms

| ID  | Decided contract term                                                                                                                                                                                      |
| --- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| D1  | The top bar and the login page render the shared 0.1.38 logo inline from the synced file, with the app label beside it in the top bar.                                                                     |
| D2  | The logo is 40 px high (larger than the 24 px page-title role) at every band; the top bar stays 56 px; the link is at least 44 px high. The start-page greeting, game titles and recovery page are exempt. |
| D3  | The logo links to `/`, the sign-in fallback for every role.                                                                                                                                                |
| D4  | The wordmark tokens colour the logo; the immersive bar overrides them instead of a CSS filter; only the linked logo shows a pointer cursor.                                                                |
| D5  | Skriptoteket adopts 0.1.38 through `design-system sync`; the PDF-export copy takes the same file, or plain-hex fills if WeasyPrint ignores the fallbacks.                                                  |
| D6  | Light route: one junior on the WIP branch, focused Vitest, one PDF render, the user's check in production; no review.                                                                                      |
