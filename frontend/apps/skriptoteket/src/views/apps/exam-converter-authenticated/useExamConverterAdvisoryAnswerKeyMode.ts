/**
 * Exam Converter advisory answer-key UI mode.
 *
 * Domain purpose:
 *   Track whether the selected pending advisory row has entered manual edit
 *   mode without turning that local choice into review-state truth.
 *
 * Relationships:
 *   - Used by `ExamConverterQuestionReviewShell`.
 *   - Reads compact producer review state only to decide whether the local
 *     panel or existing answer-key editor should be visible.
 *   - Leaves persistence and replay projection authority in
 *     `useExamConverterUnifiedCorrections`.
 */

import { ref, watch, type Ref } from "vue";

import type {
  ExamConverterQuestionReviewRow,
  ExamConverterReviewProjection,
} from "./digiexamIrReviewParser";
import { hasUsableCompletionCandidate } from "./digiexamIrReviewParser";

function isPendingAdvisoryQuestion(question: ExamConverterQuestionReviewRow): boolean {
  return question.answerKeyReviewState === "review_required" && hasUsableCompletionCandidate(question);
}

function isEditableAnswerKeyQuestion(question: ExamConverterQuestionReviewRow): boolean {
  return question.alternatives.length > 0 || question.gaps.length > 0;
}

export function useExamConverterAdvisoryAnswerKeyMode(
  projection: Ref<ExamConverterReviewProjection>,
) {
  const advisoryEditItemIds = ref<Set<string>>(new Set());

  function isAdvisoryEditOpen(question: ExamConverterQuestionReviewRow): boolean {
    return advisoryEditItemIds.value.has(question.itemId);
  }

  function showAdvisoryAnswerKeyPanel(question: ExamConverterQuestionReviewRow): boolean {
    return isPendingAdvisoryQuestion(question) && !isAdvisoryEditOpen(question);
  }

  function canShowAnswerKeyEditor(question: ExamConverterQuestionReviewRow): boolean {
    if (!isEditableAnswerKeyQuestion(question)) return false;
    const hasEditorReason =
      question.missingFields.includes("Facit") ||
      question.effectiveAnswerKey !== null ||
      hasUsableCompletionCandidate(question);
    if (!hasEditorReason) return false;
    return !isPendingAdvisoryQuestion(question) || isAdvisoryEditOpen(question);
  }

  function editAdvisoryAnswerKey(question: ExamConverterQuestionReviewRow): void {
    advisoryEditItemIds.value = new Set([...advisoryEditItemIds.value, question.itemId]);
  }

  watch(
    () => projection.value.sourceFileSha256,
    () => {
      advisoryEditItemIds.value = new Set();
    },
  );

  watch(
    () => projection.value.questions,
    (questions) => {
      advisoryEditItemIds.value = new Set(
        [...advisoryEditItemIds.value].filter((itemId) => {
          const question = questions.find((entry) => entry.itemId === itemId);
          return question ? isPendingAdvisoryQuestion(question) : false;
        }),
      );
    },
  );

  return {
    canShowAnswerKeyEditor,
    editAdvisoryAnswerKey,
    isPendingAdvisoryQuestion,
    showAdvisoryAnswerKeyPanel,
  };
}
