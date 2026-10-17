import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import LoginEventsPanel from "./LoginEventsPanel.vue";

describe("LoginEventsPanel error feedback", () => {
  it("announces a load failure and removes the alert when loading succeeds", async () => {
    const wrapper = mount(LoginEventsPanel, {
      props: { events: [], isLoading: false, errorMessage: "Händelserna kunde inte hämtas" },
    });

    expect(wrapper.get('[role="alert"]').text()).toContain("Händelserna kunde inte hämtas");
    expect(wrapper.find("table").exists()).toBe(false);

    await wrapper.setProps({ errorMessage: null });
    expect(wrapper.find('[role="alert"]').exists()).toBe(false);
    expect(wrapper.text()).toContain("Inga händelser hittades.");
    wrapper.unmount();
  });
});
