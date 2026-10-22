/**
 * Exam workspace picture placement.
 *
 * Expected behavior:
 *   One picture atom enters written text alone in a plain paragraph, in one
 *   transaction. A caret at a paragraph's end puts the picture after it and
 *   leaves the caret at the start of the next textblock; at the last
 *   paragraph's end it adds an empty paragraph to write in. A caret at a
 *   paragraph's start puts the picture before it and keeps the caret at the
 *   start of the text. A caret inside a sentence splits the paragraph, keeps
 *   both halves — a heading half stays a heading — and puts the caret at the
 *   start of the second half. An empty paragraph becomes the picture. A
 *   selected picture is replaced in place with its new id and nothing else
 *   changes, and a selected text range is never deleted.
 *
 * States are built from the stored body through the production mapping, so
 * every case asserts the placement against the body the editor emits.
 */

import { getSchema } from "@tiptap/core";
import type { Node as ProseMirrorNode } from "@tiptap/pm/model";
import { EditorState, NodeSelection, TextSelection } from "@tiptap/pm/state";
import type { Selection } from "@tiptap/pm/state";
import { describe, expect, it } from "vitest";

import type { NativeExamBodyParagraph, NativeExamBodySegment } from "../../../api/examWorkspace";
import { bodyFromEditor, editorContentFrom } from "./examWorkspaceRichTextDocument";
import { picturePlacement } from "./examWorkspacePicturePlacement";
import { examRichTextExtensions } from "./examWorkspaceRichTextSchema";

const OLD_PICTURE = "asset_old";
const NEW_PICTURE = "asset_new";

const schema = getSchema(
  examRichTextExtensions({
    gapState: () => ({ label: "Lucka", accessibleLabel: "Lucka", empty: true }),
    pictureUrl: () => undefined,
    keptGapToolOn: () => false,
    onUndo: () => undefined,
    onRedo: () => undefined,
    onToggleGapTool: () => false,
  }),
);

function text(value: string): NativeExamBodySegment {
  return { kind: "text", text: value, marks: [], kept_gap_id: null };
}

function picture(assetId: string): NativeExamBodySegment {
  return { kind: "asset", asset_id: assetId };
}

function paragraph(...segments: NativeExamBodySegment[]): NativeExamBodyParagraph {
  return { heading_level: null, segments };
}

function heading(level: 1 | 2 | 3, ...segments: NativeExamBodySegment[]): NativeExamBodyParagraph {
  return { heading_level: level, segments };
}

type Placed = {
  /** The body the editor would emit. */
  body: NativeExamBodyParagraph[];
  /** The document after the placement, for caret assertions. */
  doc: ProseMirrorNode;
  /** The caret after the placement. */
  caret: number;
};

function place(
  body: NativeExamBodyParagraph[],
  select: (doc: ProseMirrorNode) => Selection,
  assetId: string = NEW_PICTURE,
): Placed {
  const doc = schema.nodeFromJSON(editorContentFrom(body));
  const state = EditorState.create({ doc, selection: select(doc) });
  const transaction = picturePlacement(state, assetId);
  if (transaction === null) {
    throw new Error("the placement was refused");
  }
  const placed = state.apply(transaction);
  return { body: bodyFromEditor(placed.doc.toJSON()), doc: placed.doc, caret: placed.selection.from };
}

/** The caret position at the start of top-level block `index`. */
function blockStart(doc: ProseMirrorNode, index: number): number {
  let pos = 0;
  for (let current = 0; current <= index; current += 1) {
    if (current === index) {
      return pos + 1;
    }
    pos += doc.child(current).nodeSize;
  }
  throw new Error(`no block ${index}`);
}

/** Position `offset` characters into the first text node that contains `needle`. */
function posIn(doc: ProseMirrorNode, needle: string, offset: number): number {
  let found = -1;
  doc.descendants((node, pos) => {
    if (found < 0 && node.isText && node.text?.includes(needle)) {
      found = pos + (node.text.indexOf(needle) + offset);
    }
    return found < 0;
  });
  if (found < 0) {
    throw new Error(`no text "${needle}"`);
  }
  return found;
}

function caretIn(doc: ProseMirrorNode, needle: string, offset: number): TextSelection {
  return TextSelection.create(doc, posIn(doc, needle, offset));
}

function pictureAt(doc: ProseMirrorNode, assetId: string): NodeSelection {
  let found = -1;
  doc.descendants((node, pos) => {
    if (found < 0 && node.type.name === "examPicture" && node.attrs.assetId === assetId) {
      found = pos;
    }
    return found < 0;
  });
  if (found < 0) {
    throw new Error(`no picture ${assetId}`);
  }
  return NodeSelection.create(doc, found);
}

describe("examWorkspacePicturePlacement", () => {
  it("places the picture after a paragraph's end and puts the caret at the next textblock's start", () => {
    const placed = place([paragraph(text("Slut")), paragraph(text("Nästa"))], (doc) =>
      caretIn(doc, "Slut", 4),
    );

    expect(placed.body).toEqual([
      paragraph(text("Slut")),
      paragraph(picture(NEW_PICTURE)),
      paragraph(text("Nästa")),
    ]);
    expect(placed.caret).toBe(posIn(placed.doc, "Nästa", 0));
  });

  it("adds an empty paragraph after a picture placed at the last paragraph's end", () => {
    const placed = place([paragraph(text("Slut"))], (doc) => caretIn(doc, "Slut", 4));

    expect(placed.body).toEqual([
      paragraph(text("Slut")),
      paragraph(picture(NEW_PICTURE)),
      paragraph(),
    ]);
    // The caret sits in the new, empty paragraph: its content start is the
    // last position before the document's end.
    expect(placed.doc.childCount).toBe(3);
    expect(placed.doc.lastChild?.content.size).toBe(0);
    expect(placed.caret).toBe(placed.doc.content.size - 1);
  });

  it("places the picture before a paragraph and keeps the caret at the start of its text", () => {
    const placed = place([paragraph(text("Text"))], (doc) => caretIn(doc, "Text", 0));

    expect(placed.body).toEqual([paragraph(picture(NEW_PICTURE)), paragraph(text("Text"))]);
    expect(placed.caret).toBe(posIn(placed.doc, "Text", 0));
  });

  it("splits a sentence at the caret, keeps both halves and the caret at the second half", () => {
    const placed = place([paragraph(text("Inledning slut"))], (doc) =>
      caretIn(doc, "Inledning", 10),
    );

    expect(placed.body).toEqual([
      paragraph(text("Inledning ")),
      paragraph(picture(NEW_PICTURE)),
      paragraph(text("slut")),
    ]);
    expect(placed.caret).toBe(posIn(placed.doc, "slut", 0));
  });

  it("keeps a heading half a heading and gives the picture a plain paragraph", () => {
    const placed = place([heading(2, text("Rubrik fortsättning"))], (doc) =>
      caretIn(doc, "Rubrik", 7),
    );

    expect(placed.body).toEqual([
      heading(2, text("Rubrik ")),
      paragraph(picture(NEW_PICTURE)),
      heading(2, text("fortsättning")),
    ]);
    expect(placed.body[1]?.heading_level).toBeNull();
    expect(placed.caret).toBe(posIn(placed.doc, "fortsättning", 0));
  });

  it("turns an empty paragraph into the picture and puts the caret at the next textblock", () => {
    const placed = place([paragraph(), paragraph(text("Efter"))], (doc) =>
      TextSelection.create(doc, blockStart(doc, 0)),
    );

    expect(placed.body).toEqual([paragraph(picture(NEW_PICTURE)), paragraph(text("Efter"))]);
    expect(placed.caret).toBe(posIn(placed.doc, "Efter", 0));
  });

  it("adds an empty paragraph when an empty last paragraph becomes the picture", () => {
    const placed = place([paragraph()], (doc) => TextSelection.create(doc, blockStart(doc, 0)));

    expect(placed.body).toEqual([paragraph(picture(NEW_PICTURE)), paragraph()]);
    expect(placed.caret).toBe(placed.doc.content.size - 1);
  });

  it("replaces a selected picture in place and changes nothing else", () => {
    const placed = place(
      [paragraph(text("A"), picture(OLD_PICTURE), text("B"))],
      (doc) => pictureAt(doc, OLD_PICTURE),
    );

    expect(placed.body).toEqual([paragraph(text("A"), picture(NEW_PICTURE), text("B"))]);
    expect(placed.doc.childCount).toBe(1);
    expect(placed.doc.textContent).toBe("AB");
    expect(placed.caret).toBe(blockStart(placed.doc, 0) + 1);
  });

  it("keeps a selected text range, splitting after it instead of deleting it", () => {
    const placed = place([paragraph(text("Behåll texten"))], (doc) =>
      TextSelection.create(doc, posIn(doc, "Behåll", 0), posIn(doc, "Behåll", 7)),
    );

    expect(placed.body).toEqual([
      paragraph(text("Behåll ")),
      paragraph(picture(NEW_PICTURE)),
      paragraph(text("texten")),
    ]);
    expect(placed.caret).toBe(posIn(placed.doc, "texten", 0));
  });
});
