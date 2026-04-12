/**
 * Dedicated auth-login view tests.
 *
 * These tests verify that the page-based auth-entry route hands signed-out
 * users to HuleEdu and resumes the intended destination when shared auth
 * bootstrap later marks the user authenticated.
 */

import { flushPromises, mount } from "@vue/test-utils";
import { reactive, ref } from "vue";
import { beforeEach, describe, expect, it, vi } from "vitest";

import AuthLoginView from "./AuthLoginView.vue";

const viewMocks = vi.hoisted(() => ({
  route: {
    name: "auth-login",
    path: "/auth/login",
    query: {} as Record<string, unknown>,
  },
  router: {
    push: vi.fn().mockResolvedValue(undefined),
  },
  auth: null as {
    isAuthenticated: boolean;
  } | null,
  pageTransition: null as {
    suppressNextPageTransition: { value: boolean };
    suppressNext: ReturnType<typeof vi.fn>;
    reset: ReturnType<typeof vi.fn>;
  } | null,
}));

vi.mock("vue-router", () => ({
  useRoute: () => viewMocks.route,
  useRouter: () => viewMocks.router,
}));

vi.mock("../composables/usePageTransition", () => ({
  usePageTransition: () => viewMocks.pageTransition,
}));

vi.mock("../stores/auth", () => ({
  useAuthStore: () => viewMocks.auth,
}));

describe("AuthLoginView", () => {
  beforeEach(() => {
    viewMocks.route.name = "auth-login";
    viewMocks.route.path = "/auth/login";
    viewMocks.route.query = {};
    viewMocks.router.push.mockReset();
    viewMocks.router.push.mockResolvedValue(undefined);
    viewMocks.auth = reactive({
      isAuthenticated: false,
    });
    viewMocks.pageTransition = {
      suppressNextPageTransition: ref(false),
      suppressNext: vi.fn(),
      reset: vi.fn(),
    };
  });

  it("shows the default home-return copy when no next param is present", () => {
    const wrapper = mount(AuthLoginView, {
      global: {
        stubs: {
          AuthLoginPanel: { template: "<div data-test='auth-login-panel-stub' />" },
        },
      },
    });

    expect(wrapper.text()).toContain("Logga in");
    expect(wrapper.text()).toContain("fortsätta till din startsida");
  });

  it("shows preserved-destination copy when a next param is present", () => {
    viewMocks.route.query = { next: "/profile" };

    const wrapper = mount(AuthLoginView, {
      global: {
        stubs: {
          AuthLoginPanel: { template: "<div data-test='auth-login-panel-stub' />" },
        },
      },
    });

    expect(wrapper.text()).toContain("skickas du vidare till rätt sida");
  });

  it("completes the redirect when shared auth bootstrap marks the user authenticated", async () => {
    viewMocks.route.query = {
      next: "/apps/classroom.group-seating-studio",
      classroomPlannerEntryOrigin: "dashboard",
    };

    mount(AuthLoginView, {
      global: {
        stubs: {
          AuthLoginPanel: { template: "<div data-test='auth-login-panel-stub' />" },
        },
      },
    });

    if (!viewMocks.auth) {
      throw new Error("Expected auth stub to be initialized.");
    }
    viewMocks.auth.isAuthenticated = true;
    await flushPromises();

    expect(viewMocks.pageTransition?.suppressNext).toHaveBeenCalled();
    expect(viewMocks.router.push).toHaveBeenCalledWith({
      name: "app-detail",
      params: { appId: "classroom.group-seating-studio" },
      state: {
        classroomPlannerEntryOrigin: "dashboard",
      },
    });
  });

  it("completes the redirect from the HuleEdu callback route", async () => {
    viewMocks.route.name = "auth-callback";
    viewMocks.route.path = "/auth/callback";
    viewMocks.route.query = { next: "/editor" };

    mount(AuthLoginView, {
      global: {
        stubs: {
          AuthLoginPanel: { template: "<div data-test='auth-login-panel-stub' />" },
        },
      },
    });

    if (!viewMocks.auth) {
      throw new Error("Expected auth stub to be initialized.");
    }
    viewMocks.auth.isAuthenticated = true;
    await flushPromises();

    expect(viewMocks.pageTransition?.suppressNext).toHaveBeenCalled();
    expect(viewMocks.router.push).toHaveBeenCalledWith("/editor");
  });

  it("preserves query and hash details from the HuleEdu callback route", async () => {
    viewMocks.route.name = "auth-callback";
    viewMocks.route.path = "/auth/callback";
    viewMocks.route.query = { next: "/admin/tools?status=draft#review" };

    mount(AuthLoginView, {
      global: {
        stubs: {
          AuthLoginPanel: { template: "<div data-test='auth-login-panel-stub' />" },
        },
      },
    });

    if (!viewMocks.auth) {
      throw new Error("Expected auth stub to be initialized.");
    }
    viewMocks.auth.isAuthenticated = true;
    await flushPromises();

    expect(viewMocks.router.push).toHaveBeenCalledWith("/admin/tools?status=draft#review");
  });
});
