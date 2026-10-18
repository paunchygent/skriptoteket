/**
 * Which editor transactions are discrete edits.
 *
 * Domain purpose:
 *   The workspace history records one undo step per discrete edit and
 *   coalesces typing. A toolbar click is known to be discrete by its call
 *   site; the same edit made from the keyboard (Ctrl/Cmd+B, I, U, the
 *   super- and subscript keys, a heading key) and the deletion of a range
 *   across paragraphs arrive only as a transaction. This module reads the
 *   transaction's steps and says whether it is such an edit, so the editor's
 *   `structural` flag does not depend on how the edit was made.
 *
 * Expected behavior:
 *   - A mark added or removed, or a node's type or attributes changed (a
 *     heading set or cleared), is discrete.
 *   - A deletion whose range touches more than one textblock and holds text
 *     is discrete. Backspace at a paragraph start deletes only the boundary
 *     between two paragraphs, holds no text, and is not discrete.
 *   - Typing, Enter, Shift+Enter and paste at a caret are not discrete.
 *
 * Relationships:
 *   - `ExamWorkspaceRichTextEditor` ORs the result into `structural`.
 */

import type { Node as ProseMirrorNode } from "@tiptap/pm/model";
import type { Transaction } from "@tiptap/pm/state";
import { AddMarkStep, AttrStep, RemoveMarkStep, ReplaceAroundStep, ReplaceStep } from "@tiptap/pm/transform";

/** Whether a deletion from `from` to `to` in `doc` removes text from more than one textblock. */
function deletesTextAcrossTextblocks(doc: ProseMirrorNode, from: number, to: number): boolean {
  let textblocks = 0;
  doc.nodesBetween(from, to, (node) => {
    if (node.isTextblock) {
      textblocks += 1;
    }
    return !node.isTextblock;
  });
  return textblocks > 1 && doc.textBetween(from, to, "\n").trim() !== "";
}

/** True when one transaction is a mark, heading or range-delete edit rather than typing. */
export function isDiscreteEdit(transaction: Transaction): boolean {
  return transaction.steps.some((step, index) => {
    if (
      step instanceof AddMarkStep ||
      step instanceof RemoveMarkStep ||
      step instanceof AttrStep ||
      step instanceof ReplaceAroundStep
    ) {
      return true;
    }
    // `docs[index]` is the document this step was applied to.
    return step instanceof ReplaceStep && deletesTextAcrossTextblocks(transaction.docs[index], step.from, step.to);
  });
}
