import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import AuthPasswordField from "./AuthPasswordField.vue";

function mountField(overrides = {}) {
  return mount(AuthPasswordField, {
    props: {
      id: "account-password",
      label: "Lösenord",
      modelValue: "private-value",
      ...overrides,
    },
  });
}

describe("AuthPasswordField", () => {
  it("toggles visibility without changing the password or submitting its form", async () => {
    const wrapper = mountField();
    const input = wrapper.get("input");
    const button = wrapper.get("button");
    expect(wrapper.get("label").attributes("for")).toBe(input.attributes("id"));
    expect(input.attributes("type")).toBe("password");
    expect(button.attributes("aria-label")).toBe("Visa lösenord");
    expect(button.attributes("title")).toBe("Visa lösenord");
    expect(button.attributes("type")).toBe("button");

    await button.trigger("click");
    expect(wrapper.get("input").element).toBe(input.element);
    expect(input.attributes("type")).toBe("text");
    expect(input.element.value).toBe("private-value");
    expect(button.attributes("aria-label")).toBe("Dölj lösenord");
    expect(button.attributes("title")).toBe("Dölj lösenord");
    expect(wrapper.emitted("update:modelValue")).toBeUndefined();

    await button.trigger("click");
    expect(input.attributes("type")).toBe("password");
    await input.setValue("new-private-value");
    expect(wrapper.emitted("update:modelValue")).toEqual([["new-private-value"]]);
  });

  it("does not reveal a disabled password", async () => {
    const wrapper = mountField({ disabled: true });
    expect(wrapper.get("input").attributes("disabled")).toBeDefined();
    expect(wrapper.get("button").attributes("disabled")).toBeDefined();
    await wrapper.get("button").trigger("click");
    expect(wrapper.get("input").attributes("type")).toBe("password");
  });

  it("associates validation errors instead of the hint, then clears stale descriptions", async () => {
    const wrapper = mountField({ hint: "Password hint", error: "Password rejected", required: true });
    const input = wrapper.get("input");
    expect(input.attributes("required")).toBeDefined();
    expect(input.attributes("autocomplete")).toBe("current-password");
    expect(input.attributes("aria-invalid")).toBe("true");
    expect(wrapper.get(`#${input.attributes("aria-describedby")}`).text()).toBe("Password rejected");
    expect(wrapper.text()).not.toContain("Password hint");

    await wrapper.setProps({ error: null });
    expect(input.attributes("aria-invalid")).toBe("false");
    expect(wrapper.get(`#${input.attributes("aria-describedby")}`).text()).toBe("Password hint");
    await wrapper.setProps({ hint: null });
    expect(input.attributes("aria-describedby")).toBeUndefined();
    expect(wrapper.find("p").exists()).toBe(false);
  });
});
