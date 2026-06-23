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
import {
  LOGOUT_GENERIC_FAILURE_MESSAGE,
  LOGOUT_NETWORK_FAILURE_MESSAGE,
} from "./stores/authUserMessages";

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

const toastMocks = vi.hoisted(() => ({
  failure: vi.fn(),
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

vi.mock("./composables/useToast", () => ({
  useToast: () => toastMocks,
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
    toastMocks.failure.mockReset();
    window.history.replaceState(null, "");
  });

  function mountWithLogoutButton() {
    return mount(App, {
      global: {
        stubs: {
          LandingLayout: { template: "<div><slot /></div>" },
          AuthLayout: {
            props: ["logoutInProgress"],
            emits: ["logout"],
            template:
              "<div><button data-test='logout' @click='$emit(\"logout\")'>Logga ut</button><slot /></div>",
          },
          ToastHost: { template: "<div />" },
          RouterView: { template: "<div />" },
        },
      },
    });
  }

  async function flushAsync(): Promise<void> {
    for (let attempt = 0; attempt < 3; attempt += 1) {
      await Promise.resolve();
      await nextTick();
    }
  }

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

  it("keeps canonical Audio Transcription as the protected destination when auth drops", async () => {
    if (!routerMocks.route || !routerMocks.auth) {
      throw new Error("Expected route and auth mocks to be initialized.");
    }
    routerMocks.route.name = "audio-transcription-authenticated";
    routerMocks.route.fullPath = "/apps/audio-transcription";
    routerMocks.route.path = "/apps/audio-transcription";
    routerMocks.route.params = { appId: "" };
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
      query: { next: "/apps/audio-transcription" },
    });
  });

  it("shows the network logout failure as a toast instead of a layout panel", async () => {
    if (!routerMocks.auth) {
      throw new Error("Expected auth mocks to be initialized.");
    }
    routerMocks.auth.logout.mockRejectedValueOnce(new Error(LOGOUT_NETWORK_FAILURE_MESSAGE));

    const wrapper = mountWithLogoutButton();
    await wrapper.get("[data-test='logout']").trigger("click");
    await flushAsync();

    expect(toastMocks.failure).toHaveBeenCalledWith(LOGOUT_NETWORK_FAILURE_MESSAGE);
    expect(routerMocks.router.push).not.toHaveBeenCalledWith({ path: "/" });
  });

  it("normalizes non-network logout failures before showing the toast", async () => {
    if (!routerMocks.auth) {
      throw new Error("Expected auth mocks to be initialized.");
    }
    routerMocks.auth.logout.mockRejectedValueOnce(new Error("raw backend detail"));

    const wrapper = mountWithLogoutButton();
    await wrapper.get("[data-test='logout']").trigger("click");
    await flushAsync();

    expect(toastMocks.failure).toHaveBeenCalledWith(LOGOUT_GENERIC_FAILURE_MESSAGE);
  });
});
