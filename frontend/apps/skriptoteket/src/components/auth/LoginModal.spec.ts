/**
 * Login modal tests.
 *
 * These tests keep the unauthenticated account-recovery entry point visible in
 * the same dialog that owns local-password sign-in.
 */

import { mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import LoginModal from "./LoginModal.vue";

const authState = vi.hoisted(() => ({
  status: "idle",
  login: vi.fn(),
}));

vi.mock("../../stores/auth", () => ({
  useAuthStore: () => authState,
}));

describe("LoginModal", () => {
  beforeEach(() => {
    authState.status = "idle";
    authState.login.mockReset();
  });

  it("links to forgot-password from the modal", () => {
    const wrapper = mount(LoginModal, {
      props: { isOpen: true },
      global: {
        stubs: {
          Teleport: true,
          RouterLink: {
            props: ["to"],
            template: "<a :href=\"typeof to === 'string' ? to : '#'\"><slot /></a>",
          },
        },
      },
    });

    expect(wrapper.text()).toContain("Glömt lösenord?");
    expect(wrapper.html()).toContain('href="/forgot-password"');
  });
});
