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
  NativeExamChoice,
  NativeExamCriterion,
  NativeExamGap,
  NativeExamItem,
  NativeExamItemKind,
  NativeExamMatchPair,
} from "../../../api/examWorkspace";
import { criteriaPointsTotal } from "./examWorkspaceItemSaveRules";
import { plainBody } from "./examWorkspaceRichText";
import { placedGapIds } from "./examWorkspaceRichTextDocument";

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

/**
 * Replace the item's whole body. A gap record whose gap the new body no longer
 * places leaves with it, the rest keep their declared order; an edit never
 * adds a record.
 */
export function withBody(item: NativeExamItem, body: NativeExamBodyParagraph[]): NativeExamItem {
  const placed = new Set(placedGapIds(body));
  return { ...item, body, gaps: item.gaps.filter((gap) => placed.has(gap.gap_id)) };
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
  correctOptionId: string | null,
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
  const gaps = item.gaps.map((gap) =>
    gap.gap_id === gapId ? { ...gap, options, correct_option_id: correctOptionId } : gap,
  );
  // Only a changed correct option is the teacher's decision; a text, add,
  // remove or reorder edit leaves an AI or machine-proposed key unapproved.
  if (current.correct_option_id === correctOptionId) {
    return { ...item, gaps };
  }
  const hasKeyData = gaps.some((gap) => gap.correct_option_id !== null);
  return {
    ...item,
    answer_key: { ...item.answer_key, origin: teacherKeyOrigin(hasKeyData) },
    gaps,
  };
}

/**
 * The AI interpretation can be undone for every kind except a dropdown, which
 * has no valid keyless state.
 */
export function canUndoInterpretation(item: NativeExamItem): boolean {
  return item.answer_key.origin === "ai_interpreted" && item.kind !== "inline_choice";
}

/**
 * Remove the conversion interpretation without losing the teacher's source
 * facit. A spelling the teacher suppressed stays suppressed.
 */
export function withoutInterpretedKey(item: NativeExamItem): NativeExamItem {
  if (!canUndoInterpretation(item)) {
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

/** Replace a gap with its first accepted answer as plain text; a gap without an answer stays. */
export function withGapAsText(item: NativeExamItem, gapId: string): NativeExamItem {
  const gap = item.gaps.find((candidate) => candidate.gap_id === gapId);
  const text = gap?.accepted_values[0];
  if (!text) {
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

const GAP_ID_PATTERN = /^gap_([0-9]{3})$/;
const MAX_GAP_NUMBER = 999;

/**
 * The next free gap id above the item's highest declared or placed gap, as
 * `gap_NNN`; `gap_001` when there are none, null when the next number would
 * exceed 999. Ids outside the `gap_NNN` shape never count.
 */
export function nextGapId(item: NativeExamItem): string | null {
  let highest = 0;
  const candidates = [...item.gaps.map((gap) => gap.gap_id), ...placedGapIds(item.body)];
  for (const candidate of candidates) {
    const match = GAP_ID_PATTERN.exec(candidate);
    if (match) {
      highest = Math.max(highest, Number(match[1]));
    }
  }
  if (highest >= MAX_GAP_NUMBER) {
    return null;
  }
  return `gap_${String(highest + 1).padStart(3, "0")}`;
}

/**
 * The gap record one creation seeds: a Lucktext gap carries the converted
 * text as its accepted value, a dropdown gap carries it as its one correct
 * option, and an empty insertion carries a blank gap of the item's kind.
 */
function newGapRecord(kind: NativeExamItemKind, gapId: string, seed: string): NativeExamGap {
  const text = seed.trim();
  if (kind === "inline_choice") {
    const options: NativeExamChoice[] =
      text.length > 0
        ? [{ body: plainBody(text), choice_id: "choice_001" }]
        : blankChoices();
    return {
      accepted_values: [],
      automatic_values: [],
      correct_option_id: "choice_001",
      excluded_automatic_values: [],
      gap_id: gapId,
      options,
    };
  }
  return {
    accepted_values: text.length > 0 ? [text] : [],
    automatic_values: [],
    correct_option_id: null,
    excluded_automatic_values: [],
    gap_id: gapId,
    options: [],
  };
}

/**
 * Create one gap as one atomic structural item edit: the passed body plus the
 * new gap record together, mirroring `withGapAsText`. Kept records follow the
 * new body's placement order, so the gap's number follows the text; records
 * the new body no longer places leave with it. Anything but exactly one
 * placement of a new gap on a Lucktext or dropdown question returns the same
 * item. The written body is the passed body, so the editor's echo guard sees
 * JSON-equal content.
 */
export function withNewGap(
  item: NativeExamItem,
  body: NativeExamBodyParagraph[],
  gapId: string,
  seed: string,
): NativeExamItem {
  if (item.kind !== "gap_fill" && item.kind !== "inline_choice") {
    return item;
  }
  if (item.gaps.some((gap) => gap.gap_id === gapId)) {
    return item;
  }
  const placed = placedGapIds(body);
  if (placed.filter((placedId) => placedId === gapId).length !== 1) {
    return item;
  }
  const order = new Map(placed.map((placedId, index) => [placedId, index]));
  const position = order.get(gapId) ?? placed.length;
  const kept = item.gaps.filter((gap) => order.has(gap.gap_id));
  const record = newGapRecord(item.kind, gapId, seed);
  const insertAt = kept.findIndex((gap) => (order.get(gap.gap_id) ?? placed.length) > position);
  const gaps = [...kept];
  if (insertAt < 0) {
    gaps.push(record);
  } else {
    gaps.splice(insertAt, 0, record);
  }
  return { ...item, body, gaps };
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

/** An empty body, as the server writes one: no paragraph at all. */
function blankBody(): NativeExamBodyParagraph[] {
  return [];
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
 * The question a teacher adds: no question text, and the kind's empty
 * structure, the same structure the server gives a question it retypes
 * (TASK-SKRIPT-39-06-05). Choice kinds get two empty choices, a rullista one
 * gap whose first empty option is the key, and Kategorisera one row, two
 * categories and a zero tick value. Empty texts block export until the teacher
 * fills them in. A Kort svar is a Lucktext whose only gap stands alone in its
 * last paragraph (L2, user 2026-10-19); a new Lucktext starts with no text
 * and no gap, while a new Kort svar keeps its one-gap body.
 */
export function newTeacherItem(
  itemId: string,
  sequence: number,
  teacherKind: TeacherItemKind,
): NativeExamItem {
  const kind: NativeExamItemKind = teacherKind === "short_answer" ? "gap_fill" : teacherKind;
  const gapped = kind === "inline_choice" || (kind === "gap_fill" && teacherKind === "short_answer");
  const choice = kind === "single_choice" || kind === "multiple_response";
  const matching = kind === "matching";
  const ordering = kind === "ordering";
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
          : kind === "inline_choice" || ordering
            ? "teacher_authored"
            : "absent",
    },
    body: gapped ? [{ heading_level: null, segments: [{ kind: "gap", gap_id: "gap_001" }] }] : [],
    choices: choice || ordering ? blankChoices() : [],
    gaps: gapped ? [blankGap(kind === "inline_choice")] : [],
    item_id: itemId,
    kind,
    match_left: matching ? [{ body: blankBody(), left_id: "left_001" }] : [],
    match_right: matching
      ? ["right_001", "right_002"].map((rightId) => ({ body: blankBody(), right_id: rightId }))
      : [],
    points: ordering ? 1 : null,
    points_estimated: false,
    print_order: ordering ? ["choice_002", "choice_001"] : [],
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
