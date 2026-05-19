/**
 * Exam Converter IR-backed review shell behavior.
 *
 * Domain purpose: prove authenticated review projection for question, file,
 * and report artifacts.
 *
 * Relationships: complements the correction-specific PR-0332 spec.
 */

import { flushPromises, mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import ExamConverterAuthenticatedView from "./ExamConverterAuthenticatedView.vue";
import { mockFreeTextOnlyReviewArtifacts } from "./examConverterAuthenticatedFreeTextFixtures";
import {
  correctionApplyResult,
  correctionSourceState,
  createCorrectionSessionRecorder,
} from "./examConverterAuthenticatedCorrectionSessionFixtures";
import {
  artifactJsonBlob,
  finishConversion,
  mockReviewArtifacts,
  submittedJob,
  terminalResult,
} from "./examConverterAuthenticatedReviewFixtures";
import {
  DIGIEXAM_ARTIFACT_TARGET_READINESS_REPORT,
  DIGIEXAM_TARGET_EXAMNET_PDF,
  DIGIEXAM_TARGET_NEEDS_TEACHER_REVIEW_DECISION,
  DIGIEXAM_TARGET_QTI_PACKAGE,
  DIGIEXAM_TARGET_READY,
  SIR_CONVERT_BUNDLE_STATUS_COMPLETE,
} from "../../api/sirConvertGateway/contractValues";
import {
  TARGET_READINESS_REPORT_SCHEMA_VERSION,
} from "../../api/sirConvertGateway/schemaVersions";

const gatewayMocks = vi.hoisted(() => ({
  applyExamAuthoringCorrections: vi.fn(),
  downloadDigiExamMigrationArtifact: vi.fn(),
  getDigiExamMigrationJob: vi.fn(),
  getDigiExamMigrationResult: vi.fn(),
  issueExamAuthoringCorrectionSourceState: vi.fn(),
  listDigiExamMigrationArtifacts: vi.fn(),
  saveDigiExamMigrationArtifactToUserFiles: vi.fn(),
  submitDigiExamMigration: vi.fn(),
}));
const correctionSessionApiMocks = vi.hoisted(() => ({
  getExamConverterCorrectionSession: vi.fn(),
  registerExamConverterConversionHubJob: vi.fn(),
  upsertExamConverterCorrectionIntent: vi.fn(),
}));
const correctionSessionRecorder = createCorrectionSessionRecorder();

vi.mock("../../api/sirConvertGateway", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../../api/sirConvertGateway")>();
  return {
    ...actual,
    applyExamAuthoringCorrections: gatewayMocks.applyExamAuthoringCorrections,
    downloadDigiExamMigrationArtifact: gatewayMocks.downloadDigiExamMigrationArtifact,
    getDigiExamMigrationJob: gatewayMocks.getDigiExamMigrationJob,
    getDigiExamMigrationResult: gatewayMocks.getDigiExamMigrationResult,
    issueExamAuthoringCorrectionSourceState: gatewayMocks.issueExamAuthoringCorrectionSourceState,
    listDigiExamMigrationArtifacts: gatewayMocks.listDigiExamMigrationArtifacts,
    saveDigiExamMigrationArtifactToUserFiles:
      gatewayMocks.saveDigiExamMigrationArtifactToUserFiles,
    submitDigiExamMigration: gatewayMocks.submitDigiExamMigration,
  };
});

vi.mock("../../api/examConverterCorrectionSessions", () => ({
  getExamConverterCorrectionSession: correctionSessionApiMocks.getExamConverterCorrectionSession,
  registerExamConverterConversionHubJob:
    correctionSessionApiMocks.registerExamConverterConversionHubJob,
  upsertExamConverterCorrectionIntent: correctionSessionApiMocks.upsertExamConverterCorrectionIntent,
}));

beforeEach(() => {
  window.sessionStorage.clear();
  correctionSessionRecorder.reset();
  correctionSessionApiMocks.getExamConverterCorrectionSession.mockReset();
  correctionSessionApiMocks.registerExamConverterConversionHubJob.mockReset();
  correctionSessionApiMocks.upsertExamConverterCorrectionIntent.mockReset();
  gatewayMocks.applyExamAuthoringCorrections.mockReset();
  gatewayMocks.downloadDigiExamMigrationArtifact.mockReset();
  gatewayMocks.getDigiExamMigrationJob.mockReset();
  gatewayMocks.getDigiExamMigrationResult.mockReset();
  gatewayMocks.issueExamAuthoringCorrectionSourceState.mockReset();
  gatewayMocks.listDigiExamMigrationArtifacts.mockReset();
  gatewayMocks.saveDigiExamMigrationArtifactToUserFiles.mockReset();
  gatewayMocks.submitDigiExamMigration.mockReset();
  gatewayMocks.submitDigiExamMigration.mockResolvedValue(submittedJob("succeeded"));
  gatewayMocks.getDigiExamMigrationResult.mockResolvedValue(terminalResult());
  gatewayMocks.issueExamAuthoringCorrectionSourceState.mockResolvedValue(correctionSourceState());
  gatewayMocks.applyExamAuthoringCorrections.mockResolvedValue(correctionApplyResult());
  correctionSessionApiMocks.registerExamConverterConversionHubJob.mockResolvedValue({
    job_id: "local-conversion-hub-job-1",
    status: "succeeded",
    upstream_job_id: "job_exam_converter_review",
  });
  correctionSessionApiMocks.upsertExamConverterCorrectionIntent.mockImplementation(
    ({ request }: { request: { intent: Record<string, unknown> } }) =>
      Promise.resolve(correctionSessionRecorder.recordIntent(request.intent)),
  );
  correctionSessionApiMocks.getExamConverterCorrectionSession.mockImplementation(() =>
    Promise.resolve(correctionSessionRecorder.current()),
  );
  mockReviewArtifacts(gatewayMocks);
});

describe("ExamConverterAuthenticatedView IR-backed review shell", () => {
  it("loads read-only IR artifacts and opens the questions mode when data is missing", async () => {
    const wrapper = mount(ExamConverterAuthenticatedView);

    await finishConversion(wrapper);

    expect(gatewayMocks.listDigiExamMigrationArtifacts).toHaveBeenCalledWith({
      completionReportRequired: true,
      correlationId: "corr_exam_converter_review",
      jobId: "job_exam_converter_review",
    });
    expect(gatewayMocks.downloadDigiExamMigrationArtifact).toHaveBeenCalledWith({
      artifactKey: "ir_json",
      correlationId: "corr_exam_converter_review",
      jobId: "job_exam_converter_review",
    });
    expect(gatewayMocks.downloadDigiExamMigrationArtifact).toHaveBeenCalledWith({
      artifactKey: "answer_key_completion_report",
      correlationId: "corr_exam_converter_review",
      jobId: "job_exam_converter_review",
    });
    expect(wrapper.text()).toContain("Kontrollera facit");
    expect(wrapper.text()).toContain("Frågor (6)");
    expect(wrapper.text()).toContain("Filer (2)");
    expect(wrapper.find('[data-test="exam-converter-question-review-shell"]').exists()).toBe(true);
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
    expect(questions.findAll(".lucide-bot").length).toBeGreaterThan(0);
    expect(questions.find('[data-test="exam-converter-question-row-item-004"]').text()).not.toContain(
      "Giltigt",
    );
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
      "Flerval",
    );
    expect(wrapper.find('[data-test="exam-converter-question-row-item-005"]').text()).toContain(
      "Flerval",
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

  it("keeps the success banner when all question rows and target files are ready despite warnings", async () => {
    mockFreeTextOnlyReviewArtifacts(gatewayMocks);
    const resultWithNonBlockingWarning = terminalResult();
    gatewayMocks.getDigiExamMigrationResult.mockResolvedValue({
      ...resultWithNonBlockingWarning,
      conversion_metadata: {
        ...resultWithNonBlockingWarning.conversion_metadata,
        bundle_status: SIR_CONVERT_BUNDLE_STATUS_COMPLETE,
        manual_follow_up_required: false,
        warning_count: 1,
      },
    });
    const wrapper = mount(ExamConverterAuthenticatedView);

    await finishConversion(wrapper);

    expect(wrapper.text()).toContain("Provet är konverterat");
    expect(wrapper.text()).not.toContain("Konverteringen av provet lyckades delvis");
    expect(wrapper.findAll(".lucide-circle-check").length).toBeGreaterThan(0);
  });

  it("offers explicit export copy when QTI needs a target-level export decision even with green question rows", async () => {
    mockFreeTextOnlyReviewArtifacts(gatewayMocks);
    const baseDownload = gatewayMocks.downloadDigiExamMigrationArtifact.getMockImplementation();
    gatewayMocks.downloadDigiExamMigrationArtifact.mockImplementation(
      (params: { artifactKey: string }) => {
        if (params.artifactKey === DIGIEXAM_ARTIFACT_TARGET_READINESS_REPORT) {
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
                  readiness: DIGIEXAM_TARGET_NEEDS_TEACHER_REVIEW_DECISION,
                  export_enabled: false,
                  artifact_key: null,
                  reason_code: "manual_marking_required",
                  teacher_action: "accept_current_state_for_export",
                  retryable: false,
                  message_key: "exam_converter.target.needs_teacher_review_decision",
                  item_id: "item-001",
                  sequence: 1,
                  source_item_fingerprint: "sha256:item-001",
                },
              ],
            }),
          );
        }
        return baseDownload?.(params);
      },
    );
    gatewayMocks.getDigiExamMigrationResult.mockResolvedValue({
      ...terminalResult(),
      conversion_metadata: {
        ...terminalResult().conversion_metadata,
        bundle_status: SIR_CONVERT_BUNDLE_STATUS_COMPLETE,
        manual_follow_up_required: false,
        warning_count: 0,
      },
    });
    const wrapper = mount(ExamConverterAuthenticatedView);

    await finishConversion(wrapper);

    expect(wrapper.text()).toContain("Konverteringen av provet lyckades delvis");
    expect(wrapper.text()).toContain("1 målfil väntar på att skapas.");
    expect(wrapper.text()).not.toContain("1 fråga saknar facit eller poäng.");
    expect(
      wrapper.find('[data-test="exam-converter-review-questions-action"]').exists(),
    ).toBe(false);
    const reviewPlaceholder = wrapper.find(
      '[data-test="exam-converter-review-questions-placeholder"]',
    );
    expect(reviewPlaceholder.exists()).toBe(true);
    expect(reviewPlaceholder.attributes("aria-hidden")).toBe("true");
    expect(wrapper.text()).toContain("Skapa filer");
    expect(wrapper.text()).not.toContain("Godkänn");

    await wrapper.find('[data-test="exam-converter-accept-current-state-action"]').trigger("click");
    await flushPromises();

    expect(correctionSessionApiMocks.upsertExamConverterCorrectionIntent).toHaveBeenLastCalledWith(
      expect.objectContaining({
        request: expect.objectContaining({
          intent: expect.objectContaining({
            kind: "review_decision",
            payload: expect.objectContaining({
              accepted_targets: expect.arrayContaining([DIGIEXAM_TARGET_QTI_PACKAGE]),
            }),
            target: expect.objectContaining({
              accepted_target_family: "requested_artifacts",
            }),
          }),
        }),
      }),
    );
    expect(gatewayMocks.applyExamAuthoringCorrections).toHaveBeenLastCalledWith(
      expect.objectContaining({
        request: expect.objectContaining({
          corrections: [
            expect.objectContaining({
              item_id: "item-001",
              kind: "review_decision",
              accepted_targets: expect.arrayContaining([DIGIEXAM_TARGET_QTI_PACKAGE]),
            }),
          ],
        }),
      }),
    );
  });

  it("surfaces Lucktext gaps and embedded image structure in the detail pane", async () => {
    const wrapper = mount(ExamConverterAuthenticatedView);

    await finishConversion(wrapper);
    await wrapper.find('[data-test="exam-converter-question-row-item-001"]').trigger("click");

    const detail = wrapper.find('[data-test="exam-converter-selected-question-detail"]');
    const lucktext = wrapper.find('[data-test="exam-converter-selected-question-lucktext"]');
    expect(
      detail.find<HTMLInputElement>('[data-test="exam-converter-item-title-patch-input"]')
        .element.value,
    ).toBe("Begrepp i ekologi");
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
    expect(files.text()).toContain("Granska facit först");
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
    expect(report.text()).toContain(
      "Rapporten skiljer kvarvarande åtgärder från konverteringsvarningar.",
    );
    expect(report.text()).toContain("Facit saknas");
    expect(report.text()).toContain("Poäng saknas");
    expect(report.text()).toContain("Konverteringsdiagnostik");
    expect(report.text()).toContain("Konverteringsvarningar");
    expect(report.text()).toContain(
      "När frågor, facit och poäng är klara kan filerna användas",
    );
    expect(report.text()).not.toContain("manifest");
    expect(report.text()).not.toContain("bundle");
    expect(report.text()).not.toContain("Sir Convert");

    await wrapper.find('[data-test="exam-converter-report-open-questions"]').trigger("click");
    expect(wrapper.find('[data-test="exam-converter-question-review-shell"]').exists()).toBe(
      true,
    );
  });
});
