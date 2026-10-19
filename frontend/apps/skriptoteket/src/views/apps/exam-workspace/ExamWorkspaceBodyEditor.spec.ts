/**
 * Exam workspace question-text editor, text editing.
 *
 * Expected behavior:
 *   The question text is one editing surface holding every paragraph, with
 *   gap chips and pictures inline. Every change emits the item's whole body
 *   at once: typing as a coalescing edit, and a change of the gaps, pictures
 *   or formatting as a structural one. A selection across paragraphs deletes
 *   with Backspace, gaps and pictures included, and Backspace at a paragraph
 *   start merges. Another item's body replaces the text.
 *
 * jsdom has no layout, so selections are set through TipTap commands and keys
 * are real `keydown` events handled by the editor's keymaps; characters are
 * inserted with `insertContent`, because the browser inserts a typed one.
 */

import { describe, expect, it } from "vitest";
import { nextTick } from "vue";

import { buildGapItem, buildMergeItem, mountEditor, posIn, press, surface, tiptap } from "./ExamWorkspaceBodyEditor.specSupport";

type UpdateEvent = [string, Array<{ heading_level: number | null; segments: unknown[] }>, boolean];

describe("ExamWorkspaceBodyEditor text editing", () => {
  it("renders the whole question as one labelled surface with inline gap chips and pictures", async () => {
    const wrapper = await mountEditor();

    const root = surface(wrapper);
    expect(wrapper.findAll('[role="textbox"]')).toHaveLength(1);
    expect(root.getAttribute("aria-label")).toBe("Frågetext");
    expect(root.getAttribute("contenteditable")).toBe("true");
    expect(root.querySelectorAll("p")).toHaveLength(2);

    const filled = wrapper.get('[data-gap-id="gap_001"]');
    expect(filled.attributes("data-label")).toBe("100");
    expect(filled.attributes("aria-label")).toBe("Lucka 1, godkända svar: 100");
    expect(filled.attributes("data-empty")).toBeUndefined();
    expect(filled.text()).toBe("");

    const empty = wrapper.get('[data-gap-id="gap_002"]');
    expect(empty.attributes("data-label")).toBe("Lucka 2");
    expect(empty.attributes("aria-label")).toBe("Lucka 2, saknar godkända svar");
    expect(empty.attributes("data-empty")).toBe("true");

    expect(wrapper.get('[data-asset-id="asset_001"]').attributes("role")).toBe("img");
    expect(root.textContent).toBe("Vatten kokar vid  grader och fryser vid  grader.Se ");
    wrapper.unmount();
  });

  it("emits the whole body as a coalescing edit when text is typed", async () => {
    const wrapper = await mountEditor();
    const editor = tiptap(wrapper);

    editor.commands.insertContentAt(posIn(editor, "Vatten kokar vid ", 6), " x");

    const [event] = wrapper.emitted("updateBody") as UpdateEvent[];
    expect(event![0]).toBe("item_001");
    expect(event![1]).toHaveLength(2);
    expect(event![1][0]!.segments[0]).toEqual({ kind: "text", marks: [], text: "Vatten x kokar vid ", kept_gap_id: null });
    expect(event![1][1]!.segments).toEqual([
      { kind: "text", marks: [], text: "Se ", kept_gap_id: null },
      { kind: "asset", asset_id: "asset_001" },
    ]);
    expect(event![2]).toBe(false);
    wrapper.unmount();
  });

  it("deletes a selection across two paragraphs, a gap and a picture included, and merges them", async () => {
    const wrapper = await mountEditor(buildMergeItem());
    const editor = tiptap(wrapper);
    const from = posIn(editor, " B ", 2);
    let pictureEnd = -1;
    editor.state.doc.descendants((node, pos) => {
      if (node.type.name === "examPicture") {
        pictureEnd = pos + node.nodeSize;
      }
      return pictureEnd < 0;
    });
    editor.commands.setTextSelection({ from, to: pictureEnd });

    const event = press(surface(wrapper), "Backspace");

    expect(event.defaultPrevented).toBe(true);
    const emitted = wrapper.emitted("updateBody") as UpdateEvent[];
    expect(emitted).toHaveLength(1);
    expect(emitted[0]![1]).toEqual([
      {
        heading_level: null,
        segments: [
          { kind: "text", marks: [], text: "A ", kept_gap_id: null },
          { kind: "gap", gap_id: "gap_001" },
          { kind: "text", marks: [], text: " B D", kept_gap_id: null },
        ],
      },
    ]);
    expect(emitted[0]![2]).toBe(true);
    wrapper.unmount();
  });

  it("merges two paragraphs with Backspace at the start of the second", async () => {
    const wrapper = await mountEditor(
      buildGapItem({
        body: [
          { heading_level: null, segments: [{ kind: "text", marks: [], text: "Ett" }] },
          { heading_level: null, segments: [{ kind: "text", marks: [], text: "Två" }] },
        ],
        gaps: [],
      }),
    );
    const editor = tiptap(wrapper);
    editor.commands.setTextSelection(posIn(editor, "Två", 0));

    press(surface(wrapper), "Backspace");

    const [event] = wrapper.emitted("updateBody") as UpdateEvent[];
    expect(event![1]).toEqual([
      { heading_level: null, segments: [{ kind: "text", marks: [], text: "EttTvå", kept_gap_id: null }] },
    ]);
    wrapper.unmount();
  });

  it("emits the empty body when the whole text is deleted", async () => {
    const wrapper = await mountEditor(
      buildGapItem({
        body: [{ heading_level: null, segments: [{ kind: "text", marks: [], text: "Hej" }] }],
        gaps: [],
      }),
    );
    tiptap(wrapper).commands.selectAll();

    press(surface(wrapper), "Backspace");

    const [event] = wrapper.emitted("updateBody") as UpdateEvent[];
    expect(event![1]).toEqual([]);
    wrapper.unmount();
  });

  it("replaces the text when another item is shown, without emitting an edit", async () => {
    const wrapper = await mountEditor();
    await wrapper.setProps({
      item: buildGapItem({
        item_id: "item_002",
        body: [{ heading_level: null, segments: [{ kind: "text", marks: [], text: "Annan fråga" }] }],
        gaps: [],
      }),
    });
    await nextTick();
    await nextTick();

    expect(surface(wrapper).textContent).toBe("Annan fråga");
    expect(surface(wrapper).querySelectorAll("p")).toHaveLength(1);
    expect(wrapper.emitted("updateBody")).toBeUndefined();
    wrapper.unmount();
  });

  it("gives each question its own editor, so the first edit after switching is the new question's typing", async () => {
    const wrapper = await mountEditor();
    const first = tiptap(wrapper);
    first.commands.setTextSelection(posIn(first, "Vatten kokar vid ", 6));
    await wrapper.setProps({
      item: buildGapItem({
        item_id: "item_002",
        body: [{ heading_level: null, segments: [{ kind: "text", marks: [], text: "Annan fråga" }] }],
        gaps: [],
      }),
    });
    await nextTick();
    await nextTick();
    const second = tiptap(wrapper);

    expect(second).not.toBe(first);
    second.commands.setTextSelection(posIn(second, "Annan fråga", 11));
    second.commands.insertContent("?");

    expect(wrapper.emitted("updateBody")).toEqual([
      ["item_002", [{ heading_level: null, segments: [{ kind: "text", marks: [], text: "Annan fråga?", kept_gap_id: null }] }], false],
    ]);
    wrapper.unmount();
  });

  it("shows nothing editable and emits no edit while disabled", async () => {
    const wrapper = await mountEditor(buildGapItem(), { disabled: true });
    const editor = tiptap(wrapper);

    expect(surface(wrapper).getAttribute("contenteditable")).toBe("false");
    editor.commands.insertContentAt(posIn(editor, "Vatten kokar vid ", 6), " x");

    expect(wrapper.emitted("updateBody")).toBeUndefined();
    wrapper.unmount();
  });
});
