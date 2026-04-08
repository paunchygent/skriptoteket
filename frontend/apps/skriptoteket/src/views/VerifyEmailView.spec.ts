/**
 * Verify-email view tests.
 *
 * These tests keep the success countdown aligned with the page-based auth-entry
 * contract so verification completion does not drop the preserved destination.
 */

import { RouterLinkStub, flushPromises, mount } from "@vue/test-utils";
import { reactive } from "vue";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "../api/client";
import VerifyEmailView from "./VerifyEmailView.vue";

const verifyViewMocks = vi.hoisted(() => ({
  route: null as { query: Record<string, unknown> } | null,
  router: {
    push: vi.fn().mockResolvedValue(undefined),
  },
}));

const apiPostMock = vi.fn();

vi.mock("vue-router", () => ({
  useRoute: () => verifyViewMocks.route,
  useRouter: () => verifyViewMocks.router,
}));

vi.mock("../api/client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../api/client")>();
  return {
    ...actual,
    apiPost: (...args: unknown[]) => apiPostMock(...args),
  };
});

describe("VerifyEmailView", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    apiPostMock.mockReset();
    verifyViewMocks.router.push.mockReset();
    verifyViewMocks.router.push.mockResolvedValue(undefined);
    verifyViewMocks.route = reactive({
      query: reactive({
        token: "verify-token-123",
        next: "/browse",
      }) as Record<string, unknown>,
    });
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("routes the success countdown through auth-login without dropping next", async () => {
    apiPostMock.mockResolvedValue({
      message: "Kontot är verifierat.",
    });

    const wrapper = mount(VerifyEmailView, {
      global: {
        stubs: {
          RouterLink: RouterLinkStub,
        },
      },
    });
    await flushPromises();

    await vi.advanceTimersByTimeAsync(5000);
    await flushPromises();

    expect(verifyViewMocks.router.push).toHaveBeenCalledWith({
      name: "auth-login",
      query: { next: "/browse" },
    });

    wrapper.unmount();
  });

  it("preserves classroom planner origin through verification success and resend", async () => {
    if (!verifyViewMocks.route) {
      throw new Error("Expected route stub.");
    }
    verifyViewMocks.route.query = reactive({
      token: "verify-token-123",
      next: "/apps/classroom.group-seating-studio",
      classroomPlannerEntryOrigin: "dashboard",
    }) as Record<string, unknown>;

    apiPostMock
      .mockRejectedValueOnce(
        new ApiError({
          code: "VERIFICATION_TOKEN_EXPIRED",
          details: { email: "teacher@example.com" },
          message: "Länken har gått ut.",
          status: 400,
        }),
      )
      .mockResolvedValueOnce({
        message: "Om kontot finns skickas ett nytt verifieringsmail",
      });

    const wrapper = mount(VerifyEmailView, {
      global: {
        stubs: {
          RouterLink: RouterLinkStub,
        },
      },
    });
    await flushPromises();

    await wrapper.get("button.btn-cta").trigger("click");
    await flushPromises();

    expect(apiPostMock).toHaveBeenNthCalledWith(2, "/api/v1/auth/resend-verification", {
      email: "teacher@example.com",
      next: "/apps/classroom.group-seating-studio",
      classroom_planner_entry_origin: "dashboard",
    });

    wrapper.unmount();
  });
});
