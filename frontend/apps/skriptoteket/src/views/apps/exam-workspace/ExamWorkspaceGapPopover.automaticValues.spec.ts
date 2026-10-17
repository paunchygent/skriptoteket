/**
 * Exam workspace gap popover: automatic answers.
 *
 * Expected behavior:
 *   Each answer the conversion wrote for the gap shows as a chip marked
 *   "automatisk" with a remove control and no AI glyph. Removing one emits
 *   the item, gap and value and leaves the popover open with focus back in
 *   the answers input. A gap without automatic answers shows no section.
 */

import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import type { NativeExamGap } from "../../../api/examWorkspace";
import ExamWorkspaceGapPopover from "./ExamWorkspaceGapPopover.vue";
import { buildGap } from "./examWorkspaceKeyedItems.specSupport";

function gapWithAutomaticValues(): NativeExamGap {
  return buildGap("gap_001", ["hundra"], {
    automatic_values: ["hundraa", "hundar"],
  });
}

function mountPopover(gap: NativeExamGap | null, gapCount = 2) {
  return mount(ExamWorkspaceGapPopover, {
    attachTo: document.body,
    props: {
      gap,
      gapCount,
      gapId: "gap_001",
      gapNumber: 1,
      itemId: "item_001",
      left: 0,
      top: 0,
    },
  });
}

describe("ExamWorkspaceGapPopover automatic answers", () => {
  it("shows a chip per automatic answer, marked automatisk and without an AI glyph", () => {
    const wrapper = mountPopover(gapWithAutomaticValues());
    const chips = wrapper.findAll('[data-test="exam-workspace-gap-automatic-values"] li');

    expect(chips).toHaveLength(2);
    expect(chips[0]!.text()).toContain("hundraa");
    expect(chips[0]!.text()).toContain("automatisk");
    expect(chips[1]!.text()).toContain("hundar");
    expect(wrapper.html()).not.toContain("lucide-sparkles");
    wrapper.unmount();
  });

  it("emits the removed value and keeps the popover open with focus in the input", async () => {
    const wrapper = mountPopover(gapWithAutomaticValues());

    await wrapper.get('[data-test="exam-workspace-gap-automatic-remove-hundraa"]').trigger("click");
    await wrapper.vm.$nextTick();

    expect(wrapper.emitted("removeAutomaticValue")).toEqual([
      ["item_001", "gap_001", "hundraa"],
    ]);
    expect(wrapper.find('[data-test="exam-workspace-gap-popover"]').exists()).toBe(true);
    expect(document.activeElement).toBe(
      wrapper.get('[data-test="exam-workspace-gap-values-gap_001"]').element,
    );
    wrapper.unmount();
  });

  it("shows no automatic section when the gap has none", () => {
    const wrapper = mountPopover(buildGap("gap_001", ["100"]));

    expect(wrapper.find('[data-test="exam-workspace-gap-automatic-values"]').exists()).toBe(false);
    wrapper.unmount();
  });
});
