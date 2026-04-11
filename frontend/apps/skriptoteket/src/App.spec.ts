/**
 * Root SPA shell tests.
 *
 * These tests verify that auth-driven route recovery uses the dedicated
 * `/auth/login` handoff without dropping Klassrumskartan's entry-origin hint.
 */

import { mount } from "@vue/test-utils";
import { computed, nextTick, reactive, ref } from "vue";
import { beforeEach, describe, expect, it, vi } from "vitest";

import App from "./App.vue";

type MockRoute = {
  name: string;
  fullPath: string;
  path: string;
  params: {
    appId: string;
  };
  meta: Record<string, unknown>;
  matched: Array<{ meta: Record<string, unknown> }>;
  redirectedFrom: unknown;
};

type MockAuthStore = {
  isAuthenticated: boolean;
  user: { id: string; email: string; role: string } | null;
  profile: null;
  aiPolicy: null;
  bootstrap: ReturnType<typeof vi.fn>;
  logout: ReturnType<typeof vi.fn>;
  hasAtLeastRole: ReturnType<typeof vi.fn>;
};

type MockPageTransition = {
  suppressNextPageTransition: { value: boolean };
  suppressNext: ReturnType<typeof vi.fn>;
  reset: ReturnType<typeof vi.fn>;
};

type MockHelp = {
  isOpen: { readonly value: boolean };
};

const routerMocks = vi.hoisted(() => ({
  route: null as MockRoute | null,
  router: {
    push: vi.fn(),
  },
  auth: null as MockAuthStore | null,
  help: null as MockHelp | null,
  pageTransition: null as MockPageTransition | null,
}));

vi.mock("vue-router", () => ({
  useRoute: () => routerMocks.route,
  useRouter: () => routerMocks.router,
}));

vi.mock("./stores/auth", () => ({
  useAuthStore: () => routerMocks.auth,
}));

vi.mock("./composables/usePageTransition", () => ({
  usePageTransition: () => routerMocks.pageTransition,
}));

vi.mock("./components/help/useHelp", () => ({
  useHelp: () => routerMocks.help,
}));

describe("App", () => {
  beforeEach(() => {
    routerMocks.route = reactive({
      name: "app-detail",
      fullPath: "/apps/classroom.group-seating-studio",
      path: "/apps/classroom.group-seating-studio",
      params: {
        appId: "classroom.group-seating-studio",
      },
      meta: {},
      matched: [{ meta: { requiresAuth: true } }],
      redirectedFrom: undefined,
    });
    routerMocks.auth = reactive({
      isAuthenticated: true,
      user: { id: "user-1", email: "teacher@example.com", role: "user" },
      profile: null,
      aiPolicy: null,
      bootstrap: vi.fn().mockResolvedValue(undefined),
      logout: vi.fn().mockResolvedValue(undefined),
      hasAtLeastRole: vi.fn().mockReturnValue(false),
    });
    routerMocks.help = {
      isOpen: computed(() => false),
    };
    routerMocks.pageTransition = {
      suppressNextPageTransition: ref(false),
      suppressNext: vi.fn(),
      reset: vi.fn(),
    };

    routerMocks.router.push.mockReset();
    window.history.replaceState(null, "");
  });

  it("routes to auth-login with the classroom planner origin preserved when auth drops", async () => {
    window.history.replaceState({ classroomPlannerEntryOrigin: "dashboard" }, "");

    mount(App, {
      global: {
        stubs: {
          LandingLayout: { template: "<div><slot /></div>" },
          AuthLayout: { template: "<div><slot /></div>" },
          ToastHost: { template: "<div />" },
          RouterView: { template: "<div />" },
        },
      },
    });

    if (!routerMocks.auth) {
      throw new Error("Expected auth mocks to be initialized.");
    }
    routerMocks.auth.isAuthenticated = false;
    await nextTick();
    await nextTick();

    expect(routerMocks.pageTransition?.suppressNext).toHaveBeenCalled();
    expect(routerMocks.router.push).toHaveBeenCalledWith({
      name: "auth-login",
      query: {
        next: "/apps/classroom.group-seating-studio",
        classroomPlannerEntryOrigin: "dashboard",
      },
      state: {
        classroomPlannerEntryOrigin: "dashboard",
      },
    });
  });

  it("routes generic protected surfaces to auth-login when auth drops", async () => {
    if (!routerMocks.route || !routerMocks.auth) {
      throw new Error("Expected route and auth mocks to be initialized.");
    }
    routerMocks.route.name = "browse";
    routerMocks.route.fullPath = "/browse";
    routerMocks.route.path = "/browse";
    routerMocks.route.matched = [{ meta: { requiresAuth: true } }];

    mount(App, {
      global: {
        stubs: {
          LandingLayout: { template: "<div><slot /></div>" },
          AuthLayout: { template: "<div><slot /></div>" },
          ToastHost: { template: "<div />" },
          RouterView: { template: "<div />" },
        },
      },
    });

    routerMocks.auth.isAuthenticated = false;
    await nextTick();
    await nextTick();

    expect(routerMocks.pageTransition?.suppressNext).toHaveBeenCalled();
    expect(routerMocks.router.push).toHaveBeenCalledWith({
      name: "auth-login",
      query: { next: "/browse" },
    });
  });

  it("keeps the full current protected destination when a session expires", async () => {
    if (!routerMocks.route || !routerMocks.auth) {
      throw new Error("Expected route and auth mocks to be initialized.");
    }
    routerMocks.route.name = "admin-tools";
    routerMocks.route.fullPath = "/admin/tools?status=draft#review";
    routerMocks.route.path = "/admin/tools";
    routerMocks.route.matched = [{ meta: { requiresAuth: true, minRole: "admin" } }];

    mount(App, {
      global: {
        stubs: {
          LandingLayout: { template: "<div><slot /></div>" },
          AuthLayout: { template: "<div><slot /></div>" },
          ToastHost: { template: "<div />" },
          RouterView: { template: "<div />" },
        },
      },
    });

    routerMocks.auth.isAuthenticated = false;
    await nextTick();
    await nextTick();

    expect(routerMocks.pageTransition?.suppressNext).toHaveBeenCalled();
    expect(routerMocks.router.push).toHaveBeenCalledWith({
      name: "auth-login",
      query: { next: "/admin/tools?status=draft#review" },
    });
  });
});
