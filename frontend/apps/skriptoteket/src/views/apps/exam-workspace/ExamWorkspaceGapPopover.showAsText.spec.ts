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
import { documentControl } from "./ExamWorkspaceBodyEditor.specSupport";
import { buildGap as buildNativeGap } from "./examWorkspaceKeyedItems.specSupport";

function buildGap(overrides: Partial<NativeExamGap> = {}): NativeExamGap {
  return buildNativeGap("gap_001", ["100"], overrides);
}

function mountPopover(gap: NativeExamGap) {
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

function popoverButton(): HTMLButtonElement {
  return documentControl<HTMLButtonElement>('[data-test="exam-workspace-gap-as-text"]').element;
}

function answersInput() {
  return documentControl<HTMLInputElement>('[data-test="exam-workspace-gap-values-gap_001-input"]');
}

function answerRows(): HTMLInputElement[] {
  return Array.from(
    document.querySelectorAll<HTMLInputElement>(
      '[data-test="exam-workspace-gap-values-gap_001-input"]',
    ),
  );
}

/** Type into the answers field without committing: only the input event fires. */
async function typePendingAnswers(value: string): Promise<void> {
  answersInput().element.value = value;
  await answersInput().trigger("input");
}

describe("ExamWorkspaceGapPopover Visa som text", () => {
  it("replaces committed typing when accepted answers arrive from outside the popover", async () => {
    const wrapper = mountPopover(buildGap());
    const input = answersInput();
    input.element.value = "hundra";
    await input.trigger("input");
    // The input already committed, so nothing is pending: the outside
    // answers replace the rows instead of being held back.
    expect(wrapper.emitted("commit")).toEqual([["item_001", "gap_001", ["hundra"]]]);
    await wrapper.setProps({ gap: buildGap({ accepted_values: ["101"] }) });
    expect(answerRows().map((row) => row.value)).toEqual(["101"]);
    await documentControl('[data-test="exam-workspace-gap-as-text"]').trigger("click");
    expect(wrapper.emitted("showGapAsText")).toEqual([["item_001", "gap_001"]]);
    wrapper.unmount();
  });
  it("emits showGapAsText for the item and gap when a first accepted answer exists", async () => {
    const wrapper = mountPopover(buildGap());

    expect(popoverButton().disabled).toBe(false);
    await documentControl('[data-test="exam-workspace-gap-as-text"]').trigger("click");

    expect(wrapper.emitted("showGapAsText")).toEqual([["item_001", "gap_001"]]);
    expect(document.querySelector('[data-test="exam-workspace-gap-as-text-disabled"]')).toBeNull();
    wrapper.unmount();
  });

  it("commits typed answers while typing, once more before it emits showGapAsText", async () => {
    const wrapper = mountPopover(buildGap({ accepted_values: ["100"] }));
    const first = answersInput();
    first.element.value = "hundra";
    await first.trigger("input");
    await first.trigger("keydown", { key: "Enter" });
    await wrapper.vm.$nextTick();
    const rows = answerRows();
    expect(rows).toHaveLength(2);
    rows[1]!.value = "100";
    rows[1]!.dispatchEvent(new Event("input", { bubbles: true }));
    await wrapper.vm.$nextTick();

    await documentControl('[data-test="exam-workspace-gap-as-text"]').trigger("click");

    // One commit per typed row; the click itself sends nothing more.
    expect(wrapper.emitted("commit")).toEqual([
      ["item_001", "gap_001", ["hundra"]],
      ["item_001", "gap_001", ["hundra", "100"]],
    ]);
    expect(wrapper.emitted("showGapAsText")).toEqual([["item_001", "gap_001"]]);
    // The first commit lands before showGapAsText, so the first current value is the one shown.
    const recorded = Object.keys(wrapper.emitted());
    expect(recorded.indexOf("commit")).toBeLessThan(recorded.indexOf("showGapAsText"));
    wrapper.unmount();
  });

  it("disables the button as soon as the pending answers field is cleared", async () => {
    const wrapper = mountPopover(buildGap({ accepted_values: ["100"] }));
    expect(popoverButton().disabled).toBe(false);

    await typePendingAnswers("");

    expect(popoverButton().disabled).toBe(true);
    expect(document.querySelector('[data-test="exam-workspace-gap-as-text-disabled"]')).not.toBeNull();
    expect(wrapper.emitted("commit")).toBeUndefined();
    wrapper.unmount();
  });

  it("enables the button as soon as a first answer is typed into an empty gap", async () => {
    const wrapper = mountPopover(buildGap({ accepted_values: [] }));
    expect(popoverButton().disabled).toBe(true);

    await typePendingAnswers("hundra");

    expect(popoverButton().disabled).toBe(false);
    expect(document.querySelector('[data-test="exam-workspace-gap-as-text-disabled"]')).toBeNull();

    await documentControl('[data-test="exam-workspace-gap-as-text"]').trigger("click");
    expect(wrapper.emitted("commit")).toEqual([["item_001", "gap_001", ["hundra"]]]);
    expect(wrapper.emitted("showGapAsText")).toEqual([["item_001", "gap_001"]]);
    wrapper.unmount();
  });

  it("does not write answers back after the gap becomes text", async () => {
    const wrapper = mountPopover(buildGap({ accepted_values: ["100"] }));
    const input = answersInput().element;
    input.value = "hundra";
    input.dispatchEvent(new Event("input", { bubbles: true }));

    await documentControl('[data-test="exam-workspace-gap-as-text"]').trigger("click");
    input.dispatchEvent(new Event("change", { bubbles: true }));
    input.dispatchEvent(new FocusEvent("focusout", { bubbles: true }));

    expect(wrapper.emitted("commit")).toEqual([["item_001", "gap_001", ["hundra"]]]);
    expect(wrapper.emitted("showGapAsText")).toHaveLength(1);
    wrapper.unmount();
  });

  it("disables the button with an explanation while no accepted answer exists", async () => {
    const wrapper = mountPopover(buildGap({ accepted_values: [] }));
    const button = documentControl('[data-test="exam-workspace-gap-as-text"]');
    const explanation = documentControl('[data-test="exam-workspace-gap-as-text-disabled"]');

    expect(popoverButton().disabled).toBe(true);
    expect(button.attributes("aria-describedby")).toBe(explanation.attributes("id"));

    await button.trigger("click");
    expect(wrapper.emitted("showGapAsText")).toBeUndefined();
    wrapper.unmount();
  });
});
