/**
 * Root SPA shell tests.
 *
 * These tests verify that auth-driven login handoffs preserve protected-route
 * redirect objects so Klassrumskartan keeps its entry-origin contract.
 */

import { mount } from "@vue/test-utils";
import type { RouteLocationRaw } from "vue-router";
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

type MockLoginModal = {
  isOpen: { value: boolean };
  redirectTo: { value: RouteLocationRaw | null };
  open: ReturnType<typeof vi.fn>;
  close: ReturnType<typeof vi.fn>;
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
  loginModal: null as MockLoginModal | null,
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

vi.mock("./composables/useLoginModal", () => ({
  useLoginModal: () => routerMocks.loginModal,
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
    routerMocks.loginModal = {
      isOpen: ref(false),
      redirectTo: ref<RouteLocationRaw | null>(null),
      open: vi.fn((redirect?: RouteLocationRaw | null) => {
        (routerMocks.loginModal as { redirectTo: { value: unknown }; isOpen: { value: boolean } }).redirectTo.value = redirect ?? null;
        (routerMocks.loginModal as { isOpen: { value: boolean } }).isOpen.value = true;
      }),
      close: vi.fn(() => {
        (routerMocks.loginModal as { redirectTo: { value: unknown }; isOpen: { value: boolean } }).redirectTo.value = null;
        (routerMocks.loginModal as { isOpen: { value: boolean } }).isOpen.value = false;
      }),
    };
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

  it("reopens login with the classroom planner origin preserved when auth drops on the app route", async () => {
    window.history.replaceState({ classroomPlannerEntryOrigin: "dashboard" }, "");

    mount(App, {
      global: {
        stubs: {
          LandingLayout: { template: "<div><slot /></div>" },
          AuthLayout: { template: "<div><slot /></div>" },
          LoginModal: { template: "<div />" },
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

    expect(routerMocks.loginModal?.open).toHaveBeenCalledWith({
      name: "app-detail",
      params: { appId: "classroom.group-seating-studio" },
      state: {
        classroomPlannerEntryOrigin: "dashboard",
      },
    });
  });

  it("pushes the stored redirect object after login succeeds", async () => {
    if (!routerMocks.loginModal) {
      throw new Error("Expected login modal mocks to be initialized.");
    }
    routerMocks.loginModal.isOpen.value = true;
    routerMocks.loginModal.redirectTo.value = {
      name: "app-detail",
      params: { appId: "classroom.group-seating-studio" },
      state: {
        classroomPlannerEntryOrigin: "dashboard",
      },
    };

    const wrapper = mount(App, {
      global: {
        stubs: {
          LandingLayout: { template: "<div><slot /></div>" },
          AuthLayout: { template: "<div><slot /></div>" },
          LoginModal: {
            emits: ["success", "close"],
            template: "<button type='button' data-test='login-success' @click=\"$emit('success')\">Success</button>",
          },
          ToastHost: { template: "<div />" },
          RouterView: { template: "<div />" },
        },
      },
    });

    await wrapper.get("[data-test='login-success']").trigger("click");

    expect(routerMocks.pageTransition?.suppressNext).toHaveBeenCalled();
    expect(routerMocks.router.push).toHaveBeenCalledWith({
      name: "app-detail",
      params: { appId: "classroom.group-seating-studio" },
      state: {
        classroomPlannerEntryOrigin: "dashboard",
      },
    });
  });

  it("closes the login modal after route navigation succeeds", async () => {
    if (!routerMocks.loginModal || !routerMocks.route) {
      throw new Error("Expected route and login modal mocks to be initialized.");
    }
    routerMocks.loginModal.isOpen.value = true;

    mount(App, {
      global: {
        stubs: {
          LandingLayout: { template: "<div><slot /></div>" },
          AuthLayout: { template: "<div><slot /></div>" },
          LoginModal: { template: "<div />" },
          ToastHost: { template: "<div />" },
          RouterView: { template: "<div />" },
        },
      },
    });

    routerMocks.route.fullPath = "/forgot-password";
    routerMocks.route.path = "/forgot-password";
    routerMocks.route.name = "forgot-password";
    routerMocks.route.matched = [{ meta: {} }];
    await nextTick();
    await nextTick();

    expect(routerMocks.loginModal.close).toHaveBeenCalled();
  });
});
