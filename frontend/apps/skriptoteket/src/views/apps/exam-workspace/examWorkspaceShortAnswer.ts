/**
 * Exam workspace Kort svar shape rule (L2 option A, user 2026-10-19; L3).
 *
 * Domain purpose:
 *   The native document has no short-answer kind: a Kort svar is a Lucktext
 *   whose only gap stands alone as the sole segment of its last paragraph.
 *   The Fråga field edits only the paragraphs before that answer paragraph,
 *   and every question edit re-attaches the answer paragraph so the gap
 *   record never drops.
 *
 * Relationships:
 *   - Pure; the Kort svar editor (J8) renders through these helpers.
 *   - Reads placement through `examWorkspaceRichTextDocument`.
 */

import type {
  NativeExamBodyParagraph,
  NativeExamGap,
  NativeExamItem,
} from "../../../api/examWorkspace";
import { placedGapIds } from "./examWorkspaceRichTextDocument";

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
