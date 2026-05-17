---
type: pr
id: PR-0326
title: "ST-21-03 Exam Converter authenticated LLM-enrichment consumer sync"
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
  - review
acceptance_criteria:
  - "Given a signed-in teacher submits a `.dxe` through authenticated Exam Converter, when the first job is created, then Skriptoteket requests Sir Convert advisory enrichment with `completion_mode=local_llm_suggest_missing_machine_marked`, `remote_provider_policy=forbidden`, `result_pdf_usage=correct_machine_marked_answers_only`, and `manual_follow_up_policy=emit_item_addressable_report`."
  - "Given Sir Convert returns a DigiExam migration bundle, when Skriptoteket loads review artifacts, then it fetches and parses `answer_key_completion_report`, `effective_ir_json` when available, the bundle manifest, `target_readiness_report`, `ir_json`, and `migration_manifest` without treating advisory candidates as source truth."
  - "Given `answer_key_completion_report_v1` contains per-item advisory candidates, when the authenticated question review surface renders, then each item distinguishes no-candidate-needed, suggested-and-valid, invalid suggestion, provider unavailable, skipped because the source already had an answer key, and manual-follow-up-required states."
  - "Given valid supported machine-marked suggestions are present, when the teacher reviews them, then the UI presents them as AI-suggested facit and supports accept unchanged, reject or leave for manual follow-up, edit before accept where the payload kind is supported, and a compact accept-all-suggestions affordance whose action only accepts currently valid supported suggestions."
  - "Given the teacher accepts or edits one or more suggestions, when Skriptoteket builds the overlay, then every applied item uses `reviewed_completion_answer_key` with bounded candidate lineage and never uses `manual_answer_key`, `review_decision`, or `effective_item_patch` for this advisory-completion path."
  - "Given reviewed suggestions exist, when Skriptoteket submits the second job, then it uses `completion_mode=local_llm_apply_missing_machine_marked_with_review`, attaches `digiexam-ingestion-overlay.json`, sets `ingestion_overlay_policy=apply_teacher_overlay`, and does not rely on local UI state to unlock PDF or QTI export."
  - "Given Sir Convert returns the reviewed apply bundle, when files are shown, then PDF/QTI actions are enabled only from returned manifest and readiness evidence, or remain blocked with a clear teacher-facing reason."
---

# PR-0326: ST-21-03 Exam Converter Authenticated LLM-Enrichment Consumer Sync

## Problem

`PR-0325` made the authenticated Exam Converter lane runnable and proved the
accepted-current-state export path, but that path deliberately does not create
machine-marked answer keys. It lets the teacher knowingly export the current
conversion state when `Facit` is missing.

Sir Convert now exposes a stricter two-pass reviewed-completion contract for
missing machine-marked keys. Skriptoteket has the generated OpenAPI types for
`answer_key_completion_report_v1` and `reviewed_completion_answer_key`, but it
does not yet request advisory enrichment, parse the completion report, present
candidate state to the teacher, build reviewed-completion overlays, or resubmit
the reviewed apply job.

Without this slice, an authenticated live proof would either keep using the
weaker accepted-current-state path or treat LLM output as truth without explicit
teacher review. Both are the wrong product and contract shape.

## Goal

Implement the authenticated Exam Converter consumer side of the Sir Convert
two-pass reviewed-completion workflow:

- first submit asks Sir Convert for advisory local-LLM suggestions only;
- Skriptoteket parses and normalizes completion, source, manifest, readiness,
  and effective-IR artifacts into one item-addressable review model;
- the UI presents AI-suggested facit with explicit teacher review controls,
  including a compact accept-all-suggestions affordance for valid supported
  suggestions;
- reviewed or edited suggestions produce a source-bound
  `reviewed_completion_answer_key` overlay;
- second submit applies that reviewed overlay through Sir Convert; and
- final file availability remains governed by Sir Convert's returned bundle
  manifest and `target_readiness_report_v1`.

## Dependencies

- Authenticated runtime/save remediation:
  `docs/backlog/prs/pr-0325-st-21-03-exam-converter-authenticated-runtime-ui-and-save-remediation.md`
- Blocked authenticated proof:
  `docs/backlog/prs/pr-0324-st-21-03-exam-converter-authenticated-end-to-end-proof.md`
  and
  `docs/backlog/reviews/review-pr-0324-exam-converter-authenticated-end-to-end-proof.md`
- Exam Converter UI content model and slice approval protocol:
  `docs/reference/ref-exam-converter-ui-content-model-v1.md`
- Approved PR-0326 AI-facit review mockup:
  `docs/mockups/st-21-03-exam-converter-authenticated-progressive-review/exam-converter-authenticated-ai-facit-review-v1.png`
- Authenticated Sir Convert Gateway client:
  `frontend/apps/skriptoteket/src/api/sirConvertGateway/`
- Authenticated Exam Converter view:
  `frontend/apps/skriptoteket/src/views/apps/ExamConverterAuthenticatedView.vue`
  and
  `frontend/apps/skriptoteket/src/views/apps/exam-converter-authenticated/`
- Sir Convert generated consumer contract:
  `frontend/apps/skriptoteket/src/api/sirConvertOpenapi.d.ts`
- Sir Convert DigiExam migration artifact contract:
  `/Users/olofs_mba/Documents/Repos/sir-convert-a-lot/docs/converters/digiexam-migration-service-api-artifact-contract.md`
- Sir Convert answer-key completion roadmap:
  `/Users/olofs_mba/Documents/Repos/sir-convert-a-lot/docs/reference/ref-machine-marked-answer-key-completion-implementation-roadmap.md`

## Non-goals

- Do not reopen the public Exam Converter lane. This reviewed-completion loop
  belongs to the authenticated product workflow for now.
- Do not implement a local answer-key inference model in Skriptoteket.
  Skriptoteket is only the review consumer and overlay submitter.
- Do not treat LLM output as source evidence, source provenance, or export-ready
  reviewed truth before teacher action.
- Do not apply suggestions to open-ended/free-text manual-marking items.
- Do not send reviewed-apply jobs through public grant/read-lease behavior.
- Do not widen the accepted-current-state `Godkänn` path into an answer-key
  completion path. Accepted-current-state remains a separate export decision.
- Do not expose raw prompts, raw provider responses, result-PDF private data,
  student wrong answers, scores, identity markers, raw Sir Convert credentials,
  or HuleEdu identity material in UI, tests, or retained proof artifacts.
- Do not enable PDF or QTI file actions from local review state alone.

## Implementation Plan

1. Update the governed request builder in
   `frontend/apps/skriptoteket/src/api/sirConvertGateway/`:
   - add centralized constants for `source_evidence_only`,
     `local_llm_suggest_missing_machine_marked`,
     `local_llm_apply_missing_machine_marked_with_review`, and
     `remote_provider_policy=forbidden`;
   - make the first authenticated Exam Converter submit request advisory
     enrichment by default;
   - make overlay submits explicitly use reviewed apply mode; and
   - keep idempotency digests sensitive to completion mode and overlay JSON.
2. Add focused parser/types for `answer_key_completion_report_v1` and
   `effective_ir_json` from the generated Sir Convert contract:
   - validate schema versions and required lineage fields;
   - reject unknown candidate states rather than silently degrading;
   - keep raw answer payloads bounded to supported machine-marked shapes; and
   - preserve report SHA/digest fields needed for the reviewed overlay.
3. Extend `useExamConverterReviewArtifacts` so one load gathers:
   `bundle_manifest`, `ir_json`, `migration_manifest`,
   `target_readiness_report`, `answer_key_completion_report`, and
   `effective_ir_json` when present. Missing optional reviewed-apply artifacts
   may be represented as absent; missing advisory report in advisory mode is a
   contract failure.
4. Split the current review projection if needed to keep modules small. The
   normalized per-item model must contain:
   - `itemId`, `sequence`, `itemType`, `sourceItemFingerprint`,
     `promptPreview`, `currentAnswerKeyProvenance`, and `missingFields`;
   - `llmCandidate` with `decisionState`, `validationState`, `backendStatus`,
     `backendFailureCode`, `candidateId`, `candidatePayloadDigest`,
     `providerProfileId`, `modelProfile`, `promptTemplateVersion`,
     `schemaName`, `schemaVersion`, and `answerPayload`; and
   - a null candidate when no candidate is needed or usable.
5. Implement the approved UI slice from the PR-0326 mockup bundle. The selected
   question detail pane owns AI-facit review; the grid keeps only the existing
   compact columns plus symbolic status. Product-approved purpose for the bulk
   affordance: accept all currently valid supported suggestions; do not use that
   verbose phrase as the button label.
6. Implement the teacher review state as explicit, source-bound UI state:
   - valid supported candidates can be accepted unchanged;
   - supported candidates can be edited before accept when the payload kind is
     implemented for this slice;
   - invalid, provider-unavailable, skipped, and manual-follow-up candidates are
     visible but not accept-enabled;
   - accept-all applies only to valid supported suggestions that have not been
     rejected or manually edited;
   - changing source file, result PDF, target selection, or rerunning the first
     pass clears review state.
7. Build the reviewed-completion overlay from explicit teacher decisions:
   - schema version `digiexam_ingestion_overlay_v2`;
   - source binding from the bundle manifest;
   - per item `reviewed_completion_answer_key`;
   - `review_outcome=accepted_unchanged` or `teacher_edited`;
   - candidate lineage from the completion report; and
   - no `manual_answer_key`, no `review_decision`, and no
     `effective_item_patch` in this path.
8. Wire the second submit through the existing authenticated runtime bridge:
   - attach `digiexam-ingestion-overlay.json`;
   - set `completion_mode=local_llm_apply_missing_machine_marked_with_review`;
   - preserve HuleEdu Gateway credentials, CSRF, correlation, and idempotency;
   - reload artifacts after terminal result; and
   - render reviewed provenance from `effective_ir_json` and readiness from
     `target_readiness_report_v1`.
9. Keep files gated by producer evidence. `Hämta` and `Spara` remain disabled
   unless the reviewed apply bundle marks the corresponding target exportable.
10. Update this PR, `ST-21-03`, `EPIC-21`, `docs/index.md`, and
    `.codex/handoff.md` with implementation evidence, then create or unblock the
    follow-up live proof slice.

## Implementation Summary

Implemented the authenticated consumer side of the two-pass reviewed-completion
contract. First-pass `.dxe` submissions now request
`local_llm_suggest_missing_machine_marked` with remote providers forbidden.
Review-artifact loading fetches the completion report, effective IR when
present, bundle manifest, IR, migration manifest, readiness report, and target
artifacts through the existing HuleEdu Gateway client.

The question projection now carries source fingerprints, current answer-key
provenance, missing fields, and bounded AI-facit candidate lineage. The visible
grid keeps the approved compact shape: `Fråga`, `Typ`, `Saknas`, `Poäng`, and
`Status`, where status is terracotta robot, green check, or red cross.
Teacher-facing candidate review happens in the right detail panel with
`Godkänn`, `Redigera`, and `Lämna`; the global panel uses `Granska AI-facit`,
`Granska`, `Godkänn alla`, and `Skapa filer`.

Reviewed suggestions build source-bound `digiexam_ingestion_overlay_v2` payloads
with `reviewed_completion_answer_key` entries and bounded candidate lineage.
The reviewed apply pass submits
`local_llm_apply_missing_machine_marked_with_review` plus
`digiexam-ingestion-overlay.json`, then reloads returned artifacts so file
availability remains governed by Sir Convert manifest/readiness evidence.

The accepted-current-state `Godkänn` path remains separate and explicitly uses
`source_evidence_only`.

## UI Contract

The UI must translate service fields into teacher actions without flattening raw
contract data into the screen.

The normalized model still distinguishes source-keyed, no-key-needed, usable
suggestion, invalid suggestion, provider-unavailable, and manual-follow-up
states. The visible UI deliberately collapses that detail:

- robot icon means a usable AI-facit suggestion can be reviewed;
- green check means the item already has what it needs or needs no key;
- red cross means a supported machine-marked item is still missing a key.

Invalid, ineligible, provider-unavailable, unsupported, or absent candidates use
the same missing-key experience as before. The teacher can provide a key or
gapped words in a later correction slice, or proceed through the separate
accepted-current-state path when that is appropriate.

Minimum actions:

- accept one suggestion unchanged;
- reject one suggestion and leave the item for manual follow-up;
- edit one supported suggestion before accept;
- accept all currently valid supported suggestions with one compact affordance;
- submit reviewed suggestions for regenerated target readiness.

Approved Swedish button labels for this slice are compact:

- `Granska`
- `Godkänn`
- `Redigera`
- `Lämna`
- `Godkänn alla`
- `Skapa filer`

## Test Plan

- Focused `sirConvertGateway` tests proving:
  - first submit carries advisory completion options;
  - overlay submit carries reviewed apply options and multipart overlay JSON;
  - idempotency changes when completion mode or reviewed overlay changes; and
  - generated types still include completion report and reviewed lineage fields.
- Focused parser tests for `answer_key_completion_report_v1` and
  `effective_ir_json`, including valid suggestion, invalid suggestion, provider
  unavailable, skipped source-keyed item, manual follow-up, and unknown-state
  rejection.
- Focused projection tests proving the normalized item model joins source item
  fingerprints, prompt preview, current answer-key provenance, missing fields,
  and candidate lineage without inventing source truth.
- Focused frontend tests for:
  - AI-suggested facit presentation;
  - per-item accept/reject/edit behavior;
  - accept-all applying only valid supported suggestions;
  - clearing review state on new first-pass inputs; and
  - file actions staying disabled until reviewed apply readiness returns.
- Focused authenticated runtime tests proving the second submit uses
  `local_llm_apply_missing_machine_marked_with_review` and reloads reviewed
  artifacts before enabling target actions.
- Production bundle grep for `convert.hule.education`, `X-API-Key`,
  `SIR_CONVERT_A_LOT_V2_API_KEY`, `InternalIdentityContextV1`, direct Sir
  Convert upstream hosts, local upstream dev ports, raw prompt text, and raw
  provider response markers.
- `pdm run fe-test` with touched specs.
- `pdm run fe-type-check`
- `pdm run fe-lint`
- `pdm run fe-build`
- `pdm run docs-validate`
- `pdm run handoff-validate`
- `git diff --check`

## Verification Evidence

- `pdm run fe-test -- --run src/api/sirConvertGateway/client.spec.ts src/api/sirConvertGateway/completionContract.spec.ts src/api/sirConvertGateway/requestContext.spec.ts src/views/apps/ExamConverterAuthenticatedReviewSlice.spec.ts src/views/apps/ExamConverterAuthenticatedFilesActionSlice.spec.ts src/views/apps/ExamConverterAuthenticatedRuntimeBridgeSlice.spec.ts`
  passed on 2026-05-17 with 6 files and 41 tests.
- `pdm run fe-type-check` passed on 2026-05-17.
- `pdm run fe-lint` passed on 2026-05-17.
- `pdm run fe-build` passed on 2026-05-17. Vite still emits the existing
  large-chunk warning for unrelated shared bundles.
- Production bundle grep on 2026-05-17 found no browser-shipped
  `convert.hule.education`, `X-API-Key`,
  `SIR_CONVERT_A_LOT_V2_API_KEY`, `InternalIdentityContextV1`, direct local Sir
  Convert port, raw prompt, raw provider response, or student-private answer
  markers under `src/skriptoteket/web/static/spa`.

Live authenticated HuleEdu Gateway proof is intentionally left to the
unblocked `PR-0324` proof rerun, because this slice is the consumer
implementation and the deployed producer still has to prove
`answer_key_completion_report` delivery through the authenticated Gateway path.

## Resolved Questions

- Swedish labels are resolved by the approved mockup:
  `Granska`, `Godkänn`, `Redigera`, `Lämna`, `Godkänn alla`, and `Skapa filer`.
- Edit-before-accept starts with choice payloads in this slice. Gap-fill
  candidates can be accepted unchanged or left for manual follow-up until a
  narrower gapped-word editor is approved.
- Provider/service readiness is not a UI shortcut. This PR requires the
  advisory completion report on first-pass artifact load, but the live
  authenticated proof remains the place to verify deployed Sir Convert returns
  it through the HuleEdu Gateway.
- The accepted-current-state `Godkänn` path remains a separate
  `source_evidence_only` export decision. Reviewed AI-facit uses the
  `reviewed_completion_answer_key` overlay and apply mode.

## Stop Conditions

- Stop if Sir Convert does not return `answer_key_completion_report` for the
  advisory request.
- Stop if `answer_key_completion_report` lacks the candidate lineage needed for
  a bounded `reviewed_completion_answer_key` overlay.
- Stop if an advisory candidate cannot be joined to the source item fingerprint
  and source binding.
- Stop if apply mode calls the provider again instead of consuming the reviewed
  overlay.
- Stop if file export/save readiness would be inferred from local UI state
  instead of Sir Convert's returned manifest/readiness artifacts.
- Stop if the UI would show advisory output as source truth, source provenance,
  or final reviewed truth before teacher action.
- Stop if retained evidence or frontend code exposes raw prompts, raw provider
  responses, student private data, Sir Convert credentials, or HuleEdu identity
  material.

## Rollback Plan

Keep this behavior inside the authenticated Exam Converter route and the
existing Sir Convert Gateway client. Revert the advisory request options,
completion-report parsing, review UI state, and reviewed-overlay submit path as
one slice if the producer contract changes. The existing accepted-current-state
export path from `PR-0325` must remain separable and must not depend on this
reviewed-completion flow.
