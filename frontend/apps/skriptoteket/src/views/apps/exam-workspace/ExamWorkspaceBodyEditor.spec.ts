/**
 * Exam workspace question-text editor.
 *
 * Expected behavior:
 *   Each paragraph is one editable text with gap chips and image markers
 *   inline. Text edits emit the paragraph's normalized segments without
 *   rebuilding the DOM the teacher is typing in. Removing a gap or image is
 *   refused: the paragraph is restored and a Swedish status line explains
 *   why. Activating a gap chip opens an input that commits accepted answers
 *   once on Enter, `change` or leaving the popover, and discards them on
 *   Escape. Chip labels follow the gap's accepted answers in place and live
 *   in a `data-label` attribute, so they are never part of the text. While
 *   disabled, nothing is editable and an open popover closes uncommitted.
 */

import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import type { NativeExamItem } from "../../../api/examWorkspace";
import { PARTIAL_GAP_KEY_GUIDANCE } from "./examWorkspaceAnswerKeyRules";
import ExamWorkspaceBodyEditor from "./ExamWorkspaceBodyEditor.vue";

function buildGapItem(overrides: Partial<NativeExamItem> = {}): NativeExamItem {
  return {
    answer_key: { correct_choice_ids: [], origin: "teacher_authored" },
    body: [
      {
        segments: [
          { kind: "text", text: "Vatten kokar vid " },
          { gap_id: "gap_001", kind: "gap" },
          { kind: "text", text: " grader och fryser vid " },
          { gap_id: "gap_002", kind: "gap" },
          { kind: "text", text: " grader." },
        ],
      },
      { segments: [{ kind: "text", text: "Se " }, { asset_id: "asset_001", kind: "asset" }] },
    ],
    choices: [],
    gaps: [
      { accepted_values: ["100"], gap_id: "gap_001", hint: "Celsius" },
      { accepted_values: [], gap_id: "gap_002", hint: null },
    ],
    item_id: "item_001",
    kind: "gap_fill",
    points: 1,
    review: {
      confidence: 0.95,
      parse_origin: "deterministic",
      reasons: [],
      state: "review_complete",
    },
    sequence: 1,
    source_anchor: null,
    title: null,
    ...overrides,
  };
}

function mountEditor(item: NativeExamItem = buildGapItem()) {
  return mount(ExamWorkspaceBodyEditor, { props: { item }, attachTo: document.body });
}

function paragraph(wrapper: ReturnType<typeof mountEditor>, index: number): HTMLElement {
  return wrapper.get(`[data-test="exam-workspace-body-paragraph-${index}"]`).element as HTMLElement;
}

describe("ExamWorkspaceBodyEditor", () => {
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
      { kind: "text", text: "Vatten\nkokar vid " },
      { gap_id: "gap_001", kind: "gap" },
      { kind: "text", text: " grader och fryser vid " },
      { gap_id: "gap_002", kind: "gap" },
      { kind: "text", text: " grader." },
    ]);

    await wrapper.setProps({
      item: { ...item, body: [{ segments: segments as never }, item.body[1]!] },
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
    const item = buildGapItem({ body: [{ segments: [{ kind: "text", text: "Hej" }] }] });
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
    expect((segments as unknown[])[0]).toEqual({ kind: "text", text: "Vatten\n kokar vid " });
    wrapper.unmount();
  });

  it("opens the gap popover from the chip and commits accepted answers on change", async () => {
    const wrapper = mountEditor();
    expect(wrapper.find('[data-test="exam-workspace-gap-values-gap_001"]').exists()).toBe(false);

    await wrapper.get('[data-gap-id="gap_001"]').trigger("click");

    const popover = wrapper.get('[data-test="exam-workspace-gap-popover"]');
    expect(popover.text()).toContain("Ledtråd: Celsius");
    const input = wrapper.get('[data-test="exam-workspace-gap-values-gap_001"]');
    expect((input.element as HTMLInputElement).value).toBe("100");
    expect(document.activeElement).toBe(input.element);

    await input.setValue(" 100 , hundra,, ");
    expect(wrapper.emitted("updateGapValues")).toEqual([["item_001", "gap_001", ["100", "hundra"]]]);

    await input.trigger("keydown", { key: "Escape" });
    expect(wrapper.find('[data-test="exam-workspace-gap-popover"]').exists()).toBe(false);
    expect(document.activeElement).toBe(wrapper.get('[data-gap-id="gap_001"]').element);
    wrapper.unmount();
  });

  it("commits once on Enter even when the browser fires change as focus returns", async () => {
    const wrapper = mountEditor();
    await wrapper.get('[data-gap-id="gap_002"]').trigger("click");
    const input = wrapper.get('[data-test="exam-workspace-gap-values-gap_002"]')
      .element as HTMLInputElement;

    input.value = "0, noll";
    // Chrome order: Enter closes and focuses the chip, which fires `change`
    // synchronously on the still-attached input before Vue re-renders.
    input.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true }));
    input.dispatchEvent(new Event("change", { bubbles: true }));
    input.dispatchEvent(new FocusEvent("focusout", { bubbles: true }));
    await wrapper.vm.$nextTick();

    expect(wrapper.emitted("updateGapValues")).toEqual([["item_001", "gap_002", ["0", "noll"]]]);
    expect(wrapper.find('[data-test="exam-workspace-gap-popover"]').exists()).toBe(false);
    expect(document.activeElement).toBe(wrapper.get('[data-gap-id="gap_002"]').element);
    wrapper.unmount();
  });

  it("ignores Enter while an IME composition is active", async () => {
    const wrapper = mountEditor();
    await wrapper.get('[data-gap-id="gap_001"]').trigger("click");
    const input = wrapper.get('[data-test="exam-workspace-gap-values-gap_001"]')
      .element as HTMLInputElement;
    input.value = "hund";

    input.dispatchEvent(
      new KeyboardEvent("keydown", { key: "Enter", bubbles: true, isComposing: true }),
    );
    input.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true, keyCode: 229 }));
    await wrapper.vm.$nextTick();
    expect(wrapper.emitted("updateGapValues")).toBeUndefined();
    expect(wrapper.find('[data-test="exam-workspace-gap-popover"]').exists()).toBe(true);

    input.value = "hundra";
    input.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true }));
    await wrapper.vm.$nextTick();
    expect(wrapper.emitted("updateGapValues")).toEqual([["item_001", "gap_001", ["hundra"]]]);
    wrapper.unmount();
  });

  it("gives the popover room for long answers", async () => {
    const wrapper = mountEditor();
    await wrapper.get('[data-gap-id="gap_001"]').trigger("click");
    const popover = wrapper.get('[data-test="exam-workspace-gap-popover"]');
    expect(popover.classes()).toContain("w-[min(28rem,100%)]");
    expect(wrapper.get('[data-test="exam-workspace-gap-values-gap_001"]').classes()).toContain(
      "w-full",
    );
    wrapper.unmount();
  });

  it("commits when focus leaves the popover and discards on Escape", async () => {
    const wrapper = mountEditor();
    await wrapper.get('[data-gap-id="gap_001"]').trigger("click");
    const input = wrapper.get('[data-test="exam-workspace-gap-values-gap_001"]')
      .element as HTMLInputElement;
    input.value = "hundra";
    input.dispatchEvent(new FocusEvent("focusout", { bubbles: true, relatedTarget: null }));
    await wrapper.vm.$nextTick();
    expect(wrapper.emitted("updateGapValues")).toEqual([["item_001", "gap_001", ["hundra"]]]);
    expect(wrapper.find('[data-test="exam-workspace-gap-popover"]').exists()).toBe(false);

    await wrapper.get('[data-gap-id="gap_001"]').trigger("click");
    const reopened = wrapper.get('[data-test="exam-workspace-gap-values-gap_001"]')
      .element as HTMLInputElement;
    reopened.value = "kasta";
    reopened.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
    reopened.dispatchEvent(new Event("change", { bubbles: true }));
    reopened.dispatchEvent(new FocusEvent("focusout", { bubbles: true }));
    await wrapper.vm.$nextTick();
    expect(wrapper.emitted("updateGapValues")).toHaveLength(1);
    expect(wrapper.find('[data-test="exam-workspace-gap-popover"]').exists()).toBe(false);
    wrapper.unmount();
  });

  it("closes an open popover without committing when the editor becomes disabled", async () => {
    const wrapper = mountEditor();
    await wrapper.get('[data-gap-id="gap_001"]').trigger("click");
    const input = wrapper.get('[data-test="exam-workspace-gap-values-gap_001"]')
      .element as HTMLInputElement;
    input.value = "ändrat";

    await wrapper.setProps({ disabled: true });
    input.dispatchEvent(new Event("change", { bubbles: true }));
    input.dispatchEvent(new FocusEvent("focusout", { bubbles: true }));

    expect(wrapper.find('[data-test="exam-workspace-gap-popover"]').exists()).toBe(false);
    expect(wrapper.emitted("updateGapValues")).toBeUndefined();
    expect(paragraph(wrapper, 0).getAttribute("contenteditable")).toBe("false");
    expect(paragraph(wrapper, 0).getAttribute("aria-disabled")).toBe("true");

    const beforeInput = new InputEvent("beforeinput", {
      bubbles: true,
      cancelable: true,
      inputType: "insertText",
      data: "x",
    });
    paragraph(wrapper, 0).dispatchEvent(beforeInput);
    expect(beforeInput.defaultPrevented).toBe(true);
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
    expect((segments as unknown[])[0]).toEqual({ kind: "text", text: "Vatten kokar vid å" });
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

  it("opens the popover from the keyboard and not while disabled", async () => {
    const wrapper = mountEditor();
    await wrapper.get('[data-gap-id="gap_002"]').trigger("keydown", { key: "Enter" });
    expect(wrapper.find('[data-test="exam-workspace-gap-values-gap_002"]').exists()).toBe(true);

    await wrapper.setProps({ disabled: true });
    expect(wrapper.find('[data-test="exam-workspace-gap-popover"]').exists()).toBe(false);
    await wrapper.get('[data-gap-id="gap_001"]').trigger("click");
    await wrapper.get('[data-gap-id="gap_001"]').trigger("keydown", { key: "Enter" });
    expect(wrapper.find('[data-test="exam-workspace-gap-popover"]').exists()).toBe(false);
    expect(paragraph(wrapper, 0).getAttribute("contenteditable")).toBe("false");
    wrapper.unmount();
  });

  it("updates chip labels in place when accepted answers change", async () => {
    const item = buildGapItem();
    const wrapper = mountEditor(item);
    const chip = wrapper.get('[data-gap-id="gap_002"]').element;

    await wrapper.setProps({
      item: {
        ...item,
        gaps: [item.gaps[0]!, { accepted_values: ["0", "noll"], gap_id: "gap_002", hint: null }],
      },
    });

    expect(wrapper.get('[data-gap-id="gap_002"]').element).toBe(chip);
    expect(chip.getAttribute("data-label")).toBe("0 / noll");
    expect(chip.getAttribute("aria-label")).toBe("Lucka 2, godkända svar: 0 / noll");
    expect(chip.classList.contains("border-warning")).toBe(false);
    wrapper.unmount();
  });

  it("leaves unchanged chips untouched when only the text changes", async () => {
    const item = buildGapItem();
    const wrapper = mountEditor(item);
    const chip = wrapper.get('[data-gap-id="gap_001"]').element;
    const records: MutationRecord[] = [];
    const observer = new MutationObserver((batch) => records.push(...batch));
    observer.observe(chip, { attributeFilter: ["data-label", "aria-label", "class"] });
    const element = paragraph(wrapper, 0);
    (element.firstChild as Text).data = "Vatten kokar vid ungefär ";
    element.dispatchEvent(new Event("input", { bubbles: true }));
    const [, , segments] = wrapper.emitted("updateParagraphSegments")![0]!;

    await wrapper.setProps({
      item: { ...item, body: [{ segments: segments as never }, item.body[1]!] },
    });
    expect(wrapper.get('[data-gap-id="gap_001"]').element).toBe(chip);
    expect([...records, ...observer.takeRecords()]).toEqual([]);
    observer.disconnect();
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
    expect((segments as unknown[])[0]).toEqual({ kind: "text", text: "Vatten x\ny kokar vid " });

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
        body: [{ segments: [{ kind: "text", text: "Annan fråga" }] }],
        gaps: [],
      }),
    });
    expect(paragraph(wrapper, 0).textContent).toBe("Annan fråga");
    expect(wrapper.find('[data-test="exam-workspace-body-paragraph-1"]').exists()).toBe(false);
    wrapper.unmount();
  });

  it("shows the partial-key hint and the free-text note", async () => {
    const wrapper = mountEditor();
    expect(wrapper.get('[data-test="exam-workspace-gap-key-hint"]').text()).toBe(
      PARTIAL_GAP_KEY_GUIDANCE,
    );

    await wrapper.setProps({
      item: buildGapItem({
        answer_key: { correct_choice_ids: [], origin: "not_applicable" },
        body: [{ segments: [{ kind: "text", text: "Beskriv." }] }],
        gaps: [],
        kind: "free_text",
      }),
    });
    expect(wrapper.find('[data-test="exam-workspace-gap-key-hint"]').exists()).toBe(false);
    expect(wrapper.text()).toContain("Fritextfråga – eleven svarar med egen text.");
    wrapper.unmount();
  });
});
