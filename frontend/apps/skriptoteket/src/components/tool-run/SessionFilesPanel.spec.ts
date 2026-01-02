import { describe, expect, it } from "vitest";
import { mount } from "@vue/test-utils";

import SessionFilesPanel from "./SessionFilesPanel.vue";

describe("SessionFilesPanel", () => {
  it("renders empty and populated states", async () => {
    const wrapper = mount(SessionFilesPanel, {
      props: {
        files: [],
        mode: "none",
      },
    });

    expect(wrapper.text()).toContain("Inga sparade filer.");

    await wrapper.setProps({
      files: [{ name: "input.txt", bytes: 12 }],
    });

    expect(wrapper.text()).toContain("input.txt");
    expect(wrapper.text()).not.toContain("Inga sparade filer.");

    wrapper.unmount();
  });

  it("emits reuse/clear mode updates", async () => {
    const wrapper = mount(SessionFilesPanel, {
      props: {
        files: [],
        mode: "none",
      },
    });

    await wrapper.find('input[type="checkbox"]').trigger("change");
    await wrapper.find("button").trigger("click");

    const events = wrapper.emitted("update:mode") ?? [];
    expect(events[0]).toEqual(["reuse"]);
    expect(events[1]).toEqual(["clear"]);

    await wrapper.setProps({ mode: "clear" });
    expect(wrapper.text()).toContain("Rensar vid nästa körning.");

    wrapper.unmount();
  });

  it("disables controls when reuse/clear are unavailable", async () => {
    const wrapper = mount(SessionFilesPanel, {
      props: {
        files: [],
        mode: "none",
        canReuse: false,
        canClear: false,
        helperText: "Help text",
      },
    });

    const checkbox = wrapper.find('input[type="checkbox"]');
    const button = wrapper.find("button");

    expect(checkbox.attributes("disabled")).toBeDefined();
    expect(button.attributes("disabled")).toBeDefined();
    expect(wrapper.text()).toContain("Help text");

    await checkbox.trigger("change");
    await button.trigger("click");
    expect(wrapper.emitted("update:mode")).toBeUndefined();

    wrapper.unmount();
  });
});
