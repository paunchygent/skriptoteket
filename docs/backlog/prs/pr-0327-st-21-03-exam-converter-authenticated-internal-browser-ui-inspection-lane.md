---
type: pr
id: PR-0327
title: "ST-21-03 Exam Converter authenticated internal-browser UI inspection lane"
status: done
owners: "agents"
created: 2026-05-17
updated: 2026-05-17
stories:
  - "ST-21-03"
tags:
  - frontend
  - authenticated
  - conversion-hub
  - exam-converter
  - browser-proof
  - ui-fixtures
acceptance_criteria:
  - "Given an agent must inspect authenticated Exam Converter post-conversion UI in the Codex internal browser, when the state normally requires local file upload, then a governed dev/test-only fixture lane renders the real authenticated components without relying on unsupported in-browser file upload."
  - "Given the fixture lane is available, when an agent opens the internal browser at approved viewport widths, then it can inspect the real dense workspace layout for success, partial, blocked-QTI, missing-facit, files, and report states without adding throwaway query hooks."
  - "Given the lane is dev/test-only, when production code is built or deployed, then fixture access is disabled by environment/build-time guard and cannot create a user-visible debug backdoor."
  - "Given future Exam Converter UI changes touch layout or breakpoint behavior, when the change is closed out, then the handoff records the internal-browser route/state, viewport widths, screenshots or DOM evidence, and the focused test commands that protect the approved UI slice."
  - "Given the frontend build runs on newer system Node versions, when agents run `pdm run fe-build`, then the Tailwind Vite integration is retained and the checked-in pnpm patch prevents the deprecated Node `module.register()` cache-loader path from emitting the Node 26 `DEP0205` warning during normal closeout."
---

# PR-0327: ST-21-03 Exam Converter Authenticated Internal-Browser UI Inspection Lane

## Problem

Authenticated Exam Converter UI work currently depends on post-conversion
states that are reached by uploading `.dxe` files and optional result PDFs. The
Codex internal browser is the required surface for live visual inspection during
interactive UI work, but it cannot drive native file chooser uploads. That
makes upload-first flows hard to inspect without either switching to a separate
automation lane or adding temporary state hooks.

Temporary query parameters, debug component mutation, or browser-local state
injection are not acceptable for this product surface. They are easy to leave
behind, bypass the approved UI slice model, and do not give future agents a
repeatable way to inspect the same dense workspace states.

## Goal

Create a durable, documented dev/test-only UI inspection lane for authenticated
Exam Converter states. The lane must let agents use the Codex internal browser
to inspect the real authenticated view and its real child components at approved
viewport widths without needing browser file upload support.

The lane should cover at least these teacher-visible states:

- all questions complete, PDF and QTI available;
- all questions complete but QTI blocked with a surfaced readiness reason;
- missing facit or poäng with item-addressable review state;
- AI-suggested facit ready for teacher review;
- files tab with enabled and blocked file actions;
- report tab with producer warnings and manual-follow-up details; and
- compact workspace widths where the inspector must remain an intentional
  subordinate surface, not an accidental stacked panel.

## Required Design

The implementation must render the same authenticated Exam Converter shell and
review components used by production. Fixture data may be injected only through
a dedicated dev/test fixture boundary that is hard-disabled in production
builds.

Recommended shape:

- add a small fixture catalog under the frontend Exam Converter authenticated
  module, or a backend fixture endpoint available only in local/test mode;
- route fixture selection through an explicit dev/test-only surface, not
  general query parameters on the production route;
- keep fixture records close to the artifact projection contracts they model;
- make fixture names teacher-state oriented, for example
  `complete-qti-ready`, `complete-qti-blocked`, `missing-facit`, and
  `ai-facit-review`;
- reuse the approved UI content model and component surfaces rather than
  rendering isolated screenshots of partial components; and
- require the HuleEdu browser-session ceremony for the authenticated shell even
  when the inner conversion state is fixture-backed.

## Non-goals

- Do not build a production support or diagnostics feature.
- Do not bypass HuleEdu browser-session login for authenticated UI inspection.
- Do not use fixture state as evidence that Sir Convert or HuleEdu runtime
  contracts work.
- Do not replace focused Vitest or the retained Playwright proof lane for
  repeatable regression coverage.
- Do not reopen the public Exam Converter lane.
- Do not expose raw prompts, provider payloads, credentials, identity context,
  student answers, or private result-PDF content in fixtures.

## Implementation Plan

1. Add a dev/test-only fixture boundary for authenticated Exam Converter review
   states. The guard must be explicit and covered by tests.
2. Define a small fixture catalog that maps to the existing normalized review
   projection, file-action, and report models.
3. Add a local fixture route or mode that is reachable after normal HuleEdu
   authenticated entry into `documents.conversion_hub`.
4. Keep the runtime submit/poll/download/save paths separate from fixture
   state so no fixture can unlock real file actions.
5. Add a focused component or view test proving that production-like rendering
   uses the real shell and that fixture access is disabled outside dev/test.
6. Update the browser automation runbook with the exact internal-browser
   workflow, canonical viewport widths, and evidence expectations.
7. Record each future UI-layout closeout in `.codex/handoff.md` with the route,
   fixture state, viewport widths, screenshots or DOM evidence, and commands.
8. Keep Tailwind on the documented Vite integration and patch only
   `@tailwindcss/node@4.3.0`'s optional cache-loader registration so Node 25+
   does not call the deprecated `module.register()` API.

## Test Plan

- Focused Vitest for the fixture catalog and guard.
- Focused Vitest for authenticated view rendering through fixture-backed state.
- `pdm run fe-type-check`
- `pdm run fe-lint`
- `pdm run fe-build`
- `pdm run fe-build` must complete without the Node 26 `DEP0205`
  `module.register()` warning.
- `pdm run docs-validate`
- `pdm run handoff-validate`
- `git diff --check`

For UI layout changes that use this lane, also run a live internal-browser
inspection at desktop and compact workspace widths and record the evidence in
handoff before closeout.

## Implementation Closeout

Implemented:

- Added the dev/test-only authenticated fixture route
  `/apps/documents.conversion_hub/exam-converter/ui-fixtures/:fixtureId`.
- Added fixture-backed states for `complete-qti-ready`,
  `complete-qti-blocked`, `missing-facit`, and `ai-facit-review`, all mapped
  through the existing normalized review projection instead of a separate mock
  UI.
- Kept fixture access behind dev/test guards and dynamic import boundaries so
  production builds do not include fixture route names or fixture ids.
- Corrected the conversion result state so blocked QTI readiness alone does
  not make an otherwise complete question import show partial conversion.
- Surfaced blocked file reason text in the Files tab, including
  `qti_package_export_disabled`.
- Kept the question-detail inspector beside the question list at desktop and
  narrow-laptop workspace widths; desktop keeps the full question table, while
  narrow-laptop widths switch the left pane to a purpose-built question
  navigator so the inspector remains visible and the table is not crushed or
  stacked below the list.
- Retained Tailwind's documented Vite plugin integration and added a pnpm
  patch for `@tailwindcss/node@4.3.0` so Node 25+ skips only the optional
  deprecated `module.register()` cache-loader registration.

Live internal-browser proof on 2026-05-17:

- `complete-qti-blocked` at 1512x900 showed `Provet är konverterat`, did not
  show `Konverteringen av provet lyckades delvis`, displayed the QTI blocked
  reason, and had no exact main-content `Granska` action.
- `missing-facit` at 1512x900 showed the partial warning and exact `Granska`
  action; the desktop table remained visible and the compact navigator stayed
  hidden.
- `missing-facit` at 1024x768 used the designed narrow-laptop composition:
  setup rail as a compact top band, desktop table hidden, question navigator
  visible at `192px`, inspector visible at `430px`, and document scroll width
  equal to viewport width (`1024px`).

## Rollback Plan

Remove the fixture route/module and its tests. Production runtime behavior must
remain unaffected because fixture access is guarded away from production builds
and does not own submit, poll, download, save, or readiness decisions.
