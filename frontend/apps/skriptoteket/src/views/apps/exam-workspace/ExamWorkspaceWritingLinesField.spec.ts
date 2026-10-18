/**
 * Exam workspace Skrivyta field (TASK-SKRIPT-40-04-07, W4).
 *
 * Expected behavior:
 *   The field names the question's writing area in rows, the − / + stepper
 *   emits the next count, is bounded by the house range, and the
 *   "Använd för alla fritextfrågor" button emits the current count only while
 *   the free-text questions do not already share it. Every control is inert
 *   while the field is disabled.
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

function mountField(
  lines: number,
  options: { disabled?: boolean; allFreeTextMatch?: boolean } = {},
) {
  return mount(ExamWorkspaceWritingLinesField, {
    props: {
      lines,
      disabled: options.disabled ?? false,
      allFreeTextMatch: options.allFreeTextMatch ?? false,
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
});
