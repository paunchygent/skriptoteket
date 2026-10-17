import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import UiOutputNotice from "./UiOutputNotice.vue";

describe("UiOutputNotice shared feedback", () => {
  it("keeps a persisted error notice polite on initial render", () => {
    const wrapper = mount(UiOutputNotice, {
      props: {
        output: { kind: "notice", level: "error", message: "Underlaget kunde inte läsas." },
      },
    });

    const notice = wrapper.get('[data-ui="system-message"]');
    expect(notice.attributes("role")).toBe("status");
    expect(notice.attributes("aria-live")).toBe("polite");
    expect(notice.text()).toBe("Underlaget kunde inte läsas.");
    expect(wrapper.find('[role="alert"]').exists()).toBe(false);
    wrapper.unmount();
  });

  it("announces the current output and does not offer dismissal of run data", async () => {
    const wrapper = mount(UiOutputNotice, {
      props: {
        output: { kind: "notice", level: "warning", message: "Tre rader saknar värde." },
        density: "compact",
      },
    });

    expect(wrapper.get('[role="status"]').text()).toBe("Tre rader saknar värde.");
    expect(wrapper.find("button").exists()).toBe(false);

    await wrapper.setProps({
      output: { kind: "notice", level: "error", message: "Underlaget kunde inte läsas." },
    });
    expect(wrapper.get('[role="status"]').text()).toBe("Underlaget kunde inte läsas.");
    expect(wrapper.find("button").exists()).toBe(false);
    wrapper.unmount();
  });
});
