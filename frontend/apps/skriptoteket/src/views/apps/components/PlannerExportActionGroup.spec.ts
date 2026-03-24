/**
 * Export action group tests.
 *
 * These tests keep the compact export affordance honest so the default action,
 * alternate menu, and download-again state do not regress into a flatter
 * format-button surface.
 */

import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import PlannerExportActionGroup from "./PlannerExportActionGroup.vue";

describe("PlannerExportActionGroup", () => {
  it("renders the compact export family with a default action and alternate menu", async () => {
    const wrapper = mount(PlannerExportActionGroup);

    expect(wrapper.text()).toContain("Export");
    expect(wrapper.get('[data-test="seating-export-default"]').text()).toContain("Exportera");

    await wrapper.get('[data-test="seating-export-default"]').trigger("click");
    expect(wrapper.emitted("export-default")).toEqual([[]]);

    await wrapper.get('[data-test="seating-export-menu-trigger"]').trigger("click");
    expect(wrapper.get('[data-test="seating-export-option-a3"]').text()).toContain("Affisch (A3)");
    expect(wrapper.get('[data-test="seating-export-option-a4"]').text()).toContain("Affisch (A4)");
    expect(wrapper.get('[data-test="seating-export-option-a3"]').text()).toContain("Standard");

    await wrapper.get('[data-test="seating-export-option-a4"]').trigger("click");
    expect(wrapper.emitted("export-option")).toEqual([["a4_landscape"]]);
  });

  it("shows compact status, error, and download-again affordances", async () => {
    const wrapper = mount(PlannerExportActionGroup, {
      props: {
        statusLabel: "PDF hämtad och sparad i Mina filer.",
        errorMessage: "PDF skapades men kunde inte laddas ned automatiskt.",
        canDownloadLatest: true,
      },
    });

    expect(wrapper.get('[data-test="seating-export-status"]').text()).toContain(
      "PDF hämtad och sparad i Mina filer.",
    );
    expect(wrapper.get('[data-test="seating-export-error"]').text()).toContain(
      "PDF skapades men kunde inte laddas ned automatiskt.",
    );
    expect(wrapper.get('[data-test="seating-export-download-latest"]').text()).toContain(
      "Ladda ned igen",
    );

    await wrapper.get('[data-test="seating-export-download-latest"]').trigger("click");
    expect(wrapper.emitted("download-latest")).toEqual([[]]);
  });
});
