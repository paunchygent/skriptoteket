/**
 * Exam Converter review decision and file-action behavior.
 *
 * Slice purpose:
 *   Let the teacher either review missing question data or approve the current
 *   conversion state before downloading or saving generated files.
 *
 * Expected behavior:
 *   File actions stay disabled until Sir Convert's target-readiness report
 *   marks a generated target exportable. `Godkänn` submits a source-bound
 *   accepted-current-state overlay, then the refreshed producer report decides
 *   which targets can be downloaded or saved.
 *
 * Recommended implementation shape:
 *   Keep file rows inside `Filer`, construct the accepted-current-state
 *   overlay from source binding and item fingerprints, and use the existing
 *   Gateway submit/download plus owner-scoped user-file save clients.
 */

import { flushPromises, mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import ExamConverterAuthenticatedView from "./ExamConverterAuthenticatedView.vue";
import type {
  SirConvertJobStatus,
  SirConvertSubmittedJob,
  SirConvertTerminalResult,
} from "../../api/sirConvertGateway";
import {
  DIGIEXAM_INTERMEDIATE_EXAM_SCHEMA_VERSION,
  DIGIEXAM_IR_MANIFEST_SCHEMA_VERSION,
  DIGIEXAM_MIGRATION_BUNDLE_SCHEMA_VERSION,
} from "../../api/sirConvertGateway/schemaVersions";

const gatewayMocks = vi.hoisted(() => ({
  downloadDigiExamMigrationArtifact: vi.fn(),
  getDigiExamMigrationJob: vi.fn(),
  getDigiExamMigrationResult: vi.fn(),
  listDigiExamMigrationArtifacts: vi.fn(),
  saveDigiExamMigrationArtifactToUserFiles: vi.fn(),
  submitDigiExamMigration: vi.fn(),
}));

vi.mock("../../api/sirConvertGateway", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../../api/sirConvertGateway")>();
  return {
    ...actual,
    downloadDigiExamMigrationArtifact: gatewayMocks.downloadDigiExamMigrationArtifact,
    getDigiExamMigrationJob: gatewayMocks.getDigiExamMigrationJob,
    getDigiExamMigrationResult: gatewayMocks.getDigiExamMigrationResult,
    listDigiExamMigrationArtifacts: gatewayMocks.listDigiExamMigrationArtifacts,
    saveDigiExamMigrationArtifactToUserFiles:
      gatewayMocks.saveDigiExamMigrationArtifactToUserFiles,
    submitDigiExamMigration: gatewayMocks.submitDigiExamMigration,
  };
});

function submittedJob(status: SirConvertJobStatus): SirConvertSubmittedJob {
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

function terminalResult(): SirConvertTerminalResult {
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
      target_availability: {
        examnet_pdf: "unavailable",
        qti_package: "unavailable",
      },
      warning_count: 0,
    },
    job: {
      jobId: "job_exam_converter_files",
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

function fileArtifactBlob(artifactKey: string, filename: string, contentType: string) {
  return {
    artifactKey,
    blob: new Blob(["file"], { type: contentType }),
    contentType,
    filename,
  };
}

let acceptedOverlaySubmitted = false;

function targetReadinessReportPayload() {
  if (acceptedOverlaySubmitted) {
    return {
      schema_version: "target_readiness_report_v1",
      job_id: "job_exam_converter_files",
      source_ir_sha256: "sha256:ir",
      effective_exam_sha256: "sha256:effective",
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
    schema_version: "target_readiness_report_v1",
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

function mockReviewArtifacts(): void {
  gatewayMocks.listDigiExamMigrationArtifacts.mockResolvedValue({
    artifacts: [
      {
        artifact_key: "examnet_pdf",
        availability: acceptedOverlaySubmitted ? "unavailable" : "unavailable",
        content_type: "application/pdf",
        filename: "Ma1c_Exam.net.pdf",
        unavailable_code: acceptedOverlaySubmitted
          ? "accepted_current_state_not_renderable"
          : "manual_answer_key_required",
        sha256: null,
        size_bytes: null,
      },
      {
        artifact_key: "qti_package",
        availability: acceptedOverlaySubmitted ? "available" : "unavailable",
        content_type: "application/zip",
        filename: "Ma1c_QTI.zip",
        unavailable_code: acceptedOverlaySubmitted ? undefined : "manual_answer_key_required",
        sha256: null,
        size_bytes: acceptedOverlaySubmitted ? 4 : null,
      },
    ],
    bundle_status: "needs_review",
    job_id: "job_exam_converter_files",
    source: {
      filename: "Ma1c_NationelltProv_HT25.dxe",
      format: "digiexam_dxe",
      sha256: "sha256:source",
    },
    manual_follow_up: {
      artifact_key: "manual_follow_up_report",
      count: 1,
      required: true,
    },
    schema_version: DIGIEXAM_MIGRATION_BUNDLE_SCHEMA_VERSION,
    warnings: {
      artifact_key: "warnings_report",
      count: 0,
    },
    readiness: {
      artifact_key: "target_readiness_report",
      exportable_targets: acceptedOverlaySubmitted ? ["qti_package"] : [],
      review_required: !acceptedOverlaySubmitted,
    },
    source_binding: {
      source_ir_schema_version: DIGIEXAM_INTERMEDIATE_EXAM_SCHEMA_VERSION,
      source_ir_sha256: "sha256:ir",
      effective_exam_schema_version: "digiexam_effective_exam_v2",
      effective_exam_sha256: "sha256:effective",
    },
  });
  gatewayMocks.downloadDigiExamMigrationArtifact.mockImplementation(
    ({ artifactKey }: { artifactKey: string }) => {
      if (artifactKey === "ir_json") {
        return Promise.resolve(
          artifactJsonBlob("ir_json", {
            items: [
              {
                answer_key: { provenance: "absent" },
                item_id: "item-001",
                item_type: "multiple_choice",
                max_score: 1,
                alternatives: [
                  { id: 1, title: "21", about: "" },
                  { id: 2, title: "37", about: "" },
                ],
                prompt_html: null,
                prompt_lines: ["Vilket av följande tal är ett primtal?"],
                sequence: 1,
                title: "Vilket av följande tal är ett primtal?",
                warnings: [],
              },
            ],
            manual_follow_ups: [
              {
                item_id: "item-001",
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
          }),
        );
      }
      if (artifactKey === "migration_manifest") {
        return Promise.resolve(
          artifactJsonBlob("migration_manifest", {
            asset_count: 0,
            asset_summaries: [],
            exam_schema_version: DIGIEXAM_INTERMEDIATE_EXAM_SCHEMA_VERSION,
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
          }),
        );
      }
      if (artifactKey === "target_readiness_report") {
        return Promise.resolve(
          artifactJsonBlob("target_readiness_report", targetReadinessReportPayload()),
        );
      }
      return Promise.resolve(
        fileArtifactBlob(
          artifactKey,
          artifactKey === "examnet_pdf" ? "Ma1c_Exam.net.pdf" : "Ma1c_QTI.zip",
          artifactKey === "examnet_pdf" ? "application/pdf" : "application/zip",
        ),
      );
    },
  );
  gatewayMocks.saveDigiExamMigrationArtifactToUserFiles.mockResolvedValue({
    source_artifact_id: "documents.conversion_hub:job_exam_converter_files:qti_package",
    vault_artifact: {
      bytes: 4,
      created_at: "2026-05-14T10:00:00Z",
      file_id: "vault-file-1",
      name: "Ma1c_QTI.zip",
    },
  });
}

async function chooseSourceFile(wrapper: ReturnType<typeof mount>) {
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

async function finishConversion(wrapper: ReturnType<typeof mount>) {
  await chooseSourceFile(wrapper);
  await wrapper.find('[data-test="exam-converter-start-conversion"]').trigger("click");
  await flushPromises();
}

beforeEach(() => {
  acceptedOverlaySubmitted = false;
  gatewayMocks.downloadDigiExamMigrationArtifact.mockReset();
  gatewayMocks.getDigiExamMigrationJob.mockReset();
  gatewayMocks.getDigiExamMigrationResult.mockReset();
  gatewayMocks.listDigiExamMigrationArtifacts.mockReset();
  gatewayMocks.saveDigiExamMigrationArtifactToUserFiles.mockReset();
  gatewayMocks.submitDigiExamMigration.mockReset();
  gatewayMocks.submitDigiExamMigration.mockImplementation((params: { ingestionOverlay?: unknown }) => {
    acceptedOverlaySubmitted = Boolean(params.ingestionOverlay);
    mockReviewArtifacts();
    return Promise.resolve(submittedJob("succeeded"));
  });
  gatewayMocks.getDigiExamMigrationResult.mockResolvedValue(terminalResult());
  mockReviewArtifacts();
});

describe("ExamConverterAuthenticatedView review decision and file actions", () => {
  it("uses short decision buttons and keeps explanations in help affordances", async () => {
    const wrapper = mount(ExamConverterAuthenticatedView);

    await finishConversion(wrapper);

    const gate = wrapper.find('[data-test="exam-converter-review-decision-gate"]');
    const review = wrapper.find('[data-test="exam-converter-review-questions-action"]');
    const accept = wrapper.find('[data-test="exam-converter-accept-current-state-action"]');

    expect(gate.exists()).toBe(true);
    expect(review.text()).toBe("Granska");
    expect(accept.text()).toBe("Godkänn");
    expect(review.attributes("title")).toBe(
      "Granska och redigera frågorna som saknar facit eller poäng.",
    );
    expect(accept.attributes("title")).toBe(
      "Hoppa över granskningen och exportera provet direkt.",
    );
    expect(wrapper.text()).not.toContain(
      "Granska och redigera frågorna som saknar facit eller poäng.",
    );
    expect(wrapper.text()).not.toContain(
      "Hoppa över granskningen och exportera provet direkt.",
    );
    expect(wrapper.text()).not.toContain("Använd provet som det är");
  });

  it("blocks generated file actions until the teacher approves the current state", async () => {
    const wrapper = mount(ExamConverterAuthenticatedView);

    await finishConversion(wrapper);
    await wrapper.find('[data-test="exam-converter-inspection-tab-files"]').trigger("click");

    const downloadBefore = wrapper.find(
      '[data-test="exam-converter-download-file-examnet_pdf"]',
    );
    const saveBefore = wrapper.find('[data-test="exam-converter-save-file-examnet_pdf"]');
    expect(downloadBefore.attributes("disabled")).toBeDefined();
    expect(saveBefore.attributes("disabled")).toBeDefined();
    expect(wrapper.text()).toContain("Granska eller godkänn först");

    await wrapper.find('[data-test="exam-converter-accept-current-state-action"]').trigger("click");
    await flushPromises();

    const pdfDownloadAfter = wrapper.find(
      '[data-test="exam-converter-download-file-examnet_pdf"]',
    );
    const qtiDownloadAfter = wrapper.find(
      '[data-test="exam-converter-download-file-qti_package"]',
    );
    const qtiSaveAfter = wrapper.find('[data-test="exam-converter-save-file-qti_package"]');
    expect(
      wrapper.find('[data-test="exam-converter-review-decision-gate"]').exists(),
    ).toBe(false);
    expect(wrapper.text()).toContain("Godkänt för export");
    expect(pdfDownloadAfter.attributes("disabled")).toBeDefined();
    expect(qtiDownloadAfter.attributes("disabled")).toBeUndefined();
    expect(qtiSaveAfter.attributes("disabled")).toBeUndefined();
  });

  it("saves an approved generated file through the owner-scoped user-file client", async () => {
    const wrapper = mount(ExamConverterAuthenticatedView);

    await finishConversion(wrapper);
    await wrapper.find('[data-test="exam-converter-accept-current-state-action"]').trigger("click");
    await flushPromises();
    await wrapper.find('[data-test="exam-converter-save-file-qti_package"]').trigger("click");
    await flushPromises();

    expect(gatewayMocks.downloadDigiExamMigrationArtifact).toHaveBeenCalledWith({
      artifactKey: "qti_package",
      correlationId: "corr_exam_converter_files",
      jobId: "job_exam_converter_files",
    });
    expect(gatewayMocks.saveDigiExamMigrationArtifactToUserFiles).toHaveBeenCalledWith(
      expect.objectContaining({
        artifact: expect.objectContaining({
          artifact_key: "qti_package",
          content_type: "application/zip",
          filename: "Ma1c_QTI.zip",
        }),
        correlationId: "corr_exam_converter_files",
        jobId: "job_exam_converter_files",
      }),
    );
    expect(wrapper.text()).toContain("Sparad i mina filer");
  });

  it("clears the accepted state when local choices are reset", async () => {
    const wrapper = mount(ExamConverterAuthenticatedView);

    await finishConversion(wrapper);
    await wrapper.find('[data-test="exam-converter-accept-current-state-action"]').trigger("click");
    await flushPromises();
    expect(
      wrapper.find('[data-test="exam-converter-download-file-qti_package"]').attributes(
        "disabled",
      ),
    ).toBeUndefined();

    await wrapper.find('[data-test="exam-converter-reset-local-choices"]').trigger("click");

    expect(wrapper.find('[data-test="exam-converter-source-drop-zone"]').exists()).toBe(true);
  });
});
