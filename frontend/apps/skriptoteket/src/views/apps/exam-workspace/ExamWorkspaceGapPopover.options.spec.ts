/**
 * Exam workspace gap popover: dropdown option editor.
 *
 * Expected behavior:
 *   A dropdown gap lists its options in stored order with a radio for the
 *   correct one. Radio, add, remove and move each emit the whole option
 *   state once as a structural edit and keep the popover open. Typed text
 *   commits while typing as a typing edit, rides along as plain text, and
 *   is kept on Escape. The correct option cannot be removed. A Lucktext gap
 *   keeps the accepted answers field and shows no option editor.
 */

import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import type { NativeExamChoice, NativeExamGap } from "../../../api/examWorkspace";
import ExamWorkspaceGapPopover from "./ExamWorkspaceGapPopover.vue";
import { buildGapItem, clickGap, documentControl, mountEditor, popoverExists, popoverRoot } from "./ExamWorkspaceBodyEditor.specSupport";
import { buildGap } from "./examWorkspaceKeyedItems.specSupport";
import { plainBody } from "./examWorkspaceRichText";

const MARKED_BODY: NativeExamChoice["body"] = [
  { heading_level: 2, segments: [{ kind: "text", text: "fet", marks: ["bold"] }] },
];

function options(): NativeExamChoice[] {
  return [
    { body: plainBody("zebra"), choice_id: "choice_003" },
    { body: MARKED_BODY, choice_id: "choice_001" },
    { body: plainBody("apa"), choice_id: "choice_005" },
  ];
}

function dropdownGap(overrides: Partial<NativeExamGap> = {}): NativeExamGap {
  return buildGap("gap_001", [], { options: options(), correct_option_id: "choice_001", ...overrides });
}

function mountPopover(gap: NativeExamGap, dropdown = true) {
  return mount(ExamWorkspaceGapPopover, {
    attachTo: document.body,
    props: { anchor: document.body, dropdown, gap, gapId: "gap_001", gapNumber: 1, itemId: "item_001" },
  });
}

type Wrapper = ReturnType<typeof mountPopover>;

function sel(part: string, id: string): string {
  return `[data-test="exam-workspace-gap-option-${part}-${id}"]`;
}

function text(wrapper: Wrapper, id: string) {
  return documentControl<HTMLInputElement>(sel("text", id));
}

type UpdateOptionsEvent = [string, string, NativeExamChoice[], string | null, boolean];

function updates(wrapper: Wrapper): UpdateOptionsEvent[] {
  return wrapper.emitted<UpdateOptionsEvent>("updateOptions") ?? [];
}

function ids(options: NativeExamChoice[]): string[] {
  return options.map((option) => option.choice_id);
}

describe("ExamWorkspaceGapPopover dropdown options", () => {
  it("renders rows in stored order with the correct radio checked", () => {
    const wrapper = mountPopover(dropdownGap());
    const rows = Array.from(
      document.querySelectorAll('[data-test^="exam-workspace-gap-option-choice_"]'),
    );
    expect(rows.map((row) => row.getAttribute("data-test"))).toEqual([
      "exam-workspace-gap-option-choice_003",
      "exam-workspace-gap-option-choice_001",
      "exam-workspace-gap-option-choice_005",
    ]);
    expect(documentControl<HTMLInputElement>(sel("correct", "choice_001")).element.checked).toBe(true);
    expect(documentControl<HTMLInputElement>(sel("correct", "choice_003")).element.checked).toBe(false);
    expect(documentControl(sel("correct", "choice_003")).attributes("aria-label")).toBe("Rätt svar: zebra");
    expect(popoverRoot().getAttribute("aria-label")).toBe("Alternativ för lucka 1");
    wrapper.unmount();
  });

  it("hides the accepted answers, automatic answers and Visa som text", () => {
    const wrapper = mountPopover(dropdownGap({ automatic_values: ["x"] }));
    expect(document.querySelector('[data-test="exam-workspace-gap-values-gap_001"]')).toBeNull();
    expect(document.querySelector('[data-test="exam-workspace-gap-automatic-values"]')).toBeNull();
    expect(document.querySelector('[data-test="exam-workspace-gap-as-text"]')).toBeNull();
    wrapper.unmount();
  });

  it("keeps the accepted answers field and no option editor for a Lucktext gap", () => {
    const wrapper = mountPopover(buildGap("gap_001", ["100"]), false);
    expect(document.querySelector('[data-test="exam-workspace-gap-values-gap_001"]')).not.toBeNull();
    expect(document.querySelector('[data-test="exam-workspace-gap-options"]')).toBeNull();
    expect(document.querySelector('[data-test="exam-workspace-gap-as-text"]')).not.toBeNull();
    wrapper.unmount();
  });

  it("focuses the first empty option, else the first option", () => {
    const empty = mountPopover(
      dropdownGap({ options: [...options(), { body: plainBody(" "), choice_id: "choice_007" }] }),
    );
    expect(document.activeElement).toBe(text(empty, "choice_007").element);
    empty.unmount();
    const filled = mountPopover(dropdownGap());
    expect(document.activeElement).toBe(text(filled, "choice_003").element);
    filled.unmount();
  });

  it("focuses the Lägg till alternativ button for a dropdown gap with no options", () => {
    const wrapper = mountPopover(dropdownGap({ correct_option_id: null, options: [] }));
    const add = document.querySelector('[data-test="exam-workspace-gap-option-add"]');
    const active = document.activeElement;
    wrapper.unmount();
    expect(add instanceof HTMLButtonElement).toBe(true);
    expect(active).toBe(add);
  });

  it("keeps option focus for a dropdown gap with options, not the add button", () => {
    const empty = mountPopover(
      dropdownGap({ options: [...options(), { body: plainBody(" "), choice_id: "choice_007" }] }),
    );
    const add = document.querySelector('[data-test="exam-workspace-gap-option-add"]');
    expect(document.activeElement).toBe(text(empty, "choice_007").element);
    expect(document.activeElement).not.toBe(add);
    empty.unmount();
    const filled = mountPopover(dropdownGap());
    const filledAdd = document.querySelector('[data-test="exam-workspace-gap-option-add"]');
    expect(document.activeElement).toBe(text(filled, "choice_003").element);
    expect(document.activeElement).not.toBe(filledAdd);
    filled.unmount();
  });

  it("emits the new correct option from the radio as structural and stays open", async () => {
    const wrapper = mountPopover(dropdownGap());
    await documentControl(sel("correct", "choice_005")).setValue(true);
    const [event] = updates(wrapper);
    expect(event[0]).toBe("item_001");
    expect(event[1]).toBe("gap_001");
    expect(ids(event[2])).toEqual(["choice_003", "choice_001", "choice_005"]);
    expect(event[3]).toBe("choice_005");
    expect(event[4]).toBe(true);
    expect(wrapper.emitted("close")).toBeUndefined();
    wrapper.unmount();
  });

  it("adds an option with the smallest unused id and blank text", async () => {
    const wrapper = mountPopover(
      dropdownGap({
        options: [
          { body: plainBody("a"), choice_id: "choice_001" },
          { body: plainBody("c"), choice_id: "choice_003" },
        ],
      }),
    );
    const add = documentControl<HTMLButtonElement>('[data-test="exam-workspace-gap-option-add"]');
    expect(add.element.textContent).not.toContain("Lägg till alternativ");
    expect(add.attributes("aria-label")).toBe("Lägg till alternativ");
    expect(add.attributes("title")).toBe("Lägg till alternativ");
    await add.trigger("click");
    const [event] = updates(wrapper);
    expect(ids(event[2])).toEqual(["choice_001", "choice_003", "choice_002"]);
    expect(event[2][2].body).toEqual(plainBody(" "));
    expect(event[3]).toBe("choice_001");
    expect(wrapper.emitted("close")).toBeUndefined();
    wrapper.unmount();
  });

  it("disables remove on the correct option with a hint and removes others", async () => {
    const wrapper = mountPopover(dropdownGap());
    const correctRemove = documentControl<HTMLButtonElement>(sel("remove", "choice_001"));
    const hint = documentControl('[data-test="exam-workspace-gap-option-remove-hint"]');
    expect(correctRemove.element.disabled).toBe(true);
    expect(correctRemove.attributes("aria-describedby")).toBe(hint.attributes("id"));
    expect(hint.text()).toBe("Markera ett annat alternativ som rätt först");

    const otherRemove = documentControl<HTMLButtonElement>(sel("remove", "choice_003"));
    expect(otherRemove.element.disabled).toBe(false);
    await otherRemove.trigger("click");
    const [event] = updates(wrapper);
    expect(ids(event[2])).toEqual(["choice_001", "choice_005"]);
    expect(event[3]).toBe("choice_001");
    expect(wrapper.emitted("close")).toBeUndefined();
    wrapper.unmount();
  });

  it("moves options up and down, disabled at the ends", async () => {
    const wrapper = mountPopover(dropdownGap());
    expect(documentControl<HTMLButtonElement>(sel("up", "choice_003")).element.disabled).toBe(true);
    expect(documentControl<HTMLButtonElement>(sel("down", "choice_005")).element.disabled).toBe(true);

    await documentControl(sel("up", "choice_001")).trigger("click");
    await documentControl(sel("down", "choice_001")).trigger("click");
    const events = updates(wrapper);
    expect(ids(events[0][2])).toEqual(["choice_001", "choice_003", "choice_005"]);
    expect(ids(events[1][2])).toEqual(["choice_003", "choice_005", "choice_001"]);
    expect(events[0][3]).toBe("choice_001");
    expect(wrapper.emitted("close")).toBeUndefined();
    wrapper.unmount();
  });

  it("emits typed text at once while typing as a typing edit, once per content", async () => {
    const wrapper = mountPopover(dropdownGap());
    const input = text(wrapper, "choice_005");
    input.element.value = "gorilla";
    await input.trigger("input");

    const events = updates(wrapper);
    expect(events).toHaveLength(1);
    const sent = events[0][2];
    expect(sent[2]).toEqual({ body: plainBody("gorilla"), choice_id: "choice_005" });
    expect(sent[1].body).toEqual(MARKED_BODY);
    expect(sent[0].body).toEqual(plainBody("zebra"));
    expect(events[0][4]).toBe(false);

    await input.trigger("change");
    expect(updates(wrapper)).toHaveLength(1);
    wrapper.unmount();
  });

  it("drops the heading format of an edited option only", async () => {
    const wrapper = mountPopover(dropdownGap());
    const input = text(wrapper, "choice_001");
    input.element.value = "fetare";
    await input.trigger("input");
    await input.trigger("change");
    const sent = updates(wrapper)[0][2];
    expect(sent[1].body).toEqual(plainBody("fetare"));
    wrapper.unmount();
  });

  it("commits typed text on Enter and closes", async () => {
    const wrapper = mountPopover(dropdownGap());
    const input = text(wrapper, "choice_003");
    input.element.value = "zeta";
    await input.trigger("input");
    await input.trigger("keydown", { key: "Enter" });
    // The input already sent the text; Enter sends nothing more.
    expect(wrapper.emitted("updateOptions")).toHaveLength(1);
    expect(wrapper.emitted("close")).toEqual([[true]]);
    wrapper.unmount();
  });

  it("keeps typed text on Escape with no further commit", async () => {
    const wrapper = mountPopover(dropdownGap());
    const input = text(wrapper, "choice_003");
    input.element.value = "behållen";
    await input.trigger("input");
    expect(wrapper.emitted("updateOptions")).toHaveLength(1);
    await input.trigger("keydown", { key: "Escape" });
    await input.trigger("change");
    expect(wrapper.emitted("updateOptions")).toHaveLength(1);
    expect(wrapper.emitted("close")).toEqual([[true]]);
    await input.trigger("change");
    expect(updates(wrapper)).toHaveLength(1);
    wrapper.unmount();
  });

  it("carries typed text with the next structural edit", async () => {
    const wrapper = mountPopover(dropdownGap());
    const input = text(wrapper, "choice_003");
    input.element.value = "zeta";
    await input.trigger("input");
    await documentControl(sel("down", "choice_003")).trigger("click");
    const events = updates(wrapper);
    expect(events).toHaveLength(2);
    for (const event of events) {
      expect(event[2].find((option) => option.choice_id === "choice_003")).toEqual({
        body: plainBody("zeta"),
        choice_id: "choice_003",
      });
    }
    expect(events[0][4]).toBe(false);
    expect(events[1][4]).toBe(true);
    wrapper.unmount();
  });

  describe("without a correct option", () => {
    function noCorrect() {
      return mountPopover(dropdownGap({ correct_option_id: null }));
    }

    it("checks no radio and removes nothing from the hint-free remove buttons", () => {
      const wrapper = noCorrect();
      for (const id of ["choice_003", "choice_001", "choice_005"]) {
        expect(documentControl<HTMLInputElement>(sel("correct", id)).element.checked).toBe(false);
        const remove = documentControl<HTMLButtonElement>(sel("remove", id));
        expect(remove.element.disabled).toBe(false);
        expect(remove.attributes("aria-describedby")).toBeUndefined();
      }
      expect(document.querySelector('[data-test="exam-workspace-gap-option-remove-hint"]')).toBeNull();
      wrapper.unmount();
    });

    it("emits the chosen radio id", async () => {
      const wrapper = noCorrect();
      await documentControl(sel("correct", "choice_003")).setValue(true);
      expect(updates(wrapper)[0][3]).toBe("choice_003");
      wrapper.unmount();
    });

    it("keeps null through add, move, remove and text edits", async () => {
      const wrapper = noCorrect();
      await documentControl('[data-test="exam-workspace-gap-option-add"]').trigger("click");
      await documentControl(sel("down", "choice_003")).trigger("click");
      await documentControl(sel("remove", "choice_001")).trigger("click");
      const input = text(wrapper, "choice_005");
      input.element.value = "gorilla";
      await input.trigger("input");
      await input.trigger("change");
      const events = updates(wrapper);
      expect(events).toHaveLength(4);
      expect(events.map((event) => event[3])).toEqual([null, null, null, null]);
      wrapper.unmount();
    });
  });
});

describe("ExamWorkspaceBodyEditor dropdown gap options", () => {
  it("forwards the option state with item and gap ids", async () => {
    const item = buildGapItem({
      kind: "inline_choice",
      gaps: [dropdownGap(), buildGap("gap_002", [])],
    });
    const wrapper = await mountEditor(item);
    clickGap(wrapper, "gap_001");
    await wrapper.vm.$nextTick();
    await wrapper.vm.$nextTick();
    expect(popoverExists()).toBe(true);
    expect(document.querySelector('[data-test="exam-workspace-gap-options"]')).not.toBeNull();
    await documentControl(sel("correct", "choice_005")).setValue(true);
    const [event] = wrapper.emitted("updateGapOptions") ?? [];
    expect(event[0]).toBe("item_001");
    expect(event[1]).toBe("gap_001");
    expect(event[3]).toBe("choice_005");
    wrapper.unmount();
  });

  it("keeps the accepted answers field for a gap-fill item", async () => {
    const wrapper = await mountEditor();
    clickGap(wrapper, "gap_001");
    await wrapper.vm.$nextTick();
    await wrapper.vm.$nextTick();
    expect(document.querySelector('[data-test="exam-workspace-gap-values-gap_001"]')).not.toBeNull();
    expect(document.querySelector('[data-test="exam-workspace-gap-options"]')).toBeNull();
    wrapper.unmount();
  });
});
