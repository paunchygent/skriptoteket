/**
 * Route-stage tests for the root SPA shell.
 *
 * These tests mount the real shell with a real memory-history router and the
 * real page-transition state, and check that switching the page animation on
 * or off never rebuilds the view on a same-path navigation.
 */

import { flushPromises, mount } from "@vue/test-utils";
import { defineComponent, h, reactive } from "vue";
import { createPinia } from "pinia";
import { createMemoryHistory, createRouter, type Router } from "vue-router";
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

const workspace: PageLifecycle = { mounts: 0, unmounts: 0 };
const other: PageLifecycle = { mounts: 0, unmounts: 0 };

function buildRouter(): Router {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: "/auth/callback", component: { render: () => h("p", "callback") } },
      { path: "/apps/exam-workspace", component: trackedPage(workspace) },
      { path: "/other", component: trackedPage(other) },
    ],
  });
  router.beforeEach((to) => {
    if (to.path === "/auth/callback") {
      return String(to.query.next);
    }
    return true;
  });
  return router;
}

async function mountShell(router: Router) {
  const wrapper = mount(App, {
    attachTo: document.body,
    global: {
      plugins: [createPinia(), router],
      stubs: {
        transition: false,
        LandingLayout: { template: "<div><slot /></div>" },
        AuthLayout: { template: "<div><slot /></div>" },
        ToastHost: { template: "<div />" },
      },
    },
  });
  await router.isReady();
  await flushPromises();
  return wrapper;
}

describe.each([
  { layout: "authenticated", isAuthenticated: true },
  { layout: "landing", isAuthenticated: false },
])("App route stage ($layout layout)", ({ isAuthenticated }) => {
  let wrapper: Awaited<ReturnType<typeof mountShell>> | null = null;

  beforeEach(() => {
    Object.assign(workspace, { mounts: 0, unmounts: 0 });
    Object.assign(other, { mounts: 0, unmounts: 0 });
    usePageTransition().reset();
    authMocks.store = reactive({
      isAuthenticated,
      user: isAuthenticated ? { id: "user-1", email: "teacher@example.com", role: "user" } : null,
      profile: null,
      bootstrap: vi.fn().mockResolvedValue(undefined),
      logout: vi.fn().mockResolvedValue(undefined),
      hasAtLeastRole: vi.fn().mockReturnValue(false),
    });
  });

  afterEach(() => {
    wrapper?.unmount();
    wrapper = null;
  });

  it("keeps the page entered through a guard redirect when only the query changes", async () => {
    const router = buildRouter();
    await router.push("/auth/callback?next=/apps/exam-workspace");
    wrapper = await mountShell(router);

    expect(router.currentRoute.value.redirectedFrom).toBeDefined();
    expect(workspace).toEqual({ mounts: 1, unmounts: 0 });
    const stageItem = wrapper.get(".route-stage-item").element;

    await router.replace({ path: "/apps/exam-workspace", query: { document: "lineage-1" } });
    await flushPromises();

    expect(router.currentRoute.value.redirectedFrom).toBeUndefined();
    expect(workspace).toEqual({ mounts: 1, unmounts: 0 });
    expect(wrapper.get(".route-stage-item").element).toBe(stageItem);
  });

  it("keeps the page after a suppressed transition when only the query changes", async () => {
    const router = buildRouter();
    await router.push("/other");
    wrapper = await mountShell(router);

    usePageTransition().suppressNext();
    await router.push("/apps/exam-workspace");
    await flushPromises();

    expect(usePageTransition().suppressNextPageTransition.value).toBe(false);
    expect(workspace).toEqual({ mounts: 1, unmounts: 0 });
    const stageItem = wrapper.get(".route-stage-item").element;

    await router.replace({ path: "/apps/exam-workspace", query: { document: "lineage-1" } });
    await flushPromises();

    expect(workspace).toEqual({ mounts: 1, unmounts: 0 });
    expect(wrapper.get(".route-stage-item").element).toBe(stageItem);
  });

  it("replaces the page when the path changes", async () => {
    vi.useFakeTimers();
    try {
      const router = buildRouter();
      await router.push("/apps/exam-workspace");
      wrapper = await mountShell(router);
      const stageItem = wrapper.get(".route-stage-item").element;

      await router.push("/other");
      await flushPromises();
      vi.runAllTimers();
      await flushPromises();

      expect(workspace).toEqual({ mounts: 1, unmounts: 1 });
      expect(other).toEqual({ mounts: 1, unmounts: 0 });
      expect(wrapper.findAll(".route-stage-item")).toHaveLength(1);
      expect(wrapper.get(".route-stage-item").element).not.toBe(stageItem);
    } finally {
      vi.useRealTimers();
    }
  });

  it("animates a path change and skips the animation after suppressNext", async () => {
    vi.useFakeTimers();
    try {
      const router = buildRouter();
      await router.push("/apps/exam-workspace");
      wrapper = await mountShell(router);

      await router.push("/other");
      await flushPromises();
      const animated = wrapper.findAll(".route-stage-item");
      expect(animated).toHaveLength(2);
      expect(animated[0].classes()).toContain("page-leave-active");
      expect(animated[1].classes()).toContain("page-enter-active");
      vi.runAllTimers();
      await flushPromises();

      usePageTransition().suppressNext();
      await router.push("/apps/exam-workspace");
      await flushPromises();
      const suppressed = wrapper.findAll(".route-stage-item");
      expect(suppressed).toHaveLength(1);
      expect(suppressed[0].classes().filter((name) => name.startsWith("page-"))).toEqual([]);
    } finally {
      vi.useRealTimers();
    }
  });
});
