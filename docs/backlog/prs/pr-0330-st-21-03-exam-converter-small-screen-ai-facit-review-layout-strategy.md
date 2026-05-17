---
type: pr
id: PR-0330
title: "ST-21-03 Exam Converter small-screen AI-facit review layout strategy"
status: ready
owners: "agents"
created: 2026-05-17
updated: 2026-05-17
stories:
  - "ST-21-03"
tags:
  - frontend
  - ux
  - authenticated
  - conversion-hub
  - small-screen
  - reviewed-completion
acceptance_criteria:
  - "Given the authenticated Exam Converter AI-facit review state renders below the phone breakpoint, when the teacher opens the view, then Skriptoteket uses a phone-specific review flow instead of the tablet/narrow-laptop two-column navigator and detail composition."
  - "Given the tablet breakpoint renders, when the teacher reviews AI-facit, then Skriptoteket keeps the tablet/narrow-laptop composition distinct from the phone branch and does not inherit phone-only bottom sheets, one-column detail routing, or compressed action docks."
  - "Given desktop and laptop widths render, when this slice is implemented, then the existing table-plus-detail and narrow-laptop navigator-plus-detail compositions remain protected and are not flattened into stacked phone cards."
  - "Given valid AI-facit suggestions exist, when the phone layout renders, then `Granska`, per-question approve/leave/edit where supported, `Godkänn alla`, and `Skapa filer` remain reachable with readable labels, stable touch targets, and no horizontal document overflow."
  - "Given the teacher applies reviewed suggestions, when the phone branch emits actions, then it uses the existing reviewed-completion overlay state and submit path without creating phone-only data, storage, or Sir Convert contract logic."
---

# PR-0330: ST-21-03 Exam Converter Small-Screen AI-Facit Review Layout Strategy

## Problem

The current AI-facit review UI inherits the `max-width: 1199px` reduced
navigator/detail layout on true phone screens. That layout was designed for
tablet and narrow laptop proof, not for a 390px class viewport. On an iPhone
screenshot from 2026-05-17, the action panel collapses into unreadable
fragments: the icon, explanatory text, `Granska`, and `Godkänn alla` compete
inside a desktop-like horizontal grid, while the content surface itself is
wider than the browser viewport.

This is not a tuning bug in a fluid responsive layout. It is a breakpoint
contract bug: phone, tablet/narrow-laptop, and desktop are different
compositions. The design philosophy must match Klassrumskartan: responsive
within a breakpoint, not across breakpoints.

## Goal

Define and implement a phone-specific authenticated Exam Converter AI-facit
review flow while preserving the existing tablet/narrow-laptop and desktop
compositions.

The phone branch should be a reduced companion workflow:

- one primary surface at a time;
- no side-by-side navigator/detail layout;
- compact top context and tab state;
- a question queue for scan/select;
- a single-question review surface for the selected item;
- sticky or bottom-docked high-commitment actions only where they remain
  readable and reachable; and
- the same shared AI-facit review state, overlay builder, and Sir Convert
  Gateway submit path as tablet and desktop.

## Breakpoint Strategy

Use explicit named compositions instead of one fluid responsive chain:

| Composition | Viewport contract | Intended behavior |
|---|---:|---|
| Phone | `max-width: 767px` | Dedicated one-surface review flow; no table, no side-by-side detail, no three-action horizontal header grid. |
| Tablet / narrow laptop | `768px-1199px` | Reduced navigator plus visible detail pane; no phone bottom-sheet routing. |
| Laptop / desktop | `min-width: 1200px` | Dense table plus selected-question detail pane; current desktop scanning behavior is preserved. |

Tailwind range variants may be used for bounded utility changes, for example
`md:max-xl:*`, but structural composition should live in focused CSS or
separate Vue components with CSS owning breakpoint geometry. Vue conditional
rendering may choose named layout components, but JavaScript must not measure
viewport width or own persistent layout geometry.

## Recommended Component Shape

Keep the domain state shared and split only the presentation branch:

- `ExamConverterQuestionReviewShell.vue` remains the desktop/tablet shell.
- Add a phone-only presentation component, for example
  `ExamConverterPhoneQuestionReviewFlow.vue`, rendered only below `768px`.
- Reuse `ExamConverterQuestionNavigator` row semantics where useful, but do
  not force the existing navigator to be both phone queue and tablet rail if it
  makes either branch unclear.
- Keep per-question AI-facit decisions in `useExamConverterAiFacitReview.ts`.
- Keep overlay construction and reviewed apply submit unchanged.
- Move only layout and phone-specific control placement into the phone branch.

The phone layout should default to the question queue and open a focused
question-review surface for the selected row. `Skapa filer` should appear only
when reviewed suggestions can actually be applied; it must not imply that the
first advisory bundle unlocked files locally.

## Non-goals

- No Sir Convert producer changes.
- No HuleEdu Gateway/auth changes.
- No phone-only reviewed-completion overlay shape.
- No JavaScript viewport measurement for persistent layout.
- No attempt to make every desktop operation simultaneously visible on phone.
- No broad Conversion Hub redesign outside the authenticated Exam Converter
  AI-facit review state.

## Implementation Plan

1. Confirm the UI content model and this strategy with the product owner before
   changing production UI code.
2. Add or extend a focused test-code specification for the small-screen
   AI-facit review slice. The test must describe teacher-visible phone behavior,
   not just selectors.
3. Add a phone-specific branch below `768px` for the authenticated question
   review state:
   - queue/list state;
   - selected-question detail state;
   - valid AI-facit suggestion state;
   - accepted/left decision state; and
   - reviewed apply ready/running/blocked state.
4. Keep tablet/narrow-laptop at `768px-1199px` on the existing
   navigator/detail composition, then harden it with proof so phone changes do
   not leak upward.
5. Keep desktop at `min-width: 1200px` on the existing table/detail
   composition.
6. Update the internal-browser fixture proof to cover:
   - `phone`: `390x844` or equivalent iPhone portrait viewport;
   - `tablet`: `768x1024`;
   - `narrow-laptop`: `1024x768`; and
   - `desktop`: `1440x900`.
7. Record whether the phone branch, tablet branch, and desktop branch are
   active; record no horizontal document overflow; retain screenshots or DOM
   evidence.
8. Update `.codex/handoff.md` and the relevant `ST-21-03` docs with the final
   proof status.

## Test Plan

- Focused Vitest coverage for phone branch rendering:
  - phone queue appears instead of desktop table;
  - phone detail view shows one selected question and valid AI-facit actions;
  - bulk accept and reviewed apply actions emit the same events as desktop;
  - file/report tabs remain reachable without stacked desktop panels; and
  - provider/internal wording remains hidden.
- Regression coverage for tablet and desktop:
  - tablet/narrow-laptop keeps navigator plus detail;
  - desktop keeps table plus detail;
  - accepted suggestions still build the shared reviewed-completion overlay.
- Live internal-browser proof through the governed fixture lane at the named
  viewports above.

Closeout commands:

```bash
pdm run fe-test -- --run src/views/apps/ExamConverterAuthenticatedReviewSlice.spec.ts src/views/apps/ExamConverterAuthenticatedUiInspectionFixtures.spec.ts
pdm run fe-type-check
pdm run fe-lint
pdm run fe-build
pdm run docs-validate
pdm run handoff-validate
git diff --check
```

## Rollback Plan

Remove the phone-only presentation branch and its CSS/test proof while keeping
the shared AI-facit review state, overlay construction, and existing
tablet/desktop shells. The Sir Convert Gateway client and reviewed-completion
contract must remain untouched.
