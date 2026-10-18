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
  NativeExamBodyParagraph,
  NativeExamBodySegment,
  NativeExamChoice,
  NativeExamCriterion,
  NativeExamGap,
  NativeExamItem,
  NativeExamItemKind,
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

/** Replace one paragraph's rich text, keeping its heading level. */
export function withParagraphSegments(
  item: NativeExamItem,
  paragraphIndex: number,
  segments: NativeExamBodySegment[],
): NativeExamItem {
  return {
    ...item,
    body: item.body.map((paragraph, candidateParagraphIndex) =>
      candidateParagraphIndex === paragraphIndex ? { ...paragraph, segments } : paragraph,
    ),
  };
}

/** Set one paragraph's heading level; null returns it to body text. */
export function withParagraphHeading(
  item: NativeExamItem,
  paragraphIndex: number,
  headingLevel: NativeExamBodyParagraph["heading_level"],
): NativeExamItem {
  return {
    ...item,
    body: item.body.map((paragraph, candidateParagraphIndex) =>
      candidateParagraphIndex === paragraphIndex ? { ...paragraph, heading_level: headingLevel } : paragraph,
    ),
  };
}

/** Replace one choice's rich paragraphs. */
export function withChoiceBody(
  item: NativeExamItem,
  choiceId: string,
  body: NativeExamBodyParagraph[],
): NativeExamItem {
  return {
    ...item,
    choices: item.choices.map((choice) =>
      choice.choice_id === choiceId ? { ...choice, body } : choice,
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

/** Replace one matching entry's rich paragraphs. */
export function withMatchEntryBody(
  item: NativeExamItem,
  side: "left" | "right",
  entryId: string,
  body: NativeExamBodyParagraph[],
): NativeExamItem {
  return side === "left"
    ? {
        ...item,
        match_left: item.match_left.map((entry) =>
          entry.left_id === entryId ? { ...entry, body } : entry,
        ),
      }
    : {
        ...item,
        match_right: item.match_right.map((entry) =>
          entry.right_id === entryId ? { ...entry, body } : entry,
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

/** Replace one dropdown gap's options and its correct option; the same item when nothing changes. */
export function withGapOptions(
  item: NativeExamItem,
  gapId: string,
  options: NativeExamChoice[],
  correctOptionId: string,
): NativeExamItem {
  const current = item.gaps.find((gap) => gap.gap_id === gapId);
  if (
    !current ||
    (current.correct_option_id === correctOptionId &&
      current.options.length === options.length &&
      current.options.every((option, index) => option === options[index]))
  ) {
    return item;
  }
  return {
    ...item,
    gaps: item.gaps.map((gap) =>
      gap.gap_id === gapId ? { ...gap, options, correct_option_id: correctOptionId } : gap,
    ),
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
          ? { kind: "text" as const, text, marks: [] }
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

/** The teacher has reviewed the question and every AI-written answer key on it. */
export function isTeacherReviewed(item: NativeExamItem): boolean {
  const origin = item.answer_key.origin;
  return item.review.state === "review_complete" && origin !== "machine_proposed" && origin !== "ai_interpreted";
}

/** Takes back "Granskad"; the answer key keeps its reviewed origin until the teacher undoes. */
export function unreviewed(item: NativeExamItem): NativeExamItem {
  return { ...item, review: { ...item.review, state: "review_required" } };
}

/** The kinds of question a teacher adds from "Ny uppgift": every item kind, and Kort svar. */
export type TeacherItemKind = NativeExamItemKind | "short_answer";

/** An empty paragraph, as the server writes one: a text segment needs one character. */
function blankBody(): NativeExamBodyParagraph[] {
  return [{ heading_level: null, segments: [{ kind: "text", text: " ", marks: [] }] }];
}

function blankChoices(): NativeExamChoice[] {
  return ["choice_001", "choice_002"].map((choiceId) => ({ body: blankBody(), choice_id: choiceId }));
}

function blankGap(inlineChoice: boolean): NativeExamGap {
  return {
    accepted_values: [],
    automatic_values: [],
    correct_option_id: inlineChoice ? "choice_001" : null,
    excluded_automatic_values: [],
    gap_id: "gap_001",
    options: inlineChoice ? blankChoices() : [],
  };
}

/**
 * The question a teacher adds: "Ny fråga" with the kind's empty structure,
 * the same structure the server gives a question it retypes (TASK-SKRIPT-39-06-05).
 * Choice kinds get two empty choices, gap kinds one gap after the question
 * text (Kort svar is a Lucktext with one gap, Q14), a rullista one gap whose
 * first empty option is the key, and Kategorisera one row, two categories and
 * a zero tick value. Empty texts block export until the teacher fills them in.
 */
export function newTeacherItem(
  itemId: string,
  sequence: number,
  teacherKind: TeacherItemKind,
): NativeExamItem {
  const kind: NativeExamItemKind = teacherKind === "short_answer" ? "gap_fill" : teacherKind;
  const question: NativeExamBodyParagraph = {
    heading_level: null,
    segments: [{ kind: "text", text: "Ny fråga", marks: [] }],
  };
  const gapped = kind === "gap_fill" || kind === "inline_choice";
  const choice = kind === "single_choice" || kind === "multiple_response";
  const matching = kind === "matching";
  return {
    ai_suggestion: null,
    import_record: null,
    facit_text: null,
    criteria: [],
    printed_label: null,
    retry_source: null,
    answer_key: {
      correct_choice_ids: [],
      match_pairs: [],
      origin:
        kind === "free_text"
          ? "not_applicable"
          : kind === "inline_choice"
            ? "teacher_authored"
            : "absent",
    },
    body: gapped
      ? [question, { heading_level: null, segments: [{ kind: "gap", gap_id: "gap_001" }] }]
      : [question],
    choices: choice ? blankChoices() : [],
    gaps: gapped ? [blankGap(kind === "inline_choice")] : [],
    item_id: itemId,
    kind,
    match_left: matching ? [{ body: blankBody(), left_id: "left_001" }] : [],
    match_right: matching
      ? ["right_001", "right_002"].map((rightId) => ({ body: blankBody(), right_id: rightId }))
      : [],
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
    suggested_kind: null,
    tick_points: matching ? "0" : null,
  };
}
