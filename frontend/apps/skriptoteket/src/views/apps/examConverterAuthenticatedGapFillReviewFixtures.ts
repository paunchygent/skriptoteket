/**
 * Exam Converter vision-backed gap-fill review fixtures.
 *
 * Domain purpose:
 *   Model the live PR-0329 handoff where Exam Converter returns a valid
 *   vision-backed Lucktext AI-facit candidate in the first advisory bundle and
 *   a reviewed effective IR in the second apply bundle.
 *
 * Relationships:
 *   - Used by authenticated review specs to prove the Skriptoteket UI handoff.
 *   - Reuses the shared review fixture helpers for gateway-shaped artifacts.
 */

import {
  DIGIEXAM_ARTIFACT_ANSWER_KEY_REVIEW_STATE_REPORT,
  DIGIEXAM_ARTIFACT_TARGET_READINESS_REPORT,
  DIGIEXAM_TARGET_EXAMNET_PDF,
  DIGIEXAM_TARGET_QTI_PACKAGE,
} from "../../api/examConverterContracts";
import {
  ANSWER_KEY_REVIEW_STATE_SCHEMA_VERSION,
  ANSWER_KEY_COMPLETION_REPORT_SCHEMA_VERSION,
  DIGIEXAM_EFFECTIVE_EXAM_SCHEMA_VERSION,
  DIGIEXAM_INTERMEDIATE_EXAM_SCHEMA_VERSION,
  DIGIEXAM_IR_MANIFEST_SCHEMA_VERSION,
  DIGIEXAM_MIGRATION_BUNDLE_SCHEMA_VERSION,
  TARGET_READINESS_REPORT_SCHEMA_VERSION,
} from "../../api/examConverterContracts";
import {
  artifactJsonBlob,
  type ExamConverterGatewayMocks,
  reviewItem,
  submittedJob,
} from "./examConverterAuthenticatedReviewFixtures";

export const REVIEWED_GAP_FILL_APPLY_JOB_ID = "job_reviewed_apply";
export const MANUAL_GAP_FILL_APPLY_JOB_ID = "job_manual_gap_fill_apply";

function replayArtifactReferences(jobId: string) {
  return [
    {
      artifact_key: "correction_replay_examnet_pdf",
      artifact_set_id: `${jobId}-artifact-set-pdf`,
      content_sha256: `sha256:${jobId}-pdf`,
      correction_payload_digest: `sha256:${jobId}-correction-payload`,
      created_at: "2026-06-29T12:00:00Z",
      job_id: jobId,
      replay_profile_version: "correction-replay-v1",
      request_id: `${jobId}-request`,
      schema_version: "correction_replay_artifact_reference_v1",
      source_binding_digest: `sha256:${jobId}-source-binding`,
      source_state_sha256: `sha256:${jobId}-source-state`,
      target: "examnet_pdf",
      target_set_digest: `sha256:${jobId}-target-set`,
    },
    {
      artifact_key: "correction_replay_qti_package",
      artifact_set_id: `${jobId}-artifact-set-qti`,
      content_sha256: `sha256:${jobId}-qti`,
      correction_payload_digest: `sha256:${jobId}-correction-payload`,
      created_at: "2026-06-29T12:00:00Z",
      job_id: jobId,
      replay_profile_version: "correction-replay-v1",
      request_id: `${jobId}-request`,
      schema_version: "correction_replay_artifact_reference_v1",
      source_binding_digest: `sha256:${jobId}-source-binding`,
      source_state_sha256: `sha256:${jobId}-source-state`,
      target: "qti_package",
      target_set_digest: `sha256:${jobId}-target-set`,
    },
  ];
}

function isCorrectedApplyJob(jobId: string): boolean {
  return jobId === REVIEWED_GAP_FILL_APPLY_JOB_ID || jobId === MANUAL_GAP_FILL_APPLY_JOB_ID;
}

function artifactManifestPayload(jobId: string) {
  const isApplyJob = isCorrectedApplyJob(jobId);
  return {
    artifacts: [
      {
        artifact_key: DIGIEXAM_TARGET_EXAMNET_PDF,
        availability: isApplyJob ? "available" : "unavailable",
        content_type: "application/pdf",
        filename: "Ma1c_Exam.net.pdf",
        sha256: isApplyJob ? "sha256:pdf" : null,
        size_bytes: isApplyJob ? 700_416 : null,
        unavailable_code: isApplyJob ? undefined : "manual_answer_key_required",
      },
      {
        artifact_key: DIGIEXAM_TARGET_QTI_PACKAGE,
        availability: isApplyJob ? "available" : "unavailable",
        content_type: "application/zip",
        filename: "Ma1c_QTI.zip",
        sha256: isApplyJob ? "sha256:qti" : null,
        size_bytes: isApplyJob ? 1_258_291 : null,
        unavailable_code: isApplyJob ? undefined : "manual_answer_key_required",
      },
      {
        artifact_key: DIGIEXAM_ARTIFACT_ANSWER_KEY_REVIEW_STATE_REPORT,
        availability: "available",
        content_type: "application/json",
        filename: "answer-key-review-state.json",
        sha256: "sha256:answer-key-review-state-gap",
        size_bytes: 1_024,
      },
      {
        artifact_key: "answer_key_completion_report",
        availability: "available",
        content_type: "application/json",
        filename: "answer-key-completion-report.json",
        sha256: "sha256:completion-report-gap",
        size_bytes: 1_024,
      },
      ...(isApplyJob
        ? [
            {
              artifact_key: "effective_ir_json",
              availability: "available",
              content_type: "application/json",
              filename: "effective-ir.json",
              sha256: "sha256:effective-ir",
              size_bytes: 2_048,
            },
          ]
        : []),
    ],
    bundle_status: isApplyJob ? "complete" : "partial",
    job_id: jobId,
    source: {
      filename: "Ma1c_NationelltProv_HT25.dxe",
      format: "digiexam_dxe",
      sha256: "sha256:source",
    },
    manual_follow_up: {
      artifact_key: "manual_follow_up_report",
      count: isApplyJob ? 0 : 1,
      required: !isApplyJob,
    },
    readiness: {
      artifact_key: "target_readiness_report",
      exportable_targets: isApplyJob
        ? [DIGIEXAM_TARGET_EXAMNET_PDF, DIGIEXAM_TARGET_QTI_PACKAGE]
        : [],
      review_required: !isApplyJob,
    },
    schema_version: DIGIEXAM_MIGRATION_BUNDLE_SCHEMA_VERSION,
    source_binding: {
      effective_exam_schema_version: DIGIEXAM_EFFECTIVE_EXAM_SCHEMA_VERSION,
      effective_exam_sha256: "sha256:effective",
      source_ir_schema_version: DIGIEXAM_INTERMEDIATE_EXAM_SCHEMA_VERSION,
      source_ir_sha256: "sha256:ir",
    },
    warnings: {
      artifact_key: "warnings_report",
      count: 0,
    },
  };
}

function irJsonPayload(_jobId: string) {
  return {
    items: [
      reviewItem({
        answer_key: { provenance: "absent" },
        gaps: [
          { guid: "gap-001", validations: [] },
          { guid: "gap-002", validations: [] },
        ],
        item_id: "item-013",
        sequence: 13,
        title: "Lucktext med bild",
      }),
    ],
    manual_follow_ups: [
      {
        item_id: "item-013",
        message: "Manual answer key is required.",
        reason: "manual_answer_key_required",
        source_span: null,
      },
    ],
    parse_status: "success",
    renderer_ready: true,
    schema_version: DIGIEXAM_INTERMEDIATE_EXAM_SCHEMA_VERSION,
    source_filename: "Ma1c_NationelltProv_HT25.dxe",
    source_producer: null,
    warnings: [],
  };
}

function migrationManifestPayload(_jobId: string) {
  return {
    asset_count: 1,
    asset_summaries: [],
    exam_schema_version: DIGIEXAM_INTERMEDIATE_EXAM_SCHEMA_VERSION,
    item_count: 1,
    item_summaries: [
      {
        answer_key_provenance: "absent",
        asset_summaries: [],
        item_id: "item-013",
        item_type: "gap_fill",
        manual_follow_up_required: true,
        sequence: 13,
        source_item_fingerprint: "sha256:item-013",
        title: "Lucktext med bild",
      },
    ],
    manual_follow_up_count: 1,
    parse_status: "success",
    renderer_ready: true,
    schema_version: DIGIEXAM_IR_MANIFEST_SCHEMA_VERSION,
    source_filename: "Ma1c_NationelltProv_HT25.dxe",
    source_producer: null,
    warning_count: 0,
  };
}

function targetReadinessReportPayload(jobId: string) {
  const isApplyJob = isCorrectedApplyJob(jobId);
  return {
    effective_exam_sha256: isApplyJob ? "sha256:effective-ir" : "sha256:effective",
    job_id: jobId,
    schema_version: TARGET_READINESS_REPORT_SCHEMA_VERSION,
    source_ir_sha256: "sha256:ir",
    targets: [DIGIEXAM_TARGET_EXAMNET_PDF, DIGIEXAM_TARGET_QTI_PACKAGE].map((target) => ({
      artifact_key: isApplyJob ? target : null,
      export_enabled: isApplyJob,
      item_id: isApplyJob ? null : "item-013",
      message_key: isApplyJob
        ? "exam_converter.target.ready"
        : "exam_converter.target.needs_teacher_answer_key",
      readiness: isApplyJob ? "ready" : "needs_teacher_answer_key",
      reason_code: isApplyJob ? "target_available" : "manual_answer_key_required",
      retryable: false,
      sequence: isApplyJob ? null : 13,
      source_item_fingerprint: isApplyJob ? null : "sha256:item-013",
      target,
      teacher_action: isApplyJob ? "none" : "supply_answer_key_overlay",
    })),
  };
}

function answerKeyCompletionReportPayload(candidateAvailable: boolean) {
  return {
    completion_mode: "local_llm_suggest_missing_machine_marked",
    items: [
      candidateAvailable
        ? {
            answer_payload: {
              gap_answers: [
                { accepted_values: ["kretslopp"], gap_id: "gap-001" },
                { accepted_values: ["näringsväv"], gap_id: "gap-002" },
              ],
              kind: "gap_fill",
            },
            backend_failure_code: null,
            backend_status: "success",
            candidate_id: "candidate-item-013",
            candidate_payload_digest: "sha256:candidate-item-013",
            decision_state: "suggested",
            item_id: "item-013",
            item_type: "gap_fill",
            model_profile: "qwen3.6-27b-q6k-mtp",
            prompt_template_version: "digiexam-gap-fill-answer-key-v1",
            provider_profile_id: "task309-llama-cpp",
            schema_name: "digiexam_gap_fill_answer_key_decision_v1",
            schema_version: "digiexam_gap_fill_answer_key_decision_v1",
            sequence: 13,
            validation_state: "valid",
          }
        : {
            answer_payload: null,
            backend_failure_code: null,
            backend_status: "skipped",
            candidate_id: null,
            candidate_payload_digest: null,
            decision_state: "skipped",
            item_id: "item-013",
            item_type: "gap_fill",
            model_profile: null,
            prompt_template_version: null,
            provider_profile_id: null,
            schema_name: null,
            schema_version: null,
            sequence: 13,
            validation_state: "skipped",
          },
    ],
    job_id: "job_exam_converter_review",
    schema_version: ANSWER_KEY_COMPLETION_REPORT_SCHEMA_VERSION,
  };
}

function answerKeyReviewStatePayload(jobId: string, candidateAvailable: boolean) {
  const isManualCorrection = jobId === MANUAL_GAP_FILL_APPLY_JOB_ID;
  const isReviewedCorrection = jobId === REVIEWED_GAP_FILL_APPLY_JOB_ID;
  const isPendingAdvisory = candidateAvailable && !isManualCorrection && !isReviewedCorrection;
  return {
    schema_version: ANSWER_KEY_REVIEW_STATE_SCHEMA_VERSION,
    items: [
      {
        choice_ids: [],
        choice_interaction_ids: [],
        correction_affordances:
          isManualCorrection || isReviewedCorrection ? [] : ["manual_gap_answer_key"],
        current_key_origin: isManualCorrection
          ? "teacher_authored"
          : isReviewedCorrection
            ? "reviewed_advisory"
            : "none",
        gap_ids: ["gap-001", "gap-002"],
        gap_interaction_ids: ["gap-item-013"],
        item_id: "item-013",
        item_type: "gap_fill",
        message_key: isManualCorrection
          ? "exam_converter.answer_key.teacher_answer_key_present"
          : isReviewedCorrection
            ? "exam_converter.answer_key.reviewed_advisory_accepted"
            : isPendingAdvisory
              ? "exam_converter.answer_key.advisory_candidate_pending"
              : "exam_converter.answer_key.manual_required",
        provenance_detail: isManualCorrection || !isPendingAdvisory
          ? null
          : {
              candidate_id: "candidate-item-013",
              candidate_payload_digest: "sha256:candidate-item-013",
              prompt_template_version: "digiexam-gap-fill-answer-key-v1",
              provider_profile_id: "task309-llama-cpp",
              schema_name: "digiexam_gap_fill_answer_key_decision_v1",
              schema_version: "digiexam_gap_fill_answer_key_decision_v1",
              validation_state: "valid",
            },
        reasons: isManualCorrection
          ? ["teacher_answer_key_present"]
          : isReviewedCorrection
            ? ["reviewed_advisory_accepted"]
            : isPendingAdvisory
              ? ["advisory_candidate_pending"]
              : ["manual_answer_key_required"],
        replay_artifact_references:
          isManualCorrection || isReviewedCorrection
            ? replayArtifactReferences(
                isManualCorrection ? MANUAL_GAP_FILL_APPLY_JOB_ID : REVIEWED_GAP_FILL_APPLY_JOB_ID,
              )
            : [],
        review_state:
          isManualCorrection || isReviewedCorrection
            ? "review_complete"
            : isPendingAdvisory
              ? "review_required"
              : "validation_required",
        sequence: 13,
        source_item_fingerprint: "sha256:item-013",
      },
    ],
  };
}

function effectiveIrPayload(jobId: string) {
  const isManualCorrection = jobId === MANUAL_GAP_FILL_APPLY_JOB_ID;
  return {
    answer_key_completion_report_sha256: isManualCorrection
      ? null
      : "sha256:completion-report-gap",
    ingestion_overlay_sha256: isManualCorrection
      ? "sha256:manual-gap-fill-overlay"
      : "sha256:reviewed-overlay",
    items: [
      {
        effective_answer_key: {
          correct_gap_answers: [
            { "gap-001": "kretslopp" },
            { "gap-002": "näringsväv" },
          ],
          lineage: isManualCorrection
            ? null
            : {
                candidate_id: "candidate-item-013",
                review_outcome: "accepted_unchanged",
              },
          provenance: isManualCorrection ? "teacher_provided" : "reviewed",
        },
        effective_item_patch: null,
        effective_point_correction: null,
        item_id: "item-013",
        item_type: "gap_fill",
        sequence: 13,
        source_item_fingerprint: "sha256:item-013",
      },
    ],
    schema_version: DIGIEXAM_EFFECTIVE_EXAM_SCHEMA_VERSION,
    source_file_sha256: "sha256:source",
    source_ir_schema_version: DIGIEXAM_INTERMEDIATE_EXAM_SCHEMA_VERSION,
    source_ir_sha256: "sha256:ir",
  };
}

export function mockVisionBackedGapFillReviewArtifacts(
  gatewayMocks: ExamConverterGatewayMocks,
): void {
  gatewayMocks.submitDigiExamMigration.mockImplementation(
    (params: { ingestionOverlay?: unknown }) =>
      Promise.resolve(
        submittedJob(
          "succeeded",
          params.ingestionOverlay ? REVIEWED_GAP_FILL_APPLY_JOB_ID : undefined,
        ),
      ),
  );
  gatewayMocks.listDigiExamMigrationArtifacts.mockImplementation(
    ({ jobId }: { jobId: string }) => Promise.resolve(artifactManifestPayload(jobId)),
  );
  gatewayMocks.downloadDigiExamMigrationArtifact.mockImplementation(
    ({ artifactKey, jobId }: { artifactKey: string; jobId: string }) => {
      if (artifactKey === "ir_json") {
        return Promise.resolve(artifactJsonBlob("ir_json", irJsonPayload(jobId)));
      }
      if (artifactKey === "migration_manifest") {
        return Promise.resolve(
          artifactJsonBlob("migration_manifest", migrationManifestPayload(jobId)),
        );
      }
      if (artifactKey === DIGIEXAM_ARTIFACT_TARGET_READINESS_REPORT) {
        return Promise.resolve(
          artifactJsonBlob(
            DIGIEXAM_ARTIFACT_TARGET_READINESS_REPORT,
            targetReadinessReportPayload(jobId),
          ),
        );
      }
      if (artifactKey === "answer_key_completion_report") {
        return Promise.resolve(
          artifactJsonBlob("answer_key_completion_report", answerKeyCompletionReportPayload(true)),
        );
      }
      if (artifactKey === DIGIEXAM_ARTIFACT_ANSWER_KEY_REVIEW_STATE_REPORT) {
        return Promise.resolve(
          artifactJsonBlob(
            DIGIEXAM_ARTIFACT_ANSWER_KEY_REVIEW_STATE_REPORT,
            answerKeyReviewStatePayload(jobId, true),
          ),
        );
      }
      if (artifactKey === "effective_ir_json") {
        return Promise.resolve(artifactJsonBlob("effective_ir_json", effectiveIrPayload(jobId)));
      }
      return Promise.resolve(artifactJsonBlob(artifactKey, {}));
    },
  );
}

export function mockManualGapFillCorrectionArtifacts(
  gatewayMocks: ExamConverterGatewayMocks,
): void {
  gatewayMocks.submitDigiExamMigration.mockImplementation(
    (params: { ingestionOverlay?: unknown }) =>
      Promise.resolve(
        submittedJob(
          "succeeded",
          params.ingestionOverlay ? MANUAL_GAP_FILL_APPLY_JOB_ID : undefined,
        ),
      ),
  );
  gatewayMocks.listDigiExamMigrationArtifacts.mockImplementation(
    ({ jobId }: { jobId: string }) => Promise.resolve(artifactManifestPayload(jobId)),
  );
  gatewayMocks.downloadDigiExamMigrationArtifact.mockImplementation(
    ({ artifactKey, jobId }: { artifactKey: string; jobId: string }) => {
      if (artifactKey === "ir_json") {
        return Promise.resolve(artifactJsonBlob("ir_json", irJsonPayload(jobId)));
      }
      if (artifactKey === "migration_manifest") {
        return Promise.resolve(
          artifactJsonBlob("migration_manifest", migrationManifestPayload(jobId)),
        );
      }
      if (artifactKey === DIGIEXAM_ARTIFACT_TARGET_READINESS_REPORT) {
        return Promise.resolve(
          artifactJsonBlob(
            DIGIEXAM_ARTIFACT_TARGET_READINESS_REPORT,
            targetReadinessReportPayload(jobId),
          ),
        );
      }
      if (artifactKey === "answer_key_completion_report") {
        return Promise.resolve(
          artifactJsonBlob("answer_key_completion_report", answerKeyCompletionReportPayload(false)),
        );
      }
      if (artifactKey === DIGIEXAM_ARTIFACT_ANSWER_KEY_REVIEW_STATE_REPORT) {
        return Promise.resolve(
          artifactJsonBlob(
            DIGIEXAM_ARTIFACT_ANSWER_KEY_REVIEW_STATE_REPORT,
            answerKeyReviewStatePayload(jobId, false),
          ),
        );
      }
      if (artifactKey === "effective_ir_json") {
        return Promise.resolve(artifactJsonBlob("effective_ir_json", effectiveIrPayload(jobId)));
      }
      return Promise.resolve(artifactJsonBlob(artifactKey, {}));
    },
  );
}
