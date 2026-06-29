/**
 * Exam Converter compact answer-key review-state behavior.
 *
 * Slice purpose:
 *   Prove Skriptoteket consumes Sir Convert's compact answer-key projection as
 *   the only review-state authority for question rows.
 *
 * Expected behavior:
 *   Unknown producer vocabulary and legacy compatibility fields fail closed,
 *   while valid producer states map to the approved Swedish labels and symbols.
 *
 * Recommended implementation shape:
 *   Keep strict contract parsing and Swedish presentation mapping in one
 *   narrow adapter before question-list, detail, report, or files rendering.
 */

import { describe, expect, it } from "vitest";

import {
  applyAnswerKeyReviewStateToQuestions,
  parseAnswerKeyReviewState,
} from "./answerKeyReviewStateAdapter";
import type { ExamConverterQuestionReviewRow } from "./digiexamIrReviewParser";

function reviewItem(overrides: Record<string, unknown> = {}) {
  return {
    choice_ids: [],
    choice_interaction_ids: [],
    correction_affordances: [],
    current_key_origin: "none",
    gap_ids: [],
    gap_interaction_ids: [],
    item_id: "item-001",
    item_type: "gap_fill",
    message_key: "exam_converter.answer_key.review_required",
    provenance_detail: null,
    reasons: ["advisory_candidate_pending"],
    replay_artifact_references: [],
    review_state: "review_required",
    sequence: 1,
    source_item_fingerprint: "sha256:item-001",
    ...overrides,
  };
}

function reviewState(overrides: Record<string, unknown> = {}) {
  return {
    items: [reviewItem()],
    schema_version: "digiexam_answer_key_review_state_v1",
    ...overrides,
  };
}

function question(overrides: Partial<ExamConverterQuestionReviewRow> = {}): ExamConverterQuestionReviewRow {
  return {
    alternatives: [],
    answerKeyReviewOrigin: null,
    answerKeyReviewReasons: [],
    answerKeyReviewState: null,
    answerKeyReviewStateLabel: "Klart",
    answerKeyReviewStateReasonLabel: null,
    currentAnswerKeyProvenance: "absent",
    effectiveAnswerKey: null,
    effectivePointCorrection: null,
    gaps: [{ id: "gap-001", label: "Lucka 1" }],
    itemId: "item-001",
    itemType: "gap_fill",
    llmCandidate: {
      answerPayload: {
        gapAnswers: [{ acceptedValues: ["Polisen"], gapId: "gap-001" }],
        kind: "gap_fill",
      },
      backendFailureCode: null,
      backendStatus: "ok",
      candidateId: "candidate-001",
      candidatePayloadDigest: "sha256:candidate",
      completionReportSha256: "sha256:completion-report",
      decisionState: "suggested",
      itemId: "item-001",
      itemType: "gap_fill",
      modelProfile: "local",
      promptTemplateVersion: "prompt-v1",
      providerProfileId: "provider-local",
      schemaName: "schema",
      schemaVersion: "schema-v1",
      sequence: 1,
      validationState: "valid",
    },
    lucktextStructure: null,
    manualFollowUpMessages: [],
    missingFields: ["Facit"],
    pointsLabel: "1 p",
    pointsValue: 1,
    promptText: "Fyll i luckan.",
    sequence: 1,
    sourceItemFingerprint: "sha256:item-001",
    status: "attention",
    statusSymbol: "validation_required",
    title: "Fråga 1",
    typeLabel: "Lucktext",
    ...overrides,
  };
}

describe("answerKeyReviewStateAdapter", () => {
  it.each([
    ["schema_version", reviewState({ schema_version: "digiexam_answer_key_review_state_v0" })],
    ["review_state", reviewState({ items: [reviewItem({ review_state: "accepted" })] })],
    ["current_key_origin", reviewState({ items: [reviewItem({ current_key_origin: "ai" })] })],
    ["reasons", reviewState({ items: [reviewItem({ reasons: ["legacy_reason"] })] })],
    ["missing projection", { schema_version: "digiexam_answer_key_review_state_v1" }],
    ["history", reviewState({ history: [] })],
    ["review_decision", reviewState({ items: [reviewItem({ review_decision: "accepted" })] })],
  ])("fails closed for invalid compact projection payloads: %s", (_caseName, payload) => {
    expect(() => parseAnswerKeyReviewState(payload)).toThrow();
  });

  it("maps every producer state to approved Swedish label and symbol semantics", () => {
    const parsed = parseAnswerKeyReviewState({
      schema_version: "digiexam_answer_key_review_state_v1",
      items: [
        reviewItem({
          item_id: "item-001",
          review_state: "review_required",
          current_key_origin: "none",
          reasons: ["advisory_candidate_pending"],
        }),
        reviewItem({
          item_id: "item-002",
          review_state: "review_complete",
          current_key_origin: "reviewed_advisory",
          reasons: ["reviewed_advisory_accepted"],
          sequence: 2,
        }),
        reviewItem({
          item_id: "item-003",
          review_state: "teacher_modified",
          current_key_origin: "teacher_edited_advisory",
          reasons: ["teacher_edited_advisory_candidate"],
          sequence: 3,
        }),
        reviewItem({
          item_id: "item-004",
          item_type: "multiple_choice",
          review_state: "validation_required",
          current_key_origin: "none",
          reasons: ["no_correct_choice_selected"],
          sequence: 4,
        }),
      ],
    });

    const rows = applyAnswerKeyReviewStateToQuestions({
      questions: [
        question({ itemId: "item-001", sequence: 1 }),
        question({ itemId: "item-002", sequence: 2 }),
        question({ itemId: "item-003", sequence: 3 }),
        question({ itemId: "item-004", itemType: "multiple_choice", sequence: 4 }),
      ],
      reviewState: parsed,
    });

    expect(rows.map((row) => [row.answerKeyReviewStateLabel, row.statusSymbol])).toEqual([
      ["Granska", "ai_suggestion"],
      ["Klart", "complete"],
      ["Ändrat", "teacher_modified"],
      ["Kontrollera", "validation_required"],
    ]);
    expect(rows[1]?.llmCandidate).toBeNull();
    expect(rows[2]?.llmCandidate).toBeNull();
    expect(rows[3]?.answerKeyReviewStateReasonLabel).toBe("Inget rätt svar valt");
  });
});
