/**
 * Exam workspace question-text editor, gap popover and chips.
 *
 * Expected behavior:
 *   Activating a gap chip opens an input that commits accepted answers once
 *   on Enter, `change` or leaving the popover, and discards them on Escape.
 *   Chip labels follow the gap's accepted answers in place and live in a
 *   `data-label` attribute, so they are never part of the text. While
 *   disabled, nothing is editable and an open popover closes uncommitted. A
 *   partially keyed gap item shows the key hint; a free-text item shows its
 *   note.
 */

import { describe, expect, it } from "vitest";

import { PARTIAL_GAP_KEY_GUIDANCE } from "./examWorkspaceAnswerKeyRules";
import { buildGap } from "./examWorkspaceKeyedItems.specSupport";
import { buildGapItem, mountEditor, paragraph } from "./ExamWorkspaceBodyEditor.specSupport";

describe("ExamWorkspaceBodyEditor gap popover and chips", () => {
  it("opens the gap popover from the chip and commits accepted answers on change", async () => {
    const wrapper = mountEditor();
    expect(wrapper.find('[data-test="exam-workspace-gap-values-gap_001"]').exists()).toBe(false);

    await wrapper.get('[data-gap-id="gap_001"]').trigger("click");

    expect(wrapper.find('[data-test="exam-workspace-gap-popover"]').exists()).toBe(true);
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
        gaps: [item.gaps[0]!, buildGap("gap_002", ["0", "noll"])],
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
      item: { ...item, body: [{ heading_level: null, segments: segments as never }, item.body[1]!] },
    });
    expect(wrapper.get('[data-gap-id="gap_001"]').element).toBe(chip);
    expect([...records, ...observer.takeRecords()]).toEqual([]);
    observer.disconnect();
    wrapper.unmount();
  });

  it("shows the partial-key hint and the free-text note", async () => {
    const wrapper = mountEditor();
    expect(wrapper.get('[data-test="exam-workspace-gap-key-hint"]').text()).toBe(
      PARTIAL_GAP_KEY_GUIDANCE,
    );

    await wrapper.setProps({
      item: buildGapItem({
        answer_key: { correct_choice_ids: [], match_pairs: [], origin: "not_applicable" },
        body: [{ heading_level: null, segments: [{ kind: "text", marks: [], text: "Beskriv." }] }],
        gaps: [],
        kind: "free_text",
        match_left: [],
        match_right: [],
      }),
    });
    expect(wrapper.find('[data-test="exam-workspace-gap-key-hint"]').exists()).toBe(false);
    expect(wrapper.text()).toContain("Fritextfråga – eleven svarar med egen text.");
    wrapper.unmount();
  });
});
