/**
 * Exam workspace Skrivyta field (TASK-SKRIPT-40-04-07, W4).
 *
 * Expected behavior:
 *   The field names the question's writing area in rows, the − / + stepper
 *   emits the next count, is bounded by the house range, and the
 *   "Använd för alla fritextfrågor" button emits the current count only while
 *   the free-text questions do not already share it. Every control is inert
 *   while the field is disabled. A control that cannot act states why: the
 *   stepped bound, the already-shared count, or the lock notice it points at.
 */

import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import ExamWorkspaceWritingLinesField from "./ExamWorkspaceWritingLinesField.vue";
import {
  MAX_WRITING_LINES,
  MIN_WRITING_LINES,
} from "./examWorkspaceWritingLines";

const FIELD = '[data-test="exam-workspace-writing-lines"]';
const MINUS = '[data-test="exam-workspace-writing-lines-minus"]';
const PLUS = '[data-test="exam-workspace-writing-lines-plus"]';
const APPLY_ALL = '[data-test="exam-workspace-writing-lines-apply-all"]';
const CONTROLS = [MINUS, PLUS, APPLY_ALL];
const LOCK_REASON_ID = "exam-workspace-writing-lines-lock-reason";
const LOCK_REASON_TEXT =
  "Frågan konverteras fortfarande. Texten från provfilen visas tills den är klar och går inte att ändra under tiden.";

function mountField(
  lines: number,
  options: { disabled?: boolean; allFreeTextMatch?: boolean; lockedReasonId?: string | null } = {},
) {
  return mount(ExamWorkspaceWritingLinesField, {
    props: {
      lines,
      disabled: options.disabled ?? false,
      allFreeTextMatch: options.allFreeTextMatch ?? false,
      lockedReasonId: options.lockedReasonId ?? null,
    },
  });
}

describe("ExamWorkspaceWritingLinesField", () => {
  it("names the writing area in rows", () => {
    expect(mountField(8).get(FIELD).text()).toContain("Skrivyta: 8 rader");
  });

  it("uses the singular for one row", () => {
    expect(mountField(1).get(FIELD).text()).toContain("Skrivyta: 1 rad");
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

  it("emits the current count to every free-text question", async () => {
    const wrapper = mountField(8);
    await wrapper.get(APPLY_ALL).trigger("click");

    expect(wrapper.emitted("applyToAll")).toEqual([[8]]);
  });

  it("disables apply-to-all when the free-text questions already match", () => {
    const match = mountField(8, { allFreeTextMatch: true });

    expect(match.get(APPLY_ALL).attributes("disabled")).toBeDefined();
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

  it("states the shared count on apply-to-all only while it matches", () => {
    const match = mountField(8, { allFreeTextMatch: true });

    expect(match.get(APPLY_ALL).attributes("title")).toBe("Alla fritextfrågor har redan 8 rader");
    expect(mountField(8).get(APPLY_ALL).attributes("title")).toBeUndefined();
  });

  it("adds no reason to a control that can act", () => {
    const wrapper = mountField(8);

    for (const control of CONTROLS) {
      expect(wrapper.get(control).attributes("title")).toBeUndefined();
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
