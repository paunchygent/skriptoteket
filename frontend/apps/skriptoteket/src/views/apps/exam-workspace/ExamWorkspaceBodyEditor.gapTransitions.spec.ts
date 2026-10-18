/**
 * Exam workspace question-text editor: gap changes that reshape the item.
 *
 * Expected behavior:
 *   The body editor forwards an automatic answer removal and "Visa som
 *   text" from the open popover, closes the popover on the latter and moves
 *   focus to the question text, and forwards neither while disabled. The
 *   item's only gap can be shown as text too: no gap is a valid state.
 */

import { describe, expect, it, vi } from "vitest";
import { nextTick } from "vue";

import ExamWorkspaceGapPopover from "./ExamWorkspaceGapPopover.vue";
import { buildGap } from "./examWorkspaceKeyedItems.specSupport";
import { buildGapItem, clickGap, mountEditor, surface } from "./ExamWorkspaceBodyEditor.specSupport";

function itemWithAutomaticValue() {
  return buildGapItem({
    body: [
      { heading_level: null, segments: [{ kind: "text", marks: [], text: "Inledning." }] },
      { heading_level: null, segments: [
          { kind: "text", marks: [], text: "Svar: " },
          { gap_id: "gap_001", kind: "gap" },
          { kind: "text", marks: [], text: " grader." },
        ],
      },
    ],
    gaps: [
      buildGap("gap_001", ["100"], { automatic_values: ["hundra"] }),
      buildGap("gap_002", ["0"]),
    ],
  });
}

describe("ExamWorkspaceBodyEditor gap transitions", () => {
  it("forwards an automatic answer removal from the open popover", async () => {
    const wrapper = await mountEditor(itemWithAutomaticValue());
    clickGap(wrapper, "gap_001");
    await nextTick();

    await wrapper.get('[data-test="exam-workspace-gap-automatic-remove-hundra"]').trigger("click");

    expect(wrapper.emitted("removeAutomaticValue")).toEqual([
      ["item_001", "gap_001", "hundra"],
    ]);
    wrapper.unmount();
  });

  it("forwards Visa som text, closes the popover and focuses the question text", async () => {
    const wrapper = await mountEditor(itemWithAutomaticValue());
    clickGap(wrapper, "gap_001");
    await nextTick();
    expect(wrapper.find('[data-test="exam-workspace-gap-popover"]').exists()).toBe(true);

    await wrapper.get('[data-test="exam-workspace-gap-as-text"]').trigger("click");

    expect(wrapper.emitted("showGapAsText")).toEqual([["item_001", "gap_001"]]);
    expect(wrapper.find('[data-test="exam-workspace-gap-popover"]').exists()).toBe(false);
    // TipTap moves focus on the next animation frame.
    await vi.waitFor(() => expect(document.activeElement).toBe(surface(wrapper)));
    wrapper.unmount();
  });

  it("lets the item's only gap be shown as text", async () => {
    const item = buildGapItem({
      body: [
        {
          heading_level: null,
          segments: [{ kind: "text", marks: [], text: "Svar: " }, { gap_id: "gap_001", kind: "gap" }],
        },
      ],
      gaps: [buildGap("gap_001", ["100"])],
    });
    const wrapper = await mountEditor(item);
    clickGap(wrapper, "gap_001");
    await nextTick();

    const button = wrapper.get('[data-test="exam-workspace-gap-as-text"]');
    expect((button.element as HTMLButtonElement).disabled).toBe(false);
    expect(wrapper.find('[data-test="exam-workspace-gap-as-text-disabled"]').exists()).toBe(false);
    await button.trigger("click");

    expect(wrapper.emitted("showGapAsText")).toEqual([["item_001", "gap_001"]]);
    expect(wrapper.find('[data-test="exam-workspace-gap-popover"]').exists()).toBe(false);
    wrapper.unmount();
  });

  it("forwards neither gap change once the editor is disabled", async () => {
    const wrapper = await mountEditor(itemWithAutomaticValue());
    clickGap(wrapper, "gap_001");
    await nextTick();
    const popover = wrapper.findComponent(ExamWorkspaceGapPopover);
    await wrapper.setProps({ disabled: true });
    expect(wrapper.find('[data-test="exam-workspace-gap-popover"]').exists()).toBe(false);

    popover.vm.$emit("removeAutomaticValue", "item_001", "gap_001", "hundra");
    popover.vm.$emit("showGapAsText", "item_001", "gap_001");
    await wrapper.vm.$nextTick();

    expect(wrapper.emitted("removeAutomaticValue")).toBeUndefined();
    expect(wrapper.emitted("showGapAsText")).toBeUndefined();
    wrapper.unmount();
  });
});
