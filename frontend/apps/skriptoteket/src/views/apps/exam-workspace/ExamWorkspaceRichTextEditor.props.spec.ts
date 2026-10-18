/**
 * Exam workspace rich-text editor: the body prop and the disabled state.
 *
 * Expected behavior (TASK-SKRIPT-40-04-06 D1):
 *   A new body from the owner replaces the content without an update; the
 *   owner echoing the last emitted body leaves the caret alone. A disabled
 *   editor changes and emits nothing, and enabling it makes it editable
 *   again. The surface follows its label, invalid and describedBy props.
 */

import { afterEach, describe, expect, it } from "vitest";
import {
  gap,
  mountEditor,
  paragraph,
  paste,
  posIn,
  press,
  releaseEditor,
  text,
} from "./ExamWorkspaceRichTextEditor.specSupport";

describe("ExamWorkspaceRichTextEditor", () => {
  afterEach(releaseEditor);

  describe("body prop and disabled state", () => {
    it("replaces the content when a new body arrives, without emitting an update", async () => {
      const opened = await mountEditor({ body: [paragraph(text("old"))] });
      await opened.setProps({ body: [paragraph(text("new"), gap("gap_001"))] });
      expect(opened.editor.getText()).toContain("new");
      expect(opened.surface.querySelector("[data-atom='gap']")).not.toBeNull();
      expect(opened.updates).toHaveLength(0);
    });

    it("keeps the content and the caret when the owner echoes the last emitted body", async () => {
      const opened = await mountEditor({ body: [paragraph(text("ab"))] });
      opened.editor.commands.setTextSelection(posIn(opened.editor, "ab", 1));
      opened.editor.commands.insertContent("X");
      const echoed = opened.last();
      const caret = opened.editor.state.selection.from;
      await opened.setProps({ body: echoed });
      expect(opened.editor.state.selection.from).toBe(caret);
      expect(opened.editor.getText()).toBe("aXb");
      expect(opened.updates).toHaveLength(1);
    });

    it("treats a body the owner changed back to an earlier value as new content", async () => {
      const opened = await mountEditor({ body: [paragraph(text("ab"))] });
      opened.editor.commands.insertContent("X");
      expect(opened.updates).toHaveLength(1);
      await opened.setProps({ body: [paragraph(text("ab"))] });
      expect(opened.editor.getText()).toBe("ab");
      expect(opened.updates).toHaveLength(1);
    });

    it("counts a later change as structural when it differs from the replaced body's atoms", async () => {
      const opened = await mountEditor({ body: [paragraph(text("a"))] });
      await opened.setProps({ body: [paragraph(text("a"), gap("gap_001"), text("b"))] });
      opened.editor.commands.setTextSelection(posIn(opened.editor, "b", 1));
      opened.editor.commands.insertContent("c");
      expect(opened.lastStructural()).toBe(false);
    });

    it("changes nothing and emits nothing while disabled", async () => {
      const opened = await mountEditor({ body: [paragraph(text("keep"))], disabled: true });
      expect(opened.surface.getAttribute("contenteditable")).toBe("false");
      opened.editor.commands.setTextSelection({ from: posIn(opened.editor, "keep", 0), to: posIn(opened.editor, "keep", 4) });
      press(opened.surface, "Backspace");
      paste(opened.surface, "<p>pasted</p>", "pasted");
      expect(opened.editor.getText()).toBe("keep");
      expect(opened.updates).toHaveLength(0);
    });

    it("becomes editable again when enabled", async () => {
      const opened = await mountEditor({ body: [paragraph(text("abc"))], disabled: true });
      await opened.setProps({ disabled: false });
      expect(opened.surface.getAttribute("contenteditable")).toBe("true");
      opened.editor.commands.setTextSelection({ from: posIn(opened.editor, "abc", 0), to: posIn(opened.editor, "abc", 3) });
      press(opened.surface, "Backspace");
      expect(opened.last()).toEqual([]);
    });

    it("names the surface and follows invalid and describedBy", async () => {
      const opened = await mountEditor({ body: [], label: "Frågetext" });
      expect(opened.surface.getAttribute("aria-label")).toBe("Frågetext");
      expect(opened.surface.getAttribute("aria-invalid")).toBeNull();
      await opened.wrapper.setProps({ editorProps: { body: [], label: "Alternativ 2", invalid: true, describedBy: "err-1" } });
      expect(opened.surface.getAttribute("aria-label")).toBe("Alternativ 2");
      expect(opened.surface.getAttribute("aria-invalid")).toBe("true");
      expect(opened.surface.getAttribute("aria-describedby")).toBe("err-1");
    });
  });
});
