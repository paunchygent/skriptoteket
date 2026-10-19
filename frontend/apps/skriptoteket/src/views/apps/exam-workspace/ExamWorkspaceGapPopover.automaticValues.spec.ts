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
    expect(chips[0]!.textContent).toContain("hundraa");
    expect(chips[0]!.textContent).not.toContain("automatisk");
    expect(chips[1]!.textContent).toContain("hundar");
    expect(chips[1]!.textContent).not.toContain("automatisk");
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

  it("shows no automatic section when the gap has none", () => {
    const wrapper = mountPopover(buildGap("gap_001", ["100"]));

    expect(document.querySelector('[data-test="exam-workspace-gap-automatic-values"]')).toBeNull();
    wrapper.unmount();
  });
});
