import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import type { ExamCourse } from "../../../api/examWorkspace";
import ExamCourseCombobox from "./ExamCourseCombobox.vue";

// Recorded Skolverket course names/codes, with GY25 subject + level composition.
const COURSES: ExamCourse[] = [
  { key: "gy11:SVESVE01", code: "SVESVE01", name: "Svenska 1", school_form: "gymnasiet", reform: "GY11", subject_code: "SVE", subject_name: "Svenska", points: 100 },
  { key: "gy11:SVESVE02", code: "SVESVE02", name: "Svenska 2", school_form: "gymnasiet", reform: "GY11", subject_code: "SVE", subject_name: "Svenska", points: 100 },
  { key: "gy25:SVEN2000X", code: "SVEN2000X", name: "Svenska nivå 2", school_form: "gymnasiet", reform: "GY25", subject_code: "SVEN", subject_name: "Svenska", points: 100 },
  { key: "gr:GRGRMAT01:7-9", code: "GRGRMAT01", name: "Matematik, åk 7–9", school_form: "grundskolan", subject_code: "GRGRMAT01", subject_name: "Matematik", year_band: "7-9", year_band_label: "åk 7–9" },
];

function mountPicker(overrides: Partial<{ modelValue: string | null; hint: string; disabled: boolean; courses: ExamCourse[] }> = {}) {
  return mount(ExamCourseCombobox, {
    props: { modelValue: null, courses: COURSES, inputId: "exam-course", ...overrides },
  });
}

describe("ExamCourseCombobox", () => {
  it("searches all query tokens and shows course identity without picking while typing", async () => {
    const wrapper = mountPicker();
    const input = wrapper.get('[role="combobox"]');
    await input.setValue("sve 2");
    const options = wrapper.findAll('[role="option"]');
    expect(options).toHaveLength(2);
    expect(options.map((option) => option.text()).join(" ")).toContain("Svenska nivå 2");
    expect(options.map((option) => option.text()).join(" ")).not.toContain("Svenska 1");
    const gy11 = options.find((option) => option.text().includes("SVESVE02"));
    expect(gy11?.text()).toContain("Svenska 2");
    expect(gy11?.text()).toContain("Gymnasiet GY11");
    expect(wrapper.emitted("update:modelValue")).toBeUndefined();
  });

  it("searches a course code and Enter emits the highlighted key with linked ARIA", async () => {
    const wrapper = mountPicker();
    const input = wrapper.get('[role="combobox"]');
    await input.setValue("svesve02");
    await input.trigger("keydown", { key: "ArrowDown" });
    expect(input.attributes("aria-expanded")).toBe("true");
    expect(wrapper.get('[role="listbox"]').attributes("id")).toBe(input.attributes("aria-controls"));
    const activeId = input.attributes("aria-activedescendant");
    expect(activeId).toBeTruthy();
    expect(wrapper.get(`[id="${activeId}"]`).attributes("role")).toBe("option");
    await input.trigger("keydown", { key: "Enter" });
    expect(wrapper.emitted("update:modelValue")).toEqual([["gy11:SVESVE02"]]);
    expect(input.attributes("aria-expanded")).toBe("false");
  });

  it("arrow navigation chooses the next option; Escape and Tab close without choosing", async () => {
    const wrapper = mountPicker();
    const input = wrapper.get('[role="combobox"]');
    await input.setValue("sve 2");
    await input.trigger("keydown", { key: "ArrowDown" });
    const first = input.attributes("aria-activedescendant");
    await input.trigger("keydown", { key: "ArrowDown" });
    expect(input.attributes("aria-activedescendant")).not.toBe(first);
    await input.trigger("keydown", { key: "ArrowUp" });
    expect(input.attributes("aria-activedescendant")).toBe(first);
    await input.trigger("keydown", { key: "Escape" });
    expect(input.attributes("aria-expanded")).toBe("false");
    await input.trigger("keydown", { key: "ArrowDown" });
    const tab = new KeyboardEvent("keydown", { key: "Tab", bubbles: true, cancelable: true });
    input.element.dispatchEvent(tab);
    await wrapper.vm.$nextTick();
    expect(tab.defaultPrevented).toBe(false);
    expect(input.attributes("aria-expanded")).toBe("false");
    expect(wrapper.emitted("update:modelValue")).toBeUndefined();
  });

  it("shows a selected course when closed, emits null on clear, and preserves the raw hint only when empty", async () => {
    const wrapper = mountPicker({ modelValue: "gy11:SVESVE02", hint: "Svenska kursavslutande" });
    expect((wrapper.get('[role="combobox"]').element as HTMLInputElement).value).toContain("Svenska 2");
    expect(wrapper.text()).not.toContain("Svenska kursavslutande");
    await wrapper.get('button[aria-label*="ensa"]').trigger("click");
    expect(wrapper.emitted("update:modelValue")).toEqual([[null]]);
    await wrapper.setProps({ modelValue: null });
    expect(wrapper.text()).toContain("Kursrad i dokumentet: Svenska kursavslutande");
  });

  it("accepts clicking an option, including a grundskolan year band", async () => {
    const wrapper = mountPicker();
    await wrapper.get('[role="combobox"]').setValue("åk 7-9");
    const option = wrapper.get('[role="option"]');
    expect(option.text()).toContain("Grundskolan");
    expect(option.text()).toContain("GRGRMAT01");
    await option.trigger("click");
    expect(wrapper.emitted("update:modelValue")).toEqual([["gr:GRGRMAT01:7-9"]]);
  });

  it("limits rendered matches and distinguishes too many results from no results", async () => {
    // Synthetic volume probe; the catalog normally holds thousands of entries.
    const courses = Array.from({ length: 60 }, (_, index) => ({
      ...COURSES[0]!, key: `course-${index}`, name: `Svenska ${index}`, code: `SV${index}`,
    }));
    const wrapper = mountPicker({ courses });
    const input = wrapper.get('[role="combobox"]');
    await input.setValue("sve");
    expect(wrapper.findAll('[role="option"]')).toHaveLength(50);
    expect(wrapper.get('[role="status"]').text()).toContain("Skriv mer");
    await input.setValue("ingenting");
    expect(wrapper.findAll('[role="option"]')).toHaveLength(0);
    expect(input.attributes("aria-activedescendant")).toBeUndefined();
    expect(wrapper.get('[role="status"]').text()).not.toContain("Skriv mer");
    await input.trigger("keydown", { key: "Enter" });
    expect(wrapper.emitted("update:modelValue")).toBeUndefined();
  });

  it("abandoning a search restores the selection and a later prop change updates its displayed name", async () => {
    const wrapper = mountPicker({ modelValue: "gy11:SVESVE02" });
    const input = wrapper.get('[role="combobox"]');
    await input.setValue("matematik");
    await input.trigger("keydown", { key: "Escape" });
    expect((input.element as HTMLInputElement).value).toBe("Svenska 2");
    await wrapper.setProps({ modelValue: "gy25:SVEN2000X" });
    expect((input.element as HTMLInputElement).value).toBe("Svenska nivå 2");
    expect(wrapper.emitted("update:modelValue")).toBeUndefined();
  });

  it("disabled input ignores synthetic typing and keyboard selection", async () => {
    const wrapper = mountPicker({ disabled: true });
    const input = wrapper.get('[role="combobox"]');
    expect(input.attributes("disabled")).toBeDefined();
    await input.setValue("sve 2");
    await input.trigger("keydown", { key: "ArrowDown" });
    await input.trigger("keydown", { key: "Enter" });
    expect(wrapper.find('[role="listbox"]').exists()).toBe(false);
    expect(wrapper.emitted("update:modelValue")).toBeUndefined();
  });
});
