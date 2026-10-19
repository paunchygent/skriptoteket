/**
 * Exam workspace kept-gap link.
 *
 * Expected behavior (TASK-SKRIPT-40-04-13 items 2 and 5, unit H2):
 *   A reverted word carries its kept gap id on its text, so the link moves
 *   with the word when the text around it changes and goes when the whole
 *   word is deleted. Copy and paste never copy the link, inside the editor
 *   and from outside. A segment without the link carries `kept_gap_id: null`,
 *   and `withBody` drops kept records no run names any more. The frontend
 *   preview reads a kept word as plain text.
 */

import { Editor } from "@tiptap/core";
import { DOMSerializer } from "@tiptap/pm/model";
import { afterEach, describe, expect, it } from "vitest";

import type {
  NativeExamBodyParagraph,
  NativeExamBodySegment,
  NativeExamGap,
  NativeExamItem,
} from "../../../api/examWorkspace";
import type { BodyMark } from "./examWorkspaceBodyMarks";
import { newTeacherItem, withBody } from "./examWorkspaceItemEdits";
import { withGapAsText } from "./examWorkspaceGapEdits";
import { paragraphText } from "./examWorkspaceRichText";
import {
  bodyFromEditor,
  editorContentFrom,
  placedKeptGapIds,
} from "./examWorkspaceRichTextDocument";
import { examRichTextExtensions } from "./examWorkspaceRichTextSchema";
import {
  mountEditor,
  paragraph,
  paste,
  posIn,
  releaseEditor,
  text,
} from "./ExamWorkspaceRichTextEditor.specSupport";

function keptText(value: string, keptGapId: string, marks: BodyMark[] = []): NativeExamBodySegment {
  return { kind: "text", text: value, marks, kept_gap_id: keptGapId };
}

function keptGap(gapId: string): NativeExamGap {
  return {
    accepted_values: ["ord", "ordet"],
    automatic_values: [],
    correct_option_id: null,
    excluded_automatic_values: [],
    gap_id: gapId,
    options: [],
  };
}

function itemWithKept(body: NativeExamBodyParagraph[]): NativeExamItem {
  return {
    ...newTeacherItem("item_001", 1, "gap_fill"),
    body,
    gaps: [],
    kept_gaps: [keptGap("gap_001")],
  };
}

/** A headless editor on the real schema, for typing and deletion probes. */
function openBody(body: NativeExamBodyParagraph[]): Editor {
  return new Editor({
    extensions: examRichTextExtensions({
      gapState: () => ({ label: "Lucka", accessibleLabel: "Lucka", empty: true }),
      pictureUrl: () => undefined,
      onUndo: () => undefined,
      onRedo: () => undefined,
      onToggleGapTool: () => false,
    }),
    content: editorContentFrom(body),
  });
}

const KEPT_BODY: NativeExamBodyParagraph[] = [
  paragraph(text("say "), keptText("ord", "gap_001"), text(" now")),
];

describe("examWorkspaceKeptGap", () => {
  afterEach(releaseEditor);

  it("round-trips a kept run through the editor unchanged", () => {
    const editor = openBody(KEPT_BODY);
    try {
      expect(bodyFromEditor(editor.getJSON())).toEqual(KEPT_BODY);
    } finally {
      editor.destroy();
    }
  });

  it("round-trips a kept run that carries formatting marks", () => {
    const body = [paragraph(text("say "), keptText("ord", "gap_001", ["bold", "italic"]), text(" now"))];
    const editor = openBody(body);
    try {
      expect(bodyFromEditor(editor.getJSON())).toEqual(body);
    } finally {
      editor.destroy();
    }
  });

  it("keeps the link on the word when typing before and after it", () => {
    const editor = openBody(KEPT_BODY);
    try {
      editor.commands.insertContentAt(posIn(editor, "ord", 0), "X");
      editor.commands.insertContentAt(posIn(editor, " now", 0), "Y");
      expect(bodyFromEditor(editor.getJSON())).toEqual([
        paragraph(text("say X"), keptText("ord", "gap_001"), text("Y now")),
      ]);
    } finally {
      editor.destroy();
    }
  });

  it("deletes the link with the whole word and withBody drops its kept record", () => {
    const editor = openBody(KEPT_BODY);
    try {
      const from = posIn(editor, "ord", 0);
      editor.commands.deleteRange({ from, to: from + 3 });
      const body = bodyFromEditor(editor.getJSON());
      expect(body).toEqual([paragraph(text("say  now"))]);
      expect(placedKeptGapIds(body)).toEqual([]);
      const item = withBody(itemWithKept(KEPT_BODY), body);
      expect(item.kept_gaps).toEqual([]);
    } finally {
      editor.destroy();
    }
  });

  it("keeps the kept record while a run still names it", () => {
    const item = withBody(itemWithKept(KEPT_BODY), KEPT_BODY);
    expect(item.kept_gaps.map((gap) => gap.gap_id)).toEqual(["gap_001"]);
  });

  it("never pastes the link from a copy inside the editor", async () => {
    const serial = openBody(KEPT_BODY);
    const slice = serial.state.doc.slice(0, serial.state.doc.content.size);
    const fragment = DOMSerializer.fromSchema(serial.schema).serializeFragment(slice.content);
    const holder = document.createElement("div");
    holder.appendChild(fragment);
    const html = holder.innerHTML;
    serial.destroy();
    // The clipboard copy really carries the mark's rendering: the test is not vacuous.
    expect(html).toContain("data-kept-gap");
    const opened = await mountEditor({ body: [paragraph(text("ab"))] });
    opened.editor.commands.setTextSelection(posIn(opened.editor, "ab", 1));
    paste(opened.surface, html);
    for (const entry of opened.last()) {
      for (const segment of entry.segments) {
        expect(segment.kind === "text" ? segment.kept_gap_id : null).toBeNull();
      }
    }
    expect(placedKeptGapIds(opened.last())).toEqual([]);
  });

  it("never pastes the link from outside HTML", async () => {
    const opened = await mountEditor({ body: [paragraph(text("ab"))] });
    opened.editor.commands.setTextSelection(posIn(opened.editor, "ab", 1));
    paste(opened.surface, '<p>x<span data-kept-gap="gap_001">y</span>z</p>');
    const [pasted] = opened.last();
    expect(pasted.segments.every((segment) => segment.kind === "text")).toBe(true);
    for (const segment of pasted.segments) {
      expect(segment.kind === "text" ? segment.kept_gap_id : null).toBeNull();
    }
  });

  it("gives a new text segment kept_gap_id null", () => {
    const body = bodyFromEditor({
      type: "doc",
      content: [{ type: "paragraph", content: [{ type: "text", text: "new" }] }],
    });
    expect(body).toEqual([paragraph(text("new"))]);
    expect(body[0]?.segments[0]).toEqual({ kind: "text", text: "new", marks: [], kept_gap_id: null });
  });

  it("keeps adjacent runs with different kept ids apart and merges equal ones", () => {
    const body = bodyFromEditor({
      type: "doc",
      content: [
        {
          type: "paragraph",
          content: [
            { type: "text", text: "a", marks: [{ type: "examKeptGap", attrs: { keptGapId: "gap_001" } }] },
            { type: "text", text: "b", marks: [{ type: "examKeptGap", attrs: { keptGapId: "gap_001" } }] },
            { type: "text", text: "c" },
            { type: "text", text: "d", marks: [{ type: "examKeptGap", attrs: { keptGapId: "gap_002" } }] },
          ],
        },
      ],
    });
    expect(body).toEqual([
      paragraph(keptText("ab", "gap_001"), text("c"), keptText("d", "gap_002")),
    ]);
  });

  it("sets kept_gap_id null on the text withGapAsText creates", () => {
    const source: NativeExamItem = {
      ...newTeacherItem("item_002", 2, "gap_fill"),
      body: [paragraph({ kind: "gap", gap_id: "gap_007" })],
      gaps: [{ ...keptGap("gap_007"), accepted_values: ["Svart"] }],
    };
    const result = withGapAsText(source, "gap_007");
    expect(result.body[0]?.segments).toEqual([
      { kind: "text", text: "Svart", marks: [], kept_gap_id: null },
    ]);
  });

  it("reads a kept word as plain text", () => {
    expect(paragraphText(KEPT_BODY[0]!)).toBe("say ord now");
  });
});
