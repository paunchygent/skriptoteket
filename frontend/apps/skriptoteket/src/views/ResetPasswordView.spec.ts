/**
 * Reset-password view tests.
 *
 * These tests verify token-driven rendering and the success/error transitions
 * for the emailed local-account password-reset flow.
 */

import { flushPromises, mount } from "@vue/test-utils";
import { nextTick, reactive } from "vue";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "../api/client";
import ResetPasswordView from "./ResetPasswordView.vue";

const routerMocks = vi.hoisted(() => ({
  route: null as { query: Record<string, unknown> } | null,
  auth: null as {
    clear: ReturnType<typeof vi.fn>;
  } | null,
}));

const apiPostMock = vi.fn();

vi.mock("vue-router", () => ({
  useRoute: () => routerMocks.route,
}));

vi.mock("../api/client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../api/client")>();
  return {
    ...actual,
    apiPost: (...args: unknown[]) => apiPostMock(...args),
  };
});

vi.mock("../stores/auth", () => ({
  useAuthStore: () => routerMocks.auth,
}));

describe("ResetPasswordView", () => {
  beforeEach(() => {
    apiPostMock.mockReset();
    routerMocks.route = reactive({
      query: reactive({ token: "reset-token-123" }) as Record<string, unknown>,
    });
    routerMocks.auth = reactive({
      clear: vi.fn(),
    });
  });

  it("shows an invalid state when the reset token is missing", () => {
    if (!routerMocks.route) {
      throw new Error("Expected route stub.");
    }
    routerMocks.route.query = reactive({});

    const wrapper = mount(ResetPasswordView, {
      global: {
        stubs: {
          RouterLink: {
            props: ["to"],
            template: "<a :href=\"typeof to === 'string' ? to : '#'\"><slot /></a>",
          },
        },
      },
    });

    expect(wrapper.text()).toContain("Ogiltig återställningslänk");
  });

  it("re-enters the form when a token appears after initial invalid state", async () => {
    if (!routerMocks.route) {
      throw new Error("Expected route stub.");
    }
    routerMocks.route.query = reactive({});

    const wrapper = mount(ResetPasswordView, {
      global: {
        stubs: {
          RouterLink: {
            props: ["to"],
            template: "<a :href=\"typeof to === 'string' ? to : '#'\"><slot /></a>",
          },
        },
      },
    });

    expect(wrapper.text()).toContain("Ogiltig återställningslänk");

    routerMocks.route.query.token = "fresh-reset-token";
    await nextTick();
    await flushPromises();

    expect(wrapper.find("form").exists()).toBe(true);
    await wrapper.get("#reset-password-new").setValue("new-password-123");
    expect((wrapper.get("#reset-password-new").element as HTMLInputElement).value).toBe(
      "new-password-123",
    );
  });

  it("submits the new password and clears client auth state on success", async () => {
    apiPostMock.mockResolvedValue({
      message: "Lösenordet har återställts. Logga in med ditt nya lösenord.",
    });

    const wrapper = mount(ResetPasswordView, {
      global: {
        stubs: {
          RouterLink: {
            props: ["to"],
            template: "<a :href=\"typeof to === 'string' ? to : '#'\"><slot /></a>",
          },
        },
      },
    });

    await wrapper.get("#reset-password-new").setValue("new-password-123");
    await wrapper.get("#reset-password-confirm").setValue("new-password-123");
    await wrapper.get("form").trigger("submit.prevent");
    await flushPromises();

    expect(apiPostMock).toHaveBeenCalledWith("/api/v1/auth/reset-password", {
      token: "reset-token-123",
      new_password: "new-password-123",
    });
    expect(routerMocks.auth?.clear).toHaveBeenCalled();
    expect(wrapper.text()).toContain("Lösenordet är uppdaterat");
  });

  it("renders the expired-token state when the backend rejects an expired reset token", async () => {
    apiPostMock.mockRejectedValue(
      new ApiError({
        code: "PASSWORD_RESET_TOKEN_EXPIRED",
        message: "Återställningslänken har gått ut.",
        status: 400,
      }),
    );

    const wrapper = mount(ResetPasswordView, {
      global: {
        stubs: {
          RouterLink: {
            props: ["to"],
            template: "<a :href=\"typeof to === 'string' ? to : '#'\"><slot /></a>",
          },
        },
      },
    });

    await wrapper.get("#reset-password-new").setValue("new-password-123");
    await wrapper.get("#reset-password-confirm").setValue("new-password-123");
    await wrapper.get("form").trigger("submit.prevent");
    await flushPromises();

    expect(wrapper.text()).toContain("Återställningslänken har gått ut");
  });
});
