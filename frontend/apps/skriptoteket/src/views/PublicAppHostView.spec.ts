/**
 * Public curated app host tests.
 *
 * These tests verify that the dedicated public host route only calls the
 * public bootstrap endpoint and resolves the public Klassrumskartan shell.
 */

import { mount } from "@vue/test-utils";
import { nextTick } from "vue";
import { beforeEach, describe, expect, it, vi } from "vitest";

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

const loginModalMocks = vi.hoisted(() => ({
  open: vi.fn(),
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

vi.mock("../composables/useLoginModal", () => ({
  useLoginModal: () => loginModalMocks,
}));

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
    routeMocks.route.params.appId = "classroom.group-seating-studio";
    routeMocks.router.push.mockReset();
    clientMocks.apiGet.mockReset();
    clientMocks.isApiError.mockReset();
    clientMocks.isApiError.mockReturnValue(false);
    loginModalMocks.open.mockReset();
  });

  it("loads the public bootstrap endpoint and renders the public Klassrumskartan shell", async () => {
    clientMocks.apiGet.mockResolvedValue(createPublicBootstrap());

    const wrapper = mount(PublicAppHostView);
    await flushPromises();
    await flushPromises();

    expect(clientMocks.apiGet).toHaveBeenCalledWith(
      "/api/v1/public/apps/classroom.group-seating-studio",
    );
    expect(wrapper.text()).toContain("Klassrumskartan");
    expect(wrapper.text()).toContain("Vissa funktioner kräver att du registrerar ett konto.");

    wrapper.unmount();
  });
});
