/**
 * Provisioning-required view tests.
 *
 * These tests lock the deliberate missing-projection state so authenticated
 * users are not sent through the retired local browser auth ceremony again.
 */

import { mount, RouterLinkStub } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import AuthProvisioningRequiredView from "./AuthProvisioningRequiredView.vue";

describe("AuthProvisioningRequiredView", () => {
  it("explains that shared auth succeeded but Skriptoteket access is not active", () => {
    const wrapper = mount(AuthProvisioningRequiredView, {
      global: {
        stubs: {
          RouterLink: RouterLinkStub,
        },
      },
    });

    expect(wrapper.text()).toContain("Åtkomsten behöver aktiveras");
    expect(wrapper.text()).toContain("Du är inloggad");
    expect(wrapper.text()).toContain("ditt Skriptoteket-konto är ännu inte aktiverat");
    expect(wrapper.findComponent(RouterLinkStub).props("to")).toEqual({
      name: "auth-login",
    });
  });
});
