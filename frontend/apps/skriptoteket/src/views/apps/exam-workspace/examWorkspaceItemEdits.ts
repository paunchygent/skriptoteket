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
import { placedGapIds, placedKeptGapIds } from "./examWorkspaceRichTextDocument";
import { DEFAULT_WRITING_LINES } from "./examWorkspaceWritingLines";

export function teacherKeyOrigin(hasKeyData: boolean): NativeExamAnswerKeyOrigin {
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
 * places leaves with it, and so does a kept record no text run names any
 * more; the rest keep their declared order; an edit never adds a record.
 */
export function withBody(item: NativeExamItem, body: NativeExamBodyParagraph[]): NativeExamItem {
  const placed = new Set(placedGapIds(body));
  const kept = new Set(placedKeptGapIds(body));
  return {
    ...item,
    body,
    gaps: item.gaps.filter((gap) => placed.has(gap.gap_id)),
    kept_gaps: item.kept_gaps.filter((gap) => kept.has(gap.gap_id)),
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

/**
 * The AI key can be undone for every kind except a dropdown, which has no
 * valid keyless state (TASK-SKRIPT-40-04-26 D5): an `ai_interpreted` key and a
 * `machine_proposed` one the teacher has not reviewed both count as AI keys.
 */
export function canUndoAiKey(item: NativeExamItem): boolean {
  const origin = item.answer_key.origin;
  return (
    (origin === "ai_interpreted" || origin === "machine_proposed") &&
    item.kind !== "inline_choice"
  );
}

/**
 * Remove the AI key without losing the teacher's source facit. A spelling the
 * teacher suppressed stays suppressed, and the kept suggestion stays on the
 * question. Undo opens the question's one retry: a `none` retry becomes
 * `offered`, while an already offered or used retry stays as it is, so a spent
 * retry stays spent (D4, D5).
 */
export function withoutAiKey(item: NativeExamItem): NativeExamItem {
  if (!canUndoAiKey(item)) {
    return item;
  }
  return withGridPoints({
    ...item,
    answer_key: { ...item.answer_key, origin: "absent", correct_choice_ids: [], match_pairs: [] },
    answer_key_retry: item.answer_key_retry === "none" ? "offered" : item.answer_key_retry,
    gaps: item.gaps.map((gap) => ({ ...gap, accepted_values: [], automatic_values: [] })),
  });
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

export function blankChoices(): NativeExamChoice[] {
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
    answer_key_retry: "none",
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
    kept_gaps: [],
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
    source_points: null,
    conflicting_source_points: [],
    suggested_kind: null,
    tick_points: matching ? "0" : null,
    writing_lines: kind === "free_text" ? DEFAULT_WRITING_LINES : null,
    leftover_points_text: null,
  };
}
