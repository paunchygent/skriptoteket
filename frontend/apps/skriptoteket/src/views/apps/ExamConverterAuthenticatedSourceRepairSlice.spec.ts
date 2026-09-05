/** Authenticated source-repair warning rendering for the Exam Converter. */

import { mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  DIGIEXAM_ARTIFACT_ANSWER_KEY_REVIEW_STATE_REPORT,
  DIGIEXAM_ARTIFACT_IR_JSON,
  DIGIEXAM_WARNING_MISSING_PROMPT_IMAGE,
  DIGIEXAM_WARNING_MISSING_QUESTION_TITLE,
} from "../../api/examConverterContracts";
import ExamConverterAuthenticatedView from "./ExamConverterAuthenticatedView.vue";
import ExamConverterReportSummary from "./exam-converter-authenticated/ExamConverterReportSummary.vue";
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

const MISSING_TITLE_MESSAGE_QUESTION_3 =
  "Fråga 3 saknade titel. Titeln ”Question 3” lades till automatiskt. Kontrollera titeln innan du använder provet.";
const MISSING_IMAGE_MESSAGE_QUESTION_3 =
  "Bilden i fråga 3 saknas. Lägg till den innan du använder provet.";

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
  for (const mock of Object.values(correctionSessionApiMocks)) mock.mockReset();
  for (const mock of Object.values(gatewayMocks)) mock.mockReset();
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

describe("ExamConverter authenticated source-repair reporting", () => {
  it("renders AI suggestion outcomes without promoting source diagnostics", () => {
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
          missingImageCount: 0,
          missingPointsCount: 0,
          missingTitleCount: 0,
          sourceRepairQuestions: [],
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

  it("renders exact numbered repair messages beside the question and in the report", async () => {
    const baseDownload = gatewayMocks.downloadDigiExamMigrationArtifact.getMockImplementation();
    gatewayMocks.downloadDigiExamMigrationArtifact.mockImplementation(
      async (params: { artifactKey: string }) => {
        const artifact = await baseDownload?.(params);
        if (!artifact) return artifact;
        if (params.artifactKey === DIGIEXAM_ARTIFACT_IR_JSON) {
          const irJson = JSON.parse(await artifact.blob.text());
          irJson.items.splice(1, 0, {
            answer_key: { provenance: "not_applicable" },
            embedded_asset_references: [],
            embedded_assets: [],
            gaps: [],
            item_id: "item-003",
            item_type: "open_ended",
            max_score: 2,
            prompt_lines: ["Beskriv hur fotosyntesen fungerar."],
            sequence: 3,
            title: "Question 3",
            warnings: [
              {
                blocking: false,
                code: DIGIEXAM_WARNING_MISSING_QUESTION_TITLE,
                message: MISSING_TITLE_MESSAGE_QUESTION_3,
              },
              {
                blocking: false,
                code: DIGIEXAM_WARNING_MISSING_PROMPT_IMAGE,
                message: MISSING_IMAGE_MESSAGE_QUESTION_3,
              },
            ],
          });
          return artifactJsonBlob(DIGIEXAM_ARTIFACT_IR_JSON, irJson);
        }
        if (params.artifactKey === DIGIEXAM_ARTIFACT_ANSWER_KEY_REVIEW_STATE_REPORT) {
          const reviewState = JSON.parse(await artifact.blob.text());
          reviewState.items.splice(1, 0, {
            choice_ids: [],
            choice_interaction_ids: [],
            correction_affordances: [],
            current_key_origin: "none",
            gap_ids: [],
            gap_interaction_ids: [],
            item_id: "item-003",
            item_type: "open_ended",
            message_key: "exam_converter.answer_key.not_applicable",
            provenance_detail: null,
            reasons: ["answer_key_not_applicable"],
            replay_artifact_references: [],
            review_state: "review_complete",
            sequence: 3,
            source_item_fingerprint: "sha256:item-003",
          });
          return artifactJsonBlob(
            DIGIEXAM_ARTIFACT_ANSWER_KEY_REVIEW_STATE_REPORT,
            reviewState,
          );
        }
        return artifact;
      },
    );
    const wrapper = mount(ExamConverterAuthenticatedView);

    await finishConversion(wrapper);
    await wrapper.find('[data-test="exam-converter-question-row-item-003"]').trigger("click");

    const messages = wrapper.find(
      '[data-test="exam-converter-selected-question-source-repair-messages"]',
    );
    expect(messages.text()).toContain(MISSING_TITLE_MESSAGE_QUESTION_3);
    expect(messages.text()).toContain(MISSING_IMAGE_MESSAGE_QUESTION_3);

    await wrapper.find('[data-test="exam-converter-inspection-tab-report"]').trigger("click");
    const report = wrapper.find('[data-test="exam-converter-report-summary"]');
    expect(
      report.find('[data-test="exam-converter-report-missing-title-count"]').text().trim(),
    ).toBe("1");
    expect(
      report.find('[data-test="exam-converter-report-missing-image-count"]').text().trim(),
    ).toBe("1");
    const questions = wrapper.find('[data-test="exam-converter-report-source-repair-questions"]');
    expect(questions.text()).toContain("3. Question 3");
    expect(questions.text()).toContain(MISSING_TITLE_MESSAGE_QUESTION_3);
    expect(questions.text()).toContain(MISSING_IMAGE_MESSAGE_QUESTION_3);
    expect(wrapper.text()).not.toContain("Fråga N");
    expect(wrapper.text()).not.toContain("Question N");
  });
});
