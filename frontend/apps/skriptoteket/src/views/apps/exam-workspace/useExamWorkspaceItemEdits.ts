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
  NativeExamChoice,
  NativeExamCriterion,
  NativeExamItem,
  NativeExamMatchPair,
} from "../../../api/examWorkspace";
import {
  reviewed,
  unreviewed,
  withBody,
  withChoiceBody,
  withCorrectChoices,
  withCriteria,
  withoutInterpretedKey,
  withMatchEntryBody,
  withMatchPairs,
  withPoints,
  withTickPoints,
} from "./examWorkspaceItemEdits";
import { withGapAsText, withGapOptions, withNewGap } from "./examWorkspaceGapEdits";
import { withGapReverted, withKeptGapRestored } from "./examWorkspaceKeptGapEdits";
import { withShuffledSteps, withStepAdded, withStepMoved, withStepRemoved } from "./examWorkspaceOrdering";
import { withoutEmptyOptions, withoutOptionHeadings } from "./examWorkspaceBlockers";
import { withWritingLines } from "./examWorkspaceWritingLines";

/** One patch of one item, refused while the document is busy or the item still converts. */
export type ExamWorkspaceItemPatch = (
  itemId: string,
  patch: (item: NativeExamItem) => NativeExamItem,
  /** A click edit (a key, the review state) is one undo step at once; typing waits for a pause. */
  structural?: boolean,
) => boolean;

export function useExamWorkspaceItemEdits(patchItem: ExamWorkspaceItemPatch) {
  /**
   * Replace one item's criteria. Adding a row is a structural edit (one step
   * at once); typing a text or a valid points value waits for the pause.
   */
  function updateItemCriteria(
    itemId: string,
    criteria: NativeExamCriterion[],
    structural: boolean,
  ): void {
    patchItem(itemId, (item) => withCriteria(item, criteria), structural);
  }

  function updateItemPoints(itemId: string, points: number | null): void {
    patchItem(itemId, (item) => withPoints(item, points));
  }

  /** The question text as one document; typing waits for the pause, a gap or picture change is one undo step. */
  function updateItemBody(itemId: string, body: NativeExamBodyParagraph[], structural: boolean): void {
    patchItem(itemId, (item) => withBody(item, body), structural);
  }

  /**
   * Replace one dropdown gap's options. Radio, add, remove and move are
   * structural edits (one step at once); typed option text waits for the
   * pause, and rides along with the next structural edit.
   */
  function updateItemGapOptions(
    itemId: string,
    gapId: string,
    options: NativeExamChoice[],
    correctOptionId: string | null,
    structural: boolean,
  ): void {
    patchItem(itemId, (item) => withGapOptions(item, gapId, options, correctOptionId), structural);
  }

  function updateItemChoiceBody(
    itemId: string,
    choiceId: string,
    body: NativeExamBodyParagraph[],
    structural: boolean,
  ): void {
    patchItem(itemId, (item) => withChoiceBody(item, choiceId, body), structural);
  }

  function updateItemCorrectChoices(itemId: string, correctChoiceIds: string[]): void {
    patchItem(itemId, (item) => withCorrectChoices(item, correctChoiceIds), true);
  }

  function updateItemMatchEntryBody(
    itemId: string,
    side: "left" | "right",
    entryId: string,
    body: NativeExamBodyParagraph[],
    structural: boolean,
  ): void {
    patchItem(itemId, (item) => withMatchEntryBody(item, side, entryId, body), structural);
  }

  function updateItemMatchPairs(itemId: string, pairs: NativeExamMatchPair[]): void {
    patchItem(itemId, (item) => withMatchPairs(item, pairs), true);
  }

  function updateItemTickPoints(itemId: string, tickPoints: string): void {
    patchItem(itemId, (item) => withTickPoints(item, tickPoints));
  }

  /** The question's printed writing area; a stepper click is one undo step. */
  function updateItemWritingLines(itemId: string, lines: number): void {
    patchItem(itemId, (item) => withWritingLines(item, lines), true);
  }

  function addItemOrderingStep(itemId: string): void {
    patchItem(itemId, (item) => withStepAdded(item), true);
  }

  function removeItemOrderingStep(itemId: string, choiceId: string): void {
    patchItem(itemId, (item) => withStepRemoved(item, choiceId), true);
  }

  function moveItemOrderingStep(itemId: string, choiceId: string, delta: -1 | 1): void {
    patchItem(itemId, (item) => withStepMoved(item, choiceId, delta), true);
  }

  function shuffleItemOrderingSteps(itemId: string): void {
    patchItem(itemId, (item) => withShuffledSteps(item), true);
  }

  function undoItemInterpretation(itemId: string): void {
    patchItem(itemId, withoutInterpretedKey, true);
  }

  function showItemGapAsText(itemId: string, gapId: string): void {
    patchItem(itemId, (item) => withGapAsText(item, gapId), true);
  }

  /** A gap-tool revert is one structural undo step, so H4 can call it from a gap click. */
  function revertItemGap(itemId: string, gapId: string): void {
    patchItem(itemId, (item) => withGapReverted(item, gapId), true);
  }

  /** A kept-word restore is one structural undo step, so H4 can call it from a word click. */
  function restoreItemKeptGap(itemId: string, keptGapId: string, atBlock: number): void {
    patchItem(itemId, (item) => withKeptGapRestored(item, keptGapId, atBlock), true);
  }

  /** One gap creation is one atomic structural item edit: body plus gap record together. */
  function createItemGap(
    itemId: string,
    body: NativeExamBodyParagraph[],
    gapId: string,
    seed: string,
  ): void {
    patchItem(itemId, (item) => withNewGap(item, body, gapId, seed), true);
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
    addItemOrderingStep,
    createItemGap,
    markItemReviewed,
    moveItemOrderingStep,
    removeItemOrderingStep,
    shuffleItemOrderingSteps,
    removeItemEmptyOptions,
    removeItemOptionHeadings,
    restoreItemKeptGap,
    revertItemGap,
    unmarkItemReviewed,
    showItemGapAsText,
    undoItemInterpretation,
    updateItemBody,
    updateItemChoiceBody,
    updateItemCorrectChoices,
    updateItemCriteria,
    updateItemGapOptions,
    updateItemMatchEntryBody,
    updateItemMatchPairs,
    updateItemPoints,
    updateItemTickPoints,
    updateItemWritingLines,
  };
}
