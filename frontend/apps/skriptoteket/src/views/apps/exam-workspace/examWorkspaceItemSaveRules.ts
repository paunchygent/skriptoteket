/**
 * Exam workspace item save rules.
 *
 * Domain purpose:
 *   Name the item states the editor can reach but the server refuses to
 *   save, so the teacher sees them at the question and a save is refused
 *   with Swedish copy naming the questions instead of a generic failure.
 *   Mirrors these `NativeExamItem` field rules exactly: points must be
 *   non-negative and finite (`_nonnegative_finite_points`). A free-text item's criteria must have
 *   non-empty text and whole points of at least 1, only free-text items
 *   carry them, and a non-empty list's points are exactly the item's points.
 *   An incomplete matching key (`_answer_key_invariants`) comes from
 *   `examWorkspaceAnswerKeyRules`. An empty gap saves as a draft
 *   (TASK-SKRIPT-40-04-13 U4, L2) and blocks export through readiness
 *   instead; an empty choice or matching entry saves (TASK-SKRIPT-40-04-06
 *   D3) and is likewise export-only.
 *
 * Relationships:
 *   - Mirrors `domain/curated_apps/exam_workspace/native_exam_document.py`.
 *   - Consumed by `useExamWorkspaceDocument` (save refusal),
 *     `examWorkspaceItemReadiness` (per-question reasons), and
 *     `ExamWorkspaceQuestionEditor` (inline field hints).
 */

import type { NativeExamCriterion, NativeExamDocument, NativeExamItem } from "../../../api/examWorkspace";
import {
  incompleteMatchKeyCopy,
  isIncompleteMatchingItem,
  questionSubject,
} from "./examWorkspaceAnswerKeyRules";
import { isEmptyBody } from "./examWorkspaceRichTextDocument";

export const NEGATIVE_POINTS_GUIDANCE = "Ange 0 poäng eller mer.";

/** An ordering question inside a part is worth Exam.net's 1 point (TASK-SKRIPT-39-06-11 D1): the note beside its locked field. */
export const PART_ORDERING_POINTS_NOTE = "Exam.net ger alltid Ordna-frågor i en del 1 poäng";
/** The tooltip on that locked points field. */
export const PART_ORDERING_POINTS_LOCKED_TITLE = "Låst: Exam.net ger Ordna i en del 1 poäng";
export const EMPTY_CHOICE_TEXT_GUIDANCE = "Ett svarsalternativ saknar text.";
export const EMPTY_MATCH_TEXT_GUIDANCE = "En rad eller en kategori saknar text.";
export const EMPTY_CRITERION_TEXT_GUIDANCE = "Ett kriterium saknar text.";
export const INVALID_CRITERION_POINTS_GUIDANCE =
  "Poängen för ett kriterium måste vara ett heltal som är minst 1.";
export const CRITERIA_POINTS_MISMATCH_GUIDANCE =
  "Kriteriernas poängsumma ska vara frågans poäng.";
export const CRITERIA_ON_WRONG_KIND_GUIDANCE = "Endast fritextfrågor kan ha kriterier.";

export function hasNegativePoints(item: NativeExamItem): boolean {
  return typeof item.points === "number" && (!Number.isFinite(item.points) || item.points < 0);
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
  document: NativeExamDocument,
  isRefused: (item: NativeExamItem) => boolean,
  copy: (document: NativeExamDocument, refused: NativeExamItem[]) => string,
): string | null {
  const refused = document.items.filter(isRefused);
  return refused.length > 0 ? copy(document, refused) : null;
}

/**
 * Swedish copy for every rule the items break, one sentence group per rule,
 * or `null` when the server would accept them. Questions are named by the
 * question list's labels.
 */
export function examWorkspaceSaveRefusalCopy(document: NativeExamDocument): string | null {
  const refusals = [
    refusal(document, isIncompleteMatchingItem, incompleteMatchKeyCopy),
    refusal(
      document,
      hasNegativePoints,
      (named, refused) =>
        `${questionSubject(named, refused)} har negativa poäng. ${NEGATIVE_POINTS_GUIDANCE}`,
    ),
    refusal(
      document,
      hasEmptyCriterionText,
      (named, refused) =>
        `${questionSubject(named, refused)} har ett kriterium utan text. Skriv text i varje kriterium.`,
    ),
    refusal(
      document,
      hasInvalidCriterionPoints,
      (named, refused) =>
        `${questionSubject(named, refused)} har ett kriterium med ogiltiga poäng. ${INVALID_CRITERION_POINTS_GUIDANCE}`,
    ),
    refusal(
      document,
      hasCriteriaPointsMismatch,
      (named, refused) =>
        `${questionSubject(named, refused)} har kriterier vars poängsumma inte stämmer med frågans poäng. ${CRITERIA_POINTS_MISMATCH_GUIDANCE}`,
    ),
    refusal(
      document,
      hasCriteriaOnWrongKind,
      (named, refused) =>
        `${questionSubject(named, refused)} har kriterier men är inte en fritextfråga. ${CRITERIA_ON_WRONG_KIND_GUIDANCE}`,
    ),
  ].filter((copy): copy is string => copy !== null);
  return refusals.length > 0 ? refusals.join(" ") : null;
}
