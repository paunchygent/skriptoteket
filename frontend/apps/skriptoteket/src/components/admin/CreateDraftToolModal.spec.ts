import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import CreateDraftToolModal from "./CreateDraftToolModal.vue";

function mountModal(isSubmitting = false) {
  return mount(CreateDraftToolModal, {
    props: {
      isOpen: true,
      title: "Mitt verktyg",
      summary: "",
      error: null,
      isSubmitting,
    },
    global: { stubs: { Teleport: true } },
  });
}

describe("CreateDraftToolModal close action", () => {
  it("closes without submitting through the named icon action", async () => {
    const wrapper = mountModal();

    await wrapper.get('button[aria-label="Stäng"]').trigger("click");

    expect(wrapper.emitted("close")).toEqual([[]]);
    expect(wrapper.emitted("submit")).toBeUndefined();
    wrapper.unmount();
  });

  it("blocks the close action while creating and restores it afterwards", async () => {
    const wrapper = mountModal(true);
    const close = wrapper.get('button[aria-label="Stäng"]');

    expect(close.attributes("disabled")).toBeDefined();
    await close.trigger("click");
    expect(wrapper.emitted("close")).toBeUndefined();

    await wrapper.setProps({ isSubmitting: false });
    const restoredClose = wrapper.get('button[aria-label="Stäng"]');
    expect(restoredClose.attributes("disabled")).toBeUndefined();
    await restoredClose.trigger("click");
    expect(wrapper.emitted("close")).toEqual([[]]);
    wrapper.unmount();
  });
});
