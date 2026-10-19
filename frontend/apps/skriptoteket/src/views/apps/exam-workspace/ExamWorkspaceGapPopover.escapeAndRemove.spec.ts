/**
 * Exam workspace gap popover: Escape keeps typing and remove keeps focus.
 *
 * Expected behavior:
 *   Escape in the popover keeps what was typed (typing already committed it
 *   on input): typed dropdown option text is emitted through `updateOptions`,
 *   typed text-gap answers through `commit`, exactly once even when a
 *   `focusout` or `change` fires late, and the popover closes returning
 *   focus. Escape during an IME composition belongs to the composition and
 *   is ignored. Removing a dropdown option row keeps the popover open and
 *   moves focus synchronously to the neighbouring row's text input (the
 *   previous row, else the next row, else the add control).
 */

import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import { nextTick } from "vue";

import type { NativeExamChoice, NativeExamGap } from "../../../api/examWorkspace";
import ExamWorkspaceGapPopover from "./ExamWorkspaceGapPopover.vue";
import { documentControl, popoverExists } from "./ExamWorkspaceBodyEditor.specSupport";
import { buildGap } from "./examWorkspaceKeyedItems.specSupport";
import { plainBody } from "./examWorkspaceRichText";

const ITEM_ID = "item_001";
const GAP_ID = "gap_001";

function dropdownGap(overrides: Partial<NativeExamGap> = {}): NativeExamGap {
  return buildGap(
    GAP_ID,
    [],
    {
      options: [
        { body: plainBody("alpha"), choice_id: "choice_001" },
        { body: plainBody("beta"), choice_id: "choice_002" },
      ],
      correct_option_id: "choice_001",
      ...overrides,
    },
  );
}

function mountDropdown(gap: NativeExamGap) {
  return mount(ExamWorkspaceGapPopover, {
    attachTo: document.body,
    props: { anchor: document.body, dropdown: true, gap, gapId: GAP_ID, gapNumber: 1, itemId: ITEM_ID },
  });
}

function mountTextGap(gap: NativeExamGap) {
  return mount(ExamWorkspaceGapPopover, {
    attachTo: document.body,
    props: { anchor: document.body, gap, gapId: GAP_ID, gapNumber: 1, itemId: ITEM_ID },
  });
}

function optionText(id: string): HTMLInputElement {
  return documentControl<HTMLInputElement>(
    `[data-test="exam-workspace-gap-option-text-${id}"]`,
  ).element;
}

function removeButton(id: string): HTMLButtonElement {
  return documentControl<HTMLButtonElement>(
    `[data-test="exam-workspace-gap-option-remove-${id}"]`,
  ).element;
}

type UpdateOptionsEvent = [string, string, NativeExamChoice[], string | null];

function updates(wrapper: ReturnType<typeof mountDropdown>): UpdateOptionsEvent[] {
  return wrapper.emitted<UpdateOptionsEvent>("updateOptions") ?? [];
}

describe("ExamWorkspaceGapPopover Escape keeps typing", () => {
  it("commits typed dropdown option text on Escape and closes, once", async () => {
    const wrapper = mountDropdown(dropdownGap());
    const input = optionText("choice_002");
    input.value = "Ny text";
    input.dispatchEvent(new Event("input", { bubbles: true }));
    await wrapper.vm.$nextTick();

    input.dispatchEvent(new KeyboardEvent("keydown", { bubbles: true, key: "Escape" }));
    await wrapper.vm.$nextTick();

    const events = updates(wrapper);
    expect(events).toHaveLength(1);
    expect(events[0][0]).toBe(ITEM_ID);
    expect(events[0][1]).toBe(GAP_ID);
    expect(events[0][2].find((option) => option.choice_id === "choice_002")?.body).toEqual(
      plainBody("Ny text"),
    );
    expect(events[0][3]).toBe("choice_001");
    expect(wrapper.emitted("close")).toEqual([[true]]);

    // A focusout that follows the close commits nothing twice.
    input.dispatchEvent(new FocusEvent("focusout", { bubbles: true, relatedTarget: null }));
    await wrapper.vm.$nextTick();
    expect(updates(wrapper)).toHaveLength(1);
    wrapper.unmount();
  });

  it("commits typed text-gap answers on Escape and closes, once", async () => {
    const wrapper = mountTextGap(buildGap(GAP_ID, ["ett"]));
    const row = documentControl<HTMLInputElement>(
      `[data-test="exam-workspace-gap-values-${GAP_ID}-input"]`,
    );
    row.element.value = "etta";
    await row.trigger("input");
    await row.trigger("keydown", { key: "Escape" });

    expect(wrapper.emitted("commit")).toEqual([[ITEM_ID, GAP_ID, ["etta"]]]);
    expect(wrapper.emitted("close")).toEqual([[true]]);

    row.element.dispatchEvent(new Event("change", { bubbles: true }));
    await wrapper.vm.$nextTick();
    expect(wrapper.emitted("commit")).toHaveLength(1);
    wrapper.unmount();
  });

  it("ignores Escape during an IME composition", async () => {
    const wrapper = mountDropdown(dropdownGap());
    const input = optionText("choice_002");
    input.value = "Ny text";
    input.dispatchEvent(new Event("input", { bubbles: true }));
    await wrapper.vm.$nextTick();

    // Typing already committed on input; the ignored Escape adds nothing.
    expect(updates(wrapper)).toHaveLength(1);

    const composing = new KeyboardEvent("keydown", { bubbles: true, key: "Escape" });
    Object.defineProperty(composing, "isComposing", { value: true });
    input.dispatchEvent(composing);
    await wrapper.vm.$nextTick();

    expect(updates(wrapper)).toHaveLength(1);
    expect(wrapper.emitted("close")).toBeUndefined();
    wrapper.unmount();
  });
});

describe("ExamWorkspaceGapPopover remove keeps focus", () => {
  it("focuses the previous row when removing a later option", async () => {
    const wrapper = mountDropdown(dropdownGap());
    removeButton("choice_002").focus();
    removeButton("choice_002").click();

    expect(document.activeElement).toBe(optionText("choice_001"));

    await nextTick();
    expect(popoverExists()).toBe(true);
    expect(wrapper.emitted("close")).toBeUndefined();
    const events = updates(wrapper);
    expect(events).toHaveLength(1);
    expect(events[0][2].map((option) => option.choice_id)).toEqual(["choice_001"]);
    expect(events[0][3]).toBe("choice_001");
    wrapper.unmount();
  });

  it("focuses the next row when removing the first option", async () => {
    const wrapper = mountDropdown(dropdownGap({ correct_option_id: null }));
    removeButton("choice_001").focus();
    removeButton("choice_001").click();

    expect(document.activeElement).toBe(optionText("choice_002"));

    await nextTick();
    expect(popoverExists()).toBe(true);
    expect(wrapper.emitted("close")).toBeUndefined();
    const events = updates(wrapper);
    expect(events).toHaveLength(1);
    expect(events[0][2].map((option) => option.choice_id)).toEqual(["choice_002"]);
    wrapper.unmount();
  });

  it("focuses the add control when removing the only option", async () => {
    const wrapper = mountDropdown(
      dropdownGap({
        correct_option_id: null,
        options: [{ body: plainBody("solo"), choice_id: "choice_001" }],
      }),
    );
    removeButton("choice_001").focus();
    removeButton("choice_001").click();

    expect(document.activeElement).toBe(
      document.querySelector('[data-test="exam-workspace-gap-option-add"]'),
    );

    await nextTick();
    expect(popoverExists()).toBe(true);
    expect(wrapper.emitted("close")).toBeUndefined();
    const events = updates(wrapper);
    expect(events).toHaveLength(1);
    expect(events[0][2]).toEqual([]);
    wrapper.unmount();
  });
});
