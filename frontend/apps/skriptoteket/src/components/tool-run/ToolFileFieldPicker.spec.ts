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
