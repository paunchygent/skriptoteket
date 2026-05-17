---
type: pr
id: PR-0332
title: "ST-21-03 Exam Converter teacher-owned correction overlay contract"
status: ready
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
acceptance_criteria:
  - "Given `ADR-0086` is accepted, when this PR starts implementation, then the active UI edit actions, overlay fields, validation rules, submit/apply behavior, and artifact proof requirements are mapped before code changes."
  - "Given any teacher correction overlay is submitted, when Skriptoteket builds the request, then it carries source file SHA-256, source IR schema version, source IR SHA-256, item id, sequence, item type, and source item fingerprint, and stale or mismatched binding fails before rendering."
  - "Given a teacher edits a supported stem/prompt, choice key, matching key, or gapped/open-cloze accepted value, when the correction is submitted, then Skriptoteket sends a source-bound overlay and does not mutate source IR or unlock files from browser-local state."
  - "Given point correction is part of the full teacher correction workflow, when PR-0332 starts implementation, then the small producer-owned Sir Convert Task 322 has already added the source-bound points/scoring correction DTO, regenerated the consumer contract, and proved effective IR plus PDF/QTI behavior."
  - "Given a correction starts from an AI suggestion, when the teacher edits before applying, then the submitted overlay uses reviewed-completion lineage with a teacher-edited outcome where the upstream contract supports it."
  - "Given a correction is teacher-authored without AI lineage, when the correction is submitted, then the overlay uses the explicit non-advisory teacher correction contract rather than advisory candidate metadata."
  - "Given a teacher rejects one or all AI suggestions, when that rejection is recorded, then it suppresses candidates only and does not create an answer key, approve manual-unkeyed export, block targets, or enable PDF/QTI generation unless a separate source-bound review decision is submitted."
  - "Given the corrected apply job returns, when files are shown or downloaded, then question state, target readiness, PDF output, and QTI output are derived from the returned bundle and effective IR/artifact evidence."
  - "Given corrected artifacts are inspected, when PDF/QTI proof is retained, then it verifies corrected choice, matching, and gapped/open-cloze semantics where supported and proves internal diagnostics, raw overlay JSON, raw provider prompts/responses, student-result data, scores, credentials, and identity markers are absent."
  - "Given upstream Sir Convert lacks a required correction overlay or renderer behavior, when this PR maps the gap, then it records the exact upstream task dependency instead of adding a Skriptoteket local workaround."
---

# PR-0332: ST-21-03 Exam Converter Teacher-Owned Correction Overlay Contract

## Problem

The authenticated Exam Converter review flow can accept AI-facit suggestions
and can knowingly export the current state, but it does not yet govern the
teacher-owned correction workflow. Teachers still need a clear way to edit
wrong or missing stems/prompts, choice keys, matching keys, and
gapped/open-cloze accepted values before creating final PDF/QTI artifacts.
Point correction is also part of the full teacher workflow, but it must be
unblocked by a small producer-owned Sir Convert task immediately before this
PR. `PR-0332` must consume that returned producer contract; it must not invent
a local point-editing workaround or fold producer DTO ownership into the
Skriptoteket slice.

That workflow must not be implemented as local-only UI state or folded into
`PR-0331`. It needs its own decision boundary and PR-sized implementation
authority.

## Goal

Define and implement the first teacher-owned correction overlay slice for
authenticated Exam Converter:

- map current and intended edit actions before code changes;
- submit corrections through a source-bound Sir Convert overlay;
- depend on the preceding Sir Convert points/scoring producer DTO before
  exposing point editing;
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
3. Map the Sir Convert overlay fields available for:
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
6. Define the item-shape contract for choice, matching, and gapped/open-cloze
   corrections against source-neutral IR/QTI/PDF support.
7. Implement only the smallest correction editor slice whose upstream overlay
   and renderer contract is already available. Create upstream Sir Convert
   tasks for any missing producer capability.
8. Add focused frontend and contract tests for overlay construction, state
   clearing, post-apply projection, and blocked local-only downloads.
9. Add live Playwright proof, or reuse the durable PR-0331 proof harness if it
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
