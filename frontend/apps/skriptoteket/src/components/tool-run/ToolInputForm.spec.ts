import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import type { components } from "../../api/openapi";
import ToolInputForm from "./ToolInputForm.vue";

type Field = NonNullable<components["schemas"]["ToolMetadataResponse"]["input_schema"]>[number];

const fields: Field[] = [
  { name: "count", kind: "integer", label: "Antal" },
  { name: "amount", kind: "number", label: "Mängd" },
  { name: "title", kind: "string", label: "Titel" },
  { name: "body", kind: "text", label: "Text" },
  { name: "choice", kind: "enum", label: "Val", options: [{ value: "a", label: "A" }] },
  { name: "enabled", kind: "boolean", label: "Aktiverad" },
];

describe("ToolInputForm field errors", () => {
  it.each(fields)("links the $kind control to its own error and clears invalid state after correction", async (field) => {
    const message = field.kind === "integer" ? "Ogiltigt heltal." : "Kontrollera värdet.";
    const wrapper = mount(ToolInputForm, {
      props: {
        idBase: "runner",
        fields,
        modelValue: {},
        errors: { [field.name]: message },
      },
    });

    const control = wrapper.get(`#runner-input-${field.name}`);
    expect(control.attributes("aria-invalid")).toBe("true");
    const describedBy = control.attributes("aria-describedby");
    expect(describedBy).toBeTruthy();
    const error = wrapper.findAll("[id]").find((node) => node.attributes("id") === describedBy);
    expect(error?.text()).toBe(message);
    for (const other of fields.filter((item) => item.name !== field.name)) {
      expect(wrapper.get(`#runner-input-${other.name}`).attributes("aria-invalid")).not.toBe("true");
      expect(wrapper.get(`#runner-input-${other.name}`).attributes("aria-describedby")).toBeUndefined();
    }

    await wrapper.setProps({ errors: {} });
    expect(control.attributes("aria-invalid")).not.toBe("true");
    expect(control.attributes("aria-describedby")).toBeUndefined();
    expect(wrapper.text()).not.toContain(message);
    wrapper.unmount();
  });

  it("gives errors distinct targets when the same field appears in two runner forms", () => {
    const wrappers = ["first", "second"].map((idBase) => mount(ToolInputForm, {
      props: {
        idBase,
        fields: [fields[0]],
        modelValue: { count: "1.5" },
        errors: { count: "Ogiltigt heltal." },
      },
    }));
    const targets = wrappers.map((wrapper) => wrapper.get("input").attributes("aria-describedby"));
    expect(targets.every(Boolean)).toBe(true);
    expect(new Set(targets).size).toBe(2);
    wrappers.forEach((wrapper) => wrapper.unmount());
  });
});
