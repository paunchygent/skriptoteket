import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import ToolFileFieldPicker from "./ToolFileFieldPicker.vue";

describe("ToolFileFieldPicker", () => {
  const field = {
    name: "attachments",
    label: "Bilagor",
    min: 0,
    max: 3,
  };

  it("removes only the chosen vault reference and respects read-only mode", async () => {
    const wrapper = mount(ToolFileFieldPicker, {
      props: {
        fields: [field],
        selections: {
          attachments: {
            mode: "refs",
            uploads: [],
            refs: ["vault:first", "vault:second"],
          },
        },
        acceptByField: {},
        errors: {},
        availableRefs: [
          { ref: "vault:first", name: "first.pdf", bytes: 10 },
          { ref: "vault:second", name: "second.pdf", bytes: 20 },
        ],
        isReadOnly: true,
      },
      global: { stubs: { VaultPickerModal: true } },
    });
    const remove = wrapper.findAll("button").find((button) => button.text() === "Ta bort")!;

    expect(remove.element.disabled).toBe(true);
    await remove.trigger("click");
    expect(wrapper.emitted("update:refs")).toBeUndefined();

    await wrapper.setProps({ isReadOnly: false });
    await remove.trigger("click");
    expect(wrapper.emitted("update:refs")).toEqual([
      [{ field: "attachments", refs: ["vault:second"] }],
    ]);
    wrapper.unmount();
  });

  it("keeps a keyed mode surface for upload and saved-file swaps", async () => {
    const wrapper = mount(ToolFileFieldPicker, {
      props: {
        fields: [field],
        selections: {
          attachments: {
            mode: "upload",
            uploads: [],
            refs: [],
          },
        },
        acceptByField: {},
        errors: {},
        availableRefs: [],
      },
      global: {
        stubs: {
          VaultPickerModal: true,
        },
      },
    });

    expect(wrapper.find('[data-test="tool-file-picker-mode-upload"]').exists()).toBe(true);

    await wrapper.setProps({
      selections: {
        attachments: {
          mode: "refs",
          uploads: [],
          refs: [],
        },
      },
    });

    expect(wrapper.find('[data-test="tool-file-picker-mode-refs"]').exists()).toBe(true);
  });
});
