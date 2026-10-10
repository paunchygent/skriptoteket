/**
 * Exam workspace item save rules.
 *
 * Domain purpose:
 *   Name the item states the editor can reach but the server refuses to
 *   save, so the teacher sees them at the question and a save is refused
 *   with Swedish copy naming the questions instead of a generic failure.
 *   Mirrors these `NativeExamItem` field rules exactly: points must be
 *   greater than zero (`_positive_finite_points`), and choice text must not
 *   be empty (`NativeChoice.text`, `min_length=1`, not stripped). A partial
 *   gap key (`_answer_key_invariants`) comes from
 *   `examWorkspaceAnswerKeyRules`.
 *
 * Relationships:
 *   - Mirrors `domain/curated_apps/exam_workspace/native_exam_document.py`.
 *   - Consumed by `useExamWorkspaceDocument` (save refusal),
 *     `examWorkspaceItemReadiness` (per-question reasons), and
 *     `ExamWorkspaceItemEditor` (inline field hints).
 */

import type { NativeExamItem } from "../../../api/examWorkspace";
import {
  isPartiallyKeyedGapItem,
  partialGapKeyCopy,
  questionSubject,
} from "./examWorkspaceAnswerKeyRules";

export const NON_POSITIVE_POINTS_GUIDANCE = "Poängen måste vara större än noll.";
export const EMPTY_CHOICE_TEXT_GUIDANCE = "Ett svarsalternativ saknar text.";

export function hasNonPositivePoints(item: NativeExamItem): boolean {
  return typeof item.points === "number" && item.points <= 0;
}

export function isEmptyChoiceText(text: string): boolean {
  return text.length === 0;
}

export function hasEmptyChoiceText(item: NativeExamItem): boolean {
  return item.choices.some((choice) => isEmptyChoiceText(choice.text));
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
  ].filter((copy): copy is string => copy !== null);
  return refusals.length > 0 ? refusals.join(" ") : null;
}
