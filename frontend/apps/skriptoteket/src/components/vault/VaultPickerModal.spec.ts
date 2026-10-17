import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import VaultPanel from "./VaultPanel.vue";
import VaultPickerModal from "./VaultPickerModal.vue";

function mountPicker() {
  return mount(VaultPickerModal, {
    props: { isOpen: true, title: "Välj underlag", selectedRefs: ["vault:original"], maxSelected: 3 },
    global: { stubs: { teleport: true, VaultPanel: true } },
  });
}

describe("VaultPickerModal", () => {
  it("names its dialog and icon close control", async () => {
    const wrapper = mountPicker();
    const dialog = wrapper.get('[role="dialog"]');
    const labelId = dialog.attributes("aria-labelledby");
    expect(labelId).toBeTruthy();
    expect(wrapper.get(`[id="${labelId}"]`).text()).toBe("Välj underlag");
    await wrapper.get('button[aria-label="Stäng"]').trigger("click");
    expect(wrapper.emitted("close")).toHaveLength(1);
    expect(wrapper.emitted("confirm")).toBeUndefined();
    wrapper.unmount();
  });

  it("cancels draft selection without mutating the caller and resets the draft on reopening", async () => {
    const wrapper = mountPicker();
    const original = wrapper.props("selectedRefs");
    wrapper.getComponent(VaultPanel).vm.$emit("update:model-value", ["vault:draft"]);
    await wrapper.findAll("button").find(button => button.text() === "Avbryt")!.trigger("click");
    expect(wrapper.emitted("confirm")).toBeUndefined();
    expect(original).toEqual(["vault:original"]);
    await wrapper.setProps({ isOpen: false });
    await wrapper.setProps({ isOpen: true, selectedRefs: ["vault:new-parent-selection"] });
    expect(wrapper.getComponent(VaultPanel).props("modelValue")).toEqual(["vault:new-parent-selection"]);
    await wrapper.findAll("button").find(button => button.text() === "Bekräfta")!.trigger("click");
    expect(wrapper.emitted("confirm")).toEqual([[["vault:new-parent-selection"]]]);
    wrapper.unmount();
  });

  it("blocks confirmation in read-only mode while still allowing cancellation", async () => {
    const wrapper = mountPicker();
    await wrapper.setProps({ isReadOnly: true });
    const confirm = wrapper.findAll("button").find(button => button.text() === "Bekräfta")!;
    expect((confirm.element as HTMLButtonElement).disabled).toBe(true);
    await confirm.trigger("click");
    expect(wrapper.emitted("confirm")).toBeUndefined();
    await wrapper.findAll("button").find(button => button.text() === "Avbryt")!.trigger("click");
    expect(wrapper.emitted("close")).toHaveLength(1);
    wrapper.unmount();
  });
});
