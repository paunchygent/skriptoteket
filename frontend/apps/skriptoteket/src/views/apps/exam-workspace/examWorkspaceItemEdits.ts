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

function teacherKeyOrigin(hasKeyData: boolean): NativeExamAnswerKeyOrigin {
  return hasKeyData ? "teacher_authored" : "absent";
}

export function withTitle(item: NativeExamItem, title: string): NativeExamItem {
  return { ...item, title: title.trim().length > 0 ? title : null };
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

function keyMatchesSuggestion(
  item: NativeExamItem,
  suggestion: NativeAnswerKeySuggestion,
): boolean {
  const key = item.answer_key;
  if (key.correct_choice_ids.length !== suggestion.correct_choice_ids.length) {
    return false;
  }
  if (!key.correct_choice_ids.every((id) => suggestion.correct_choice_ids.includes(id))) {
    return false;
  }
  if (key.match_pairs.length !== suggestion.match_pairs.length) {
    return false;
  }
  const suggestedPairs = new Set(suggestion.match_pairs.map((p) => `${p.left_id}:${p.right_id}`));
  if (!key.match_pairs.every((p) => suggestedPairs.has(`${p.left_id}:${p.right_id}`))) {
    return false;
  }
  const suggestedGaps = new Map(
    suggestion.gap_accepted_values.map((entry) => [entry.gap_id, entry.accepted_values]),
  );
  return item.gaps.every((gap) => {
    const suggested = suggestedGaps.get(gap.gap_id) ?? [];
    return (
      gap.accepted_values.length === suggested.length &&
      gap.accepted_values.every((value) => suggested.includes(value))
    );
  });
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
 * Write an arriving AI suggestion onto its question (T5). The suggestion
 * is always kept on the question; it also becomes the key, as
 * `machine_proposed` with review required, only where the question has no
 * key or its key is the previous suggestion's key. Any other key stays.
 */
export function withArrivingSuggestion(
  item: NativeExamItem,
  suggestion: NativeAnswerKeySuggestion,
): NativeExamItem {
  const previous = item.ai_suggestion ?? null;
  const becomesKey =
    item.answer_key.origin === "absent" ||
    (previous !== null && keyMatchesSuggestion(item, previous));
  if (becomesKey) {
    return withSuggestionAsKey(item, suggestion);
  }
  return { ...item, ai_suggestion: suggestion };
}

/** Whether two kept suggestions carry exactly the same proposal and lineage. */
export function suggestionsEqual(
  left: NativeAnswerKeySuggestion | null | undefined,
  right: NativeAnswerKeySuggestion | null | undefined,
): boolean {
  if (!left || !right) {
    return false;
  }
  const stringArraysEqual = (a: string[], b: string[]): boolean =>
    a.length === b.length && a.every((value, index) => value === b[index]);
  return (
    stringArraysEqual(left.correct_choice_ids, right.correct_choice_ids) &&
    left.match_pairs.length === right.match_pairs.length &&
    left.match_pairs.every(
      (pair, index) =>
        pair.left_id === right.match_pairs[index].left_id &&
        pair.right_id === right.match_pairs[index].right_id,
    ) &&
    left.gap_accepted_values.length === right.gap_accepted_values.length &&
    left.gap_accepted_values.every(
      (entry, index) =>
        entry.gap_id === right.gap_accepted_values[index].gap_id &&
        stringArraysEqual(entry.accepted_values, right.gap_accepted_values[index].accepted_values),
    ) &&
    left.fingerprint === right.fingerprint &&
    left.provider_profile_id === right.provider_profile_id &&
    left.model === right.model &&
    left.prompt_template_version === right.prompt_template_version
  );
}

/** Make the kept suggestion the key again: `machine_proposed`, review required (T6). */
export function withRestoredSuggestion(item: NativeExamItem): NativeExamItem {
  const suggestion = item.ai_suggestion ?? null;
  if (!suggestion) {
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
    title: null,
  };
}
