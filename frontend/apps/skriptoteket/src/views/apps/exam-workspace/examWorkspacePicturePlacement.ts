/**
 * Exam workspace picture placement.
 *
 * Domain purpose:
 *   The one place a picture atom enters written text: the toolbar's Lägg till
 *   bild / Byt bild, a dropped file and a pasted file all resolve to one
 *   transaction that puts `assetId` alone in its own plain paragraph. A
 *   selection that covers a whole picture is replaced in place, so the
 *   picture keeps its place in the text and only its id changes. Otherwise
 *   the placement follows the caret at the selection's end: an empty
 *   paragraph becomes the picture, a caret at a paragraph's start puts the
 *   picture before it, a caret at its end puts the picture after it, and a
 *   caret inside the text splits the paragraph and puts the picture between
 *   the halves. A selected text range is never deleted; only the empty
 *   paragraph it sits in is replaced.
 *
 *   The picture is always alone in a plain paragraph, never in a heading,
 *   even when it is placed at a heading's edge or inside one, so a picture
 *   never inherits a heading's size. The caret lands where the teacher keeps
 *   writing: at the start of the textblock after the picture, or in a new
 *   empty paragraph when the picture is the last block.
 *
 * Relationships:
 *   - Called by `ExamWorkspaceRichTextEditor`'s target `placePicture`, inside
 *     one toolbar edit so the whole placement is one undo step.
 *   - Reads the picture node name from `examWorkspaceRichTextSchema`; nothing
 *     else builds a picture paragraph.
 */

import type { Node as ProseMirrorNode, Schema } from "@tiptap/pm/model";
import { NodeSelection, TextSelection } from "@tiptap/pm/state";
import type { EditorState, Transaction } from "@tiptap/pm/state";

import { EXAM_PICTURE_NODE } from "./examWorkspaceRichTextSchema";

/** One plain paragraph that holds the picture and nothing else. */
function pictureParagraph(schema: Schema, assetId: string): ProseMirrorNode | null {
  const pictureType = schema.nodes[EXAM_PICTURE_NODE];
  const paragraphType = schema.nodes.paragraph;
  if (!pictureType || !paragraphType) {
    return null;
  }
  return paragraphType.create(null, pictureType.create({ assetId }));
}

/**
 * Put the caret at the start of the textblock that begins at `after`, or in a
 * new empty paragraph there when no textblock follows, so the teacher always
 * has somewhere to type after the picture.
 */
function caretAfterBlock(
  transaction: Transaction,
  schema: Schema,
  after: number,
): Transaction | null {
  const following = transaction.doc.resolve(after).nodeAfter;
  if (following === null || !following.isTextblock) {
    const paragraphType = schema.nodes.paragraph;
    if (!paragraphType) {
      return null;
    }
    transaction.insert(after, paragraphType.create());
  }
  return transaction.setSelection(TextSelection.create(transaction.doc, after + 1));
}

/**
 * The one transaction that places `assetId` at the selection, or null when
 * this schema or selection cannot take a picture. A whole-picture selection
 * is replaced in place; otherwise the selection's end decides where the
 * picture's own paragraph goes, and the selected text is kept.
 */
export function picturePlacement(state: EditorState, assetId: string): Transaction | null {
  const { selection } = state;
  if (selection instanceof NodeSelection && selection.node.type.name === EXAM_PICTURE_NODE) {
    const replaced = state.tr.setNodeMarkup(selection.from, undefined, {
      ...selection.node.attrs,
      assetId,
    });
    // The picture keeps both its place and its selection, so "Byt bild" is
    // still the toolbar's action on the new picture.
    return replaced.setSelection(NodeSelection.create(replaced.doc, selection.from));
  }
  const $to = selection.$to;
  if (!$to.parent.isTextblock) {
    return null;
  }
  const block = pictureParagraph(state.schema, assetId);
  if (block === null) {
    return null;
  }
  const transaction = state.tr;
  const start = $to.before();
  const end = $to.after();
  if ($to.parent.content.size === 0) {
    transaction.replaceWith(start, end, block);
    return caretAfterBlock(transaction, state.schema, start + block.nodeSize);
  }
  if ($to.parentOffset === 0) {
    transaction.insert(start, block);
    return transaction.setSelection(
      TextSelection.create(transaction.doc, $to.pos + block.nodeSize),
    );
  }
  if ($to.parentOffset === $to.parent.content.size) {
    transaction.insert(end, block);
    return caretAfterBlock(transaction, state.schema, end + block.nodeSize);
  }
  transaction.split($to.pos);
  // The split closes the first half at `$to.pos`; the second half starts one
  // position later, and the picture paragraph sits between them.
  const secondHalf = $to.pos + 1;
  transaction.insert(secondHalf, block);
  return transaction.setSelection(
    TextSelection.create(transaction.doc, secondHalf + block.nodeSize + 1),
  );
}
