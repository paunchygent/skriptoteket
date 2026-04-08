/**
 * Auth-login panel tests.
 *
 * These tests keep the page-based login form aligned with the local auth and
 * recovery contract used by the dedicated `/auth/login` route.
 */

import { RouterLinkStub, flushPromises, mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "../../api/client";
import AuthLoginPanel from "./AuthLoginPanel.vue";

const authState = vi.hoisted(() => ({
  status: "idle",
  login: vi.fn(),
}));
const apiPostMock = vi.hoisted(() => vi.fn());
const routeState = vi.hoisted(() => ({
  query: {} as Record<string, unknown>,
}));

vi.mock("../../stores/auth", () => ({
  useAuthStore: () => authState,
}));

vi.mock("vue-router", async (importOriginal) => {
  const actual = await importOriginal<typeof import("vue-router")>();
  return {
    ...actual,
    useRoute: () => routeState,
  };
});

vi.mock("../../api/client", async () => {
  const actual = await vi.importActual<typeof import("../../api/client")>("../../api/client");
  return {
    ...actual,
    apiPost: (...args: unknown[]) => apiPostMock(...args),
  };
});

describe("AuthLoginPanel", () => {
  beforeEach(() => {
    authState.status = "idle";
    authState.login.mockReset();
    apiPostMock.mockReset();
    routeState.query = {};
  });

  it("preserves next when the user detours from auth-login to forgot-password", async () => {
    routeState.query = { next: "/browse" };
    const wrapper = mount(AuthLoginPanel, {
      global: {
        stubs: {
          RouterLink: RouterLinkStub,
        },
      },
    });

    const [forgotPasswordLink] = wrapper.findAllComponents(RouterLinkStub);
    expect(forgotPasswordLink.props("to")).toEqual({
      name: "forgot-password",
      query: { next: "/browse" },
    });
  });

  it("preserves next when the user detours from auth-login to register", async () => {
    routeState.query = { next: "/browse" };
    const wrapper = mount(AuthLoginPanel, {
      global: {
        stubs: {
          RouterLink: RouterLinkStub,
        },
      },
    });

    const [, registerLink] = wrapper.findAllComponents(RouterLinkStub);
    expect(registerLink.props("to")).toEqual({
      name: "register",
      query: { next: "/browse" },
    });
  });

  it("preserves classroom planner origin across auth detours", async () => {
    routeState.query = {
      next: "/apps/classroom.group-seating-studio",
      classroomPlannerEntryOrigin: "dashboard",
    };

    const wrapper = mount(AuthLoginPanel, {
      global: {
        stubs: {
          RouterLink: RouterLinkStub,
        },
      },
    });

    const [forgotPasswordLink, registerLink] = wrapper.findAllComponents(RouterLinkStub);

    expect(forgotPasswordLink.props("to")).toEqual({
      name: "forgot-password",
      query: {
        next: "/apps/classroom.group-seating-studio",
        classroomPlannerEntryOrigin: "dashboard",
      },
    });
    expect(registerLink.props("to")).toEqual({
      name: "register",
      query: {
        next: "/apps/classroom.group-seating-studio",
        classroomPlannerEntryOrigin: "dashboard",
      },
    });
  });

  it("keeps resend-verification available without a client cooldown after EMAIL_NOT_VERIFIED", async () => {
    routeState.query = {
      next: "/apps/classroom.group-seating-studio",
      classroomPlannerEntryOrigin: "dashboard",
    };
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

    const wrapper = mount(AuthLoginPanel, {
      global: {
        stubs: {
          RouterLink: RouterLinkStub,
        },
      },
    });

    await wrapper.get("#auth-login-email").setValue("olof.larsson@harryda.se");
    await wrapper.get("#auth-login-password").setValue("hemligt-losenord");
    await wrapper.get("form").trigger("submit.prevent");
    await flushPromises();

    expect(wrapper.text()).toContain("Verifiera din e-postadress innan du loggar in");
    expect(wrapper.text()).toContain("Skicka nytt verifieringsmejl");

    await wrapper.get("button.btn-secondary").trigger("click");
    await flushPromises();

    expect(apiPostMock).toHaveBeenCalledWith("/api/v1/auth/resend-verification", {
      email: "olof.larsson@harryda.se",
      next: "/apps/classroom.group-seating-studio",
      classroom_planner_entry_origin: "dashboard",
    });
    expect(wrapper.text()).toContain("Om kontot finns skickas ett nytt verifieringsmail");
    expect(wrapper.text()).not.toContain("Försök igen om");

    await wrapper.get("button.btn-secondary").trigger("click");
    await flushPromises();

    expect(apiPostMock).toHaveBeenNthCalledWith(2, "/api/v1/auth/resend-verification", {
      email: "olof.larsson@harryda.se",
      next: "/apps/classroom.group-seating-studio",
      classroom_planner_entry_origin: "dashboard",
    });
  });
});
