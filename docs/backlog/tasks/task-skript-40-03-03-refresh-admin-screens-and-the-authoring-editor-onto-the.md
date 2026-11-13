---
type: task
id: TASK-SKRIPT-40-03-03
title: Refresh admin screens and the authoring editor onto the shared tokens and components
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
  approval_evidence: 'Pi ruthless-reviewer (Sol) approvals in the retained session 01a149c9-5bc7-7713-ba64-12dee0470bdd, evidence/reviews/TASK-SKRIPT-40-03-03/: the area review, review 3b4d672a''s other items and rereview da8419e4 of the shared dialog focus repair (9334a739, da8419e4); merged to main fdc2973b. The Mac parent''s staging walk on 1c133433 found batch-1 items 4 and 5; their repairs close on adversarial unit specs and approved review under the user''s 2026-10-17 rule that parent walks cover only the exam converter. The parent authorized closure.'
task_kind: story
acceptance_criteria:
  - The admin screens, the suggestion form, Mina verktyg, the editor hub and the script editor render with the shared tokens, action buttons and components and no hard offset shadows, keep their layout, and pass a browser walk at phone, tablet and desktop widths
dependencies:
  - TASK-SKRIPT-40-01-02
  - TASK-SKRIPT-40-01-03
story: ST-SKRIPT-40-03
backlog_document_profile: contract-derived
---

## Implementation Contract

The admin screens, the suggestion form, Mina verktyg, the editor hub and the script editor keep their layout and move onto the shared package that
ST-SKRIPT-40-01 adopted. Paths are under `frontend/apps/skriptoteket/src/`.

Screens and folders:

- Admin: `views/admin/AdminToolsView.vue`, `views/admin/AdminUsersView.vue`,
  `views/admin/AdminUserDetailView.vue`,
  `views/admin/AdminSuggestionsListView.vue`,
  `views/admin/AdminSuggestionDetailView.vue` and `components/admin/`.
- Suggestion form (`/suggestions/new`): `views/SuggestionNewView.vue`.
- Mina verktyg (`/my-tools`): `views/MyToolsView.vue` and
  `components/tools/ToolListRow.vue`, which the suggestions list also uses.
- Editor hub (`/editor`): `views/editor/EditorHubView.vue`.
- Script editor (`/admin/tools/:toolId`, `/admin/tool-versions/:versionId`):
  `views/admin/ScriptEditorView.vue`, `components/editor/` and the button
  classes built in `composables/editor/`.

What changes:

- Colours, surfaces, borders and type use the shared tokens through
  token-mapped utilities or CSS variables.
- Every button renders from the package action-button stylesheet adopted by
  TASK-SKRIPT-40-01-03 or from a shared dense button component in
  `components/ui/shared/`. Local button styling (including button classes built in `composables/editor/`) and local
  overrides of the `.btn-*` classes go.
- Where the area hand-rolls a control that the shared subtree exports (dense
  action, icon and status components, spinner, segmented toggle,
  SystemMessage), it uses the shared component.
- Panels, cards and surfaces carry no hard offset shadow and no heavy frame:
  flat surfaces use hairline borders, floating layers the soft shadow-md, and
  press and hover feedback is colour only.

What stays: the placement and order of every element, the breakpoints and the
workflow.

Out of scope: `components/layout/` (the shell) and the exam workspace, both ST-SKRIPT-40-04.

Coordination: TASK-SKRIPT-14-32-01 (in progress) changes the editor's selectors and
its Testkör, Metadata and Diff panels. This area is frozen only while its
refresh pair works on it.

## Contract Inputs

- ST-SKRIPT-40-03 terms G6, G7, G9, G11, G12, G29, S1 and S7.
- TASK-SKRIPT-40-01-02 (shared Vue subtree and the 0.1.24 sync with the local
  shadow sweep) and TASK-SKRIPT-40-01-03 (package action buttons).
- `huleedu-ui-design` for the panel, card, button and token treatment;
  `integrated-frontend-stack` for token mechanics.
- Area facts:
  `.orchestration/context/sessions/01a1495e-8398-75be-b2da-f0b08ba11afa/evidence/discovery/planning-facts-2026-10-17.md`.

## Core Vertical And Performance

An admin opens the tool list, a user and a suggestion; a user sends a
suggestion through the suggestion form; a script author opens
Mina verktyg, the editor hub and a tool in the script editor, uses the chat
drawer and runs a test. Every screen has the same layout as before; buttons, panels and
status markers come from the shared package. No request or data flow changes,
and no material performance concern is identified.

## Validation

- Focused Vitest: `pdm run fe-test` with the existing specs of the listed views and folders (for example the
  specs under `components/editor/`), updated where they assert
  removed local classes.
- `pdm run fe-type-check` and `pdm run fe-build`.
- The task evidence lists every divergence from the shared core that the area keeps, for registration when TASK-SKILL-REP-0280 lands (ST-SKRIPT-40-03 G29).
- Gate: an independent Sol review and a real browser walk (Hemma,
  `staging-walk`) of the admin tool, user and suggestion screens, the suggestion form, Mina verktyg, the editor hub and the script editor with phone, tablet and desktop screenshots. No Opus
  step.

## Stop Conditions

- A screen cannot take a shared token, button or component without a layout
  change: stop and report to the user.
- The shared package lacks a token, button variant or component the area needs:
  report it upstream; do not patch synced files or add a local fork.

## Decided Contract Terms

| ID  | Decided contract term                                                                                                                                                                                                                                                                |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| G9  | The admin screens, the suggestion form, Mina verktyg, the editor hub and the script editor keep their layout and get the Sol 6.1 refresh onto shared tokens, buttons and components. Source: ST-SKRIPT-40-03 G9 (user 2026-10-17).                                                   |
| G7  | A Sol 6.1 pair does the refresh; it is transitional work with no greenfield UI design. Source: ST-SKRIPT-40-03 G7 (user 2026-10-17).                                                                                                                                                 |
| G11 | The task starts right after TASK-SKRIPT-40-01-02 and 40-01-03 and runs in parallel with the other areas; the area is frozen only while its pair works on it. Source: ST-SKRIPT-40-03 G11 and G6 (user 2026-10-17).                                                                   |
| G12 | Gate: independent Sol review plus a real browser walk with phone, tablet and desktop screenshots; no Opus step. Source: ST-SKRIPT-40-03 G12 (user 2026-10-17).                                                                                                                       |
| S1  | Panels and surfaces leave hard offset shadows and heavy frames for the shared panel and card treatment, with one token pass for the area. Source: ST-SKRIPT-40-03 S1 (user 2026-10-12).                                                                                              |
| S7  | The 0.1.24 sync and the removal of local shadow tokens, utilities, `.btn-brutal` and press or hover-lift transforms happen in TASK-SKRIPT-40-01-02, with hairline borders, soft shadow-md on floating layers and colour-only feedback. Source: ST-SKRIPT-40-03 S7 (user 2026-10-12). |
| L5  | `SuggestionNewView`, which had no area task, joins this task. Source: ST-SKRIPT-40-03 L5 (lead 2026-10-17).                                                                                                                                                                          |
