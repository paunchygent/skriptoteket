import { mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";

import { UiDenseIconButton } from "./shared";

describe("shared UiDenseIconButton touch contract", () => {
  it("gives the opt-in icon a 44px square target without losing its name, slot or click", async () => {
    const onClick = vi.fn();
    const wrapper = mount(UiDenseIconButton, {
      attrs: { onClick },
      props: { label: "Redigera regel", tone: "danger", size: "touch" },
      slots: { default: '<svg data-test="edit-icon" />' },
    });
    const button = wrapper.get("button");
    // jsdom has no layout: verify the Tailwind geometry contract, not a measured box.
    expect(button.classes()).toContain("h-[44px]");
    expect(button.classes()).toContain("w-[44px]");
    expect(button.classes()).not.toContain("h-9");
    expect(button.classes()).not.toContain("w-9");
    expect(button.attributes("aria-label")).toBe("Redigera regel");
    expect(button.attributes("title")).toBe("Redigera regel");
    expect(button.find('[data-test="edit-icon"]').exists()).toBe(true);
    await button.trigger("click");
    expect(onClick).toHaveBeenCalledTimes(1);
    wrapper.unmount();
  });

  it("keeps the touch icon disabled without dispatching clicks", async () => {
    const onClick = vi.fn();
    const wrapper = mount(UiDenseIconButton, {
      attrs: { onClick },
      props: { label: "Ta bort regel", disabled: true, size: "touch" },
    });
    expect(wrapper.get("button").element.disabled).toBe(true);
    expect(wrapper.get("button").attributes("aria-label")).toBe("Ta bort regel");
    await wrapper.get("button").trigger("click");
    expect(onClick).not.toHaveBeenCalled();
    wrapper.unmount();
  });

  it("keeps the default icon at 36px with the same accessible name", () => {
    const wrapper = mount(UiDenseIconButton, { props: { label: "Redigera" } });
    expect(wrapper.get("button").classes()).toEqual(expect.arrayContaining(["h-9", "w-9"]));
    expect(wrapper.get("button").attributes("aria-label")).toBe("Redigera");
    wrapper.unmount();
  });
});
