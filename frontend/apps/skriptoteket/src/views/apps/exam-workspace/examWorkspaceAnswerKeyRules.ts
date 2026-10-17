/**
 * Exam workspace answer-key completeness rules.
 *
 * Domain purpose:
 *   Decide whether a gap item carries a partial answer key (keyed, but with
 *   empty accepted values in some gaps) or a Kategorisera grid carries an
 *   incomplete tick list (keyed, but a row without a tick, a repeated tick or
 *   a tick naming an unknown entry), and build the Swedish guidance copy the teacher sees
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
  "Kryssa minst en kategori för varje rad, eller lämna alla rader utan kryss om frågan ska sakna facit.";

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

/**
 * A keyed Kategorisera grid needs at least one tick in every row, no repeated
 * tick and no tick naming an unknown entry (Q9); a column may hold several
 * ticks or none. The server refuses anything else.
 */
export function isIncompleteMatchingItem(item: NativeExamItem): boolean {
  if (item.kind !== "matching" || !hasKeyedOrigin(item)) {
    return false;
  }
  const leftIds = item.match_left.map((left) => left.left_id);
  const rightIds = item.match_right.map((right) => right.right_id);
  const pairs = item.answer_key.match_pairs;
  const pairKeys = pairs.map((pair) => `${pair.left_id} ${pair.right_id}`);
  const namesOnlyKnownEntries = pairs.every(
    (pair) => leftIds.includes(pair.left_id) && rightIds.includes(pair.right_id),
  );
  return !(
    namesOnlyKnownEntries &&
    new Set(pairKeys).size === pairKeys.length &&
    leftIds.every((id) => pairs.some((pair) => pair.left_id === id))
  );
}

/**
 * Whether the item's answer key breaks a rule the server applies to a saved
 * key (`_answer_key_invariants`): a free-text question carries no key; a
 * keyed kind has no `not_applicable` key; an absent key carries no key
 * data; only matching items key pairs; correct choices are declared
 * choices, exactly one for single choice and at least one for multiple
 * response; matching keys pair every left entry once; gap keys fill every
 * gap; inline-choice keys select an option declared in each gap and carry
 * no typed values; neither
 * gap kind keys top-level choices.
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
      item.gaps.some((gap) => gap.accepted_values.length > 0 || gap.correct_option_id !== null)
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
    case "inline_choice":
      return key.correct_choice_ids.length > 0 || item.gaps.some((gap) =>
        gap.accepted_values.length > 0 ||
        gap.automatic_values.length > 0 ||
        gap.excluded_automatic_values.length > 0 ||
        gap.correct_option_id === null ||
        !gap.options.some((option) => option.choice_id === gap.correct_option_id),
      );
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
  return `${questionSubject(items)} har en kategorisering där facit inte är komplett. ${INCOMPLETE_MATCH_KEY_GUIDANCE}`;
}
