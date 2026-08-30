/**
 * Exam Converter IR-backed review shell behavior.
 *
 * Domain purpose: prove authenticated review projection for question, file,
 * and report artifacts.
 *
 * Relationships: complements the correction-specific PR-0332 spec.
 */

import { mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import ExamConverterAuthenticatedView from "./ExamConverterAuthenticatedView.vue";
import ExamConverterReportSummary from "./exam-converter-authenticated/ExamConverterReportSummary.vue";
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
  DIGIEXAM_ARTIFACT_ANSWER_KEY_REVIEW_STATE_REPORT,
  DIGIEXAM_ARTIFACT_TARGET_READINESS_REPORT,
  DIGIEXAM_TARGET_EXAMNET_PDF,
  DIGIEXAM_TARGET_QTI_PACKAGE,
  DIGIEXAM_TARGET_READY,
  EXAM_CONVERTER_BUNDLE_STATUS_COMPLETE,
} from "../../api/examConverterContracts";
import {
  ANSWER_KEY_REVIEW_STATE_SCHEMA_VERSION,
  TARGET_READINESS_REPORT_SCHEMA_VERSION,
} from "../../api/examConverterContracts";

const gatewayMocks = vi.hoisted(() => ({
  applyExamAuthoringCorrections: vi.fn(),
  downloadDigiExamMigrationArtifact: vi.fn(),
  getDigiExamMigrationJob: vi.fn(),
  getDigiExamMigrationResult: vi.fn(),
  issueExamAuthoringCorrectionSourceState: vi.fn(),
  listDigiExamMigrationArtifacts: vi.fn(),
  replayLocalExamConversion: vi.fn(),
  saveDigiExamMigrationArtifactToUserFiles: vi.fn(),
  submitDigiExamMigration: vi.fn(),
}));

vi.mock("../../api/examConverterLocal", () => ({
  downloadLocalExamConversionArtifact: gatewayMocks.downloadDigiExamMigrationArtifact,
  getLocalExamConversionJob: gatewayMocks.getDigiExamMigrationJob,
  getLocalExamConversionResult: gatewayMocks.getDigiExamMigrationResult,
  getLocalExamConversionSourceState: gatewayMocks.issueExamAuthoringCorrectionSourceState,
  listLocalExamConversionArtifacts: gatewayMocks.listDigiExamMigrationArtifacts,
  replayLocalExamConversion: gatewayMocks.replayLocalExamConversion,
  submitLocalExamConversion: gatewayMocks.submitDigiExamMigration,
}));
const correctionSessionApiMocks = vi.hoisted(() => ({
  getExamConverterCorrectionSession: vi.fn(),
  registerExamConverterConversionHubJob: vi.fn(),
  replaceExamConverterCorrectionIntents: vi.fn(),
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
  replaceExamConverterCorrectionIntents: correctionSessionApiMocks.replaceExamConverterCorrectionIntents,
}));

beforeEach(() => {
  window.sessionStorage.clear();
  correctionSessionRecorder.reset();
  correctionSessionApiMocks.getExamConverterCorrectionSession.mockReset();
  correctionSessionApiMocks.registerExamConverterConversionHubJob.mockReset();
  correctionSessionApiMocks.replaceExamConverterCorrectionIntents.mockReset();
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
  correctionSessionApiMocks.replaceExamConverterCorrectionIntents.mockImplementation(
    ({ request }: { request: { intents: Record<string, unknown>[] } }) =>
      Promise.resolve(correctionSessionRecorder.recordIntents(request.intents)),
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
    expect(questions.text()).toContain("Granska");
    expect(questions.find('[data-test="exam-converter-selected-question-ai-suggestion"]').exists()).toBe(false);
    expect(questions.text()).toContain("Poäng");
    expect(questions.text()).not.toContain("Facit saknas");
    expect(questions.text()).not.toContain("Poäng saknas");
    expect(questions.text()).not.toContain("FOSID");
    expect(questions.text()).not.toContain("Svarsalternativ");
    expect(questions.text()).not.toContain("Komplettering");
    expect(questions.text()).not.toContain("Behöver ses över");
    expect(questions.findAll(".lucide-check").length).toBeGreaterThan(0);
    expect(questions.findAll(".lucide-sparkles").length).toBeGreaterThan(0);
    expect(questions.findAll(".lucide-circle-check")).toHaveLength(0);
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
    expect(manualMarkedFreeTextRow.find(".lucide-check").exists()).toBe(true);
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
    expect(freeTextRow.find(".lucide-check").exists()).toBe(true);
    expect(freeTextRow.find(".lucide-triangle-alert").exists()).toBe(false);
  });

  it("ignores impossible free-text manual answer-key repair from compact review state", async () => {
    mockFreeTextOnlyReviewArtifacts(gatewayMocks);
    const baseDownload = gatewayMocks.downloadDigiExamMigrationArtifact.getMockImplementation();
    gatewayMocks.downloadDigiExamMigrationArtifact.mockImplementation(
      (params: { artifactKey: string }) => {
        if (params.artifactKey === DIGIEXAM_ARTIFACT_ANSWER_KEY_REVIEW_STATE_REPORT) {
          return Promise.resolve(
            artifactJsonBlob(DIGIEXAM_ARTIFACT_ANSWER_KEY_REVIEW_STATE_REPORT, {
              schema_version: ANSWER_KEY_REVIEW_STATE_SCHEMA_VERSION,
              items: [
                {
                  choice_ids: [],
                  choice_interaction_ids: [],
                  correction_affordances: [],
                  current_key_origin: "none",
                  gap_ids: [],
                  gap_interaction_ids: [],
                  item_id: "item-001",
                  item_type: "open_ended",
                  message_key: "exam_converter.answer_key.manual_required",
                  provenance_detail: null,
                  reasons: ["manual_answer_key_required"],
                  replay_artifact_references: [],
                  review_state: "validation_required",
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
    const wrapper = mount(ExamConverterAuthenticatedView);

    await finishConversion(wrapper);

    expect(wrapper.text()).toContain("Provet är konverterat");
    expect(wrapper.text()).not.toContain("Kontrollera facit");
    expect(wrapper.text()).not.toContain("saknar rätt svar eller facitsvar");
    expect(wrapper.text()).not.toContain("Saknar facitsvar");
    expect(wrapper.text()).not.toContain("Inget rätt svar valt");
    expect(wrapper.text()).not.toContain("Spara facit");

    await wrapper.find('[data-test="exam-converter-inspection-tab-questions"]').trigger("click");
    const freeTextRow = wrapper.find('[data-test="exam-converter-question-row-item-001"]');
    expect(freeTextRow.text()).toContain(
      "1. Varför är stål hårdare och starkare än järn?",
    );
    expect(freeTextRow.text()).toContain("Fritext");
    expect(freeTextRow.text()).toContain("Klart");
    expect(freeTextRow.text()).not.toContain("Kontrollera");
    expect(freeTextRow.text()).not.toContain("Facit");
    expect(freeTextRow.find(".lucide-check").exists()).toBe(true);
    expect(freeTextRow.find(".lucide-triangle-alert").exists()).toBe(false);

    await wrapper.find('[data-test="exam-converter-inspection-tab-report"]').trigger("click");
    const reportRows = wrapper.findAll(".exam-converter-report-row");
    expect(reportRows.find((row) => row.text().includes("Frågor"))?.text()).toContain("0");
    expect(reportRows.find((row) => row.text().includes("Facit saknas"))?.text()).toContain("0");
  });

  it("renders free-text unsupported-type follow-up as non-gated review state", async () => {
    mockFreeTextOnlyReviewArtifacts(gatewayMocks);
    const baseDownload = gatewayMocks.downloadDigiExamMigrationArtifact.getMockImplementation();
    gatewayMocks.downloadDigiExamMigrationArtifact.mockImplementation(
      (params: { artifactKey: string }) => {
        if (params.artifactKey === DIGIEXAM_ARTIFACT_ANSWER_KEY_REVIEW_STATE_REPORT) {
          return Promise.resolve(
            artifactJsonBlob(DIGIEXAM_ARTIFACT_ANSWER_KEY_REVIEW_STATE_REPORT, {
              schema_version: ANSWER_KEY_REVIEW_STATE_SCHEMA_VERSION,
              items: [
                {
                  choice_ids: [],
                  choice_interaction_ids: [],
                  correction_affordances: [],
                  current_key_origin: "none",
                  gap_ids: [],
                  gap_interaction_ids: [],
                  item_id: "item-001",
                  item_type: "open_ended",
                  message_key: "exam_converter.answer_key.unsupported_item_type",
                  provenance_detail: null,
                  reasons: ["unsupported_item_type"],
                  replay_artifact_references: [],
                  review_state: "validation_required",
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
    const wrapper = mount(ExamConverterAuthenticatedView);

    await finishConversion(wrapper);
    await wrapper.find('[data-test="exam-converter-inspection-tab-questions"]').trigger("click");

    const freeTextRow = wrapper.find('[data-test="exam-converter-question-row-item-001"]');
    expect(wrapper.text()).not.toContain("Kontrollera facit");
    expect(freeTextRow.text()).toContain("Fritext");
    expect(freeTextRow.text()).toContain("Klart");
    expect(freeTextRow.text()).not.toContain("Kontrollera");
    expect(freeTextRow.text()).not.toContain("Frågetypen behöver kontrolleras");
    expect(freeTextRow.find(".lucide-check").exists()).toBe(true);
    expect(freeTextRow.find(".lucide-triangle-alert").exists()).toBe(false);
  });

  it("keeps the success banner when all question rows and target files are ready despite warnings", async () => {
    mockFreeTextOnlyReviewArtifacts(gatewayMocks);
    const resultWithNonBlockingWarning = terminalResult();
    gatewayMocks.getDigiExamMigrationResult.mockResolvedValue({
      ...resultWithNonBlockingWarning,
      conversion_metadata: {
        ...resultWithNonBlockingWarning.conversion_metadata,
        bundle_status: EXAM_CONVERTER_BUNDLE_STATUS_COMPLETE,
        manual_follow_up_required: false,
        warning_count: 1,
      },
    });
    const wrapper = mount(ExamConverterAuthenticatedView);

    await finishConversion(wrapper);

    expect(wrapper.text()).toContain("Provet är konverterat");
    expect(wrapper.text()).not.toContain("Konverteringen av provet lyckades delvis");
    expect(wrapper.find('[data-test="exam-converter-result-strip"]').findComponent({ name: "IconCheck" }).exists()).toBe(true);
  });

  it("keeps target-level export blockers out of teacher authoring state", async () => {
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
                  readiness: "unsupported_target_shape",
                  export_enabled: false,
                  artifact_key: null,
                  reason_code: "unsupported_target_shape",
                  teacher_action: "manual_target_creation_required",
                  retryable: false,
                  message_key: "exam_converter.target.unsupported_target_shape",
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
        bundle_status: EXAM_CONVERTER_BUNDLE_STATUS_COMPLETE,
        manual_follow_up_required: false,
        warning_count: 0,
      },
    });
    const wrapper = mount(ExamConverterAuthenticatedView);

    await finishConversion(wrapper);

    expect(wrapper.text()).toContain("Provet är konverterat");
    expect(wrapper.text()).toContain("Målfilen kunde inte skapas. Granska rapporten.");
    expect(wrapper.text()).not.toContain("1 fråga saknar facit eller poäng.");
    expect(
      wrapper.find('[data-test="exam-converter-review-questions-action"]').exists(),
    ).toBe(false);
    expect(wrapper.find('[data-test="exam-converter-review-decision-gate"]').exists()).toBe(false);
    expect(wrapper.find('[data-test="exam-converter-accept-current-state-action"]').exists()).toBe(false);
    expect(wrapper.text()).not.toContain("Skapa filer");
    expect(wrapper.text()).not.toContain("Godkänn");
    expect(correctionSessionApiMocks.replaceExamConverterCorrectionIntents).not.toHaveBeenCalled();
    expect(gatewayMocks.applyExamAuthoringCorrections).not.toHaveBeenCalled();
  });

  it("surfaces Lucktext gaps and embedded image structure in the detail pane", async () => {
    const wrapper = mount(ExamConverterAuthenticatedView);

    await finishConversion(wrapper);
    await wrapper.find('[data-test="exam-converter-question-row-item-001"]').trigger("click");

    const detail = wrapper.find('[data-test="exam-converter-selected-question-detail"]');
    const lucktext = wrapper.find('[data-test="exam-converter-selected-question-lucktext"]');
    expect(detail.attributes("data-selected-item-id")).toBe("item-001");
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
      "Rapporten visar kvarvarande åtgärder och hur AI-förslag har hanterats.",
    );
    expect(report.text()).toContain("Facit saknas");
    expect(report.text()).toContain("Poäng saknas");
    expect(report.text()).toContain("AI-förslag");
    expect(report.text()).toContain("Kvar att granska");
    expect(report.text()).not.toContain("Konverteringsvarningar");
    expect(report.text()).not.toContain("källnoteringar");
    expect(report.text()).not.toContain("manifest");
    expect(report.text()).not.toContain("bundle");
    expect(report.text()).not.toContain("Sir Convert");

    await wrapper.find('[data-test="exam-converter-report-open-questions"]').trigger("click");
    expect(wrapper.find('[data-test="exam-converter-question-review-shell"]').exists()).toBe(
      true,
    );
  });

  it("renders AI suggestion outcomes without making source diagnostics the main signal", () => {
    const wrapper = mount(ExamConverterReportSummary, {
      props: {
        report: {
          aiSuggestionCount: 0,
          aiSuggestionOutcomes: {
            acceptedUnchangedCount: 1,
            items: [
              {
                itemId: "item-004",
                outcome: "accepted_unchanged",
                sequence: 4,
                title: "Fråga 4",
              },
              {
                itemId: "item-013",
                outcome: "teacher_edited",
                sequence: 13,
                title: "Fråga 13",
              },
              {
                itemId: "item-014",
                outcome: "suppressed",
                sequence: 14,
                title: "Fråga 14",
              },
            ],
            suppressedCount: 1,
            teacherEditedCount: 1,
            totalCount: 3,
            unresolvedCount: 0,
          },
          attentionQuestionCount: 0,
          blockedTargetFileCount: 0,
          missingAnswerKeyCount: 0,
          missingPointsCount: 0,
          warningCount: 4,
        },
      },
    });

    expect(wrapper.text()).toContain("Alla AI-förslag är hanterade.");
    expect(wrapper.text()).toContain("Accepterat");
    expect(wrapper.text()).toContain("Ändrat av lärare");
    expect(wrapper.text()).toContain("Avvisat");
    expect(wrapper.text()).not.toContain("Konverteringsvarningar");
    expect(wrapper.text()).not.toContain("källnoteringar");
  });
});
