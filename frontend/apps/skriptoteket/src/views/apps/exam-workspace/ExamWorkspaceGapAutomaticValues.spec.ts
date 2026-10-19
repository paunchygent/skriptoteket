/**
 * Exam workspace gap automatic answers.
 *
 * Expected behavior:
 *   Each answer the conversion wrote for the gap shows as a chip marked
 *   "automatisk" with a remove control. Removing one emits the value;
 *   while disabled every remove control is disabled and nothing emits.
 *   A gap without automatic answers shows no section (the owner keeps the
 *   v-if, so the component is never mounted empty).
 */

import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import ExamWorkspaceGapAutomaticValues from "./ExamWorkspaceGapAutomaticValues.vue";

function mountValues(values: string[], disabled = false) {
  return mount(ExamWorkspaceGapAutomaticValues, {
    attachTo: document.body,
    props: { values, disabled },
  });
}

describe("ExamWorkspaceGapAutomaticValues", () => {
  it("renders a chip per value, marked automatisk and without an AI glyph", () => {
    const wrapper = mountValues(["hundraa", "hundar"]);

    const chips = wrapper.findAll('[data-test="exam-workspace-gap-automatic-values"] li');
    expect(chips).toHaveLength(2);
    expect(chips[0]?.text()).toContain("hundraa");
    expect(chips[0]?.text()).toContain("automatisk");
    expect(chips[1]?.text()).toContain("hundar");
    expect(wrapper.html()).not.toContain("lucide-sparkles");
    wrapper.unmount();
  });

  it("emits the removed value on remove", async () => {
    const wrapper = mountValues(["hundraa", "hundar"]);

    await wrapper
      .get('[data-test="exam-workspace-gap-automatic-remove-hundraa"]')
      .trigger("click");

    expect(wrapper.emitted("remove")).toEqual([["hundraa"]]);
    wrapper.unmount();
  });

  it("disables every remove control and emits nothing while disabled", async () => {
    const wrapper = mountValues(["hundraa"], true);

    expect(
      wrapper.get('[data-test="exam-workspace-gap-automatic-remove-hundraa"]').attributes("disabled"),
    ).toBeDefined();
    await wrapper
      .get('[data-test="exam-workspace-gap-automatic-remove-hundraa"]')
      .trigger("click");
    expect(wrapper.emitted("remove")).toBeUndefined();
    wrapper.unmount();
  });
});
