---
type: pr
id: PR-0408
title: "ST-21-04 Exam Converter frontend design implementation alignment"
status: done
owners: "agents"
created: 2026-06-29
updated: 2026-06-29
stories:
  - "ST-21-04"
tags:
  - frontend
  - vue
  - exam-converter
  - answer-key-review
  - design-implementation
  - browser-proof
dependencies:
  - "PR-0406"
  - "ST-21-11"
  - "REV-PR-0406"
  - "ADR-0086"
  - "ADR-0087"
links:
  - "docs/mockups/pr-0406-answer-key-review-small-screen/README.md"
  - "docs/mockups/pr-0406-answer-key-review-desktop/README.md"
  - "docs/reference/ref-exam-converter-ui-content-model-v1.md"
  - "docs/backlog/stories/story-21-11-cross-repo-compact-answer-key-review-state-production-proof.md"
  - "docs/backlog/prs/pr-0406-st-21-04-exam-converter-consume-compact-answer-key-review-state.md"
  - "docs/backlog/reviews/review-pr-0406-exam-converter-compact-answer-key-review-state.md"
acceptance_criteria:
  - "Given the teacher has not converted a source file yet, when the authenticated Exam Converter workflow rail renders, then it accepts the source file only and does not expose pre-conversion PDF/QTI target-file or source-format controls."
  - "Given compact answer-key review state exists on desktop, when the question review mode renders, then the screen keeps the left workflow rail, central question table, and one selected-question detail pane for `Frågor`."
  - "Given compact answer-key review state exists on desktop, when the result band renders, then it uses `Kontrollera facit`, a compact review count, and `Granska frågorna som saknar rätt svar eller facitsvar.` instead of partial-conversion copy."
  - "Given the teacher opens `Filer` or `Rapport` on desktop, when that mode is active, then selected-question detail/editor content is not shown and the mode renders only its own file or report surface."
  - "Given generated PDF/QTI artifacts are available, when file actions render, then download/save controls live in `Filer` only and remain gated by Sir Convert target readiness plus replay artifact references."
  - "Given the teacher reviews a desktop question detail, when previous/next controls render, then they are sticky symbolic controls with accessible labels and no visible `Föregående` or `Nästa` text."
  - "Given a pending advisory answer-key item is selected, when the teacher chooses `Ändra`, then the normal answer-key editor opens with `Spara facit` and bounded `Tidigare förslag` detail rather than a separate AI-specific workflow."
  - "Given answer-key review state is computed and rendered, when items are classified, then keyed closed-response items including MCQ/choice and Lucktext/gap-fill/open-cloze participate in answer-key review, while free-text/open-writing items are not counted as missing facit, do not ask for a key, do not show warning status such as `Kontrollera` / `Frågetypen behöver kontrolleras`, and do not block `Kontrollera facit`."
  - "Given the screen is phone-sized, when the teacher moves between review list, detail, files, and report, then those are separate task surfaces and the UI does not squeeze or stack the desktop workbench."
  - "Given phone-sized review, file, and report surfaces render, when labels and actions appear, then Swedish copy, status labels, and action controls do not clip or create horizontal document overflow."
  - "Given PR-0406 review states render anywhere in the Exam Converter UI, when symbols are used, then pending advisory uses `IconAi`/`Sparkles`, complete uses `IconCheck`/`Check`, teacher-owned edits use `IconEdit`/`PencilLine`, validation problems use `IconWarning`/`AlertTriangle`, and feature-local `Bot`, `CheckCircle2`, or `XCircle` are not used for these states."
  - "Given validation problems render for keyed closed-response answer-key items, when the teacher reads the actionable message, then it uses compact copy such as `Kontrollera`, `Inget rätt svar valt`, `Välj minst ett rätt svar`, or `Saknar facitsvar` for Lucktext/open-cloze values and does not expose internal enum names, stale-AI wording, free-text key requirements, or partial-conversion copy as the review action."
  - "Given the implementation is complete, when retained review and proof close the slice, then focused Vitest coverage, frontend typecheck/lint/build, docs/handoff validation if touched, `git diff --check`, and browser/screenshot proof cover the desktop and small-screen requirements above."
---

# PR-0408: ST-21-04 Exam Converter Frontend Design Implementation Alignment

## Problem

`PR-0406` and `ST-21-11` closed the compact answer-key review-state contract,
producer/consumer truth split, retained review, and production proof. A new
frontend-only implementation slice is needed before further code work so the
live Exam Converter UI can be audited and, where needed, aligned with the
governed PR-0406 desktop and small-screen design authorities.

This PR does not reopen the closed Sir Convert Task 373, `PR-0406`, or
`ST-21-11` remediation/proof work. It uses those artifacts as authority for the
frontend design implementation only.

## Goal

Align the authenticated Exam Converter desktop and small-screen experiences with
the governed PR-0406 design decisions for answer-key review, edit-facit, files,
report, copy, symbols, and layout.

The implementation must preserve the PR-0406 ownership split: Sir Convert owns
compact answer-key review-state truth and target readiness; Skriptoteket
renders that truth, collects teacher interaction, persists local correction
intents, and renders replay-returned projection/readiness.

Product clarification for this slice: answer-key review belongs to keyed
closed-response items, including MCQ/choice and
Lucktext/gap-fill/open-cloze. Free-text and open-writing response items can
require later teacher marking or item-editing workflow, but they are not missing
facit, cannot have generated keys, and must not inflate answer-key review
counts or block answer-key review completion.

## Non-goals

- No Sir Convert schema, runtime, replay, fingerprint, owner-matching, export
  root-cause, or producer remediation changes.
- No backend contract changes in Skriptoteket unless a separate governed slice
  proves they are required.
- No local answer-key review-state inference fallback.
- No answer-key requirements for free-text or open-writing response items.
- No file readiness inferred from local drafts, visual labels, or browser state.
- No reintroduction of pre-conversion PDF/QTI target choices.
- No public anonymous compact review-state consumption.
- No broad redesign outside the represented Exam Converter answer-key review,
  edit-facit, files, report, symbol, copy, and responsive layout surfaces.

## Design Authorities

- `docs/mockups/pr-0406-answer-key-review-small-screen/README.md` is the
  approved exact small-screen authority.
- `docs/mockups/pr-0406-answer-key-review-desktop/README.md` is the retained
  desktop alignment authority for this implementation slice.
- `docs/reference/ref-exam-converter-ui-content-model-v1.md` provides the
  durable Exam Converter content model and responsive composition contract.
- `docs/backlog/stories/story-21-11-cross-repo-compact-answer-key-review-state-production-proof.md`
  is background authority only. Do not reopen its completed remediation or
  production proof.

If production constraints require changing the represented mockup decisions,
stop and update the relevant mockup/governed decision artifact before changing
production UI behavior.

## Implementation Plan

Use the overseer implementation/review loop:

1. Spawn `implementation_agent` for this frontend-only slice.
1. Require the implementer to read `AGENTS.md`, this PR, the design authorities,
   `integrated-frontend-stack`, `skriptoteket-frontend-specialist`, `testing`,
   `.codex/skills/skriptoteket-testing/SKILL.md`, the routed frontend testing
   and browser proof references, and the relevant Exam Converter components and
   specs before editing.
1. Require a current-state audit before edits. If a requirement is already
   satisfied, preserve or strengthen the proof instead of rewriting it.
1. Require red-first or characterization tests where feasible for:
   - desktop result-band framing;
   - edit-facit `Ändra` to normal `Spara facit` editor state;
   - Lucktext/gap-fill/open-cloze items retained as keyed closed-response
     answer-key review work;
   - free-text/open-writing items excluded from answer-key counts, missing-facit
     copy, and manual answer-key editors;
   - `Filer`/`Rapport` exclusivity;
   - no pre-conversion target/source-format selection;
   - approved review-state symbol usage;
   - sticky symbolic previous/next navigation;
   - small-screen separate list/detail/files/report task surfaces and overflow
     safety.
1. Implement the smallest frontend changes that make the approved design
   behavior true while keeping existing adapter/replay/file-readiness authority
   intact.
1. Run focused Vitest and frontend gates, then report exact evidence.
1. Spawn the fixed `ruthless_review_agent` for retained review.
1. If review requests changes, return findings to the same implementation lane,
   require tests that would have caught the finding, and repeat until approved.
1. After approval, run required validation gates and retained browser/screenshot
   proof.

## Test Plan

Closeout state on 2026-06-29: frontend code is approved by `REV-PR-0408`;
focused Vitest, proof-helper unit tests, frontend typecheck, lint, build, docs
validation, handoff validation, and `git diff --check` are green for the latest
free-text/open-ended and advisory-button remediation. Fresh retained browser
proof passed at
`.artifacts/pr-0408-exam-converter-design-proof/20260629T174933Z/manifest.redacted.json`,
with desktop `Frågor`/`Filer`/`Rapport` screenshots, phone
list/detail/files/report screenshots, and no horizontal overflow at the
captured desktop or phone widths.

- Focused component tests for the desktop result band,
  `Kontrollera facit` copy, review count, and non-partial conversion framing.
- Focused component tests for `Ändra` entering the normal answer-key editor with
  `Spara facit` and bounded `Tidigare förslag`.
- Focused component tests proving Lucktext/gap-fill/open-cloze items remain
  keyed closed-response answer-key review rows, including missing-facit and
  `Spara facit` repair where the compact review state requires it.
- Focused component tests proving free-text and open-writing response items are
  not counted as answer-key review work, do not show missing-facit/actionable
  key copy, and do not expose `Spara facit` as a required repair.
- Focused component tests proving `Filer` and `Rapport` do not leak selected
  question detail/editor content.
- Focused component tests proving no pre-conversion PDF/QTI target-file or
  source-format controls are rendered in the workflow rail.
- Focused component tests proving approved symbol wrappers/components are used
  for PR-0406 states and feature-local `Bot`, `CheckCircle2`, and `XCircle` are
  not used for those states.
- Focused component tests proving sticky previous/next controls are symbolic,
  accessible, and do not show persistent `Föregående` / `Nästa` labels.
- Small-screen tests or browser proof at phone width proving separate
  list/detail/files/report task surfaces, no horizontal document overflow, and
  no clipped Swedish action labels.
- `pdm run fe-test -- --run <focused Exam Converter specs>`
- `pdm run fe-type-check`
- `pdm run fe-lint`
- `pdm run fe-build`
- `pdm run docs-validate` if docs are touched after this scaffold
- `pdm run handoff-validate` if `.codex/handoff.md` is touched after this
  scaffold
- `git diff --check`
- Retained browser/screenshot proof using the repo browser proof lane and
  HuleEdu browser-session ceremony for protected UI proof.

## Rollback Plan

Revert the PR-0408 frontend UI changes while preserving the closed PR-0406
compact projection adapter, correction-session persistence, replay artifact
authority, and file-readiness gates. If proof shows a design decision cannot be
implemented without changing producer/backend contracts, stop and open a new
governed decision slice instead of widening this PR.

## Stop Conditions

- Stop if the implementation requires changing closed Sir Convert Task 373,
  `PR-0406`, backend producer contracts, replay semantics, fingerprinting,
  owner matching, or export-runtime root cause work.
- Stop if any UI path starts deriving producer truth locally from IR, readiness,
  correction sessions, visual labels, browser state, or local drafts.
- Stop if any UI path treats free-text or open-writing responses as missing
  answer keys.
- Stop if file readiness is inferred outside Sir Convert target readiness plus
  replay artifact references.
- Stop if pre-conversion PDF/QTI target choices reappear.
- Stop if a production constraint requires changing the approved/proposed
  mockup decisions instead of implementing them.
