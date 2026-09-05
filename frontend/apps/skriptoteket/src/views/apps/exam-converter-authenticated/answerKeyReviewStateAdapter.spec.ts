/**
 * Exam Converter compact answer-key review-state behavior.
 *
 * Slice purpose:
 *   Prove Skriptoteket consumes the local compact answer-key projection as
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
  countActionableAnswerKeyRows,
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

function replayReference(overrides: Record<string, unknown> = {}) {
  return {
    artifact_key: "correction_replay_examnet_pdf",
    artifact_set_id: "artifact-set-001",
    content_sha256: "sha256:replay-pdf",
    correction_payload_digest: "sha256:correction-payload",
    created_at: "2026-06-29T12:00:00Z",
    job_id: "sir-job-001",
    replay_profile_version: "correction-replay-v1",
    request_id: "correction-session-replay-session-001-v2",
    schema_version: "correction_replay_artifact_reference_v1",
    source_binding_digest: "sha256:source-binding",
    source_state_sha256: "sha256:source-state",
    target: "examnet_pdf",
    target_set_digest: "sha256:target-set",
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
    reviewWarnings: [],
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
    [
      "stale replay reference",
      reviewState({
        items: [
          reviewItem({
            replay_artifact_references: [
              { artifact_key: "correction_replay_examnet_pdf", target: "examnet_pdf" },
            ],
          }),
        ],
      }),
    ],
    [
      "unknown replay reference field",
      reviewState({
        items: [reviewItem({ replay_artifact_references: [replayReference({ legacy: true })] })],
      }),
    ],
    [
      "missing replay content digest",
      reviewState({
        items: [
          reviewItem({
            replay_artifact_references: [
              replayReference({ content_sha256: undefined }),
            ],
          }),
        ],
      }),
    ],
  ])("fails closed for invalid compact projection payloads: %s", (_caseName, payload) => {
    expect(() => parseAnswerKeyReviewState(payload)).toThrow();
  });

  it("accepts Task 378 request-scoped replay artifact references", () => {
    const parsed = parseAnswerKeyReviewState(
      reviewState({
        items: [
          reviewItem({
            replay_artifact_references: [
              replayReference(),
              replayReference({
                artifact_key: "correction_replay_qti_package",
                artifact_set_id: "artifact-set-002",
                content_sha256: "sha256:replay-qti",
                target: "qti_package",
              }),
            ],
          }),
        ],
      }),
    );

    expect(parsed.items[0]?.replay_artifact_references).toEqual([
      expect.objectContaining({
        artifact_key: "correction_replay_examnet_pdf",
        artifact_set_id: "artifact-set-001",
        content_sha256: "sha256:replay-pdf",
        job_id: "sir-job-001",
        schema_version: "correction_replay_artifact_reference_v1",
        target: "examnet_pdf",
      }),
      expect.objectContaining({
        artifact_key: "correction_replay_qti_package",
        artifact_set_id: "artifact-set-002",
        content_sha256: "sha256:replay-qti",
        target: "qti_package",
      }),
    ]);
  });

  it("retains reviewed-advisory completion-report lineage", () => {
    const parsed = parseAnswerKeyReviewState(
      reviewState({
        items: [
          reviewItem({
            current_key_origin: "reviewed_advisory",
            provenance_detail: {
              candidate_id: "candidate-001",
              candidate_payload_digest: "sha256:candidate",
              completion_report_sha256: "sha256:completion-report",
              prompt_template_version: "prompt-v1",
              provider_profile_id: "provider-local",
              schema_name: "exam_authoring_answer_key_candidate_v1",
              schema_version: "v1",
              validation_state: "valid",
            },
            reasons: ["reviewed_advisory_accepted"],
            review_state: "review_complete",
          }),
        ],
      }),
    );

    expect(parsed.items[0]?.provenance_detail?.completion_report_sha256).toBe(
      "sha256:completion-report",
    );
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

  it("keeps Lucktext keyed review actionable while excluding open-ended rows", () => {
    const parsed = parseAnswerKeyReviewState({
      schema_version: "digiexam_answer_key_review_state_v1",
      items: [
        reviewItem({
          item_id: "item-001",
          item_type: "gap_fill",
          review_state: "review_required",
          current_key_origin: "none",
          reasons: ["advisory_candidate_pending"],
        }),
        reviewItem({
          item_id: "item-002",
          item_type: "open_ended",
          review_state: "validation_required",
          current_key_origin: "none",
          reasons: ["manual_answer_key_required"],
          sequence: 2,
        }),
        reviewItem({
          item_id: "item-003",
          item_type: "open_ended",
          review_state: "validation_required",
          current_key_origin: "none",
          reasons: ["unsupported_item_type"],
          sequence: 3,
        }),
        reviewItem({
          item_id: "item-004",
          item_type: "open_ended",
          review_state: "review_complete",
          current_key_origin: "none",
          reasons: ["answer_key_not_applicable"],
          sequence: 4,
        }),
      ],
    });

    const rows = applyAnswerKeyReviewStateToQuestions({
      questions: [
        question({ itemId: "item-001", itemType: "gap_fill", sequence: 1 }),
        question({
          gaps: [],
          itemId: "item-002",
          itemType: "open_ended",
          llmCandidate: null,
          sequence: 2,
          typeLabel: "Fritext",
        }),
        question({
          gaps: [],
          itemId: "item-003",
          itemType: "open_ended",
          llmCandidate: null,
          sequence: 3,
          typeLabel: "Fritext",
        }),
        question({
          gaps: [],
          itemId: "item-004",
          itemType: "open_ended",
          llmCandidate: null,
          sequence: 4,
          typeLabel: "Fritext",
        }),
      ],
      reviewState: parsed,
    });

    expect(countActionableAnswerKeyRows(parsed)).toBe(1);
    expect(rows.map((row) => row.answerKeyReviewStateLabel)).toEqual([
      "Granska",
      "Klart",
      "Klart",
      "Klart",
    ]);
    expect(rows.map((row) => row.statusSymbol)).toEqual([
      "ai_suggestion",
      "complete",
      "complete",
      "complete",
    ]);
    expect(rows.map((row) => row.status)).toEqual([
      "attention",
      "complete",
      "complete",
      "complete",
    ]);
    expect(rows[0]?.missingFields).not.toContain("Facit");
    expect(rows[1]?.missingFields).not.toContain("Facit");
    expect(rows[2]?.missingFields).not.toContain("Facit");
    expect(rows[3]?.missingFields).not.toContain("Facit");
    expect(rows[0]?.llmCandidate).not.toBeNull();
    expect(rows[0]?.answerKeyReviewStateReasonLabel).toBeNull();
    expect(rows[1]?.answerKeyReviewStateReasonLabel).toBeNull();
    expect(rows[2]?.answerKeyReviewStateReasonLabel).toBeNull();
    expect(rows[3]?.answerKeyReviewStateReasonLabel).toBeNull();
  });
});
