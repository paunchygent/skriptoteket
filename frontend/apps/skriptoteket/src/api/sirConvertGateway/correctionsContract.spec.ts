/**
 * Sir Convert unified correction contract specs.
 *
 * Domain purpose:
 *   Prove Skriptoteket's generated Sir Convert v2 consumer types expose the
 *   unified source-state/apply route payloads used by teacher corrections.
 *
 * Relationships:
 *   - Guards PR-0332 against stale generated OpenAPI types.
 *   - Covers only Task 333 non-matching correction families; matching remains
 *     blocked until the Task 332 producer state exists.
 */

import { describe, expect, it } from "vitest";

import type {
  ExamAuthoringCorrectionSourceBinding,
  ExamAuthoringCorrectionSourceState,
  ExamAuthoringCorrectionSourceStateIssueRequest,
  ExamAuthoringCorrectionSourceStateIssueResult,
  ExamAuthoringCorrectionsApplyRequest,
  ExamAuthoringNonMatchingCorrectionEntry,
} from "./types";

type Task333CorrectionEntry = Extract<
  ExamAuthoringNonMatchingCorrectionEntry,
  {
    kind:
      | "item_text_patch"
      | "manual_choice_answer_key"
      | "manual_gap_open_cloze_answer_key"
      | "point_correction";
  }
>;

function sourceBinding(): ExamAuthoringCorrectionSourceBinding {
  return {
    source_authoring_schema_version: "exam_authoring_ir_v1",
    source_bundle_id: "bundle-001",
    source_file_sha256: "sha256:source-file",
    source_state_sha256: "sha256:source-state",
    source_state_signature: "signature",
  };
}

function sourceAuthoringState(): ExamAuthoringCorrectionSourceState {
  return {
    schema_version: "exam_authoring_correction_source_state_v1",
    source_authoring_schema_version: "exam_authoring_ir_v1",
    source_state_sha256: "sha256:source-state",
    items: [
      {
        choice_interactions: [],
        gap_open_cloze_interactions: [],
        item_id: "item-001",
        item_type: "multiple_choice",
        matching_interactions: [],
        max_score: null,
        prompt_html: null,
        prompt_lines: ["Question"],
        sequence: 1,
        source_item_fingerprint: "sha256:item-001",
        title: "Question 1",
      },
    ],
  };
}

describe("Sir Convert Gateway unified correction contract", () => {
  it("keeps source-state issue request and result types generated", () => {
    const request = {
      expected_source_state_sha256: "sha256:source-state",
      job_id: "jobv2_001",
      schema_version: "exam_authoring_correction_source_state_issue_request_v1",
    } satisfies ExamAuthoringCorrectionSourceStateIssueRequest;
    const result = {
      schema_version: "exam_authoring_correction_source_state_issue_result_v1",
      source_authoring_state: sourceAuthoringState(),
      source_binding: sourceBinding(),
    } satisfies ExamAuthoringCorrectionSourceStateIssueResult;

    expect(request.schema_version).toBe(
      "exam_authoring_correction_source_state_issue_request_v1",
    );
    expect(result.source_binding.source_state_sha256).toBe("sha256:source-state");
  });

  it("keeps Task 333 non-matching apply entries and excludes matching from this slice", () => {
    const pointCorrection = {
      entry_id: "corr-points-item-001",
      item_id: "item-001",
      item_type: "multiple_choice",
      kind: "point_correction",
      max_score: 2,
      sequence: 1,
      source_item_fingerprint: "sha256:item-001",
    } satisfies Task333CorrectionEntry;
    const choiceAnswerKey = {
      candidate_lineage: null,
      correct_choice_ids: ["choice-001"],
      entry_id: "corr-choice-item-001",
      interaction_id: "choice-item-001",
      item_id: "item-001",
      item_type: "multiple_choice",
      kind: "manual_choice_answer_key",
      sequence: 1,
      source_item_fingerprint: "sha256:item-001",
      submission_origin: "teacher_authored",
    } satisfies Task333CorrectionEntry;
    const gapAnswerKey = {
      candidate_lineage: null,
      entry_id: "corr-gap-item-002",
      gap_answers: [{ accepted_values: ["kretslopp"], gap_id: "gap-001" }],
      interaction_id: "gap-item-002",
      item_id: "item-002",
      item_type: "gap_fill",
      kind: "manual_gap_open_cloze_answer_key",
      sequence: 2,
      source_item_fingerprint: "sha256:item-002",
      submission_origin: "teacher_authored",
    } satisfies Task333CorrectionEntry;
    const itemTextPatch = {
      entry_id: "corr-text-item-003",
      item_id: "item-003",
      item_type: "open_ended",
      kind: "item_text_patch",
      patches: [{ field: "prompt_lines", value: "Updated prompt" }],
      sequence: 3,
      source_item_fingerprint: "sha256:item-003",
    } satisfies Task333CorrectionEntry;
    const request = {
      corrections: [pointCorrection, choiceAnswerKey, gapAnswerKey, itemTextPatch],
      request_id: "request-001",
      requested_targets: ["examnet_pdf", "qti_package"],
      schema_version: "exam_authoring_corrections_apply_request_v1",
      source_authoring_state: sourceAuthoringState(),
      source_binding: sourceBinding(),
    } satisfies ExamAuthoringCorrectionsApplyRequest;

    expect(request.corrections.map((correction) => correction.kind)).toEqual([
      "point_correction",
      "manual_choice_answer_key",
      "manual_gap_open_cloze_answer_key",
      "item_text_patch",
    ]);
    expect(JSON.stringify(request)).not.toContain("manual_matching_answer_key");
  });
});
