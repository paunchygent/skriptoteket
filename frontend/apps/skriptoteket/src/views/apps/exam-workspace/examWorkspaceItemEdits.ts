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
  NativeExamCriterion,
  NativeExamItem,
  NativeExamMatchPair,
} from "../../../api/examWorkspace";
import { criteriaPointsTotal } from "./examWorkspaceItemSaveRules";

function teacherKeyOrigin(hasKeyData: boolean): NativeExamAnswerKeyOrigin {
  return hasKeyData ? "teacher_authored" : "absent";
}

/**
 * Replace the item's criteria. A non-empty list is the teacher's point
 * breakdown: the item's points become the exact sum of the criterion points
 * and stop being an estimate from a printed section total.
 */
export function withCriteria(
  item: NativeExamItem,
  criteria: NativeExamCriterion[],
): NativeExamItem {
  if (criteria.length === 0) {
    return { ...item, criteria };
  }
  return {
    ...item,
    criteria,
    points: criteriaPointsTotal(criteria),
    points_estimated: false,
  };
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

/**
 * A Kategorisera grid's points are its tick value times its ticks (Q10); an
 * unkeyed grid has no points. Both values carry at most 2 decimals, so the
 * product is rounded to 2 decimals to drop floating-point noise.
 */
function gridPoints(tickPoints: string | null, tickCount: number): number | null {
  if (tickPoints === null || tickCount === 0) {
    return null;
  }
  return Math.round(Number(tickPoints) * tickCount * 100) / 100;
}

/**
 * Re-derive a grid's points after its key changed by any route other than a
 * tick edit: undoing an interpretation or writing a suggestion. Non-grid items
 * and an unchanged total pass through; a changed total is no longer an estimate.
 */
export function withGridPoints(item: NativeExamItem): NativeExamItem {
  if (item.kind !== "matching") {
    return item;
  }
  const points = gridPoints(item.tick_points, item.answer_key.match_pairs.length);
  return points === item.points ? item : { ...item, points, points_estimated: false };
}

export function withMatchPairs(item: NativeExamItem, pairs: NativeExamMatchPair[]): NativeExamItem {
  return {
    ...item,
    answer_key: {
      ...item.answer_key,
      match_pairs: pairs,
      origin: teacherKeyOrigin(pairs.length > 0),
    },
    points: gridPoints(item.tick_points, pairs.length),
    points_estimated: false,
  };
}

/** Set the grid's value per correct tick; its points follow from the ticks. */
export function withTickPoints(item: NativeExamItem, tickPoints: string): NativeExamItem {
  return {
    ...item,
    tick_points: tickPoints,
    points: gridPoints(tickPoints, item.answer_key.match_pairs.length),
    points_estimated: false,
  };
}

/** The key value under the server's spelling policy: collapsed whitespace and folded case. */
function normalizedAnswer(value: string): string {
  return value.trim().replace(/\s+/g, " ").toLocaleLowerCase("sv-SE");
}

/** Every accepted answer the question holds, in gap order and without duplicates. */
export function itemAcceptedAnswers(item: NativeExamItem): string[] {
  const seen = new Set<string>();
  const answers: string[] = [];
  for (const gap of item.gaps) {
    for (const value of gap.accepted_values) {
      if (!seen.has(value)) {
        seen.add(value);
        answers.push(value);
      }
    }
  }
  return answers;
}

/**
 * Append produced misspellings to one gap's automatic values, keeping the
 * existing ones: a value the question already accepts as a gold answer, one
 * the gap already carries, and one the teacher suppressed are all dropped
 * under the server's spelling policy (collapsed whitespace, folded case), and
 * the rest keep the producer's order and their display form.
 */
export function withAutomaticValues(
  item: NativeExamItem,
  gapId: string,
  values: string[],
): NativeExamItem {
  const gap = item.gaps.find((candidate) => candidate.gap_id === gapId);
  if (!gap || values.length === 0) {
    return item;
  }
  const known = new Set([
    ...itemAcceptedAnswers(item).map(normalizedAnswer),
    ...gap.automatic_values.map(normalizedAnswer),
    ...gap.excluded_automatic_values.map(normalizedAnswer),
  ]);
  const added: string[] = [];
  for (const value of values) {
    const normalized = normalizedAnswer(value);
    if (normalized.length > 0 && !known.has(normalized)) {
      known.add(normalized);
      added.push(value);
    }
  }
  if (added.length === 0) {
    return item;
  }
  return {
    ...item,
    gaps: item.gaps.map((candidate) =>
      candidate.gap_id === gapId
        ? { ...candidate, automatic_values: [...candidate.automatic_values, ...added] }
        : candidate,
    ),
  };
}

export function withGapValues(
  item: NativeExamItem,
  gapId: string,
  acceptedValues: string[],
): NativeExamItem {
  const current = item.gaps.find((gap) => gap.gap_id === gapId);
  if (
    !current ||
    (current.accepted_values.length === acceptedValues.length &&
      current.accepted_values.every((value, index) => value === acceptedValues[index]))
  ) {
    return item;
  }
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

/**
 * Remove the conversion interpretation without losing the teacher's source
 * facit. A spelling the teacher suppressed stays suppressed.
 */
export function withoutInterpretedKey(item: NativeExamItem): NativeExamItem {
  if (item.answer_key.origin !== "ai_interpreted") {
    return item;
  }
  return withGridPoints({
    ...item,
    answer_key: { ...item.answer_key, origin: "absent", correct_choice_ids: [], match_pairs: [] },
    gaps: item.gaps.map((gap) => ({ ...gap, accepted_values: [], automatic_values: [] })),
  });
}

/**
 * Remove only the selected automatic answer, preserving the key's
 * provenance, and suppress it so no later reply or regeneration adds it back.
 */
export function withoutAutomaticValue(
  item: NativeExamItem,
  gapId: string,
  value: string,
): NativeExamItem {
  const gap = item.gaps.find((candidate) => candidate.gap_id === gapId);
  const normalized = normalizedAnswer(value);
  if (
    !gap ||
    normalized.length === 0 ||
    !gap.automatic_values.some((entry) => normalizedAnswer(entry) === normalized)
  ) {
    return item;
  }
  const suppressed = gap.excluded_automatic_values.some(
    (entry) => normalizedAnswer(entry) === normalized,
  );
  return {
    ...item,
    gaps: item.gaps.map((candidate) =>
      candidate.gap_id === gapId
        ? {
            ...candidate,
            automatic_values: candidate.automatic_values.filter(
              (entry) => normalizedAnswer(entry) !== normalized,
            ),
            excluded_automatic_values: suppressed
              ? candidate.excluded_automatic_values
              : [...candidate.excluded_automatic_values, value],
          }
        : candidate,
    ),
  };
}

/** Keep at least one gap and the item's points when turning an answer into text. */
export function withGapAsText(item: NativeExamItem, gapId: string): NativeExamItem {
  const gap = item.gaps.find((candidate) => candidate.gap_id === gapId);
  const text = gap?.accepted_values[0];
  if (item.gaps.length <= 1 || !text) {
    return item;
  }
  return {
    ...item,
    gaps: item.gaps.filter((candidate) => candidate.gap_id !== gapId),
    body: item.body.map((paragraph) => ({
      ...paragraph,
      segments: paragraph.segments.map((segment) =>
        segment.kind === "gap" && segment.gap_id === gapId
          ? { kind: "text" as const, text }
          : segment,
      ),
    })),
  };
}

export function reviewed(item: NativeExamItem): NativeExamItem {
  return {
    ...item,
    answer_key:
      item.answer_key.origin === "machine_proposed" || item.answer_key.origin === "ai_interpreted"
        ? { ...item.answer_key, origin: "reviewed_advisory" }
        : item.answer_key,
    review: { ...item.review, state: "review_complete" },
  };
}

/** The kinds of question a teacher adds from "Ny fråga". */
export type TeacherItemKind = "free_text" | "short_answer";

/**
 * The question a teacher adds after the last item: a free-text question, or a
 * short answer, which is a Lucktext with one gap after the question text (Q14).
 */
export function newTeacherItem(
  itemId: string,
  sequence: number,
  kind: TeacherItemKind,
): NativeExamItem {
  const question = { segments: [{ kind: "text" as const, text: "Ny fråga" }] };
  const shortAnswer = kind === "short_answer";
  return {
    ai_suggestion: null,
    facit_text: null,
    criteria: [],
    printed_label: null,
    retry_source: null,
    // A Fritext carries no key; a short answer starts unkeyed until the teacher keys its gap.
    answer_key: {
      correct_choice_ids: [],
      match_pairs: [],
      origin: shortAnswer ? "absent" : "not_applicable",
    },
    body: shortAnswer
      ? [question, { segments: [{ kind: "gap", gap_id: "gap_001" }] }]
      : [question],
    choices: [],
    gaps: shortAnswer
      ? [{ gap_id: "gap_001", accepted_values: [], automatic_values: [], excluded_automatic_values: [] }]
      : [],
    item_id: itemId,
    kind: shortAnswer ? "gap_fill" : "free_text",
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
    tick_points: null,
  };
}
