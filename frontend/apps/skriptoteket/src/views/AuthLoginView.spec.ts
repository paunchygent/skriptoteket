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

import { rememberAuthCallbackRetry } from "../composables/auth/authCallbackRetry";
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

const redirectMocks = vi.hoisted(() => ({
  redirectToSharedAuthCeremony: vi.fn(),
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

vi.mock("../composables/auth/sharedAuthRedirect", () => ({
  redirectToSharedAuthCeremony: redirectMocks.redirectToSharedAuthCeremony,
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
    redirectMocks.redirectToSharedAuthCeremony.mockReset();
    window.sessionStorage.clear();
  });

  it("starts the shared auth ceremony when no next param is present", () => {
    const wrapper = mount(AuthLoginView, {
      global: {
        stubs: {
          AuthLoginPanel: { template: "<div data-test='auth-login-panel-stub' />" },
        },
      },
    });

    expect(wrapper.text()).toContain("Logga in");
    expect(wrapper.text()).toContain("Inloggningen öppnas automatiskt");
    expect(redirectMocks.redirectToSharedAuthCeremony).toHaveBeenCalledWith(
      "https://api.hule.education/auth/login?app=skriptoteket&product_identity_realm=skriptoteket_standalone&return_to=http%3A%2F%2Flocalhost%3A3000%2Fauth%2Fcallback",
    );
  });

  it("preserves the destination in the shared auth ceremony URL", () => {
    viewMocks.route.query = { next: "/profile" };

    mount(AuthLoginView, {
      global: {
        stubs: {
          AuthLoginPanel: { template: "<div data-test='auth-login-panel-stub' />" },
        },
      },
    });

    expect(redirectMocks.redirectToSharedAuthCeremony).toHaveBeenCalledWith(
      "https://api.hule.education/auth/login?app=skriptoteket&product_identity_realm=skriptoteket_standalone&return_to=http%3A%2F%2Flocalhost%3A3000%2Fauth%2Fcallback&next=%2Fprofile",
    );
  });

  it("completes the redirect when shared auth bootstrap has marked the user authenticated", async () => {
    viewMocks.route.query = {
      next: "/apps/classroom.group-seating-studio",
      classroomPlannerEntryOrigin: "dashboard",
    };
    viewMocks.auth = reactive({
      isAuthenticated: true,
    });

    mount(AuthLoginView, {
      global: {
        stubs: {
          AuthLoginPanel: { template: "<div data-test='auth-login-panel-stub' />" },
        },
      },
    });

    await flushPromises();

    expect(viewMocks.pageTransition?.suppressNext).toHaveBeenCalled();
    expect(viewMocks.router.push).toHaveBeenCalledWith({
      name: "app-detail",
      params: { appId: "classroom.group-seating-studio" },
      state: {
        classroomPlannerEntryOrigin: "dashboard",
      },
    });
    expect(redirectMocks.redirectToSharedAuthCeremony).not.toHaveBeenCalled();
  });

  it("completes the redirect from the HuleEdu callback route", async () => {
    viewMocks.route.name = "auth-callback";
    viewMocks.route.path = "/auth/callback";
    viewMocks.route.query = { next: "/editor" };
    viewMocks.auth = reactive({
      isAuthenticated: true,
    });

    mount(AuthLoginView, {
      global: {
        stubs: {
          AuthLoginPanel: { template: "<div data-test='auth-login-panel-stub' />" },
        },
      },
    });

    await flushPromises();

    expect(viewMocks.pageTransition?.suppressNext).toHaveBeenCalled();
    expect(viewMocks.router.push).toHaveBeenCalledWith("/editor");
    expect(redirectMocks.redirectToSharedAuthCeremony).not.toHaveBeenCalled();
  });

  it("preserves query and hash details from the HuleEdu callback route", async () => {
    viewMocks.route.name = "auth-callback";
    viewMocks.route.path = "/auth/callback";
    viewMocks.route.query = { next: "/admin/tools?status=draft#review" };
    viewMocks.auth = reactive({
      isAuthenticated: true,
    });

    mount(AuthLoginView, {
      global: {
        stubs: {
          AuthLoginPanel: { template: "<div data-test='auth-login-panel-stub' />" },
        },
      },
    });

    await flushPromises();

    expect(viewMocks.router.push).toHaveBeenCalledWith("/admin/tools?status=draft#review");
    expect(redirectMocks.redirectToSharedAuthCeremony).not.toHaveBeenCalled();
  });

  it("retries shared auth once when the callback has no HuleEdu session", () => {
    viewMocks.route.name = "auth-callback";
    viewMocks.route.path = "/auth/callback";
    viewMocks.route.query = { next: "/" };

    mount(AuthLoginView, {
      global: {
        stubs: {
          AuthLoginPanel: { template: "<div data-test='auth-login-panel-stub' />" },
        },
      },
    });

    expect(viewMocks.pageTransition?.suppressNext).toHaveBeenCalled();
    expect(redirectMocks.redirectToSharedAuthCeremony).toHaveBeenCalledWith(
      "https://api.hule.education/auth/login?app=skriptoteket&product_identity_realm=skriptoteket_standalone&return_to=http%3A%2F%2Flocalhost%3A3000%2Fauth%2Fcallback&next=%2F",
    );
  });

  it("shows explicit recovery copy after the anonymous callback retry has already run", () => {
    viewMocks.route.name = "auth-callback";
    viewMocks.route.path = "/auth/callback";
    viewMocks.route.query = { next: "/" };
    rememberAuthCallbackRetry("/");

    const wrapper = mount(AuthLoginView);

    expect(wrapper.text()).toContain("Inloggningen slutfördes inte");
    expect(wrapper.text()).toContain("Logga in igen");
    expect(wrapper.text()).not.toContain("Saknar du konto?");
    expect(redirectMocks.redirectToSharedAuthCeremony).not.toHaveBeenCalled();
  });
});
