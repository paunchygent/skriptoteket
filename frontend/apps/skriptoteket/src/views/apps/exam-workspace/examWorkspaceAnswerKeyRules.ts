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

import type { NativeExamDocument, NativeExamGap, NativeExamItem } from "../../../api/examWorkspace";
import { examWorkspaceQuestionLabels } from "./examWorkspaceListEntries";

export const PARTIAL_GAP_KEY_GUIDANCE =
  "Fyll i godkända svar i varje lucka.";

export const INCOMPLETE_MATCH_KEY_GUIDANCE =
  "Kryssa minst en kategori för varje rad, eller lämna alla rader utan kryss om frågan ska sakna facit.";

/** Whether the question carries an answer key; a question without one has no empty gaps (Q9). */
export function hasKeyedOrigin(item: NativeExamItem): boolean {
  return item.answer_key.origin !== "absent" && item.answer_key.origin !== "not_applicable";
}

/** Dropdown gaps with no option marked correct: an empty gap is a valid draft (U4, L2). */
export function dropdownGapsWithoutCorrectOption(item: NativeExamItem): NativeExamGap[] {
  return item.kind === "inline_choice" ? item.gaps.filter((gap) => gap.correct_option_id === null) : [];
}

/** A keyed Lucktext item with a gap that holds no accepted answer (Q9).
 *
 * Saving accepts it as a draft (U4, L2); the export readiness and the
 * export drawer refuse it instead, naming the question by its list label.
 */
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
 * response; matching keys pair every left entry once; inline-choice keys
 * carry no typed values and a correct option that names a declared option,
 * but an empty dropdown gap (no correct option, possibly no options) is a
 * valid draft; neither
 * gap kind keys top-level choices. An empty gap is a valid draft
 * (TASK-SKRIPT-40-04-13 U4, L2): a keyed Lucktext gap needs no accepted
 * values to save and a keyed dropdown gap needs no correct option, so only
 * the export readiness flags them.
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
    case "ordering":
      // The key is the list order of the steps, so no key data can break a rule.
      return false;
    case "matching":
      return key.correct_choice_ids.length > 0 || isIncompleteMatchingItem(item);
    case "gap_fill":
      // An empty gap saves as a draft; the export readiness owns the refusal (U4, L2).
      return key.correct_choice_ids.length > 0;
    case "inline_choice":
      return key.correct_choice_ids.length > 0 || item.gaps.some((gap) =>
        gap.accepted_values.length > 0 ||
        gap.automatic_values.length > 0 ||
        gap.excluded_automatic_values.length > 0 ||
        // An empty dropdown gap saves as a draft; the export readiness owns the refusal (U4, L2).
        (gap.correct_option_id !== null &&
          !gap.options.some((option) => option.choice_id === gap.correct_option_id)),
      );
  }
}

function joinSwedishList(values: string[]): string {
  if (values.length <= 1) {
    return values.join("");
  }
  return `${values.slice(0, -1).join(", ")} och ${values[values.length - 1]}`;
}

/** "Fråga 4" for one question, "Frågorna 4 och 5" for several, using the list labels. */
export function questionSubject(document: NativeExamDocument, items: NativeExamItem[]): string {
  const labels = examWorkspaceQuestionLabels(document);
  const names = items.map((item) => {
    const label = labels.get(item.item_id);
    if (label === undefined) {
      throw new Error(`Missing list label for item ${item.item_id}`);
    }
    return label;
  });
  return names.length === 1
    ? `Fråga ${names[0]}`
    : `Frågorna ${joinSwedishList(names)}`;
}

export function partialGapKeyCopy(document: NativeExamDocument, items: NativeExamItem[]): string {
  return `${questionSubject(document, items)} saknar godkända svar i vissa luckor. ${PARTIAL_GAP_KEY_GUIDANCE}`;
}

export function incompleteMatchKeyCopy(document: NativeExamDocument, items: NativeExamItem[]): string {
  return `${questionSubject(document, items)} har en kategorisering där facit inte är komplett. ${INCOMPLETE_MATCH_KEY_GUIDANCE}`;
}
