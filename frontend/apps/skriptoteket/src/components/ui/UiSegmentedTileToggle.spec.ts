/**
 * Segmented tile toggle tests.
 *
 * Domain purpose:
 *   Lock shared icon-supported segmented tile behavior for curated app
 *   workspaces that need larger choice cards than the compact toggle.
 */

import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import { IconCombinePdf, IconSeparatePdfs } from "../icons";
import UiSegmentedTileToggle from "./UiSegmentedTileToggle.vue";

describe("UiSegmentedTileToggle", () => {
  it("renders one selected radio option and emits the next value", async () => {
    const wrapper = mount(UiSegmentedTileToggle, {
      props: {
        modelValue: "separate",
        ariaLabel: "Exportera som",
        options: [
          {
            value: "separate",
            label: "Enskilda PDF-filer",
            icon: IconSeparatePdfs,
            dataTest: "separate",
          },
          {
            value: "combined",
            label: "Kombinerad PDF",
            icon: IconCombinePdf,
            dataTest: "combined",
          },
        ],
      },
    });

    expect(wrapper.get('[role="radiogroup"]').attributes("aria-label")).toBe("Exportera som");
    expect(wrapper.get('[data-test="separate"]').attributes("aria-checked")).toBe("true");
    for (const option of wrapper.findAll('[role="radio"]')) {
      expect(option.get("svg").attributes("aria-hidden")).toBe("true");
      expect(option.get("svg").attributes("aria-label")).toBeUndefined();
      expect(option.text()).not.toBe("");
    }

    await wrapper.get('[data-test="combined"]').trigger("click");
    expect(wrapper.emitted("update:modelValue")).toEqual([["combined"]]);
    await wrapper.setProps({ modelValue: "combined", disabled: true });
    expect(wrapper.get('[data-test="combined"]').attributes("aria-checked")).toBe("true");
    expect(wrapper.get('[data-test="separate"]').attributes("aria-checked")).toBe("false");
    await wrapper.get('[data-test="separate"]').trigger("click");
    expect(wrapper.emitted("update:modelValue")).toEqual([["combined"]]);
    wrapper.unmount();
  });
});
