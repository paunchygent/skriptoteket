/**
 * Exam workspace AI suggestion edits.
 *
 * Domain purpose:
 *   Write an arriving AI answer-key suggestion onto its question, and restore
 *   a kept suggestion as the key. A suggestion becomes the key only where the
 *   key follows arrivals and the suggestion fits the question as it is now.
 *
 * Relationships:
 *   - Applied by `useExamWorkspaceDocument` and `useExamWorkspaceSaveArrivals`.
 *   - Uses `withGridPoints` from `examWorkspaceItemEdits` so a grid keeps its
 *     points equal to its tick value times its ticks.
 */

import type {
  NativeAnswerKeySuggestion,
  NativeExamItem,
  NativeExamMatchPair,
} from "../../../api/examWorkspace";
import { hasInvalidAnswerKey } from "./examWorkspaceAnswerKeyRules";
import { withGridPoints } from "./examWorkspaceItemEdits";

function sameSet(left: string[], right: string[]): boolean {
  const leftSet = new Set(left);
  const rightSet = new Set(right);
  return leftSet.size === rightSet.size && [...leftSet].every((value) => rightSet.has(value));
}

function pairIds(pairs: NativeExamMatchPair[]): string[] {
  return pairs.map((pair) => `${pair.left_id}:${pair.right_id}`);
}

/**
 * Whether the item's current key is this suggestion's whole key, in any
 * order: the same choice ids, the same match pairs and the same gaps with
 * the same accepted values, each compared as sets. A gap without values
 * carries no key data. A historical id the suggestion still names, or any
 * other extra or missing entry, makes them unequal.
 */
function keyMatchesSuggestion(
  item: NativeExamItem,
  suggestion: NativeAnswerKeySuggestion,
): boolean {
  const key = item.answer_key;
  const keyedGaps = item.gaps.filter((gap) => gap.accepted_values.length > 0);
  const suggestedGaps = new Map(
    suggestion.gap_accepted_values.map((entry) => [entry.gap_id, entry.accepted_values]),
  );
  return (
    sameSet(key.correct_choice_ids, suggestion.correct_choice_ids) &&
    sameSet(pairIds(key.match_pairs), pairIds(suggestion.match_pairs)) &&
    sameSet(
      keyedGaps.map((gap) => gap.gap_id),
      [...suggestedGaps.keys()],
    ) &&
    keyedGaps.every((gap) => sameSet(gap.accepted_values, suggestedGaps.get(gap.gap_id) ?? []))
  );
}

/** Write a suggestion's key onto the item as `machine_proposed`, review required. */
function withSuggestionAsKey(
  item: NativeExamItem,
  suggestion: NativeAnswerKeySuggestion,
): NativeExamItem {
  const gaps = item.gaps.map((gap) => {
    const suggested = suggestion.gap_accepted_values.find((entry) => entry.gap_id === gap.gap_id);
    return suggested ? { ...gap, accepted_values: [...suggested.accepted_values] } : gap;
  });
  return withGridPoints({
    ...item,
    ai_suggestion: suggestion,
    answer_key: {
      correct_choice_ids: [...suggestion.correct_choice_ids],
      match_pairs: suggestion.match_pairs.map((pair) => ({ ...pair })),
      origin: "machine_proposed",
    },
    gaps,
    review: { ...item.review, state: "review_required" },
  });
}

/**
 * Whether the suggestion would be a valid key for the question as it is
 * now (P13): a gap suggestion names exactly the question's gaps, and the
 * key it makes breaks no rule the server applies to a saved key. A
 * suggestion naming a choice, match entry or gap the question no longer
 * has, or missing one it now has, does not fit.
 */
function suggestionFitsItem(
  item: NativeExamItem,
  suggestion: NativeAnswerKeySuggestion,
): boolean {
  const suggestedGapIds = suggestion.gap_accepted_values.map((entry) => entry.gap_id);
  if (
    suggestedGapIds.length > 0 &&
    !sameSet(
      suggestedGapIds,
      item.gaps.map((gap) => gap.gap_id),
    )
  ) {
    return false;
  }
  return !hasInvalidAnswerKey(withSuggestionAsKey(item, suggestion));
}

/**
 * Whether this item's key gives way to an arriving suggestion (T5, P12):
 * only where the question has no key, or its key is an unreviewed
 * `machine_proposed` key equal to the previous suggestion. A source,
 * teacher or reviewed key stays, even when it equals the previous
 * suggestion.
 */
function keyFollowsArrivals(item: NativeExamItem): boolean {
  const origin = item.answer_key.origin;
  if (origin === "absent") {
    return true;
  }
  const previous = item.ai_suggestion ?? null;
  return (
    origin === "machine_proposed" &&
    item.review.state === "review_required" &&
    previous !== null &&
    keyMatchesSuggestion(item, previous)
  );
}

/**
 * Write an arriving AI suggestion onto its question (T5, P12, P13). The
 * suggestion is always kept on the question; it also becomes the key, as
 * `machine_proposed` with review required, only where the key follows
 * arrivals and the suggestion fits the question. Any other key stays. A
 * suggestion arriving on a question whose undo opened a retry spends it, so
 * the item keeps a `used` retry whether or not the suggestion becomes the key
 * (TASK-SKRIPT-40-04-26 D4).
 */
export function withArrivingSuggestion(
  item: NativeExamItem,
  suggestion: NativeAnswerKeySuggestion,
): NativeExamItem {
  const answerKeyRetry = item.answer_key_retry === "offered" ? "used" : item.answer_key_retry;
  if (keyFollowsArrivals(item) && suggestionFitsItem(item, suggestion)) {
    return { ...withSuggestionAsKey(item, suggestion), answer_key_retry: answerKeyRetry };
  }
  return { ...item, ai_suggestion: suggestion, answer_key_retry: answerKeyRetry };
}

/**
 * Make the kept suggestion the key again: `machine_proposed`, review
 * required (T6). A kept suggestion that no longer fits the question leaves
 * it unchanged, as the server refuses that key (P13).
 */
export function withRestoredSuggestion(item: NativeExamItem): NativeExamItem {
  const suggestion = item.ai_suggestion ?? null;
  if (!suggestion || !suggestionFitsItem(item, suggestion)) {
    return item;
  }
  return withSuggestionAsKey(item, suggestion);
}
