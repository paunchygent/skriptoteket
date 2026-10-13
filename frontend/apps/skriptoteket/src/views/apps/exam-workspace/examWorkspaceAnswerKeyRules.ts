/**
 * Exam workspace answer-key completeness rules.
 *
 * Domain purpose:
 *   Decide whether a gap item carries a partial answer key (keyed, but with
 *   empty accepted values in some gaps) or a matching item carries an
 *   incomplete pair list (keyed, but not every left entry in exactly one
 *   pair, or a right entry in more than one pair), and build the Swedish guidance copy the teacher sees
 *   inline and when a save is refused. Also decide whether an item's key
 *   breaks any rule the server applies to a saved key, which decides
 *   whether an AI suggestion fits its question.
 *
 * Relationships:
 *   - Pure functions consumed by `examWorkspaceItemSaveRules`,
 *     `examWorkspaceItemReadiness`, `ExamWorkspaceBodyEditor`, and
 *     `examWorkspaceItemEdits` (suggestion fit).
 *   - Mirrors `NativeExamItem._answer_key_invariants` in
 *     `domain/curated_apps/exam_workspace/native_exam_document.py`.
 *   - Reads shapes from `api/examWorkspace.ts`.
 */

import type { NativeExamItem } from "../../../api/examWorkspace";

export const PARTIAL_GAP_KEY_GUIDANCE =
  "Fyll i godkända svar för varje lucka, eller lämna alla luckor tomma om frågan ska sakna facit.";

export const INCOMPLETE_MATCH_KEY_GUIDANCE =
  "Välj ett svar för varje rad. Ett svar får användas högst en gång; svar som inte hör till någon rad får stå kvar. Eller lämna alla rader utan svar om frågan ska sakna facit.";

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

function countOf(id: string, pairIds: string[]): number {
  return pairIds.filter((pairId) => pairId === id).length;
}

/**
 * A keyed matching item needs every left entry in exactly one pair and each
 * right entry in at most one pair (unpaired right entries are distractors),
 * and no pair naming an unknown entry; the server refuses anything else.
 */
export function isIncompleteMatchingItem(item: NativeExamItem): boolean {
  if (item.kind !== "matching" || !hasKeyedOrigin(item)) {
    return false;
  }
  const leftIds = item.match_left.map((left) => left.left_id);
  const rightIds = item.match_right.map((right) => right.right_id);
  const pairs = item.answer_key.match_pairs;
  const pairLeftIds = pairs.map((pair) => pair.left_id);
  const pairRightIds = pairs.map((pair) => pair.right_id);
  const namesOnlyKnownEntries =
    pairLeftIds.every((id) => leftIds.includes(id)) &&
    pairRightIds.every((id) => rightIds.includes(id));
  return !(
    namesOnlyKnownEntries &&
    leftIds.every((id) => countOf(id, pairLeftIds) === 1) &&
    rightIds.every((id) => countOf(id, pairRightIds) <= 1)
  );
}

/**
 * Whether the item's answer key breaks a rule the server applies to a saved
 * key (`_answer_key_invariants`): a free-text question carries no key; a
 * keyed kind has no `not_applicable` key; an absent key carries no key
 * data; only matching items key pairs; correct choices are declared
 * choices, exactly one for single choice and at least one for multiple
 * response; matching keys pair every left entry once; gap keys fill every
 * gap; neither keys choices.
 */
export function hasInvalidAnswerKey(item: NativeExamItem): boolean {
  const key = item.answer_key;
  if (item.kind === "free_text") {
    return (
      key.origin !== "not_applicable" ||
      key.correct_choice_ids.length > 0 ||
      key.match_pairs.length > 0
    );
  }
  if (key.origin === "not_applicable") {
    return true;
  }
  if (key.match_pairs.length > 0 && item.kind !== "matching") {
    return true;
  }
  if (key.origin === "absent") {
    return (
      key.correct_choice_ids.length > 0 ||
      key.match_pairs.length > 0 ||
      item.gaps.some((gap) => gap.accepted_values.length > 0)
    );
  }
  const declared = new Set(item.choices.map((choice) => choice.choice_id));
  if (key.correct_choice_ids.some((choiceId) => !declared.has(choiceId))) {
    return true;
  }
  switch (item.kind) {
    case "single_choice":
      return key.correct_choice_ids.length !== 1;
    case "multiple_response":
      return key.correct_choice_ids.length === 0;
    case "matching":
      return key.correct_choice_ids.length > 0 || isIncompleteMatchingItem(item);
    case "gap_fill":
      return key.correct_choice_ids.length > 0 || isPartiallyKeyedGapItem(item);
  }
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

export function incompleteMatchKeyCopy(items: NativeExamItem[]): string {
  return `${questionSubject(items)} har en matchning där facit inte är komplett. ${INCOMPLETE_MATCH_KEY_GUIDANCE}`;
}
