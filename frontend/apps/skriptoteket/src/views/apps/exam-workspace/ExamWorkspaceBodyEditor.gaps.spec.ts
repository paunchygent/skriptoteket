/**
 * Exam workspace question-text editor, gap popover and chips.
 *
 * Expected behavior:
 *   Activating a gap chip opens one row per accepted answer that commits
 *   while typing (leaving the popover commits any remainder once), and
 *   keeps typed text on Escape. Enter in a row adds a row below it and never
 *   closes the popover. The popover opens from a click on a gap and from
 *   Enter on a selected gap, anchored below that gap. Chip labels follow
 *   the gap's accepted answers in place and live in a `data-label`
 *   attribute, so they are never part of the text. While
 *   disabled, nothing is editable and an open popover closes uncommitted. A
 *   partially keyed gap item shows the key hint; a free-text item shows its
 *   note.
 */

import { NodeSelection } from "@tiptap/pm/state";
import { describe, expect, it, vi } from "vitest";
import { nextTick } from "vue";

import { PARTIAL_GAP_KEY_GUIDANCE } from "./examWorkspaceAnswerKeyRules";
import { buildGap } from "./examWorkspaceKeyedItems.specSupport";
import {
  atomPos,
  buildGapItem,
  clickGap,
  gapElement,
  mountEditor,
  popoverExists,
  popoverInput,
  popoverRoot,
  press,
  surface,
  tiptap,
  type MountedBodyEditor,
} from "./ExamWorkspaceBodyEditor.specSupport";

/** Click a gap as a user does, then let the popover render. */
async function openGap(wrapper: MountedBodyEditor, gapId: string): Promise<void> {
  clickGap(wrapper, gapId);
  await nextTick();
  await nextTick();
}

function valuesInput(gapId: string) {
  return popoverInput(gapId);
}

function valuesInputs(gapId: string): HTMLInputElement[] {
  return Array.from(
    document.querySelectorAll<HTMLInputElement>(
      `[data-test="exam-workspace-gap-values-${gapId}-input"]`,
    ),
  );
}

describe("ExamWorkspaceBodyEditor gap popover and chips", () => {
  it("opens the gap popover from the chip and commits accepted answers on change", async () => {
    const wrapper = await mountEditor();
    expect(popoverExists()).toBe(false);

    await openGap(wrapper, "gap_001");

    expect(popoverExists()).toBe(true);
    const input = popoverInput("gap_001");
    expect(input.element.value).toBe("100");
    expect(document.activeElement).toBe(input.element);
    expect(gapElement(wrapper, "gap_001").getAttribute("aria-expanded")).toBe("true");

    await input.setValue("hundra");
    expect(wrapper.emitted("updateGapValues")).toEqual([["item_001", "gap_001", ["hundra"]]]);

    await input.trigger("keydown", { key: "Escape" });
    expect(popoverExists()).toBe(false);
    expect(document.activeElement).toBe(surface(wrapper));
    expect(gapElement(wrapper, "gap_001").getAttribute("aria-expanded")).toBe("false");
    wrapper.unmount();
  });

  it("teleports the popover to the body and anchors it under the gap", async () => {
    const rects = new Map<Element, Partial<DOMRect>>();
    const spy = vi
      .spyOn(HTMLElement.prototype, "getBoundingClientRect")
      .mockImplementation(function (this: HTMLElement): DOMRect {
        const stored = rects.get(this);
        return {
          left: 0,
          right: 0,
          top: 0,
          bottom: 0,
          width: 0,
          height: 0,
          x: 0,
          y: 0,
          ...stored,
          toJSON: () => ({}),
        };
      });
    try {
      const wrapper = await mountEditor();
      rects.set(gapElement(wrapper, "gap_001"), { left: 180, top: 240, bottom: 260 });
      rects.set(gapElement(wrapper, "gap_002"), { left: 650, top: 280, bottom: 300 });

      await openGap(wrapper, "gap_001");
      // Teleported out of the clipping editor box, held by fixed positioning.
      expect(popoverRoot().parentElement).toBe(document.body);
      expect(popoverRoot().closest(".xw-rich")).toBeNull();
      expect(popoverRoot().classList).toContain("fixed");
      expect(popoverRoot().classList).toContain("z-30");
      // jsdom has no layout, so the panel measures 0 px and sits right under the chip.
      expect(popoverRoot().getAttribute("style")).toContain("top: 264px; left: 180px;");

      await openGap(wrapper, "gap_002");
      expect(popoverRoot().getAttribute("style")).toContain("top: 304px; left: 650px;");
      expect(gapElement(wrapper, "gap_001").getAttribute("aria-expanded")).toBe("false");
      expect(gapElement(wrapper, "gap_002").getAttribute("aria-expanded")).toBe("true");
      wrapper.unmount();
    } finally {
      spy.mockRestore();
    }
  });

  it("adds a row on Enter without closing and keeps the typed commit", async () => {
    const wrapper = await mountEditor();
    await openGap(wrapper, "gap_002");
    const input = valuesInput("gap_002");

    input.element.value = "noll";
    await input.trigger("input");
    // Typing already committed; Enter only adds the row.
    expect(wrapper.emitted("updateGapValues")).toEqual([["item_001", "gap_002", ["noll"]]]);
    await input.trigger("keydown", { key: "Enter" });
    await nextTick();
    expect(valuesInputs("gap_002")).toHaveLength(2);
    expect(popoverExists()).toBe(true);

    await input.trigger("change");
    await input.trigger("change");
    expect(wrapper.emitted("updateGapValues")).toEqual([["item_001", "gap_002", ["noll"]]]);
    expect(popoverExists()).toBe(true);
    wrapper.unmount();
  });

  it("ignores Enter while an IME composition is active", async () => {
    const wrapper = await mountEditor();
    await openGap(wrapper, "gap_001");
    const input = valuesInput("gap_001");
    input.element.value = "hund";

    input.element.dispatchEvent(
      new KeyboardEvent("keydown", { key: "Enter", bubbles: true, isComposing: true }),
    );
    input.element.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true, keyCode: 229 }));
    await nextTick();
    expect(wrapper.emitted("updateGapValues")).toBeUndefined();
    expect(popoverExists()).toBe(true);
    expect(valuesInputs("gap_001")).toHaveLength(1);

    input.element.value = "hundra";
    input.element.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true }));
    await nextTick();
    // A real Enter adds a row instead of committing and keeps the popover open.
    expect(valuesInputs("gap_001")).toHaveLength(2);
    expect(wrapper.emitted("updateGapValues")).toBeUndefined();
    expect(popoverExists()).toBe(true);
    wrapper.unmount();
  });

  it("gives the popover room for long answers", async () => {
    const wrapper = await mountEditor();
    await openGap(wrapper, "gap_001");
    expect(popoverRoot().classList).toContain("w-[min(28rem,calc(100vw-16px))]");
    expect(popoverInput("gap_001").classes()).toContain("flex-1");
    wrapper.unmount();
  });

  it("commits when focus leaves the popover and keeps typed text on Escape", async () => {
    const wrapper = await mountEditor();
    await openGap(wrapper, "gap_001");
    const input = valuesInput("gap_001");
    input.element.value = "hundra";
    await input.trigger("input");
    input.element.dispatchEvent(new FocusEvent("focusout", { bubbles: true, relatedTarget: null }));
    await nextTick();
    expect(wrapper.emitted("updateGapValues")).toEqual([["item_001", "gap_001", ["hundra"]]]);
    expect(popoverExists()).toBe(false);

    await openGap(wrapper, "gap_001");
    const reopened = valuesInput("gap_001");
    reopened.element.value = "kasta";
    await reopened.trigger("input");
    reopened.element.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
    reopened.element.dispatchEvent(new Event("change", { bubbles: true }));
    reopened.element.dispatchEvent(new FocusEvent("focusout", { bubbles: true }));
    await nextTick();
    // Typing already committed before Escape; the late events add nothing.
    expect(wrapper.emitted("updateGapValues")).toEqual([
      ["item_001", "gap_001", ["hundra"]],
      ["item_001", "gap_001", ["kasta"]],
    ]);
    expect(popoverExists()).toBe(false);
    wrapper.unmount();
  });

  it("closes an open popover without further commits when the editor becomes disabled", async () => {
    const wrapper = await mountEditor();
    await openGap(wrapper, "gap_001");
    const input = valuesInput("gap_001");
    input.element.value = "ändrat";
    await input.trigger("input");

    await wrapper.setProps({ disabled: true });
    input.element.dispatchEvent(new Event("change", { bubbles: true }));
    input.element.dispatchEvent(new FocusEvent("focusout", { bubbles: true }));

    expect(popoverExists()).toBe(false);
    // The typing committed before the disable; the late events add nothing.
    expect(wrapper.emitted("updateGapValues")).toEqual([["item_001", "gap_001", ["ändrat"]]]);
    expect(surface(wrapper).getAttribute("contenteditable")).toBe("false");
    wrapper.unmount();
  });

  it("opens the popover from Enter on a selected gap and not while disabled", async () => {
    const wrapper = await mountEditor();
    const editor = tiptap(wrapper);
    editor.commands.setNodeSelection(atomPos(editor, "examGap", "gap_002"));
    expect(editor.state.selection).toBeInstanceOf(NodeSelection);

    const event = press(surface(wrapper), "Enter");
    await nextTick();

    expect(event.defaultPrevented).toBe(true);
    expect(popoverExists()).toBe(true);
    // Enter opened the popover; it did not split the paragraph.
    expect(surface(wrapper).querySelectorAll("p")).toHaveLength(2);

    await wrapper.setProps({ disabled: true });
    expect(popoverExists()).toBe(false);
    await openGap(wrapper, "gap_001");
    editor.commands.setNodeSelection(atomPos(editor, "examGap", "gap_001"));
    press(surface(wrapper), "Enter");
    await nextTick();
    expect(popoverExists()).toBe(false);
    wrapper.unmount();
  });

  it("updates chip labels in place when accepted answers change", async () => {
    const item = buildGapItem();
    const wrapper = await mountEditor(item);
    const chip = gapElement(wrapper, "gap_002");

    await wrapper.setProps({
      item: {
        ...item,
        gaps: [item.gaps[0]!, buildGap("gap_002", ["0", "noll"])],
      },
    });

    expect(gapElement(wrapper, "gap_002")).toBe(chip);
    expect(chip.getAttribute("data-label")).toBe("0 / noll");
    expect(chip.getAttribute("aria-label")).toBe("Lucka 2, godkända svar: 0 / noll");
    expect(chip.hasAttribute("data-empty")).toBe(false);
    wrapper.unmount();
  });

  it("shows the partial-key hint and the free-text note", async () => {
    const wrapper = await mountEditor();
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
