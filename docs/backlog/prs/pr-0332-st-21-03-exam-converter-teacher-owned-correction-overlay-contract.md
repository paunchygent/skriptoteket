---
type: pr
id: PR-0332
title: "ST-21-03 Exam Converter teacher-owned correction overlay contract"
status: in_progress
owners: "Codex"
created: 2026-05-17
updated: 2026-05-18
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
  - "REV-PR-0332"
  - "Sir Convert task-322-add-points-scoring-correction-producer-dto-before-pr-0332"
  - "Sir Convert task-323-source-neutral-matching-manual-answer-key-dto"
  - "Sir Convert ADR-0011-source-neutral-exam-authoring-correction-apply-contract"
  - "Sir Convert task-327-define-unified-source-neutral-exam-authoring-correction-apply-contract"
  - "Sir Convert task-333-non-matching-unified-correction-apply-runtime"
  - "Sir Convert task-332-matching-capable-source-state-producer"
  - "HuleEdu TASK-0567-unified-sir-convert-corrections-edge"
acceptance_criteria:
  - "Given `ADR-0086` is accepted, when this PR starts implementation, then the active UI edit actions, overlay fields, validation rules, submit/apply behavior, and artifact proof requirements are mapped before code changes."
  - "Given any teacher correction overlay is submitted, when Skriptoteket builds the request, then it carries source file SHA-256, source IR schema version, source IR SHA-256, item id, sequence, item type, and source item fingerprint, and stale or mismatched binding fails before rendering."
  - "Given a teacher edits a supported stem/prompt, choice key, point value, or gapped/open-cloze accepted value, when the correction is submitted, then Skriptoteket sends a source-bound unified correction request and does not mutate source IR or unlock files from browser-local state."
  - "Given point correction is part of the full teacher correction workflow, when PR-0332 starts implementation, then the small producer-owned Sir Convert Task 322 has already added the source-bound points/scoring correction DTO, regenerated the consumer contract, and proved effective IR plus PDF/QTI behavior."
  - "Given a correction starts from an AI suggestion, when the teacher edits before applying, then the submitted overlay uses reviewed-completion lineage with a teacher-edited outcome where the upstream contract supports it."
  - "Given a correction is teacher-authored without AI lineage, when the correction is submitted, then the overlay uses the explicit non-advisory teacher correction contract rather than advisory candidate metadata."
  - "Given a teacher rejects one or all AI suggestions, when that rejection is recorded, then it suppresses candidates only and does not create an answer key, approve manual-unkeyed export, block targets, or enable PDF/QTI generation unless a separate source-bound review decision is submitted."
  - "Given the corrected apply job returns, when files are shown or downloaded, then question state, target readiness, PDF output, and QTI output are derived from the returned bundle and effective IR/artifact evidence."
  - "Given corrected artifacts are inspected, when PDF/QTI proof is retained, then it verifies corrected point, choice, text, and gapped/open-cloze semantics where supported and proves internal diagnostics, raw overlay JSON, raw provider prompts/responses, student-result data, scores, credentials, and identity markers are absent."
  - "Given upstream Sir Convert lacks a required correction overlay or renderer behavior, when this PR maps the gap, then it records the exact upstream task dependency instead of adding a Skriptoteket local workaround."
  - "Given Sir Convert ADR-0011 is accepted, when PR-0332 continues beyond already-started DXE correction slices, then new teacher-correction work targets the unified `/v2/exam-authoring/corrections/apply` contract for non-matching correction families only, does not preserve or consume the abandoned Task 324 matching-specific route, and keeps matching blocked until Sir Convert Task 332 provides a real matching-capable producer."
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

## Implementation Plan

1. Confirm `ADR-0086` is accepted or update this PR with the explicit decision
   outcome before implementation.
2. Map the current UI edit surfaces, including disabled or removed controls, so
   stale labels and legacy local-only branches do not re-enter the workflow.
3. Map the Sir Convert correction fields available for:
   - teacher-edited reviewed suggestions;
   - teacher-authored answer keys without AI lineage;
   - stem/prompt corrections;
   - rejection/global rejection of advisory suggestions.
4. Classify `effective_item_patch`, `manual_answer_key`,
   `reviewed_completion_answer_key`, and `review_decision` against the
   `ADR-0086` supported/blocked/upstream-required capability matrix.
5. Confirm the preceding Sir Convert points/scoring producer task has landed:
   source-bound DTO, validation, regenerated consumer contract, effective IR
   reporting, target readiness, and PDF/QTI proof. If it has not landed,
   `PR-0332` remains blocked and must not expose point editing.
6. Apply accepted Sir Convert ADR-0011 and Task 327 before any new
   teacher-correction API expansion: new work must target the unified
   `/v2/exam-authoring/corrections/apply` contract after the Sir Convert
   runtime hard cut and must not target, proxy, test-preserve, or wrap the
   Task 324 matching-specific route.
7. Wait for Sir Convert Task 333 and HuleEdu TASK-0567 before submitting
   non-matching unified corrections. Do not submit matching corrections until
   Sir Convert Task 332 provides real matching-capable producer state.
8. Define the item-shape contract for choice, point, text, and
   gapped/open-cloze corrections against producer-issued source state and
   target PDF/QTI behavior.
9. Implement only the smallest correction editor slice whose upstream correction
   and renderer contract is already available. Create upstream Sir Convert
   tasks for any missing producer capability.
10. Add focused frontend and contract tests for correction construction, state
   clearing, post-apply projection, and blocked local-only downloads.
11. Add live Playwright proof, or reuse the durable PR-0331 proof harness if it
   has landed, to show corrected effective IR and generated PDF/QTI artifacts.

## Task 322 Producer Prerequisite Status

Resolved on 2026-05-18.

- Sir Convert Task 322 added the producer-owned `point_correction` DTO with
  strict positive-integer `max_score`, effective IR reporting, target-readiness
  behavior, and PDF/QTI proof.
- Skriptoteket regenerated
  `frontend/apps/skriptoteket/src/api/sirConvertOpenapi.d.ts` from the Task
  322 OpenAPI snapshot.
- `frontend/apps/skriptoteket/src/api/sirConvertGateway/completionContract.spec.ts`
  now includes a producer-contract preflight assertion that generated consumer
  types expose both `point_correction` and `effective_point_correction`.
- Point-editing UI remains out of this prerequisite patch; this PR is now ready
  for its separate implementation pass against the returned Sir Convert state.

## Task 323 Producer Prerequisite Status

Resolved on 2026-05-18.

- Sir Convert Task 323 added the source-neutral
  `ExamAuthoringMatchingManualAnswerKey` DTO for matching keys.
- Skriptoteket regenerated
  `frontend/apps/skriptoteket/src/api/sirConvertOpenapi.d.ts` from the Task
  323 OpenAPI snapshot.
- The current DigiExam ingestion overlay item remains choice/gap-fill only;
  matching must use the source-neutral producer contract and must not be
  forced into the DigiExam overlay path.
- Task 323 is not sufficient to enable matching submission. Matching remains
  blocked until Sir Convert Task 332 issues real matching-capable source state
  and proves unified-route `manual_matching_answer_key` application.

## Unified Non-Matching Correction Addendum

Added on 2026-05-18 after Sir Convert Task 331 and Review 24 closed.

- Sir Convert Task 333 is the upstream prerequisite for continuing PR-0332 on
  the unified route. It must implement non-matching apply runtime for
  DigiExam-backed point, choice, gap/open-cloze, and item-text corrections
  against producer-issued source state.
- HuleEdu TASK-0567 is the auth-edge prerequisite after Task 333. It must
  expose only
  `/sir-convert/v2/exam-authoring/corrections/source-state/issue` and
  `/sir-convert/v2/exam-authoring/corrections/apply`, and must remove or
  disable the old Task 324 matching edge.
- PR-0332 may continue only for correction families implemented by Sir Convert
  Task 333 and exposed through HuleEdu TASK-0567.
- `manual_matching_answer_key` UI submission, gateway client code, generated
  route preflights, and artifact-readiness claims remain blocked until Sir
  Convert Task 332 provides a real matching-capable producer. The existing
  Exam.net matching PDF artifact is future Task 332 evidence, not a PR-0332
  non-matching prerequisite.

## Task 324 Superseded Route Status

Superseded and abandoned as an implementation path on 2026-05-18 by accepted
Sir Convert ADR-0011 and completed Task 327.

- Sir Convert Task 324 added
  `POST /v2/exam-authoring/matching/manual-answer-key/apply` for
  source-neutral matching manual-answer-key application, but that route is no
  longer a producer prerequisite or a tolerated bridge path for PR-0332.
- Skriptoteket regenerated
  `frontend/apps/skriptoteket/src/api/sirConvertOpenapi.d.ts` from the Task
  324 OpenAPI snapshot before ADR-0011 accepted the unified correction/apply
  direction. The generated path may remain in the snapshot until Sir Convert's
  unified hard cut regenerates the consumer contract, but no Skriptoteket test,
  client, or handoff step may protect it as desired API surface.
- The route-preserving
  `frontend/apps/skriptoteket/src/api/sirConvertGateway/matchingContract.spec.ts`
  has been removed so PR-0332 no longer guards dead API surface.
- HuleEdu must not expose a Gateway edge for the Task 324 route. The next
  Gateway work in this lane is the single unified
  `/sir-convert/v2/exam-authoring/corrections/apply` product edge after Sir
  Convert lands the runtime hard cut.

## Implementation Progress

Started on 2026-05-18.

- Added the first Skriptoteket consumer correction slice for item points:
  `digiexamTeacherCorrectionOverlay.ts` builds a source-bound
  `point_correction` overlay with all non-point correction fields explicit
  `null`.
- `digiexamAnswerKeyCompletionReport.ts`,
  `digiexamIrQuestionReviewProjection.ts`, and
  `digiexamIrReviewParser.ts` now project returned
  `effective_point_correction` from Sir Convert `effective_ir_json` into the
  question rows.
- `ExamConverterQuestionReviewShell.vue`, `ExamConverterWorkspaceShell.vue`,
  and `ExamConverterAuthenticatedView.vue` now let the teacher submit a point
  correction through the normal Sir Convert apply path. The local input does
  not mutate source IR, does not create answer-key evidence, and does not
  unlock file actions before the corrected bundle is returned.
- Focused Vitest proof now covers the point-correction overlay payload, the
  reload from returned effective state, and the pre-submit file-action gate.
- Added the first manual answer-key correction slice for DigiExam choice
  items without usable AI suggestions. `digiexamTeacherCorrectionOverlay.ts`
  now builds source-bound `manual_answer_key` overlays for choice and gap-fill
  payloads; `ExamConverterManualAnswerKeyEditor.vue` submits teacher-authored
  choice keys through Sir Convert, and returned `effective_answer_key` state is
  projected back into the question detail.
- `ExamConverterAuthenticatedCorrectionSlice.spec.ts` proves local manual-key
  selection does not submit or unlock files before the corrected Sir Convert
  bundle returns, then verifies the submitted overlay and returned effective
  state/file readiness.
- Added the next manual-key correction proof for DigiExam gap-fill accepted
  values. The manual editor now has focused coverage for teacher-entered source
  gap values; `digiexamTeacherCorrectionOverlay.ts` validates that submitted
  gap ids match the current source gaps, and the returned
  `effective_answer_key.correct_gap_answers` fixture now matches the generated
  map-shaped Sir Convert v2 contract.

Still open in this PR:

- Unified non-matching correction submit is blocked until Sir Convert Task 333
  lands and HuleEdu TASK-0567 exposes the unified authenticated product edge.
- Source-neutral matching correction submit is blocked until Sir Convert Task
  332 emits real matching-capable producer state. The unified route existing is
  not enough to enable matching.
- Map and implement visible item patches without widening advisory AI-facit
  semantics.
- Add live Playwright proof against the authenticated dev stack once the
  correction workflow slice is ready for browser-level validation.

## Source-Neutral Matching Contract Realignment

Realigned on 2026-05-18 after accepted Sir Convert ADR-0011 and completed Task
327.

Confirmed ready:

- Sir Convert Task 323 exposes generated DTOs:
  `ExamAuthoringMatchingManualAnswerKey`,
  `ExamAuthoringMatchingManualAnswerKeyPayload`, and
  `ExamAuthoringMatchingManualAnswerKeyPair`.
- Skriptoteket's generated `sirConvertOpenapi.d.ts` still exposes those DTOs to
  consumers.
- The DTO is source-neutral `ExamAuthoringIR v1` and is not a DigiExam overlay.

Superseded path:

- `POST /v2/exam-authoring/matching/manual-answer-key/apply` is abandoned as a
  PR-0332 implementation path. It must not be proxied by HuleEdu, consumed by
  Skriptoteket, preserved through a route-level consumer preflight, or retained
  as an adapter, shim, alias, wrapper, compatibility layer, or temporary bridge.

Decision for this PR:

- Non-matching correction UI submit is not implementable in Skriptoteket until
  Sir Convert Task 333 and HuleEdu TASK-0567 land.
- Matching correction UI submit is not implementable in Skriptoteket until Sir
  Convert Task 332 lands, even though the unified route exists.
- After HuleEdu TASK-0567 lands, add focused Skriptoteket gateway preflights for
  the source-state issue/apply routes, then implement only the consumer UI path
  whose correction family is supported by Sir Convert runtime and waits for
  returned effective state/readiness before file actions unlock.

## Test Plan

- Focused component/composable tests for edit-state lifecycle and overlay
  construction.
- Gateway request tests proving corrected overlays are multipart, source-bound,
  and completion-mode/policy correct.
- Parser/projection tests proving effective IR corrections replace stale
  source-missing presentation.
- Artifact inspection proof for PDF and QTI.
- Durable live Playwright proof against authenticated Skriptoteket, HuleEdu
  auth edge, Sir Convert, and any required local/tunneled LLM runtime.
- Producer-contract preflight proving the generated Sir Convert consumer types
  include the points/scoring correction DTO before point-editing UI is enabled.
- Producer-contract preflight proving the generated Sir Convert consumer types
  include the unified source-state issue/apply routes and the non-matching
  correction entries implemented by Task 333.
- Separate future preflight proving `manual_matching_answer_key` is backed by
  Task 332 matching-capable producer state before matching editing is enabled.
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
