---
type: pr
id: PR-0406
title: "ST-21-04 Exam Converter consume compact answer-key review state"
status: blocked
owners: "agents"
created: 2026-06-29
updated: 2026-06-29
stories:
  - "ST-21-04"
  - "ST-21-11"
tags:
  - frontend
  - vue
  - conversion-hub
  - exam-converter
  - teacher-corrections
  - sir-convert
  - answer-key-review
dependencies:
  - "Sir Convert task-373-project-compact-digiexam-answer-key-review-state-for-skriptoteket"
  - "Sir Convert story-57-cross-repo-compact-answer-key-review-state-production-proof"
  - "ADR-0087"
  - "ADR-0086"
links:
  - "docs/backlog/stories/story-21-11-cross-repo-compact-answer-key-review-state-production-proof.md"
  - "Sir Convert docs/backlog/tasks/task-373-project-compact-digiexam-answer-key-review-state-for-skriptoteket.md"
  - "Sir Convert docs/backlog/stories/story-57-cross-repo-compact-answer-key-review-state-production-proof.md"
  - "docs/reference/ref-exam-converter-ui-content-model-v1.md"
  - "docs/reference/ref-exam-converter-reviewed-ai-facit-contract-map-pr-0331.md"
acceptance_criteria:
  - "Given Sir Convert exposes a compact answer-key review-state projection, when Skriptoteket renders the question list, then list state comes from that projection instead of being re-derived from multiple producer artifacts and local UI state."
  - "Given a pending advisory answer-key suggestion exists, when the list renders, then the item uses the compact review-needed state with a robot affordance and does not imply an error."
  - "Given a teacher has reviewed an AI-suggested key unchanged, when the list renders, then the item shows only the normal completed state, such as `Klart` with a checkmark, and no extra AI badge."
  - "Given a teacher has edited the suggested key, keyed option text, gap value, stem, or other keyed content, when the list renders, then the current key is treated as teacher-owned and no AI provenance marker is shown for the current key."
  - "Given a multiple-choice or gap/open-cloze item lacks a valid selected key or accepted value, when the list and detail render, then the UI shows a compact current validation problem such as `Kontrollera` with a reason like `Inget rätt svar valt`, not stale-AI wording."
  - "Given file actions are evaluated, when Sir Convert has not returned target readiness or replay artifact references, then Skriptoteket keeps downloads/save actions disabled and does not infer readiness from local drafts."
  - "Given local correction-session readback exists, when Skriptoteket claims saved/reviewed/exportable state, then that claim is backed by Sir Convert returned projection/effective state rather than component-local state."
---

# PR-0406: ST-21-04 Exam Converter Consume Compact Answer-Key Review State

## Problem

Authenticated Exam Converter currently assembles item review state from several
surfaces: source IR, migration manifest, target readiness, optional
answer-key completion report, optional effective IR, correction-session
readback, and replay apply results. That makes the UI too responsible for
state semantics that belong to the producer. Small local assumptions can drift
from Sir Convert's source/effective state and artifact readiness contracts.

The current UX direction is deliberately compact:

- `Granska` means a teacher action is needed, including a pending AI suggestion
  where a robot affordance may be shown.
- `Klart` means the item is reviewed/valid for the current projection and needs
  no extra AI badge in the list.
- `Ändrat` may be used for a teacher-owned modified key, but AI provenance must
  not be shown as current-key provenance after keyed content changes.
- `Kontrollera` means a current validation problem, such as no correct answer
  selected or no accepted gap value. It does not mean stale AI provenance.

Those visible labels are Skriptoteket presentation choices. The durable
semantic state must come from Sir Convert.

## Goal

Consume the Sir Convert compact answer-key review-state projection introduced
by Task 373 and make it the primary source for authenticated Exam Converter
question-list, detail, report, and file-action review state.

Skriptoteket still owns teacher interaction, local authenticated
correction-session persistence, and presentation. Sir Convert owns source and
effective state, answer-key provenance semantics, candidate lineage/audit data,
target readiness, and replay artifact authority.

## Non-goals

- No Sir Convert schema or runtime implementation in this PR.
- No local answer-key inference fallback once the Sir Convert projection is
  available.
- No accepted-current-state export workaround.
- No browser-local claim that a draft, prefill, or saved intent is export-ready
  before Sir Convert returns effective projection/readiness evidence.
- No resurrection of the old reviewed-AI acceptance workflow as a separate
  state machine. AI candidates seed normal facit editing and correction
  submission.

## Implementation Plan

1. Regenerate or update the Sir Convert Gateway types after Task 373 exports the
   new projection.
1. Add a typed parser/adapter for the compact projection response or named
   artifact.
1. Replace local list-state inference in the Exam Converter review projection
   with the Sir Convert projection where present.
1. Preserve local draft state only as draft UI; do not use it to unlock files,
   report completion, or reviewed-state claims.
1. Keep correction-session persistence and replay orchestration intact:
   teacher input still becomes source-bound correction intents, and saved state
   becomes authoritative only after readback plus Sir Convert replay/projection.
1. Update the mobile/small-screen question list and detail copy to use compact
   labels:
   - pending advisory: `Granska` with robot affordance;
   - reviewed/complete: `Klart` with checkmark only;
   - teacher-owned modified: `Ändrat` or `Klart`, no AI marker;
   - current validation problem: `Kontrollera` plus a short reason.
1. Update report and files views so file readiness remains driven by Sir
   Convert target readiness and replay artifact references, not question-list
   review state.

## Open Questions Before Implementation

1. Projection transport.
   - Open: will Task 373 expose the projection as a named artifact, a top-level
     correction-apply response field, or both?
   - Recommendation: support both if Sir Convert does; use the response field
     for immediate replay UI and named artifact for first-pass bundle review.
1. Exact semantic enum names.
   - Open: what exact producer codes will map to `Granska`, `Klart`,
     `Ändrat`, and `Kontrollera`?
   - Recommendation: wait for Task 373 to define semantic codes; do not encode
     assumptions from the mockup in TypeScript before the producer contract is
     fixed.
1. `Ändrat` versus `Klart` in the list.
   - Open: should teacher-owned edited keys show `Ändrat` persistently in the
     list, or collapse to `Klart` once saved/replayed?
   - Recommendation: use `Ändrat` while it helps orient the teacher during the
     current review session, but allow report/export completion to treat it as
     complete once Sir Convert returns a valid teacher-owned key.
1. Provenance detail.
   - Decision: consume only Task 373's bounded `provenance_detail` object for
     any `Tidigare förslag` style disclosure. Do not consume or model a generic
     `history` event stream.
   - Rationale: provenance detail is optional detail/audit context. It must not
     create a second review state machine, explain current truth through legacy
     lineage, or affect list labels, report completion, or file readiness.
1. Public lane behavior.
   - Open: should the public anonymous Exam Converter consume the compact
     report if present, or should PR-0406 be authenticated-only?
   - Recommendation: keep PR-0406 authenticated-only unless Task 373 and the
     public grant contract explicitly expose the report for public jobs.
1. Saved local intent versus producer projection conflict.
   - Open: how should the UI prioritize a saved correction intent when Sir
     Convert replay is stale/unavailable?
   - Recommendation: show the saved intent as local saved input but do not show
     fresh `Klart`/file-ready state until replay projection succeeds.

These questions must be answered by Task 373 output, an explicit product
decision, or a docs update before implementation starts. They are not left for
the implementation agent to infer.

## Assumptions

- Sir Convert Task 373 will remain the semantic source of truth for compact
  review states.
- Task 373 will expose bounded `provenance_detail` for advisory detail display
  and will not expose a legacy `history` or `review_decision` compatibility
  surface.
- Skriptoteket will continue to persist authenticated teacher correction
  intents locally, then replay the complete set through Sir Convert apply.
- Sir Convert target readiness remains separate from item review state.
- Swedish visible copy remains in Skriptoteket; Sir Convert emits semantic
  codes and message keys, not final UI strings.

## Recommended Implementation Shape

Prefer one narrow adapter module that maps the producer projection into the
existing Exam Converter view model. Avoid distributing new state mapping across
`digiexamIrReviewParser.ts`, `digiexamIrQuestionReviewProjection.ts`, and
`correctionSessionProjection.ts` without a single owner; that is the current
drift risk.

The adapter should make unsupported/missing producer fields fail closed: show
review unavailable or keep existing conservative blocked behavior rather than
guessing `Klart`.

## Test Plan

- Focused projection tests proving Sir Convert compact states map to the
  visible short labels without adding an AI marker to `Klart`.
- Correction-session tests proving local drafts and saved intents do not unlock
  file actions before Sir Convert replay projection/readiness.
- Replay projection tests proving replay artifact references are preserved and
  original job artifacts are not used for corrected downloads.
- Report/files tests proving `Kontrollera` represents a current validation
  problem, not stale AI provenance.
- Small-screen/component tests for the mobile question list and detail layout
  once the visual slice is implemented.
- `pdm run fe-test -- --run <focused Exam Converter specs>`
- `pdm run fe-type-check`
- `pdm run fe-lint`
- `pdm run fe-build`
- `pdm run docs-validate`
- `pdm run handoff-validate`
- `git diff --check`

## Rollback Plan

Revert the compact-projection adapter and UI mapping while preserving existing
correction-session persistence and replay behavior. Keep file actions
conservative if the projection is unavailable.

## Stop Conditions

- Stop if Sir Convert Task 373 has not closed its open questions or has not
  emitted a stable versioned projection contract.
- Stop if implementing this PR would require Skriptoteket to define producer
  answer-key semantics locally.
- Stop if file readiness becomes coupled to question-list labels instead of
  Sir Convert target readiness and replay artifact references.
- Stop if any implementation would reintroduce accepted-current-state export as
  authoring or correction state.
