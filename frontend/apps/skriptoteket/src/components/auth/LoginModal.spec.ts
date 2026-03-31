/**
 * Login modal tests.
 *
 * These tests keep both password-reset and resend-verification recovery paths
 * available from the same dialog that owns local-password sign-in.
 */

import { flushPromises, mount } from "@vue/test-utils";
import { createMemoryHistory, createRouter } from "vue-router";
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

  it("navigates to forgot-password without emitting close first", async () => {
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: "/", component: { template: "<div>home</div>" } },
        { path: "/forgot-password", component: { template: "<div>forgot</div>" } },
        { path: "/register", component: { template: "<div>register</div>" } },
      ],
    });
    await router.push("/");
    await router.isReady();

    const wrapper = mount(LoginModal, {
      props: { isOpen: true },
      global: {
        plugins: [router],
        stubs: {
          Teleport: true,
        },
      },
    });

    wrapper.get('a[href="/forgot-password"]').element.dispatchEvent(
      new MouseEvent("click", {
        bubbles: true,
        cancelable: true,
        button: 0,
      }),
    );
    await flushPromises();

    expect(router.currentRoute.value.fullPath).toBe("/forgot-password");
    expect(wrapper.emitted("close")).toBeUndefined();
  });

  it("keeps resend-verification available without a client cooldown after EMAIL_NOT_VERIFIED", async () => {
    authState.login.mockRejectedValue(
      new ApiError({
        code: "EMAIL_NOT_VERIFIED",
        message: "Verifiera din e-postadress innan du loggar in",
        status: 401,
      }),
    );
    apiPostMock
      .mockResolvedValueOnce({
        message: "Om kontot finns skickas ett nytt verifieringsmail",
      })
      .mockResolvedValueOnce({
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
    expect(wrapper.text()).not.toContain("Försök igen om");

    await wrapper.get("button.btn-secondary").trigger("click");
    await flushPromises();

    expect(apiPostMock).toHaveBeenNthCalledWith(2, "/api/v1/auth/resend-verification", {
      email: "olof.larsson@harryda.se",
    });
  });
});
