/**
 * Exam Converter persisted correction display helpers.
 *
 * Domain purpose:
 *   Centralize read-only presentation of correction state returned by Sir
 *   Convert so teacher-authored submits never depend on editor-local drafts.
 *
 * Relationships:
 *   - Consumes `ExamConverterQuestionReviewRow` effective state.
 *   - Used by review-detail components after unified correction apply returns.
 *   - Keeps selection highlighting and summary chips aligned across item
 *     navigation and correction families.
 */

import type { ExamConverterQuestionReviewRow } from "./digiexamIrReviewParser";

export function numericAlternativeId(id: string): number | null {
  const value = Number.parseInt(id, 10);
  return Number.isInteger(value) ? value : null;
}

export function effectiveChoiceIdsForQuestion(
  question: ExamConverterQuestionReviewRow,
): number[] {
  return question.effectiveAnswerKey?.correct_alternative_ids ?? [];
}

export function isEffectiveChoiceAlternative(params: {
  alternativeId: string;
  question: ExamConverterQuestionReviewRow;
}): boolean {
  const numericId = numericAlternativeId(params.alternativeId);
  return (
    numericId !== null &&
    effectiveChoiceIdsForQuestion(params.question).includes(numericId)
  );
}

export function effectiveGapAnswerEntries(
  question: ExamConverterQuestionReviewRow,
): [string, string][] {
  return question.effectiveAnswerKey?.correct_gap_answers?.map((gapAnswer) => [
    gapAnswer.gap_id,
    gapAnswer.value,
  ]) ?? [];
}

export type EffectiveGapAnswerDisplayEntry = {
  gapId: string;
  label: string;
  value: string;
};

export function effectiveGapAnswerDisplayEntries(
  question: ExamConverterQuestionReviewRow,
): EffectiveGapAnswerDisplayEntry[] {
  const entries = effectiveGapAnswerEntries(question);
  const gapIndexById = new Map(question.gaps.map((gap, index) => [gap.id, index + 1]));
  return entries.map(([gapId, value], index) => ({
    gapId,
    label: `Lucka ${gapIndexById.get(gapId) ?? index + 1}`,
    value,
  }));
}
