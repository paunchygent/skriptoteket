---
type: task
id: TASK-SKRIPT-40-03-05
title: Refresh Conversion Hub document and transcript tools onto the shared tokens and components
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: '2026-10-17'
status: in_progress
closeout_review:
  record: inline
  status: not_started
task_kind: story
acceptance_criteria:
  - The document converter and the transcript mode of Conversion Hub render with the shared tokens, action buttons and components and no hard offset shadows, keep their layout, and pass a browser walk at phone, tablet and desktop widths
dependencies:
  - TASK-SKRIPT-40-01-02
  - TASK-SKRIPT-40-01-03
story: ST-SKRIPT-40-03
backlog_document_profile: contract-derived
---

## Implementation Contract

The document converter and the Ljudtranskribering mode of Conversion Hub keep their layout and move onto the shared package that
ST-SKRIPT-40-01 adopted. Paths are under `frontend/apps/skriptoteket/src/`.

Screens and folders:

- Document converter (`/apps/document-converter`):
  `views/apps/document-converter/`, including `documentConverterWorkspace.css`
  and `documentConverterPreview.css`.
- Ljudtranskribering: `views/apps/conversion-hub-transcript/`, including the
  local button class builder `transcriptCommandButtonClasses.ts`.

What changes:

- Colours, surfaces, borders and type use the shared tokens through
  token-mapped utilities or CSS variables.
- Every button renders from the package action-button stylesheet adopted by
  TASK-SKRIPT-40-01-03 or from a shared dense button component in
  `components/ui/shared/`. Local button styling (including `transcriptCommandButtonClasses.ts`) and local
  overrides of the `.btn-*` classes go.
- Where the area hand-rolls a control that the shared subtree exports (dense
  action, icon and status components, spinner, segmented toggle,
  SystemMessage), it uses the shared component.
- Panels, cards and surfaces carry no hard offset shadow and no heavy frame:
  flat surfaces use hairline borders, floating layers the soft shadow-md, and
  press and hover feedback is colour only.

What stays: the placement and order of every element, the breakpoints and the
workflow.

The transcript mode is mounted by `views/apps/ExamConverterAuthenticatedView.vue`,
the old exam converter host that TASK-SKRIPT-39-07-03 retires. This task
refreshes the transcript folder, not that host.

Out of scope: `components/layout/` (the shell) and the exam workspace, both ST-SKRIPT-40-04; the old exam converter screens (`ExamConverterAuthenticatedView.vue`, `exam-converter*/`), which get only what the shared sync delivers.

Coordination: no in-progress UI task is recorded for this area.
TASK-SKRIPT-39-07-03 retires the host that mounts the transcript mode. This
area is frozen only while its refresh pair works on it.

## Contract Inputs

- ST-SKRIPT-40-03 terms G6, G7, G9, G11, G12, G29, S1 and S7.
- TASK-SKRIPT-40-01-02 (shared Vue subtree and the 0.1.24 sync with the local
  shadow sweep) and TASK-SKRIPT-40-01-03 (package action buttons).
- `huleedu-ui-design` for the panel, card, button and token treatment;
  `integrated-frontend-stack` for token mechanics.
- Area facts:
  `.orchestration/context/sessions/01a1495e-8398-75be-b2da-f0b08ba11afa/evidence/discovery/planning-facts-2026-10-17.md`.

## Core Vertical And Performance

A teacher converts a single document and a project in the document converter,
previews and saves the result, then switches Conversion Hub to
Ljudtranskribering, transcribes a file and exports the transcript. Every screen has the same layout as before; buttons, panels and
status markers come from the shared package. No request or data flow changes,
and no material performance concern is identified.

## Validation

- Focused Vitest: `pdm run fe-test` with the existing specs under `views/apps/document-converter/` and
  `views/apps/conversion-hub-transcript/` and
  `views/apps/ConversionHubTranscriptMode.spec.ts`, updated where they assert
  removed local classes.
- `pdm run fe-type-check` and `pdm run fe-build`.
- The task evidence lists every divergence from the shared core that the area keeps, for registration when TASK-SKILL-REP-0280 lands (ST-SKRIPT-40-03 G29).
- Gate: an independent Sol review and a real browser walk (Hemma,
  `staging-walk`) of the document converter and the Ljudtranskribering mode with phone, tablet and desktop screenshots. No Opus
  step.

## Stop Conditions

- A screen cannot take a shared token, button or component without a layout
  change: stop and report to the user.
- The shared package lacks a token, button variant or component the area needs:
  report it upstream; do not patch synced files or add a local fork.
- TASK-SKRIPT-39-07-03 moves or removes the transcript mode's host while this
  task runs: report to the user before continuing.

## Decided Contract Terms

| ID  | Decided contract term                                                                                                                                                                                                                                                                |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| G9  | The document converter and the Ljudtranskribering mode of Conversion Hub keep their layout and get the Sol 6.1 refresh onto shared tokens, buttons and components. Source: ST-SKRIPT-40-03 G9 (user 2026-10-17).                                                                     |
| G7  | A Sol 6.1 pair does the refresh; it is transitional work with no greenfield UI design. Source: ST-SKRIPT-40-03 G7 (user 2026-10-17).                                                                                                                                                 |
| G11 | The task starts right after TASK-SKRIPT-40-01-02 and 40-01-03 and runs in parallel with the other areas; the area is frozen only while its pair works on it. Source: ST-SKRIPT-40-03 G11 and G6 (user 2026-10-17).                                                                   |
| G12 | Gate: independent Sol review plus a real browser walk with phone, tablet and desktop screenshots; no Opus step. Source: ST-SKRIPT-40-03 G12 (user 2026-10-17).                                                                                                                       |
| S1  | Panels and surfaces leave hard offset shadows and heavy frames for the shared panel and card treatment, with one token pass for the area. Source: ST-SKRIPT-40-03 S1 (user 2026-10-12).                                                                                              |
| S7  | The 0.1.24 sync and the removal of local shadow tokens, utilities, `.btn-brutal` and press or hover-lift transforms happen in TASK-SKRIPT-40-01-02, with hairline borders, soft shadow-md on floating layers and colour-only feedback. Source: ST-SKRIPT-40-03 S7 (user 2026-10-12). |
