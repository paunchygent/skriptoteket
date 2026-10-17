import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import ToolRunControlBar from "./ToolRunControlBar.vue";

describe("ToolRunControlBar shared actions", () => {
  it("blocks running without permission or while busy and permits retry after completion", async () => {
    const wrapper = mount(ToolRunControlBar, {
      props: {
        isRunning: false,
        hasResults: false,
        hasSettings: false,
        isSettingsOpen: false,
        canRun: false,
      },
    });
    const run = wrapper.get("button");

    expect(run.element.disabled).toBe(true);
    await run.trigger("click");
    expect(wrapper.emitted("run")).toBeUndefined();

    await wrapper.setProps({ canRun: true, isRunning: true });
    expect(run.element.disabled).toBe(true);
    expect(run.attributes("aria-busy")).toBe("true");
    await run.trigger("click");
    expect(wrapper.emitted("run")).toBeUndefined();

    await wrapper.setProps({ isRunning: false });
    await run.trigger("click");
    expect(wrapper.emitted("run")).toEqual([[]]);
    wrapper.unmount();
  });

  it("forwards settings and clear actions without also running the tool", async () => {
    const wrapper = mount(ToolRunControlBar, {
      props: {
        isRunning: false,
        hasResults: true,
        hasSettings: true,
        isSettingsOpen: false,
        canRun: true,
        density: "compact",
      },
    });
    const settings = wrapper.findAll("button").find((button) => button.text() === "Inställningar")!;
    const clear = wrapper.findAll("button").find((button) => button.text() === "Rensa")!;

    expect(settings.attributes("aria-expanded")).toBe("false");
    await settings.trigger("click");
    expect(wrapper.emitted("toggle-settings")).toEqual([[]]);
    await wrapper.setProps({ isSettingsOpen: true });
    expect(settings.attributes("aria-expanded")).toBe("true");

    await clear.trigger("click");
    expect(wrapper.emitted("clear")).toEqual([[]]);
    expect(wrapper.emitted("run")).toBeUndefined();
    wrapper.unmount();
  });
});
