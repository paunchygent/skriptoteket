/**
 * Exam workspace rich-text editor: word-processor editing.
 *
 * Expected behavior (TASK-SKRIPT-40-04-06 D1):
 *   One stored body is one document, so Backspace over a range or at a
 *   paragraph start, Delete, Enter and Shift+Enter edit it as a word
 *   processor does and emit the mapped body at once. Shared mounting and
 *   key helpers are in `ExamWorkspaceRichTextEditor.specSupport.ts`.
 */

import { afterEach, describe, expect, it } from "vitest";
import {
  atomPos,
  gap,
  mountEditor,
  paragraph,
  picture,
  posIn,
  press,
  releaseEditor,
  text,
  TWO_PARAGRAPHS,
} from "./ExamWorkspaceRichTextEditor.specSupport";

describe("ExamWorkspaceRichTextEditor", () => {
  afterEach(releaseEditor);

  describe("word-processor editing", () => {
    it("deletes a selection across two paragraphs with one Backspace and merges them", async () => {
      const opened = await mountEditor({ body: TWO_PARAGRAPHS });
      opened.editor.commands.setTextSelection({
        from: posIn(opened.editor, "first", 2),
        to: posIn(opened.editor, "second", 3),
      });
      press(opened.surface, "Backspace");
      expect(opened.updates).toHaveLength(1);
      expect(opened.last()).toEqual([paragraph(text("fiond"))]);
    });

    it("deletes a range holding a gap and a picture in one keystroke and reports it as structural", async () => {
      const opened = await mountEditor({
        body: [
          paragraph(text("a"), gap("gap_001"), text("b")),
          paragraph(text("c"), picture("asset_1"), text("d")),
        ],
      });
      opened.editor.commands.setTextSelection({
        from: posIn(opened.editor, "a", 1),
        to: posIn(opened.editor, "d", 0),
      });
      press(opened.surface, "Backspace");
      expect(opened.updates).toHaveLength(1);
      expect(opened.last()).toEqual([paragraph(text("ad"))]);
      expect(opened.lastStructural()).toBe(true);
    });

    it("deletes an atom right after the caret with the first Backspace", async () => {
      // ProseMirror stops the browser's own delete next to a non-text inline
      // node and removes the node itself, so one Backspace deletes it; it does
      // not first select it.
      const opened = await mountEditor({ body: [paragraph(text("a"), gap("gap_001"), text("b"))] });
      const gapPos = atomPos(opened.editor, "examGap");
      opened.editor.commands.setTextSelection(gapPos + 1);
      press(opened.surface, "Backspace");
      expect(opened.updates).toHaveLength(1);
      expect(opened.last()).toEqual([paragraph(text("ab"))]);
      expect(opened.lastStructural()).toBe(true);
    });

    it("deletes a node-selected atom with Backspace and keeps its neighbours", async () => {
      const opened = await mountEditor({ body: [paragraph(text("a"), picture("asset_1"), text("b"))] });
      opened.editor.commands.setNodeSelection(atomPos(opened.editor, "examPicture"));
      press(opened.surface, "Backspace");
      expect(opened.updates).toHaveLength(1);
      expect(opened.last()).toEqual([paragraph(text("ab"))]);
      expect(opened.lastStructural()).toBe(true);
    });

    it("deletes an atom right after the caret with Delete from the other side", async () => {
      const opened = await mountEditor({ body: [paragraph(text("a"), gap("gap_001"), text("b"))] });
      opened.editor.commands.setTextSelection(atomPos(opened.editor, "examGap"));
      press(opened.surface, "Delete");
      expect(opened.last()).toEqual([paragraph(text("ab"))]);
      expect(opened.lastStructural()).toBe(true);
    });

    it("merges a paragraph into the one before it with Backspace at its start", async () => {
      const opened = await mountEditor({ body: TWO_PARAGRAPHS });
      opened.editor.commands.setTextSelection(posIn(opened.editor, "second", 0));
      press(opened.surface, "Backspace");
      expect(opened.last()).toEqual([paragraph(text("firstsecond"))]);
    });

    it("removes an emptied paragraph with Backspace", async () => {
      const opened = await mountEditor({
        body: [paragraph(text("a")), paragraph(text("b")), paragraph(text("c"))],
      });
      opened.editor.commands.setTextSelection({
        from: posIn(opened.editor, "b", 0),
        to: posIn(opened.editor, "b", 1),
      });
      press(opened.surface, "Backspace");
      expect(opened.last()).toEqual([paragraph(text("a")), { heading_level: null, segments: [] }, paragraph(text("c"))]);
      press(opened.surface, "Backspace");
      expect(opened.last()).toEqual([paragraph(text("a")), paragraph(text("c"))]);
    });

    it("emits the empty body when everything is deleted", async () => {
      const opened = await mountEditor({ body: TWO_PARAGRAPHS });
      opened.editor.commands.selectAll();
      press(opened.surface, "Backspace");
      expect(opened.last()).toEqual([]);
    });

    it("splits a paragraph on Enter", async () => {
      const opened = await mountEditor({ body: [paragraph(text("abcd"))] });
      opened.editor.commands.setTextSelection(posIn(opened.editor, "abcd", 2));
      press(opened.surface, "Enter");
      expect(opened.last()).toEqual([paragraph(text("ab")), paragraph(text("cd"))]);
    });

    it("inserts a hard break in the same paragraph on Shift+Enter", async () => {
      const opened = await mountEditor({ body: [paragraph(text("abcd"))] });
      opened.editor.commands.setTextSelection(posIn(opened.editor, "abcd", 2));
      press(opened.surface, "Enter", { shiftKey: true });
      expect(opened.last()).toEqual([paragraph(text("ab\ncd"))]);
    });
  });
});
