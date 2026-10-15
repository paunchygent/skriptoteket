/**
 * Exam workspace item save rules.
 *
 * Domain purpose:
 *   Name the item states the editor can reach but the server refuses to
 *   save, so the teacher sees them at the question and a save is refused
 *   with Swedish copy naming the questions instead of a generic failure.
 *   Mirrors these `NativeExamItem` field rules exactly: points must be
 *   greater than zero (`_positive_finite_points`), a choice's rich body must
 *   not be empty (`NativeChoice.body`, text segments with `min_length=1`),
 *   and so must a matching entry's. A free-text item's criteria must have
 *   non-empty text and whole points of at least 1, only free-text items
 *   carry them, and a non-empty list's points are exactly the item's points.
 *   A partial gap key or an incomplete matching key
 *   (`_answer_key_invariants`) comes from `examWorkspaceAnswerKeyRules`.
 *
 * Relationships:
 *   - Mirrors `domain/curated_apps/exam_workspace/native_exam_document.py`.
 *   - Consumed by `useExamWorkspaceDocument` (save refusal),
 *     `examWorkspaceItemReadiness` (per-question reasons), and
 *     `ExamWorkspaceItemEditor` (inline field hints).
 */

import type { NativeExamCriterion, NativeExamItem } from "../../../api/examWorkspace";
import {
  incompleteMatchKeyCopy,
  isIncompleteMatchingItem,
  isPartiallyKeyedGapItem,
  partialGapKeyCopy,
  questionSubject,
} from "./examWorkspaceAnswerKeyRules";
import { isEmptyBody } from "./examWorkspaceRichText";

export const NON_POSITIVE_POINTS_GUIDANCE = "Poängen måste vara större än noll.";
export const EMPTY_CHOICE_TEXT_GUIDANCE = "Ett svarsalternativ saknar text.";
export const EMPTY_MATCH_TEXT_GUIDANCE = "En rad eller en kategori saknar text.";
export const EMPTY_CRITERION_TEXT_GUIDANCE = "Ett kriterium saknar text.";
export const INVALID_CRITERION_POINTS_GUIDANCE =
  "Poängen för ett kriterium måste vara ett heltal som är minst 1.";
export const CRITERIA_POINTS_MISMATCH_GUIDANCE =
  "Kriteriernas poängsumma ska vara frågans poäng.";
export const CRITERIA_ON_WRONG_KIND_GUIDANCE = "Endast fritextfrågor kan ha kriterier.";

export function hasNonPositivePoints(item: NativeExamItem): boolean {
  return typeof item.points === "number" && item.points <= 0;
}

export function isEmptyChoiceBody(choice: NativeExamItem["choices"][number]): boolean {
  return isEmptyBody(choice.body);
}

export function hasEmptyChoiceText(item: NativeExamItem): boolean {
  return item.choices.some(isEmptyChoiceBody);
}

export function hasEmptyMatchText(item: NativeExamItem): boolean {
  return [...item.match_left, ...item.match_right].some((entry) => isEmptyBody(entry.body));
}

/** The exact sum the model requires of a non-empty criteria list. */
export function criteriaPointsTotal(criteria: readonly NativeExamCriterion[]): number {
  return criteria.reduce((sum, criterion) => sum + criterion.points, 0);
}

/**
 * The model strips criterion text only to check it, so whitespace alone is
 * an empty criterion, unlike a choice's text.
 */
export function hasEmptyCriterionText(item: NativeExamItem): boolean {
  return item.criteria.some((criterion) => criterion.text.trim().length === 0);
}

export function hasInvalidCriterionPoints(item: NativeExamItem): boolean {
  return item.criteria.some(
    (criterion) => !Number.isInteger(criterion.points) || criterion.points < 1,
  );
}

export function hasCriteriaPointsMismatch(item: NativeExamItem): boolean {
  return item.criteria.length > 0 && item.points !== criteriaPointsTotal(item.criteria);
}

export function hasCriteriaOnWrongKind(item: NativeExamItem): boolean {
  return item.criteria.length > 0 && item.kind !== "free_text";
}

function refusal(
  items: NativeExamItem[],
  isRefused: (item: NativeExamItem) => boolean,
  copy: (refused: NativeExamItem[]) => string,
): string | null {
  const refused = items.filter(isRefused);
  return refused.length > 0 ? copy(refused) : null;
}

/**
 * Swedish copy for every rule the items break, one sentence group per rule,
 * or `null` when the server would accept them.
 */
export function examWorkspaceSaveRefusalCopy(items: NativeExamItem[]): string | null {
  const refusals = [
    refusal(items, isPartiallyKeyedGapItem, partialGapKeyCopy),
    refusal(items, isIncompleteMatchingItem, incompleteMatchKeyCopy),
    refusal(
      items,
      hasNonPositivePoints,
      (refused) =>
        `${questionSubject(refused)} har noll eller negativa poäng. ${NON_POSITIVE_POINTS_GUIDANCE}`,
    ),
    refusal(
      items,
      hasEmptyChoiceText,
      (refused) =>
        `${questionSubject(refused)} har svarsalternativ utan text. Skriv text i varje svarsalternativ.`,
    ),
    refusal(
      items,
      hasEmptyMatchText,
      (refused) =>
        `${questionSubject(refused)} har rader eller kategorier utan text. Skriv text i varje rad och varje kategori.`,
    ),
    refusal(
      items,
      hasEmptyCriterionText,
      (refused) =>
        `${questionSubject(refused)} har ett kriterium utan text. Skriv text i varje kriterium.`,
    ),
    refusal(
      items,
      hasInvalidCriterionPoints,
      (refused) =>
        `${questionSubject(refused)} har ett kriterium med ogiltiga poäng. ${INVALID_CRITERION_POINTS_GUIDANCE}`,
    ),
    refusal(
      items,
      hasCriteriaPointsMismatch,
      (refused) =>
        `${questionSubject(refused)} har kriterier vars poängsumma inte stämmer med frågans poäng. ${CRITERIA_POINTS_MISMATCH_GUIDANCE}`,
    ),
    refusal(
      items,
      hasCriteriaOnWrongKind,
      (refused) =>
        `${questionSubject(refused)} har kriterier men är inte en fritextfråga. ${CRITERIA_ON_WRONG_KIND_GUIDANCE}`,
    ),
  ].filter((copy): copy is string => copy !== null);
  return refusals.length > 0 ? refusals.join(" ") : null;
}
