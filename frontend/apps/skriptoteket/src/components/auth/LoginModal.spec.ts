/**
 * Login modal tests.
 *
 * These tests keep both password-reset and resend-verification recovery paths
 * available from the same dialog that owns local-password sign-in.
 */

import { flushPromises, mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import LoginModal from "./LoginModal.vue";
import { ApiError } from "../../api/client";

const authState = vi.hoisted(() => ({
  status: "idle",
  login: vi.fn(),
}));
const apiPostMock = vi.hoisted(() => vi.fn());

vi.mock("../../stores/auth", () => ({
  useAuthStore: () => authState,
}));

vi.mock("../../api/client", async () => {
  const actual = await vi.importActual<typeof import("../../api/client")>("../../api/client");
  return {
    ...actual,
    apiPost: (...args: unknown[]) => apiPostMock(...args),
  };
});

describe("LoginModal", () => {
  beforeEach(() => {
    authState.status = "idle";
    authState.login.mockReset();
    apiPostMock.mockReset();
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

  it("offers resend-verification when login fails because the email is not verified", async () => {
    authState.login.mockRejectedValue(
      new ApiError({
        code: "EMAIL_NOT_VERIFIED",
        message: "Verifiera din e-postadress innan du loggar in",
        status: 400,
      }),
    );
    apiPostMock.mockResolvedValue({
      message: "Om kontot finns skickas ett nytt verifieringsmail",
    });

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

    await wrapper.get("#modal-email").setValue("olof.larsson@harryda.se");
    await wrapper.get("#modal-password").setValue("hemligt-losenord");
    await wrapper.get("form").trigger("submit.prevent");
    await flushPromises();

    expect(wrapper.text()).toContain("Verifiera din e-postadress innan du loggar in");
    expect(wrapper.text()).toContain("Skicka nytt verifieringsmejl");

    await wrapper.get("button.btn-secondary").trigger("click");
    await flushPromises();

    expect(apiPostMock).toHaveBeenCalledWith("/api/v1/auth/resend-verification", {
      email: "olof.larsson@harryda.se",
    });
    expect(wrapper.text()).toContain("Om kontot finns skickas ett nytt verifieringsmail");
  });
});
