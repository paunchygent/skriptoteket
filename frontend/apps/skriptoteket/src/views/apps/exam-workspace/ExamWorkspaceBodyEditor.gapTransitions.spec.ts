/**
 * Exam workspace question-text editor: gap changes that reshape the item.
 *
 * Expected behavior:
 *   The body editor forwards an automatic answer removal and "Visa som
 *   text" from the open popover, closes the popover on the latter and moves
 *   focus to the paragraph that held the gap, and forwards neither while
 *   disabled.
 */

import { describe, expect, it } from "vitest";

import ExamWorkspaceGapPopover from "./ExamWorkspaceGapPopover.vue";
import { buildGapItem, mountEditor, paragraph } from "./ExamWorkspaceBodyEditor.specSupport";

function itemWithAutomaticValue() {
  return buildGapItem({
    body: [
      { segments: [{ kind: "text", text: "Inledning." }] },
      {
        segments: [
          { kind: "text", text: "Svar: " },
          { gap_id: "gap_001", kind: "gap" },
          { kind: "text", text: " grader." },
        ],
      },
    ],
    gaps: [
      { accepted_values: ["100"], automatic_values: ["hundra"], excluded_automatic_values: [], gap_id: "gap_001" },
      { accepted_values: ["0"], automatic_values: [], excluded_automatic_values: [], gap_id: "gap_002" },
    ],
  });
}

describe("ExamWorkspaceBodyEditor gap transitions", () => {
  it("forwards an automatic answer removal from the open popover", async () => {
    const wrapper = mountEditor(itemWithAutomaticValue());
    await wrapper.get('[data-gap-id="gap_001"]').trigger("click");

    await wrapper.get('[data-test="exam-workspace-gap-automatic-remove-hundra"]').trigger("click");

    expect(wrapper.emitted("removeAutomaticValue")).toEqual([
      ["item_001", "gap_001", "hundra"],
    ]);
    wrapper.unmount();
  });

  it("forwards Visa som text, closes the popover and focuses the paragraph", async () => {
    const wrapper = mountEditor(itemWithAutomaticValue());
    await wrapper.get('[data-gap-id="gap_001"]').trigger("click");
    expect(wrapper.find('[data-test="exam-workspace-gap-popover"]').exists()).toBe(true);

    await wrapper.get('[data-test="exam-workspace-gap-as-text"]').trigger("click");

    expect(wrapper.emitted("showGapAsText")).toEqual([["item_001", "gap_001"]]);
    expect(wrapper.find('[data-test="exam-workspace-gap-popover"]').exists()).toBe(false);
    expect(document.activeElement).toBe(paragraph(wrapper, 1));
    wrapper.unmount();
  });

  it("forwards neither gap change once the editor is disabled", async () => {
    const wrapper = mountEditor(itemWithAutomaticValue());
    await wrapper.get('[data-gap-id="gap_001"]').trigger("click");
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
