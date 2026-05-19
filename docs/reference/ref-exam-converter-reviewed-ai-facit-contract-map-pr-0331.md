---
type: reference
id: REF-exam-converter-reviewed-ai-facit-contract-map-pr-0331
title: "Exam Converter reviewed AI-facit contract map for PR-0331"
status: deprecated
owners: "Codex"
created: 2026-05-17
topic: "exam-converter-reviewed-ai-facit-contract"
links:
  [
    "EPIC-21",
    "ST-21-03",
    "PR-0331",
    "PR-0329",
    "REF-exam-converter-ui-content-model-v1",
  ]
---

# Exam Converter Reviewed AI-Facit Contract Map For PR-0331

> Deprecated workflow note: `PR-0338` retires the reviewed-AI acceptance
> interaction model for the durable authenticated correction-session flow. AI
> answer-key candidates are now editor prefill data only; teacher saves go
> through the normal `applyManualAnswerKey(question, answerKey)` path and carry
> `submission_origin` plus candidate lineage as audit metadata. This reference
> remains historical PR-0331 RCA/evidence, not active implementation guidance.

## Purpose

This reference starts `PR-0331` with a root-cause analysis of the reviewed
AI-facit flow. It maps the teacher flow, Skriptoteket client state, the
Skriptoteket -> Sir Convert Gateway contract, Sir Convert parsing/conversion
stages, and the answer-key metadata shape used when a teacher accepts AI
suggestions.

This is an engineering plumbing reference, not a layout/design artifact.
`PR-0330` remains the small-screen layout task.

## Current User Flow

Observed sequence from the 2026-05-17 user evidence:

1. Teacher uploads a `.dxe` source and starts conversion with PDF and QTI
   targets selected.
2. Skriptoteket submits advisory completion mode:
   `local_llm_suggest_missing_machine_marked`.
3. Sir Convert returns source IR, migration manifest, target readiness, and an
   `answer_key_completion_report` with AI-suggested keys.
4. Skriptoteket shows AI-facit review, bulk selection, and reviewed apply
   actions close together.
5. Teacher selects all valid AI-facit suggestions.
6. Skriptoteket stores local accepted decisions for valid candidates but does
   not send anything yet.
7. Teacher submits reviewed apply. In the current cleaned-up UI this is
   `Skapa filer med facit`; older evidence used less precise labels.
8. Skriptoteket submits a second job in reviewed apply mode with a
   `reviewed_completion_answer_key` overlay.
9. Teacher later sees Files and/or current-state approval affordances.
10. Teacher submits the current-state export path and downloads artifacts.
11. Downloaded PDF/QTI output lacks the reviewed keys. The PDF also contains
    internal fallback text:
    `Manuell bedömning. Ursprunglig lucktext utan betrodda accepterade värden.`

The reported failure is therefore not simply that the first apply pass never
accepted suggestions. The higher-risk path is that a later export/approval path
can replace the reviewed-key job with a current-state/manual-unkeyed job.

## Skriptoteket Client Flow

### First Submit: Advisory Suggestions

`ExamConverterAuthenticatedView.vue` starts conversion by resetting review
state, then calls `submitAndPoll` with:

- `completionMode = local_llm_suggest_missing_machine_marked`;
- selected `.dxe` source;
- optional graded result PDF; and
- selected PDF/QTI targets.

`finishRuntimeResult(..., completionReportRequired=true)` then loads:

- `ir_json`;
- `migration_manifest`;
- `target_readiness_report`;
- required `answer_key_completion_report`; and
- optional `effective_ir_json`.

`digiexamAnswerKeyCompletionReport.ts` parses each advisory item into a
bounded `ExamConverterLlmAnswerKeyCandidate` with:

- `answerPayload`;
- `candidateId`;
- `candidatePayloadDigest`;
- `completionReportSha256`;
- `providerProfileId`;
- `schemaName`;
- `schemaVersion`;
- `promptTemplateVersion`;
- `validationState`; and
- `decisionState`.

Only candidates with `decisionState=suggested`,
`validationState=valid`, and a non-null `answerPayload` are usable.

### Teacher Accepts Suggestions

`useExamConverterAiFacitReview.ts` owns local AI-facit review state.

Per-question approval stores:

```ts
{
  itemId,
  outcome: "accepted_unchanged",
  answerPayload: question.llmCandidate.answerPayload
}
```

Bulk AI-facit selection iterates over the current projection and stores the
same decision for every usable candidate that does not already have a decision.

### Teacher Clicks `Skapa filer`

`handleApplyReviewedSuggestions` builds
`reviewedCompletionOverlay(reviewProjection)` and submits a second job with:

- `completionMode = local_llm_apply_missing_machine_marked_with_review`;
- `ingestionOverlay = reviewedCompletionOverlay`;
- same selected source/supporting files; and
- same targets.

The overlay entry generated for each accepted suggestion has this shape:

```json
{
  "item_id": "item-001",
  "sequence": 1,
  "item_type": "gap_fill",
  "source_item_fingerprint": "sha256:item-source",
  "effective_item_patch": null,
  "manual_answer_key": null,
  "review_decision": null,
  "reviewed_completion_answer_key": {
    "kind": "gap_fill",
    "review_decision_id": "review-item-001",
    "review_outcome": "accepted_unchanged",
    "candidate_lineage": {
      "completion_report_sha256": "sha256:completion-report",
      "candidate_id": "candidate-id",
      "candidate_payload_digest": "sha256:candidate-payload",
      "provider_profile_id": "provider-profile",
      "schema_name": "schema-name",
      "schema_version": "schema-version",
      "prompt_template_version": "prompt-template-version",
      "validation_state": "valid"
    },
    "answer_payload": {
      "kind": "gap_fill",
      "gap_answers": [
        {"gap_id": "gap-id", "accepted_values": ["value"]}
      ]
    }
  }
}
```

For choice items, `answer_payload` is:

```json
{
  "kind": "choice",
  "correct_alternative_ids": [2]
}
```

### Transport To Sir Convert

`client.ts` serializes the overlay as multipart
`digiexam_ingestion_overlay` with filename from
`DIGIEXAM_INGESTION_OVERLAY_FILENAME`.

`jobSpec.ts` also sets:

- `digiexam_migration_options.completion_mode` to the selected completion
  mode;
- `ingestion_overlay_filename` when an overlay is present; and
- `ingestion_overlay_policy=apply_teacher_overlay`.

`requestContext.ts` includes the stable overlay JSON in both:

- the source label used for correlation ID generation; and
- the idempotency digest parts.

Therefore, a reviewed-apply submit with overlay should be a distinct Sir
Convert job from the first advisory job.

## Sir Convert Parsing And Conversion Flow

Sir Convert's `digiexam_dxe -> examnet_migration_bundle` route is orchestrated
by `digiexam_migration_bundle_builder.py`.

The high-level order is:

1. Parse the uploaded `.dxe` into source parser output.
2. Build immutable `DigiExamIntermediateExam` source IR.
3. Write `ir_json`.
4. Build `migration_manifest` and source fingerprints.
5. Resolve requested targets and completion mode.
6. If an ingestion overlay exists, parse and apply it to an effective renderer
   exam.
7. If renderer input changed, emit `effective_ir_json`.
8. Optionally write answer-key completion reports according to completion
   mode.
9. Render Exam.net PDF from the effective exam.
10. Build QTI package from the effective exam.
11. Build target readiness from the effective exam and target artifacts.
12. Write final artifact manifest.

Important contract boundary: source IR and parser provenance remain immutable.
Reviewed AI keys are allowed to change only effective renderer input and
effective IR/reporting.

## Sir Convert Reviewed-Completion Apply Contract

`digiexam_ingestion_overlay.py` enforces:

- source-file SHA binding;
- source-IR SHA binding;
- source-IR schema binding;
- item ID, sequence, item type, and source item fingerprint binding;
- reviewed completion entries only when
  `completion_mode=local_llm_apply_missing_machine_marked_with_review`; and
- reviewed apply mode fails closed if no reviewed-completion entries exist.

`digiexam_reviewed_completion_application.py` applies a reviewed completion
only when:

- the source item has no parser/source answer key;
- the reviewed payload validates against the item-local structure;
- `accepted_unchanged` payload digest matches the advisory candidate digest;
  and
- lineage fields are bounded and valid.

If accepted, Sir Convert replaces the renderer item answer key with
`DigiExamAnswerKeyProvenance.MANUAL_TEACHER_KEY`, while the effective IR reports
the provenance as:

- `reviewed` for accepted-unchanged AI candidates; or
- `teacher_provided` for teacher-edited candidates.

The effective answer-key metadata includes:

- `correct_alternative_ids`;
- `correct_gap_answers`;
- `completion_report_sha256`;
- `candidate_id`;
- `candidate_payload_digest`;
- `provider_profile_id`;
- `schema_name`;
- `schema_version`;
- `prompt_template_version`;
- `validation_state`;
- `review_decision_id`; and
- `review_outcome`.

## Accepted-Current-State Is A Different Contract

2026-05-19 update: `PR-0341` supersedes this path as active product behavior.
The analysis below remains the historical root cause for why the path was
removed from the correction-session workflow. Accepted-current-state export is
now treated as an export-owned concern, not teacher authoring state.

Skriptoteket also has an older current-state export path for accepting the
current conversion state. That path is intentionally not an answer-key path.

`digiexamAcceptedCurrentStateOverlay.ts` builds overlay entries with:

```json
{
  "manual_answer_key": null,
  "reviewed_completion_answer_key": null,
  "review_decision": {
    "kind": "accept_current_state_for_export",
    "accepted_targets": ["examnet_pdf", "qti_package"]
  }
}
```

This says "export the current state anyway." It does not preserve or create AI
answer-key evidence.

In Sir Convert, accepted-current-state decisions are tracked separately as
`accepted_review_decisions`. They do not create replacements, so
`renderer_input_changed` remains false unless another overlay field changed the
item. If this current-state job is submitted after a reviewed-completion job,
it starts again from the uploaded source file and source IR unless the reviewed
completion entries are also included in that new overlay.

## Working Root Cause

The most likely root cause is a destructive branch in the teacher flow:

1. The bulk AI-facit selection action correctly stores local accepted
   AI-facit decisions.
2. `Skapa filer` can correctly submit those decisions as
   `reviewed_completion_answer_key` entries.
3. The reviewed apply job may produce an `effective_ir_json` containing
   effective answer keys.
4. Skriptoteket parses `effective_ir_json` into `effectiveAnswerKeysByItem`,
   but `digiexamIrReviewParser.ts` does not use that map when projecting
   question rows, missing-facit counts, default mode, or accepted-current-state
   overlay eligibility.
5. The post-apply UI can therefore continue to look like the source IR still
   has missing facit.
6. The teacher could then click the generic current-state approval action.
7. That submits a new source-evidence/current-state job with only
   `review_decision` entries, not the prior `reviewed_completion_answer_key`
   entries.
8. Sir Convert renders that later job from source-only/manual-unkeyed state,
   because accepted-current-state is not an answer-key overlay.
9. Skriptoteket updates `lastJobId`/`lastCorrelationId` to this later job, so
   downloads come from the manual-unkeyed artifacts rather than from the
   reviewed-key apply job.

This explains the user-observed final artifacts:

- The PDF contains manual/free-text fallback content because the last exported
  job was accepted-current-state/manual-unkeyed.
- The QTI package lacks `correctResponse` declarations because manual-unkeyed
  QTI items intentionally have no automatic keys.
- The teacher-approved AI keys are effectively removed from the downloadable
  output because the later overlay did not carry them forward.

## Corrected Item-Type Contract

The item-type support contract for `PR-0331` is source-neutral and must not be
derived from the current DigiExam-specific adapter shape.

- Matching items are supported by the generic intermediate IR and by the target
  export contract when matching structure and key pairs are present.
- Single-gap and multi-gap/open-cloze `Lucktext` items are supported by the
  generic intermediate IR and by the QTI/PDF export contract when gapped key
  values are present.
- PDF may render gapped items as free text, but it must include the accepted
  gapped-item key values in the exported artifact.
- QTI must preserve keyed choice, matching, and gapped/open-cloze semantics when
  the effective exam contains those keys.
- Any current source-specific DigiExam adapter path that serializes choice,
  matching, or gapped/open-cloze shapes as keyless/manual-only output despite
  effective keys is implementation drift, not a product limitation.

Therefore `PR-0331` must distinguish:

- accepted AI keys lost by a later current-state overwrite;
- reviewed keys present in `effective_ir_json` but dropped by a target adapter
  or renderer;
- artifact copy that exposes internal fallback diagnostics instead of
  teacher-facing output; and
- the single accepted PDF exception: gapped items may be rendered as free text,
  but only with the accepted gapped key values included.

## Verification Matrix

Implementation should prove each boundary separately:

| Boundary | Required evidence |
|---|---|
| Advisory report -> UI candidates | Candidate count, item IDs, payload kind, validation state, candidate digest. |
| Bulk AI-facit selection -> local decisions | Accepted decision count equals usable candidate count unless a prior explicit decision exists. |
| Local decisions -> overlay | Overlay item count, item IDs, source binding, reviewed-completion payload, lineage digest. |
| Overlay submit -> Sir Convert job | Multipart overlay present, job spec apply mode, overlay policy, non-replayed job ID/correlation where expected. |
| Sir Convert overlay -> effective IR | `ingestion_overlay_report.accepted_entries` includes `reviewed_completion_answer_key`; `effective_ir_json.items[].effective_answer_key` contains reviewed/teacher-provided keys. |
| Effective IR -> Skriptoteket projection | Rows with effective keys no longer show `Facit` missing; accepted-current-state overlay is not offered for those items as if they were still source-missing. |
| Post-apply UI -> subsequent actions | Switching tabs/files does not reset AI decisions; any later create/export path either preserves reviewed keys or is blocked/explained. |
| Effective exam -> PDF/QTI | Downloaded artifacts contain expected key semantics for choice, matching, and gapped/open-cloze items; PDF gapped-item free-text rendering still includes accepted key values. |
| Artifact copy | No internal fallback diagnostics appear in teacher-facing artifacts. |

## Immediate Implementation Target

Start with a failing focused frontend/runtime test that reproduces the reported
sequence:

1. advisory bundle with multiple valid AI-facit candidates;
2. teacher selects all valid AI-facit suggestions;
3. teacher clicks `Skapa filer`;
4. reviewed apply bundle includes `effective_ir_json` with reviewed keys;
5. projection still offers/permits accepted-current-state approval;
6. teacher submits current-state export;
7. next submit omits `reviewed_completion_answer_key` entries.

The first fix should make this impossible by treating reviewed accepted keys as
durable conversion intent in the post-apply state. A subsequent
accepted-current-state action must not erase them or replace the downloadable
job with source-only/manual-unkeyed artifacts.

Initial `PR-0331` cleanup on 2026-05-17 codifies this destructive path in the
authenticated review slice tests. The fixture now keeps the source IR and
migration manifest source-missing after reviewed apply and moves reviewed keys
to `effective_ir_json`; the parser/projection then consumes effective keys when
projecting rows and suppresses the accepted-current-state overlay for reviewed
apply bundles that contain effective answer keys.

The next cleanup on 2026-05-17 removed teacher-facing ambiguity that was not
allowed to survive as legacy behavior:

- Files no longer falls back to raw `Orsak: ${reasonCode}` copy.
- Current-state export no longer shares generic approval language with
  AI-facit approval.
- AI-facit candidate actions now distinguish local selection
  (`Använd förslag`, `Använd alla förslag`) from the reviewed apply submit
  (`Skapa filer med facit`).

The 2026-05-17 correction also clarifies and removes the old `Lämna` behavior.
It mapped to local Vue state only and was omitted from the reviewed-completion
overlay because the Sir Convert `reviewed_completion_answer_key.review_outcome`
contract only accepts `accepted_unchanged` and `teacher_edited`. It was
therefore not a submitted review decision. PR-0331 removes that fake reject
branch from the active UI/state path; real rejection/global rejection must be
implemented as an explicit source-backed contract before it can create PDF/QTI
artifacts.

Any wording about teacher edits, "adding missing keys", prompt/stem changes, or
teacher-authored answer-key correction is out of scope for `PR-0331`. That
broader workflow is now governed separately by proposed `ADR-0086` and
independent `PR-0332`. It must not be represented as parser metadata mutation
after the source IR is written and must not reintroduce local-only controls that
imply persisted correction or export readiness.

## 2026-05-18 Hemma/Public Proof Closeout

The producer/artifact boundary is now proven for the retained ecology `.dxe`
fixture after Sir Convert commit `166fea9140ac2e5709aa30f5b432ffe1e53fe2c3`
fixed the OpenAI Responses vision image URL shape.

Retained proof:

- `.artifacts/playwright-pr-0331-reviewed-ai-facit-live/20260518T192044Z/manifest.redacted.json`

The proof script forces fresh Sir Convert idempotency keys for its POSTs and
records `idempotent_replay`, so the result cannot be satisfied by old advisory
jobs or stale AI suggestions. The retained manifest shows:

- advisory job `jobv2_e9031daf34424bd6a729df167f` and reviewed-apply job
  `jobv2_2fbff2f0d8d84f23aa4b0e83de` were fresh
  (`idempotent_replay=false`);
- the reviewed overlay contained four reviewed-completion entries:
  `item-001`, `item-002`, `item-003`, and image-backed `item-013`;
- `effective_ir_json` retained reviewed choice keys and item-013 reviewed
  gap-fill values with OpenAI mini lineage;
- `ingestion_overlay_report` accepted four entries and rejected none;
- the post-apply UI reported `Provet är konverterat`, exposed PDF/QTI as
  `Kan hämtas`, and did not show raw reason-code text; and
- downloaded PDF/QTI inspection found no forbidden internal fallback
  diagnostics, with the QTI package retaining correct responses.

This closes the `PR-0331` contract-map concern for reviewed-key survival
through Skriptoteket projection, reviewed apply, target readiness, and
downloaded artifacts. Future teacher-owned correction work remains governed by
`ADR-0086` and `PR-0332`.
