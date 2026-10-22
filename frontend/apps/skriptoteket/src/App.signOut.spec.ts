/**
 * Sign-out tests for the root SPA shell.
 *
 * These tests mount the real shell with a real memory-history router and check
 * that the signed-out frame never mounts a route that needs sign-in, whether the
 * teacher signs out or the session ends on a protected page.
 */

import { flushPromises, mount } from "@vue/test-utils";
import { defineComponent, h, reactive, type SetupContext } from "vue";
import { createPinia } from "pinia";
import { createMemoryHistory, createRouter, type RouteMeta, type Router } from "vue-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import App from "./App.vue";
import { usePageTransition } from "./composables/usePageTransition";

const authMocks = vi.hoisted(() => ({
  store: null as Record<string, unknown> | null,
}));

vi.mock("./stores/auth", () => ({
  useAuthStore: () => authMocks.store,
}));

type PageLifecycle = { mounts: number; unmounts: number };

function trackedPage(lifecycle: PageLifecycle) {
  return defineComponent({
    mounted() {
      lifecycle.mounts += 1;
    },
    unmounted() {
      lifecycle.unmounts += 1;
    },
    render: () => h("p", "page"),
  });
}

const protectedPage: PageLifecycle = { mounts: 0, unmounts: 0 };
const home: PageLifecycle = { mounts: 0, unmounts: 0 };

function buildRouter(protectedMeta: RouteMeta): Router {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: "/", component: trackedPage(home) },
      { path: "/auth/login", name: "auth-login", component: { render: () => h("p", "login") } },
      { path: "/apps/exam-workspace", component: trackedPage(protectedPage), meta: protectedMeta },
    ],
  });
}

const AuthLayoutStub = {
  emits: ["logout"],
  setup(_props: unknown, { emit, slots }: SetupContext<["logout"]>) {
    return () =>
      h("div", [
        h("button", { "data-test": "logout", onClick: () => emit("logout") }, "logout"),
        slots.default?.(),
      ]);
  },
};

async function mountShell(router: Router) {
  const wrapper = mount(App, {
    attachTo: document.body,
    global: {
      plugins: [createPinia(), router],
      stubs: {
        transition: false,
        LandingLayout: { template: "<div><slot /></div>" },
        AuthLayout: AuthLayoutStub,
        ToastHost: { template: "<div />" },
      },
    },
  });
  await router.isReady();
  await flushPromises();
  return wrapper;
}

describe.each([
  { rule: "requiresAuth", protectedMeta: { requiresAuth: true } },
  { rule: "minRole", protectedMeta: { minRole: "admin" } },
])("App sign-out on a $rule route", ({ protectedMeta }) => {
  let wrapper: Awaited<ReturnType<typeof mountShell>> | null = null;
  let store: { user: unknown; isAuthenticated: boolean };

  beforeEach(() => {
    Object.assign(protectedPage, { mounts: 0, unmounts: 0 });
    Object.assign(home, { mounts: 0, unmounts: 0 });
    usePageTransition().reset();
    store = reactive({
      isAuthenticated: true,
      user: { id: "user-1", email: "teacher@example.com", role: "admin" },
      profile: null,
      bootstrap: vi.fn().mockResolvedValue(undefined),
      logout: vi.fn(async () => {
        store.user = null;
        store.isAuthenticated = false;
      }),
      hasAtLeastRole: vi.fn().mockReturnValue(false),
    });
    authMocks.store = store as unknown as Record<string, unknown>;
  });

  afterEach(() => {
    wrapper?.unmount();
    wrapper = null;
  });

  it("never mounts the protected page again when the teacher signs out", async () => {
    const router = buildRouter(protectedMeta);
    await router.push("/apps/exam-workspace");
    wrapper = await mountShell(router);
    expect(protectedPage).toEqual({ mounts: 1, unmounts: 0 });

    await wrapper.get("[data-test='logout']").trigger("click");
    await flushPromises();

    expect(router.currentRoute.value.path).toBe("/");
    expect(protectedPage).toEqual({ mounts: 1, unmounts: 1 });
    expect(home).toEqual({ mounts: 1, unmounts: 0 });
  });

  it("never mounts the protected page again when the session ends on it", async () => {
    const router = buildRouter(protectedMeta);
    await router.push("/apps/exam-workspace");
    wrapper = await mountShell(router);
    expect(protectedPage).toEqual({ mounts: 1, unmounts: 0 });

    store.user = null;
    store.isAuthenticated = false;
    await flushPromises();

    expect(router.currentRoute.value.name).toBe("auth-login");
    expect(protectedPage.mounts).toBe(1);
    expect(protectedPage.unmounts).toBe(1);
  });
});
