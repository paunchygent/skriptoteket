/**
 * Exam Converter IR-backed review shell behavior.
 *
 * Slice purpose:
 *   Render the approved read-only inspection modes from Sir Convert's
 *   item-addressable DigiExam IR after an authenticated conversion finishes.
 *
 * Expected behavior:
 *   The teacher sees one active inspection mode at a time. `Frågor` leads when
 *   questions need attention, the table uses a sparse `Saknas` column with
 *   only field labels, status is icon-only in dense rows, and files/report do
 *   not introduce download, save, edit, or service-contract actions.
 *
 * Recommended implementation shape:
 *   Keep artifact fetching in a small composable, validate/project IR in a
 *   parser boundary, and keep tabs, question rows, file rows, and report
 *   summary as focused presentation components.
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
    jobId: "job_exam_converter_review",
    requestContext: {
      correlationId: "corr_exam_converter_review",
      idempotencyKey: "idem_exam_converter_review",
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
    item_id: "item-001",
    item_type: "gap_fill",
    max_score: 2,
    prompt_html: null,
    prompt_lines: ["Beräkna värdet av uttrycket 3x² − 2x + 5"],
    sequence: 1,
    title: "Beräkna värdet av uttrycket 3x² − 2x + 5",
    warnings: [],
    ...overrides,
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
        size_bytes: 700_416,
      },
      {
        artifact_key: "qti_package",
        availability: "available",
        content_type: "application/zip",
        filename: "Ma1c_QTI.zip",
        sha256: null,
        size_bytes: 1_258_291,
      },
      {
        artifact_key: "manual_follow_up_report",
        availability: "available",
        content_type: "application/json",
        filename: "rapport.json",
        sha256: null,
        size_bytes: 2_048,
      },
    ],
    bundle_status: "partial",
    job_id: "job_exam_converter_review",
    manual_follow_up: {
      artifact_key: "manual_follow_up_report",
      count: 2,
      required: true,
    },
    schema_version: "digiexam_migration_bundle_v1",
    warnings: {
      artifact_key: "warnings_report",
      count: 1,
    },
  });
  gatewayMocks.downloadDigiExamMigrationArtifact.mockImplementation(
    ({ artifactKey }: { artifactKey: string }) => {
      if (artifactKey === "ir_json") {
        return Promise.resolve(
          artifactJsonBlob("ir_json", {
            items: [
              reviewItem(),
              reviewItem({
                answer_key: { provenance: "absent" },
                item_id: "item-004",
                item_type: "multiple_choice",
                max_score: 1,
                prompt_lines: ["Vilket av följande tal är ett primtal?"],
                sequence: 4,
                title: "Vilket av följande tal är ett primtal?",
              }),
              reviewItem({
                answer_key: { provenance: "not_applicable" },
                item_id: "item-012",
                item_type: "open_ended",
                max_score: null,
                prompt_lines: ["Resonera om lösningsmetod."],
                sequence: 12,
                title: "Resonera om lösningsmetod",
              }),
              reviewItem({
                answer_key: { provenance: "not_applicable" },
                item_id: "item-013",
                item_type: "open_ended",
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
                reason: "manual_answer_key_required",
                source_span: null,
              },
              {
                item_id: "item-012",
                message: "Manual marking is required.",
                reason: "manual_marking_required",
                source_span: null,
              },
              {
                item_id: "item-013",
                message: "Manual marking is required.",
                reason: "manual_marking_required",
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
      return Promise.resolve(
        artifactJsonBlob("migration_manifest", {
          asset_count: 0,
          asset_summaries: [],
          exam_schema_version: "digiexam_intermediate_exam_v2",
          item_count: 4,
          item_summaries: [],
          manual_follow_up_count: 3,
          parse_status: "success",
          renderer_ready: true,
          schema_version: "digiexam_ir_manifest_v2",
          source_filename: "Ma1c_NationelltProv_HT25.dxe",
          source_producer: null,
          warning_count: 1,
        }),
      );
    },
  );
}

function mockFreeTextOnlyReviewArtifacts(): void {
  gatewayMocks.listDigiExamMigrationArtifacts.mockResolvedValue({
    artifacts: [
      {
        artifact_key: "examnet_pdf",
        availability: "available",
        content_type: "application/pdf",
        filename: "Metaller_Exam.net.pdf",
        sha256: null,
        size_bytes: 700_416,
      },
      {
        artifact_key: "qti_package",
        availability: "available",
        content_type: "application/zip",
        filename: "Metaller_QTI.zip",
        sha256: null,
        size_bytes: 1_258_291,
      },
    ],
    bundle_status: "partial",
    job_id: "job_exam_converter_review",
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
              reviewItem({
                answer_key: { provenance: "not_applicable" },
                item_id: "item-001",
                item_type: "open_ended",
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
                reason: "manual_marking_required",
                source_span: null,
              },
            ],
            parse_status: "success",
            renderer_ready: true,
            schema_version: "digiexam_intermediate_exam_v2",
            source_filename: "1819077059-e-metaller-och-elektrokemi-23c.dxe",
            source_producer: null,
            warnings: [],
          }),
        );
      }
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
          source_filename: "1819077059-e-metaller-och-elektrokemi-23c.dxe",
          source_producer: null,
          warning_count: 0,
        }),
      );
    },
  );
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

describe("ExamConverterAuthenticatedView IR-backed review shell", () => {
  it("loads read-only IR artifacts and opens the questions mode when data is missing", async () => {
    const wrapper = mount(ExamConverterAuthenticatedView);

    await finishConversion(wrapper);

    expect(gatewayMocks.listDigiExamMigrationArtifacts).toHaveBeenCalledWith({
      correlationId: "corr_exam_converter_review",
      jobId: "job_exam_converter_review",
    });
    expect(gatewayMocks.downloadDigiExamMigrationArtifact).toHaveBeenCalledWith({
      artifactKey: "ir_json",
      correlationId: "corr_exam_converter_review",
      jobId: "job_exam_converter_review",
    });
    expect(wrapper.text()).toContain("Konverteringen av provet lyckades delvis");
    expect(wrapper.text()).toContain("2 frågor saknar facit eller poäng.");
    expect(wrapper.text()).toContain("Frågor (4)");
    expect(wrapper.text()).toContain("Filer (2)");
    expect(wrapper.find('[data-test="exam-converter-question-review-shell"]').exists()).toBe(
      true,
    );
  });

  it("uses sparse missing-field labels and icon-only row status in the dense question list", async () => {
    const wrapper = mount(ExamConverterAuthenticatedView);

    await finishConversion(wrapper);
    const questions = wrapper.find('[data-test="exam-converter-question-review-shell"]');

    expect(questions.text()).toContain("Saknas");
    expect(questions.text()).toContain("Facit");
    expect(questions.text()).toContain("Poäng");
    expect(questions.text()).not.toContain("Facit saknas");
    expect(questions.text()).not.toContain("Poäng saknas");
    expect(questions.text()).not.toContain("FOSID");
    expect(questions.text()).not.toContain("Svarsalternativ");
    expect(questions.text()).not.toContain("Komplettering");
    expect(questions.text()).not.toContain("Behöver ses över");
    expect(questions.findAll(".lucide-circle-check").length).toBeGreaterThan(0);
    expect(questions.findAll(".lucide-triangle-alert").length).toBeGreaterThan(0);
  });

  it("shows question number and prompt preview in one column and treats marked free text as normal", async () => {
    const wrapper = mount(ExamConverterAuthenticatedView);

    await finishConversion(wrapper);
    const questions = wrapper.find('[data-test="exam-converter-question-review-shell"]');
    const keyedRow = wrapper.find('[data-test="exam-converter-question-row-item-004"]');
    const manualMarkedFreeTextRow = wrapper.find(
      '[data-test="exam-converter-question-row-item-013"]',
    );

    expect(questions.text()).not.toContain("Nr");
    expect(keyedRow.text()).toContain("4. Vilket av följande tal är ett primtal?");
    expect(manualMarkedFreeTextRow.text()).toContain(
      "13. Förklara varför stål är hårdare än järn.",
    );
    expect(manualMarkedFreeTextRow.text()).toContain("Fritext");
    expect(manualMarkedFreeTextRow.text()).toContain("—");
    expect(manualMarkedFreeTextRow.text()).toContain("1 p");
    expect(manualMarkedFreeTextRow.text()).not.toContain("Facit");
    expect(manualMarkedFreeTextRow.text()).not.toContain("Poäng");
    expect(manualMarkedFreeTextRow.find(".lucide-circle-check").exists()).toBe(true);
    expect(manualMarkedFreeTextRow.find(".lucide-triangle-alert").exists()).toBe(false);
  });

  it("does not present free-text manual marking as missing facit or poäng", async () => {
    mockFreeTextOnlyReviewArtifacts();
    const freeTextOnlyResult = terminalResult();
    gatewayMocks.getDigiExamMigrationResult.mockResolvedValue({
      ...freeTextOnlyResult,
      conversion_metadata: {
        ...freeTextOnlyResult.conversion_metadata,
        warning_count: 0,
      },
    });
    const wrapper = mount(ExamConverterAuthenticatedView);

    await finishConversion(wrapper);

    expect(wrapper.text()).toContain("Provet är konverterat");
    expect(wrapper.text()).not.toContain("Konverteringen av provet lyckades delvis");
    expect(wrapper.text()).not.toContain("saknar facit eller poäng");

    await wrapper.find('[data-test="exam-converter-inspection-tab-questions"]').trigger("click");
    const freeTextRow = wrapper.find('[data-test="exam-converter-question-row-item-001"]');
    expect(freeTextRow.text()).toContain(
      "1. Varför är stål hårdare och starkare än järn?",
    );
    expect(freeTextRow.text()).toContain("Fritext");
    expect(freeTextRow.text()).toContain("—");
    expect(freeTextRow.text()).toContain("1 p");
    expect(freeTextRow.find(".lucide-circle-check").exists()).toBe(true);
    expect(freeTextRow.find(".lucide-triangle-alert").exists()).toBe(false);
  });

  it("shows only one selected question detail and does not offer local edit state", async () => {
    const wrapper = mount(ExamConverterAuthenticatedView);

    await finishConversion(wrapper);
    await wrapper.find('[data-test="exam-converter-question-row-item-004"]').trigger("click");

    const detail = wrapper.find('[data-test="exam-converter-selected-question-detail"]');
    expect(detail.text()).toContain("Fråga 4");
    expect(detail.text()).toContain("item-004");
    expect(detail.text()).toContain("Finns");
    expect(detail.text()).toContain("Saknas");
    expect(detail.text()).toContain("Facit");
    expect(wrapper.text()).not.toContain("Markera som kontrollerad");
    expect(wrapper.text()).not.toContain("Spara ändring");
    expect(wrapper.text()).not.toContain("när redigering stöds");
  });

  it("keeps file actions gated before the review decision is accepted", async () => {
    const wrapper = mount(ExamConverterAuthenticatedView);

    await finishConversion(wrapper);
    await wrapper.find('[data-test="exam-converter-inspection-tab-files"]').trigger("click");

    const files = wrapper.find('[data-test="exam-converter-files-readiness-list"]');
    expect(files.exists()).toBe(true);
    expect(files.text()).toContain("Ma1c_Exam.net.pdf");
    expect(files.text()).toContain("QTI-format");
    expect(files.text()).toContain("Granska eller godkänn först");
    expect(files.text()).not.toContain("Åtgärd");
    expect(
      wrapper.find('[data-test="exam-converter-download-file-examnet_pdf"]').attributes(
        "disabled",
      ),
    ).toBeDefined();
    expect(
      wrapper.find('[data-test="exam-converter-save-file-examnet_pdf"]').attributes("disabled"),
    ).toBeDefined();
  });

  it("keeps the report diagnostic and points back to the questions mode", async () => {
    const wrapper = mount(ExamConverterAuthenticatedView);

    await finishConversion(wrapper);
    await wrapper.find('[data-test="exam-converter-inspection-tab-report"]').trigger("click");

    const report = wrapper.find('[data-test="exam-converter-report-summary"]');
    expect(report.text()).toContain("Rapporten visar frågor som saknar facit eller poäng.");
    expect(report.text()).toContain("Facit saknas");
    expect(report.text()).toContain("Poäng saknas");
    expect(report.text()).not.toContain("manifest");
    expect(report.text()).not.toContain("bundle");
    expect(report.text()).not.toContain("Sir Convert");

    await wrapper.find('[data-test="exam-converter-report-open-questions"]').trigger("click");
    expect(wrapper.find('[data-test="exam-converter-question-review-shell"]').exists()).toBe(
      true,
    );
  });
});
