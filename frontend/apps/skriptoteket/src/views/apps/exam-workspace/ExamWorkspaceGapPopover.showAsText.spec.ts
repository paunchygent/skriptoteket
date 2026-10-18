/**
 * Exam workspace gap popover: "Visa som text".
 *
 * Expected behavior:
 *   The button replaces the gap with its first accepted answer as plain
 *   text. The pending answers field decides whether it is enabled: clearing
 *   the field disables it at once and typing a first answer into an empty
 *   gap enables it without a commit. Clicking commits pending edits before
 *   it emits, and the disabled state carries a visible explanation linked
 *   to the button.
 */

import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import type { NativeExamGap } from "../../../api/examWorkspace";
import ExamWorkspaceGapPopover from "./ExamWorkspaceGapPopover.vue";
import { buildGap as buildNativeGap } from "./examWorkspaceKeyedItems.specSupport";

function buildGap(overrides: Partial<NativeExamGap> = {}): NativeExamGap {
  return buildNativeGap("gap_001", ["100"], overrides);
}

function mountPopover(gap: NativeExamGap) {
  return mount(ExamWorkspaceGapPopover, {
    attachTo: document.body,
    props: {
      gap,
      gapId: "gap_001",
      gapNumber: 1,
      itemId: "item_001",
      left: 0,
      top: 0,
    },
  });
}

type PopoverWrapper = ReturnType<typeof mountPopover>;

function popoverButton(wrapper: PopoverWrapper): HTMLButtonElement {
  return wrapper.get('[data-test="exam-workspace-gap-as-text"]').element as HTMLButtonElement;
}

function answersInput(wrapper: PopoverWrapper) {
  return wrapper.get('[data-test="exam-workspace-gap-values-gap_001"]');
}

/** Type into the answers field without committing: only the input event fires. */
async function typePendingAnswers(wrapper: PopoverWrapper, value: string): Promise<void> {
  (answersInput(wrapper).element as HTMLInputElement).value = value;
  await answersInput(wrapper).trigger("input");
}

describe("ExamWorkspaceGapPopover Visa som text", () => {
  it("keeps an uncommitted draft when accepted answers arrive from outside the popover", async () => {
    const wrapper = mountPopover(buildGap());
    const input = wrapper.get<HTMLInputElement>('[data-test="exam-workspace-gap-values-gap_001"]');
    input.element.value = "hundra";
    await input.trigger("input");
    await wrapper.setProps({ gap: buildGap({ accepted_values: ["101"] }) });
    expect(input.element.value).toBe("hundra");
    await wrapper.get('[data-test="exam-workspace-gap-as-text"]').trigger("click");
    expect(wrapper.emitted("commit")).toEqual([["item_001", "gap_001", ["hundra"]]]);
    wrapper.unmount();
  });
  it("emits showGapAsText for the item and gap when a first accepted answer exists", async () => {
    const wrapper = mountPopover(buildGap());

    expect(popoverButton(wrapper).disabled).toBe(false);
    await wrapper.get('[data-test="exam-workspace-gap-as-text"]').trigger("click");

    expect(wrapper.emitted("showGapAsText")).toEqual([["item_001", "gap_001"]]);
    expect(wrapper.find('[data-test="exam-workspace-gap-as-text-disabled"]').exists()).toBe(false);
    wrapper.unmount();
  });

  it("commits pending answer edits before it emits showGapAsText", async () => {
    const wrapper = mountPopover(buildGap({ accepted_values: ["100"] }));
    await typePendingAnswers(wrapper, "hundra, 100");

    await wrapper.get('[data-test="exam-workspace-gap-as-text"]').trigger("click");

    expect(wrapper.emitted("commit")).toEqual([["item_001", "gap_001", ["hundra", "100"]]]);
    expect(wrapper.emitted("showGapAsText")).toEqual([["item_001", "gap_001"]]);
    // The commit must land first, so the first current value is the one shown.
    const recorded = Object.keys(wrapper.emitted());
    expect(recorded.indexOf("commit")).toBeLessThan(recorded.indexOf("showGapAsText"));
    wrapper.unmount();
  });

  it("disables the button as soon as the pending answers field is cleared", async () => {
    const wrapper = mountPopover(buildGap({ accepted_values: ["100"] }));
    expect(popoverButton(wrapper).disabled).toBe(false);

    await typePendingAnswers(wrapper, "");

    expect(popoverButton(wrapper).disabled).toBe(true);
    expect(wrapper.find('[data-test="exam-workspace-gap-as-text-disabled"]').exists()).toBe(true);
    expect(wrapper.emitted("commit")).toBeUndefined();
    wrapper.unmount();
  });

  it("enables the button as soon as a first answer is typed into an empty gap", async () => {
    const wrapper = mountPopover(buildGap({ accepted_values: [] }));
    expect(popoverButton(wrapper).disabled).toBe(true);

    await typePendingAnswers(wrapper, "hundra");

    expect(popoverButton(wrapper).disabled).toBe(false);
    expect(wrapper.find('[data-test="exam-workspace-gap-as-text-disabled"]').exists()).toBe(false);

    await wrapper.get('[data-test="exam-workspace-gap-as-text"]').trigger("click");
    expect(wrapper.emitted("commit")).toEqual([["item_001", "gap_001", ["hundra"]]]);
    expect(wrapper.emitted("showGapAsText")).toEqual([["item_001", "gap_001"]]);
    wrapper.unmount();
  });

  it("does not write answers back after the gap becomes text", async () => {
    const wrapper = mountPopover(buildGap({ accepted_values: ["100"] }));
    const input = answersInput(wrapper).element as HTMLInputElement;
    input.value = "hundra";

    await wrapper.get('[data-test="exam-workspace-gap-as-text"]').trigger("click");
    input.dispatchEvent(new Event("change", { bubbles: true }));
    input.dispatchEvent(new FocusEvent("focusout", { bubbles: true }));

    expect(wrapper.emitted("commit")).toEqual([["item_001", "gap_001", ["hundra"]]]);
    expect(wrapper.emitted("showGapAsText")).toHaveLength(1);
    wrapper.unmount();
  });

  it("disables the button with an explanation while no accepted answer exists", async () => {
    const wrapper = mountPopover(buildGap({ accepted_values: [] }));
    const button = wrapper.get('[data-test="exam-workspace-gap-as-text"]');
    const explanation = wrapper.get('[data-test="exam-workspace-gap-as-text-disabled"]');

    expect(popoverButton(wrapper).disabled).toBe(true);
    expect(button.attributes("aria-describedby")).toBe(explanation.attributes("id"));

    await button.trigger("click");
    expect(wrapper.emitted("showGapAsText")).toBeUndefined();
    wrapper.unmount();
  });
});
