/**
 * Exam workspace question-text editor, marks, headings and shortcuts.
 *
 * Expected behavior:
 *   A stored mark renders as its semantic element and a heading level as a
 *   heading. Selecting text and pressing the toolbar glyph or Ctrl/Cmd+B
 *   adds the mark, pressing it again removes it, superscript and subscript
 *   exclude each other, and a heading glyph sets and clears the paragraph's
 *   level. Each toolbar change is one structural edit of the whole body,
 *   and the stored body keeps only the five supported marks.
 *
 * jsdom has no layout, so selections are set through TipTap commands; the
 * toolbar buttons are clicked and the shortcut is a real `keydown`.
 */

import { describe, expect, it } from "vitest";

import {
  buildGapItem,
  mountEditor,
  posIn,
  press,
  surface,
  tiptap,
} from "./ExamWorkspaceBodyEditor.specSupport";
import type { MountedBodyEditor } from "./ExamWorkspaceBodyEditor.specSupport";

type UpdateEvent = [string, Array<{ heading_level: number | null; segments: unknown[] }>, boolean];

function selectWord(wrapper: MountedBodyEditor, word: string): void {
  const editor = tiptap(wrapper);
  const from = posIn(editor, word, 0);
  editor.commands.setTextSelection({ from, to: from + word.length });
  // The surface takes focus, which registers it as the toolbar's target.
  surface(wrapper).focus();
}

function lastUpdate(wrapper: MountedBodyEditor): UpdateEvent {
  return (wrapper.emitted("updateBody") as UpdateEvent[]).at(-1)!;
}

describe("ExamWorkspaceBodyEditor marks", () => {
  it("renders stored marks as semantic elements and the heading level as a heading", async () => {
    const wrapper = await mountEditor(
      buildGapItem({
        body: [
          {
            heading_level: 2,
            segments: [
              { kind: "text", text: "Vatten", marks: ["bold", "italic"] },
              { gap_id: "gap_001", kind: "gap" },
              { kind: "text", text: " och ", marks: ["superscript"] },
              { kind: "text", text: "is", marks: ["subscript"] },
            ],
          },
        ],
      }),
    );

    const root = surface(wrapper);
    expect(root.querySelector("h2")).not.toBeNull();
    expect(root.querySelector("strong em, em strong")?.textContent).toBe("Vatten");
    expect(root.querySelector("sup")?.textContent).toBe(" och ");
    expect(root.querySelector("sub")?.textContent).toBe("is");
    wrapper.unmount();
  });

  it("adds a mark over the selection from the toolbar as one structural body edit", async () => {
    const wrapper = await mountEditor();
    selectWord(wrapper, "Vatten");

    await wrapper.get('[data-test="exam-workspace-body-mark-bold"]').trigger("click");

    const [itemId, body, structural] = lastUpdate(wrapper);
    expect(itemId).toBe("item_001");
    expect(body[0]!.segments[0]).toEqual({ kind: "text", marks: ["bold"], text: "Vatten" });
    expect(body[0]!.segments[1]).toEqual({ kind: "text", marks: [], text: " kokar vid " });
    expect(structural).toBe(true);
    wrapper.unmount();
  });

  it("toggles a mark off when the whole selection already carries it", async () => {
    const wrapper = await mountEditor(
      buildGapItem({
        body: [
          {
            heading_level: null,
            segments: [
              { kind: "text", text: "Vatten", marks: ["bold"] },
              { kind: "text", text: " kokar.", marks: [] },
            ],
          },
        ],
        gaps: [],
      }),
    );
    selectWord(wrapper, "Vatten");

    await wrapper.get('[data-test="exam-workspace-body-mark-bold"]').trigger("click");

    expect(lastUpdate(wrapper)[1][0]!.segments).toEqual([
      { kind: "text", marks: [], text: "Vatten kokar." },
    ]);
    wrapper.unmount();
  });

  it("toggles bold with Ctrl+B on the selected text", async () => {
    const wrapper = await mountEditor();
    selectWord(wrapper, "Vatten");

    press(surface(wrapper), "b", { ctrlKey: true });

    expect(lastUpdate(wrapper)[1][0]!.segments[0]).toEqual({ kind: "text", marks: ["bold"], text: "Vatten" });
    wrapper.unmount();
  });

  it("makes superscript replace subscript on the selection", async () => {
    const wrapper = await mountEditor(
      buildGapItem({
        body: [
          { heading_level: null, segments: [{ kind: "text", text: "H2O", marks: ["subscript"] }] },
        ],
        gaps: [],
      }),
    );
    selectWord(wrapper, "H2O");

    await wrapper.get('[data-test="exam-workspace-body-mark-superscript"]').trigger("click");

    expect(lastUpdate(wrapper)[1][0]!.segments).toEqual([
      { kind: "text", marks: ["superscript"], text: "H2O" },
    ]);
    wrapper.unmount();
  });

  it("sets and clears the heading level of the paragraph with the caret", async () => {
    const wrapper = await mountEditor();
    selectWord(wrapper, "Vatten");

    await wrapper.get('[data-test="exam-workspace-body-heading-2"]').trigger("click");
    expect(lastUpdate(wrapper)[1].map((paragraph) => paragraph.heading_level)).toEqual([2, null]);
    expect(lastUpdate(wrapper)[2]).toBe(true);

    await wrapper.get('[data-test="exam-workspace-body-heading-2"]').trigger("click");
    expect(lastUpdate(wrapper)[1].map((paragraph) => paragraph.heading_level)).toEqual([null, null]);
    wrapper.unmount();
  });

  it("keeps the mark of the text it edits", async () => {
    const wrapper = await mountEditor(
      buildGapItem({
        body: [
          { heading_level: null, segments: [{ kind: "text", text: "fet", marks: ["bold"] }] },
        ],
        gaps: [],
      }),
    );
    const editor = tiptap(wrapper);

    editor.commands.insertContentAt(posIn(editor, "fet", 1), "x");

    expect(lastUpdate(wrapper)[1][0]!.segments).toEqual([{ kind: "text", marks: ["bold"], text: "fxet" }]);
    wrapper.unmount();
  });
});
