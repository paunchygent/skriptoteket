import { Editor } from "@tiptap/core";
import { describe, expect, it } from "vitest";

import type { NativeExamBodyParagraph, NativeExamBodySegment } from "../../../api/examWorkspace";
import { BODY_MARKS } from "./examWorkspaceBodyMarks";
import type { BodyMark } from "./examWorkspaceBodyMarks";
import {
  bodyFromEditor,
  editorContentFrom,
  isEmptyBody,
  placedAssetIds,
  placedGapIds,
} from "./examWorkspaceRichTextDocument";
import { examRichTextExtensions } from "./examWorkspaceRichTextSchema";

type Level = NativeExamBodyParagraph["heading_level"];

function text(value: string, marks: BodyMark[] = []): NativeExamBodySegment {
  return { kind: "text", text: value, marks };
}
function gap(id: string): NativeExamBodySegment {
  return { kind: "gap", gap_id: id };
}
function picture(id: string): NativeExamBodySegment {
  return { kind: "asset", asset_id: id };
}
function paragraph(segments: NativeExamBodySegment[], level: Level = null): NativeExamBodyParagraph {
  return { heading_level: level, segments };
}

/** A headless editor on the real schema: the document passes through ProseMirror's own validation. */
function throughEditor(body: NativeExamBodyParagraph[]): NativeExamBodyParagraph[] {
  const editor = new Editor({
    extensions: examRichTextExtensions({
      gapState: () => ({ label: "Lucka", accessibleLabel: "Lucka", empty: true }),
      pictureUrl: () => undefined,
      onUndo: () => undefined,
      onRedo: () => undefined,
    }),
    content: editorContentFrom(body),
  });
  try {
    return bodyFromEditor(editor.getJSON());
  } finally {
    editor.destroy();
  }
}

describe("exam rich-text document mapping", () => {
  it.each(BODY_MARKS.map((mark) => [mark]))("round-trips a run marked only %s", (mark) => {
    const body = [paragraph([text("a", []), text("b", [mark]), text("c", [])])];
    expect(throughEditor(body)).toEqual(body);
  });

  it("round-trips marks combined in the stored order", () => {
    const body = [
      paragraph([
        text("x", ["bold", "italic", "underline"]),
        text("y", ["italic", "subscript"]),
        text("z", ["bold", "superscript"]),
      ]),
    ];
    expect(throughEditor(body)).toEqual(body);
  });

  it("reads every mark in the stored order whatever order the editor lists them", () => {
    const body = bodyFromEditor({
      type: "doc",
      content: [
        {
          type: "paragraph",
          content: [{ type: "text", text: "t", marks: [{ type: "underline" }, { type: "bold" }] }],
        },
      ],
    });
    expect(body).toEqual([paragraph([text("t", ["bold", "underline"])])]);
  });

  it("round-trips headings 1 to 3 next to plain paragraphs", () => {
    const body = [
      paragraph([text("one")], 1),
      paragraph([text("plain")]),
      paragraph([text("two")], 2),
      paragraph([text("three")], 3),
      paragraph([text("end")]),
    ];
    expect(throughEditor(body)).toEqual(body);
  });

  it("keeps the marks of a run across a line break inside it", () => {
    const body = [paragraph([text("a\nb", ["bold"])])];
    const content = editorContentFrom(body);
    expect(content.content?.[0].content?.map((node) => node.type)).toEqual(["text", "hardBreak", "text"]);
    expect(content.content?.[0].content?.[1].marks).toEqual([{ type: "bold" }]);
    expect(throughEditor(body)).toEqual(body);
  });

  it("round-trips a line break at the start and at the end of a run", () => {
    const body = [paragraph([text("\nstart", ["italic"]), gap("gap_001"), text("end\n", ["underline"])])];
    expect(throughEditor(body)).toEqual(body);
  });

  it("round-trips a run that is only line breaks", () => {
    const body = [paragraph([text("x"), text("\n\n", ["bold"]), text("y")])];
    expect(throughEditor(body)).toEqual(body);
  });

  it("round-trips gaps and pictures between and at the edges of text", () => {
    const body = [
      paragraph([gap("gap_001"), text("a"), picture("asset_1"), text("b"), gap("gap_002")]),
      paragraph([picture("asset_2")]),
      paragraph([gap("gap_003"), gap("gap_004")]),
    ];
    expect(throughEditor(body)).toEqual(body);
    expect(placedGapIds(body)).toEqual(["gap_001", "gap_002", "gap_003", "gap_004"]);
    expect(placedAssetIds(body)).toEqual(["asset_1", "asset_2"]);
  });

  it("keeps an emptied paragraph between two texts as a paragraph without segments", () => {
    const body = [paragraph([text("first")]), paragraph([]), paragraph([text("last")])];
    expect(throughEditor(body)).toEqual(body);
  });

  it("keeps an emptied heading between two texts as an empty heading", () => {
    const body = [paragraph([text("first")]), paragraph([], 2), paragraph([text("last")])];
    expect(throughEditor(body)).toEqual(body);
  });

  it("opens the empty body as one empty paragraph and maps it back to the empty body", () => {
    expect(editorContentFrom([])).toEqual({ type: "doc", content: [{ type: "paragraph" }] });
    expect(throughEditor([])).toEqual([]);
  });

  it("maps a document of only empty paragraphs and headings to the empty body", () => {
    const body = [paragraph([]), paragraph([], 1), paragraph([])];
    expect(throughEditor(body)).toEqual([]);
  });

  it("merges adjacent text nodes with equal marks into one segment and keeps unequal ones apart", () => {
    const body = bodyFromEditor({
      type: "doc",
      content: [
        {
          type: "paragraph",
          content: [
            { type: "text", text: "a", marks: [{ type: "bold" }] },
            { type: "text", text: "b", marks: [{ type: "bold" }] },
            { type: "hardBreak", marks: [{ type: "bold" }] },
            { type: "text", text: "c" },
            { type: "text", text: "d" },
            { type: "text", text: "e", marks: [{ type: "bold" }] },
          ],
        },
      ],
    });
    expect(body).toEqual([paragraph([text("ab\n", ["bold"]), text("cd"), text("e", ["bold"])])]);
  });

  it("does not merge text across an atom", () => {
    const body = [paragraph([text("a"), gap("gap_001"), text("a")])];
    expect(throughEditor(body)).toEqual(body);
  });

  it("treats whitespace-only text with a line break as empty, and a lone gap or picture as not", () => {
    expect(isEmptyBody([])).toBe(true);
    expect(isEmptyBody([paragraph([text(" \n \n")]), paragraph([])])).toBe(true);
    expect(isEmptyBody([paragraph([gap("gap_001")])])).toBe(false);
    expect(isEmptyBody([paragraph([picture("asset_1")])])).toBe(false);
    expect(isEmptyBody([paragraph([text(" \n"), text("x")])])).toBe(false);
  });
});
