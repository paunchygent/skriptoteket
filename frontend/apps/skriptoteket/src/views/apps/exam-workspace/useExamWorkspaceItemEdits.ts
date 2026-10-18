/**
 * Exam workspace item edit commands.
 *
 * Domain purpose:
 *   Every teacher edit the editor offers on one item, as a named command
 *   applied through the document's one item patch path. The commands carry
 *   no state: they translate an event payload into the pure item transition
 *   from `examWorkspaceItemEdits`, so `useExamWorkspaceDocument` keeps only
 *   the patch path, the save lifecycle and the conversion lifecycle.
 *
 * Relationships:
 *   - Used by `useExamWorkspaceDocument`, which owns the patch path and
 *     re-exports these commands.
 *   - Reads its transitions from `examWorkspaceItemEdits`, and the export
 *     blocker fixes from `examWorkspaceBlockers`.
 */

import type {
  NativeExamBodyParagraph,
  NativeExamBodySegment,
  NativeExamChoice,
  NativeExamCriterion,
  NativeExamItem,
  NativeExamMatchPair,
} from "../../../api/examWorkspace";
import {
  reviewed,
  unreviewed,
  withChoiceBody,
  withCorrectChoices,
  withCriteria,
  withGapAsText,
  withGapOptions,
  withoutInterpretedKey,
  withMatchEntryBody,
  withMatchPairs,
  withParagraphHeading,
  withParagraphSegments,
  withPoints,
  withTickPoints,
} from "./examWorkspaceItemEdits";
import { withoutEmptyOptions, withoutOptionHeadings } from "./examWorkspaceBlockers";

/** One patch of one item, refused while the document is busy or the item still converts. */
export type ExamWorkspaceItemPatch = (
  itemId: string,
  patch: (item: NativeExamItem) => NativeExamItem,
  /** A click edit (a key, the review state) is one undo step at once; typing waits for a pause. */
  structural?: boolean,
) => boolean;

export function useExamWorkspaceItemEdits(patchItem: ExamWorkspaceItemPatch) {
  function updateItemCriteria(itemId: string, criteria: NativeExamCriterion[]): void {
    patchItem(itemId, (item) => withCriteria(item, criteria));
  }

  function updateItemPoints(itemId: string, points: number | null): void {
    patchItem(itemId, (item) => withPoints(item, points));
  }

  function updateItemParagraphSegments(
    itemId: string,
    paragraphIndex: number,
    segments: NativeExamBodySegment[],
  ): void {
    patchItem(itemId, (item) => withParagraphSegments(item, paragraphIndex, segments));
  }

  function updateItemParagraphHeading(
    itemId: string,
    paragraphIndex: number,
    headingLevel: NativeExamBodyParagraph["heading_level"],
  ): void {
    patchItem(itemId, (item) => withParagraphHeading(item, paragraphIndex, headingLevel));
  }

  function updateItemGapOptions(
    itemId: string,
    gapId: string,
    options: NativeExamChoice[],
    correctOptionId: string | null,
  ): void {
    patchItem(itemId, (item) => withGapOptions(item, gapId, options, correctOptionId), true);
  }

  function updateItemChoiceBody(
    itemId: string,
    choiceId: string,
    body: NativeExamBodyParagraph[],
  ): void {
    patchItem(itemId, (item) => withChoiceBody(item, choiceId, body));
  }

  function updateItemCorrectChoices(itemId: string, correctChoiceIds: string[]): void {
    patchItem(itemId, (item) => withCorrectChoices(item, correctChoiceIds), true);
  }

  function updateItemMatchEntryBody(
    itemId: string,
    side: "left" | "right",
    entryId: string,
    body: NativeExamBodyParagraph[],
  ): void {
    patchItem(itemId, (item) => withMatchEntryBody(item, side, entryId, body));
  }

  function updateItemMatchPairs(itemId: string, pairs: NativeExamMatchPair[]): void {
    patchItem(itemId, (item) => withMatchPairs(item, pairs), true);
  }

  function updateItemTickPoints(itemId: string, tickPoints: string): void {
    patchItem(itemId, (item) => withTickPoints(item, tickPoints));
  }

  function undoItemInterpretation(itemId: string): void {
    patchItem(itemId, withoutInterpretedKey, true);
  }

  function showItemGapAsText(itemId: string, gapId: string): void {
    patchItem(itemId, (item) => withGapAsText(item, gapId), true);
  }

  function markItemReviewed(itemId: string): void {
    patchItem(itemId, reviewed, true);
  }

  function unmarkItemReviewed(itemId: string): void {
    patchItem(itemId, unreviewed, true);
  }

  function removeItemEmptyOptions(itemId: string): void {
    patchItem(itemId, withoutEmptyOptions, true);
  }

  function removeItemOptionHeadings(itemId: string): void {
    patchItem(itemId, withoutOptionHeadings, true);
  }

  return {
    markItemReviewed,
    removeItemEmptyOptions,
    removeItemOptionHeadings,
    unmarkItemReviewed,
    showItemGapAsText,
    undoItemInterpretation,
    updateItemChoiceBody,
    updateItemCorrectChoices,
    updateItemCriteria,
    updateItemGapOptions,
    updateItemMatchEntryBody,
    updateItemMatchPairs,
    updateItemParagraphHeading,
    updateItemParagraphSegments,
    updateItemPoints,
    updateItemTickPoints,
  };
}
