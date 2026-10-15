/**
 * Exam workspace question-text editor, text editing.
 *
 * Expected behavior:
 *   Each paragraph is one editable text with gap chips and image markers
 *   inline. Text edits emit the paragraph's normalized segments without
 *   rebuilding the DOM the teacher is typing in. Removing a gap or image is
 *   refused: the paragraph is restored and a Swedish status line explains
 *   why. Drops are refused, a paste inserts plain text at the caret, and an
 *   IME composition is read only once it ends.
 */

import { describe, expect, it } from "vitest";

import { buildGapItem, mountEditor, paragraph } from "./ExamWorkspaceBodyEditor.specSupport";

describe("ExamWorkspaceBodyEditor text editing", () => {
  it("renders each paragraph as one text with inline gap chips and image markers", () => {
    const wrapper = mountEditor();

    const first = wrapper.get('[data-test="exam-workspace-body-paragraph-0"]');
    expect(first.attributes("aria-label")).toBe("Frågetext, stycke 1");
    expect(first.attributes("contenteditable")).not.toBe("false");

    const filledChip = wrapper.get('[data-test="exam-workspace-body-gap-0-1"]');
    expect(filledChip.attributes("data-label")).toBe("100");
    expect(filledChip.text()).toBe("");
    expect(filledChip.attributes("data-gap-id")).toBe("gap_001");
    expect(filledChip.attributes("contenteditable")).toBe("false");
    expect(filledChip.attributes("role")).toBe("button");

    const emptyChip = wrapper.get('[data-test="exam-workspace-body-gap-0-3"]');
    expect(emptyChip.attributes("data-label")).toBe("Lucka 2");
    expect(emptyChip.classes()).toContain("border-warning");

    const asset = wrapper.get('[data-asset-id="asset_001"]');
    expect(asset.attributes("data-label")).toBe("Bild");
    expect(asset.attributes("aria-label")).toBe("Bild");
    expect(first.element.textContent).toBe("Vatten kokar vid  grader och fryser vid  grader.");
    expect(paragraph(wrapper, 1).textContent).toBe("Se ");
    wrapper.unmount();
  });

  it("emits normalized paragraph segments and keeps the typed DOM in place", async () => {
    const item = buildGapItem();
    const wrapper = mountEditor(item);
    const element = paragraph(wrapper, 0);
    const firstText = element.firstChild as Text;

    firstText.data = "Vatten\nkokar vid ";
    element.dispatchEvent(new Event("input", { bubbles: true }));

    const emitted = wrapper.emitted("updateParagraphSegments");
    expect(emitted).toHaveLength(1);
    const [itemId, paragraphIndex, segments] = emitted![0]!;
    expect(itemId).toBe("item_001");
    expect(paragraphIndex).toBe(0);
    expect(segments).toEqual([
      { kind: "text", marks: [], text: "Vatten\nkokar vid " },
      { gap_id: "gap_001", kind: "gap" },
      { kind: "text", marks: [], text: " grader och fryser vid " },
      { gap_id: "gap_002", kind: "gap" },
      { kind: "text", marks: [], text: " grader." },
    ]);

    await wrapper.setProps({
      item: { ...item, body: [{ heading_level: null, segments: segments as never }, item.body[1]!] },
    });
    expect(paragraph(wrapper, 0).firstChild).toBe(firstText);
    wrapper.unmount();
  });

  it("re-indexes chips when the text before a gap disappears", () => {
    const wrapper = mountEditor();
    const element = paragraph(wrapper, 0);
    (element.firstChild as Text).data = "";
    element.dispatchEvent(new Event("input", { bubbles: true }));

    const [, , segments] = wrapper.emitted("updateParagraphSegments")![0]!;
    expect((segments as unknown[])[0]).toEqual({ gap_id: "gap_001", kind: "gap" });
    expect(wrapper.find('[data-test="exam-workspace-body-gap-0-0"]').exists()).toBe(true);
    wrapper.unmount();
  });

  it("restores a removed gap and explains why", async () => {
    const wrapper = mountEditor();
    const element = paragraph(wrapper, 0);
    element.querySelector('[data-gap-id="gap_002"]')!.remove();
    element.dispatchEvent(new Event("input", { bubbles: true }));
    await wrapper.vm.$nextTick();

    expect(wrapper.emitted("updateParagraphSegments")).toBeUndefined();
    expect(element.querySelector('[data-gap-id="gap_002"]')).not.toBeNull();
    const status = wrapper.get('[data-test="exam-workspace-body-status"]');
    expect(status.attributes("role")).toBe("status");
    expect(status.text()).toBe("Luckor och bilder kan inte tas bort i texten.");
    wrapper.unmount();
  });

  it("refuses an emptied paragraph and restores it when focus leaves", async () => {
    const item = buildGapItem({ body: [{ heading_level: null, segments: [{ kind: "text", marks: [], text: "Hej" }] }] });
    const wrapper = mountEditor(item);
    const element = paragraph(wrapper, 0);
    (element.firstChild as Text).data = "";
    element.dispatchEvent(new Event("input", { bubbles: true }));
    await wrapper.vm.$nextTick();

    expect(wrapper.emitted("updateParagraphSegments")).toBeUndefined();
    expect(wrapper.get('[data-test="exam-workspace-body-status"]').text()).toBe(
      "Stycket måste innehålla text.",
    );

    element.dispatchEvent(new FocusEvent("focusout", { bubbles: true }));
    await wrapper.vm.$nextTick();
    expect(element.textContent).toBe("Hej");
    expect(wrapper.find('[data-test="exam-workspace-body-status"]').exists()).toBe(false);
    wrapper.unmount();
  });

  it("blocks a deletion whose target range covers a gap", () => {
    const wrapper = mountEditor();
    const element = paragraph(wrapper, 0);
    const chip = element.querySelector('[data-gap-id="gap_001"]')!;
    const range = document.createRange();
    range.selectNode(chip);
    const selection = window.getSelection()!;
    selection.removeAllRanges();
    selection.addRange(range);

    const event = new InputEvent("beforeinput", {
      bubbles: true,
      cancelable: true,
      inputType: "deleteContentBackward",
    });
    element.dispatchEvent(event);

    expect(event.defaultPrevented).toBe(true);
    wrapper.unmount();
  });

  it("blocks backspace when the caret sits right after a gap", () => {
    const wrapper = mountEditor();
    const element = paragraph(wrapper, 0);
    const afterChip = element.querySelector('[data-gap-id="gap_001"]')!.nextSibling as Text;
    const range = document.createRange();
    range.setStart(afterChip, 0);
    range.collapse(true);
    const selection = window.getSelection()!;
    selection.removeAllRanges();
    selection.addRange(range);

    const event = new InputEvent("beforeinput", {
      bubbles: true,
      cancelable: true,
      inputType: "deleteContentBackward",
    });
    element.dispatchEvent(event);
    expect(event.defaultPrevented).toBe(true);

    range.setStart(afterChip, 3);
    range.collapse(true);
    selection.removeAllRanges();
    selection.addRange(range);
    const textDelete = new InputEvent("beforeinput", {
      bubbles: true,
      cancelable: true,
      inputType: "deleteContentBackward",
    });
    element.dispatchEvent(textDelete);
    expect(textDelete.defaultPrevented).toBe(false);
    wrapper.unmount();
  });

  it("explains that Backspace beside an image changes nothing, without mentioning gaps", async () => {
    const wrapper = mountEditor();
    const element = paragraph(wrapper, 1);
    const marker = element.querySelector('[data-asset-id="asset_001"]')!;
    const range = document.createRange();
    range.setStartAfter(marker);
    range.collapse(true);
    const selection = window.getSelection()!;
    selection.removeAllRanges();
    selection.addRange(range);

    const event = new InputEvent("beforeinput", {
      bubbles: true,
      cancelable: true,
      inputType: "deleteContentBackward",
    });
    element.dispatchEvent(event);
    await wrapper.vm.$nextTick();

    expect(event.defaultPrevented).toBe(true);
    expect(wrapper.get('[data-test="exam-workspace-body-status"]').text()).toBe(
      "Bilden kan inte tas bort i texten.",
    );
    wrapper.unmount();
  });

  it("explains why Backspace beside a gap changes nothing, until the next input", async () => {
    const wrapper = mountEditor();
    const element = paragraph(wrapper, 0);
    const afterChip = element.querySelector('[data-gap-id="gap_001"]')!.nextSibling as Text;
    const range = document.createRange();
    range.setStart(afterChip, 0);
    range.collapse(true);
    const selection = window.getSelection()!;
    selection.removeAllRanges();
    selection.addRange(range);

    element.dispatchEvent(
      new InputEvent("beforeinput", {
        bubbles: true,
        cancelable: true,
        inputType: "deleteContentBackward",
      }),
    );
    await wrapper.vm.$nextTick();

    const status = wrapper.get('[data-test="exam-workspace-body-status"]');
    expect(status.attributes("aria-live")).toBe("polite");
    expect(status.text()).toBe(
      "Luckan tas inte bort med Backsteg eller Delete. Öppna luckan för att ändra svaret.",
    );

    afterChip.data = " grader och fryser vid, ";
    element.dispatchEvent(new Event("input", { bubbles: true }));
    await wrapper.vm.$nextTick();
    expect(wrapper.find('[data-test="exam-workspace-body-status"]').exists()).toBe(false);
    wrapper.unmount();
  });

  it("inserts Enter as a newline in the text", () => {
    const wrapper = mountEditor();
    const element = paragraph(wrapper, 0);
    const range = document.createRange();
    range.setStart(element.firstChild!, 6);
    range.collapse(true);
    const selection = window.getSelection()!;
    selection.removeAllRanges();
    selection.addRange(range);

    const event = new InputEvent("beforeinput", {
      bubbles: true,
      cancelable: true,
      inputType: "insertParagraph",
    });
    element.dispatchEvent(event);

    expect(event.defaultPrevented).toBe(true);
    const [, , segments] = wrapper.emitted("updateParagraphSegments")![0]!;
    expect((segments as unknown[])[0]).toEqual({ kind: "text", marks: [], text: "Vatten\n kokar vid " });
    wrapper.unmount();
  });

  it("waits for an IME composition to end before reading the paragraph", () => {
    const wrapper = mountEditor();
    const element = paragraph(wrapper, 0);
    element.dispatchEvent(new CompositionEvent("compositionstart", { bubbles: true }));
    (element.firstChild as Text).data = "Vatten kokar vid å";
    element.dispatchEvent(new Event("input", { bubbles: true }));
    expect(wrapper.emitted("updateParagraphSegments")).toBeUndefined();

    element.dispatchEvent(new CompositionEvent("compositionend", { bubbles: true }));
    const [, , segments] = wrapper.emitted("updateParagraphSegments")![0]!;
    expect((segments as unknown[])[0]).toEqual({ kind: "text", marks: [], text: "Vatten kokar vid å" });
    wrapper.unmount();
  });

  it("refuses drops into a paragraph", () => {
    const wrapper = mountEditor();
    const element = paragraph(wrapper, 0);
    const dragOver = new Event("dragover", { bubbles: true, cancelable: true });
    const drop = new Event("drop", { bubbles: true, cancelable: true });
    element.dispatchEvent(dragOver);
    element.dispatchEvent(drop);
    expect(dragOver.defaultPrevented).toBe(true);
    expect(drop.defaultPrevented).toBe(true);
    expect(element.textContent).toBe("Vatten kokar vid  grader och fryser vid  grader.");
    wrapper.unmount();
  });

  it("pastes plain text at the caret and refuses a paste over a gap", () => {
    const wrapper = mountEditor();
    const element = paragraph(wrapper, 0);
    const selection = window.getSelection()!;
    const range = document.createRange();
    range.setStart(element.firstChild!, 6);
    range.collapse(true);
    selection.removeAllRanges();
    selection.addRange(range);

    const paste = new Event("paste", { bubbles: true, cancelable: true });
    Object.defineProperty(paste, "clipboardData", { value: { getData: () => " x\r\ny" } });
    element.dispatchEvent(paste);
    expect(paste.defaultPrevented).toBe(true);
    const [, , segments] = wrapper.emitted("updateParagraphSegments")![0]!;
    expect((segments as unknown[])[0]).toEqual({ kind: "text", marks: [], text: "Vatten x\ny kokar vid " });

    const chipRange = document.createRange();
    chipRange.selectNode(element.querySelector('[data-gap-id="gap_001"]')!);
    selection.removeAllRanges();
    selection.addRange(chipRange);
    const overGap = new Event("paste", { bubbles: true, cancelable: true });
    Object.defineProperty(overGap, "clipboardData", { value: { getData: () => "z" } });
    element.dispatchEvent(overGap);
    expect(wrapper.emitted("updateParagraphSegments")).toHaveLength(1);
    expect(element.querySelector('[data-gap-id="gap_001"]')).not.toBeNull();
    wrapper.unmount();
  });

  it("rebuilds the paragraphs when another item is shown", async () => {
    const wrapper = mountEditor();
    await wrapper.setProps({
      item: buildGapItem({
        item_id: "item_002",
        body: [{ heading_level: null, segments: [{ kind: "text", marks: [], text: "Annan fråga" }] }],
        gaps: [],
      }),
    });
    expect(paragraph(wrapper, 0).textContent).toBe("Annan fråga");
    expect(wrapper.find('[data-test="exam-workspace-body-paragraph-1"]').exists()).toBe(false);
    wrapper.unmount();
  });
});
