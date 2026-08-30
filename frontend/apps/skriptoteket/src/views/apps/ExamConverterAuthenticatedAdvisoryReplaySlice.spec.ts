/**
 * Exam Converter advisory replay preservation behavior.
 *
 * Domain purpose:
 *   Prove correction replay for one accepted advisory answer key does not drop
 *   untouched producer-issued advisory candidates for sibling keyed items.
 *
 * Relationships:
 *   - Mounts `ExamConverterAuthenticatedView` through the authenticated review
 *     flow.
 *   - Uses compact answer-key review-state and completion-report fixtures from
 *     the local Exam Converter contract.
 *   - Guards the app/script handshake after correction-session replay.
 */

import { flushPromises, mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  DIGIEXAM_ARTIFACT_ANSWER_KEY_COMPLETION_REPORT,
  DIGIEXAM_ARTIFACT_ANSWER_KEY_REVIEW_STATE_REPORT,
} from "../../api/examConverterContracts";
import {
  ANSWER_KEY_COMPLETION_REPORT_SCHEMA_VERSION,
} from "../../api/examConverterContracts";
import ExamConverterAuthenticatedView from "./ExamConverterAuthenticatedView.vue";
import {
  correctionApplyResult,
  correctionSourceState,
  createCorrectionSessionRecorder,
} from "./examConverterAuthenticatedCorrectionSessionFixtures";
import {
  answerKeyReviewItem,
  answerKeyReviewStateReport,
  artifactJsonBlob,
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
  for (const mock of Object.values(gatewayMocks)) mock.mockReset();
  for (const mock of Object.values(correctionSessionApiMocks)) mock.mockReset();
  gatewayMocks.submitDigiExamMigration.mockResolvedValue(submittedJob("succeeded"));
  gatewayMocks.getDigiExamMigrationResult.mockResolvedValue(terminalResult());
  gatewayMocks.issueExamAuthoringCorrectionSourceState.mockResolvedValue(correctionSourceState());
  gatewayMocks.applyExamAuthoringCorrections.mockResolvedValue(preservedSiblingReplayResult());
  gatewayMocks.replayLocalExamConversion.mockResolvedValue({});
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
  mockTwoPendingChoiceCandidates();
});

function advisoryCandidateReportItem(params: {
  correctAlternativeIds: number[];
  itemId: string;
  itemType: string;
  sequence: number;
}) {
  return {
    answer_payload: {
      correct_alternative_ids: params.correctAlternativeIds,
      kind: "choice",
    },
    backend_failure_code: null,
    backend_status: "ok",
    candidate_id: `candidate-${params.itemId}`,
    candidate_payload_digest: `sha256:candidate-${params.itemId}`,
    decision_state: "suggested",
    item_id: params.itemId,
    item_type: params.itemType,
    model_profile: "local",
    prompt_template_version: "digiexam-choice-answer-key-v1",
    provider_profile_id: "task309-llama-cpp",
    schema_name: "digiexam_choice_answer_key_decision_v1",
    schema_version: "digiexam_choice_answer_key_decision_v1",
    sequence: params.sequence,
    validation_state: "valid",
  };
}

function pendingAdvisoryReviewItem(params: {
  choiceIds: string[];
  interactionId: string;
  itemId: string;
  itemType: string;
  sequence: number;
}) {
  return answerKeyReviewItem({
    choice_ids: params.choiceIds,
    choice_interaction_ids: [params.interactionId],
    correction_affordances: ["manual_choice_answer_key"],
    current_key_origin: "none",
    item_id: params.itemId,
    item_type: params.itemType,
    message_key: "exam_converter.answer_key.advisory_candidate_pending",
    provenance_detail: {
      candidate_id: `candidate-${params.itemId}`,
      candidate_payload_digest: `sha256:candidate-${params.itemId}`,
      prompt_template_version: "digiexam-choice-answer-key-v1",
      provider_profile_id: "task309-llama-cpp",
      schema_name: "digiexam_choice_answer_key_decision_v1",
      schema_version: "digiexam_choice_answer_key_decision_v1",
      validation_state: "valid",
    },
    reasons: ["advisory_candidate_pending"],
    review_state: "review_required",
    sequence: params.sequence,
    source_item_fingerprint: `sha256:${params.itemId}`,
  });
}

function reviewedAdvisoryReviewItem(params: {
  choiceIds: string[];
  interactionId: string;
  itemId: string;
  itemType: string;
  sequence: number;
}) {
  return answerKeyReviewItem({
    choice_ids: params.choiceIds,
    choice_interaction_ids: [params.interactionId],
    current_key_origin: "reviewed_advisory",
    item_id: params.itemId,
    item_type: params.itemType,
    message_key: "exam_converter.answer_key.reviewed_advisory_accepted",
    reasons: ["reviewed_advisory_accepted"],
    review_state: "review_complete",
    sequence: params.sequence,
    source_item_fingerprint: `sha256:${params.itemId}`,
  });
}

function hasPersistedAnswerKeyIntent(itemId: string): boolean {
  return correctionSessionRecorder.current().active_intents.some(
    (intent) => intent.item_id === itemId,
  );
}

function mockTwoPendingChoiceCandidates(): void {
  const baseDownload = gatewayMocks.downloadDigiExamMigrationArtifact.getMockImplementation();
  if (!baseDownload) {
    throw new Error("Review artifacts must be mocked before advisory replay fixtures.");
  }
  gatewayMocks.downloadDigiExamMigrationArtifact.mockImplementation(
    (params: { artifactKey: string }) => {
      if (params.artifactKey === DIGIEXAM_ARTIFACT_ANSWER_KEY_COMPLETION_REPORT) {
        return Promise.resolve(
          artifactJsonBlob(DIGIEXAM_ARTIFACT_ANSWER_KEY_COMPLETION_REPORT, {
            completion_mode: "local_llm_suggest_missing_machine_marked",
            items: [
              advisoryCandidateReportItem({
                correctAlternativeIds: [3],
                itemId: "item-004",
                itemType: "single_choice",
                sequence: 4,
              }),
              advisoryCandidateReportItem({
                correctAlternativeIds: [1, 2],
                itemId: "item-005",
                itemType: "multiple_response",
                sequence: 5,
              }),
            ],
            job_id: "job_exam_converter_review",
            schema_version: ANSWER_KEY_COMPLETION_REPORT_SCHEMA_VERSION,
          }),
        );
      }
      if (params.artifactKey === DIGIEXAM_ARTIFACT_ANSWER_KEY_REVIEW_STATE_REPORT) {
        const reviewItem = hasPersistedAnswerKeyIntent("item-004")
          ? reviewedAdvisoryReviewItem({
              choiceIds: ["choice-3"],
              interactionId: "choice-item-004",
              itemId: "item-004",
              itemType: "single_choice",
              sequence: 4,
            })
          : pendingAdvisoryReviewItem({
              choiceIds: ["choice-3"],
              interactionId: "choice-item-004",
              itemId: "item-004",
              itemType: "single_choice",
              sequence: 4,
            });
        const siblingReviewItem = hasPersistedAnswerKeyIntent("item-005")
          ? reviewedAdvisoryReviewItem({
              choiceIds: ["choice-1", "choice-2"],
              interactionId: "choice-item-005",
              itemId: "item-005",
              itemType: "multiple_response",
              sequence: 5,
            })
          : pendingAdvisoryReviewItem({
              choiceIds: ["choice-1", "choice-2"],
              interactionId: "choice-item-005",
              itemId: "item-005",
              itemType: "multiple_response",
              sequence: 5,
            });
        return Promise.resolve(
          artifactJsonBlob(
            DIGIEXAM_ARTIFACT_ANSWER_KEY_REVIEW_STATE_REPORT,
            answerKeyReviewStateReport([
              answerKeyReviewItem(),
              reviewItem,
              siblingReviewItem,
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
          ),
        );
      }
      return baseDownload(params);
    },
  );
}

function preservedSiblingReplayResult() {
  const replay = correctionApplyResult();
  const acceptedItem = replay.effective_state.items.find((item) => item.item_id === "item-004");
  return {
    ...replay,
    answer_key_review_state: answerKeyReviewStateReport([
      answerKeyReviewItem(),
      answerKeyReviewItem({
        choice_ids: ["choice-3"],
        choice_interaction_ids: ["choice-item-004"],
        current_key_origin: "reviewed_advisory",
        item_id: "item-004",
        item_type: "single_choice",
        message_key: "exam_converter.answer_key.reviewed_advisory_accepted",
        reasons: ["reviewed_advisory_accepted"],
        review_state: "review_complete",
        sequence: 4,
        source_item_fingerprint: "sha256:item-004",
      }),
      answerKeyReviewItem({
        choice_ids: ["choice-1", "choice-2"],
        choice_interaction_ids: ["choice-item-005"],
        correction_affordances: ["manual_choice_answer_key"],
        current_key_origin: "none",
        item_id: "item-005",
        item_type: "multiple_response",
        message_key: "exam_converter.answer_key.advisory_candidate_pending",
        provenance_detail: {
          candidate_id: "candidate-item-005",
          candidate_payload_digest: "sha256:candidate-item-005",
          prompt_template_version: "digiexam-choice-answer-key-v1",
          provider_profile_id: "task309-llama-cpp",
          schema_name: "digiexam_choice_answer_key_decision_v1",
          schema_version: "digiexam_choice_answer_key_decision_v1",
          validation_state: "valid",
        },
        reasons: ["advisory_candidate_pending"],
        review_state: "review_required",
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
    effective_state: {
      ...replay.effective_state,
      items: acceptedItem ? [acceptedItem] : [],
    },
  };
}

function lossySiblingReplayResult() {
  const replay = preservedSiblingReplayResult();
  return {
    ...replay,
    answer_key_review_state: {
      ...replay.answer_key_review_state,
      items: replay.answer_key_review_state.items.map((item) =>
        item.item_id === "item-005"
          ? answerKeyReviewItem({
              choice_ids: [],
              choice_interaction_ids: ["choice-item-005"],
              correction_affordances: ["manual_choice_answer_key"],
              current_key_origin: "none",
              item_id: "item-005",
              item_type: "multiple_response",
              message_key: "exam_converter.answer_key.manual_required",
              reasons: ["no_correct_choice_selected"],
              review_state: "validation_required",
              sequence: 5,
              source_item_fingerprint: "sha256:item-005",
            })
          : item,
      ),
    },
  };
}

describe("ExamConverterAuthenticatedView advisory replay preservation", () => {
  it("opens the first unresolved review and advances after each persisted decision", async () => {
    const wrapper = mount(ExamConverterAuthenticatedView);

    await finishConversion(wrapper);
    await wrapper.get('[data-test="exam-converter-open-ai-prefill-action"]').trigger("click");

    const questionShell = wrapper.get('[data-test="exam-converter-question-review-shell"]');
    expect(questionShell.classes()).toContain("is-compact-detail-open");
    expect(wrapper.get('[data-test="exam-converter-selected-question-detail"]')
      .attributes("data-selected-item-id")).toBe("item-004");

    await wrapper.get('[data-test="exam-converter-accept-advisory-answer-key-action"]')
      .trigger("click");
    await flushPromises();

    expect(questionShell.classes()).toContain("is-compact-detail-open");
    expect(wrapper.get('[data-test="exam-converter-selected-question-detail"]')
      .attributes("data-selected-item-id")).toBe("item-005");

    await wrapper.get('[data-test="exam-converter-edit-advisory-answer-key-action"]')
      .trigger("click");
    await wrapper.get('[data-test="exam-converter-apply-manual-answer-key-action"]')
      .trigger("click");
    await flushPromises();

    expect(correctionSessionApiMocks.upsertExamConverterCorrectionIntent).toHaveBeenCalledTimes(2);
    expect(gatewayMocks.replayLocalExamConversion).toHaveBeenCalledTimes(2);
    expect(wrapper.get('[data-test="exam-converter-question-review-shell"]').classes())
      .not.toContain("is-compact-detail-open");
  });

  it("renders untouched sibling AI suggestions when correction replay preserves them", async () => {
    const wrapper = mount(ExamConverterAuthenticatedView);

    await finishConversion(wrapper);
    expect(wrapper.find('[data-test="exam-converter-question-row-item-004"]').text()).toContain(
      "Granska",
    );
    expect(wrapper.find('[data-test="exam-converter-question-row-item-005"]').text()).toContain(
      "Granska",
    );

    await wrapper.find('[data-test="exam-converter-question-row-item-004"]').trigger("click");
    await wrapper
      .find('[data-test="exam-converter-accept-advisory-answer-key-action"]')
      .trigger("click");
    await flushPromises();

    const siblingRow = wrapper.find('[data-test="exam-converter-question-row-item-005"]');
    expect(siblingRow.text()).toContain("Granska");
    expect(siblingRow.text()).not.toContain("Kontrollera");
    expect(siblingRow.text()).not.toContain("Välj minst ett rätt svar");
    expect(siblingRow.find(".lucide-sparkles").exists()).toBe(true);

    expect(correctionSessionApiMocks.upsertExamConverterCorrectionIntent).toHaveBeenCalledTimes(1);
    expect(gatewayMocks.replayLocalExamConversion).toHaveBeenCalledTimes(1);
  });

  it("does not infer a pending sibling suggestion when producer replay returns validation", async () => {
    gatewayMocks.applyExamAuthoringCorrections.mockResolvedValueOnce(lossySiblingReplayResult());
    const wrapper = mount(ExamConverterAuthenticatedView);

    await finishConversion(wrapper);
    await wrapper.find('[data-test="exam-converter-question-row-item-004"]').trigger("click");
    await wrapper
      .find('[data-test="exam-converter-accept-advisory-answer-key-action"]')
      .trigger("click");
    await flushPromises();

    expect(correctionSessionApiMocks.upsertExamConverterCorrectionIntent).toHaveBeenCalledTimes(1);
    expect(gatewayMocks.replayLocalExamConversion).toHaveBeenCalledTimes(1);
  });
});
