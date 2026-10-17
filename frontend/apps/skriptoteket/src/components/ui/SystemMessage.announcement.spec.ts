import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import { SystemMessage } from "./index";

describe("SystemMessage announcement defaults", () => {
  it("announces failure feedback as an assertive, atomic alert without consumer attributes", () => {
    const wrapper = mount(SystemMessage, {
      props: { tone: "failure", modelValue: "Det gick inte att spara." },
    });

    expect(wrapper.attributes("role")).toBe("alert");
    expect(wrapper.attributes("aria-live")).toBe("assertive");
    expect(wrapper.attributes("aria-atomic")).toBe("true");
    wrapper.unmount();
  });

  it.each(["info", "success", "warning"] as const)("keeps %s feedback as a status", (tone) => {
    const wrapper = mount(SystemMessage, { props: { tone, modelValue: "Meddelande" } });

    expect(wrapper.attributes("role")).toBe("status");
    expect(wrapper.attributes("aria-live")).toBeUndefined();
    expect(wrapper.attributes("aria-atomic")).toBeUndefined();
    wrapper.unmount();
  });

  it.each(["failure", "info", "success", "warning"] as const)("allows consumers to override %s announcement attributes", (tone) => {
    const wrapper = mount(SystemMessage, {
      props: { tone, modelValue: "Ett tidigare resultat." },
      attrs: { role: "status", "aria-live": "polite", "aria-atomic": "false" },
    });

    expect(wrapper.attributes("role")).toBe("status");
    expect(wrapper.attributes("aria-live")).toBe("polite");
    expect(wrapper.attributes("aria-atomic")).toBe("false");
    wrapper.unmount();
  });

  it("updates announcement semantics when the tone changes", async () => {
    const wrapper = mount(SystemMessage, { props: { tone: "info", modelValue: "Meddelande" } });

    await wrapper.setProps({ tone: "failure" });
    expect(wrapper.attributes("role")).toBe("alert");
    expect(wrapper.attributes("aria-live")).toBe("assertive");
    expect(wrapper.attributes("aria-atomic")).toBe("true");

    await wrapper.setProps({ tone: "success" });
    expect(wrapper.attributes("role")).toBe("status");
    expect(wrapper.attributes("aria-live")).toBeUndefined();
    expect(wrapper.attributes("aria-atomic")).toBeUndefined();
    wrapper.unmount();
  });
});
