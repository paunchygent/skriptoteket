import { RouterLinkStub, mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import UnavailableAppView from "./UnavailableAppView.vue";

describe("UnavailableAppView", () => {
  it("shows the shared unavailable message and a route back home", () => {
    const wrapper = mount(UnavailableAppView, {
      props: { appTitle: "Ljudtranskribering" },
      global: {
        stubs: { RouterLink: RouterLinkStub },
      },
    });

    expect(wrapper.get('[role="status"]').text()).toContain(
      "Ljudtranskribering är inte tillgänglig för närvarande.",
    );
    expect(wrapper.getComponent(RouterLinkStub).props("to")).toBe("/");
  });
});
