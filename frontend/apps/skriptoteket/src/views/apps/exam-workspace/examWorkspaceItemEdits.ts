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

/**
 * Move an advisory proposal into the editor as an unreviewed prefill
 * (`machine_proposed`, item marked `review_required`). With `approve`, the
 * teacher accepts the key unchanged in the same step, which records it as
 * `reviewed_advisory` and leaves the item's review state and reasons as
 * they were: parse-confidence review still needs the explicit
 * "mark reviewed" action.
 */
export function withProposal(
  item: NativeExamItem,
  proposedItem: NativeExamItem,
  approve: boolean,
): NativeExamItem {
  const gaps = item.gaps.map((gap) => {
    const proposedGap = proposedItem.gaps.find((candidate) => candidate.gap_id === gap.gap_id);
    return proposedGap ? { ...gap, accepted_values: proposedGap.accepted_values } : gap;
  });
  if (approve) {
    return {
      ...item,
      answer_key: { ...proposedItem.answer_key, origin: "reviewed_advisory" },
      gaps,
    };
  }
  return {
    ...item,
    answer_key: { ...proposedItem.answer_key, origin: "machine_proposed" },
    gaps,
    review: { ...item.review, state: "review_required" },
  };
}

/** The free-text question a teacher adds after the last item. */
export function newTeacherItem(itemId: string, sequence: number): NativeExamItem {
  return {
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
