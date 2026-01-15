import { describe, expect, it } from "vitest";
import { mount } from "@vue/test-utils";

import type { components } from "../../api/openapi";
import UiActionForm from "./UiActionForm.vue";

describe("UiActionForm", () => {
  it("prefills fields from action.prefill", async () => {
    const action = {
      action_id: "confirm",
      label: "Confirm",
      kind: "form",
      fields: [
        { name: "notify", kind: "boolean", label: "Notify" },
        { name: "limit", kind: "integer", label: "Limit" },
      ],
      prefill: { notify: true, limit: 3 },
    } as components["schemas"]["UiFormAction"];

    const wrapper = mount(UiActionForm, {
      props: {
        action,
        idBase: "test",
      },
      global: {
        stubs: {
          UiActionFieldRenderer: {
            template: "<div />",
            props: ["field", "idBase", "modelValue", "density"],
          },
        },
      },
    });

    await wrapper.find("form").trigger("submit");

    const events = wrapper.emitted("submit") ?? [];
    expect(events[0]).toEqual([{ actionId: "confirm", input: { notify: true, limit: 3 } }]);

    wrapper.unmount();
  });
});
