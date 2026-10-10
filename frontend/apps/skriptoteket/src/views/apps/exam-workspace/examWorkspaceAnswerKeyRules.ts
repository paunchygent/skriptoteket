/**
 * Exam workspace answer-key completeness rules.
 *
 * Domain purpose:
 *   Decide whether a gap item carries a partial answer key (keyed, but with
 *   empty accepted values in some gaps) and build the Swedish guidance copy
 *   the teacher sees inline and when a save is refused.
 *
 * Relationships:
 *   - Pure functions consumed by `examWorkspaceItemSaveRules`,
 *     `examWorkspaceItemReadiness`, and `ExamWorkspaceBodyEditor`.
 *   - Reads shapes from `api/examWorkspace.ts`.
 */

import type { NativeExamItem } from "../../../api/examWorkspace";

export const PARTIAL_GAP_KEY_GUIDANCE =
  "Fyll i godkända svar för varje lucka, eller lämna alla luckor tomma om frågan ska sakna facit.";

function hasKeyedOrigin(item: NativeExamItem): boolean {
  return item.answer_key.origin !== "absent" && item.answer_key.origin !== "not_applicable";
}

/** Keyed gap items need accepted values in every gap; the server refuses partial keys. */
export function isPartiallyKeyedGapItem(item: NativeExamItem): boolean {
  return (
    item.kind === "gap_fill" &&
    hasKeyedOrigin(item) &&
    item.gaps.some((gap) => gap.accepted_values.length === 0)
  );
}

function joinSwedishList(values: string[]): string {
  if (values.length <= 1) {
    return values.join("");
  }
  return `${values.slice(0, -1).join(", ")} och ${values[values.length - 1]}`;
}

/** "Fråga 4" for one question, "Frågorna 4 och 5" for several. */
export function questionSubject(items: NativeExamItem[]): string {
  return items.length === 1
    ? `Fråga ${items[0]?.sequence}`
    : `Frågorna ${joinSwedishList(items.map((item) => String(item.sequence)))}`;
}

export function partialGapKeyCopy(items: NativeExamItem[]): string {
  return `${questionSubject(items)} saknar godkända svar i vissa luckor. ${PARTIAL_GAP_KEY_GUIDANCE}`;
}
