import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import MaintainersDrawer from "./MaintainersDrawer.vue";

describe("MaintainersDrawer add-editor row", () => {
  it("keeps the e-mail field and its add button in one non-wrapping row", () => {
    const wrapper = mount(MaintainersDrawer, {
      props: {
        isOpen: true,
        maintainers: [],
        ownerUserId: null,
        isSuperuser: true,
        isLoading: false,
        isSaving: false,
        error: null,
      },
    });
    const input = wrapper.get("#maintainer-email");
    const row = input.element.parentElement!;
    const rowClasses = Array.from(row.classList);

    expect(rowClasses).toContain("flex-nowrap");
    expect(rowClasses).not.toContain("flex-col");
    expect(rowClasses).not.toContain("flex-wrap");
    expect(rowClasses.some((name) => name.startsWith("sm:flex"))).toBe(false);
    expect(input.classes()).toContain("min-w-0");
    expect(input.classes()).toContain("flex-1");
    expect(row.querySelector("button[type='submit']")?.textContent?.trim()).toBe("Lägg till");
    wrapper.unmount();
  });
});
