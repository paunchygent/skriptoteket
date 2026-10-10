/**
 * Exam workspace question-text editor.
 *
 * Expected behavior:
 *   Each paragraph is one editable text with gap chips and image markers
 *   inline. Text edits emit the paragraph's normalized segments without
 *   rebuilding the DOM the teacher is typing in. Removing a gap or image is
 *   refused: the paragraph is restored and a Swedish status line explains
 *   why. Activating a gap chip opens an input that commits accepted answers
 *   on `change`, and chip labels follow the gap's accepted answers in place.
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
    expect(filledChip.text()).toBe("100");
    expect(filledChip.attributes("data-gap-id")).toBe("gap_001");
    expect(filledChip.attributes("contenteditable")).toBe("false");
    expect(filledChip.attributes("role")).toBe("button");

    const emptyChip = wrapper.get('[data-test="exam-workspace-body-gap-0-3"]');
    expect(emptyChip.text()).toBe("Lucka 2");
    expect(emptyChip.classes()).toContain("border-warning");

    expect(wrapper.get('[data-asset-id="asset_001"]').text()).toBe("Bild");
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

  it("opens the popover from the keyboard and not while disabled", async () => {
    const wrapper = mountEditor();
    await wrapper.get('[data-gap-id="gap_002"]').trigger("keydown", { key: "Enter" });
    expect(wrapper.find('[data-test="exam-workspace-gap-values-gap_002"]').exists()).toBe(true);

    await wrapper.setProps({ disabled: true });
    await wrapper.get('[data-test="exam-workspace-gap-values-gap_002"]').trigger("keydown", {
      key: "Escape",
    });
    await wrapper.get('[data-gap-id="gap_001"]').trigger("click");
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
    expect(chip.textContent).toBe("0 / noll");
    expect(chip.classList.contains("border-warning")).toBe(false);
    wrapper.unmount();
  });

  it("leaves unchanged chips untouched when only the text changes", async () => {
    const item = buildGapItem();
    const wrapper = mountEditor(item);
    const chipText = wrapper.get('[data-gap-id="gap_001"]').element.firstChild;
    const element = paragraph(wrapper, 0);
    (element.firstChild as Text).data = "Vatten kokar vid ungefär ";
    element.dispatchEvent(new Event("input", { bubbles: true }));
    const [, , segments] = wrapper.emitted("updateParagraphSegments")![0]!;

    await wrapper.setProps({
      item: { ...item, body: [{ segments: segments as never }, item.body[1]!] },
    });
    expect(wrapper.get('[data-gap-id="gap_001"]').element.firstChild).toBe(chipText);
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
