/**
 * Exam workspace Skrivyta field (TASK-SKRIPT-40-04-07 W4, TASK-SKRIPT-40-04-18).
 *
 * Expected behavior:
 *   The field names the question's writing area in rows, the − / + stepper
 *   emits the next count and is bounded by the house range, and the
 *   "Alla fritextfrågor" tool opens a popover in either of two states. When
 *   other free-text questions differ, it names how many questions get the
 *   count and which differ, and confirming emits the current count and closes.
 *   When all already match, it confirms that with only "Stäng". The tool stays
 *   enabled when the counts match and is inert only while the field is
 *   disabled. Escape, Avbryt, Stäng and a pointer press outside close the
 *   popover and return focus to the tool. A control that cannot act states
 *   why: the stepped bound or the lock notice it points at.
 */

import { mount, type VueWrapper } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";

import ExamWorkspaceWritingLinesField from "./ExamWorkspaceWritingLinesField.vue";
import {
  MAX_WRITING_LINES,
  MIN_WRITING_LINES,
  type FreeTextWritingLines,
} from "./examWorkspaceWritingLines";

const FIELD = '[data-test="exam-workspace-writing-lines"]';
const MINUS = '[data-test="exam-workspace-writing-lines-minus"]';
const PLUS = '[data-test="exam-workspace-writing-lines-plus"]';
const APPLY_ALL = '[data-test="exam-workspace-writing-lines-apply-all"]';
const COUNT = '[data-test="exam-workspace-writing-lines-count"]';
const POPOVER = '[data-test="exam-workspace-writing-lines-popover"]';
const CONFIRM = '[data-test="exam-workspace-writing-lines-apply-confirm"]';
const CANCEL = '[data-test="exam-workspace-writing-lines-cancel"]';
const CLOSE = '[data-test="exam-workspace-writing-lines-close"]';
const CONTROLS = [MINUS, PLUS, APPLY_ALL];
const LOCK_REASON_ID = "exam-workspace-writing-lines-lock-reason";
const LOCK_REASON_TEXT =
  "Frågan konverteras fortfarande. Texten från provfilen visas tills den är klar och går inte att ändra under tiden.";

/** Six free-text questions of which 1a, 1b and 3a differ from 8 rows. */
const MIXED: FreeTextWritingLines[] = [
  { itemId: "i1", label: "1a", lines: 4 },
  { itemId: "i2", label: "1b", lines: null },
  { itemId: "i3", label: "2", lines: 8 },
  { itemId: "i4", label: "3a", lines: 12 },
  { itemId: "i5", label: "3b", lines: 8 },
  { itemId: "i6", label: "4", lines: 8 },
];
const MATCHING: FreeTextWritingLines[] = MIXED.map((entry) => ({ ...entry, lines: 8 }));

const mounted: VueWrapper[] = [];

function mountField(
  lines: number,
  options: { disabled?: boolean; freeText?: FreeTextWritingLines[]; lockedReasonId?: string | null } = {},
) {
  const wrapper = mount(ExamWorkspaceWritingLinesField, {
    attachTo: document.body,
    props: {
      lines,
      disabled: options.disabled ?? false,
      freeText: options.freeText ?? MIXED,
      lockedReasonId: options.lockedReasonId ?? null,
    },
  });
  mounted.push(wrapper);
  return wrapper;
}

afterEach(() => {
  for (const wrapper of mounted.splice(0)) {
    wrapper.unmount();
  }
});

describe("ExamWorkspaceWritingLinesField", () => {
  it("names the writing area in rows", () => {
    const field = mountField(8).get(FIELD);

    expect(field.text()).toContain("Skrivyta");
    expect(field.text()).toContain("8 rader");
  });

  it("uses the singular for one row", () => {
    expect(mountField(1).get(FIELD).text()).toContain("1 rad");
  });

  it("is one row group named by its Skrivyta label", () => {
    const field = mountField(8).get(FIELD);
    const labelId = field.attributes("aria-labelledby");

    expect(field.attributes("role")).toBe("group");
    expect(field.classes()).toContain("xw-answer-row");
    expect(labelId).toBeDefined();
    expect(field.get(`[id="${labelId}"]`).text()).toBe("Skrivyta");
  });

  it("emits the next count from the stepper", async () => {
    const up = mountField(8);
    await up.get(PLUS).trigger("click");
    expect(up.emitted("update")).toEqual([[9]]);

    const down = mountField(8);
    await down.get(MINUS).trigger("click");
    expect(down.emitted("update")).toEqual([[7]]);
  });

  it("disables the stepper at the house bounds", () => {
    expect(mountField(MIN_WRITING_LINES).get(MINUS).attributes("disabled")).toBeDefined();
    expect(mountField(MAX_WRITING_LINES).get(PLUS).attributes("disabled")).toBeDefined();
  });

  it("shows the count in a fixed-width centred value between the stepper tools", () => {
    const wrapper = mountField(8);
    const count = wrapper.get(COUNT);

    expect(count.classes()).toContain("xw-lines__value");
    expect(wrapper.get(".xw-answer-controls").classes()).toContain("xw-lines");
    expect(count.element.previousElementSibling).toBe(wrapper.get(MINUS).element);
    expect(count.element.nextElementSibling).toBe(wrapper.get(PLUS).element);
    expect(wrapper.get(MINUS).classes()).toContain("xw-tool");
    expect(wrapper.get(APPLY_ALL).classes()).toEqual(["xw-tool", "xw-tool--word"]);
    expect(wrapper.get(APPLY_ALL).text()).toBe("Alla fritextfrågor");
    expect(wrapper.find(".xw-toolsep").exists()).toBe(true);
  });

  it("opens no popover until the tool is pressed", () => {
    const wrapper = mountField(8);
    const tool = wrapper.get(APPLY_ALL);

    expect(wrapper.find(POPOVER).exists()).toBe(false);
    expect(tool.attributes("aria-haspopup")).toBe("dialog");
    expect(tool.attributes("aria-expanded")).toBe("false");
    expect(tool.attributes("title")).toBe("Samma skrivyta för alla fritextfrågor");
  });

  it("names the questions that change and what they get", async () => {
    const wrapper = mountField(8);
    await wrapper.get(APPLY_ALL).trigger("click");

    const popover = wrapper.get(POPOVER);
    const paragraphs = popover.findAll("p").map((p) => p.text());
    expect(popover.attributes("role")).toBe("dialog");
    expect(popover.attributes("aria-label")).toBe("Samma skrivyta för alla fritextfrågor");
    expect(wrapper.get(APPLY_ALL).attributes("aria-expanded")).toBe("true");
    expect(popover.get("h3").text()).toBe("Samma skrivyta för alla fritextfrågor");
    expect(paragraphs).toEqual([
      "Alla 6 fritextfrågor får 8 rader.",
      "1a, 1b och 3a har i dag en annan skrivyta.",
    ]);
    expect(popover.findAll("button").map((button) => button.text())).toEqual(["Avbryt", "Använd 8 rader"]);
  });

  it("uses the singular for one row in the popover", async () => {
    const wrapper = mountField(1, { freeText: [{ itemId: "i1", label: "1", lines: 1 }, { itemId: "i2", label: "2", lines: 3 }] });
    await wrapper.get(APPLY_ALL).trigger("click");

    expect(wrapper.findAll(`${POPOVER} p`)[0]!.text()).toBe("Alla 2 fritextfrågor får 1 rad.");
    expect(wrapper.findAll(`${POPOVER} p`)[1]!.text()).toBe("2 har i dag en annan skrivyta.");
    expect(wrapper.get(CONFIRM).text()).toBe("Använd 1 rad");
  });

  it("moves focus to the confirm action on open", async () => {
    const wrapper = mountField(8);
    await wrapper.get(APPLY_ALL).trigger("click");
    await wrapper.vm.$nextTick();

    expect(document.activeElement).toBe(wrapper.get(CONFIRM).element);
  });

  it("emits the current count to every free-text question on confirm and closes", async () => {
    const wrapper = mountField(8);
    await wrapper.get(APPLY_ALL).trigger("click");
    await wrapper.get(CONFIRM).trigger("click");
    await wrapper.vm.$nextTick();

    expect(wrapper.emitted("applyToAll")).toEqual([[8]]);
    expect(wrapper.find(POPOVER).exists()).toBe(false);
    expect(document.activeElement).toBe(wrapper.get(APPLY_ALL).element);
  });

  it("emits nothing from opening the popover", async () => {
    const wrapper = mountField(8);
    await wrapper.get(APPLY_ALL).trigger("click");

    expect(wrapper.emitted("applyToAll")).toBeUndefined();
  });

  it("closes on Avbryt without emitting and returns focus to the tool", async () => {
    const wrapper = mountField(8);
    await wrapper.get(APPLY_ALL).trigger("click");
    await wrapper.get(CANCEL).trigger("click");
    await wrapper.vm.$nextTick();

    expect(wrapper.find(POPOVER).exists()).toBe(false);
    expect(wrapper.emitted("applyToAll")).toBeUndefined();
    expect(document.activeElement).toBe(wrapper.get(APPLY_ALL).element);
  });

  it("closes on Escape without emitting and returns focus to the tool", async () => {
    const wrapper = mountField(8);
    await wrapper.get(APPLY_ALL).trigger("click");
    await wrapper.vm.$nextTick();
    await wrapper.get(CONFIRM).trigger("keydown", { key: "Escape" });
    await wrapper.vm.$nextTick();

    expect(wrapper.find(POPOVER).exists()).toBe(false);
    expect(wrapper.emitted("applyToAll")).toBeUndefined();
    expect(document.activeElement).toBe(wrapper.get(APPLY_ALL).element);
  });

  it("closes on a pointer press outside and leaves focus where the press put it", async () => {
    const outside = document.createElement("button");
    document.body.append(outside);
    try {
      const wrapper = mountField(8);
      await wrapper.get(APPLY_ALL).trigger("click");
      outside.focus();
      outside.dispatchEvent(new Event("pointerdown", { bubbles: true }));
      await wrapper.vm.$nextTick();

      expect(wrapper.find(POPOVER).exists()).toBe(false);
      expect(wrapper.emitted("applyToAll")).toBeUndefined();
      expect(document.activeElement).toBe(outside);
    } finally {
      outside.remove();
    }
  });

  it("stays open for a pointer press inside the popover", async () => {
    const wrapper = mountField(8);
    await wrapper.get(APPLY_ALL).trigger("click");
    wrapper.get(POPOVER).element.dispatchEvent(new Event("pointerdown", { bubbles: true }));
    await wrapper.vm.$nextTick();

    expect(wrapper.find(POPOVER).exists()).toBe(true);
  });

  it("closes when the tool is pressed again", async () => {
    const wrapper = mountField(8);
    await wrapper.get(APPLY_ALL).trigger("click");
    await wrapper.get(APPLY_ALL).trigger("click");

    expect(wrapper.find(POPOVER).exists()).toBe(false);
  });

  it("closes when the field becomes disabled", async () => {
    const wrapper = mountField(8);
    await wrapper.get(APPLY_ALL).trigger("click");
    await wrapper.setProps({ disabled: true });

    expect(wrapper.find(POPOVER).exists()).toBe(false);
  });

  it("names the exam's only free-text question instead of counting it", async () => {
    const wrapper = mountField(8, { freeText: [{ itemId: "i1", label: "1", lines: 8 }] });
    await wrapper.get(APPLY_ALL).trigger("click");
    await wrapper.vm.$nextTick();

    const popover = wrapper.get(POPOVER);
    expect(popover.text()).toContain("Det här är provets enda fritextfråga.");
    expect(popover.text()).not.toContain("Alla 1");
  });

  it("keeps the tool enabled and opens a confirmation with only Stäng when every count matches", async () => {
    const wrapper = mountField(8, { freeText: MATCHING });
    const tool = wrapper.get(APPLY_ALL);

    expect(tool.attributes("disabled")).toBeUndefined();
    expect(tool.attributes("title")).toBe("Samma skrivyta för alla fritextfrågor");
    await tool.trigger("click");
    await wrapper.vm.$nextTick();

    const popover = wrapper.get(POPOVER);
    expect(popover.text()).toContain("Alla 6 fritextfrågor har redan 8 rader.");
    expect(popover.find(".xw-pop__ok svg").exists()).toBe(true);
    expect(popover.findAll("button").map((button) => button.text())).toEqual(["Stäng"]);
    expect(wrapper.find(CONFIRM).exists()).toBe(false);
    expect(document.activeElement).toBe(wrapper.get(CLOSE).element);

    await wrapper.get(CLOSE).trigger("click");
    await wrapper.vm.$nextTick();

    expect(wrapper.find(POPOVER).exists()).toBe(false);
    expect(wrapper.emitted("applyToAll")).toBeUndefined();
    expect(document.activeElement).toBe(tool.element);
  });

  it("keeps the row steady while the popover opens and the count changes", async () => {
    const wrapper = mountField(8);
    const before = wrapper.get(".xw-answer-controls").element.children.length;
    await wrapper.get(APPLY_ALL).trigger("click");

    // The popover lives inside the tool's anchor span, not as a new row child.
    expect(wrapper.get(".xw-answer-controls").element.children.length).toBe(before);
    expect(wrapper.get(POPOVER).element.closest(".xw-lines__apply")).not.toBeNull();
    expect(wrapper.get(".xw-answer-controls").classes()).toContain("xw-lines");
    await wrapper.setProps({ lines: 12 });
    expect(wrapper.get(COUNT).classes()).toContain("xw-lines__value");
  });

  it("makes every control inert while disabled", () => {
    const wrapper = mountField(8, { disabled: true });

    expect(wrapper.get(MINUS).attributes("disabled")).toBeDefined();
    expect(wrapper.get(PLUS).attributes("disabled")).toBeDefined();
    expect(wrapper.get(APPLY_ALL).attributes("disabled")).toBeDefined();
  });

  it("states the minimum bound only while the floor holds", () => {
    const atMin = mountField(MIN_WRITING_LINES);

    expect(atMin.get(MINUS).attributes("title")).toBe("Minst 1 rad");
    expect(atMin.get(PLUS).attributes("title")).toBeUndefined();
  });

  it("states the maximum bound only while the ceiling holds", () => {
    const atMax = mountField(MAX_WRITING_LINES);

    expect(atMax.get(PLUS).attributes("title")).toBe("Högst 40 rader");
    expect(atMax.get(MINUS).attributes("title")).toBeUndefined();
  });

  it("adds no reason to a control that can act", () => {
    const wrapper = mountField(8);

    // The apply-all tool always carries its descriptive title; it states no blocking reason.
    for (const control of [MINUS, PLUS]) {
      expect(wrapper.get(control).attributes("title")).toBeUndefined();
    }
    for (const control of CONTROLS) {
      expect(wrapper.get(control).attributes("aria-describedby")).toBeUndefined();
    }
  });

  it("points every control at the lock notice only while the lock holds", () => {
    const notice = document.createElement("p");
    notice.id = LOCK_REASON_ID;
    notice.textContent = LOCK_REASON_TEXT;
    document.body.append(notice);

    try {
      const locked = mountField(8, { disabled: true, lockedReasonId: LOCK_REASON_ID });
      for (const control of CONTROLS) {
        const describedBy = locked.get(control).attributes("aria-describedby");
        expect(describedBy).toBe(LOCK_REASON_ID);
        const resolved = describedBy === undefined ? null : document.getElementById(describedBy);
        expect(resolved).toBe(notice);
        expect(resolved?.textContent).toBe(LOCK_REASON_TEXT);
      }

      // The lock id alone does nothing while the field is enabled.
      const enabled = mountField(8, { lockedReasonId: LOCK_REASON_ID });
      for (const control of CONTROLS) {
        expect(enabled.get(control).attributes("aria-describedby")).toBeUndefined();
      }
    } finally {
      notice.remove();
    }
  });
});
