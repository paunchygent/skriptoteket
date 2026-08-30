import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import {
  ANSWER_KEY_REVIEW_STATE_SCHEMA_VERSION,
  DIGIEXAM_EFFECTIVE_EXAM_SCHEMA_VERSION,
  DIGIEXAM_INTERMEDIATE_EXAM_SCHEMA_VERSION,
  DIGIEXAM_ITEM_TYPE_GAP_FILL,
} from "../../../api/examConverterContracts";
import type {
  ExamConverterQuestionReviewRow,
  ExamConverterReviewProjection,
} from "./digiexamIrReviewParser";
import ExamConverterQuestionReviewShell from "./ExamConverterQuestionReviewShell.vue";

const FIRST_GAP_ID = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa";
const SECOND_GAP_ID = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb";

function gapQuestion(reviewState: "review_complete" | "review_required"):
  ExamConverterQuestionReviewRow {
  const isPending = reviewState === "review_required";
  return {
    alternatives: [],
    answerKeyReviewOrigin: isPending ? "none" : "reviewed_advisory",
    answerKeyReviewReasons: isPending
      ? ["advisory_candidate_pending"]
      : ["reviewed_advisory_accepted"],
    answerKeyReviewState: reviewState,
    answerKeyReviewStateLabel: isPending ? "Granska facit" : "Facit granskat",
    answerKeyReviewStateReasonLabel: null,
    currentAnswerKeyProvenance: isPending ? "machine_proposed" : "reviewed",
    effectiveAnswerKey: {
      correct_gap_answers: [
        { gap_id: FIRST_GAP_ID, value: "Första svaret" },
        { gap_id: SECOND_GAP_ID, value: "Andra svaret" },
      ],
      lineage: null,
      provenance: isPending ? "machine_proposed" : "reviewed",
    },
    effectivePointCorrection: null,
    gaps: [
      { id: FIRST_GAP_ID, label: "Lucka 1" },
      { id: SECOND_GAP_ID, label: "Lucka 2" },
    ],
    itemId: "item-gap",
    itemType: DIGIEXAM_ITEM_TYPE_GAP_FILL,
    llmCandidate: isPending
      ? {
          answerPayload: {
            gapAnswers: [
              { acceptedValues: ["Första svaret"], gapId: FIRST_GAP_ID },
              { acceptedValues: ["Andra svaret"], gapId: SECOND_GAP_ID },
            ],
            kind: "gap_fill",
          },
          backendFailureCode: null,
          backendStatus: "success",
          candidateId: "candidate-item-gap",
          candidatePayloadDigest: "sha256:candidate-item-gap",
          completionReportSha256: "sha256:completion-report",
          decisionState: "suggested",
          itemId: "item-gap",
          itemType: DIGIEXAM_ITEM_TYPE_GAP_FILL,
          modelProfile: "gpt-5.6-luna",
          promptTemplateVersion: "digiexam-gap-fill-answer-key-v1",
          providerProfileId: "luna",
          schemaName: "digiexam_gap_fill_answer_key_decision_v1",
          schemaVersion: "digiexam_gap_fill_answer_key_decision_v1",
          sequence: 1,
          validationState: "valid",
        }
      : null,
    lucktextStructure: {
      gapCount: 2,
      imageCount: 0,
      images: [],
    },
    manualFollowUpMessages: [],
    missingFields: isPending ? ["Facit"] : [],
    pointsLabel: "1 p",
    pointsValue: 1,
    promptText: "Fyll i begreppen.",
    sequence: 1,
    sourceItemFingerprint: "sha256:item-gap",
    status: isPending ? "attention" : "complete",
    statusSymbol: isPending ? "ai_suggestion" : "complete",
    title: "Begrepp",
    typeLabel: "Lucktext",
  };
}

function projection(question: ExamConverterQuestionReviewRow): ExamConverterReviewProjection {
  const effectiveAnswerKeysByItem: ExamConverterReviewProjection["effectiveAnswerKeysByItem"] =
    new Map();
  if (question.effectiveAnswerKey) {
    effectiveAnswerKeysByItem.set(question.itemId, question.effectiveAnswerKey);
  }
  return {
    answerKeyCompletionReport: null,
    answerKeyReviewState: {
      items: [],
      schema_version: ANSWER_KEY_REVIEW_STATE_SCHEMA_VERSION,
    },
    artifactSourceBinding: {
      effective_exam_schema_version: DIGIEXAM_EFFECTIVE_EXAM_SCHEMA_VERSION,
      effective_exam_sha256: "sha256:effective",
      source_ir_schema_version: DIGIEXAM_INTERMEDIATE_EXAM_SCHEMA_VERSION,
      source_ir_sha256: "sha256:source-ir",
    },
    defaultMode: "questions",
    effectiveAnswerKeysByItem,
    effectivePointCorrectionsByItem: new Map(),
    files: [],
    questions: [question],
    report: {
      aiSuggestionCount: question.llmCandidate ? 1 : 0,
      aiSuggestionOutcomes: {
        acceptedUnchangedCount: question.llmCandidate ? 0 : 1,
        items: [],
        suppressedCount: 0,
        teacherEditedCount: 0,
        totalCount: 1,
        unresolvedCount: question.llmCandidate ? 1 : 0,
      },
      attentionQuestionCount: question.status === "attention" ? 1 : 0,
      blockedTargetFileCount: 0,
      missingAnswerKeyCount: question.missingFields.includes("Facit") ? 1 : 0,
      missingPointsCount: 0,
      warningCount: 0,
    },
    sourceFilename: "lag-och-ratt.dxe",
    sourceFileSha256: "sha256:source",
  };
}

describe("ExamConverterQuestionReviewShell", () => {
  it("shows pending AI review controls without presenting the proposal as accepted", async () => {
    const question = gapQuestion("review_required");
    const wrapper = mount(ExamConverterQuestionReviewShell, {
      props: {
        aiSuggestionFocusKey: 0,
        isCorrectionApplying: false,
        projection: projection(question),
      },
    });

    expect(wrapper.find('[data-test="exam-converter-selected-question-ai-suggestion"]').exists())
      .toBe(true);
    expect(wrapper.find('[data-test="exam-converter-effective-answer-key-summary"]').exists())
      .toBe(false);
    expect(wrapper.get('[data-test="exam-converter-accept-advisory-answer-key-action"]').text())
      .toBe("Acceptera");
    expect(wrapper.get('[data-test="exam-converter-edit-advisory-answer-key-action"]').text())
      .toBe("Ändra");
    expect(wrapper.text()).toContain("Lucka 1: Första svaret");
    expect(wrapper.text()).toContain("Lucka 2: Andra svaret");
    expect(wrapper.text()).not.toContain(FIRST_GAP_ID);
    expect(wrapper.text()).not.toContain(SECOND_GAP_ID);

    await wrapper.get('[data-test="exam-converter-edit-advisory-answer-key-action"]').trigger("click");
    expect(wrapper.find('[data-test="exam-converter-effective-answer-key-summary"]').exists())
      .toBe(false);
    expect(wrapper.find('[data-test="exam-converter-manual-answer-key-editor"]').exists())
      .toBe(true);

    const freshWrapper = mount(ExamConverterQuestionReviewShell, {
      props: {
        aiSuggestionFocusKey: 0,
        isCorrectionApplying: false,
        projection: projection(question),
      },
    });

    await freshWrapper
      .get('[data-test="exam-converter-accept-advisory-answer-key-action"]')
      .trigger("click");

    expect(freshWrapper.emitted("applyManualAnswerKey")?.[0]?.[1]).toEqual({
      gapAnswers: [
        { acceptedValues: ["Första svaret"], gapId: FIRST_GAP_ID },
        { acceptedValues: ["Andra svaret"], gapId: SECOND_GAP_ID },
      ],
      kind: "gap_fill",
    });
  });

  it("renders persisted gap values in source order without leaking identifiers", () => {
    const question = gapQuestion("review_complete");
    const wrapper = mount(ExamConverterQuestionReviewShell, {
      props: {
        aiSuggestionFocusKey: 0,
        isCorrectionApplying: false,
        projection: projection(question),
      },
    });

    const summary = wrapper.get('[data-test="exam-converter-effective-answer-key-summary"]');
    expect(summary.text()).toContain("Första svaret, Andra svaret");
    expect(summary.text()).not.toContain(FIRST_GAP_ID);
    expect(summary.text()).not.toContain(SECOND_GAP_ID);
    expect(wrapper.get(`[data-test="exam-converter-effective-gap-answer-${FIRST_GAP_ID}"]`).text())
      .toBe("Lucka 1: Första svaret");
    expect(wrapper.get(`[data-test="exam-converter-effective-gap-answer-${SECOND_GAP_ID}"]`).text())
      .toBe("Lucka 2: Andra svaret");
  });
});
