/**
 * Dense split button tests.
 *
 * These tests freeze the shared split-button contract around default actions,
 * disclosure-menu behavior, and keyboard navigation.
 */

import { mount } from "@vue/test-utils";
import { nextTick } from "vue";
import { describe, expect, it } from "vitest";

import UiDenseSplitButton from "./UiDenseSplitButton.vue";

describe("UiDenseSplitButton", () => {
  it("emits the main action and alternate menu selections", async () => {
    const wrapper = mount(UiDenseSplitButton, {
      props: {
        label: "Exportera",
        menuLabel: "Fler exportval",
        rootTestId: "split-root",
        mainButtonTestId: "split-main",
        menuTriggerTestId: "split-menu",
        itemTestIdPrefix: "split-item",
        items: [
          { id: "pdf", label: "PDF", metaLabel: "Standard" },
          { id: "xlsx", label: "Excel" },
        ],
      },
    });

    await wrapper.get('[data-test="split-main"]').trigger("click");
    expect(wrapper.emitted("trigger")).toEqual([[]]);

    await wrapper.get('[data-test="split-menu"]').trigger("click");
    await wrapper.get('[data-test="split-item-xlsx"]').trigger("click");

    expect(wrapper.emitted("select")).toEqual([["xlsx"]]);
  });

  it("opens with ArrowDown and moves focus with menu keys", async () => {
    const wrapper = mount(UiDenseSplitButton, {
      attachTo: document.body,
      props: {
        label: "Exportera",
        menuLabel: "Fler exportval",
        menuTriggerTestId: "split-menu",
        itemTestIdPrefix: "split-item",
        items: [
          { id: "pdf", label: "PDF" },
          { id: "xlsx", label: "Excel" },
          { id: "csv", label: "CSV" },
        ],
      },
    });

    await wrapper.get('[data-test="split-menu"]').trigger("keydown", { key: "ArrowDown" });
    await nextTick();
    expect(document.activeElement?.getAttribute("data-test")).toBe("split-item-pdf");

    await wrapper.get('[role="menu"]').trigger("keydown", { key: "End" });
    expect(document.activeElement?.getAttribute("data-test")).toBe("split-item-csv");

    await wrapper.get('[role="menu"]').trigger("keydown", { key: "Escape" });
    await nextTick();
    expect(document.activeElement?.getAttribute("data-test")).toBe("split-menu");

    wrapper.unmount();
  });
});
