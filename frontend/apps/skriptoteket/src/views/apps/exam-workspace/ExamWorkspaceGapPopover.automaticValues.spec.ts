/**
 * Exam workspace gap popover: automatic answers.
 *
 * Expected behavior:
 *   Each answer the conversion wrote for the gap shows as a chip with a
 *   remove control, no per-chip status tag and no AI glyph. Removing one emits
 *   the item, gap and value and leaves the popover open with focus back in
 *   the answers input. A gap without automatic answers shows no section.
 */

import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import { nextTick } from "vue";

import type { NativeExamGap } from "../../../api/examWorkspace";
import ExamWorkspaceGapPopover from "./ExamWorkspaceGapPopover.vue";
import { documentControl, popoverExists, popoverRoot } from "./ExamWorkspaceBodyEditor.specSupport";
import { buildGap } from "./examWorkspaceKeyedItems.specSupport";

function gapWithAutomaticValues(): NativeExamGap {
  return buildGap("gap_001", ["hundra"], {
    automatic_values: ["hundraa", "hundar"],
  });
}

function mountPopover(gap: NativeExamGap | null) {
  return mount(ExamWorkspaceGapPopover, {
    attachTo: document.body,
    props: {
      anchor: document.body,
      gap,
      gapId: "gap_001",
      gapNumber: 1,
      itemId: "item_001",
    },
  });
}

function automaticChips(): HTMLElement[] {
  return Array.from(
    document.querySelectorAll<HTMLElement>('[data-test="exam-workspace-gap-automatic-values"] li'),
  );
}

describe("ExamWorkspaceGapPopover automatic answers", () => {
  it("shows a chip per automatic answer with no per-chip automatisk tag and without an AI glyph", () => {
    const wrapper = mountPopover(gapWithAutomaticValues());
    const chips = automaticChips();

    expect(chips).toHaveLength(2);
    const texts = chips.map((chip) => chip.textContent ?? "");
    expect(texts).toEqual([
      expect.stringContaining("hundraa"),
      expect.stringContaining("hundar"),
    ]);
    for (const text of texts) {
      expect(text).not.toContain("automatisk");
    }
    expect(popoverRoot().innerHTML).not.toContain("lucide-sparkles");
    wrapper.unmount();
  });

  it("emits the removed value and keeps the popover open with focus in the input", async () => {
    const wrapper = mountPopover(gapWithAutomaticValues());

    await documentControl('[data-test="exam-workspace-gap-automatic-remove-hundraa"]').trigger("click");
    await wrapper.vm.$nextTick();

    expect(wrapper.emitted("removeAutomaticValue")).toEqual([
      ["item_001", "gap_001", "hundraa"],
    ]);
    expect(popoverExists()).toBe(true);
    expect(document.activeElement).toBe(
      documentControl<HTMLInputElement>('[data-test="exam-workspace-gap-values-gap_001-input"]')
        .element,
    );
    wrapper.unmount();
  });

  it("moves focus to the answer input synchronously before emitting the removal", async () => {
    const wrapper = mountPopover(gapWithAutomaticValues());

    const remove = documentControl('[data-test="exam-workspace-gap-automatic-remove-hundraa"]').element;
    if (!(remove instanceof HTMLButtonElement)) {
      throw new Error("the automatic remove control is not a button");
    }
    remove.focus();
    remove.click();

    const input = documentControl('[data-test="exam-workspace-gap-values-gap_001-input"]').element;
    if (!(input instanceof HTMLInputElement)) {
      throw new Error("the answer input is not an input");
    }
    expect(document.activeElement).toBe(input);

    await wrapper.setProps({
      gap: buildGap("gap_001", ["hundra"], { automatic_values: ["hundar"] }),
    });
    await nextTick();

    expect(wrapper.emitted("removeAutomaticValue")).toEqual([
      ["item_001", "gap_001", "hundraa"],
    ]);
    expect(popoverExists()).toBe(true);
    expect(wrapper.emitted("close")).toBeUndefined();
    const inputAfter = documentControl('[data-test="exam-workspace-gap-values-gap_001-input"]').element;
    if (!(inputAfter instanceof HTMLInputElement)) {
      throw new Error("the answer input is not an input");
    }
    expect(document.activeElement).toBe(inputAfter);
    wrapper.unmount();
  });

  it("shows no automatic section when the gap has none", () => {
    const wrapper = mountPopover(buildGap("gap_001", ["100"]));

    expect(document.querySelector('[data-test="exam-workspace-gap-automatic-values"]')).toBeNull();
    wrapper.unmount();
  });
});
