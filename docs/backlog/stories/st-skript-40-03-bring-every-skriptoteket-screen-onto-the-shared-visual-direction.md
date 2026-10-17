---
type: story
id: ST-SKRIPT-40-03
title: Bring every Skriptoteket screen onto the shared visual direction
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: '2026-10-12'
status: ready
closeout_review:
  record: inline
  status: not_started
epic: EPIC-SKRIPT-40
acceptance_criteria:
  - Every Skriptoteket screen except the app shell and the exam workspace keeps its layout and renders panels, cards and controls with the shared huleedu-ui-design visual authority, tokens, action buttons and components, without hard offset shadows
  - Skriptoteket has no .codex/rules; every still-valid rule fact lives in the skill that owns its topic, and AGENTS.md and CLAUDE.md route agent instruction through skills only
links:
  decisions: []
backlog_document_profile: contract-derived
---

## Slice Contract

Every Skriptoteket screen except the app shell (top bar, sidebar, page frame)
and the exam workspace keeps its layout and moves onto the shared visual
direction owned by `huleedu-ui-design` and the shared `huleedu-integrated`
package. Each screen gets:

- the shared tokens for colour, surfaces, borders and type;
- the shared action buttons: every button renders from the package
  action-button stylesheet adopted by TASK-SKRIPT-40-01-03 or from a shared
  dense button component, with no local button styling left;
- the shared components adopted by TASK-SKRIPT-40-01-02 wherever the screen
  hand-rolls the same control;
- the shared panel and card treatment, with no hard offset shadows and no heavy
  frames.

This is a refresh, not new design. Sol 6.1 pairs do the work, one pair per
area. The refresh starts right after TASK-SKRIPT-40-01-02 and
TASK-SKRIPT-40-01-03 land. The areas run in parallel, and an area is frozen
(bug fixes only) only while its refresh pair works on it. Other areas keep
shipping UI until their turn.

TASK-SKRIPT-40-01-02 now carries the first sync of `huleedu-integrated` 0.1.24
and removes every local use of the removed shadow tokens, shadow-brutal
utilities, `.btn-brutal` and hover-lift or press transforms in the same commit.
The area tasks build on that result and remove any hard offset shadow or heavy
frame that the sync did not reach.

The refresh does not wait for TASK-SKILL-REP-0280. Each pair removes every
divergence from the shared core in its area. A divergence the pair must keep is
listed in the task evidence and registered in the shared register when
TASK-SKILL-REP-0280 lands.

TASK-SKRIPT-40-03-09 removes Skriptoteket's rule system: every still-valid fact
under `.codex/rules` moves into the skill that owns its topic, and agent
instruction routes through skills only.

Out of scope:

- The app shell and the exam workspace: ST-SKRIPT-40-04.
- The old exam converter screens: they get only what arrives through the
  shared classes and tokens, and TASK-SKRIPT-39-07-03 retires them.
- The Flunk-Out Frenzy game, including its page chrome
  (`views/apps/FlunkOutFrenzyView.vue`, `views/apps/components/Fof*.vue`,
  `views/apps/styles/fof-shell-*.css`), by the plan the user confirmed on
  2026-10-17. This overrides the page-chrome scope of retained plan S4.

## Contract Inputs

- User decisions G6, G7, G9, G11, G12 and G29 and lead decisions L5 and L6
  (2026-10-17):
  `.orchestration/context/sessions/01a1495e-8398-75be-b2da-f0b08ba11afa/evidence/planning/decisions-2026-10-17.md`.
- Retained plan S1-S8 (2026-10-12):
  `.orchestration/context/sessions/01a13082-a8f9-7137-aa65-848f7e3c53c2/evidence/planning/ST-SKRIPT-40-03/plan.md`.
- Screen and area facts:
  `.orchestration/context/sessions/01a1495e-8398-75be-b2da-f0b08ba11afa/evidence/discovery/planning-facts-2026-10-17.md`.
- ST-SKRIPT-40-01: TASK-SKRIPT-40-01-02 (shared Vue subtree under
  `frontend/apps/skriptoteket/src/components/ui/shared/` and the 0.1.24 sync
  with the local shadow sweep) and TASK-SKRIPT-40-01-03 (package
  `action-buttons.css`; `main.css` carries no `.btn-*` rules).
- TASK-SKILL-REP-0279 (done): `huleedu-integrated` 0.1.24 ships without hard
  offset shadows, `.btn-brutal` or press offsets, and names the replacement
  treatment.
- ST-SKRIPT-40-04 owns the shell (`components/layout/`) and the exam workspace.
- TASK-SKRIPT-11-26-01 (in progress) refreshes the shared palette tokens and
  touches every area.
- Design authority: `huleedu-ui-design`; token and sync mechanics:
  `integrated-frontend-stack` and its Skriptoteket reference.

## Tasks

| Order | Task                 | Outcome                                                                                                      |
| ----- | -------------------- | ------------------------------------------------------------------------------------------------------------ |
| 0     | TASK-SKRIPT-40-01-02 | Prerequisite in ST-SKRIPT-40-01: shared components and the 0.1.24 sync with the local shadow sweep.          |
| 0     | TASK-SKRIPT-40-01-03 | Prerequisite in ST-SKRIPT-40-01: shared action-button stylesheet.                                            |
| 1     | TASK-SKRIPT-40-03-01 | Home, catalog, app detail, the tool run page and Mina körningar refreshed.                                   |
| 1     | TASK-SKRIPT-40-03-02 | Profile and Mina filer refreshed.                                                                            |
| 1     | TASK-SKRIPT-40-03-03 | Admin screens, the suggestion form, Mina verktyg, the editor hub and the script editor refreshed.            |
| 1     | TASK-SKRIPT-40-03-04 | Klassrumskartan, including its phone views, refreshed.                                                       |
| 1     | TASK-SKRIPT-40-03-05 | The document converter and the Ljudtranskribering mode of Conversion Hub refreshed.                          |
| 1     | TASK-SKRIPT-40-03-06 | Reagent Prep Chef refreshed.                                                                                 |
| 1     | TASK-SKRIPT-40-03-07 | The Hjälp panel, its topics, tutorial and MicroHelp refreshed.                                               |
| 1     | TASK-SKRIPT-40-03-08 | The sign-in, account and system pages refreshed, including the curated-app hosts.                            |
| any   | TASK-SKRIPT-40-03-09 | `.codex/rules` removed; every still-valid fact lives in its owning skill; instruction routes through skills. |

Order 1 tasks run in parallel. TASK-SKRIPT-40-03-09 may run any time before
TASK-SKRIPT-39-04-05 (S7), which ST-SKRIPT-40-04 replaces (G1).

## Verification

- Each area task passes its gate: an independent Sol review and a real browser
  walk with phone, tablet and desktop screenshots of its screens. There is no
  Opus step.
- Each area task's evidence lists every divergence from the shared core that
  the area keeps, for registration when TASK-SKILL-REP-0280 lands.
- TASK-SKRIPT-40-03-09 passes `pdm run skills-validate`, `pdm run docs-validate`
  and a tracked-file search that finds no `.codex/rules` reference outside this
  story and its task documents.

## Decided Contract Terms

| ID  | Decided contract term                                                                                                                                                                                                                                                                                                                                                                                              |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| G6  | Rolling freeze: only the area being worked on is frozen (bug fixes only); other areas keep shipping UI until their turn. Source: user 2026-10-17.                                                                                                                                                                                                                                                                  |
| G7  | Sol 6.1 agents do this refresh to the shared token package; it is transitional work with no greenfield UI design. Source: user 2026-10-17.                                                                                                                                                                                                                                                                         |
| G9  | Only the app shell (top bar, sidebar, page frame) and the exam workspace are greenfield Opus work; every other screen keeps its layout and gets the Sol 6.1 refresh onto shared tokens, buttons and components. Source: user 2026-10-17.                                                                                                                                                                           |
| G11 | The refresh starts right after TASK-SKRIPT-40-01-02 and 40-01-03; Sol pairs refresh areas in parallel; each area is frozen only while its pair works on it. Source: user 2026-10-17.                                                                                                                                                                                                                               |
| G12 | Refresh gate: independent Sol review plus a real browser walk with phone, tablet and desktop screenshots; no Opus step. Source: user 2026-10-17.                                                                                                                                                                                                                                                                   |
| S1  | One EPIC-SKRIPT-40 story brings every Skriptoteket screen onto the shared visual direction: panels and surfaces leave hard offset shadows and heavy frames for the shared panel and card treatment, with one token pass per area; G9 removes the exam workspace from this story. Source: retained plan S1 (user 2026-10-12), narrowed by G9.                                                                       |
| S3  | The old DigiExam converter views get only what arrives through shared classes and tokens and no layout work of their own; TASK-SKRIPT-39-07-03 retires them. Source: retained plan S3 (user 2026-10-12).                                                                                                                                                                                                           |
| S4  | The Flunk-Out Frenzy playfield canvas is out of scope; L6 also takes its page chrome out of this story. Source: retained plan S4 (user 2026-10-12), narrowed by L6.                                                                                                                                                                                                                                                |
| S5  | This story removes Skriptoteket's rule system: every still-valid fact under `.codex/rules` moves to the skill that owns its topic; `.codex/rules` and every rule reference are deleted; rule 045's design content is not carried over; CLAUDE.md names huleedu-ui-design for design work. Source: retained plan S5 (user 2026-10-12).                                                                              |
| S6  | The shared release drops hard offset shadows first: `huleedu-integrated` 0.1.24 from TASK-SKILL-REP-0279, with HuleEdu's own cleanup. Source: retained plan S6 (user 2026-10-12).                                                                                                                                                                                                                                  |
| S7  | The first 0.1.24 sync removes every local use of the removed shadow tokens, utilities, `.btn-brutal` and hover-lift or press transforms in the same commit, using hairline borders on flat surfaces, the existing soft shadow-md on floating layers and colour-only feedback. That sync now lives in TASK-SKRIPT-40-01-02. Source: retained plan S7 (user 2026-10-12); relocated in the 2026-10-17 planning round. |
| G29 | The restyle starts without waiting for TASK-SKILL-REP-0280: pairs remove every divergence from the shared core; any divergence they must keep is listed in the task evidence and registered when TASK-SKILL-REP-0280 lands. This replaces retained plan S8's wait and keeps S8's goal that Skriptoteket carries no local design drift. Source: user 2026-10-17.                                                    |
| L5  | Screens without an area task join one: `SuggestionNewView` joins TASK-SKRIPT-40-03-03; `ForbiddenView`, `RouteRecoveryView`, `AppHostView`, `PublicAppHostView` and `CuratedAppHostSurface` join TASK-SKRIPT-40-03-08. Source: lead 2026-10-17.                                                                                                                                                                    |
| L6  | G9 narrows G5: areas outside the app shell and the exam workspace keep their layout and need no prototype. The Flunk-Out Frenzy game, including its page chrome, stays out of this story by the plan the user confirmed on 2026-10-17, overriding S4's page-chrome scope. Source: lead 2026-10-17.                                                                                                                 |
