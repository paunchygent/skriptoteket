/**
 * Exam workspace Skrivyta field: label, stepper, bounds and lock notice.
 *
 * Expected behavior:
 *   The field names the question's writing area in rows, the − / + stepper
 *   emits the next count and is bounded by the house range, and the count
 *   shows in a fixed-width centred value between the stepper tools without
 *   changing the row. A control that cannot act states why: the stepped
 *   bound or the lock notice it points at.
 */

import { afterEach, describe, expect, it } from "vitest";

import {
  APPLY_ALL,
  CONTROLS,
  COUNT,
  FIELD,
  LOCK_REASON_ID,
  LOCK_REASON_TEXT,
  MINUS,
  PLUS,
  POPOVER,
  mountField,
  teardownWritingLinesField,
} from "./ExamWorkspaceWritingLinesField.specSupport";
import { MAX_WRITING_LINES, MIN_WRITING_LINES } from "./examWorkspaceWritingLines";

afterEach(() => {
  teardownWritingLinesField();
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
    expect(count.element.parentElement?.classList.contains("xw-lines__stepper")).toBe(true);
    expect(wrapper.get(APPLY_ALL).classes()).toEqual(["xw-tool", "xw-tool--word"]);
    expect(wrapper.get(APPLY_ALL).text()).toBe("Alla fritextfrågor");
    expect(wrapper.find(".xw-toolsep").exists()).toBe(true);
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
