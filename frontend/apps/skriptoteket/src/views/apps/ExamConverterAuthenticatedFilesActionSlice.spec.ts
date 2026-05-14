/**
 * Exam Converter review decision and file-action behavior.
 *
 * Slice purpose:
 *   Let the teacher either review missing question data or approve the current
 *   conversion state before downloading or saving generated files.
 *
 * Expected behavior:
 *   File actions stay blocked while actual `Facit`/`Poäng` gaps exist, then
 *   become available after `Godkänn`. Action buttons use short labels, while
 *   explanatory copy lives in dynamic help affordances.
 *
 * Recommended implementation shape:
 *   Keep review acceptance in local job state, keep file rows inside `Filer`,
 *   and use the existing Gateway download plus owner-scoped user-file save
 *   clients without mutating Sir Convert IR.
 */

import { flushPromises, mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import ExamConverterAuthenticatedView from "./ExamConverterAuthenticatedView.vue";
import type {
  SirConvertJobStatus,
  SirConvertSubmittedJob,
  SirConvertTerminalResult,
} from "../../api/sirConvertGateway";

const gatewayMocks = vi.hoisted(() => ({
  downloadDigiExamMigrationArtifact: vi.fn(),
  getDigiExamMigrationJob: vi.fn(),
  getDigiExamMigrationResult: vi.fn(),
  listDigiExamMigrationArtifacts: vi.fn(),
  saveDigiExamMigrationArtifactToUserFiles: vi.fn(),
  submitDigiExamMigration: vi.fn(),
}));

vi.mock("../../api/sirConvertGateway", () => ({
  downloadDigiExamMigrationArtifact: gatewayMocks.downloadDigiExamMigrationArtifact,
  getDigiExamMigrationJob: gatewayMocks.getDigiExamMigrationJob,
  getDigiExamMigrationResult: gatewayMocks.getDigiExamMigrationResult,
  listDigiExamMigrationArtifacts: gatewayMocks.listDigiExamMigrationArtifacts,
  saveDigiExamMigrationArtifactToUserFiles:
    gatewayMocks.saveDigiExamMigrationArtifactToUserFiles,
  submitDigiExamMigration: gatewayMocks.submitDigiExamMigration,
}));

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
      bundle_schema_version: "digiexam_migration_bundle_v1",
      bundle_status: "partial",
      manual_follow_up_required: true,
      route_key: "digiexam_dxe_to_examnet_migration_bundle",
      source_sha256: null,
      target_availability: {
        examnet_pdf: "available",
        qti_package: "available",
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

function mockReviewArtifacts(): void {
  gatewayMocks.listDigiExamMigrationArtifacts.mockResolvedValue({
    artifacts: [
      {
        artifact_key: "examnet_pdf",
        availability: "available",
        content_type: "application/pdf",
        filename: "Ma1c_Exam.net.pdf",
        sha256: null,
        size_bytes: 4,
      },
      {
        artifact_key: "qti_package",
        availability: "available",
        content_type: "application/zip",
        filename: "Ma1c_QTI.zip",
        sha256: null,
        size_bytes: 4,
      },
    ],
    bundle_status: "partial",
    job_id: "job_exam_converter_files",
    manual_follow_up: {
      artifact_key: "manual_follow_up_report",
      count: 1,
      required: true,
    },
    schema_version: "digiexam_migration_bundle_v1",
    warnings: {
      artifact_key: "warnings_report",
      count: 0,
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
            schema_version: "digiexam_intermediate_exam_v2",
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
            exam_schema_version: "digiexam_intermediate_exam_v2",
            item_count: 1,
            item_summaries: [],
            manual_follow_up_count: 1,
            parse_status: "success",
            renderer_ready: true,
            schema_version: "digiexam_ir_manifest_v2",
            source_filename: "Ma1c_NationelltProv_HT25.dxe",
            source_producer: null,
            warning_count: 0,
          }),
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
    source_artifact_id: "documents.conversion_hub:job_exam_converter_files:examnet_pdf",
    vault_artifact: {
      bytes: 4,
      created_at: "2026-05-14T10:00:00Z",
      file_id: "vault-file-1",
      name: "Ma1c_Exam.net.pdf",
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
  gatewayMocks.downloadDigiExamMigrationArtifact.mockReset();
  gatewayMocks.getDigiExamMigrationJob.mockReset();
  gatewayMocks.getDigiExamMigrationResult.mockReset();
  gatewayMocks.listDigiExamMigrationArtifacts.mockReset();
  gatewayMocks.saveDigiExamMigrationArtifactToUserFiles.mockReset();
  gatewayMocks.submitDigiExamMigration.mockReset();
  gatewayMocks.submitDigiExamMigration.mockResolvedValue(submittedJob("succeeded"));
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

    const downloadAfter = wrapper.find(
      '[data-test="exam-converter-download-file-examnet_pdf"]',
    );
    const saveAfter = wrapper.find('[data-test="exam-converter-save-file-examnet_pdf"]');
    expect(wrapper.text()).toContain("Godkänt som det är");
    expect(wrapper.text()).toContain("Godkänt för export");
    expect(downloadAfter.attributes("disabled")).toBeUndefined();
    expect(saveAfter.attributes("disabled")).toBeUndefined();
  });

  it("saves an approved generated file through the owner-scoped user-file client", async () => {
    const wrapper = mount(ExamConverterAuthenticatedView);

    await finishConversion(wrapper);
    await wrapper.find('[data-test="exam-converter-accept-current-state-action"]').trigger("click");
    await wrapper.find('[data-test="exam-converter-save-file-examnet_pdf"]').trigger("click");
    await flushPromises();

    expect(gatewayMocks.downloadDigiExamMigrationArtifact).toHaveBeenCalledWith({
      artifactKey: "examnet_pdf",
      correlationId: "corr_exam_converter_files",
      jobId: "job_exam_converter_files",
    });
    expect(gatewayMocks.saveDigiExamMigrationArtifactToUserFiles).toHaveBeenCalledWith(
      expect.objectContaining({
        artifact: expect.objectContaining({
          artifact_key: "examnet_pdf",
          content_type: "application/pdf",
          filename: "Ma1c_Exam.net.pdf",
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
    expect(wrapper.text()).toContain("Godkänt som det är");

    await wrapper.find('[data-test="exam-converter-reset-local-choices"]').trigger("click");

    expect(wrapper.text()).not.toContain("Godkänt som det är");
    expect(wrapper.find('[data-test="exam-converter-source-drop-zone"]').exists()).toBe(true);
  });
});
