/**
 * Segmented tile toggle tests.
 *
 * Domain purpose:
 *   Lock shared icon-supported segmented tile behavior for curated app
 *   workspaces that need larger choice cards than the compact toggle.
 */

import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import { IconFileText } from "../icons";
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
            icon: IconFileText,
            dataTest: "separate",
          },
          {
            value: "combined",
            label: "Kombinerad PDF",
            icon: IconFileText,
            dataTest: "combined",
          },
        ],
      },
    });

    expect(wrapper.get('[role="radiogroup"]').attributes("aria-label")).toBe("Exportera som");
    expect(wrapper.get('[data-test="separate"]').attributes("aria-checked")).toBe("true");

    await wrapper.get('[data-test="combined"]').trigger("click");

    expect(wrapper.emitted("update:modelValue")).toEqual([["combined"]]);
  });
});
