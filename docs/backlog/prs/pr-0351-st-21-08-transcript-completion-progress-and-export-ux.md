---
type: pr
id: PR-0351
title: "ST-21-08 Transcript completion, progress, and export UX"
status: ready
owners: "agents"
created: 2026-06-14
updated: 2026-06-14
stories:
  - "ST-21-08"
tags:
  - frontend
  - transcript
  - conversion-hub
  - progress
  - export
  - ux
dependencies:
  - "PR-0350"
  - "MOCK-pr-0351-transcript-progress-export-ux"
  - "Sir Convert task-364 for improved STT phase progress/telemetry where new producer fields are required"
acceptance_criteria:
  - "Given a teacher starts transcript conversion, when upload/admission and STT work are in progress, then the UI shows a stable progress layout with normal Swedish copy, measured progress/ETA where available, elapsed time, and no spinner-only or dead 0% presentation."
  - "Given a transcript finishes successfully, when the completed transcript view appears, then the transcript is saved automatically and the teacher lands directly in the useful transcript workspace without a generic manual Spara gate."
  - "Given the completed transcript workspace is shown, when speaker names and export controls render, then the transcript keeps real reading width and the inspector follows the approved mockup hierarchy without redundant labels, cramped middle columns, or calculator-like export button rows."
  - "Given export formats are available, when the teacher selects TXT, MD, VTT, or SRT, then the UI offers stable one-line actions Ladda ner and Mina filer for the selected format without duplicating download affordances or interpolating the selected format into action labels."
  - "Given warning, pending, running, failed, or recovery states are needed, when they render, then they use reserved layout or separately planned state layouts and never appear as hidden jump-scare rows that push surrounding controls."
  - "Given implementation is complete, when focused tests and live proof run, then old manual-save/export-gate copy and browser-owned replay/download/base64 behavior remain absent."
---

# PR-0351: ST-21-08 Transcript Completion, Progress, And Export UX

## Problem

The transcript lane is now architecturally product-owned after `PR-0350`, but
the teacher-facing workflow still carries confusing legacy UX:

- upload/admission and STT phases can look frozen or dead for short/few-chunk
  jobs;
- completion lands behind a generic manual `Spara` gate even though saving is
  not a meaningful teacher choice at that moment;
- speaker naming and export affordances appear too late and with unclear
  hierarchy;
- export controls have repeatedly drifted into duplicated download/save
  actions, metadata cards, dropdown symbols without menus, and cramped button
  rows;
- warning/status rows risk appearing dynamically and moving the layout.

The approved mockup direction now defines the product hierarchy and the
lessons learned from design review. This PR turns that direction into the
runtime transcript workspace.

## Goal

Make the transcript lane feel alive, direct, and product-owned:

- conversion progress is stable and understandable;
- completed transcripts autosave and open into the actual workspace;
- speaker naming and export actions are visible as the useful next work;
- exports have one selected format and two stable actions: `Ladda ner` and
  `Mina filer`;
- layout does not jump when status, failure, or warning state changes.

## Non-goals

- No chunk-size or batch-size tuning in Skriptoteket.
- No browser-owned Sir Convert submit/poll/download/base64/complete saga.
- No local TXT/Markdown/VTT/SRT formatter fallback.
- No manual save gate after a successful transcript conversion.
- No Swenglish/internal phase copy such as `diariserar` or raw producer stage
  names in teacher-facing UI.
- No hidden status, warning, or recovery row that appears later and pushes
  controls around.
- No new product promise that the teacher can leave or use other parts of the
  service unless the implementation has verified that behavior.

## Governing Mockup

Use the approved mockup bundle as qualitative product direction:

- `docs/mockups/pr-0351-transcript-progress-export-ux/README.md`
- `docs/mockups/pr-0351-transcript-progress-export-ux/index.html`

The implementation must preserve the state hierarchy and interaction contract;
it does not need to pixel-match the static HTML.

Mockup lessons that are part of this PR contract:

- Do not show the transcript/export workspace while the transcript does not
  exist. The running state is a conversion-progress workspace, not a preview of
  later controls.
- Do not use an `Avbryt efter klar` concept. Running work has one clear
  `Avbryt` action only where cancellation is actually possible.
- Avoid internal terms. Use normal Swedish such as `Hittar talare`, `Skriver ut
  samtalet`, and `Gör texten klar`.
- Do not add explanatory marketing/helper text unless it states verified
  product behavior.
- Do not add redundant labels such as `Talarnamn` and `Export` inside an
  inspector already titled `Talare och export`.
- Do not duplicate download controls. Format selection is one control; actions
  are `Ladda ner` and `Mina filer`.
- Do not interpolate selected file formats into visible action labels; `TXT`,
  `MD`, `VTT`, or `SRT` belongs in the format selector, not as a dynamic
  two-line button label.

## Implementation Plan

1. Audit the current transcript workspace components and API clients after
   `PR-0350`, especially completion/save state, progress rendering, speaker
   overlay editing, formatter export state, download action, and Mina filer
   action.
2. Add red-first frontend tests for the approved UX contract:
   - running progress does not render as a dead 0% single-chunk surface;
   - transcript completion autosaves and skips the generic `Spara` gate;
   - old copy/actions such as primary `Spara`, `Skapa exportfiler`, `Skapa
     igen`, and `Skapa transkript igen` are absent from the normal path;
   - export controls expose one selected format and stable `Ladda ner` /
     `Mina filer` actions.
3. Update the progress rendering to consume the current product/Sir Convert
   progress fields and, after Sir Convert `task-364`, prefer the new measured
   phase progress/ETA fields when present.
4. Refactor the completed workspace around the approved hierarchy:
   transcript reading surface plus right-side inspector, with responsive
   breakpoints that preserve transcript width before moving the inspector.
5. Remove the manual save gate from successful transcript completion and make
   autosave/readback the normal completed-state transition.
6. Replace export UI affordance drift with the approved format selector plus
   two stable one-line actions.
7. Add explicit reserved state handling for pending/running/failed export or
   save states so messages do not pop in and move controls.
8. Run focused frontend tests, focused backend tests if DTO/API behavior
   changes, browser proof through the sanctioned HuleEdu ceremony, and docs
   closeout.

## Test Plan

- Focused Vitest for transcript host/workspace rendering:
  - upload/admission/STT progress states;
  - autosave completion path;
  - absence of manual `Spara` gate and old export labels;
  - stable export action labels and no duplicate download controls;
  - no hidden jump-scare state rows.
- Focused API/client tests if DTOs or generated types change.
- Focused backend tests only if product export/save state contracts change.
- Live browser proof through the HuleEdu browser-session ceremony only,
  recording:
  - upload/admission/progress state;
  - autosaved transcript completion;
  - speaker rename/readback;
  - format selection;
  - download and Mina filer actions for a representative format;
  - failure/pending layout proof if feasible without destructive actions.
- Required closeout:

```bash
pdm run fe-test -- --run <focused transcript workspace specs>
pdm run fe-type-check
pdm run fe-lint
pdm run fe-build
pdm run docs-validate
pdm run handoff-validate
git diff --check
```

If backend or DTO surfaces change, also run:

```bash
pdm run test <focused backend transcript/export tests>
pdm run lint
pdm run typecheck
pdm run fe-gen-api-types
```

## Rollback Plan

Hide or disable the redesigned transcript/export controls while preserving
saved transcript readback and existing product-owned export endpoints. Do not
restore the browser-owned Sir Convert saga, local formatter fallback, or manual
generic `Spara` gate.
