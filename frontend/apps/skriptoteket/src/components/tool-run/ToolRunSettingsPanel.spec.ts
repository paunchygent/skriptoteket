import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import ToolRunSettingsPanel from "./ToolRunSettingsPanel.vue";

function mountPanel(errorMessage: string | null) {
  return mount(ToolRunSettingsPanel, {
    props: {
      idBase: "settings",
      schema: [],
      modelValue: {},
      isLoading: false,
      isSaving: false,
      errorMessage,
    },
  });
}

describe("ToolRunSettingsPanel failure feedback", () => {
  it("preserves dismissal for a consumer that previously omitted dismissible", async () => {
    const wrapper = mountPanel("Inställningarna kunde inte sparas");
    const alert = wrapper.get('[role="alert"]');
    expect(alert.text()).toContain("Inställningarna kunde inte sparas");

    await alert.get('button[aria-label="Stäng"]').trigger("click");

    expect(wrapper.emitted("update:errorMessage")).toEqual([[null]]);
    // Visibility is parent-owned: forwarding the event must not discard the prop.
    expect(wrapper.get('[role="alert"]').text()).toContain("Inställningarna kunde inte sparas");
    await wrapper.setProps({ errorMessage: null });
    expect(wrapper.find('[role="alert"]').exists()).toBe(false);
    wrapper.unmount();
  });

  it("hides null and empty errors and shows subsequent text without remounting", async () => {
    const wrapper = mountPanel(null);
    expect(wrapper.find('[role="alert"]').exists()).toBe(false);

    await wrapper.setProps({ errorMessage: "Första felet" });
    expect(wrapper.get('[role="alert"]').text()).toContain("Första felet");

    await wrapper.setProps({ errorMessage: "" });
    expect(wrapper.find('[role="alert"]').exists()).toBe(false);

    await wrapper.setProps({ errorMessage: "Ett nytt fel" });
    expect(wrapper.get('[role="alert"]').text()).toContain("Ett nytt fel");

    await wrapper.setProps({ errorMessage: null });
    expect(wrapper.find('[role="alert"]').exists()).toBe(false);
    wrapper.unmount();
  });
});
