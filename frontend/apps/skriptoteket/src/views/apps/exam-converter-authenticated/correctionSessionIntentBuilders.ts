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
} from "./digiexamIrReviewParser";

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
