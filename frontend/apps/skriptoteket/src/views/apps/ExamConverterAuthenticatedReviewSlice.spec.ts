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

import { mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import ExamConverterAuthenticatedView from "./ExamConverterAuthenticatedView.vue";
import {
  finishConversion,
  mockFreeTextOnlyReviewArtifacts,
  mockReviewArtifacts,
  submittedJob,
  terminalResult,
} from "./examConverterAuthenticatedReviewFixtures";

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

beforeEach(() => {
  gatewayMocks.downloadDigiExamMigrationArtifact.mockReset();
  gatewayMocks.getDigiExamMigrationJob.mockReset();
  gatewayMocks.getDigiExamMigrationResult.mockReset();
  gatewayMocks.listDigiExamMigrationArtifacts.mockReset();
  gatewayMocks.saveDigiExamMigrationArtifactToUserFiles.mockReset();
  gatewayMocks.submitDigiExamMigration.mockReset();
  gatewayMocks.submitDigiExamMigration.mockResolvedValue(submittedJob("succeeded"));
  gatewayMocks.getDigiExamMigrationResult.mockResolvedValue(terminalResult());
  mockReviewArtifacts(gatewayMocks);
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
    expect(wrapper.text()).toContain("Frågor (6)");
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
    expect(keyedRow.text()).toContain(
      "4. Vilket av följande påståenden beskriver cellandning bäst?",
    );
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

  it("uses the approved Swedish item labels and no Enval shortcut", async () => {
    const wrapper = mount(ExamConverterAuthenticatedView);

    await finishConversion(wrapper);

    expect(wrapper.find('[data-test="exam-converter-question-row-item-001"]').text()).toContain(
      "Lucktext",
    );
    expect(wrapper.find('[data-test="exam-converter-question-row-item-004"]').text()).toContain(
      "Flerval: ett val",
    );
    expect(wrapper.find('[data-test="exam-converter-question-row-item-005"]').text()).toContain(
      "Flerval: flera val",
    );
    expect(wrapper.find('[data-test="exam-converter-question-row-item-006"]').text()).toContain(
      "Fritext",
    );
    expect(wrapper.text()).not.toContain("Enval");
    expect(wrapper.text()).not.toContain("Flerval: matchning");
  });

  it("does not present free-text manual marking as missing facit or poäng", async () => {
    mockFreeTextOnlyReviewArtifacts(gatewayMocks);
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
    expect(detail.text()).toContain("Alternativ");
    expect(detail.text()).toContain("Växter tar upp vatten ur marken.");
    expect(detail.text()).toContain(
      "Djur och växter frigör energi ur socker med hjälp av syre.",
    );
    expect(detail.text()).toContain("Saknas");
    expect(detail.text()).toContain("Facit");
    expect(wrapper.text()).not.toContain("Markera som kontrollerad");
    expect(wrapper.text()).not.toContain("Spara ändring");
    expect(wrapper.text()).not.toContain("när redigering stöds");
  });

  it("surfaces Lucktext gaps and embedded image structure in the detail pane", async () => {
    const wrapper = mount(ExamConverterAuthenticatedView);

    await finishConversion(wrapper);
    await wrapper.find('[data-test="exam-converter-question-row-item-001"]').trigger("click");

    const detail = wrapper.find('[data-test="exam-converter-selected-question-detail"]');
    const lucktext = wrapper.find('[data-test="exam-converter-selected-question-lucktext"]');
    expect(detail.text()).toContain("Fråga 1");
    expect(detail.text()).toContain("Lucktext");
    expect(lucktext.text()).toContain("Luckor");
    expect(lucktext.text()).toContain("5");
    expect(lucktext.text()).toContain("Bilder");
    expect(lucktext.text()).toContain("1");
    expect(lucktext.find("img").attributes("src")).toContain("data:image/png;base64,");
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
