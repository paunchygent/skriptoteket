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
  NativeExamItem,
} from "../../../api/examWorkspace";
import { placedGapIds } from "./examWorkspaceRichTextDocument";

/** A Kort svar is a Lucktext whose only gap stands alone in its last paragraph. */
export function isShortAnswer(item: NativeExamItem): boolean {
  if (item.kind !== "gap_fill") {
    return false;
  }
  if (item.gaps.length !== 1) {
    return false;
  }
  const gap = item.gaps[0]!;
  const placed = placedGapIds(item.body);
  if (placed.length !== 1 || placed[0] !== gap.gap_id) {
    return false;
  }
  if (item.body.length === 0) {
    return false;
  }
  const last = item.body[item.body.length - 1]!;
  if (last.segments.length !== 1) {
    return false;
  }
  const only = last.segments[0]!;
  return only.kind === "gap" && only.gap_id === gap.gap_id;
}

/** The question part of a Kort svar: its body without the last answer paragraph. */
export function shortAnswerQuestion(item: NativeExamItem): NativeExamBodyParagraph[] {
  return item.body.slice(0, -1);
}

/** The one gap a Kort svar answers. */
export function shortAnswerGapId(item: NativeExamItem): string {
  return item.gaps[0]!.gap_id;
}

/**
 * The edited question with the item's current answer paragraph re-attached
 * last, so the gap stays placed. A question that itself places a gap is not
 * a Fråga edit and leaves the body unchanged.
 */
export function withShortAnswerQuestion(
  item: NativeExamItem,
  question: NativeExamBodyParagraph[],
): NativeExamBodyParagraph[] {
  if (placedGapIds(question).length > 0) {
    return item.body;
  }
  return [...question, item.body[item.body.length - 1]!];
}
