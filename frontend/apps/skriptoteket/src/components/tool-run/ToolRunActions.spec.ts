import { describe, expect, it } from "vitest";
import { mount } from "@vue/test-utils";

import type { components } from "../../api/openapi";
import ToolRunActions from "./ToolRunActions.vue";

describe("ToolRunActions", () => {
  function mountNumericAction(kind: "integer" | "number") {
    return mount(ToolRunActions, {
      props: {
        actions: [{
          action_id: "confirm", label: "Confirm", kind: "form",
          fields: [{ name: "amount", kind, label: "Amount" }],
        }],
        idBase: "numeric-action",
      },
      global: { stubs: { UiActionFieldRenderer: true } },
    });
  }

  it.each([
    ["integer", "1.5"], ["integer", "12junk"],
    ["number", "Infinity"], ["number", "-Infinity"], ["number", "1e309"],
    ["number", "12junk"], ["number", "1e"],
  ] as const)("rejects %s input %s and surfaces its conversion error", async (kind, raw) => {
    const wrapper = mountNumericAction(kind);
    wrapper.findComponent({ name: "UiActionFieldRenderer" }).vm.$emit("update:modelValue", raw);
    await wrapper.find("button").trigger("click");

    expect(wrapper.emitted("submit")).toBeUndefined();
    const errors = wrapper.emitted("update:errorMessage") ?? [];
    expect(errors.some(([message]) => typeof message === "string" && message.length > 0)).toBe(true);
    wrapper.unmount();
  });

  it.each(["integer", "number"] as const)("preserves exponent notation for %s input", async (kind) => {
    const wrapper = mountNumericAction(kind);
    wrapper.findComponent({ name: "UiActionFieldRenderer" }).vm.$emit("update:modelValue", "1e3");
    await wrapper.find("button").trigger("click");

    expect(wrapper.emitted("submit")).toEqual([[{
      actionId: "confirm", input: { amount: 1000 }, fileRefsByField: {},
    }]]);
    wrapper.unmount();
  });

  it("surfaces a conversion error even when parsing cannot produce any number", async () => {
    const wrapper = mountNumericAction("integer");
    wrapper.findComponent({ name: "UiActionFieldRenderer" }).vm.$emit("update:modelValue", "invalid");
    await wrapper.find("button").trigger("click");

    expect(wrapper.emitted("submit")).toBeUndefined();
    expect(wrapper.emitted("update:errorMessage")?.some(([message]) => Boolean(message))).toBe(true);
    wrapper.unmount();
  });

  it.each(["default", "compact"] as const)("prefills shared fields through the %s action button", async (density) => {
    const actions: components["schemas"]["UiFormAction"][] = [
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
    ];

    const wrapper = mount(ToolRunActions, {
      props: {
        actions,
        idBase: "test",
        density,
      },
      global: {
        stubs: {
          SystemMessage: {
            template: "<div />",
            props: ["modelValue", "tone"],
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
    expect(events[0]).toEqual([
      { actionId: "confirm", input: { notify: true, limit: 3 }, fileRefsByField: {} },
    ]);

    wrapper.unmount();
  });
});
