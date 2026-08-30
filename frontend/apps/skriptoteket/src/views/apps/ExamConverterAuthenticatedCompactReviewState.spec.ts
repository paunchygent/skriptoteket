/**
 * Exam Converter compact review-state UI behavior.
 *
 * Slice purpose:
 *   Prove PR-0406 renders producer-backed answer-key review state across the
 *   authenticated desktop and small-screen inspection surfaces.
 *
 * Expected behavior:
 *   Question rows use compact labels and approved symbols, files/report remain
 *   separate inspection surfaces, and file actions stay disabled until replay
 *   artifact references authorize them.
 *
 * Recommended implementation shape:
 *   Consume `answer_key_review_state_report` for first-pass review and top
 *   level `answer_key_review_state` from correction apply before rendering.
 */

import { flushPromises, mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import ExamConverterAuthenticatedView from "./ExamConverterAuthenticatedView.vue";
import {
  correctionApplyResult,
  correctionSourceState,
  createCorrectionSessionRecorder,
} from "./examConverterAuthenticatedCorrectionSessionFixtures";
import {
  answerKeyReviewItem,
  answerKeyReviewStateReport,
  finishConversion,
  mockReviewArtifacts,
  submittedJob,
  terminalResult,
} from "./examConverterAuthenticatedReviewFixtures";

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
vi.mock("../../api/examConverterLocal", () => ({
  downloadLocalExamConversionArtifact: gatewayMocks.downloadDigiExamMigrationArtifact,
  getLocalExamConversionJob: gatewayMocks.getDigiExamMigrationJob,
  getLocalExamConversionResult: gatewayMocks.getDigiExamMigrationResult,
  getLocalExamConversionSourceState: gatewayMocks.issueExamAuthoringCorrectionSourceState,
  listLocalExamConversionArtifacts: gatewayMocks.listDigiExamMigrationArtifacts,
  replayLocalExamConversion: vi.fn(),
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
  for (const mock of Object.values(gatewayMocks)) mock.mockReset();
  for (const mock of Object.values(correctionSessionApiMocks)) mock.mockReset();
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

describe("ExamConverterAuthenticatedView compact review state", () => {
  it("renders first-pass producer review labels with approved symbols and result-band copy", async () => {
    const wrapper = mount(ExamConverterAuthenticatedView);

    await finishConversion(wrapper);

    expect(gatewayMocks.downloadDigiExamMigrationArtifact).toHaveBeenCalledWith({
      artifactKey: "answer_key_review_state_report",
      correlationId: "corr_exam_converter_review",
      jobId: "job_exam_converter_review",
    });
    expect(wrapper.text()).toContain("Föreslagna facit");
    expect(wrapper.text()).toContain("Granska");
    expect(wrapper.text()).toContain("1 att granska.");
    const reviewBand = wrapper.find('[data-test="exam-converter-ai-prefill-panel"]');
    expect(reviewBand.findComponent({ name: "IconAi" }).exists()).toBe(true);
    expect(reviewBand.findAll(".lucide-bot")).toHaveLength(0);
    const questionRows = wrapper.find('[data-test="exam-converter-question-review-shell"]');
    expect(questionRows.text()).toContain("Förslag");
    expect(questionRows.text()).toContain("Klart");
    expect(questionRows.text()).toContain("Ändrat");
    expect(questionRows.findAllComponents({ name: "IconAi" }).length).toBeGreaterThan(0);
    expect(questionRows.findAllComponents({ name: "IconCheck" }).length).toBeGreaterThan(0);
    expect(questionRows.findAllComponents({ name: "IconEdit" }).length).toBeGreaterThan(0);
    expect(questionRows.findAll(".lucide-circle-check")).toHaveLength(0);
    expect(questionRows.findAll(".lucide-circle-x")).toHaveLength(0);
  });

  it("keeps files and report as separate surfaces without selected-question detail", async () => {
    const wrapper = mount(ExamConverterAuthenticatedView);

    await finishConversion(wrapper);
    await wrapper.find('[data-test="exam-converter-question-row-item-001"]').trigger("click");
    expect(wrapper.find('[data-test="exam-converter-selected-question-detail"]').exists()).toBe(true);

    await wrapper.find('[data-test="exam-converter-inspection-tab-files"]').trigger("click");
    expect(wrapper.find('[data-test="exam-converter-files-readiness-list"]').exists()).toBe(true);
    expect(wrapper.find('[data-test="exam-converter-selected-question-detail"]').exists()).toBe(false);

    await wrapper.find('[data-test="exam-converter-inspection-tab-report"]').trigger("click");
    expect(wrapper.find('[data-test="exam-converter-report-summary"]').exists()).toBe(true);
    expect(wrapper.find('[data-test="exam-converter-selected-question-detail"]').exists()).toBe(false);
  });

  it("does not unlock file actions from local saved intent before fresh replay artifacts", async () => {
    gatewayMocks.applyExamAuthoringCorrections.mockResolvedValueOnce({
      ...correctionApplyResult(),
      answer_key_review_state: answerKeyReviewStateReport([
        answerKeyReviewItem(),
        answerKeyReviewItem({
          choice_ids: ["choice-3"],
          choice_interaction_ids: ["choice-item-004"],
          correction_affordances: ["manual_choice_answer_key"],
          current_key_origin: "teacher_authored",
          item_id: "item-004",
          item_type: "single_choice",
          message_key: "exam_converter.answer_key.teacher_answer_key_present",
          reasons: ["teacher_answer_key_present", "replay_artifact_unavailable"],
          replay_artifact_references: [],
          review_state: "teacher_modified",
          sequence: 4,
          source_item_fingerprint: "sha256:item-004",
        }),
        answerKeyReviewItem({
          choice_ids: ["choice-1", "choice-2"],
          choice_interaction_ids: ["choice-item-005"],
          current_key_origin: "reviewed_advisory",
          item_id: "item-005",
          item_type: "multiple_response",
          message_key: "exam_converter.answer_key.reviewed_advisory_accepted",
          reasons: ["reviewed_advisory_accepted"],
          review_state: "review_complete",
          sequence: 5,
          source_item_fingerprint: "sha256:item-005",
        }),
        answerKeyReviewItem({
          current_key_origin: "none",
          item_id: "item-006",
          item_type: "open_ended",
          message_key: "exam_converter.answer_key.source_present",
          reasons: ["source_answer_key_present"],
          review_state: "review_complete",
          sequence: 6,
          source_item_fingerprint: "sha256:item-006",
        }),
        answerKeyReviewItem({
          current_key_origin: "teacher_edited_advisory",
          item_id: "item-012",
          item_type: "open_ended",
          message_key: "exam_converter.answer_key.teacher_modified",
          reasons: ["teacher_edited_advisory_candidate"],
          review_state: "teacher_modified",
          sequence: 12,
          source_item_fingerprint: "sha256:item-012",
        }),
        answerKeyReviewItem({
          current_key_origin: "none",
          item_id: "item-013",
          item_type: "open_ended",
          message_key: "exam_converter.answer_key.source_present",
          reasons: ["source_answer_key_present"],
          review_state: "review_complete",
          sequence: 13,
          source_item_fingerprint: "sha256:item-013",
        }),
      ]),
      artifact_availability: [
        { artifact_key: "examnet_pdf", availability: "unavailable", unavailable_code: "replay_artifact_unavailable" },
        { artifact_key: "qti_package", availability: "unavailable", unavailable_code: "replay_artifact_unavailable" },
      ],
      target_readiness: {
        schema_version: "target_readiness_report_v1",
        targets: [],
      },
    });
    const wrapper = mount(ExamConverterAuthenticatedView);

    await finishConversion(wrapper);
    await wrapper.find('[data-test="exam-converter-question-row-item-004"]').trigger("click");
    await wrapper.find('[data-test="exam-converter-edit-advisory-answer-key-action"]').trigger("click");
    await wrapper.find('[data-test="exam-converter-advisory-edit-choice-3"]').trigger("click");
    await wrapper.find('[data-test="exam-converter-save-advisory-answer-key-action"]').trigger("click");
    await flushPromises();
    await wrapper.find('[data-test="exam-converter-inspection-tab-files"]').trigger("click");

    expect(wrapper.text()).toContain("Granska facit först");
    expect(
      wrapper.find('[data-test="exam-converter-download-file-examnet_pdf"]').attributes("disabled"),
    ).toBeDefined();
    expect(
      wrapper.find('[data-test="exam-converter-save-file-examnet_pdf"]').attributes("disabled"),
    ).toBeDefined();
  });
});
