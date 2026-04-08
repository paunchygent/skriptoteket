/**
 * Public curated app host tests.
 *
 * These tests verify that the dedicated public host route only calls the
 * public bootstrap endpoint and resolves the public Klassrumskartan shell.
 */

import { mount } from "@vue/test-utils";
import { defineComponent, nextTick } from "vue";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";

import PublicAppHostView from "./PublicAppHostView.vue";
import type { components } from "../api/openapi";

type PublicAppBootstrapResponse = components["schemas"]["PublicAppBootstrapResponse"];

const routeMocks = vi.hoisted(() => ({
  route: {
    params: {
      appId: "classroom.group-seating-studio",
    },
  },
  router: {
    push: vi.fn(),
  },
}));

const clientMocks = vi.hoisted(() => ({
  apiGet: vi.fn(),
  isApiError: vi.fn(),
}));

const hostRegistryMocks = vi.hoisted(() => ({
  resolveCuratedAppHostView: vi.fn(),
}));

vi.mock("vue-router", async (importOriginal) => {
  const actual = await importOriginal<typeof import("vue-router")>();
  return {
    ...actual,
    RouterLink: {
      props: ["to"],
      template: "<a :href='typeof to === \"string\" ? to : to.path'><slot /></a>",
    },
    useRoute: () => routeMocks.route,
    useRouter: () => routeMocks.router,
  };
});

vi.mock("../api/client", () => ({
  apiGet: clientMocks.apiGet,
  isApiError: clientMocks.isApiError,
}));

vi.mock("./curatedAppHostRegistry", async (importOriginal) => {
  const actual = await importOriginal<typeof import("./curatedAppHostRegistry")>();
  return {
    ...actual,
    resolveCuratedAppHostView: hostRegistryMocks.resolveCuratedAppHostView,
  };
});

const PublicHostViewStub = defineComponent({
  name: "PublicHostViewStub",
  props: {
    hostMode: { type: String, required: false, default: null },
  },
  template: "<div data-test='classroom-planner-entry-view-stub'>ClassroomPlannerEntryView {{ hostMode }}</div>",
});

async function flushPromises(): Promise<void> {
  await Promise.resolve();
  await Promise.resolve();
  await nextTick();
  await nextTick();
  await vi.dynamicImportSettled();
  await nextTick();
}

function createPublicBootstrap(
  overrides: Partial<PublicAppBootstrapResponse> = {},
): PublicAppBootstrapResponse {
  return {
    app_id: "classroom.group-seating-studio",
    title: "Klassrumskartan",
    summary: "Skapa sittplatsscheman och grupper automatiskt.",
    ui_mode: "bespoke_required",
    public_access_profile: "public_browser_workspace_with_upgrade",
    host_mode: "public",
    ...overrides,
  };
}

describe("PublicAppHostView", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    routeMocks.route.params.appId = "classroom.group-seating-studio";
    routeMocks.router.push.mockReset();
    clientMocks.apiGet.mockReset();
    clientMocks.isApiError.mockReset();
    clientMocks.isApiError.mockReturnValue(false);
    hostRegistryMocks.resolveCuratedAppHostView.mockReset();
    hostRegistryMocks.resolveCuratedAppHostView.mockReturnValue({
      component: PublicHostViewStub,
      props: { hostMode: "public" },
    });
  });

  it("loads the public bootstrap endpoint and renders the public Klassrumskartan shell", async () => {
    clientMocks.apiGet.mockResolvedValue(createPublicBootstrap());
    const pinia = createPinia();
    setActivePinia(pinia);

    const wrapper = mount(PublicAppHostView, {
      global: {
        plugins: [pinia],
      },
    });
    await flushPromises();
    await flushPromises();

    expect(clientMocks.apiGet).toHaveBeenCalledWith(
      "/api/v1/public/apps/classroom.group-seating-studio",
    );
    expect(wrapper.find("[data-test='classroom-planner-entry-view-stub']").exists()).toBe(true);
    expect(wrapper.text()).toContain("ClassroomPlannerEntryView public");

    wrapper.unmount();
  });
});
