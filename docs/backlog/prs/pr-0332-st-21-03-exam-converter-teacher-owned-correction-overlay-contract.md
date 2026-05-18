---
type: pr
id: PR-0332
title: "ST-21-03 Exam Converter teacher-owned correction overlay contract"
status: done
owners: "Codex"
created: 2026-05-17
updated: 2026-05-19
stories:
  - "ST-21-03"
tags:
  - frontend
  - authenticated
  - conversion-hub
  - sir-convert
  - teacher-edit
  - overlay
  - artifact-contract
links:
  - "ADR-0086"
  - "ADR-0087"
  - "REV-PR-0332"
  - "Sir Convert task-322-add-points-scoring-correction-producer-dto-before-pr-0332"
  - "Sir Convert task-323-source-neutral-matching-manual-answer-key-dto"
  - "Sir Convert ADR-0011-source-neutral-exam-authoring-correction-apply-contract"
  - "Sir Convert task-327-define-unified-source-neutral-exam-authoring-correction-apply-contract"
  - "Sir Convert task-333-non-matching-unified-correction-apply-runtime"
  - "Sir Convert task-332-matching-capable-source-state-producer"
  - "HuleEdu TASK-0567-unified-sir-convert-corrections-edge"
acceptance_criteria:
  - "Given a teacher submits a supported non-matching correction, when the Gateway request is inspected, then Skriptoteket uses the unified source-state issue/apply routes and never calls or preserves the retired Task 324 matching route."
  - "Given a point, choice, gap/open-cloze, or item-text correction is submitted, when Skriptoteket builds the apply request, then it carries the producer source binding, item id, sequence, item type, source item fingerprint, and the Task 333 correction entry shape for that family."
  - "Given a teacher-authored correction has no AI lineage, when it is submitted, then the request uses explicit teacher-authored non-advisory correction fields rather than advisory candidate metadata."
  - "Given matching correction would require `manual_matching_answer_key`, when this PR builds client code or UI submit paths, then matching remains absent and blocked until Sir Convert Task 332 provides matching-capable producer state."
  - "Given a correction apply response returns effective state, when the question review UI updates, then rows, counters, visible text, points, and read-only key display are projected from that returned transaction state without mutating source IR."
  - "Given a correction draft exists before submit, when file actions are evaluated, then local drafts do not unlock downloads or create artifact-readiness claims."
  - "Given unified correction apply fails, when the error path runs, then the failure is preserved for diagnostics and the UI exits the correction-applying state."
  - "Given durable correction sessions are required for navigation/reload stability, when this PR is scoped, then it does not implement or claim persisted teacher-correction truth; that architecture belongs to accepted ADR-0087 and ready ST-21-04."
---

# PR-0332: ST-21-03 Exam Converter Teacher-Owned Correction Overlay Contract

## Problem

The authenticated Exam Converter review flow can accept AI-facit suggestions
and can knowingly export the current state, but it does not yet govern the
teacher-owned correction workflow. Teachers still need a clear way to edit
wrong or missing stems/prompts, point values, choice keys, and
gapped/open-cloze accepted values before creating final PDF/QTI artifacts.
Matching correction remains part of the longer product direction, but is not in
the implementable PR-0332 continuation until Sir Convert Task 332 provides a
real matching-capable producer.
Point correction is also part of the full teacher workflow, but it must be
unblocked by a small producer-owned Sir Convert task immediately before this
PR. `PR-0332` must consume that returned producer contract; it must not invent
a local point-editing workaround or fold producer DTO ownership into the
Skriptoteket slice.

That workflow must not be implemented as local-only UI state or folded into
`PR-0331`. It needs its own decision boundary and PR-sized implementation
authority.

## Goal

Define and implement the first teacher-owned correction contract slice for
authenticated Exam Converter:

- map current and intended edit actions before code changes;
- submit corrections through a source-bound Sir Convert correction contract;
- depend on the preceding Sir Convert points/scoring producer DTO before
  exposing point editing;
- depend on Sir Convert Task 333 and HuleEdu TASK-0567 before consuming the
  unified non-matching correction route;
- keep source IR immutable;
- reload effective IR and target readiness from the corrected apply job;
- prove corrected keys/content reach PDF and QTI artifacts; and
- block or route upstream producer gaps instead of hiding them in UI copy.

## Non-goals

- No phone layout work; `PR-0330` owns that strategy.
- No reviewed AI-facit artifact-preservation cleanup; `PR-0331` owns that.
- No local parser mutation or local answer-key inference in Skriptoteket.
- No artifact download enablement from browser-local edit state.
- No expansion of public Exam Converter behavior unless a later public-lane
  authority explicitly includes teacher correction.

## Implementation Scope

`PR-0332` is a consumer/projection slice for the unified non-matching Sir
Convert correction edge. It may:

- issue producer source state through the HuleEdu Gateway route
  `/sir-convert/v2/exam-authoring/corrections/source-state/issue`;
- submit only Task 333-supported non-matching corrections through
  `/sir-convert/v2/exam-authoring/corrections/apply`;
- build entries for `point_correction`, `manual_choice_answer_key`,
  `manual_gap_open_cloze_answer_key`, and `item_text_patch`;
- project returned transaction-effective state into the current review rows;
- recompute counters from that returned state;
- keep local drafts from unlocking downloads; and
- log correction-apply failures before falling back to the failed UI state.

`PR-0332` must not:

- call, proxy, test-preserve, or wrap the retired Task 324 matching route;
- add `manual_matching_answer_key` submit paths before Sir Convert Task 332;
- persist correction-session truth in Skriptoteket;
- claim Sir Convert persists correction truth for the stateless apply edge;
- mutate parser/source IR; or
- close PDF/QTI artifact semantics for durable correction sessions.

Durable correction sessions are governed by accepted `ADR-0087` and ready
`ST-21-04`. The ordered implementation tasks for that story may persist
source-bound correction intents in Skriptoteket and replay the complete
supported set through stateless Sir Convert apply. That durable workflow remains
outside `PR-0332`.

## Implementation Summary

`PR-0332` is complete as a non-durable consumer/projection slice for unified
non-matching corrections:

- regenerated Sir Convert v2 types expose the unified source-state issue/apply
  contract consumed by Skriptoteket;
- the HuleEdu Gateway client uses the unified correction routes and no longer
  preserves the retired Task 324 matching route;
- correction request construction is limited to `point_correction`,
  `manual_choice_answer_key`, `manual_gap_open_cloze_answer_key`, and
  `item_text_patch`;
- matching submit paths remain blocked until Sir Convert Task 332 and a later
  governed slice;
- transaction-returned effective state drives the current question projection,
  counters, read-only answer-key display, point display, and item-text display;
- teacher drafts do not unlock downloads or claim artifact readiness; and
- correction apply failures are logged before the UI exits the applying state.

The slice intentionally does not persist correction sessions, replay persisted
sets, or prove reload/readback durability. That work remains under `ADR-0087`
and `ST-21-04`.

## Test Plan

- Focused component/composable tests for edit-state lifecycle and overlay
  construction.
- Gateway request tests proving unified source-state/apply calls are JSON,
  authenticated, source-bound, and limited to Task 333 non-matching correction
  families.
- Parser/projection tests proving effective IR corrections replace stale
  source-missing presentation.
- Producer-contract preflight proving the generated Sir Convert consumer types
  include the points/scoring correction DTO before point-editing UI is enabled.
- Producer-contract preflight proving the generated Sir Convert consumer types
  include the unified source-state issue/apply routes and the non-matching
  correction entries implemented by Task 333.
- Separate future preflight proving `manual_matching_answer_key` is backed by
  Task 332 matching-capable producer state before matching editing is enabled.
- No PDF/QTI or durable readback proof closes this PR. Artifact semantics and
  navigation/reload persistence move to the later accepted `ST-21-04`
  implementation chain.
- `pdm run fe-type-check`
- `pdm run fe-lint`
- `pdm run fe-build`
- `pdm run docs-validate`
- `pdm run handoff-validate`
- `git diff --check`

## Closeout Evidence

The closeout validation for this slice is:

- `pdm run fe-test -- --run src/api/sirConvertGateway/client.spec.ts src/api/sirConvertGateway/correctionsContract.spec.ts src/views/apps/ExamConverterAuthenticatedCorrectionSlice.spec.ts`
- `pdm run fe-type-check`
- `pdm run fe-lint`
- `pdm run fe-build`
- `pdm run docs-validate`
- `pdm run handoff-validate`
- `git diff --check`

## Rollback Plan

Revert the teacher-correction editor and overlay-submit code as one slice while
preserving the existing accepted-current-state and reviewed AI-facit apply
paths. Keep any upstream Sir Convert gap evidence in the governed task that
owns it.
