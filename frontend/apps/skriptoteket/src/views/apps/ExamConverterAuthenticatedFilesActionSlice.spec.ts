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
import {
  artifactJsonBlob,
  fileArtifactBlob,
  filesTerminalResult,
  singleMissingChoiceManifest,
  submittedFilesJob,
  targetReadinessReportPayload,
} from "./examConverterAuthenticatedFilesActionPayloads";
import { DIGIEXAM_ARTIFACT_ANSWER_KEY_COMPLETION_REPORT } from "../../api/sirConvertGateway/contractValues";
import {
  ANSWER_KEY_COMPLETION_REPORT_SCHEMA_VERSION,
  DIGIEXAM_EFFECTIVE_EXAM_SCHEMA_VERSION,
  DIGIEXAM_INTERMEDIATE_EXAM_SCHEMA_VERSION,
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

let acceptedOverlaySubmitted = false;

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
      ...(!acceptedOverlaySubmitted
        ? [
            {
              artifact_key: DIGIEXAM_ARTIFACT_ANSWER_KEY_COMPLETION_REPORT,
              availability: "available",
              content_type: "application/json",
              filename: "answer-key-completion-report.json",
              sha256: "sha256:completion-report",
              size_bytes: 512,
            },
          ]
        : []),
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
      effective_exam_schema_version: DIGIEXAM_EFFECTIVE_EXAM_SCHEMA_VERSION,
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
          artifactJsonBlob("migration_manifest", singleMissingChoiceManifest),
        );
      }
      if (artifactKey === "target_readiness_report") {
        return Promise.resolve(
          artifactJsonBlob(
            "target_readiness_report",
            targetReadinessReportPayload(acceptedOverlaySubmitted),
          ),
        );
      }
      if (artifactKey === DIGIEXAM_ARTIFACT_ANSWER_KEY_COMPLETION_REPORT) {
        return Promise.resolve(
          artifactJsonBlob(DIGIEXAM_ARTIFACT_ANSWER_KEY_COMPLETION_REPORT, {
            schema_version: ANSWER_KEY_COMPLETION_REPORT_SCHEMA_VERSION,
            completion_mode: "local_llm_suggest_missing_machine_marked",
            job_id: "job_exam_converter_files",
            items: [
              {
                item_id: "item-001",
                sequence: 1,
                item_type: "multiple_choice",
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
    return Promise.resolve(submittedFilesJob("succeeded"));
  });
  gatewayMocks.getDigiExamMigrationResult.mockResolvedValue(filesTerminalResult());
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
