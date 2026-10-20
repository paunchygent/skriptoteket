/**
 * Exam workspace edit pieces (TASK-SKRIPT-40-04-14, R9-2 per-piece intent).
 *
 * Domain purpose:
 *   The semantic units a teacher edit owns: separate keys for the title,
 *   the header and the document instructions; one key per question by
 *   `item_id` for its content and existence (excluding the derived
 *   sequence); one key for the question order; one key per parent by
 *   `parent_id` for its content and existence; one key per question for its
 *   parent membership; one key for the parent/block outline. `diffPieces`
 *   returns the keys where two documents differ by these units, ignoring
 *   revision and identity metadata, derived sequence numbers and asset
 *   declarations. Assets are not a teacher edit: restored content keeps its
 *   pictures through the asset owner instead.
 *
 * Relationships:
 *   - `examWorkspaceRefusedEditMerge` takes an owned piece set selected by
 *     these keys; specs derive that set with `diffPieces`.
 *   - The history store records `diffPieces` of the confirmed copy against
 *     each sent snapshot, and the sync gate captures the same diff as the
 *     kept record's owned pieces.
 */

import type {
  NativeExamDocument,
  NativeExamItem,
  NativeExamParent,
} from "../../../api/examWorkspace";
import { sameValue } from "./examWorkspaceConversionMerge";

/** The document title as one owned unit. */
export const EDIT_PIECE_TITLE = "title";
/** The document header as one owned unit, at the contract's granularity. */
export const EDIT_PIECE_HEADER = "header";
/** The document instructions as one owned unit. */
export const EDIT_PIECE_INSTRUCTIONS = "instructions";
/** The question order, separate from any question's content. */
export const EDIT_PIECE_QUESTION_ORDER = "question-order";
/** The parent/block outline: order and question-relative placement. */
export const EDIT_PIECE_OUTLINE = "outline";

/** One question's content and existence, excluding its derived sequence. */
export function questionPiece(itemId: string): string {
  return `question:${itemId}`;
}

/** One parent's content and existence, excluding derived placement. */
export function parentPiece(parentId: string): string {
  return `parent:${parentId}`;
}

/** One question's parent membership, separate from its content. */
export function membershipPiece(itemId: string): string {
  return `membership:${itemId}`;
}

function itemsById(items: NativeExamItem[]): Map<string, NativeExamItem> {
  return new Map(items.map((item) => [item.item_id, item]));
}

function parentsById(parents: NativeExamParent[]): Map<string, NativeExamParent> {
  return new Map(parents.map((parent) => [parent.parent_id, parent]));
}

/** Item content without the derived position, so renumbering never reads as an edit. */
function sameItemContent(a: NativeExamItem, b: NativeExamItem): boolean {
  return sameValue({ ...a, sequence: 1 }, { ...b, sequence: 1 });
}

/** A part's own content without its derived place; membership is reconciled separately. */
function sameParentContent(a: NativeExamParent, b: NativeExamParent): boolean {
  return sameValue(
    { instruction: a.instruction, printed_total: a.printed_total ?? null },
    { instruction: b.instruction, printed_total: b.printed_total ?? null },
  );
}

/** The part holding the item in this document, or null when it stands alone. */
export function parentIdIn(document: NativeExamDocument, itemId: string): string | null {
  for (const parent of document.parents) {
    if (parent.item_ids.includes(itemId)) {
      return parent.parent_id;
    }
  }
  return null;
}

/** The block outline: each part's identity in order with its question-relative place. */
function outlineOf(document: NativeExamDocument): Array<{ parent_id: string; place: number }> {
  return document.parents.map((parent) => ({ parent_id: parent.parent_id, place: parent.place }));
}

/**
 * The piece keys where two documents differ by the semantic units above.
 * Either side being null means there is no baseline to own against, so no
 * piece differs. Revision, document, origin and schema metadata, derived
 * sequence numbers and asset declarations never produce a piece.
 */
export function diffPieces(
  a: NativeExamDocument | null,
  b: NativeExamDocument | null,
): Set<string> {
  const pieces = new Set<string>();
  if (a === null || b === null || a === b) {
    return pieces;
  }
  if (!sameValue(a.title, b.title)) {
    pieces.add(EDIT_PIECE_TITLE);
  }
  if (!sameValue(a.header, b.header)) {
    pieces.add(EDIT_PIECE_HEADER);
  }
  if (!sameValue(a.instructions, b.instructions)) {
    pieces.add(EDIT_PIECE_INSTRUCTIONS);
  }
  const aItems = itemsById(a.items);
  const bItems = itemsById(b.items);
  const itemIds = new Set<string>([...aItems.keys(), ...bItems.keys()]);
  for (const itemId of itemIds) {
    const aItem = aItems.get(itemId);
    const bItem = bItems.get(itemId);
    if (aItem === undefined || bItem === undefined || !sameItemContent(aItem, bItem)) {
      pieces.add(questionPiece(itemId));
    }
    // Membership is its own unit: a question edited and moved owns both.
    if (aItem !== undefined && bItem !== undefined && parentIdIn(a, itemId) !== parentIdIn(b, itemId)) {
      pieces.add(membershipPiece(itemId));
    }
  }
  const orderOf = (document: NativeExamDocument): string[] =>
    document.items.map((item) => item.item_id);
  if (!sameValue(orderOf(a), orderOf(b))) {
    pieces.add(EDIT_PIECE_QUESTION_ORDER);
  }
  const aParents = parentsById(a.parents);
  const bParents = parentsById(b.parents);
  const parentIds = new Set<string>([...aParents.keys(), ...bParents.keys()]);
  for (const parentId of parentIds) {
    const aParent = aParents.get(parentId);
    const bParent = bParents.get(parentId);
    if (aParent === undefined || bParent === undefined || !sameParentContent(aParent, bParent)) {
      pieces.add(parentPiece(parentId));
    }
  }
  if (!sameValue(outlineOf(a), outlineOf(b))) {
    pieces.add(EDIT_PIECE_OUTLINE);
  }
  return pieces;
}
