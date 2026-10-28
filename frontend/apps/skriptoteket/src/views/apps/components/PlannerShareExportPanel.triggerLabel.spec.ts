/**
 * Planner share/export trigger label tests.
 *
 * These tests lock TASK-SKRIPT-26-06-01 D1: the Klassrumskartan share trigger
 * reads `Dela länk` in every trigger variant the export menu renders, while the
 * panel heading keeps its own wording.
 */

import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import PlannerShareExportPanel from "./PlannerShareExportPanel.vue";

const TRIGGER_SELECTOR = '[data-test="planner-share-export-trigger"]';

describe("PlannerShareExportPanel trigger label", () => {
  it("labels the toolbar share trigger Dela länk", async () => {
    const wrapper = mount(PlannerShareExportPanel, {
      props: { triggerVariant: "toolbar" },
    });

    const trigger = wrapper.get(TRIGGER_SELECTOR);
    expect(trigger.text()).toBe("Dela länk");

    await trigger.trigger("click");
    expect(wrapper.get('[data-test="planner-share-export-panel"]').text()).toContain("Dela och exportera");
  });

  it("labels the menu-item share trigger Dela länk", () => {
    const wrapper = mount(PlannerShareExportPanel, {
      props: { triggerVariant: "menu-item" },
    });

    expect(wrapper.get(TRIGGER_SELECTOR).text()).toBe("Dela länk");
  });

  it("labels the phone-row share trigger Dela länk", () => {
    const wrapper = mount(PlannerShareExportPanel, {
      props: { triggerVariant: "phone-row" },
    });

    expect(wrapper.get(TRIGGER_SELECTOR).get("span").text()).toBe("Dela länk");
  });
});
