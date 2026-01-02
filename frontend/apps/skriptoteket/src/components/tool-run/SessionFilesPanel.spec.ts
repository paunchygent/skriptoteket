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
});
