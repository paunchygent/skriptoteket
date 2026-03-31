/**
 * Segmented mode-switch tests.
 *
 * These tests keep the shared segmented control anchored to single-choice
 * radio semantics and arrow-key mode changes.
 */

import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import UiSegmentedToggle from "./UiSegmentedToggle.vue";

describe("UiSegmentedToggle", () => {
  it("renders as a radiogroup with one checked option", () => {
    const wrapper = mount(UiSegmentedToggle, {
      props: {
        modelValue: "seating",
        ariaLabel: "Välj läge",
        options: [
          { value: "overview", label: "Översikt" },
          { value: "seating", label: "Sittplatser" },
          { value: "rules", label: "Regler" },
        ],
      },
    });

    expect(wrapper.get('[role="radiogroup"]').attributes("aria-label")).toBe("Välj läge");
    expect(wrapper.get('[role="radio"][aria-checked="true"]').text()).toBe("Sittplatser");
  });

  it("moves selection with arrow keys", async () => {
    const wrapper = mount(UiSegmentedToggle, {
      props: {
        modelValue: "overview",
        options: [
          { value: "overview", label: "Översikt" },
          { value: "grouping", label: "Grupper" },
          { value: "rules", label: "Regler" },
        ],
      },
    });

    await wrapper.get('[role="radio"][aria-checked="true"]').trigger("keydown", { key: "ArrowRight" });
    expect(wrapper.emitted("update:modelValue")).toEqual([["grouping"]]);
  });

  it("forwards per-option test ids for secondary local rails", () => {
    const wrapper = mount(UiSegmentedToggle, {
      props: {
        modelValue: "newest",
        density: "compact",
        variant: "subrail",
        options: [
          { value: "newest", label: "Nyast", dataTest: "sort-newest" },
          { value: "name", label: "Namn", dataTest: "sort-name" },
        ],
      },
    });

    expect(wrapper.get('[data-test="sort-newest"]').attributes("aria-checked")).toBe("true");
    expect(wrapper.get('[data-test="sort-name"]').text()).toBe("Namn");
  });

  it("keeps one explicit column per option for auto-width local rails", () => {
    const wrapper = mount(UiSegmentedToggle, {
      props: {
        modelValue: "newest",
        density: "compact",
        variant: "subrail",
        width: "auto",
        options: [
          { value: "newest", label: "Nyast", dataTest: "sort-newest" },
          { value: "name", label: "Namn", dataTest: "sort-name" },
          { value: "size", label: "Storlek", dataTest: "sort-size" },
        ],
      },
    });

    expect(wrapper.attributes("style")).toContain("repeat(3, auto)");
    expect(wrapper.get('[data-test="sort-name"]').classes()).toContain("border-l");
    expect(wrapper.get('[data-test="sort-size"]').classes()).toContain("border-l");
    expect(wrapper.get('[data-test="sort-newest"]').classes()).toContain("h-[34px]");
  });

  it("supports the larger workspace variant for equal-weight mode selection", () => {
    const wrapper = mount(UiSegmentedToggle, {
      props: {
        modelValue: "overview",
        variant: "workspace",
        options: [
          { value: "overview", label: "Översikt", dataTest: "workspace-overview" },
          { value: "grouping", label: "Grupper", dataTest: "workspace-grouping" },
        ],
      },
    });

    expect(wrapper.get('[data-test="workspace-overview"]').classes()).toContain("uppercase");
    expect(wrapper.get('[data-test="workspace-overview"]').classes()).toContain("h-[40px]");
  });

  it("keeps disabled option guidance available beyond the disabled button title", () => {
    const wrapper = mount(UiSegmentedToggle, {
      props: {
        modelValue: "overview",
        variant: "workspace",
        options: [
          { value: "overview", label: "Översikt", dataTest: "workspace-overview" },
          {
            value: "grouping",
            label: "Grupper",
            disabled: true,
            title: "Skapa först en klasslista.",
            dataTest: "workspace-grouping",
          },
        ],
      },
    });

    const groupingButton = wrapper.get('[data-test="workspace-grouping"]');
    expect(groupingButton.attributes("disabled")).toBeDefined();
    expect(groupingButton.attributes("aria-describedby")).toBe("segmented-toggle-option-hint-1");
    expect(wrapper.find('[title="Skapa först en klasslista."]').exists()).toBe(true);
    expect(wrapper.get("#segmented-toggle-option-hint-1").text()).toBe("Skapa först en klasslista.");
  });
});
