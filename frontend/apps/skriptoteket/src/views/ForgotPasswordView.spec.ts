/**
 * Forgot-password view tests.
 *
 * These tests verify the public request screen keeps its generic-success
 * contract while redirecting authenticated users away from the anonymous flow.
 */

import { flushPromises, mount } from "@vue/test-utils";
import { reactive } from "vue";
import { beforeEach, describe, expect, it, vi } from "vitest";

import ForgotPasswordView from "./ForgotPasswordView.vue";

const routerMocks = vi.hoisted(() => ({
  router: {
    replace: vi.fn(),
  },
  auth: null as {
    isAuthenticated: boolean;
    bootstrap: ReturnType<typeof vi.fn>;
  } | null,
}));

const apiPostMock = vi.fn();

vi.mock("vue-router", () => ({
  useRouter: () => routerMocks.router,
}));

vi.mock("../api/client", () => ({
  apiPost: (...args: unknown[]) => apiPostMock(...args),
}));

vi.mock("../stores/auth", () => ({
  useAuthStore: () => routerMocks.auth,
}));

describe("ForgotPasswordView", () => {
  beforeEach(() => {
    routerMocks.router.replace.mockReset();
    apiPostMock.mockReset();
    routerMocks.auth = reactive({
      isAuthenticated: false,
      bootstrap: vi.fn().mockResolvedValue(undefined),
    });
  });

  it("submits the reset request and renders the generic success message", async () => {
    apiPostMock.mockResolvedValue({
      message: "Om kontot kan återställas skickas en återställningslänk.",
    });

    const wrapper = mount(ForgotPasswordView, {
      global: {
        stubs: {
          RouterLink: {
            props: ["to"],
            template: "<a :href=\"typeof to === 'string' ? to : '#'\"><slot /></a>",
          },
        },
      },
    });

    await wrapper.get("#forgot-password-email").setValue("teacher@example.com");
    await wrapper.get("form").trigger("submit.prevent");
    await flushPromises();

    expect(apiPostMock).toHaveBeenCalledWith("/api/v1/auth/forgot-password", {
      email: "teacher@example.com",
    });
    expect(wrapper.text()).toContain(
      "Om kontot kan återställas skickas en återställningslänk.",
    );
  });

  it("allows resend-verification for a different email in the same surface without cooldown drift", async () => {
    apiPostMock
      .mockResolvedValueOnce({
        message: "Om kontot kan återställas skickas en återställningslänk.",
      })
      .mockResolvedValueOnce({
        message: "Om kontot finns skickas ett nytt verifieringsmail",
      })
      .mockResolvedValueOnce({
        message: "Om kontot finns skickas ett nytt verifieringsmail",
      });

    const wrapper = mount(ForgotPasswordView, {
      global: {
        stubs: {
          RouterLink: {
            props: ["to"],
            template: "<a :href=\"typeof to === 'string' ? to : '#'\"><slot /></a>",
          },
        },
      },
    });

    await wrapper.get("#forgot-password-email").setValue("olof.larsson@harryda.se");
    await wrapper.get("form").trigger("submit.prevent");
    await flushPromises();

    expect(wrapper.text()).toContain("Inte verifierat än?");

    await wrapper.get("button[type='button']").trigger("click");
    await flushPromises();

    expect(apiPostMock).toHaveBeenNthCalledWith(2, "/api/v1/auth/resend-verification", {
      email: "olof.larsson@harryda.se",
    });
    expect(wrapper.text()).toContain("Om kontot finns skickas ett nytt verifieringsmail");
    expect(wrapper.text()).not.toContain("Försök igen om");

    await wrapper.get("#forgot-password-email").setValue("ada.lovelace@mail.harryda.se");
    await wrapper.get("button[type='button']").trigger("click");
    await flushPromises();

    expect(apiPostMock).toHaveBeenNthCalledWith(3, "/api/v1/auth/resend-verification", {
      email: "ada.lovelace@mail.harryda.se",
    });
  });

  it("redirects authenticated users away from the anonymous reset request route", async () => {
    if (!routerMocks.auth) {
      throw new Error("Expected auth store stub.");
    }
    routerMocks.auth.isAuthenticated = true;

    mount(ForgotPasswordView, {
      global: {
        stubs: {
          RouterLink: {
            props: ["to"],
            template: "<a :href=\"typeof to === 'string' ? to : '#'\"><slot /></a>",
          },
        },
      },
    });

    await flushPromises();

    expect(routerMocks.auth.bootstrap).toHaveBeenCalled();
    expect(routerMocks.router.replace).toHaveBeenCalledWith("/");
  });
});
