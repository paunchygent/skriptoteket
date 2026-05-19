/**
 * Exam Converter correction-session intent builders.
 *
 * Domain purpose:
 *   Convert teacher actions and producer-issued source state into durable
 *   Skriptoteket correction-session intent writes.
 *
 * Relationships:
 *   - Consumed by `useExamConverterUnifiedCorrections`.
 *   - Uses Sir Convert source-state DTOs only as binding material.
 *   - Keeps matching corrections blocked until their governed producer state exists.
 */

import type {
  ExamConverterCorrectionIntentWrite,
} from "../../../api/examConverterCorrectionSessions";
import type {
  ExamAuthoringCorrectionsApplyRequest,
  ExamAuthoringCorrectionSourceItem,
  ExamAuthoringCorrectionSourceStateIssueResult,
  ExamAuthoringNonMatchingCorrectionEntry,
} from "../../../api/sirConvertGateway";
import type {
  ExamConverterQuestionReviewRow,
  ExamConverterReviewProjection,
} from "./digiexamIrReviewParser";
import type {
  ExamConverterReviewedSuggestionDecision,
} from "./useExamConverterAiFacitReview";

type JsonRecord = Record<string, unknown>;

function payloadFromCorrection(
  correction: ExamAuthoringNonMatchingCorrectionEntry,
): JsonRecord {
  if (correction.kind === "point_correction") {
    return { max_score: correction.max_score };
  }
  if (correction.kind === "item_text_patch") {
    return { patches: correction.patches };
  }
  if (correction.kind === "manual_choice_answer_key") {
    return {
      candidate_lineage: correction.candidate_lineage,
      correct_choice_ids: correction.correct_choice_ids,
      interaction_id: correction.interaction_id,
      submission_origin: correction.submission_origin,
    };
  }
  if (correction.kind === "manual_gap_open_cloze_answer_key") {
    return {
      candidate_lineage: correction.candidate_lineage,
      gap_answers: correction.gap_answers,
      interaction_id: correction.interaction_id,
      submission_origin: correction.submission_origin,
    };
  }
  throw new Error("Unsupported durable correction entry.");
}

function targetFromCorrection(
  correction: ExamAuthoringNonMatchingCorrectionEntry,
): ExamConverterCorrectionIntentWrite["target"] {
  if (correction.kind === "manual_choice_answer_key") {
    return { interaction_id: correction.interaction_id };
  }
  if (correction.kind === "manual_gap_open_cloze_answer_key") {
    return { interaction_id: correction.interaction_id };
  }
  if (correction.kind === "item_text_patch") {
    const [patch] = correction.patches;
    return { text_field: typeof patch?.field === "string" ? patch.field : null };
  }
  return {};
}

export function intentFromCorrectionRequest(
  request: ExamAuthoringCorrectionsApplyRequest,
): ExamConverterCorrectionIntentWrite {
  const [correction] = request.corrections;
  if (!correction || correction.kind === "manual_matching_answer_key") {
    throw new Error("Matching corrections are blocked until Task 332.");
  }
  if (!correction.source_item_fingerprint) {
    throw new Error("Durable corrections require source item fingerprints.");
  }
  return {
    entry_id: correction.entry_id,
    item_id: correction.item_id,
    item_type: correction.item_type,
    kind: correction.kind,
    payload: payloadFromCorrection(correction),
    sequence: correction.sequence,
    source_binding: request.source_binding,
    source_item_fingerprint: correction.source_item_fingerprint,
    target: targetFromCorrection(correction),
  };
}

function sourceItemForQuestion(params: {
  question: ExamConverterQuestionReviewRow;
  sourceState: ExamAuthoringCorrectionSourceStateIssueResult;
}): ExamAuthoringCorrectionSourceItem {
  const sourceItem = params.sourceState.source_authoring_state.items.find(
    (item) => item.item_id === params.question.itemId,
  );
  if (!sourceItem || sourceItem.source_item_fingerprint !== params.question.sourceItemFingerprint) {
    throw new Error("Teacher action no longer matches the current exam source.");
  }
  return sourceItem;
}

function candidateLineage(question: ExamConverterQuestionReviewRow): JsonRecord {
  const candidate = question.llmCandidate;
  if (
    !candidate?.candidateId ||
    !candidate.candidatePayloadDigest ||
    !candidate.providerProfileId ||
    !candidate.promptTemplateVersion ||
    !candidate.schemaName ||
    !candidate.schemaVersion
  ) {
    throw new Error("Candidate rejection requires bounded candidate lineage.");
  }
  return {
    candidate_id: candidate.candidateId,
    candidate_payload_digest: candidate.candidatePayloadDigest,
    completion_report_sha256: candidate.completionReportSha256,
    prompt_template_version: candidate.promptTemplateVersion,
    provider_profile_id: candidate.providerProfileId,
    schema_name: candidate.schemaName,
    schema_version: candidate.schemaVersion,
    validation_state: "valid",
  };
}

function sourceChoiceIdForDisplayId(params: {
  displayId: number;
  question: ExamConverterQuestionReviewRow;
  sourceItem: ExamAuthoringCorrectionSourceItem;
}): string {
  const [interaction] = params.sourceItem.choice_interactions;
  if (!interaction) {
    throw new Error("Accepted suggestion requires producer choice state.");
  }
  const choice = interaction.choices.find(
    (candidate) =>
      candidate.source_id === String(params.displayId) || candidate.order === params.displayId,
  );
  if (!choice) {
    throw new Error("Accepted suggestion references an unknown producer choice.");
  }
  return choice.choice_id;
}

function acceptedSuggestionSubmissionOrigin(
  decision: ExamConverterReviewedSuggestionDecision,
):
  | "accepted_advisory_candidate"
  | "teacher_edited_advisory_candidate" {
  return decision.outcome === "teacher_edited"
    ? "teacher_edited_advisory_candidate"
    : "accepted_advisory_candidate";
}

function acceptedSuggestionIntent(params: {
  decision: ExamConverterReviewedSuggestionDecision;
  question: ExamConverterQuestionReviewRow;
  sourceState: ExamAuthoringCorrectionSourceStateIssueResult;
}): ExamConverterCorrectionIntentWrite | null {
  if (!params.decision.answerPayload) {
    return null;
  }
  const sourceItem = sourceItemForQuestion({
    question: params.question,
    sourceState: params.sourceState,
  });
  const lineage = candidateLineage(params.question);
  const submissionOrigin = acceptedSuggestionSubmissionOrigin(params.decision);
  if (params.decision.answerPayload.kind === "choice") {
    const [interaction] = sourceItem.choice_interactions;
    if (!interaction) {
      throw new Error("Accepted suggestion requires producer choice state.");
    }
    return {
      entry_id: `corr-ai-choice-${sourceItem.item_id}`,
      item_id: sourceItem.item_id,
      item_type: sourceItem.item_type,
      kind: "manual_choice_answer_key",
      payload: {
        candidate_lineage: lineage,
        correct_choice_ids: params.decision.answerPayload.correctAlternativeIds.map((displayId) =>
          sourceChoiceIdForDisplayId({ displayId, question: params.question, sourceItem }),
        ),
        interaction_id: interaction.interaction_id,
        submission_origin: submissionOrigin,
      },
      sequence: sourceItem.sequence,
      source_binding: params.sourceState.source_binding,
      source_item_fingerprint: sourceItem.source_item_fingerprint ?? "",
      target: { interaction_id: interaction.interaction_id },
    };
  }
  const [interaction] = sourceItem.gap_open_cloze_interactions;
  if (!interaction) {
    throw new Error("Accepted suggestion requires producer gap state.");
  }
  return {
    entry_id: `corr-ai-gap-${sourceItem.item_id}`,
    item_id: sourceItem.item_id,
    item_type: sourceItem.item_type,
    kind: "manual_gap_open_cloze_answer_key",
    payload: {
      candidate_lineage: lineage,
      gap_answers: params.decision.answerPayload.gapAnswers.map((gapAnswer) => ({
        accepted_values: gapAnswer.acceptedValues,
        gap_id: gapAnswer.gapId,
      })),
      interaction_id: interaction.interaction_id,
      submission_origin: submissionOrigin,
    },
    sequence: sourceItem.sequence,
    source_binding: params.sourceState.source_binding,
    source_item_fingerprint: sourceItem.source_item_fingerprint ?? "",
    target: { interaction_id: interaction.interaction_id },
  };
}

export function candidateSuppressionIntent(params: {
  question: ExamConverterQuestionReviewRow;
  sourceState: ExamAuthoringCorrectionSourceStateIssueResult;
}): ExamConverterCorrectionIntentWrite {
  const sourceItem = sourceItemForQuestion(params);
  const lineage = candidateLineage(params.question);
  const candidateId = String(lineage.candidate_id);
  const candidatePayloadDigest = String(lineage.candidate_payload_digest);
  return {
    entry_id: `corr-suppress-${sourceItem.item_id}-${candidateId}`,
    item_id: sourceItem.item_id,
    item_type: sourceItem.item_type,
    kind: "candidate_suppression",
    payload: { candidate_lineage: lineage },
    sequence: sourceItem.sequence,
    source_binding: params.sourceState.source_binding,
    source_item_fingerprint: sourceItem.source_item_fingerprint ?? "",
    target: {
      candidate_lineage_id: candidateId,
      candidate_payload_digest: candidatePayloadDigest,
    },
  };
}

export function acceptedSuggestionIntents(params: {
  decisions: Record<string, ExamConverterReviewedSuggestionDecision>;
  projection: ExamConverterReviewProjection;
  sourceState: ExamAuthoringCorrectionSourceStateIssueResult;
}): ExamConverterCorrectionIntentWrite[] {
  return params.projection.questions.flatMap((question) => {
    const decision = params.decisions[question.itemId];
    if (!decision || decision.outcome === "rejected") return [];
    const intent = acceptedSuggestionIntent({
      decision,
      question,
      sourceState: params.sourceState,
    });
    return intent ? [intent] : [];
  });
}

export function reviewDecisionIntents(params: {
  projection: ExamConverterReviewProjection;
  sourceState: ExamAuthoringCorrectionSourceStateIssueResult;
}): ExamConverterCorrectionIntentWrite[] {
  const overlayItems = params.projection.acceptedStateOverlay?.items ?? [];
  const sourceItemsById = new Map(
    params.sourceState.source_authoring_state.items.map((item) => [item.item_id, item]),
  );
  return overlayItems.flatMap((item) => {
    if (!item.review_decision) return [];
    const sourceItem = sourceItemsById.get(item.item_id);
    if (!sourceItem || sourceItem.source_item_fingerprint !== item.source_item_fingerprint) {
      throw new Error("Review decision no longer matches the current exam source.");
    }
    return [
      {
        entry_id: `corr-review-${sourceItem.item_id}`,
        item_id: sourceItem.item_id,
        item_type: sourceItem.item_type,
        kind: "review_decision" as const,
        payload: {
          accepted_targets: item.review_decision.accepted_targets,
          decision_id: item.review_decision.decision_id,
          note: item.review_decision.note,
        },
        sequence: sourceItem.sequence,
        source_binding: params.sourceState.source_binding,
        source_item_fingerprint: sourceItem.source_item_fingerprint ?? "",
        target: {
          accepted_target_family: "requested_artifacts",
        },
      },
    ];
  });
}
