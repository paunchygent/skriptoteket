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
type PublicAppCapabilityBootstrapResponse =
  components["schemas"]["PublicAppCapabilityBootstrapResponse"];

const routeMocks = vi.hoisted(() => ({
  route: {
    params: {
      appId: "classroom.group-seating-studio",
    } as Record<string, string>,
  },
  router: {
    push: vi.fn(),
  },
}));

const clientMocks = vi.hoisted(() => ({
  isApiError: vi.fn(),
  publicApiGet: vi.fn(),
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
  isApiError: clientMocks.isApiError,
  publicApiGet: clientMocks.publicApiGet,
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

function createScopedPublicBootstrap(
  overrides: Partial<PublicAppCapabilityBootstrapResponse> = {},
): PublicAppCapabilityBootstrapResponse {
  return {
    app_id: "documents.conversion_hub",
    title: "Exam Converter",
    summary: "Konvertera DigiExam-prov utan inloggning.",
    ui_mode: "bespoke_required",
    public_access_profile: "authenticated_only",
    host_mode: "public",
    public_capability: {
      scope: "exam_converter",
      profile: "public_browser_runtime",
      frontend_route: "/public/apps/documents.conversion_hub/exam-converter",
      api_namespace: "/api/v1/public/apps/documents.conversion_hub/exam-converter",
      runtime_status: "active",
    },
    ...overrides,
  };
}

describe("PublicAppHostView", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    routeMocks.route.params.appId = "classroom.group-seating-studio";
    delete routeMocks.route.params.publicCapabilitySlug;
    routeMocks.router.push.mockReset();
    clientMocks.isApiError.mockReset();
    clientMocks.isApiError.mockReturnValue(false);
    clientMocks.publicApiGet.mockReset();
    hostRegistryMocks.resolveCuratedAppHostView.mockReset();
    hostRegistryMocks.resolveCuratedAppHostView.mockReturnValue({
      component: PublicHostViewStub,
      props: { hostMode: "public" },
    });
  });

  it("loads the public bootstrap endpoint and renders the public Klassrumskartan shell", async () => {
    clientMocks.publicApiGet.mockResolvedValue(createPublicBootstrap());
    const pinia = createPinia();
    setActivePinia(pinia);

    const wrapper = mount(PublicAppHostView, {
      global: {
        plugins: [pinia],
      },
    });
    await flushPromises();
    await flushPromises();

    expect(clientMocks.publicApiGet).toHaveBeenCalledWith(
      "/api/v1/public/apps/classroom.group-seating-studio",
    );
    expect(wrapper.find("[data-test='classroom-planner-entry-view-stub']").exists()).toBe(true);
    expect(wrapper.text()).toContain("ClassroomPlannerEntryView public");

    wrapper.unmount();
  });

  it("keeps the public classroom planner host on the dedicated public view lane", async () => {
    clientMocks.publicApiGet.mockResolvedValue(createPublicBootstrap());
    const pinia = createPinia();
    setActivePinia(pinia);

    mount(PublicAppHostView, {
      global: {
        plugins: [pinia],
      },
    });
    await flushPromises();
    await flushPromises();

    expect(hostRegistryMocks.resolveCuratedAppHostView).toHaveBeenCalledWith(
      "classroom.group-seating-studio",
      "public",
    );
  });

  it("loads active Exam Converter metadata and resolves the public runtime view", async () => {
    routeMocks.route.params.appId = "documents.conversion_hub";
    routeMocks.route.params.publicCapabilitySlug = "exam-converter";
    clientMocks.publicApiGet.mockResolvedValue(createScopedPublicBootstrap());
    hostRegistryMocks.resolveCuratedAppHostView.mockReturnValue({
      component: PublicHostViewStub,
      props: {},
    });
    const pinia = createPinia();
    setActivePinia(pinia);

    const wrapper = mount(PublicAppHostView, {
      global: {
        plugins: [pinia],
      },
    });
    await flushPromises();
    await flushPromises();

    expect(clientMocks.publicApiGet).toHaveBeenCalledWith(
      "/api/v1/public/apps/documents.conversion_hub/exam-converter",
    );
    expect(hostRegistryMocks.resolveCuratedAppHostView).toHaveBeenCalledWith(
      "documents.conversion_hub",
      "public",
    );
    expect(wrapper.find("[data-test='classroom-planner-entry-view-stub']").exists()).toBe(true);

    wrapper.unmount();
  });
});
