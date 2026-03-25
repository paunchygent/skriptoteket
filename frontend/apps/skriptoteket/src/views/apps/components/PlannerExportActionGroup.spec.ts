/**
 * Export action group tests.
 *
 * These tests keep the compact export affordance honest by focusing on the
 * behaviors it owns: starting the default export, exposing alternate export
 * choices, and blocking interaction while busy.
 */

import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import PlannerExportActionGroup from "./PlannerExportActionGroup.vue";

describe("PlannerExportActionGroup", () => {
  it("emits the default export action and alternate export selections", async () => {
    const wrapper = mount(PlannerExportActionGroup);

    await wrapper.get('[data-test="seating-export-default"]').trigger("click");
    expect(wrapper.emitted("export-default")).toEqual([[]]);

    await wrapper.get('[data-test="seating-export-menu-trigger"]').trigger("click");

    expect(wrapper.get('[data-test="seating-export-option-xlsx"]').text()).toContain(
      "Excel (.xlsx)",
    );

    await wrapper.get('[data-test="seating-export-option-xlsx"]').trigger("click");
    expect(wrapper.emitted("export-option")).toEqual([["xlsx"]]);
  });

  it("blocks export interactions while busy", async () => {
    const wrapper = mount(PlannerExportActionGroup, {
      props: {
        busy: true,
      },
    });

    expect(wrapper.get('[data-test="seating-export-default"]').attributes("disabled")).toBeDefined();
    expect(
      wrapper.get('[data-test="seating-export-menu-trigger"]').attributes("disabled"),
    ).toBeDefined();

    await wrapper.get('[data-test="seating-export-default"]').trigger("click");
    await wrapper.get('[data-test="seating-export-menu-trigger"]').trigger("click");

    expect(wrapper.emitted("export-default")).toBeUndefined();
    expect(wrapper.find('[data-test="seating-export-option-a3"]').exists()).toBe(false);
    expect(wrapper.emitted("export-option")).toBeUndefined();
  });
});
