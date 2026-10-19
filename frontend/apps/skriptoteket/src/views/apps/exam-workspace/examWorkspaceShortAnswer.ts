/**
 * Exam workspace Kort svar shape rule and shape edits (L2 option A, user 2026-10-19; L3; R4, R5).
 *
 * Domain purpose:
 *   The native document has no short-answer kind: a Kort svar is a Lucktext
 *   whose only gap stands alone as the sole segment of its last paragraph.
 *   The Fråga field edits only the paragraphs before that answer paragraph,
 *   and every question edit re-attaches the answer paragraph so the gap
 *   record never drops. Byt frågetyp moves between the two shapes as one
 *   undoable client edit: a Kort svar becomes a Lucktext with its answer gap
 *   at the end of the last question paragraph, and an eligible Lucktext (at
 *   most one gap) becomes a Kort svar with its gap alone in the last
 *   paragraph. Both keep the gap record and its answers through the existing
 *   body and gap-record paths, with no server change type and no
 *   native-format change.
 *
 * Relationships:
 *   - Pure; the Kort svar editor (J8) renders through these helpers, and the
 *     item edit commands apply the shape edits.
 *   - Reads placement through `examWorkspaceRichTextDocument`, keeps records
 *     through `withBody`, and creates the missing gap through `withNewGap`.
 */

import type {
  NativeExamBodyParagraph,
  NativeExamBodySegment,
  NativeExamGap,
  NativeExamItem,
} from "../../../api/examWorkspace";
import { nextGapId, withNewGap } from "./examWorkspaceGapEdits";
import { withBody } from "./examWorkspaceItemEdits";
import { placedGapIds } from "./examWorkspaceRichTextDocument";

/** The Byt frågetyp shapes of a Lucktext: the question field or the gap text. */
export type ExamWorkspaceItemShape = "short_answer" | "gap_fill";

/** A Kort svar split into its editable question and its answer paragraph. */
export type ShortAnswerParts = {
  question: NativeExamBodyParagraph[];
  answer: NativeExamBodyParagraph;
  gap: NativeExamGap;
};

/** The Kort svar parts of a Lucktext whose only gap stands alone in its last paragraph, else null. */
export function shortAnswerParts(item: NativeExamItem): ShortAnswerParts | null {
  if (item.kind !== "gap_fill") {
    return null;
  }
  if (item.gaps.length !== 1) {
    return null;
  }
  const gap = item.gaps[0];
  if (gap === undefined) {
    return null;
  }
  const placed = placedGapIds(item.body);
  if (placed.length !== 1 || placed[0] !== gap.gap_id) {
    return null;
  }
  if (item.body.length === 0) {
    return null;
  }
  const last = item.body[item.body.length - 1];
  if (last === undefined || last.segments.length !== 1) {
    return null;
  }
  const only = last.segments[0];
  if (only === undefined || only.kind !== "gap" || only.gap_id !== gap.gap_id) {
    return null;
  }
  return { question: item.body.slice(0, -1), answer: last, gap };
}

/** A Kort svar is a Lucktext whose only gap stands alone in its last paragraph. */
export function isShortAnswer(item: NativeExamItem): boolean {
  return shortAnswerParts(item) !== null;
}

/**
 * The edited question with the item's current answer paragraph re-attached
 * last, so the gap stays placed. A question that itself places a gap is not
 * a Fråga edit and leaves the body unchanged.
 */
export function withShortAnswerQuestion(
  parts: ShortAnswerParts,
  question: NativeExamBodyParagraph[],
): NativeExamBodyParagraph[] {
  if (placedGapIds(question).length > 0) {
    return [...parts.question, parts.answer];
  }
  return [...question, parts.answer];
}

/**
 * A Lucktext Byt frågetyp offers as Kort svar: one gap at most, and that gap
 * placed at most once. A Kort svar itself and any other kind stay untouched.
 */
export function canBecomeShortAnswer(item: NativeExamItem): boolean {
  return (
    item.kind === "gap_fill" &&
    !isShortAnswer(item) &&
    item.gaps.length <= 1 &&
    placedGapIds(item.body).length <= 1
  );
}

/**
 * A Kort svar as a Lucktext: the answer gap at the end of the last question
 * paragraph, separated from the text by one space. An empty question keeps
 * the gap paragraph first and follows it with an empty paragraph, which the
 * backend accepts and the body mapping keeps. The gap record and its answers
 * stay untouched through `withBody`. Anything but a Kort svar passes through.
 */
export function withGapTextShape(item: NativeExamItem): NativeExamItem {
  const parts = shortAnswerParts(item);
  if (parts === null) {
    return item;
  }
  if (parts.question.length === 0) {
    return withBody(item, [parts.answer, { heading_level: null, segments: [] }]);
  }
  const last = parts.question[parts.question.length - 1]!;
  const gapSegment: NativeExamBodySegment = { kind: "gap", gap_id: parts.gap.gap_id };
  const trailing = last.segments[last.segments.length - 1];
  const separator: NativeExamBodySegment[] =
    trailing !== undefined && trailing.kind === "text" && !/\s$/.test(trailing.text)
      ? [{ kind: "text", marks: [], text: " " }]
      : [];
  return withBody(item, [
    ...parts.question.slice(0, -1),
    { ...last, segments: [...last.segments, ...separator, gapSegment] },
  ]);
}

/**
 * An eligible Lucktext as a Kort svar: its one placed gap alone in the last
 * paragraph, so the editor shows the Fråga and Godkända svar fields. A
 * paragraph that held only the gap drops away. A Lucktext with no gap grows
 * a new empty gap there through `withNewGap`. The record and its answers
 * stay untouched. Anything ineligible passes through.
 */
export function withShortAnswerShape(item: NativeExamItem): NativeExamItem {
  if (!canBecomeShortAnswer(item)) {
    return item;
  }
  const placed = placedGapIds(item.body);
  const gapId = placed[0];
  if (gapId === undefined) {
    const next = nextGapId(item);
    if (next === null) {
      return item;
    }
    return withNewGap(item, [...item.body, { heading_level: null, segments: [{ kind: "gap", gap_id: next }] }], next, "");
  }
  const gapSegment: NativeExamBodySegment = { kind: "gap", gap_id: gapId };
  const rest = item.body.flatMap((paragraph) => {
    if (!paragraph.segments.some((segment) => segment.kind === "gap" && segment.gap_id === gapId)) {
      return [paragraph];
    }
    const kept = paragraph.segments.filter(
      (segment) => !(segment.kind === "gap" && segment.gap_id === gapId),
    );
    return kept.length > 0 ? [{ ...paragraph, segments: kept }] : [];
  });
  return withBody(item, [...rest, { heading_level: null, segments: [gapSegment] }]);
}
