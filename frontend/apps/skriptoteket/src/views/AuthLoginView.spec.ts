/**
 * Dedicated auth-login view tests.
 *
 * These tests verify that the page-based auth-entry route resumes the intended
 * destination after local login succeeds.
 */

import { flushPromises, mount } from "@vue/test-utils";
import { reactive, ref } from "vue";
import { beforeEach, describe, expect, it, vi } from "vitest";

import AuthLoginView from "./AuthLoginView.vue";

const viewMocks = vi.hoisted(() => ({
  route: {
    name: "auth-login",
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

  it("pushes the preserved destination after login succeeds", async () => {
    viewMocks.route.query = { next: "/profile" };

    const wrapper = mount(AuthLoginView, {
      global: {
        stubs: {
          AuthLoginPanel: {
            emits: ["success"],
            template:
              "<button type='button' data-test='auth-success' @click=\"$emit('success')\">Success</button>",
          },
        },
      },
    });

    await wrapper.get("[data-test='auth-success']").trigger("click");
    await flushPromises();

    expect(viewMocks.pageTransition?.suppressNext).toHaveBeenCalled();
    expect(viewMocks.router.push).toHaveBeenCalledWith({ path: "/profile" });
  });

  it("restores the classroom planner entry-origin hint when login succeeds", async () => {
    viewMocks.route.query = {
      next: "/apps/classroom.group-seating-studio",
      classroomPlannerEntryOrigin: "dashboard",
    };

    const wrapper = mount(AuthLoginView, {
      global: {
        stubs: {
          AuthLoginPanel: {
            emits: ["success"],
            template:
              "<button type='button' data-test='auth-success' @click=\"$emit('success')\">Success</button>",
          },
        },
      },
    });

    await wrapper.get("[data-test='auth-success']").trigger("click");
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

  it("still completes the redirect if auth flips before the success event returns", async () => {
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
});
