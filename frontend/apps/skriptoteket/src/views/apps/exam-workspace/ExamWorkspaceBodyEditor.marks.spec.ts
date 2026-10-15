/**
 * Exam workspace rich paragraph marks, toolbar and shortcuts.
 *
 * Expected behavior:
 *   A stored mark renders as its semantic element and a heading level as the
 *   paragraph's data attribute and size. Selecting text and pressing the
 *   toolbar glyph or Ctrl/Cmd+B, I or U adds the mark, pressing it again
 *   removes it, superscript and subscript exclude each other, and a heading
 *   glyph sets and clears the paragraph level. Typing inside marked text
 *   keeps the mark. Every change is emitted as normalized segments, so the
 *   document keeps only the five supported marks.
 */

import { describe, expect, it } from "vitest";

import { buildGapItem, mountEditor, paragraph } from "./ExamWorkspaceBodyEditor.specSupport";

function firstTextNode(element: HTMLElement): Text {
  const walker = document.createTreeWalker(element, NodeFilter.SHOW_TEXT);
  const node = walker.nextNode();
  if (!node) {
    throw new Error("paragraph has no text node");
  }
  return node as Text;
}

function selectText(element: HTMLElement, from: number, to: number): void {
  const node = firstTextNode(element);
  const range = document.createRange();
  range.setStart(node, Math.min(from, node.data.length));
  range.setEnd(node, Math.min(to, node.data.length));
  const selection = window.getSelection()!;
  selection.removeAllRanges();
  selection.addRange(range);
}

describe("ExamWorkspaceBodyEditor marks", () => {
  it("renders stored marks as semantic elements and the heading level on the paragraph", () => {
    const wrapper = mountEditor(
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

    const element = paragraph(wrapper, 0);
    expect(element.getAttribute("data-heading-level")).toBe("2");
    expect(element.querySelector('strong[data-mark="bold"] em[data-mark="italic"]')?.textContent).toBe(
      "Vatten",
    );
    expect(element.querySelector('sup[data-mark="superscript"]')?.textContent).toBe(" och ");
    expect(element.querySelector('sub[data-mark="subscript"]')?.textContent).toBe("is");
    expect(element.className).toContain("text-xl");
    wrapper.unmount();
  });

  it("adds a mark over the selection from the toolbar and emits normalized segments", async () => {
    const wrapper = mountEditor();
    const element = paragraph(wrapper, 0);
    await wrapper.get('[data-test="exam-workspace-body-paragraph-0"]').trigger("focus");
    selectText(element, 0, 6);

    await wrapper.get('[data-test="exam-workspace-body-mark-bold"]').trigger("click");

    const [, paragraphIndex, segments] = wrapper.emitted("updateParagraphSegments")![0]!;
    expect(paragraphIndex).toBe(0);
    expect((segments as unknown[])[0]).toEqual({ kind: "text", marks: ["bold"], text: "Vatten" });
    expect(element.querySelector('strong[data-mark="bold"]')?.textContent).toBe("Vatten");
    wrapper.unmount();
  });

  it("toggles a mark off when the whole selection already carries it", async () => {
    const wrapper = mountEditor(
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
      }),
    );
    const element = paragraph(wrapper, 0);
    await wrapper.get('[data-test="exam-workspace-body-paragraph-0"]').trigger("focus");
    selectText(element, 0, 6);

    await wrapper.get('[data-test="exam-workspace-body-mark-bold"]').trigger("click");

    const [, , segments] = wrapper.emitted("updateParagraphSegments")![0]!;
    expect((segments as unknown[])[0]).toEqual({
      kind: "text",
      marks: [],
      text: "Vatten kokar.",
    });
    expect(element.querySelector('strong[data-mark="bold"]')).toBeNull();
    wrapper.unmount();
  });

  it("toggles bold with Ctrl+B on the selected text", async () => {
    const wrapper = mountEditor();
    const element = paragraph(wrapper, 0);
    await wrapper.get('[data-test="exam-workspace-body-paragraph-0"]').trigger("focus");
    selectText(element, 0, 6);

    await wrapper.get('[data-test="exam-workspace-body-paragraph-0"]').trigger("keydown", {
      ctrlKey: true,
      key: "b",
    });

    const [, , segments] = wrapper.emitted("updateParagraphSegments")![0]!;
    expect((segments as unknown[])[0]).toEqual({ kind: "text", marks: ["bold"], text: "Vatten" });
    wrapper.unmount();
  });

  it("makes superscript replace subscript on the selection", async () => {
    const wrapper = mountEditor(
      buildGapItem({
        body: [
          {
            heading_level: null,
            segments: [
              { kind: "text", text: "H", marks: [] },
              { kind: "text", text: "2", marks: ["subscript"] },
              { kind: "text", text: "O", marks: [] },
            ],
          },
        ],
      }),
    );
    const element = paragraph(wrapper, 0);
    await wrapper.get('[data-test="exam-workspace-body-paragraph-0"]').trigger("focus");
    const subscript = element.querySelector('sub[data-mark="subscript"]')!.firstChild as Text;
    const range = document.createRange();
    range.selectNodeContents(subscript);
    const selection = window.getSelection()!;
    selection.removeAllRanges();
    selection.addRange(range);

    await wrapper.get('[data-test="exam-workspace-body-mark-superscript"]').trigger("click");

    const [, , segments] = wrapper.emitted("updateParagraphSegments")![0]!;
    expect((segments as unknown[])[1]).toEqual({
      kind: "text",
      marks: ["superscript"],
      text: "2",
    });
    expect(element.querySelector('sup[data-mark="superscript"]')?.textContent).toBe("2");
    expect(element.querySelector('sub[data-mark="subscript"]')).toBeNull();
    wrapper.unmount();
  });

  it("sets and clears the heading level from the toolbar", async () => {
    const item = buildGapItem();
    const wrapper = mountEditor(item);
    await wrapper.get('[data-test="exam-workspace-body-paragraph-0"]').trigger("focus");

    await wrapper.get('[data-test="exam-workspace-body-heading-2"]').trigger("click");
    expect(wrapper.emitted("updateParagraphHeading")).toEqual([["item_001", 0, 2]]);

    await wrapper.setProps({
      item: {
        ...item,
        body: [{ ...item.body[0]!, heading_level: 2 }, ...item.body.slice(1)],
      },
    });
    await wrapper.get('[data-test="exam-workspace-body-heading-2"]').trigger("click");
    expect(wrapper.emitted("updateParagraphHeading")).toEqual([
      ["item_001", 0, 2],
      ["item_001", 0, null],
    ]);
    wrapper.unmount();
  });

  it("keeps the mark of the text it edits", async () => {
    const item = buildGapItem({
      body: [
        {
          heading_level: null,
          segments: [
            { kind: "text", text: "Vatten", marks: ["bold"] },
            { kind: "text", text: " kokar.", marks: [] },
          ],
        },
      ],
    });
    const wrapper = mountEditor(item);
    const element = paragraph(wrapper, 0);
    const marked = element.querySelector('strong[data-mark="bold"]')!.firstChild as Text;

    marked.data = "Vattnet";
    await wrapper.get('[data-test="exam-workspace-body-paragraph-0"]').trigger("input");

    const [, , segments] = wrapper.emitted("updateParagraphSegments")![0]!;
    expect(segments).toEqual([
      { kind: "text", marks: ["bold"], text: "Vattnet" },
      { kind: "text", marks: [], text: " kokar." },
    ]);
    wrapper.unmount();
  });
});
