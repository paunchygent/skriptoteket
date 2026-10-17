import { mount } from "@vue/test-utils";
import { defineComponent, markRaw } from "vue";
import { describe, expect, it } from "vitest";

import CuratedAppHostSurface from "./CuratedAppHostSurface.vue";

const ViewStub = markRaw(defineComponent({
  props: { title: { type: String, default: "" } },
  template: '<main>{{ title }}</main>',
}));

function mountSurface(overrides = {}) {
  return mount(CuratedAppHostSurface, {
    props: {
      errorMessage: null,
      fallbackView: ViewStub,
      fallbackViewProps: { title: "Fallback content", "data-test": "fallback" },
      hostView: ViewStub,
      hostViewProps: { title: "Hosted content", "data-test": "host" },
      isLoading: false,
      shouldBlock: false,
      ...overrides,
    },
  });
}

describe("CuratedAppHostSurface", () => {
  it("announces loading before errors or blocked content, then exposes the error", async () => {
    const wrapper = mountSurface({
      isLoading: true,
      errorMessage: "Appen kunde inte öppnas",
      shouldBlock: true,
    });

    expect(wrapper.get('[role="status"]').text()).toBe("Laddar...");
    expect(wrapper.find('[role="alert"]').exists()).toBe(false);
    expect(wrapper.find("main").exists()).toBe(false);
    expect(wrapper.findAll('[role="status"]')).toHaveLength(1);

    await wrapper.setProps({ isLoading: false });
    const alert = wrapper.get('[role="alert"]');
    expect(alert.text()).toBe("Appen kunde inte öppnas");
    expect(alert.attributes("aria-live")).toBe("assertive");
    expect(alert.attributes("aria-atomic")).toBe("true");
    expect(wrapper.find("main").exists()).toBe(false);
  });

  it("announces the blocked state instead of mounting either app view", () => {
    const wrapper = mountSurface({ shouldBlock: true });
    expect(wrapper.get('[role="status"]').text()).toContain("anpassad vy");
    expect(wrapper.find("main").exists()).toBe(false);
    expect(wrapper.find('[role="alert"]').exists()).toBe(false);
  });

  it("mounts the selected host with its props after loading resolves", async () => {
    const wrapper = mountSurface({ isLoading: true });
    await wrapper.setProps({ isLoading: false });
    expect(wrapper.get('[data-test="host"]').text()).toBe("Hosted content");
    expect(wrapper.find('[data-test="fallback"]').exists()).toBe(false);
    expect(wrapper.find('[role="status"]').exists()).toBe(false);
  });

  it("uses the fallback props only when no bespoke host exists", () => {
    const wrapper = mountSurface({ hostView: null });
    expect(wrapper.get('[data-test="fallback"]').text()).toBe("Fallback content");
    expect(wrapper.find('[data-test="host"]').exists()).toBe(false);
  });
});
