/**
 * Exam workspace body editor: export-blocker jump to a gap.
 *
 * Expected behavior:
 *   A synthetic click on a gap chip never opens its popover: chips open
 *   only through ProseMirror's click handling, so the export-blocker jump
 *   requests the popover through a bubbling open-gap event on the chip and
 *   the editor opens that gap's popover with focus on its first option input.
 */

import { describe, expect, it } from "vitest";
import { nextTick } from "vue";

import type { NativeExamChoice, NativeExamItem } from "../../../api/examWorkspace";
import {
  buildGapItem,
  gapElement,
  mountEditor,
  popoverExists,
  popoverRoot,
} from "./ExamWorkspaceBodyEditor.specSupport";
import { buildGap } from "./examWorkspaceKeyedItems.specSupport";
import { plainBody } from "./examWorkspaceRichText";
import { EXAM_WORKSPACE_OPEN_GAP_EVENT, openBlockerField, requestOpenGap } from "./examWorkspaceGapOpenRequest";

function dropdownItem(): NativeExamItem {
  const options = (text: string, choiceId: string): NativeExamChoice[] => [
    { body: plainBody(text), choice_id: choiceId },
  ];
  return buildGapItem({
    kind: "inline_choice",
    gaps: [
      buildGap("gap_001", [], { correct_option_id: "choice_001", options: options("enda", "choice_001") }),
      buildGap("gap_002", [], { correct_option_id: "choice_002", options: options("annat", "choice_002") }),
    ],
  });
}

/** The same field resolution `gotoBlocker` runs: the blocker's focus selector against the frame. */
async function resolveBlockerField(frame: Element, focus: string): Promise<HTMLElement | null> {
  let field = frame.querySelector<HTMLElement>(focus);
  for (let tick = 0; !field && tick < 5; tick += 1) {
    await nextTick();
    field = frame.querySelector<HTMLElement>(focus);
  }
  return field;
}

function optionInput(choiceId: string): HTMLInputElement {
  const input = document.querySelector<HTMLInputElement>(
    `[data-test="exam-workspace-gap-option-text-${choiceId}"]`,
  );
  if (!(input instanceof HTMLInputElement)) {
    throw new Error(`no option input ${choiceId}`);
  }
  return input;
}

describe("ExamWorkspaceBodyEditor gap jump", () => {
  it("does not open the popover from a synthetic click on the chip", async () => {
    const wrapper = await mountEditor(buildGapItem());
    gapElement(wrapper, "gap_001").click();
    await nextTick();
    await nextTick();
    expect(popoverExists()).toBe(false);
    wrapper.unmount();
  });

  it("opens that gap's popover with focus on its first option input", async () => {
    const wrapper = await mountEditor(dropdownItem());
    const chip = gapElement(wrapper, "gap_001");
    requestOpenGap(chip);
    await nextTick();
    await nextTick();

    expect(chip.getAttribute("aria-expanded")).toBe("true");
    expect(popoverRoot().getAttribute("aria-label")).toBe("Alternativ för lucka 1");
    expect(document.activeElement).toBe(optionInput("choice_001"));
    wrapper.unmount();
  });

  it("opens the blocker field's popover through the save-flow jump path", async () => {
    const wrapper = await mountEditor(dropdownItem());
    const field = await resolveBlockerField(wrapper.element, '[data-gap-id="gap_001"]');
    if (field === null) {
      throw new Error("no blocker field");
    }
    openBlockerField(field);
    await nextTick();
    await nextTick();

    expect(field.getAttribute("aria-expanded")).toBe("true");
    expect(popoverExists()).toBe(true);
    expect(document.activeElement).toBe(optionInput("choice_001"));
    wrapper.unmount();
  });

  it("focuses a non-gap blocker field without opening a popover", async () => {
    const wrapper = await mountEditor(dropdownItem());
    const plain = document.createElement("input");
    wrapper.element.appendChild(plain);
    openBlockerField(plain);
    await nextTick();

    expect(document.activeElement).toBe(plain);
    expect(popoverExists()).toBe(false);
    wrapper.unmount();
  });

  it("opens only the requested gap when the item holds two gaps", async () => {
    const wrapper = await mountEditor(dropdownItem());
    requestOpenGap(gapElement(wrapper, "gap_002"));
    await nextTick();
    await nextTick();

    expect(gapElement(wrapper, "gap_002").getAttribute("aria-expanded")).toBe("true");
    expect(gapElement(wrapper, "gap_001").getAttribute("aria-expanded")).not.toBe("true");
    expect(popoverRoot().getAttribute("aria-label")).toBe("Alternativ för lucka 2");
    expect(document.activeElement).toBe(optionInput("choice_002"));
    wrapper.unmount();
  });

  it("opens nothing when the editor is disabled", async () => {
    const wrapper = await mountEditor(dropdownItem(), { disabled: true });
    requestOpenGap(gapElement(wrapper, "gap_001"));
    await nextTick();
    await nextTick();
    expect(popoverExists()).toBe(false);
    wrapper.unmount();
  });

  it("opens nothing for an event from an element without a gap id", async () => {
    const wrapper = await mountEditor(dropdownItem());
    wrapper.element.dispatchEvent(new CustomEvent(EXAM_WORKSPACE_OPEN_GAP_EVENT, { bubbles: true }));
    await nextTick();
    await nextTick();
    expect(popoverExists()).toBe(false);
    wrapper.unmount();
  });
});
