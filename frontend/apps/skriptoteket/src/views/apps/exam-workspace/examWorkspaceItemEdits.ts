/**
 * Exam workspace item edits.
 *
 * Domain purpose:
 *   Each teacher edit the editor offers on one item, as a pure transition from
 *   the item before the edit to the item after it, and the new question a
 *   teacher adds. A teacher edit keys the item only while it still carries key
 *   data.
 *
 * Relationships:
 *   - Applied by `useExamWorkspaceDocument` through its one item patch path.
 */

import type {
  NativeAnswerKeySuggestion,
  NativeExamAnswerKeyOrigin,
  NativeExamBodySegment,
  NativeExamItem,
  NativeExamMatchPair,
} from "../../../api/examWorkspace";
import { hasInvalidAnswerKey } from "./examWorkspaceAnswerKeyRules";

function teacherKeyOrigin(hasKeyData: boolean): NativeExamAnswerKeyOrigin {
  return hasKeyData ? "teacher_authored" : "absent";
}

export function withMarkingGuide(item: NativeExamItem, guide: string | null): NativeExamItem {
  return { ...item, marking_guide: guide };
}

/** A points value the teacher sets is no estimate from a section total. */
export function withPoints(item: NativeExamItem, points: number | null): NativeExamItem {
  return { ...item, points, points_estimated: false };
}

/** Replace one paragraph's segments, as serialized by the inline body editor. */
export function withParagraphSegments(
  item: NativeExamItem,
  paragraphIndex: number,
  segments: NativeExamBodySegment[],
): NativeExamItem {
  return {
    ...item,
    body: item.body.map((paragraph, candidateParagraphIndex) =>
      candidateParagraphIndex === paragraphIndex ? { segments } : paragraph,
    ),
  };
}

export function withChoiceText(
  item: NativeExamItem,
  choiceId: string,
  text: string,
): NativeExamItem {
  return {
    ...item,
    choices: item.choices.map((choice) =>
      choice.choice_id === choiceId ? { ...choice, text } : choice,
    ),
  };
}

export function withCorrectChoices(
  item: NativeExamItem,
  correctChoiceIds: string[],
): NativeExamItem {
  return {
    ...item,
    answer_key: {
      ...item.answer_key,
      correct_choice_ids: correctChoiceIds,
      origin: teacherKeyOrigin(correctChoiceIds.length > 0),
    },
  };
}

export function withMatchEntryText(
  item: NativeExamItem,
  side: "left" | "right",
  entryId: string,
  text: string,
): NativeExamItem {
  return side === "left"
    ? {
        ...item,
        match_left: item.match_left.map((entry) =>
          entry.left_id === entryId ? { ...entry, text } : entry,
        ),
      }
    : {
        ...item,
        match_right: item.match_right.map((entry) =>
          entry.right_id === entryId ? { ...entry, text } : entry,
        ),
      };
}

export function withMatchPairs(item: NativeExamItem, pairs: NativeExamMatchPair[]): NativeExamItem {
  return {
    ...item,
    answer_key: {
      ...item.answer_key,
      match_pairs: pairs,
      origin: teacherKeyOrigin(pairs.length > 0),
    },
  };
}

export function withGapValues(
  item: NativeExamItem,
  gapId: string,
  acceptedValues: string[],
): NativeExamItem {
  const gaps = item.gaps.map((gap) =>
    gap.gap_id === gapId ? { ...gap, accepted_values: acceptedValues } : gap,
  );
  const hasKeyData = gaps.some((gap) => gap.accepted_values.length > 0);
  return {
    ...item,
    answer_key: { ...item.answer_key, origin: teacherKeyOrigin(hasKeyData) },
    gaps,
  };
}

export function reviewed(item: NativeExamItem): NativeExamItem {
  return {
    ...item,
    answer_key:
      item.answer_key.origin === "machine_proposed"
        ? { ...item.answer_key, origin: "reviewed_advisory" }
        : item.answer_key,
    review: { ...item.review, state: "review_complete" },
  };
}

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
  return {
    ...item,
    ai_suggestion: suggestion,
    answer_key: {
      correct_choice_ids: [...suggestion.correct_choice_ids],
      match_pairs: suggestion.match_pairs.map((pair) => ({ ...pair })),
      origin: "machine_proposed",
    },
    gaps,
    review: { ...item.review, state: "review_required" },
  };
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
 * arrivals and the suggestion fits the question. Any other key stays.
 */
export function withArrivingSuggestion(
  item: NativeExamItem,
  suggestion: NativeAnswerKeySuggestion,
): NativeExamItem {
  if (keyFollowsArrivals(item) && suggestionFitsItem(item, suggestion)) {
    return withSuggestionAsKey(item, suggestion);
  }
  return { ...item, ai_suggestion: suggestion };
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

/** The free-text question a teacher adds after the last item. */
export function newTeacherItem(itemId: string, sequence: number): NativeExamItem {
  return {
    ai_suggestion: null,
    answer_key: { correct_choice_ids: [], match_pairs: [], origin: "not_applicable" },
    body: [{ segments: [{ kind: "text", text: "Ny fråga" }] }],
    choices: [],
    gaps: [],
    item_id: itemId,
    kind: "free_text",
    match_left: [],
    match_right: [],
    points: null,
    points_estimated: false,
    review: {
      confidence: null,
      parse_origin: "teacher_created",
      reasons: [],
      state: "review_complete",
    },
    sequence,
    source_anchor: null,
  };
}
