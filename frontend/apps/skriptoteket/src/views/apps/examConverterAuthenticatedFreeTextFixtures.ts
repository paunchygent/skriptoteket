/**
 * Exam Converter authenticated free-text review fixtures.
 *
 * Domain purpose:
 *   Provide the free-text-only Sir Convert fixture used to prove AI-facit
 *   review stays quiet when automatic answer keys are not needed.
 *
 * Relationships:
 *   - Complements `examConverterAuthenticatedReviewFixtures.ts`.
 *   - Used by authenticated Exam Converter review slice tests.
 */

import type { ExamConverterGatewayMocks } from "./examConverterAuthenticatedReviewFixtures";
import {
  artifactJsonBlob,
  reviewItem,
} from "./examConverterAuthenticatedReviewFixtures";
import {
  DIGIEXAM_ARTIFACT_ANSWER_KEY_COMPLETION_REPORT,
  DIGIEXAM_ARTIFACT_IR_JSON,
  DIGIEXAM_ARTIFACT_MANUAL_FOLLOW_UP_REPORT,
  DIGIEXAM_ARTIFACT_MIGRATION_MANIFEST,
  DIGIEXAM_ARTIFACT_TARGET_READINESS_REPORT,
  DIGIEXAM_ARTIFACT_WARNINGS_REPORT,
  DIGIEXAM_ITEM_TYPE_OPEN_ENDED,
  DIGIEXAM_MANUAL_FOLLOW_UP_MANUAL_MARKING_REQUIRED,
  DIGIEXAM_SOURCE_FORMAT,
  DIGIEXAM_TARGET_EXAMNET_PDF,
  DIGIEXAM_TARGET_QTI_PACKAGE,
  DIGIEXAM_TARGET_READY,
  SIR_CONVERT_ARTIFACT_AVAILABLE,
  SIR_CONVERT_BUNDLE_STATUS_PARTIAL,
} from "../../api/sirConvertGateway/contractValues";
import {
  ANSWER_KEY_COMPLETION_REPORT_SCHEMA_VERSION,
  DIGIEXAM_EFFECTIVE_EXAM_SCHEMA_VERSION,
  DIGIEXAM_INTERMEDIATE_EXAM_SCHEMA_VERSION,
  DIGIEXAM_IR_MANIFEST_SCHEMA_VERSION,
  DIGIEXAM_MIGRATION_BUNDLE_SCHEMA_VERSION,
  TARGET_READINESS_REPORT_SCHEMA_VERSION,
} from "../../api/sirConvertGateway/schemaVersions";

export function mockFreeTextOnlyReviewArtifacts(
  gatewayMocks: ExamConverterGatewayMocks,
): void {
  gatewayMocks.listDigiExamMigrationArtifacts.mockResolvedValue({
    artifacts: [
      {
        artifact_key: DIGIEXAM_TARGET_EXAMNET_PDF,
        availability: SIR_CONVERT_ARTIFACT_AVAILABLE,
        content_type: "application/pdf",
        filename: "Metaller_Exam.net.pdf",
        sha256: null,
        size_bytes: 700_416,
      },
      {
        artifact_key: DIGIEXAM_TARGET_QTI_PACKAGE,
        availability: SIR_CONVERT_ARTIFACT_AVAILABLE,
        content_type: "application/zip",
        filename: "Metaller_QTI.zip",
        sha256: null,
        size_bytes: 1_258_291,
      },
      {
        artifact_key: DIGIEXAM_ARTIFACT_ANSWER_KEY_COMPLETION_REPORT,
        availability: SIR_CONVERT_ARTIFACT_AVAILABLE,
        content_type: "application/json",
        filename: "answer-key-completion-report.json",
        sha256: "sha256:completion-report-free-text",
        size_bytes: 512,
      },
    ],
    bundle_status: SIR_CONVERT_BUNDLE_STATUS_PARTIAL,
    job_id: "job_exam_converter_review",
    source: {
      filename: "1819077059-e-metaller-och-elektrokemi-23c.dxe",
      format: DIGIEXAM_SOURCE_FORMAT,
      sha256: "sha256:source",
    },
    manual_follow_up: {
      artifact_key: DIGIEXAM_ARTIFACT_MANUAL_FOLLOW_UP_REPORT,
      count: 1,
      required: true,
    },
    schema_version: DIGIEXAM_MIGRATION_BUNDLE_SCHEMA_VERSION,
    warnings: {
      artifact_key: DIGIEXAM_ARTIFACT_WARNINGS_REPORT,
      count: 0,
    },
    readiness: {
      artifact_key: DIGIEXAM_ARTIFACT_TARGET_READINESS_REPORT,
      exportable_targets: [DIGIEXAM_TARGET_EXAMNET_PDF, DIGIEXAM_TARGET_QTI_PACKAGE],
      review_required: false,
    },
    source_binding: {
      source_ir_schema_version: DIGIEXAM_INTERMEDIATE_EXAM_SCHEMA_VERSION,
      source_ir_sha256: "sha256:ir",
      effective_exam_schema_version: DIGIEXAM_EFFECTIVE_EXAM_SCHEMA_VERSION,
      effective_exam_sha256: "sha256:effective",
    },
  });
  gatewayMocks.downloadDigiExamMigrationArtifact.mockImplementation(
    ({ artifactKey }: { artifactKey: string }) => {
      if (artifactKey === DIGIEXAM_ARTIFACT_IR_JSON) {
        return Promise.resolve(
          artifactJsonBlob(DIGIEXAM_ARTIFACT_IR_JSON, {
            items: [
              reviewItem({
                answer_key: { provenance: "not_applicable" },
                embedded_asset_references: [],
                embedded_assets: [],
                gaps: [],
                item_id: "item-001",
                item_type: DIGIEXAM_ITEM_TYPE_OPEN_ENDED,
                max_score: 1,
                prompt_lines: ["Varför är stål hårdare och starkare än järn?"],
                sequence: 1,
                title: "Fråga 1",
              }),
            ],
            manual_follow_ups: [
              {
                item_id: "item-001",
                message: "Manual marking is required.",
                reason: DIGIEXAM_MANUAL_FOLLOW_UP_MANUAL_MARKING_REQUIRED,
                source_span: null,
              },
            ],
            parse_status: "success",
            renderer_ready: true,
            schema_version: DIGIEXAM_INTERMEDIATE_EXAM_SCHEMA_VERSION,
            source_filename: "1819077059-e-metaller-och-elektrokemi-23c.dxe",
            source_producer: null,
            warnings: [],
          }),
        );
      }
      if (artifactKey === DIGIEXAM_ARTIFACT_TARGET_READINESS_REPORT) {
        return Promise.resolve(
          artifactJsonBlob(DIGIEXAM_ARTIFACT_TARGET_READINESS_REPORT, {
            schema_version: TARGET_READINESS_REPORT_SCHEMA_VERSION,
            job_id: "job_exam_converter_review",
            source_ir_sha256: "sha256:ir",
            effective_exam_sha256: "sha256:effective",
            targets: [
              {
                target: DIGIEXAM_TARGET_EXAMNET_PDF,
                readiness: DIGIEXAM_TARGET_READY,
                export_enabled: true,
                artifact_key: DIGIEXAM_TARGET_EXAMNET_PDF,
                reason_code: "target_available",
                teacher_action: "none",
                retryable: false,
                message_key: "exam_converter.target.ready",
                item_id: null,
                sequence: null,
                source_item_fingerprint: null,
              },
              {
                target: DIGIEXAM_TARGET_QTI_PACKAGE,
                readiness: DIGIEXAM_TARGET_READY,
                export_enabled: true,
                artifact_key: DIGIEXAM_TARGET_QTI_PACKAGE,
                reason_code: "target_available",
                teacher_action: "none",
                retryable: false,
                message_key: "exam_converter.target.ready",
                item_id: null,
                sequence: null,
                source_item_fingerprint: null,
              },
            ],
          }),
        );
      }
      if (artifactKey === DIGIEXAM_ARTIFACT_ANSWER_KEY_COMPLETION_REPORT) {
        return Promise.resolve(
          artifactJsonBlob(DIGIEXAM_ARTIFACT_ANSWER_KEY_COMPLETION_REPORT, {
            schema_version: ANSWER_KEY_COMPLETION_REPORT_SCHEMA_VERSION,
            completion_mode: "local_llm_suggest_missing_machine_marked",
            job_id: "job_exam_converter_review",
            items: [
              {
                item_id: "item-001",
                sequence: 1,
                item_type: DIGIEXAM_ITEM_TYPE_OPEN_ENDED,
                decision_state: "manual_follow_up_required",
                validation_state: "manual_follow_up_required",
                backend_status: "skipped",
                backend_failure_code: null,
                candidate_id: null,
                candidate_payload_digest: null,
                provider_profile_id: null,
                model_profile: null,
                prompt_template_version: null,
                schema_name: null,
                schema_version: null,
                answer_payload: null,
              },
            ],
          }),
        );
      }
      return Promise.resolve(
        artifactJsonBlob(DIGIEXAM_ARTIFACT_MIGRATION_MANIFEST, {
          asset_count: 0,
          asset_summaries: [],
          exam_schema_version: DIGIEXAM_INTERMEDIATE_EXAM_SCHEMA_VERSION,
          item_count: 1,
          item_summaries: [
            {
              item_id: "item-001",
              sequence: 1,
              title: "Fråga 1",
              item_type: DIGIEXAM_ITEM_TYPE_OPEN_ENDED,
              source_item_fingerprint: "sha256:item-001",
              answer_key_provenance: "not_applicable",
              manual_follow_up_required: true,
              asset_summaries: [],
            },
          ],
          manual_follow_up_count: 1,
          parse_status: "success",
          renderer_ready: true,
          schema_version: DIGIEXAM_IR_MANIFEST_SCHEMA_VERSION,
          source_filename: "1819077059-e-metaller-och-elektrokemi-23c.dxe",
          source_producer: null,
          warning_count: 0,
        }),
      );
    },
  );
}
