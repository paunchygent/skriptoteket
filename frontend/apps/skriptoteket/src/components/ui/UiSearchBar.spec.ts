import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import { UiDenseIconButton } from "./shared";
import UiSearchBar from "./UiSearchBar.vue";

describe("UiSearchBar", () => {
  it.each(["panel", "popover"] as const)("uses the shared icon-size search action in %s composition", (variant) => {
    const wrapper = mount(UiSearchBar, { props: { modelValue: "", variant } });
    const action = wrapper.getComponent(UiDenseIconButton);
    expect(action.props("size")).toBe("icon");
    const button = wrapper.get('button[aria-label="Sök"]');
    expect(button.classes()).toEqual(expect.arrayContaining(["h-9", "w-9"]));
    expect(button.classes()).not.toContain("border-l");
    wrapper.unmount();
  });

  it("preserves input updates, click and Enter submission, and the accessible name", async () => {
    const wrapper = mount(UiSearchBar, {
      props: { modelValue: "", ariaLabel: "Sök bland mina filer" },
    });
    const input = wrapper.get('input[type="search"]');
    await input.setValue("matematik");
    expect(wrapper.emitted("update:modelValue")).toEqual([["matematik"]]);
    const button = wrapper.get('button[aria-label="Sök bland mina filer"]');
    expect(button.attributes("type")).toBe("button");
    await button.trigger("click");
    await input.trigger("keydown", { key: "Enter" });
    expect(wrapper.emitted("submit")).toHaveLength(2);
    wrapper.unmount();
  });

  it.each(["disabled", "isBusy", "buttonDisabled"] as const)("blocks action clicks when %s", async (condition) => {
    const wrapper = mount(UiSearchBar, {
      props: { modelValue: "", [condition]: true },
    });
    const button = wrapper.get<HTMLButtonElement>('button[aria-label="Sök"]');
    expect(button.element.disabled).toBe(true);
    await button.trigger("click");
    expect(wrapper.emitted("submit")).toBeUndefined();
    wrapper.unmount();
  });

  it("omits the optional action without losing Enter submission", async () => {
    const wrapper = mount(UiSearchBar, { props: { modelValue: "", showButton: false } });
    expect(wrapper.find("button").exists()).toBe(false);
    await wrapper.get("input").trigger("keydown", { key: "Enter" });
    expect(wrapper.emitted("submit")).toHaveLength(1);
    wrapper.unmount();
  });
});
