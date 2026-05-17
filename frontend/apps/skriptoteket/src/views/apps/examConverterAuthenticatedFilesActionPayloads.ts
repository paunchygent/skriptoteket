/**
 * Exam Converter file-action test payload helpers.
 *
 * Domain purpose:
 *   Keep authenticated file-action specs focused by isolating the Sir Convert
 *   job, artifact, and readiness payloads used by accepted-current-state tests.
 *
 * Relationships:
 *   - Used by `ExamConverterAuthenticatedFilesActionSlice.spec.ts`.
 *   - Mirrors the Gateway result shapes consumed by the authenticated view.
 */

import type {
  SirConvertJobStatus,
  SirConvertSubmittedJob,
  SirConvertTerminalResult,
} from "../../api/sirConvertGateway";
import {
  DIGIEXAM_IR_MANIFEST_SCHEMA_VERSION,
  DIGIEXAM_MIGRATION_BUNDLE_SCHEMA_VERSION,
  TARGET_READINESS_REPORT_SCHEMA_VERSION,
} from "../../api/sirConvertGateway/schemaVersions";

export function submittedFilesJob(status: SirConvertJobStatus): SirConvertSubmittedJob {
  return {
    idempotentReplay: false,
    jobId: "job_exam_converter_files",
    requestContext: {
      correlationId: "corr_exam_converter_files",
      idempotencyKey: "idem_exam_converter_files",
      jobSpec: {} as SirConvertSubmittedJob["requestContext"]["jobSpec"],
    },
    status,
  };
}

export function filesTerminalResult(): SirConvertTerminalResult {
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

export function targetReadinessReportPayload(acceptedOverlaySubmitted: boolean) {
  const base = {
    schema_version: TARGET_READINESS_REPORT_SCHEMA_VERSION,
    job_id: "job_exam_converter_files",
    source_ir_sha256: "sha256:ir",
    effective_exam_sha256: "sha256:effective",
  };
  if (acceptedOverlaySubmitted) {
    return {
      ...base,
      targets: [
        {
          target: "examnet_pdf",
          readiness: "unsupported_target_shape",
          export_enabled: false,
          artifact_key: null,
          reason_code: "accepted_current_state_not_renderable",
          teacher_action: "manual_target_creation_required",
          retryable: false,
          message_key: "exam_converter.target.accepted_current_state_not_renderable",
          item_id: "item-001",
          sequence: 1,
          source_item_fingerprint: "sha256:item-001",
        },
        {
          target: "qti_package",
          readiness: "ready_after_accepted_current_state",
          export_enabled: true,
          artifact_key: "qti_package",
          reason_code: "accepted_current_state_manual_unkeyed_profile",
          teacher_action: "review_after_import",
          retryable: false,
          message_key: "exam_converter.target.ready_after_accepted_current_state",
          item_id: "item-001",
          sequence: 1,
          source_item_fingerprint: "sha256:item-001",
        },
      ],
    };
  }
  return {
    ...base,
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
