---
type: pr
id: PR-0329
title: "ST-21-03 Exam Converter reviewed AI-facit handoff"
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
  - sir-convert
  - huleedu
  - llm
  - reviewed-completion
  - proof-blocker
acceptance_criteria:
  - "Given Sir Convert returns valid advisory answer-key candidates, including vision-backed `gap_fill` candidates, when the authenticated Exam Converter first-pass job finishes, then Skriptoteket renders those candidates in an explicit teacher review state instead of leaving the teacher only in the missing-facit/readiness-blocked state."
  - "Given a teacher accepts or edits one or more valid AI-facit suggestions, when they choose the reviewed handoff action, then Skriptoteket submits a second Sir Convert job using `completion_mode=local_llm_apply_missing_machine_marked_with_review`, multipart `digiexam-ingestion-overlay.json`, and `ingestion_overlay_policy=apply_teacher_overlay`."
  - "Given reviewed suggestions are submitted, when the overlay is built, then every item uses `reviewed_completion_answer_key` with source binding, source item fingerprint, candidate id, candidate payload digest, completion report sha256, provider profile, model profile where available, prompt template version, schema name/version, validation state, and review outcome."
  - "Given a candidate is rejected, unsupported, invalid, provider-failed, open-ended, or left for manual follow-up, when the overlay is built, then Skriptoteket does not include that item as reviewed completion data and does not infer export readiness locally."
  - "Given the second reviewed-apply job finishes, when Skriptoteket reloads artifacts, then file actions and readiness are derived only from the returned Sir Convert manifest, `target_readiness_report`, and `effective_ir_json`; the first advisory job remains lineage only."
  - "Given the live `paunchygent@gmail.com` proof is rerun with the same production `.dxe`, when Qwen vision is healthy, then retained evidence shows the advisory job with valid vision-backed candidates, the teacher-reviewed apply job, an available `effective_ir_json`, and final PDF/QTI readiness or a concrete Sir Convert target reason."
---

# PR-0329: ST-21-03 Exam Converter Reviewed AI-Facit Handoff

## Correct Owner

This slice belongs to Skriptoteket:

- repo:
  `/Users/olofs_mba/Documents/Repos/CascadeProjects/windsurf-project`;
- story: `ST-21-03`, authenticated Exam Converter under Conversion Hub; and
- product surface: the teacher-facing reviewed AI-facit handoff in the
  authenticated test-converter UI.

Sir Convert remains the producer/runtime owner for Qwen, vision assets,
advisory reports, reviewed overlays, effective IR, and target readiness.
HuleEdu remains the owner of the authenticated Gateway edge. This PR must not
move provider, auth-edge, or renderer contract ownership into Skriptoteket.

## Problem

The latest live production conversion as `paunchygent@gmail.com` proves that
the provider-side vision lane is no longer the root blocker. The Qwen provider
container is reachable from Sir Convert, vision media is mounted into the model
container, and the advisory report includes a valid vision-backed candidate for
`item-013`.

The remaining failure is the UI handoff between the advisory report and the
reviewed apply pass. Sir Convert was asked for
`completion_mode=local_llm_suggest_missing_machine_marked`, so the producer
correctly emitted `answer-key-completion-report.json` and did not apply those
suggestions into `effective_ir_json`. Target readiness therefore continued to
block with missing answer keys. That is the intended producer contract, but the
teacher workflow must make the next step clean: review the suggestions, build a
source-bound reviewed overlay, submit the reviewed apply job, and then show
file readiness from the second bundle.

`PR-0326` implemented the nominal consumer flow and `PR-0328` fixed stale
advisory idempotent replay. This slice exists because live proof still stopped
after the first-pass advisory bundle. The next implementation must reconcile
the current code, UI copy, runtime state, and proof path so a reviewer can
verify that the actual product flow performs the two-pass handoff end to end.

## Current Evidence

Operator investigation on 2026-05-17 found the following Sir Convert facts:

- Qwen provider container: `sir_convert_qwen_answer_key`.
- Provider endpoint used by Sir Convert:
  `http://sir_convert_qwen_answer_key:8082`.
- Provider model/profile evidence:
  `provider_profile_id=task309-llama-cpp` and
  `model_profile=qwen3.6-27b-q6k-mtp`.
- The model container exposes the expected multimodal server flags, including
  `--mmproj`, `--media-path`, and image-token support.
- Provider logs for `jobv2_672207df4f4b4354aeb83ebb0d` show image loading and
  processing from the Docker-visible vision-assets path:
  `/srv/scratch/sir-convert-a-lot/build/verification/task-320-qwen-provider/vision-assets/.../item-013-asset-001-1598928fcf35.png`.
- The Sir Convert `answer-key-completion-report.json` for that job includes a
  valid `item-013` `gap_fill` suggestion with
  `backend_status=success`, `validation_state=valid`, and
  `decision_state=suggested`.
- The same job has `effective_ir_json` as `not_requested`, because the request
  was advisory-only.
- The same job's target readiness still reports
  `manual_answer_key_required` for missing-key target rows, because no reviewed
  overlay was applied.

`docker debug` was not available on the Hemma snap Docker installation during
the investigation; the retained proof used `docker compose ps`, `docker logs`,
`docker compose config`, and bounded `docker exec` checks instead.

## Linked Docs

Skriptoteket authority and prior slices:

- `docs/backlog/stories/story-21-03-exam-converter-public-and-authenticated-artifact-lanes.md`
- `docs/backlog/prs/pr-0324-st-21-03-exam-converter-authenticated-end-to-end-proof.md`
- `docs/backlog/reviews/review-pr-0324-exam-converter-authenticated-end-to-end-proof.md`
- `docs/backlog/prs/pr-0325-st-21-03-exam-converter-authenticated-runtime-ui-and-save-remediation.md`
- `docs/backlog/prs/pr-0326-st-21-03-exam-converter-authenticated-llm-enrichment-consumer-sync.md`
- `docs/backlog/prs/pr-0327-st-21-03-exam-converter-authenticated-internal-browser-ui-inspection-lane.md`
- `docs/backlog/prs/pr-0328-st-21-03-exam-converter-advisory-idempotency-rerun.md`
- `docs/reference/ref-exam-converter-ui-content-model-v1.md`

Sir Convert producer and contract dependencies:

- `/Users/olofs_mba/Documents/Repos/sir-convert-a-lot/docs/backlog/stories/story-48-digiexam-overlay-and-effective-ir-contract-for-answer-key-completion.md`
- `/Users/olofs_mba/Documents/Repos/sir-convert-a-lot/docs/backlog/tasks/task-306-apply-reviewed-answer-key-completion-into-effective-ir.md`
- `/Users/olofs_mba/Documents/Repos/sir-convert-a-lot/docs/backlog/tasks/task-319-enable-qwen3-6-vision-capable-advisory-answer-key-completion-in-the-main-pipeline.md`
- `/Users/olofs_mba/Documents/Repos/sir-convert-a-lot/docs/backlog/tasks/task-320-containerize-qwen3-6-answer-key-provider-for-hemma-production.md`
- `/Users/olofs_mba/Documents/Repos/sir-convert-a-lot/docs/converters/digiexam-migration-service-api-artifact-contract.md`
- `/Users/olofs_mba/Documents/Repos/sir-convert-a-lot/docs/converters/digiexam-intermediate-exam-representation-contract.md`
- `/Users/olofs_mba/Documents/Repos/sir-convert-a-lot/docs/reference/ref-digiexam-machine-marked-answer-key-completion-architecture.md`

HuleEdu auth-edge dependency:

- `/Users/olofs_mba/Documents/Repos/huleedu/docs/backlog/stories/story-01-07-expose-sir-convert-artifact-bundle-routes-through-huleedu-auth-edge.md`
- `/Users/olofs_mba/Documents/Repos/huleedu/docs/backlog/tasks/task-0561-cut-skriptoteket-artifact-bundle-adapter-to-huleedu-sir-convert-edge.md`

## Linked Code

Skriptoteket UI/runtime surfaces:

- `frontend/apps/skriptoteket/src/views/apps/ExamConverterAuthenticatedView.vue`
- `frontend/apps/skriptoteket/src/views/apps/exam-converter-authenticated/useExamConverterAuthenticatedRuntime.ts`
- `frontend/apps/skriptoteket/src/views/apps/exam-converter-authenticated/useExamConverterReviewArtifacts.ts`
- `frontend/apps/skriptoteket/src/views/apps/exam-converter-authenticated/useExamConverterAiFacitReview.ts`
- `frontend/apps/skriptoteket/src/views/apps/exam-converter-authenticated/digiexamAnswerKeyCompletionReport.ts`
- `frontend/apps/skriptoteket/src/views/apps/exam-converter-authenticated/digiexamIrReviewParser.ts`
- `frontend/apps/skriptoteket/src/views/apps/exam-converter-authenticated/digiexamIrQuestionReviewProjection.ts`
- `frontend/apps/skriptoteket/src/views/apps/exam-converter-authenticated/ExamConverterAiReviewActionPanel.vue`
- `frontend/apps/skriptoteket/src/views/apps/exam-converter-authenticated/ExamConverterQuestionReviewShell.vue`
- `frontend/apps/skriptoteket/src/views/apps/exam-converter-authenticated/ExamConverterQuestionNavigator.vue`
- `frontend/apps/skriptoteket/src/views/apps/exam-converter-authenticated/ExamConverterFilesReadinessList.vue`
- `frontend/apps/skriptoteket/src/views/apps/exam-converter-authenticated/ExamConverterAdvisoryRetryPanel.vue`

Skriptoteket Gateway consumer surfaces:

- `frontend/apps/skriptoteket/src/api/sirConvertGateway/contractValues.ts`
- `frontend/apps/skriptoteket/src/api/sirConvertGateway/jobSpec.ts`
- `frontend/apps/skriptoteket/src/api/sirConvertGateway/requestContext.ts`
- `frontend/apps/skriptoteket/src/api/sirConvertGateway/client.ts`
- `frontend/apps/skriptoteket/src/api/sirConvertGateway/types.ts`
- `frontend/apps/skriptoteket/src/api/sirConvertOpenapi.d.ts`

Existing focused tests to extend or split:

- `frontend/apps/skriptoteket/src/api/sirConvertGateway/client.spec.ts`
- `frontend/apps/skriptoteket/src/api/sirConvertGateway/completionContract.spec.ts`
- `frontend/apps/skriptoteket/src/api/sirConvertGateway/requestContext.spec.ts`
- `frontend/apps/skriptoteket/src/views/apps/ExamConverterAuthenticatedReviewSlice.spec.ts`
- `frontend/apps/skriptoteket/src/views/apps/ExamConverterAuthenticatedRuntimeBridgeSlice.spec.ts`
- `frontend/apps/skriptoteket/src/views/apps/ExamConverterAuthenticatedFilesActionSlice.spec.ts`
- `frontend/apps/skriptoteket/src/views/apps/ExamConverterAuthenticatedAdvisoryRetry.spec.ts`
- `frontend/apps/skriptoteket/src/views/apps/ExamConverterAuthenticatedUiInspectionFixtures.spec.ts`

Sir Convert producer code to inspect only if the consumer contract appears to
drift:

- `/Users/olofs_mba/Documents/Repos/sir-convert-a-lot/scripts/sir_convert_a_lot/infrastructure/digiexam_migration_bundle_builder.py`
- `/Users/olofs_mba/Documents/Repos/sir-convert-a-lot/scripts/sir_convert_a_lot/infrastructure/digiexam_answer_key_completion_runtime.py`
- `/Users/olofs_mba/Documents/Repos/sir-convert-a-lot/scripts/sir_convert_a_lot/infrastructure/digiexam_answer_key_vision_assets.py`
- `/Users/olofs_mba/Documents/Repos/sir-convert-a-lot/scripts/sir_convert_a_lot/domain/digiexam_reviewed_completion_application.py`
- `/Users/olofs_mba/Documents/Repos/sir-convert-a-lot/scripts/sir_convert_a_lot/domain/specs_v2.py`

## Required Product Behavior

The UI must make the two-pass handoff unambiguous:

1. First pass:
   submit advisory completion with
   `local_llm_suggest_missing_machine_marked`.
2. Review:
   render valid candidates as teacher-reviewable AI-facit, including
   vision-backed `gap_fill` candidates.
3. Decision:
   require explicit teacher accept/edit/leave decisions before any suggestion
   can affect export readiness.
4. Handoff:
   build `digiexam-ingestion-overlay.json` using only accepted or edited
   suggestions and submit the reviewed apply job.
5. Reload:
   load the second job's manifest, readiness report, and effective IR.
6. Files:
   enable download/save only from the second job's producer evidence.

The teacher should not need to know whether a candidate came from text-only or
vision-backed provider input. The row must be reviewable based on the
normalized answer payload and lineage.

## Non-goals

- Do not change Sir Convert provider composition, model settings, Docker media
  mounts, or Task 320 runtime behavior in this slice.
- Do not reopen Sir Convert Story 48 or Task 306 unless the current contract is
  proven insufficient for the UI handoff.
- Do not add a local LLM, OCR parser, or answer-key inference path to
  Skriptoteket.
- Do not auto-apply advisory candidates without teacher review.
- Do not treat the first advisory job's target readiness as final readiness
  after teacher decisions exist.
- Do not expose raw prompts, raw provider responses, image bytes, student
  answers, scores, Sir Convert credentials, or HuleEdu identity material in UI,
  tests, retained artifacts, or logs.

## Implementation Plan

1. Reproduce the failure path in a focused frontend/runtime test before
   changing behavior:
   - advisory report has at least one valid vision-backed `gap_fill` candidate;
   - the advisory manifest has `effective_ir_json` unavailable or
     `not_requested`;
   - target readiness still blocks missing answer keys; and
   - the UI must present the reviewed handoff action instead of leaving the
     state as terminal missing-facit.
2. Audit `ExamConverterAuthenticatedView.vue` and
   `ExamConverterWorkspaceShell.vue` event wiring so the reviewed apply action
   is visible and reachable whenever `reviewedCompletionOverlay` is available.
3. Audit `useExamConverterAiFacitReview.ts` for gap-fill parity:
   - accept unchanged must work for `kind=gap_fill`;
   - accept-all must include valid supported gap-fill candidates;
   - edit-before-accept may remain choice-only unless a narrower gap editor is
     approved; and
   - left/manual decisions must be excluded from the overlay.
4. Audit the overlay payload against the generated OpenAPI type and Sir
   Convert Task 306 contract. If required lineage is missing in the current
   builder, add it in a small reviewed-overlay module instead of widening the
   view component.
5. Audit `useExamConverterAuthenticatedRuntime.ts`, `jobSpec.ts`,
   `client.ts`, and `requestContext.ts` to prove the second submit sends:
   - `completion_mode=local_llm_apply_missing_machine_marked_with_review`;
   - `digiexam_ingestion_overlay` multipart file named
     `digiexam-ingestion-overlay.json`;
   - `ingestion_overlay_policy=apply_teacher_overlay`; and
   - idempotency that changes with the reviewed overlay payload but remains
     stable for duplicate clicks of the same apply action.
6. After the reviewed apply job finishes, ensure artifact loading uses the
   second job id/correlation id and refreshes the projection from the second
   bundle. Do not keep file/readiness state from the first advisory bundle.
7. Add UI state that clearly distinguishes:
   - advisory candidates waiting for teacher review;
   - accepted/edited suggestions waiting to be submitted;
   - reviewed apply job running;
   - reviewed apply succeeded with producer-ready files; and
   - reviewed apply failed or remains blocked with producer reason codes.
8. Extend the internal-browser fixture lane if needed with a state matching the
   live bug: valid AI-facit candidates exist, but target readiness still blocks
   until `Skapa filer` performs the apply pass.
9. Rerun the live authenticated proof through HuleEdu Gateway as
   `paunchygent@gmail.com` and retain sanitized evidence. The proof must show
   two distinct Sir Convert jobs when teacher review is applied: advisory first,
   reviewed apply second.
10. Update `PR-0324`, `PR-0329`, `ST-21-03`, `docs/index.md`, and
    `.codex/handoff.md` with the final evidence and the next proof status.

## Review Checklist

- The implementation is in Skriptoteket, not Sir Convert, unless a producer
  contract gap is proven.
- The advisory job and reviewed apply job are visibly separate in tests and
  retained proof.
- Vision-backed candidates are handled through the same candidate payload path
  as other valid supported candidates.
- `reviewed_completion_answer_key` is the only overlay shape used for this
  AI-facit handoff.
- Local UI decisions never unlock files without Sir Convert manifest/readiness
  evidence from the apply job.
- The accepted-current-state `Godkänn` path remains separate from reviewed
  AI-facit.
- Teacher-visible copy stays Swedish and does not mention Qwen, provider
  internals, idempotency, raw model output, or Docker.

## Stop Conditions

- Stop if the current generated OpenAPI type lacks fields needed to build
  `reviewed_completion_answer_key` with bounded lineage.
- Stop if Sir Convert rejects a valid reviewed overlay that matches Task 306 and
  the artifact contract.
- Stop if the live apply job does not produce `effective_ir_json` and the Sir
  Convert artifact contract says it should.
- Stop if the only way to make readiness change is to auto-apply suggestions
  without teacher review.
- Stop if applying the vision-backed `item-013` candidate needs a new producer
  contract for gap-fill payloads or image lineage.

## Test Plan

- Focused unit tests for parsing and projection:
  - advisory report with a valid vision-backed `gap_fill` candidate;
  - advisory report with valid choice candidates;
  - invalid/provider-failed/manual-follow-up rows;
  - `effective_ir_json` absent on advisory pass; and
  - `effective_ir_json` present after reviewed apply.
- Focused overlay tests proving:
  - accepted `gap_fill` and choice candidates become
    `reviewed_completion_answer_key` entries;
  - rejected/left candidates are excluded;
  - source binding and source item fingerprints are required;
  - candidate lineage is preserved; and
  - no `manual_answer_key`, `review_decision`, or `effective_item_patch` is
    used for AI-facit handoff items.
- Focused Gateway/runtime tests proving:
  - first submit uses advisory completion mode;
  - reviewed apply submit uses apply mode and overlay multipart upload;
  - idempotency includes overlay JSON for apply;
  - duplicate apply clicks do not create accidental divergent requests; and
  - the projection reloads from the second job id.
- Focused UI tests proving:
  - valid candidates show the review/apply action;
  - accepted suggestions enable the reviewed handoff;
  - apply-running and apply-failed states are visible;
  - files remain disabled until apply-job readiness allows them; and
  - the advisory retry panel remains scoped to provider-only failures, not
    ordinary valid advisory reports.
- Browser/internal fixture proof for the review-to-apply UI state.
- Live authenticated proof through HuleEdu Gateway using the current production
  account path, with sanitized evidence of:
  - advisory job id;
  - valid `answer_key_completion_report`, including `item-013`;
  - reviewed overlay submit;
  - reviewed apply job id;
  - `effective_ir_json` availability;
  - target readiness result; and
  - download/save affordance state.

Closeout commands:

```bash
pdm run fe-test -- --run src/api/sirConvertGateway/client.spec.ts src/api/sirConvertGateway/completionContract.spec.ts src/api/sirConvertGateway/requestContext.spec.ts src/views/apps/ExamConverterAuthenticatedReviewSlice.spec.ts src/views/apps/ExamConverterAuthenticatedRuntimeBridgeSlice.spec.ts src/views/apps/ExamConverterAuthenticatedFilesActionSlice.spec.ts src/views/apps/ExamConverterAuthenticatedAdvisoryRetry.spec.ts src/views/apps/ExamConverterAuthenticatedUiInspectionFixtures.spec.ts
pdm run fe-type-check
pdm run fe-lint
pdm run fe-build
pdm run docs-validate
pdm run handoff-validate
git diff --check
```

## Implementation Closeout

Implemented on 2026-05-17 in the Skriptoteket authenticated Exam Converter UI.
The review detail pane now renders valid `gap_fill` AI-facit candidates as
teacher-facing Lucktext rows (`Lucka 1`, `Lucka 2`, ...), while keeping
edit-before-accept limited to choice payloads. Accepting a gap-fill suggestion
uses the same reviewed-completion overlay path as choice suggestions.

Focused PR-0329 coverage now proves the live-shaped handoff:

- first advisory bundle has a valid vision-backed `item-013` `gap_fill`
  candidate and target readiness still blocked by missing facit;
- the teacher can review and accept the Lucktext suggestion;
- `Skapa filer` submits
  `completion_mode=local_llm_apply_missing_machine_marked_with_review` with a
  `reviewed_completion_answer_key` gap-fill overlay;
- the overlay preserves source binding, source item fingerprint, candidate id,
  candidate payload digest, completion report sha256, provider profile, prompt
  template version, schema name/version, validation state, and review outcome;
  and
- the refreshed projection loads from the reviewed apply job id and only then
  shows producer-ready files.

The advisory parser retains `model_profile` from the completion report, but
the current generated Sir Convert `DigiExamOverlayReviewedCompletionCandidateLineage`
type does not include `model_profile` as an overlay field. Skriptoteket therefore
keeps the submitted overlay inside the typed Task 306 contract rather than
inventing a consumer-only field.

Verification run:

```bash
pdm run fe-test -- --run src/api/sirConvertGateway/client.spec.ts src/api/sirConvertGateway/completionContract.spec.ts src/api/sirConvertGateway/requestContext.spec.ts src/views/apps/ExamConverterAuthenticatedReviewSlice.spec.ts src/views/apps/ExamConverterAuthenticatedRuntimeBridgeSlice.spec.ts src/views/apps/ExamConverterAuthenticatedFilesActionSlice.spec.ts src/views/apps/ExamConverterAuthenticatedAdvisoryRetry.spec.ts src/views/apps/ExamConverterAuthenticatedUiInspectionFixtures.spec.ts
pdm run fe-type-check
pdm run fe-lint
pdm run fe-build
```

`fe-build` passed with the pre-existing large-chunk warning. A local browser
fixture attempt against
`/apps/documents.conversion_hub/exam-converter/ui-fixtures/ai-facit-review`
was blocked by the HuleEdu auth ceremony because the remote auth endpoint
rejected `http://127.0.0.1:5173` as an allowed return origin. No local
session-cookie shortcut or product-backend credential bypass was used.

## Rollback Plan

Keep the remediation inside the authenticated Exam Converter route and Sir
Convert Gateway consumer modules. If the reviewed handoff must be reverted,
remove the reviewed apply UI wiring and overlay submit path while preserving the
first-pass advisory report parser, the provider-only retry behavior from
`PR-0328`, and the separate accepted-current-state export path from `PR-0325`.
