/**
 * Exam Converter AI-prefill durable-session behavior.
 *
 * Domain purpose:
 *   Prove AI-prefilled editor values become persisted correction-session
 *   intents and are replayed before the UI exposes updated question/file truth.
 *
 * Relationships:
 *   - Complements the general authenticated review shell spec.
 *   - Uses the shared correction-session fixtures for source-bound replay.
 */

import { flushPromises, mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  correctionApplyResult,
  correctionSourceState,
  createCorrectionSessionRecorder,
} from "./examConverterAuthenticatedCorrectionSessionFixtures";
import { mockVisionBackedGapFillReviewArtifacts } from "./examConverterAuthenticatedGapFillReviewFixtures";
import {
  answerKeyReviewItem,
  answerKeyReviewStateReport,
  finishConversion,
  mockReviewArtifacts,
  submittedJob,
  terminalResult,
} from "./examConverterAuthenticatedReviewFixtures";
import ExamConverterAuthenticatedView from "./ExamConverterAuthenticatedView.vue";

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
  correctionSessionApiMocks.upsertExamConverterCorrectionIntent.mockImplementation(
    ({ request }: { request: { intent: Record<string, unknown> } }) =>
      Promise.resolve(correctionSessionRecorder.recordIntent(request.intent)),
  );
  correctionSessionApiMocks.getExamConverterCorrectionSession.mockImplementation(() =>
    Promise.resolve(correctionSessionRecorder.current()),
  );
  mockReviewArtifacts(gatewayMocks);
});

async function leaveAndReturnToQuestion(
  wrapper: ReturnType<typeof mount>,
  itemId: string,
): Promise<void> {
  const rowPrefix = "exam-converter-question-row-";
  const otherRow = wrapper
    .findAll(`[data-test^="${rowPrefix}"]`)
    .find((row) => row.attributes("data-test") !== `${rowPrefix}${itemId}`);
  if (otherRow) {
    await otherRow.trigger("click");
  }
  await wrapper.find(`[data-test="${rowPrefix}${itemId}"]`).trigger("click");
}

describe("ExamConverterAuthenticatedView AI-prefill durable sessions", () => {
  it("opens the first question with an AI-suggested facit from the top review button", async () => {
    const wrapper = mount(ExamConverterAuthenticatedView);

    await finishConversion(wrapper);
    await wrapper.find('[data-test="exam-converter-question-row-item-012"]').trigger("click");
    expect(
      wrapper.find<HTMLInputElement>('[data-test="exam-converter-item-title-patch-input"]')
        .element.value,
    ).toBe("Resonera om lösningsmetod");

    await wrapper.find('[data-test="exam-converter-open-ai-prefill-action"]').trigger("click");
    await wrapper.vm.$nextTick();

    expect(
      wrapper.find<HTMLInputElement>('[data-test="exam-converter-item-title-patch-input"]')
        .element.value,
    ).toBe("Fråga 4");
    expect(
      wrapper.find('[data-test="exam-converter-selected-question-ai-suggestion"]').exists(),
    ).toBe(true);
    expect(wrapper.find('[data-test="exam-converter-manual-answer-key-editor"]').exists()).toBe(
      false,
    );
  });

  it("keeps teacher edits to accepted suggestions instead of returning to the original AI choice", async () => {
    const wrapper = mount(ExamConverterAuthenticatedView);

    await finishConversion(wrapper);
    await wrapper.find('[data-test="exam-converter-question-row-item-004"]').trigger("click");

    await wrapper
      .find('[data-test="exam-converter-edit-advisory-answer-key-action"]')
      .trigger("click");
    expect(
      wrapper.find('[data-test="exam-converter-manual-choice-3"]').attributes("aria-pressed"),
    ).toBe("true");

    await wrapper.find('[data-test="exam-converter-manual-choice-2"]').trigger("click");
    await wrapper
      .find('[data-test="exam-converter-apply-manual-answer-key-action"]')
      .trigger("click");
    await flushPromises();

    expect(correctionSessionApiMocks.upsertExamConverterCorrectionIntent).toHaveBeenLastCalledWith(
      expect.objectContaining({
        request: expect.objectContaining({
          intent: expect.objectContaining({
            item_id: "item-004",
            kind: "manual_choice_answer_key",
            payload: expect.objectContaining({
              correct_choice_ids: ["choice-2"],
              submission_origin: "teacher_edited_advisory_candidate",
            }),
          }),
        }),
      }),
    );
    await wrapper.find('[data-test="exam-converter-question-row-item-004"]').trigger("click");
    expect(
      wrapper.find('[data-test="exam-converter-effective-answer-key-summary"]').text(),
    ).toContain("2");
    expect(
      wrapper.find('[data-test="exam-converter-effective-answer-key-choice-2"]').text(),
    ).toContain("Växter omvandlar solljus till socker.");
    expect(
      wrapper
        .find('[data-test="exam-converter-effective-answer-key-teacher-symbol"]')
        .exists(),
    ).toBe(true);
    expect(
      wrapper.find('[data-test="exam-converter-effective-answer-key-ai-symbol"]').exists(),
    ).toBe(false);
    expect(
      wrapper.find('[data-test="exam-converter-effective-answer-key-summary"]').text(),
    ).not.toContain("3");

    await leaveAndReturnToQuestion(wrapper, "item-004");
    expect(
      wrapper.find('[data-test="exam-converter-effective-answer-key-summary"]').text(),
    ).toContain("2");

    await wrapper.find('[data-test="exam-converter-inspection-tab-report"]').trigger("click");
    const report = wrapper.find('[data-test="exam-converter-report-summary"]');
    expect(report.text()).toContain("AI-förslag");
    expect(report.text()).toContain("Ändrat av lärare");
    expect(report.text()).toContain("Alla AI-förslag är hanterade.");
  });

  it("keeps edited AI choices when the teacher edits before saving", async () => {
    const wrapper = mount(ExamConverterAuthenticatedView);

    await finishConversion(wrapper);
    await wrapper.find('[data-test="exam-converter-question-row-item-004"]').trigger("click");
    expect(
      wrapper.find('[data-test="exam-converter-selected-question-ai-suggestion"]').exists(),
    ).toBe(true);
    expect(
      wrapper.find('[data-test="exam-converter-manual-answer-key-editor"]').exists(),
    ).toBe(false);
    await wrapper
      .find('[data-test="exam-converter-edit-advisory-answer-key-action"]')
      .trigger("click");
    await wrapper.find('[data-test="exam-converter-manual-choice-2"]').trigger("click");
    await wrapper
      .find('[data-test="exam-converter-apply-manual-answer-key-action"]')
      .trigger("click");
    await flushPromises();

    expect(correctionSessionApiMocks.upsertExamConverterCorrectionIntent).toHaveBeenLastCalledWith(
      expect.objectContaining({
        request: expect.objectContaining({
          intent: expect.objectContaining({
            item_id: "item-004",
            kind: "manual_choice_answer_key",
            payload: expect.objectContaining({
              correct_choice_ids: ["choice-2"],
              submission_origin: "teacher_edited_advisory_candidate",
            }),
          }),
        }),
      }),
    );
    await wrapper.find('[data-test="exam-converter-question-row-item-004"]').trigger("click");
    expect(
      wrapper.find('[data-test="exam-converter-effective-answer-key-summary"]').text(),
    ).toContain("2");
    expect(
      wrapper.find('[data-test="exam-converter-effective-answer-key-choice-2"]').text(),
    ).toContain("Växter omvandlar solljus till socker.");
  });

  it("keeps other question editors usable after saving an AI-seeded facit edit", async () => {
    const wrapper = mount(ExamConverterAuthenticatedView);

    await finishConversion(wrapper);
    await wrapper.find('[data-test="exam-converter-question-row-item-004"]').trigger("click");
    await wrapper
      .find('[data-test="exam-converter-edit-advisory-answer-key-action"]')
      .trigger("click");
    await wrapper.find('[data-test="exam-converter-manual-choice-2"]').trigger("click");
    await wrapper
      .find('[data-test="exam-converter-apply-manual-answer-key-action"]')
      .trigger("click");
    await flushPromises();
    await wrapper.find('[data-test="exam-converter-question-row-item-004"]').trigger("click");

    expect(
      wrapper.find('[data-test="exam-converter-apply-manual-answer-key-action"]').attributes(
        "disabled",
      ),
    ).toBeUndefined();
  });

  it("does not expose destructive facit removal in the question editor", async () => {
    const wrapper = mount(ExamConverterAuthenticatedView);

    await finishConversion(wrapper);
    await wrapper.find('[data-test="exam-converter-question-row-item-004"]').trigger("click");
    await wrapper
      .find('[data-test="exam-converter-accept-advisory-answer-key-action"]')
      .trigger("click");
    await flushPromises();
    await wrapper.find('[data-test="exam-converter-question-row-item-004"]').trigger("click");

    expect(wrapper.find('[data-test="exam-converter-effective-answer-key-summary"]').text()).toContain(
      "3",
    );
    expect(
      wrapper.find('[data-test="exam-converter-revert-answer-key-action"]').exists(),
    ).toBe(false);
  });

  it("persists unchanged AI-prefilled choice facit with advisory candidate provenance", async () => {
    gatewayMocks.applyExamAuthoringCorrections.mockResolvedValueOnce({
      ...correctionApplyResult(),
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
    });
    const wrapper = mount(ExamConverterAuthenticatedView);

    await finishConversion(wrapper);
    await wrapper.find('[data-test="exam-converter-question-row-item-004"]').trigger("click");
    await wrapper
      .find('[data-test="exam-converter-accept-advisory-answer-key-action"]')
      .trigger("click");
    await flushPromises();

    expect(wrapper.text()).not.toContain("Kontrollera frågorna innan du sparar eller hämtar filer.");
    expect(gatewayMocks.submitDigiExamMigration).toHaveBeenCalledTimes(1);
    expect(correctionSessionApiMocks.upsertExamConverterCorrectionIntent).toHaveBeenLastCalledWith(
      expect.objectContaining({
        request: expect.objectContaining({
          intent: expect.objectContaining({
            item_id: "item-004",
            kind: "manual_choice_answer_key",
            payload: expect.objectContaining({
              candidate_lineage: expect.objectContaining({
                candidate_id: "candidate-item-004",
                completion_report_sha256: "sha256:completion-report",
                validation_state: "valid",
              }),
              correct_choice_ids: ["choice-3"],
              submission_origin: "accepted_advisory_candidate",
            }),
          }),
        }),
      }),
    );
    await wrapper.find('[data-test="exam-converter-inspection-tab-questions"]').trigger("click");
    await wrapper.find('[data-test="exam-converter-question-row-item-004"]').trigger("click");
    expect(
      wrapper.find('[data-test="exam-converter-effective-answer-key-summary"]').text(),
    ).toContain("3");
    expect(
      wrapper.find('[data-test="exam-converter-effective-answer-key-ai-symbol"]').exists(),
    ).toBe(false);
    expect(
      wrapper
        .find('[data-test="exam-converter-effective-answer-key-teacher-symbol"]')
        .exists(),
    ).toBe(true);
    expect(
      wrapper
        .find('[data-test="exam-converter-question-row-item-004"] [aria-label="Klart"]')
        .exists(),
    ).toBe(true);
    expect(
      wrapper.findAll('[data-test="exam-converter-manual-choice-ai-symbol"]'),
    ).toHaveLength(0);
    await wrapper.find('[data-test="exam-converter-inspection-tab-report"]').trigger("click");
    const report = wrapper.find('[data-test="exam-converter-report-summary"]');
    expect(report.text()).toContain("AI-förslag");
    expect(report.text()).toContain("Accepterat");
    expect(report.text()).toContain("Alla AI-förslag är hanterade.");
    expect(gatewayMocks.applyExamAuthoringCorrections).toHaveBeenLastCalledWith(
      expect.objectContaining({
        request: expect.objectContaining({
          corrections: [
            expect.objectContaining({
              candidate_lineage: expect.objectContaining({ candidate_id: "candidate-item-004" }),
              correct_choice_ids: ["choice-3"],
              item_id: "item-004",
              kind: "manual_choice_answer_key",
            }),
          ],
        }),
      }),
    );
  });

  it("replays a saved vision-backed Lucktext AI-facit before files are available", async () => {
    mockVisionBackedGapFillReviewArtifacts(gatewayMocks);
    const wrapper = mount(ExamConverterAuthenticatedView);

    await finishConversion(wrapper);
    const gapFillRow = wrapper.find('[data-test="exam-converter-question-row-item-013"]');
    expect(gapFillRow.text()).toContain("Lucktext");
    expect(gapFillRow.text()).toContain("Granska");
    expect(gapFillRow.text()).not.toContain("Frågetypen behöver kontrolleras");
    expect(gapFillRow.find(".lucide-sparkles").exists()).toBe(true);
    await gapFillRow.trigger("click");
    expect(
      wrapper.find('[data-test="exam-converter-selected-question-ai-suggestion"]').text(),
    ).toContain("kretslopp");

    await wrapper
      .find('[data-test="exam-converter-accept-advisory-answer-key-action"]')
      .trigger("click");
    await flushPromises();

    expect(gatewayMocks.submitDigiExamMigration).toHaveBeenCalledTimes(1);
    expect(correctionSessionApiMocks.upsertExamConverterCorrectionIntent).toHaveBeenLastCalledWith(
      expect.objectContaining({
        request: expect.objectContaining({
          intent: expect.objectContaining({
            item_id: "item-013",
            kind: "manual_gap_open_cloze_answer_key",
            payload: expect.objectContaining({
              candidate_lineage: expect.objectContaining({
                candidate_id: "candidate-item-013",
                candidate_payload_digest: "sha256:candidate-item-013",
                completion_report_sha256: "sha256:completion-report-gap",
                provider_profile_id: "task309-llama-cpp",
                schema_name: "digiexam_gap_fill_answer_key_decision_v1",
                validation_state: "valid",
              }),
              gap_answers: [
                { accepted_values: ["kretslopp"], gap_id: "gap-001" },
                { accepted_values: ["näringsväv"], gap_id: "gap-002" },
              ],
              submission_origin: "accepted_advisory_candidate",
            }),
          }),
        }),
      }),
    );
    expect(wrapper.text()).toContain("Filer (2)");
    await wrapper.find('[data-test="exam-converter-inspection-tab-files"]').trigger("click");
    expect(wrapper.text()).toContain("Filer kunde inte skapas");
    expect(
      wrapper.find('[data-test="exam-converter-download-file-examnet_pdf"]').attributes(
        "disabled",
      ),
    ).toBeDefined();
    await wrapper.find('[data-test="exam-converter-inspection-tab-questions"]').trigger("click");
    expect(wrapper.find('[data-test="exam-converter-question-row-item-013"]').text()).not.toContain(
      "Facit",
    );
  });

  it("keeps edited Lucktext AI answers when the teacher edits before saving", async () => {
    mockVisionBackedGapFillReviewArtifacts(gatewayMocks);
    const wrapper = mount(ExamConverterAuthenticatedView);

    await finishConversion(wrapper);
    await wrapper.find('[data-test="exam-converter-question-row-item-013"]').trigger("click");
    await wrapper
      .find('[data-test="exam-converter-edit-advisory-answer-key-action"]')
      .trigger("click");
    await wrapper
      .find<HTMLInputElement>('[data-test="exam-converter-manual-gap-gap-001"]')
      .setValue("kolets kretslopp");
    await wrapper
      .find<HTMLInputElement>('[data-test="exam-converter-manual-gap-gap-002"]')
      .setValue("fotosyntes");
    await wrapper
      .find('[data-test="exam-converter-apply-manual-answer-key-action"]')
      .trigger("click");
    await flushPromises();

    expect(correctionSessionApiMocks.upsertExamConverterCorrectionIntent).toHaveBeenLastCalledWith(
      expect.objectContaining({
        request: expect.objectContaining({
          intent: expect.objectContaining({
            item_id: "item-013",
            kind: "manual_gap_open_cloze_answer_key",
            payload: expect.objectContaining({
              gap_answers: [
                { accepted_values: ["kolets kretslopp"], gap_id: "gap-001" },
                { accepted_values: ["fotosyntes"], gap_id: "gap-002" },
              ],
              submission_origin: "teacher_edited_advisory_candidate",
            }),
          }),
        }),
      }),
    );
    await wrapper.find('[data-test="exam-converter-question-row-item-013"]').trigger("click");
    expect(wrapper.find('[data-test="exam-converter-effective-gap-answer-gap-001"]').text()).toContain(
      "kolets kretslopp",
    );
    expect(wrapper.find('[data-test="exam-converter-effective-gap-answer-gap-002"]').text()).toContain(
      "fotosyntes",
    );
  });

  it("shows pending advisory acceptance before the normal answer-key editor", async () => {
    const wrapper = mount(ExamConverterAuthenticatedView);

    await finishConversion(wrapper);
    await wrapper.find('[data-test="exam-converter-question-row-item-004"]').trigger("click");
    expect(
      wrapper.find('[data-test="exam-converter-selected-question-ai-suggestion"]').exists(),
    ).toBe(true);
    expect(
      wrapper.find('[data-test="exam-converter-selected-question-ai-suggestion"]').text(),
    ).toContain("Tidigare förslag");
    expect(
      wrapper.find('[data-test="exam-converter-accept-advisory-answer-key-action"]').text(),
    ).toContain("Acceptera");
    expect(
      wrapper
        .find('[data-test="exam-converter-accept-advisory-answer-key-action"]')
        .classes(),
    ).toEqual(expect.arrayContaining(["border-action", "bg-action", "text-panel"]));
    expect(
      wrapper
        .find('[data-test="exam-converter-accept-advisory-answer-key-action"]')
        .classes(),
    ).not.toContain("btn-primary");
    expect(
      wrapper.find('[data-test="exam-converter-edit-advisory-answer-key-action"]').text(),
    ).toContain("Ändra");
    expect(
      wrapper.find('[data-test="exam-converter-edit-advisory-answer-key-action"] svg').exists(),
    ).toBe(false);
    expect(wrapper.find('[data-test="exam-converter-manual-answer-key-editor"]').exists()).toBe(
      false,
    );

    await wrapper
      .find('[data-test="exam-converter-edit-advisory-answer-key-action"]')
      .trigger("click");

    expect(wrapper.find('[data-test="exam-converter-manual-answer-key-editor"]').exists()).toBe(
      true,
    );
    expect(
      wrapper.find('[data-test="exam-converter-manual-choice-3"]').attributes("aria-pressed"),
    ).toBe("true");
    expect(wrapper.findAll('[data-test="exam-converter-manual-choice-ai-symbol"]')).toHaveLength(1);
    expect(wrapper.find('[data-test="exam-converter-manual-choice-teacher-symbol"]').exists()).toBe(
      false,
    );
  });
});
