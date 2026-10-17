import { mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";

import { denseActionButtonClass, UiDenseActionButton } from "./shared";

describe("shared UiDenseActionButton touch contract", () => {
  it("gives even a short text action a 44px minimum target and preserves its slot and event", async () => {
    const onClick = vi.fn();
    const wrapper = mount(UiDenseActionButton, {
      attrs: { onClick },
      props: { label: "OK", ariaLabel: "Spara regel", tone: "primary", size: "touch" },
      slots: { leading: '<svg data-test="save-icon" />' },
    });
    const button = wrapper.get("button");
    // jsdom cannot measure layout; these are the contracted Tailwind geometry classes.
    expect(button.classes()).toEqual(expect.arrayContaining(["h-[44px]", "min-w-[44px]"]));
    expect(button.classes()).not.toContain("h-[28px]");
    expect(button.text()).toBe("OK");
    expect(button.attributes("aria-label")).toBe("Spara regel");
    expect(button.find('[data-test="save-icon"]').exists()).toBe(true);
    await button.trigger("click");
    expect(onClick).toHaveBeenCalledTimes(1);
    wrapper.unmount();
  });

  it("keeps a touch action disabled and does not dispatch its click", async () => {
    const onClick = vi.fn();
    const wrapper = mount(UiDenseActionButton, {
      attrs: { onClick },
      props: { label: "Spara", disabled: true, size: "touch" },
    });
    expect(wrapper.get("button").element.disabled).toBe(true);
    await wrapper.get("button").trigger("click");
    expect(onClick).not.toHaveBeenCalled();
    wrapper.unmount();
  });

  it("exports touch geometry for both text and icon-only helper consumers", () => {
    for (const iconOnly of [false, true]) {
      const classes = denseActionButtonClass({ size: "touch", iconOnly }).split(/\s+/);
      expect(classes).toEqual(expect.arrayContaining(["h-[44px]", "min-w-[44px]"]));
      expect(classes).not.toContain("h-[28px]");
      expect(classes).not.toContain("h-9");
      if (iconOnly) expect(classes).toContain("w-[44px]");
    }
  });

  it("keeps the omitted size identical to the existing utility default", () => {
    const implicit = mount(UiDenseActionButton, { props: { label: "Spara" } });
    const explicit = mount(UiDenseActionButton, { props: { label: "Spara", size: "utility" } });
    expect(implicit.html()).toBe(explicit.html());
    expect(implicit.get("button").classes()).toContain("h-[28px]");
    expect(denseActionButtonClass()).toBe(denseActionButtonClass({ size: "utility" }));
    implicit.unmount();
    explicit.unmount();
  });
});
