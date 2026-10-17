import { mount } from "@vue/test-utils";
import { nextTick } from "vue";
import { afterEach, describe, expect, it } from "vitest";

import ReagentPrepChefSettingsPopover from "./ReagentPrepChefSettingsPopover.vue";

const props = {
  canCalculate: true,
  isDefaultsSaving: false,
  isDefaultsLoading: false,
  defaults: null,
  isSavingDefaultsToVault: false,
  isLoadingDefaultsFromVault: false,
  lastSavedDefaultsVaultRef: null,
};

const wrappers: ReturnType<typeof mount>[] = [];

afterEach(() => {
  wrappers.forEach((wrapper) => wrapper.unmount());
  wrappers.length = 0;
  document.body.replaceChildren();
});

describe("ReagentPrepChefSettingsPopover", () => {
  it("keeps clicks inside the shared trigger and popover distinct from outside dismissal", async () => {
    const wrapper = mount(ReagentPrepChefSettingsPopover, { props, attachTo: document.body });
    wrappers.push(wrapper);
    const trigger = wrapper.get('button[aria-controls="rpc-settings-popover"]');

    await trigger.get("svg").trigger("click");
    expect(trigger.attributes("aria-expanded")).toBe("true");
    expect(wrapper.get('[role="dialog"]').attributes("aria-modal")).toBe("false");

    const save = wrapper.findAll("button").find((button) => button.text() === "Spara som standard")!;
    await save.trigger("click");
    expect(wrapper.emitted("saveDefaults")).toHaveLength(1);
    expect(wrapper.find('[role="dialog"]').exists()).toBe(true);

    await trigger.get("svg").trigger("click");
    expect(trigger.attributes("aria-expanded")).toBe("false");
    expect(wrapper.find('[role="dialog"]').exists()).toBe(false);

    await trigger.trigger("click");
    document.body.click();
    await nextTick();
    expect(wrapper.find('[role="dialog"]').exists()).toBe(false);
  });

  it("forwards the shared close button and preserves Escape dismissal", async () => {
    const wrapper = mount(ReagentPrepChefSettingsPopover, { props, attachTo: document.body });
    wrappers.push(wrapper);
    const trigger = wrapper.get('button[aria-controls="rpc-settings-popover"]');

    await trigger.trigger("click");
    await wrapper.get('button[aria-label="Stäng inställningar"]').trigger("click");
    expect(trigger.attributes("aria-expanded")).toBe("false");
    expect(wrapper.find('[role="dialog"]').exists()).toBe(false);

    await trigger.trigger("click");
    document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
    await nextTick();
    expect(wrapper.find('[role="dialog"]').exists()).toBe(false);
    expect(wrapper.emitted("saveDefaults")).toBeUndefined();
  });
});
