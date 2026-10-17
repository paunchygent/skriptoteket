import { describe, expect, it } from "vitest";
import { mount } from "@vue/test-utils";

import type { components } from "../../api/openapi";
import UiActionForm from "./UiActionForm.vue";

describe("UiActionForm", () => {
  function mountNumericAction(kind: "integer" | "number") {
    return mount(UiActionForm, {
      props: {
        action: {
          action_id: "confirm", label: "Confirm", kind: "form",
          fields: [{ name: "amount", kind, label: "Amount" }],
        },
        idBase: "numeric-form",
      },
      global: { stubs: { UiActionFieldRenderer: true } },
    });
  }

  it.each([
    ["integer", "1.5"], ["integer", "12junk"],
    ["number", "Infinity"], ["number", "-Infinity"], ["number", "1e309"],
    ["number", "12junk"], ["number", "1e"],
  ] as const)("rejects %s input %s without submitting", async (kind, raw) => {
    const wrapper = mountNumericAction(kind);
    wrapper.findComponent({ name: "UiActionFieldRenderer" }).vm.$emit("update:modelValue", raw);
    await wrapper.find("form").trigger("submit");

    expect(wrapper.emitted("submit")).toBeUndefined();
    expect(wrapper.text()).toContain(kind === "integer" ? "Ogiltigt heltal" : "Ogiltigt tal");
    wrapper.unmount();
  });

  it.each(["integer", "number"] as const)("preserves exponent notation for %s input", async (kind) => {
    const wrapper = mountNumericAction(kind);
    wrapper.findComponent({ name: "UiActionFieldRenderer" }).vm.$emit("update:modelValue", "1e3");
    await wrapper.find("form").trigger("submit");

    expect(wrapper.emitted("submit")).toEqual([[{
      actionId: "confirm", input: { amount: 1000 }, fileRefsByField: {},
    }]]);
    wrapper.unmount();
  });

  it("prefills fields from action.prefill", async () => {
    const action: components["schemas"]["UiFormAction"] = {
      action_id: "confirm",
      label: "Confirm",
      kind: "form",
      fields: [
        { name: "notify", kind: "boolean", label: "Notify" },
        { name: "limit", kind: "integer", label: "Limit" },
      ],
      prefill: { notify: true, limit: 3 },
    };

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
    expect(events[0]).toEqual([
      { actionId: "confirm", input: { notify: true, limit: 3 }, fileRefsByField: {} },
    ]);

    wrapper.unmount();
  });
});
