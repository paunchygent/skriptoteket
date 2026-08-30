/**
 * Exam Converter file-action test payload helpers.
 *
 * Domain purpose:
 *   Keep authenticated file-action specs focused by isolating the Exam Converter
 *   job, artifact, and readiness payloads used by corrected-download tests.
 *
 * Relationships:
 *   - Used by `ExamConverterAuthenticatedFilesActionSlice.spec.ts`.
 *   - Mirrors the Gateway result shapes consumed by the authenticated view.
 */

import type {
  ExamConverterJobStatus,
  ExamConverterTerminalResult,
} from "../../api/examConverterContracts";
import {
  ANSWER_KEY_REVIEW_STATE_SCHEMA_VERSION,
  DIGIEXAM_IR_MANIFEST_SCHEMA_VERSION,
  DIGIEXAM_MIGRATION_BUNDLE_SCHEMA_VERSION,
  TARGET_READINESS_REPORT_SCHEMA_VERSION,
} from "../../api/examConverterContracts";

export function submittedFilesJob(status: ExamConverterJobStatus) {
  return {
    correlationId: "corr_exam_converter_files",
    idempotencyKey: "idem_exam_converter_files",
    idempotentReplay: false,
    jobId: "job_exam_converter_files",
    status,
  };
}

export function filesTerminalResult(): ExamConverterTerminalResult {
  return {
    artifact: {
      content_type: "application/json",
      filename: "exam-converter-result.json",
      sha256: null,
      size_bytes: 1024,
    },
    conversion_metadata: {
      artifact_count: 2,
      bundle_schema_version: DIGIEXAM_MIGRATION_BUNDLE_SCHEMA_VERSION,
      bundle_status: "partial",
      manual_follow_up_required: true,
      route_key: "digiexam_dxe_to_examnet_migration_bundle",
      source_sha256: null,
      target_readiness_report_artifact_key: "target_readiness_report",
      warning_count: 0,
    },
    job: {
      jobId: "job_exam_converter_files",
      status: "succeeded",
    },
  };
}

export function artifactJsonBlob(artifactKey: string, payload: unknown) {
  return {
    artifactKey,
    blob: {
      text: () => Promise.resolve(JSON.stringify(payload)),
    } as Blob,
    contentType: "application/json",
    filename: `${artifactKey}.json`,
  };
}

export function fileArtifactBlob(artifactKey: string, filename: string, contentType: string) {
  return {
    artifactKey,
    blob: new Blob(["file"], { type: contentType }),
    contentType,
    filename,
  };
}

export function targetReadinessReportPayload() {
  return {
    schema_version: TARGET_READINESS_REPORT_SCHEMA_VERSION,
    job_id: "job_exam_converter_files",
    source_ir_sha256: "sha256:ir",
    effective_exam_sha256: "sha256:effective",
    targets: [
      {
        target: "examnet_pdf",
        readiness: "needs_teacher_answer_key",
        export_enabled: false,
        artifact_key: null,
        reason_code: "manual_answer_key_required",
        teacher_action: "supply_answer_key_overlay",
        retryable: false,
        message_key: "exam_converter.target.needs_teacher_answer_key",
        item_id: "item-001",
        sequence: 1,
        source_item_fingerprint: "sha256:item-001",
      },
      {
        target: "qti_package",
        readiness: "needs_teacher_answer_key",
        export_enabled: false,
        artifact_key: null,
        reason_code: "manual_answer_key_required",
        teacher_action: "supply_answer_key_overlay",
        retryable: false,
        message_key: "exam_converter.target.needs_teacher_answer_key",
        item_id: "item-001",
        sequence: 1,
        source_item_fingerprint: "sha256:item-001",
      },
    ],
  };
}

export function answerKeyReviewStateReportPayload() {
  return {
    schema_version: ANSWER_KEY_REVIEW_STATE_SCHEMA_VERSION,
    items: [
      {
        choice_ids: [],
        choice_interaction_ids: ["choice-item-001"],
        correction_affordances: ["manual_choice_answer_key"],
        current_key_origin: "none",
        gap_ids: [],
        gap_interaction_ids: [],
        item_id: "item-001",
        item_type: "multiple_choice",
        message_key: "exam_converter.answer_key.manual_required",
        provenance_detail: null,
        reasons: ["manual_answer_key_required"],
        replay_artifact_references: [],
        review_state: "validation_required",
        sequence: 1,
        source_item_fingerprint: "sha256:item-001",
      },
    ],
  };
}

export const singleMissingChoiceManifest = {
  asset_count: 0,
  asset_summaries: [],
  exam_schema_version: "digiexam_intermediate_exam_v3",
  item_count: 1,
  item_summaries: [
    {
      item_id: "item-001",
      sequence: 1,
      title: "Vilket av följande tal är ett primtal?",
      item_type: "multiple_choice",
      source_item_fingerprint: "sha256:item-001",
      answer_key_provenance: "absent",
      manual_follow_up_required: true,
      asset_summaries: [],
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
