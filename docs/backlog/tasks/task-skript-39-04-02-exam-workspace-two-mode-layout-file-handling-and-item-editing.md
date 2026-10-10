---
type: task
id: TASK-SKRIPT-39-04-02
title: 'Exam workspace two-mode layout: file handling and item editing'
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-10-10'
status: in_progress
closeout_review:
  record: inline
  status: not_started
task_kind: story
acceptance_criteria:
- A teacher converts a DOCX exam into an Exam.net-ready QTI export and edits any item
  in a desktop-first two-mode workspace without page-long scrolling, at every review
  viewport
story: ST-SKRIPT-39-04
backlog_document_profile: contract-derived
---

## Implementation Contract

Rebuild the exam workspace (`/apps/exam-workspace`) around what the teacher
does: convert a DOCX exam into a QTI export that Exam.net imports exactly as
intended, and edit any item along the way without friction. Remove what makes
that workflow harder without a good reason; add what makes it easier.

- Two modes, switched by a mode selector in one stable toolbar:
  - **Filer**: import (DOCX now; PDF, Markdown and other sources later),
    saved exams and versions, save, reload, QTI/PDF/DOCX export with
    per-item blockers, document notes.
  - **Redigera**: item selection on the left and one large, dominating
    editor. Item metadata (review reasons, answer-key proposals, the item's
    export blockers, QTI-specific fields) lives in a drawer the teacher opens
    when needed, not in a third standing panel.
- Save state (unsaved marker, version, Spara) stays visible in both modes.
- Mode selection replaces expansions and extra clicks; no accordions or
  disclosure panels for primary work.
- Editing an item is natural: no line-break workarounds and no stack of
  per-segment fields to read or change a question.
- The editor never lets the teacher produce an item that breaks the Exam.net
  contract: Exam.net must accept every exported item as the teacher expects,
  never drop it or turn it into a free-text question. Invalid states are
  prevented or explained in Swedish at the item, not discovered at export.

## Contract Inputs

- ST-SKRIPT-39-04, ADR-SKRIPT-0091, TASK-SKRIPT-39-04-01 (workspace surface,
  item editor, export gate, answer-key proposals).
- `.codex/rules/045-huleedu-design-system.md` (operational density,
  desktop-first, surface cohesion).
- ADR-SKRIPT-0020 breakpoints: `--huleedu-bp-md` 768px, `--huleedu-bp-lg`
  1024px.
- Klassrumskartan workspace UI doctrine (2026-03-28) and the ST-29
  small-screen direction (mode sheet on phone).
- Existing dense shells to reuse rather than reinvent: the document
  converter workbench (stable top row, panel-internal scroll) and the
  planner workspace shell.

## Core Vertical And Performance

`Filer: import DOCX -> Redigera: select item, edit, resolve blockers in the
drawer -> Filer: save -> export QTI -> Exam.net import as expected`.

- Desktop (>= 1024px) is the canonical composition: toolbar plus two panels
  filling the viewport below the app header. The page does not scroll; the
  item list scrolls internally, and the editor scrolls only when one item is
  taller than the panel. Below a minimum usable height the page falls back to
  normal scrolling instead of squeezing panels. The minimum is a 35rem
  (560px) frame: on shorter viewports the frame keeps 35rem and the page
  scrolls.
- Tablet (768-1023px): the same two panels with a narrower item list; the
  metadata drawer overlays the editor; toolbar actions overflow into a menu.
- Phone (< 768px): a reduced port. The editor is the screen, with an item
  selector and previous/next in the toolbar; Filer is its own mode. No list
  above the editor.
- No new backend state or endpoints are needed for the layout itself.

## Validation

- Agent-driven browser walk on Hemma staging through the HuleEdu ceremony at
  1440x900, 1366x768, 768x1024 and 390x844, recorded in `handoff.md`.
- The walk gate is user-friendliness: at each viewport, convert the real
  DOCX fixture, edit items of every present kind, resolve blockers, save,
  export QTI and inspect it; record every point of friction (extra clicks,
  page-long scroll, cramped editing, unexplained refusal) as a finding.
- QTI exports pass the existing fail-closed validators unchanged.
- Focused Vitest slices keep every existing `data-test` behavior; layout
  selection is testable without media queries.
- Frontend typecheck, lint and build pass.

## Stop Conditions

- Stop if a change would weaken the Exam.net contract or the export gate.
- Stop if the layout requires a third standing panel on desktop.
- Production acceptance remains user-owned.

## Decided Contract Terms

| ID  | Decided contract term |
| --- | --------------------- |
| L1 | Two modes, Filer and Redigera, switched in one stable toolbar; no three-panel desktop layout (user decision 2026-10-10). |
| L2 | Redigera is item selection on the left plus a dominating editor; item metadata lives in an on-demand drawer (user decision 2026-10-10). |
| L3 | Mode selection over expansions and extra clicks; no page-long scrolling; internal scroll only for long lists and oversized items (user decision 2026-10-10). |
| L4 | Desktop-first; tablet and phone receive their own reduced layouts, with the phone editor as its own screen behind an item selector (user decision 2026-10-10). |
| L5 | The editor cannot produce items that break the Exam.net contract; Exam.net accepting the test as the teacher expects is the final gate (user decision 2026-10-10). |
| L6 | The browser walk judges user-friendliness at every review viewport (user decision 2026-10-10). |
| L7 | Gap-fill items are edited as one continuous question text with each gap as an inline chip; activating a chip edits that gap's accepted answers in place (user decision 2026-10-10). |
| L8 | On phones, the Redigera toolbar shows "Fråga N av M" with previous/next; the label opens a bottom-sheet list of every question with type, points and review status (ST-29 pattern) (user decision 2026-10-10). |
