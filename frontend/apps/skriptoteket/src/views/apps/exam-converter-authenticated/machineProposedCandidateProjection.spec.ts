import { describe, expect, it } from "vitest";

import type { ExamConverterCorrectionSessionResponse } from "../../../api/examConverterCorrectionSessions";
import type {
  DigiExamAnswerKeyReviewState,
  DigiExamAnswerKeyReviewStateItem,
  ExamAuthoringCorrectionSourceStateIssueResult,
  ExamAuthoringCorrectionsApplyResult,
  ExamConverterArtifactManifest,
} from "../../../api/examConverterContracts";
import {
  ANSWER_KEY_COMPLETION_REPORT_SCHEMA_VERSION,
  EXAM_CONVERTER_BUNDLE_STATUS_PARTIAL,
  ANSWER_KEY_REVIEW_STATE_SCHEMA_VERSION,
  DIGIEXAM_EFFECTIVE_EXAM_SCHEMA_VERSION,
  DIGIEXAM_INTERMEDIATE_EXAM_SCHEMA_VERSION,
  DIGIEXAM_IR_MANIFEST_SCHEMA_VERSION,
  DIGIEXAM_ITEM_TYPE_GAP_FILL,
  DIGIEXAM_ITEM_TYPE_SINGLE_CHOICE,
  DIGIEXAM_MANUAL_FOLLOW_UP_MANUAL_ANSWER_KEY_REQUIRED,
  DIGIEXAM_MIGRATION_BUNDLE_SCHEMA_VERSION,
  DIGIEXAM_SOURCE_FORMAT,
  TARGET_READINESS_REPORT_SCHEMA_VERSION,
} from "../../../api/examConverterContracts";
import { parseAnswerKeyCompletionReport, parseEffectiveItemState } from "./digiexamAnswerKeyCompletionReport";
import { projectUnifiedCorrectionResult } from "./correctionSessionProjection";
import { parseExamConverterReviewProjection } from "./digiexamIrReviewParser";

function candidateReviewItem(
  overrides: Partial<DigiExamAnswerKeyReviewStateItem> = {},
): DigiExamAnswerKeyReviewStateItem {
  return {
    choice_ids: [],
    choice_interaction_ids: [],
    correction_affordances: ["manual_gap_open_cloze_answer_key"],
    current_key_origin: "none",
    gap_ids: ["gap-001"],
    gap_interaction_ids: ["gap-item-001"],
    item_id: "item-001",
    item_type: DIGIEXAM_ITEM_TYPE_GAP_FILL,
    message_key: "exam_converter.answer_key.advisory_candidate_pending",
    provenance_detail: {
      candidate_id: "candidate-item-001",
      candidate_payload_digest: "sha256:candidate-item-001",
      completion_report_sha256: "sha256:completion-report",
      prompt_template_version: "digiexam-gap-answer-key-v1",
      provider_profile_id: "provider-luna",
      schema_name: "digiexam_gap_answer_key_decision_v1",
      schema_version: "digiexam_gap_answer_key_decision_v1",
      validation_state: "valid",
    },
    reasons: ["advisory_candidate_pending"],
    replay_artifact_references: [],
    review_state: "review_required",
    sequence: 1,
    source_item_fingerprint: "sha256:item-001",
    ...overrides,
  };
}

function reviewedItem(
  overrides: Partial<DigiExamAnswerKeyReviewStateItem> = {},
): DigiExamAnswerKeyReviewStateItem {
  return {
    choice_ids: ["choice-2"],
    choice_interaction_ids: ["choice-item-002"],
    correction_affordances: [],
    current_key_origin: "reviewed_advisory",
    gap_ids: [],
    gap_interaction_ids: [],
    item_id: "item-002",
    item_type: DIGIEXAM_ITEM_TYPE_SINGLE_CHOICE,
    message_key: "exam_converter.answer_key.reviewed_advisory_accepted",
    provenance_detail: null,
    reasons: ["reviewed_advisory_accepted"],
    replay_artifact_references: [],
    review_state: "review_complete",
    sequence: 2,
    source_item_fingerprint: "sha256:item-002",
    ...overrides,
  };
}

function buildReviewStatePayload(): DigiExamAnswerKeyReviewState {
  return {
    schema_version: ANSWER_KEY_REVIEW_STATE_SCHEMA_VERSION,
    items: [candidateReviewItem(), reviewedItem()],
  };
}

function buildIrPayload() {
  return {
    schema_version: DIGIEXAM_INTERMEDIATE_EXAM_SCHEMA_VERSION,
    source_filename: "lag-och-ratt.dxe",
    warnings: [],
    manual_follow_ups: [
      {
        item_id: "item-001",
        message: "Manual answer key is required.",
        reason: DIGIEXAM_MANUAL_FOLLOW_UP_MANUAL_ANSWER_KEY_REQUIRED,
      },
    ],
    items: [
      {
        answer_key: { provenance: "absent" },
        embedded_asset_references: [],
        embedded_assets: [],
        gaps: [{ guid: "gap-001", validations: [] }],
        item_id: "item-001",
        item_type: DIGIEXAM_ITEM_TYPE_GAP_FILL,
        max_score: 1,
        options: [],
        prompt_html: null,
        prompt_lines: ["Lucktextfråga."],
        sequence: 1,
        title: "Fråga 1",
        warnings: [],
      },
      {
        answer_key: { provenance: "absent" },
        alternatives: [
          { about: "", id: 1, title: "Fel svar" },
          { about: "", id: 2, title: "Rätt svar" },
        ],
        embedded_asset_references: [],
        embedded_assets: [],
        gaps: [],
        item_id: "item-002",
        item_type: DIGIEXAM_ITEM_TYPE_SINGLE_CHOICE,
        max_score: 1,
        options: [],
        prompt_html: null,
        prompt_lines: ["Vilket svar är rätt?"],
        sequence: 2,
        title: "Fråga 2",
        warnings: [],
      },
    ],
  };
}

function buildManifestPayload() {
  return {
    schema_version: DIGIEXAM_IR_MANIFEST_SCHEMA_VERSION,
    warning_count: 0,
    manual_follow_up_count: 1,
    item_summaries: [
      {
        item_id: "item-001",
        item_type: DIGIEXAM_ITEM_TYPE_GAP_FILL,
        source_item_fingerprint: "sha256:item-001",
      },
      {
        item_id: "item-002",
        item_type: DIGIEXAM_ITEM_TYPE_SINGLE_CHOICE,
        source_item_fingerprint: "sha256:item-002",
      },
    ],
  };
}

function buildArtifactManifest(): ExamConverterArtifactManifest {
  return {
    artifacts: [],
    bundle_status: EXAM_CONVERTER_BUNDLE_STATUS_PARTIAL,
    job_id: "job-001",
    manual_follow_up: {
      artifact_key: "manual_follow_up_report",
      count: 1,
      required: true,
    },
    readiness: {
      artifact_key: "target_readiness_report",
      exportable_targets: [],
      review_required: true,
    },
    schema_version: DIGIEXAM_MIGRATION_BUNDLE_SCHEMA_VERSION,
    source: {
      filename: "lag-och-ratt.dxe",
      format: DIGIEXAM_SOURCE_FORMAT,
      sha256: "sha256:source",
    },
    source_binding: {
      effective_exam_schema_version: DIGIEXAM_EFFECTIVE_EXAM_SCHEMA_VERSION,
      effective_exam_sha256: "sha256:effective",
      source_ir_schema_version: DIGIEXAM_INTERMEDIATE_EXAM_SCHEMA_VERSION,
      source_ir_sha256: "sha256:source-ir",
    },
    warnings: null,
  };
}

function buildTargetReadinessReport() {
  return {
    effective_exam_sha256: "sha256:effective",
    job_id: "job-001",
    schema_version: TARGET_READINESS_REPORT_SCHEMA_VERSION,
    source_ir_sha256: "sha256:source-ir",
    targets: [],
  };
}

function buildCompletionReportPayload() {
  return {
    completion_mode: "local_llm_suggest_missing_machine_marked",
    items: [
      {
        answer_payload: {
          gap_answers: [{ accepted_values: ["Åklagare"], gap_id: "gap-001" }],
          kind: "gap_fill",
        },
        backend_failure_code: null,
        backend_status: "ok",
        candidate_id: "candidate-item-001",
        candidate_payload_digest: "sha256:candidate-item-001",
        decision_state: "suggested",
        item_id: "item-001",
        item_type: DIGIEXAM_ITEM_TYPE_GAP_FILL,
        model_profile: "gpt-5.6-luna-low",
        prompt_template_version: "digiexam-gap-answer-key-v1",
        provider_profile_id: "provider-luna",
        schema_name: "digiexam_gap_answer_key_decision_v1",
        schema_version: "digiexam_gap_answer_key_decision_v1",
        sequence: 1,
        validation_state: "valid",
      },
      {
        answer_payload: {
          correct_alternative_ids: [2],
          kind: "choice",
        },
        backend_failure_code: null,
        backend_status: "ok",
        candidate_id: "candidate-item-002",
        candidate_payload_digest: "sha256:candidate-item-002",
        decision_state: "suggested",
        item_id: "item-002",
        item_type: DIGIEXAM_ITEM_TYPE_SINGLE_CHOICE,
        model_profile: "gpt-5.6-luna-low",
        prompt_template_version: "digiexam-choice-answer-key-v1",
        provider_profile_id: "provider-luna",
        schema_name: "digiexam_choice_answer_key_decision_v1",
        schema_version: "digiexam_choice_answer_key_decision_v1",
        sequence: 2,
        validation_state: "valid",
      },
    ],
    job_id: "job-001",
    provider_lineage: null,
    schema_version: ANSWER_KEY_COMPLETION_REPORT_SCHEMA_VERSION,
  };
}

function buildEffectiveIrPayload() {
  return {
    answer_key_completion_report_sha256: "sha256:completion-report",
    ingestion_overlay_sha256: null,
    items: [
      {
        effective_answer_key: {
          correct_gap_answers: [{ gap_id: "gap-001", value: "Åklagare" }],
          lineage: null,
          provenance: "machine_proposed",
        },
        effective_item_patch: null,
        effective_point_correction: null,
        item_id: "item-001",
        item_type: DIGIEXAM_ITEM_TYPE_GAP_FILL,
        sequence: 1,
        source_item_fingerprint: "sha256:item-001",
      },
      {
        effective_answer_key: {
          correct_alternative_ids: [2],
          lineage: {
            candidate_id: "candidate-item-002",
            candidate_payload_digest: "sha256:candidate-item-002",
            completion_report_sha256: "sha256:completion-report",
            prompt_template_version: "digiexam-choice-answer-key-v1",
            provider_profile_id: "provider-luna",
            review_decision_id: "decision-item-002",
            review_outcome: "accepted_unchanged",
            schema_name: "digiexam_choice_answer_key_decision_v1",
            schema_version: "digiexam_choice_answer_key_decision_v1",
            validation_state: "valid",
          },
          provenance: "reviewed",
        },
        effective_item_patch: null,
        effective_point_correction: null,
        item_id: "item-002",
        item_type: DIGIEXAM_ITEM_TYPE_SINGLE_CHOICE,
        sequence: 2,
        source_item_fingerprint: "sha256:item-002",
      },
    ],
    schema_version: DIGIEXAM_EFFECTIVE_EXAM_SCHEMA_VERSION,
    source_file_sha256: "sha256:source",
    source_ir_schema_version: DIGIEXAM_INTERMEDIATE_EXAM_SCHEMA_VERSION,
    source_ir_sha256: "sha256:source-ir",
  };
}

function buildCorrectionSession(): ExamConverterCorrectionSessionResponse {
  return {
    active_intents: [],
    conversion_hub_job_id: "local-conversion-hub-job-1",
    owner_user_id: "11111111-1111-4111-8111-111111111111",
    session_id: "33333333-3333-4333-8333-333333333333",
    session_version: 1,
    source_binding: {
      source_authoring_schema_version: "exam_authoring_ir_v1",
      source_bundle_id: "job-001",
      source_file_sha256: "sha256:source",
      source_state_sha256: "sha256:source-state",
      source_state_signature: "hmac-sha256:signature",
    },
  };
}

function buildCorrectionSourceState(): ExamAuthoringCorrectionSourceStateIssueResult {
  return {
    schema_version: "exam_authoring_correction_source_state_issue_result_v1",
    source_binding: {
      source_authoring_schema_version: "exam_authoring_ir_v1",
      source_bundle_id: "job-001",
      source_file_sha256: "sha256:source",
      source_state_sha256: "sha256:source-state",
      source_state_signature: "hmac-sha256:signature",
    },
    source_authoring_state: {
      items: [
        {
          choice_interactions: [],
          gap_open_cloze_interactions: [
            {
              answer_key: {
                accepted_values: [],
                provenance: "absent",
              },
              gaps: [{ display_order: 1, gap_id: "gap-001", required_for_auto_evaluation: true }],
              interaction_id: "gap-item-001",
              normalization_profile: "default",
            },
          ],
          item_id: "item-001",
          item_type: DIGIEXAM_ITEM_TYPE_GAP_FILL,
          matching_interactions: [],
          max_score: 1,
          prompt_lines: ["Lucktextfråga."],
          sequence: 1,
          source_item_fingerprint: "sha256:item-001",
          title: "Fråga 1",
        },
        {
          choice_interactions: [
            {
              answer_key: {
                correct_choice_ids: [],
                provenance: "absent",
              },
              choices: [
                { choice_id: "choice-1", order: 1, source_id: "1", text: "Fel svar" },
                { choice_id: "choice-2", order: 2, source_id: "2", text: "Rätt svar" },
              ],
              interaction_id: "choice-item-002",
              interaction_kind: "single_choice",
              max_correct_choices: 1,
              min_correct_choices: 1,
            },
          ],
          gap_open_cloze_interactions: [],
          item_id: "item-002",
          item_type: DIGIEXAM_ITEM_TYPE_SINGLE_CHOICE,
          matching_interactions: [],
          max_score: 1,
          prompt_lines: ["Vilket svar är rätt?"],
          sequence: 2,
          source_item_fingerprint: "sha256:item-002",
          title: "Fråga 2",
        },
      ],
      schema_version: "exam_authoring_correction_source_state_v1",
      source_authoring_schema_version: "exam_authoring_ir_v1",
      source_state_sha256: "sha256:source-state",
    },
  };
}

function buildCorrectionResult(): ExamAuthoringCorrectionsApplyResult {
  return {
    answer_key_review_state: buildReviewStatePayload(),
    artifact_availability: [],
    correction_report: {
      accepted_entries: [],
      rejected_entries: [],
      schema_version: "exam_authoring_correction_report_v1",
    },
    effective_state: {
      effective_state_sha256: "sha256:corrected-effective-state",
      items: [
        {
          choice_interactions: [
            {
              answer_key: {
                correct_choice_ids: ["choice-2"],
                provenance: "reviewed",
              },
              choices: [
                { choice_id: "choice-1", order: 1, source_id: "1", text: "Fel svar" },
                { choice_id: "choice-2", order: 2, source_id: "2", text: "Rätt svar" },
              ],
              interaction_id: "choice-item-002",
              interaction_kind: "single_choice",
              max_correct_choices: 1,
              min_correct_choices: 1,
            },
          ],
          gap_open_cloze_interactions: [],
          item_id: "item-002",
          item_type: DIGIEXAM_ITEM_TYPE_SINGLE_CHOICE,
          matching_interactions: [],
          max_score: 1,
          prompt_lines: ["Vilket svar är rätt?"],
          sequence: 2,
          source_item_fingerprint: "sha256:item-002",
          title: "Fråga 2",
        },
      ],
      schema_version: "exam_authoring_effective_state_v1",
    },
    request_id: "correction-session-replay-job-001-v1",
    schema_version: "exam_authoring_corrections_apply_result_v1",
    source_binding: buildCorrectionSourceState().source_binding,
    target_readiness: {
      schema_version: TARGET_READINESS_REPORT_SCHEMA_VERSION,
      targets: [],
    },
  };
}

describe("machine_proposed advisory candidate projection", () => {
  it("keeps pending machine-proposed candidates visible while suppressing finalized reviewed keys", () => {
    const completionReport = parseAnswerKeyCompletionReport({
      completionReportSha256: "sha256:completion-report",
      payload: buildCompletionReportPayload(),
    });
    const effectiveItemState = parseEffectiveItemState(buildEffectiveIrPayload());

    const projection = parseExamConverterReviewProjection({
      answerKeyCompletionReport: completionReport,
      answerKeyReviewStateReport: buildReviewStatePayload(),
      artifactManifest: buildArtifactManifest(),
      effectiveAnswerKeysByItem: effectiveItemState.answerKeysByItem,
      effectivePointCorrectionsByItem: effectiveItemState.pointCorrectionsByItem,
      irJson: buildIrPayload(),
      migrationManifest: buildManifestPayload(),
      targetReadinessReport: buildTargetReadinessReport(),
    });

    expect(projection.report.aiSuggestionCount).toBe(1);
    expect(projection.report.aiSuggestionOutcomes.totalCount).toBe(1);
    expect(projection.questions[0]?.effectiveAnswerKey?.provenance).toBe("machine_proposed");
    expect(projection.questions[0]?.llmCandidate?.candidateId).toBe("candidate-item-001");
    expect(projection.questions[1]?.effectiveAnswerKey?.provenance).toBe("reviewed");
    expect(projection.questions[1]?.llmCandidate).toBeNull();

    const replayed = projectUnifiedCorrectionResult({
      correctionSession: buildCorrectionSession(),
      projection,
      result: buildCorrectionResult(),
      sourceState: buildCorrectionSourceState(),
    });

    expect(replayed.report.aiSuggestionCount).toBe(1);
    expect(replayed.report.aiSuggestionOutcomes.totalCount).toBe(1);
    expect(replayed.questions[0]?.effectiveAnswerKey?.provenance).toBe("machine_proposed");
    expect(replayed.questions[0]?.llmCandidate?.candidateId).toBe("candidate-item-001");
    expect(replayed.questions[1]?.effectiveAnswerKey?.provenance).toBe("reviewed");
    expect(replayed.questions[1]?.llmCandidate).toBeNull();
  });
});
