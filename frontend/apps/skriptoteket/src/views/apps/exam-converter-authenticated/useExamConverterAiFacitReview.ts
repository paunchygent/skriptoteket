/**
 * Exam Converter AI-facit review state.
 *
 * Domain purpose:
 *   Track explicit teacher decisions for Sir Convert advisory answer-key
 *   candidates and build reviewed-completion overlays for the apply pass.
 *
 * Relationships:
 *   - Receives normalized question rows from `digiexamIrReviewParser`.
 *   - Builds `reviewed_completion_answer_key` overlay entries only for
 *     accepted or teacher-edited AI-facit candidates.
 *   - Keeps accepted-current-state export decisions on their separate path.
 */

import { computed, ref } from "vue";

import type { DigiExamIngestionOverlay } from "../../../api/sirConvertGateway";
import {
  DIGIEXAM_COMPLETION_MODE_APPLY_REVIEWED_MISSING_MACHINE_MARKED,
  DIGIEXAM_COMPLETION_MODE_SOURCE_EVIDENCE_ONLY,
} from "../../../api/sirConvertGateway/contractValues";
import { DIGIEXAM_INGESTION_OVERLAY_SCHEMA_VERSION } from "../../../api/sirConvertGateway/schemaVersions";
import type {
  ExamConverterCompletionAnswerPayload,
  ExamConverterLlmAnswerKeyCandidate,
} from "./digiexamAnswerKeyCompletionReport";
import {
  hasUsableCompletionCandidate,
  type ExamConverterQuestionReviewRow,
  type ExamConverterReviewProjection,
} from "./digiexamIrReviewParser";

export type ExamConverterAiFacitReviewAction = "review" | "accept" | "edit" | "leave";

export type ExamConverterReviewedSuggestionDecision = {
  answerPayload: ExamConverterCompletionAnswerPayload | null;
  itemId: string;
  outcome: "accepted_unchanged" | "teacher_edited" | "left_manual";
};

type ExamConverterAcceptedSuggestionDecision = ExamConverterReviewedSuggestionDecision & {
  answerPayload: ExamConverterCompletionAnswerPayload;
  outcome: "accepted_unchanged" | "teacher_edited";
};

export const REVIEWED_COMPLETION_MODE =
  DIGIEXAM_COMPLETION_MODE_APPLY_REVIEWED_MISSING_MACHINE_MARKED;
export const ACCEPT_CURRENT_STATE_COMPLETION_MODE = DIGIEXAM_COMPLETION_MODE_SOURCE_EVIDENCE_ONLY;

function hasAcceptedDecision(
  decision: ExamConverterReviewedSuggestionDecision | undefined,
): decision is ExamConverterAcceptedSuggestionDecision {
  return (
    decision?.answerPayload !== null &&
    (decision?.outcome === "accepted_unchanged" || decision?.outcome === "teacher_edited")
  );
}

function requiredCandidateValue<T>(
  value: T | null | undefined,
  fieldName: string,
): T {
  if (value === null || value === undefined || value === "") {
    throw new Error(`Reviewed AI-facit candidate is missing ${fieldName}.`);
  }
  return value;
}

function toOverlayAnswerPayload(payload: ExamConverterCompletionAnswerPayload) {
  if (payload.kind === "choice") {
    return {
      kind: "choice" as const,
      correct_alternative_ids: payload.correctAlternativeIds,
    };
  }
  return {
    kind: "gap_fill" as const,
    gap_answers: payload.gapAnswers.map((gapAnswer) => ({
      gap_id: gapAnswer.gapId,
      accepted_values: gapAnswer.acceptedValues,
    })),
  };
}

function buildReviewedCompletionAnswerKey(params: {
  candidate: ExamConverterLlmAnswerKeyCandidate;
  decision: ExamConverterAcceptedSuggestionDecision;
}) {
  const answerPayload = params.decision.answerPayload;
  return {
    answer_payload: toOverlayAnswerPayload(answerPayload),
    candidate_lineage: {
      candidate_id: requiredCandidateValue(params.candidate.candidateId, "candidate id"),
      candidate_payload_digest: requiredCandidateValue(
        params.candidate.candidatePayloadDigest,
        "candidate payload digest",
      ),
      completion_report_sha256: params.candidate.completionReportSha256,
      prompt_template_version: requiredCandidateValue(
        params.candidate.promptTemplateVersion,
        "prompt template version",
      ),
      provider_profile_id: requiredCandidateValue(
        params.candidate.providerProfileId,
        "provider profile id",
      ),
      schema_name: requiredCandidateValue(params.candidate.schemaName, "schema name"),
      schema_version: requiredCandidateValue(params.candidate.schemaVersion, "schema version"),
      validation_state: "valid" as const,
    },
    kind: answerPayload.kind,
    review_decision_id: `review-${params.candidate.itemId}`,
    review_outcome: params.decision.outcome,
  };
}

function buildReviewedCompletionOverlay(
  projection: ExamConverterReviewProjection,
  decisions: Record<string, ExamConverterReviewedSuggestionDecision>,
): DigiExamIngestionOverlay | null {
  const items = projection.questions
    .map((question) => {
      const decision = decisions[question.itemId];
      if (!hasAcceptedDecision(decision) || !question.llmCandidate) {
        return null;
      }
      if (!question.sourceItemFingerprint) {
        throw new Error("Reviewed AI-facit overlay requires source item fingerprints.");
      }
      return {
        effective_item_patch: null,
        item_id: question.itemId,
        item_type: question.itemType,
        manual_answer_key: null,
        review_decision: null,
        reviewed_completion_answer_key: buildReviewedCompletionAnswerKey({
          candidate: question.llmCandidate,
          decision,
        }),
        sequence: question.sequence,
        source_item_fingerprint: question.sourceItemFingerprint,
      };
    })
    .filter((item): item is NonNullable<typeof item> => item !== null);

  if (items.length === 0) return null;
  return {
    schema_version: DIGIEXAM_INGESTION_OVERLAY_SCHEMA_VERSION,
    source_binding: {
      source_file_sha256: projection.sourceFileSha256,
      source_ir_schema_version:
        projection.artifactSourceBinding.source_ir_schema_version,
      source_ir_sha256: projection.artifactSourceBinding.source_ir_sha256,
    },
    items,
  };
}

export function useExamConverterAiFacitReview() {
  const decisions = ref<Record<string, ExamConverterReviewedSuggestionDecision>>({});
  const focusedReviewAction = ref<ExamConverterAiFacitReviewAction>("review");

  const acceptedSuggestionCount = computed(
    () => Object.values(decisions.value).filter(hasAcceptedDecision).length,
  );

  function resetAiFacitReview(): void {
    decisions.value = {};
    focusedReviewAction.value = "review";
  }

  function focusReviewAction(action: ExamConverterAiFacitReviewAction): void {
    focusedReviewAction.value = action;
  }

  function acceptSuggestion(question: ExamConverterQuestionReviewRow): void {
    if (!hasUsableCompletionCandidate(question) || !question.llmCandidate?.answerPayload) return;
    decisions.value = {
      ...decisions.value,
      [question.itemId]: {
        answerPayload: question.llmCandidate.answerPayload,
        itemId: question.itemId,
        outcome: "accepted_unchanged",
      },
    };
  }

  function acceptEditedChoiceSuggestion(
    question: ExamConverterQuestionReviewRow,
    correctAlternativeIds: number[],
  ): void {
    if (!hasUsableCompletionCandidate(question)) return;
    decisions.value = {
      ...decisions.value,
      [question.itemId]: {
        answerPayload: {
          kind: "choice",
          correctAlternativeIds,
        },
        itemId: question.itemId,
        outcome: "teacher_edited",
      },
    };
  }

  function leaveSuggestion(question: ExamConverterQuestionReviewRow): void {
    decisions.value = {
      ...decisions.value,
      [question.itemId]: {
        answerPayload: null,
        itemId: question.itemId,
        outcome: "left_manual",
      },
    };
  }

  function acceptAllSuggestions(projection: ExamConverterReviewProjection | null): void {
    if (!projection) return;
    const next = { ...decisions.value };
    for (const question of projection.questions) {
      if (
        hasUsableCompletionCandidate(question) &&
        question.llmCandidate?.answerPayload &&
        !next[question.itemId]
      ) {
        next[question.itemId] = {
          answerPayload: question.llmCandidate.answerPayload,
          itemId: question.itemId,
          outcome: "accepted_unchanged",
        };
      }
    }
    decisions.value = next;
  }

  const reviewedCompletionOverlay = computed(() => {
    return (projection: ExamConverterReviewProjection | null): DigiExamIngestionOverlay | null =>
      projection ? buildReviewedCompletionOverlay(projection, decisions.value) : null;
  });

  return {
    acceptAllSuggestions,
    acceptEditedChoiceSuggestion,
    acceptedSuggestionCount,
    acceptSuggestion,
    decisions,
    focusReviewAction,
    focusedReviewAction,
    leaveSuggestion,
    resetAiFacitReview,
    reviewedCompletionOverlay,
  };
}
