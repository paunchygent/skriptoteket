import { describe, expect, it } from "vitest";
import { mount } from "@vue/test-utils";

import type { components } from "../../api/openapi";
import ToolRunActions from "./ToolRunActions.vue";

describe("ToolRunActions", () => {
  it("prefills shared fields from action.prefill", async () => {
    const actions = [
      {
        action_id: "confirm",
        label: "Confirm",
        kind: "form",
        fields: [
          { name: "notify", kind: "boolean", label: "Notify" },
          { name: "limit", kind: "integer", label: "Limit" },
        ],
        prefill: { notify: true, limit: 3 },
      },
    ] as components["schemas"]["UiFormAction"][];

    const wrapper = mount(ToolRunActions, {
      props: {
        actions,
        idBase: "test",
      },
      global: {
        stubs: {
          SystemMessage: {
            template: "<div />",
            props: ["modelValue", "variant"],
          },
          UiActionFieldRenderer: {
            template: "<div />",
            props: ["field", "idBase", "modelValue", "density"],
          },
        },
      },
    });

    await wrapper.find("button").trigger("click");

    const events = wrapper.emitted("submit") ?? [];
    expect(events[0]).toEqual([{ actionId: "confirm", input: { notify: true, limit: 3 } }]);

    wrapper.unmount();
  });
});
