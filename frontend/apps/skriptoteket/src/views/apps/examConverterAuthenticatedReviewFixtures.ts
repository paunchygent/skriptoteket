/**
 * Exam Converter authenticated review test fixtures.
 *
 * Domain purpose:
 *   Provide compact Sir Convert gateway fixtures for IR-backed question review
 *   tests without burying contract payloads inside presentation assertions.
 *
 * Relationships:
 *   - Used by `ExamConverterAuthenticatedReviewSlice.spec.ts`.
 *   - Mirrors the read-only Sir Convert `ir_json` and `migration_manifest`
 *     artifacts consumed by the authenticated Exam Converter view.
 */

import { flushPromises, type VueWrapper } from "@vue/test-utils";
import type { Mock } from "vitest";

import type {
  SirConvertJobStatus,
  SirConvertSubmittedJob,
  SirConvertTerminalResult,
} from "../../api/sirConvertGateway";
import {
  DIGIEXAM_ARTIFACT_IR_JSON,
  DIGIEXAM_ARTIFACT_MANUAL_FOLLOW_UP_REPORT,
  DIGIEXAM_ARTIFACT_MIGRATION_MANIFEST,
  DIGIEXAM_ARTIFACT_TARGET_READINESS_REPORT,
  DIGIEXAM_ARTIFACT_WARNINGS_REPORT,
  DIGIEXAM_ITEM_TYPE_GAP_FILL,
  DIGIEXAM_ITEM_TYPE_MULTIPLE_RESPONSE,
  DIGIEXAM_ITEM_TYPE_OPEN_ENDED,
  DIGIEXAM_ITEM_TYPE_SINGLE_CHOICE,
  DIGIEXAM_MANUAL_FOLLOW_UP_MANUAL_ANSWER_KEY_REQUIRED,
  DIGIEXAM_MANUAL_FOLLOW_UP_MANUAL_MARKING_REQUIRED,
  DIGIEXAM_MIGRATION_ROUTE_KEY,
  DIGIEXAM_SOURCE_FORMAT,
  DIGIEXAM_TARGET_EXAMNET_PDF,
  DIGIEXAM_TARGET_NEEDS_TEACHER_ANSWER_KEY,
  DIGIEXAM_TARGET_QTI_PACKAGE,
  DIGIEXAM_TARGET_READY,
  SIR_CONVERT_ARTIFACT_AVAILABLE,
  SIR_CONVERT_BUNDLE_STATUS_PARTIAL,
} from "../../api/sirConvertGateway/contractValues";
import {
  DIGIEXAM_EFFECTIVE_EXAM_SCHEMA_VERSION,
  DIGIEXAM_INTERMEDIATE_EXAM_SCHEMA_VERSION,
  DIGIEXAM_IR_MANIFEST_SCHEMA_VERSION,
  DIGIEXAM_MIGRATION_BUNDLE_SCHEMA_VERSION,
  TARGET_READINESS_REPORT_SCHEMA_VERSION,
} from "../../api/sirConvertGateway/schemaVersions";

export type ExamConverterGatewayMocks = {
  downloadDigiExamMigrationArtifact: Mock;
  getDigiExamMigrationJob: Mock;
  getDigiExamMigrationResult: Mock;
  listDigiExamMigrationArtifacts: Mock;
  saveDigiExamMigrationArtifactToUserFiles: Mock;
  submitDigiExamMigration: Mock;
};

export function submittedJob(status: SirConvertJobStatus): SirConvertSubmittedJob {
  return {
    idempotentReplay: false,
    jobId: "job_exam_converter_review",
    requestContext: {
      correlationId: "corr_exam_converter_review",
      idempotencyKey: "idem_exam_converter_review",
      jobSpec: {} as SirConvertSubmittedJob["requestContext"]["jobSpec"],
    },
    status,
  };
}

export function terminalResult(): SirConvertTerminalResult {
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
      bundle_status: SIR_CONVERT_BUNDLE_STATUS_PARTIAL,
      manual_follow_up_required: true,
      route_key: DIGIEXAM_MIGRATION_ROUTE_KEY,
      source_sha256: null,
      target_readiness_report_artifact_key: DIGIEXAM_ARTIFACT_TARGET_READINESS_REPORT,
      warning_count: 1,
    },
    job: {
      jobId: "job_exam_converter_review",
      status: "succeeded",
    },
  };
}

function artifactJsonBlob(artifactKey: string, payload: unknown) {
  return {
    artifactKey,
    blob: {
      text: () => Promise.resolve(JSON.stringify(payload)),
    } as Blob,
    contentType: "application/json",
    filename: `${artifactKey}.json`,
  };
}

function reviewItem(overrides: Record<string, unknown> = {}) {
  return {
    answer_key: { provenance: "dxe_populated_key" },
    embedded_asset_references: [
      {
        asset_id: "item-001-asset-001",
        reference_order: 1,
        source_image_index: 0,
      },
    ],
    embedded_assets: [
      {
        asset_id: "item-001-asset-001",
        byte_length: 68,
        content_base64:
          "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII=",
        height_px: 1,
        item_sequence: 1,
        media_type: "image/png",
        sha256: "image-sha",
        source_image_index: 0,
        width_px: 1,
      },
    ],
    gaps: [
      { guid: "gap-001", validations: [] },
      { guid: "gap-002", validations: [] },
      { guid: "gap-003", validations: [] },
      { guid: "gap-004", validations: [] },
      { guid: "gap-005", validations: [] },
    ],
    item_id: "item-001",
    item_type: DIGIEXAM_ITEM_TYPE_GAP_FILL,
    max_score: 2,
    prompt_html:
      '<p><img data-image-id="0" /></p><p>Kretslopp = <span class="dxWordGap" dx-wg-id="gap-001"></span></p>',
    prompt_lines: ["Kretslopp = _____ Näringsväv = _____ Fotosyntes = _____"],
    sequence: 1,
    title: "Begrepp i ekologi",
    warnings: [],
    ...overrides,
  };
}

export function mockReviewArtifacts(gatewayMocks: ExamConverterGatewayMocks): void {
  gatewayMocks.listDigiExamMigrationArtifacts.mockResolvedValue({
    artifacts: [
      {
        artifact_key: DIGIEXAM_TARGET_EXAMNET_PDF,
        availability: SIR_CONVERT_ARTIFACT_AVAILABLE,
        content_type: "application/pdf",
        filename: "Ma1c_Exam.net.pdf",
        sha256: null,
        size_bytes: 700_416,
      },
      {
        artifact_key: DIGIEXAM_TARGET_QTI_PACKAGE,
        availability: SIR_CONVERT_ARTIFACT_AVAILABLE,
        content_type: "application/zip",
        filename: "Ma1c_QTI.zip",
        sha256: null,
        size_bytes: 1_258_291,
      },
      {
        artifact_key: DIGIEXAM_ARTIFACT_MANUAL_FOLLOW_UP_REPORT,
        availability: SIR_CONVERT_ARTIFACT_AVAILABLE,
        content_type: "application/json",
        filename: "rapport.json",
        sha256: null,
        size_bytes: 2_048,
      },
    ],
    bundle_status: SIR_CONVERT_BUNDLE_STATUS_PARTIAL,
    job_id: "job_exam_converter_review",
    source: {
      filename: "Ma1c_NationelltProv_HT25.dxe",
      format: DIGIEXAM_SOURCE_FORMAT,
      sha256: "sha256:source",
    },
    manual_follow_up: {
      artifact_key: DIGIEXAM_ARTIFACT_MANUAL_FOLLOW_UP_REPORT,
      count: 2,
      required: true,
    },
    schema_version: DIGIEXAM_MIGRATION_BUNDLE_SCHEMA_VERSION,
    warnings: {
      artifact_key: DIGIEXAM_ARTIFACT_WARNINGS_REPORT,
      count: 1,
    },
    readiness: {
      artifact_key: DIGIEXAM_ARTIFACT_TARGET_READINESS_REPORT,
      exportable_targets: [],
      review_required: true,
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
              reviewItem(),
              reviewItem({
                answer_key: { provenance: "absent" },
                alternatives: [
                  { about: "", id: 1, right: false, title: "Växter tar upp vatten ur marken." },
                  {
                    about: "",
                    id: 2,
                    right: false,
                    title: "Växter omvandlar solljus till socker.",
                  },
                  {
                    about: "",
                    id: 3,
                    right: false,
                    title: "Djur och växter frigör energi ur socker med hjälp av syre.",
                  },
                  { about: "", id: 4, right: false, title: "Växter släpper ut syre." },
                ],
                embedded_asset_references: [],
                embedded_assets: [],
                gaps: [],
                item_id: "item-004",
                item_type: DIGIEXAM_ITEM_TYPE_SINGLE_CHOICE,
                max_score: 1,
                prompt_lines: ["Vilket av följande påståenden beskriver cellandning bäst?"],
                sequence: 4,
                title: "Fråga 4",
              }),
              reviewItem({
                answer_key: { provenance: "dxe_populated_key" },
                embedded_asset_references: [],
                embedded_assets: [],
                gaps: [],
                item_id: "item-005",
                item_type: DIGIEXAM_ITEM_TYPE_MULTIPLE_RESPONSE,
                max_score: 2,
                options: ["Producent", "Konsument", "Nedbrytare"],
                prompt_lines: ["Vilka roller kan ingå i ett ekosystem?"],
                sequence: 5,
                title: "Fråga 5",
              }),
              reviewItem({
                answer_key: { provenance: "not_applicable" },
                embedded_asset_references: [],
                embedded_assets: [],
                gaps: [],
                item_id: "item-006",
                item_type: DIGIEXAM_ITEM_TYPE_OPEN_ENDED,
                max_score: 2,
                prompt_lines: ["Beskriv hur producent och nedbrytare samspelar."],
                sequence: 6,
                title: "Fråga 6",
              }),
              reviewItem({
                answer_key: { provenance: "not_applicable" },
                embedded_asset_references: [],
                embedded_assets: [],
                gaps: [],
                item_id: "item-012",
                item_type: DIGIEXAM_ITEM_TYPE_OPEN_ENDED,
                max_score: null,
                prompt_lines: ["Resonera om lösningsmetod."],
                sequence: 12,
                title: "Resonera om lösningsmetod",
              }),
              reviewItem({
                answer_key: { provenance: "not_applicable" },
                embedded_asset_references: [],
                embedded_assets: [],
                gaps: [],
                item_id: "item-013",
                item_type: DIGIEXAM_ITEM_TYPE_OPEN_ENDED,
                max_score: 1,
                prompt_lines: ["Förklara varför stål är hårdare än järn."],
                sequence: 13,
                title: "Fråga 13",
              }),
            ],
            manual_follow_ups: [
              {
                item_id: "item-004",
                message: "Manual answer key is required.",
                reason: DIGIEXAM_MANUAL_FOLLOW_UP_MANUAL_ANSWER_KEY_REQUIRED,
                source_span: null,
              },
              {
                item_id: "item-012",
                message: "Manual marking is required.",
                reason: DIGIEXAM_MANUAL_FOLLOW_UP_MANUAL_MARKING_REQUIRED,
                source_span: null,
              },
              {
                item_id: "item-013",
                message: "Manual marking is required.",
                reason: DIGIEXAM_MANUAL_FOLLOW_UP_MANUAL_MARKING_REQUIRED,
                source_span: null,
              },
            ],
            parse_status: "success",
            renderer_ready: true,
            schema_version: DIGIEXAM_INTERMEDIATE_EXAM_SCHEMA_VERSION,
            source_filename: "Ma1c_NationelltProv_HT25.dxe",
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
                readiness: DIGIEXAM_TARGET_NEEDS_TEACHER_ANSWER_KEY,
                export_enabled: false,
                artifact_key: null,
                reason_code: DIGIEXAM_MANUAL_FOLLOW_UP_MANUAL_ANSWER_KEY_REQUIRED,
                teacher_action: "supply_answer_key_overlay",
                retryable: false,
                message_key: "exam_converter.target.needs_teacher_answer_key",
                item_id: "item-004",
                sequence: 4,
                source_item_fingerprint: "sha256:item-004",
              },
              {
                target: DIGIEXAM_TARGET_QTI_PACKAGE,
                readiness: DIGIEXAM_TARGET_NEEDS_TEACHER_ANSWER_KEY,
                export_enabled: false,
                artifact_key: null,
                reason_code: DIGIEXAM_MANUAL_FOLLOW_UP_MANUAL_ANSWER_KEY_REQUIRED,
                teacher_action: "supply_answer_key_overlay",
                retryable: false,
                message_key: "exam_converter.target.needs_teacher_answer_key",
                item_id: "item-004",
                sequence: 4,
                source_item_fingerprint: "sha256:item-004",
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
          item_count: 6,
          item_summaries: [
            {
              item_id: "item-001",
              sequence: 1,
              title: "Begrepp i ekologi",
              item_type: DIGIEXAM_ITEM_TYPE_GAP_FILL,
              source_item_fingerprint: "sha256:item-001",
              answer_key_provenance: "dxe_populated_key",
              manual_follow_up_required: false,
              asset_summaries: [],
            },
            {
              item_id: "item-004",
              sequence: 4,
              title: "Fråga 4",
              item_type: DIGIEXAM_ITEM_TYPE_SINGLE_CHOICE,
              source_item_fingerprint: "sha256:item-004",
              answer_key_provenance: "absent",
              manual_follow_up_required: true,
              asset_summaries: [],
            },
            {
              item_id: "item-005",
              sequence: 5,
              title: "Fråga 5",
              item_type: DIGIEXAM_ITEM_TYPE_MULTIPLE_RESPONSE,
              source_item_fingerprint: "sha256:item-005",
              answer_key_provenance: "dxe_populated_key",
              manual_follow_up_required: false,
              asset_summaries: [],
            },
            {
              item_id: "item-006",
              sequence: 6,
              title: "Fråga 6",
              item_type: DIGIEXAM_ITEM_TYPE_OPEN_ENDED,
              source_item_fingerprint: "sha256:item-006",
              answer_key_provenance: "not_applicable",
              manual_follow_up_required: false,
              asset_summaries: [],
            },
            {
              item_id: "item-012",
              sequence: 12,
              title: "Resonera om lösningsmetod",
              item_type: DIGIEXAM_ITEM_TYPE_OPEN_ENDED,
              source_item_fingerprint: "sha256:item-012",
              answer_key_provenance: "not_applicable",
              manual_follow_up_required: true,
              asset_summaries: [],
            },
            {
              item_id: "item-013",
              sequence: 13,
              title: "Fråga 13",
              item_type: DIGIEXAM_ITEM_TYPE_OPEN_ENDED,
              source_item_fingerprint: "sha256:item-013",
              answer_key_provenance: "not_applicable",
              manual_follow_up_required: true,
              asset_summaries: [],
            },
          ],
          manual_follow_up_count: 3,
          parse_status: "success",
          renderer_ready: true,
          schema_version: DIGIEXAM_IR_MANIFEST_SCHEMA_VERSION,
          source_filename: "Ma1c_NationelltProv_HT25.dxe",
          source_producer: null,
          warning_count: 1,
        }),
      );
    },
  );
}

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

async function chooseSourceFile(wrapper: VueWrapper): Promise<void> {
  const input = wrapper.find<HTMLInputElement>(
    '[data-test="exam-converter-source-file-input"]',
  );
  Object.defineProperty(input.element, "files", {
    configurable: true,
    value: [
      new File(["exam"], "Ma1c_NationelltProv_HT25.dxe", {
        type: "application/octet-stream",
      }),
    ],
  });
  await input.trigger("change");
}

export async function finishConversion(wrapper: VueWrapper): Promise<void> {
  await chooseSourceFile(wrapper);
  await wrapper.find('[data-test="exam-converter-start-conversion"]').trigger("click");
  await flushPromises();
}
