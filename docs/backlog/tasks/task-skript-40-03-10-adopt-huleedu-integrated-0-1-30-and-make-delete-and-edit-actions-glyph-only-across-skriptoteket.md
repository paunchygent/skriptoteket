---
type: task
id: TASK-SKRIPT-40-03-10
title: Adopt huleedu-integrated 0.1.30 and make delete and edit actions glyph-only
  across Skriptoteket
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-10-17'
status: done
closeout_review:
  record: inline
  status: approved
  reviewer: ruthless-reviewer
  decided_at: '2026-10-17'
  approval_protocol: agent-overseer:approved-review-closeout
  approval_evidence: 'Pi ruthless-reviewer 618d81fe reviewed TASK-SKILL-REP-0328 (aeb0df32, c0b67604, 728a41c2) and TASK-SKRIPT-40-03-10 (10046baf) together (retained session 01a149c9-5bc7-7713-ba64-12dee0470bdd, evidence/reviews/task-40-03-10-and-rep-0328-review-1.md): changes_requested with two medium findings, F1 remaining worded edit controls and F2 the over-limit PlannerClassWorkspace spec, and no finding on the shared package. Both were repaired on the Skriptoteket branch and, as medium findings, admitted by the parent on focused checks without rereview: full frontend Vitest 2606 passed, typecheck, ESLint, build and design-system-validate clean. User decisions 2026-10-17; the user asked for the work.'
task_kind: story
acceptance_criteria:
  - Every delete glyph action in Skriptoteket shows the glyph without a border or background square, except the worded Radera commits in the two planner modal footers
  - Every edit action in Skriptoteket is the edit glyph alone, with its tooltip and accessible name saying what it edits, and a toggle shows its open form through aria-expanded
  - The Mina kurser school-form checkboxes sit with clear space below the Skolformer label and above the course search box
story: ST-SKRIPT-40-03
backlog_document_profile: contract-derived
---

## Implementation Contract

User decisions 2026-10-17, made while reviewing the profile page on staging:

- Delete glyphs never sit in a bordered square; the glyph alone is visible
  enough. This applies everywhere.
- The `Ändra` word beside the edit glyph is pointless; an edit action is the
  glyph alone, everywhere in Skriptoteket.
- The Mina kurser school-form checkboxes are too cramped against the
  `Skolformer` label and the search box below.

This task delivers:

- Adoption of huleedu-integrated 0.1.30 (TASK-SKILL-REP-0328), where an
  icon-only `danger` action has a transparent border and background.
- Delete actions: the document converter's remove-file buttons take the
  `danger` tone; the exam-workspace criterion remove button and the planner
  share-link revoke button (icon-only on phones) lose their border; the
  Klassrumskartan overview `Radera` buttons (desktop and phone) become icon-only
  `Radera klasslistan` / `Radera klassrummet`.
- Edit actions: the profile section toggles become glyph-only with
  `aria-expanded`; the Klassrumskartan overview edit buttons become icon-only
  `Ändra klasslistan` / `Ändra klassrummet`; the exam converter's advisory edit
  button becomes glyph-only (`Ändra facit`, `Avbryt ändringen`).
- Mina kurser: the fieldset no longer cancels the section's vertical gap, and
  the checkbox row gets more space below the label.
- Review F1 repairs: the Mina verktyg and admin tool-list `Redigera` links
  become edit glyphs (`Redigera <verktyg>`); the advisory top-row edit button
  becomes glyph-only and the bottom toggle exposes `aria-expanded`; the
  instructions drawer's edit/preview switch becomes one glyph button
  (`Redigera instruktionerna` / `Förhandsgranska instruktionerna`); the Mina
  verktyg help text says to click the pen.
- Review F2 repair: `PlannerClassWorkspace.spec.ts` is split into overview,
  share-scope and task-entry specs with shared support.
- `ProfileAiSettingsPanel.vue` and `ProfileInlineField.vue` (and its spec),
  which nothing imports, are deleted.
- X/close controls that clear a selection stay as they are (D4).

## Contract Inputs

- TASK-SKILL-REP-0328 (huleedu-integrated 0.1.30 and the recorded decisions in
  `huleedu-ui-design`).

## Core Vertical And Performance

Presentation only; no behaviour or API changes.

## Validation

- Focused Vitest for the touched areas, frontend typecheck, ESLint, build and
  `pdm run design-system-validate`.
- Independent review covering this task and TASK-SKILL-REP-0328.
- A look at the profile page on staging after the merge.

## Stop Conditions

- None beyond the shared review gates.

## Decided Contract Terms

| ID  | Decided contract term |
| --- | --------------------- |
| D1  | Delete glyph actions have no border or background square anywhere (user 2026-10-17). The worded `Radera` buttons in the two planner modal footers stay, because they commit a destructive action beside Spara and Avbryt. |
| D2  | Edit actions are the edit glyph alone, everywhere in Skriptoteket (user 2026-10-17). |
| D3  | The Mina kurser school-form checkboxes get more, but not much more, space above and below (user 2026-10-17). |
| D4  | Non-delete icon-only buttons keep their current border until the user decides otherwise. |

Follow-up the same day (user decision): huleedu-integrated 0.1.31 draws every
icon-only default action and glyph edit trigger without a frame, and the Mina
kurser delete glyph is 12px and centred on the section pens above it.
